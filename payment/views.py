from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from payment.factories import PaymentProviderFactory, PaymentMethodFactory
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
import os
import hmac
import hashlib
import json
import logging
from django.http import HttpResponse
from rest_framework.decorators import api_view
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Payment
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
from .utils.helper import generate_tx_ref
from stores.serializers import ShopSerializer


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
        payment_type = data.get('data').get('metadata', {}).get('payment_type')
        payment_type == 'purchase-item'
        payment_data = data.get('data', {})
        reference = payment_data.get('reference')
        amount = payment_data.get('amount', 0) / 100
        email = payment_data.get('customer', {}).get('email')
        user_id = payment_data.get('metadata', {}).get('user_id')
        payment_type = payment_data.get('metadata', {}).get('payment_type')
        cart_items = payment_data.get('metadata', {}).get('cart_items')
        user = User.objects.get(email=email)
        data = calculate_wallet_fee(amount)
        amount = data.get('wallet_credit')
        if payment_type == 'fund-wallet':
            with transaction.atomic():
                Payment.objects.create(
                    user=user,
                    provider='paystack',
                    amount=amount,
                    transaction_id=reference,
                    status='success',
                    payment_method=payment_type
                )
                wallet = Wallet.objects.get(owner=user)
                wallet.balance += int(amount)
                wallet.total_deposit += int(amount)
                wallet.save()
                WalletTransactions.objects.create(content='Account Funded Succesfully', type='Account-Funded', wallet=wallet, amount=amount)
        elif payment_type == 'purchase-item':
            print(True)
            try:
                response = create_order_with_items(user=user,
                                                order_data=cart_items, reference=reference, method='paystack')
                print(response)
                return Response({"Message Order Placed Successfully"}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"Message Error Making Payment for Order"}, status=status.HTTP_400_BAD_REQUEST)

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


class FundWallet(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
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
        except Exception as e:
            return Response({"Messsage": f"Error Funding Wallet {e}"}, status=400)
            
        


class PurchasePaymentView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            order_data = request.data
            serializer = ShopSerializer(data=order_data)
            if serializer.is_valid():
                validated_data = serializer.validated_data
                transaction_data = {
                    "email": request.user.email,
                    "amount": int(Decimal(validated_data['total_amount'])) * 100,
                    "reference": generate_tx_ref(),
                    "currency": "NGN",
                    "metadata": {
                        "user_id": str(request.user),
                        "payment_type": 'purchase-item',
                        "cart_items": validated_data,
                    }, }
                print(transaction_data.get('amount'))
                payment_method = validated_data.get('payment_method')
                delivery_method = validated_data.get('delivery_method')
                
                print(payment_method)
                if payment_method == 'wallet':
                    try:
                        response = create_order_with_items(user=request.user,
                                                        order_data=validated_data, reference=transaction_data.get('reference'), method='wallet')
                        # print(response.data)
                        if response.status_code == 201:
                            return Response(response.data, status=status.HTTP_200_OK)
                        # else:
                        #     return Response({"Message": "Order not Created"}, status=status.HTTP_400_BAD_REQUEST)
                    except Exception as e:
                        print(str(e))
                        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

                else:
                    print(validated_data)
                    provider_name = validated_data['provider_name']
                    payment_method = validated_data['payment_method']
                    provider = PaymentProviderFactory.create_provider(
                        provider_name=provider_name)
                    print(provider)
                    method = PaymentMethodFactory.create_method(
                        method_name=payment_method)
                    print(method)
                    transaction_data = method.prepare_payment_data(
                        transaction_data)
                    response = provider.initialize_payment(transaction_data)
                    print(response)
                    return Response(response, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=400)
        except Exception as e:
            logger.info('Error Purchasing Items')
            return Response({"Messsage": f"Error Processing Purchase{e}"}, status=400)
            
          
            
     



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
