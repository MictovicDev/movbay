from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from .factories import provider_factory

# Create your views here.




class InitializePayment(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    

    def post(self, request):
        payment_type = request.data.get('payment_method')
        payment_method = provider_factory.create_method(payment_type)
        
        