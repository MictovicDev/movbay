from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, ActivateAccountSerializer
from django.contrib.auth import get_user_model
from .serializers import (
    UserTokenObtainPairSerializer, UserProfileSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView
from users.utils.otp import OTPManager
from users.utils.email import EmailManager
from celery import shared_task
from rest_framework.throttling import AnonRateThrottle
from django.template.loader import render_to_string
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .tasks import send_welcome_email_async
from .models import LoginAttempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework import permissions
from .models import UserProfile
from .utils.redis_cli import redis_client
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class CustomAnonRateThrottle(AnonRateThrottle):
    rate = '5/minute'  # Limit to 5 requests per minute

    
class UserTokenObtainPairView(TokenObtainPairView):
    serializer_class = UserTokenObtainPairSerializer
    throttle_classes = [CustomAnonRateThrottle]


    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        ip_address = request.META.get('REMOTE_ADDR')

        try:
            # 1. Try to fetch user from Redis cache
            user_data = redis_client.hgetall(f"user:{email}")
            print(user_data)
            if user_data:
                # 2. Verify password hash from cache
                if check_password(password, user_data['password']):
                    user = User.objects.get(email=email)

                    # 3. Generate token
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        "id": str(user.id),
                        "username": user.username,
                        "token": {
                            "access": str(refresh.access_token),
                            "refresh": str(refresh),
                        },
                    })

            # 4. Fallback: fetch from DB
            user = User.objects.get(email=email)

            if user and user.check_password(password):
                # 5. Cache user data for future (avoid sensitive info)
                redis_client.hset(f"user:{email}", mapping={
                    "password": user.password,  # hashed password
                    "id": str(user.id),
                    "email": user.email,
                })
                redis_client.expire(f"user:{email}", 3600)  # 1 hour

                # 6. Generate token
                refresh = RefreshToken.for_user(user)
                return Response({
                        "id": str(user.id),
                        "username": user.username,
                        "token": {
                            "access": str(refresh.access_token),
                            "refresh": str(refresh),
                        },
                })

            raise Exception("Invalid credentials")

        except Exception as e:
            # Log failed attempt
            LoginAttempt.objects.create(email=email, success=False, ip_address=ip_address)
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

class RegisterView(generics.ListCreateAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    queryset = User.objects.all()
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                otp_m = OTPManager()
                secret = otp_m.get_secret()
                otp = otp_m.generate_otp()
                user = serializer.save()
                user.secret = secret
                user.save()
                html_content = render_to_string('emails/welcome.html', {'user': user, 'otp': otp})
                send_welcome_email_async.delay(from_email='noreply@movbay.com',
                                            to_emails=user.email,
                                            subject='Welcome TO MovBay',
                                            html_content=html_content)
                token = UserTokenObtainPairSerializer().get_token(user)
                
                return Response({
                    "message": "Registration successful",
                    "user": {
                        "username": user.username,
                        "email": user.email,
                        "phone_number": str(user.phone_number),
                        "user_type": user.user_type
                    },
                    'token': {
                    'access': str(token.access_token),
                    'refresh': str(token),
                }        
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(e)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    
    
    
    
class ActivateAccountView(generics.GenericAPIView):
    throttle_classes = [CustomAnonRateThrottle]
    permission_classes = [AllowAny]
    serializer_class = ActivateAccountSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # will raise 400 if invalid

        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp']

        try:
            user = User.objects.get(email=email)
            user_secret = user.secret
            token = UserTokenObtainPairSerializer().get_token(user)
            if not user.is_active:
                if OTPManager(user_secret).verify_otp(otp_code):
                    user.is_active = True
                    user.save()
                    return Response({
                        'user': user.email,
                        'token':  {
                            'access': str(token.access_token),
                            'refresh': str(token),
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({'message': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                    return Response({'message': 'Already Verified, Login'}, status=status.HTTP_400_BAD_REQUEST)

        except User.DoesNotExist:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class ProfileView(generics.RetrieveUpdateAPIView):
    queryset = UserProfile.objects.select_related('user') 
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.queryset.get(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        import json
        try:
            cache_key = f"user_profile:{request.user.id}"
            cached_profile = redis_client.get(cache_key)
            # redis_client.delete(cache_key)
            if cached_profile:
                return Response(json.loads(cached_profile))
            
            ## if not in cache
            profile = self.get_object()
            serializer = self.get_serializer(profile)
            redis_client.set(cache_key, json.dumps(serializer.data), ex=3600)
            return Response(serializer.data)
        except Exception as e:
            print(e)
            
        
        
        
        