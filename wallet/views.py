from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Wallet
from .serializers import WalletSerializer
from rest_framework.response import Response
from rest_framework import status


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
            
       
        
        
    