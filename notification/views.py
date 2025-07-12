from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Device
from .serializers import DeviceSerializer



class RegisterFcmToken(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class  = DeviceSerializer
    
    
    def post(self, request):
        print('called')
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        Device.objects.aupdate_or_create(**data)
        return Response({"message": "Token saved successfully"})
            