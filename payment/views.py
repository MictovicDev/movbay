from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from payment.factories import PaymentProviderFactory, PaymentMethodFactory
import time
import random
from rest_framework.response import Response
from rest_framework import status
import string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import os
import hmac
import hashlib
from django.http import HttpResponse
import json
from rest_framework.decorators import api_view
import json
import hashlib
import hmac
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Payment, Transactions
from django.contrib.auth import get_user_model
from wallet.models import Wallet
from .utils.fees import calculate_purchase_fee, calculate_wallet_fee
from payment.methods import CardPayment, WalletPayment, BankTransfer
from decimal import Decimal
from stores.models import Product
from django.shortcuts import get_object_or_404
from stores.models import Order
from wallet.models import WalletTransactions
from django.db import transaction
from stores.utils.create_order import create_order_with_items
from stores.models import Store

User = get_user_model()

logger = logging.getLogger(__name__)


class PaystackWebhookView(View):
    @method_decorator(csrf_exempt)
    @method_decorator(require_http_methods(["POST"]))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        body = request.body
        # Verify webhook signature
        if not self.verify_signature(body, request.META.get('HTTP_X_PAYSTACK_SIGNATURE')):
            logger.warning("Invalid webhook signature")
            return HttpResponse("Invalid signature", status=400)
        try:
            # Parse webhook data
            data = json.loads(body.decode('utf-8'))
            event = data.get('event')

            logger.info(f"Received Paystack webhook: {event}")

            # Handle different webhook events
            if event == 'charge.success':
                print(data)
                self.handle_successful_payment(data)
                return HttpResponse("Webhook received", status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook")
            return HttpResponse("Invalid JSON", status=400)
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return HttpResponse("Processing error", status=500)

    def verify_signature(self, body, signature):
        """Verify Paystack webhook signature"""
        if not signature:
            return False

        # Your Paystack secret key
        secret = os.getenv('PAYSTACK_SECRET_KEY').encode('utf-8')
        computed_hash = hmac.new(
            secret,
            body,
            hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(computed_hash, signature)

    def handle_successful_payment(self, data):
        """Handle successful payment"""
        payment_data = data.get('data', {})

        # Extract payment information
        reference = payment_data.get('reference')
        # Convert from kobo to naira
        amount = payment_data.get('amount', 0) / 100
        email = payment_data.get('customer', {}).get('email')
        user_id = payment_data.get('metadata', {}).get('user_id')
        payment_type = payment_data.get('metadata', {}).get('payment_type')

        user = User.objects.get(email=email)
        data = calculate_wallet_fee(amount)
        amount = data.get('wallet_credit')
        Payment.objects.create(user=user, provider='paystack', amount=amount,
                               transaction_id=reference, status='success', payment_type=payment_type)
        if payment_type == 'fund-wallet':
            wallet = Wallet.objects.get(owner=user)
            wallet.balance += int(amount)
            wallet.total_deposit += int(amount)
            wallet.save()

        # Send notification to React Native frontend
        self.notify_frontend({
            'type': 'payment_success',
            'reference': reference,
            'amount': amount,
            'email': email,
            'user_id': user_id,
            'timestamp': payment_data.get('paid_at')
        })

    def notify_frontend(self, notification_data):
        """Send notification to React Native frontend via WebSocket"""
        channel_layer = get_channel_layer()

        # Also send to general payment notifications group
        async_to_sync(channel_layer.group_send)(
            "payment_notifications",
            {
                'type': 'payment_notifications',
                'data': notification_data
            }
        )


class TestHandler(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        channel_layer = get_channel_layer()
        message = {
            "receveid": "Received Succefully"
        }
        try:
            async_to_sync(channel_layer.group_send)(
                "payment_notifications",
                {
                    'type': 'payment_notifications',
                    'data': message
                }
            )
            return Response({"message": "sent"})
        except Exception as e:
            return Response(str(e))


def generate_tx_ref(prefix="TX"):
    timestamp = int(time.time())  # seconds since epoch
    rand_str = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{timestamp}-{rand_str}"


class FundWallet(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider_name = request.data.get('provider_name')
        payment_method = request.data.get('payment_method')
        transaction_data = {
            "email": request.user.email,
            "amount": int(Decimal(request.data.get('amount', '0')) * 100),
            "reference": generate_tx_ref(),
            "currency": "NGN",
            "metadata": {
                "user_id": str(request.user.id),
                "payment_type": 'fund-wallet'}
        }
        provider = PaymentProviderFactory.create_provider(
            provider_name=provider_name)
        method = PaymentMethodFactory.create_method(method_name=payment_method)
        transaction_data = method.prepare_payment_data(transaction_data)
        result = provider.initialize_payment(transaction_data)
        return Response(result, status=status.HTTP_200_OK)


 #transaction.on_commit(lambda: send_order_email_to_seller(product.store.owner.email, product.name))
    # send me the product id you want to purchase
    # initialize payment for that product with the logged in user
    # construct the meta data
    # if the payment method is movbay wallet, i would confirm first, if the price for the goods can be purchased from your wallet
    # if it's bank transfer or card i send the payment to paystack,
    # from the webhook i access the metadata then know the payment type, then get the owner of the product.
    # then send response to the frontend that payment is succesfull, then frontend shows the order place screen
    # else if i didn't send a 200 response the frontend shows there was an error with the pament and the exact issue
    # if the order is accepted the user gets notified.
    # when order has been completed we fund the sellers wallet



class PurchasePaymentView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    {
        "cart_items": [
            {
            "product_id": 101,
            "quantity": 1
            },
            {
            "product_id": 102,
            "quantity": 1
            }
        ]
    }

    def post(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        amount = int(Decimal(request.data.get('amount', '0')))
        cart_items = request.data.get('cart_items')
        platform_wallet, created = Wallet.objects.get_or_create(
            owner__is_superuser=True)
        
        transaction_data = {
        "email": request.user.email,
        "amount": amount * 100,
        "reference": generate_tx_ref(),
        "currency": "NGN",
        "metadata": {
            "user_id": str(request.user),
            "payment_type": 'purchase-item'
        },
        "product_id": product.id
        }

        payment_method = request.data.get('payment_method')

        if payment_method == 'wallet':
            sender_wallet = request.user.wallet

            if sender_wallet.balance < amount:
                return Response({"Message": "Insufficient Funds"}, status=status.HTTP_402_PAYMENT_REQUIRED)

            with transaction.atomic():
                sender_wallet.balance -= amount
                sender_wallet.save()

                platform_wallet.balance += amount
                platform_wallet.save()

                payment = Payment.objects.create(
                    user=request.user,
                    method='wallet',
                    amount=amount,
                    currency="NGN",
                    reference=transaction_data.get('reference'),
                    transaction_id=generate_tx_ref(),
                    status='completed',
                    payment_method='wallet'
                )

                Transactions.objects.create(owner=request.user, payment=payment)

                WalletTransactions.objects.create(
                    content=f"You made a Purchase of {product.id} from {product.store.owner}",
                    type='Item-Purchase',
                    wallet=sender_wallet
                )

                try:
                    order = create_order_with_items(cart_items)
                    return Response({"Message Order Placed Successfully"}, status=status.HTTP_200_OK)
                except Exception as e:
                    return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        else:
            provider_name = request.data.get('provider')
            method = PaymentMethodFactory.create_method(payment_method)
            provider = PaymentProviderFactory.create_provider(provider_name)
            data = method.prepare_payment_data(transaction_data)
            response = provider.initialize_payment(data)
            if response.status_code == 200:
                try:
                    order = create_order_with_items(cart_items)
                    return Response({"Message Order Placed Successfully"}, status=status.HTTP_200_OK)
                except Exception as e:
                    return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"Message Error Making Payment for Order"}, status=status.HTTP_400_BAD_REQUEST )


class VerifyTransaction(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider_name = request.data.get('provider_name')
        reference = request.data.get('reference')
        provider = PaymentProviderFactory.create_provider(
            provider_name=provider_name)
        response = provider.verify_payment(reference)
        return Response(response, status=status.HTTP_200_OK)
