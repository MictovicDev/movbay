from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
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
        
        
        

@csrf_exempt
@require_POST
def paystack_webhook(request):
    # Verify the Paystack signature
    paystack_signature = request.headers.get('x-paystack-signature')
    secret = os.getenv('PAYSTACK_SECRET_KEY').encode()
    body = request.body

    computed_hash = hmac.new(secret, body, hashlib.sha512).hexdigest()
    if computed_hash != paystack_signature:
        return HttpResponse(status=400)

    event = json.loads(body)

    # Example: Payment Success
    if event['event'] == 'charge.success':
        data = event['data']
        # Do something: update user's wallet, confirm order, etc.
        print("Payment received for:", data['reference'])

    return HttpResponse(status=200)
    
        
        