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
        
        
    
        
        