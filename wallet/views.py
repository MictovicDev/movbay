from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Wallet
from .serializers import WalletSerializer
from rest_framework.response import Response
from rest_framework import status
from  payment.factories import PaymentProviderFactory
from payment.utils.fees import calculate_withdrawal_fee

class WalletDetailView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    

    def get(self, request):
        try:
            wallet = Wallet.objects.get(owner=request.user)
            serializer = WalletSerializer(wallet)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
       
        
class Withdrawal(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        sent_amount = response.get('data').get('amount')
        calculated_amount = calculate_withdrawal_fee(sent_amount)
        if request.user.wallet.balance < calculated_amount:
            return Response({"error": "Insufficient balance"}, status=400)
        provider_name = request.data.get('provider_name')
        payload = {
            'account_number' : request.data.get('account_no'),
            'bank_code' : request.data.get('bank_code'),
        }
        provider = PaymentProviderFactory.create_provider(provider_name=provider_name)
        response = provider.verify_account(payload)
        if response.get('status') == True:
            payload['account_name'] = response.get('data').get('account_name')
            payload['type'] = "nuban"
            payload['currency'] = "NGN"
            if request.user.wallet.reference_code:
                data = {
                    "source": "balance",                 
                    "amount": calculated_amount,                  
                    "recipient": request.user.wallet.recipient_code,
                    "reason": "Wallet withdrawal"
                    }
                provider.transfer(data)
            else:
                response = provider.create_transfer_recipient(payload)
                data = {
                    "source": "balance",                 
                    "amount": calculated_amount,                  
                    "recipient": response.get('data').get('recipient_code'),
                    "reason": "Wallet withdrawal"
                    }
                provider.transfer(data)
            if response.status_code == '200':
                 pass
        else:
            return Response({"message" "Invalid_Account Number"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_200_OK)
        
    