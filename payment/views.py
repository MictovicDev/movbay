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
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View
import requests
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

class PaystackWebhookView(View):
    @method_decorator(csrf_exempt)
    @method_decorator(require_http_methods(["POST"]))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        # Get the raw body for signature verification
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
                self.handle_successful_payment(data)
            elif event == 'charge.failed':
                self.handle_failed_payment(data)
            elif event == 'transfer.success':
                self.handle_successful_transfer(data)
            # Add more event handlers as needed
            
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

        
        # Create hash
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
        
        logger.info(f"Processing successful payment: {reference}")
        
        # Update your database
        self.update_payment_status(reference, 'success', payment_data)
        
        # Send notification to React Native frontend
        self.notify_frontend({
            'type': 'payment_success',
            'reference': reference,
            'amount': amount,
            'email': email,
            'user_id': user_id,
            'timestamp': payment_data.get('paid_at')
        })
    
    def handle_failed_payment(self, data):
        """Handle failed payment"""
        payment_data = data.get('data', {})
        reference = payment_data.get('reference')
        
        logger.info(f"Processing failed payment: {reference}")
        
        # Update your database
        self.update_payment_status(reference, 'failed', payment_data)
        
        # Send notification to React Native frontend
        self.notify_frontend({
            'type': 'payment_failed',
            'reference': reference,
            'user_id': payment_data.get('metadata', {}).get('user_id'),
            'timestamp': payment_data.get('paid_at')
        })
    
    def handle_successful_transfer(self, data):
        """Handle successful transfer"""
        transfer_data = data.get('data', {})
        reference = transfer_data.get('reference')
        
        logger.info(f"Processing successful transfer: {reference}")
        
        # Send notification to React Native frontend
        self.notify_frontend({
            'type': 'transfer_success',
            'reference': reference,
            'amount': transfer_data.get('amount', 0) / 100,
            'timestamp': transfer_data.get('createdAt')
        })
    
    def update_payment_status(self, reference, status, data):
        """Update payment status in database"""
        print(data)
        # Implement your database update logic here
        # Example:
        # Payment.objects.filter(reference=reference).update(
        #     status=status,
        #     paystack_data=data,
        #     updated_at=timezone.now()
        # )
        pass
    
    def notify_frontend(self, notification_data):
        """Send notification to React Native frontend via WebSocket"""
        channel_layer = get_channel_layer()
        
        # Also send to general payment notifications group
        async_to_sync(channel_layer.group_send)(
            "payment_notifications",
            {
                'type': 'payment_notification',
                'message': notification_data
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
                    'message': message
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
                "user_id": str(request.user.id)}
        }
        provider = PaymentProviderFactory.create_provider(provider_name=provider_name)
        result = provider.initialize_payment(transaction_data)
        return Response(result, status=status.HTTP_200_OK)
        
        
