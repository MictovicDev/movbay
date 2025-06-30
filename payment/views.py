from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from  payment.factories import PaymentProviderFactory, PaymentMethodFactory
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
from .models import Payment
from django.contrib.auth import get_user_model
from wallet.models import Wallet
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
        amount = payment_data.get('amount', 0) / 100  # Convert from kobo to naira
        email = payment_data.get('customer', {}).get('email')
        user_id = payment_data.get('metadata', {}).get('user_id')
        payment_type = payment_data.get('metadata', {}).get('payment_type')
        
        user = User.objects.get(email=email)
        Payment.objects.create(user=user, provider='paystack', amount=amount, transacton_id=reference, status='success', payment_type=payment_type)
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
            "receveid" : "Received Succefully"
        }
        try:
            async_to_sync(channel_layer.group_send)(
                "payment_notifications",
                {
                    'type': 'payment_notifications',
                    'data': message
                }
            )
            return Response({"message":"sent"})
        except Exception as e:
            return Response(str(e))
       
            
            
def generate_tx_ref(prefix="TX"):
    timestamp = int(time.time())  # seconds since epoch
    rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{timestamp}-{rand_str}"


class FundWallet(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        provider_name = request.data.get('provider_name')
        print(provider_name)
        print(request.data.get('amount'))
        transaction_data = {
            "email": request.user.email,
            "amount": request.data.get('amount'),
            "reference_id": generate_tx_ref(),
            "plan": 'Fund Wallet',
            "metadata": {
                "user_id": str(request.user.id),
                "payment_type": request.data.get('payment_type')}
        }
        provider = PaymentProviderFactory.create_provider(provider_name=provider_name)
        result = provider.initialize_payment(transaction_data)
        return Response(result, status=status.HTTP_200_OK)
        
        


class VerifyTransaction(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    
    def post(self, request):
        provider_name = request.data.get('provider_name')
        reference = request.data.get('reference')
        provider = PaymentProviderFactory.create_provider(provider_name=provider_name)
        response = provider.verify_payment(reference)
        return Response(response, status=status.HTTP_200_OK)
        
        