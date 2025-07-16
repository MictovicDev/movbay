from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Device
from .serializers import DeviceSerializer
from django.shortcuts import get_object_or_404


class RegisterFcmToken(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceSerializer

    def post(self, request):
        print('called')
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        token = data.get("token")
        try:
            device = Device.objects.get(user=user)
            if device.token == token:
                return Response({"message": "Token Retrieved",
                                 "token": device.token
                                 }, status=200)
            else:
                device.token = token
                device.save()
                return Response({"message": "Token Updated successfully",
                                 "token": device.token
                                 }, status=200)
        except Device.DoesNotExist:
            device = Device.objects.create(user=user, token=token)
            return Response({"message": "Token created successfully",
                             "token": device.token
                             }, status=200)
