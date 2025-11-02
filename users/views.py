from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, ActivateAccountSerializer
from django.contrib.auth import get_user_model
from .serializers import (
    UserTokenObtainPairSerializer, UserProfileSerializer, RiderSerializer, ReferralSerializer, RateMovbaySerializer
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
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework import permissions
from .models import UserProfile, RiderProfile, LoginAttempt, Referral, Rating
from django.contrib.auth.hashers import check_password
import logging
from .utils.redis_cli import redis_client
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
import logging
from django.shortcuts import get_object_or_404


logger = logging.getLogger(__name__)
User = get_user_model()


class GoogleLoginView(APIView):
    """
    Google Sign-In endpoint for React Native
    Request body: { "token": "google_id_token" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        google_token = request.data.get('token')

        if not google_token:
            return Response(
                {"error": "Google token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify the Google ID token
            idinfo = id_token.verify_oauth2_token(
                google_token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            # Extract user information from Google
            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            google_id = idinfo.get('sub')
            picture = idinfo.get('picture', '')

            if not email:
                return Response(
                    {"error": "Email not provided by Google"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Google login attempt for email: {email}")

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,  # or generate a unique username
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )

            if created:
                logger.info(f"New user created via Google: {email}")
                # Set unusable password for Google users
                user.set_unusable_password()
                user.save()

            # Generate JWT tokens (same as your existing flow)
            refresh = RefreshToken.for_user(user)

            return Response({
                "id": str(user.id),
                "email": user.email,
                "user_type": getattr(user, 'user_type', None),
                "token": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "created": created,  # Indicates if this is a new user
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Invalid Google token: {str(e)}")
            return Response(
                {"error": "Invalid Google token"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Google login error: {str(e)}")
            return Response(
                {"error": "Google authentication failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {"error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
            logger.info(f"User found: {user.email}")

            # Authenticate manually using the serializer
            serializer = TokenObtainPairSerializer(data={
                "email": user.email,  # use "username" unless you've overridden USERNAME_FIELD
                "password": password
            })
            print(user.email)
            if serializer.is_valid():
                return Response({
                    "id": str(user.id),
                    "email": user.email,
                    "user_type": getattr(user, 'user_type', None),
                    "token": serializer.validated_data
                })
            else:
                return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        except User.DoesNotExist:
            logger.warning(f"Login attempt with non-existent email: {email}")
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Login error for {email}: {str(e)}")
            return Response(
                {"error": "Login failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteAccountView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            user.is_active = False
            user.save()
            return Response({"Message": "Account Deleted Successfully"}, status=200)
        except Exception as e:
            return Response({"Message": "Error Deleting Account"}, status=400)


class RegisterView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    queryset = User.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            print('Valid')
            try:
                otp_m = OTPManager()
            
                referral_code = serializer.validated_data.get('referral_code', None)
                print(referral_code)
                secret = otp_m.get_secret()
                otp = otp_m.generate_otp()
                user = serializer.save()
                user.secret = secret
                if referral_code:
                    try:
                        referrer = User.objects.get(referral_code=referral_code)
                        Referral.objects.create(
                        referrer=referrer, referred_user=user)
                    except User.DoesNotExist:
                        logger.info("User with Code Doesn't exist")
                        return Response({"error":"User with Code Doesn't exist" }, status=status.HTTP_400_BAD_REQUEST)
                    
                user.save()
                html_content = render_to_string(
                    'emails/welcome.html', {'user': user, 'otp': otp})
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
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(e)
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivateAccountView(generics.GenericAPIView):
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
                        "user_type": user.user_type,
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


class GetReferral(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            referral = Referral.objects.filter(referrer=request.user)
            serializer = ReferralSerializer(referral, many=True)
            return Response({
                "status": "success",
                "data": serializer.data
            }, status=200)
        except Exception as e:
            return Response({
                "status": "failed",
                "data": str(e)
            }, status=400)


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
            profile = self.get_object()
            print(profile)
            serializer = self.get_serializer(profile)
            print(serializer)
            # redis_client.set(cache_key, json.dumps(serializer.data), ex=3600)
            return Response(serializer.data)
        except Exception as e:
            return Response(str(e))


class RiderProfileAPIView(APIView):

    def get(self, request):
        try:
            rider = RiderProfile.objects.get(user=request.user)
            serializer = RiderSerializer(rider)
            return Response(serializer.data, status=200)
        except RiderProfile.DoesNotExist:
            return Response({"Message": "No Rider Matching Profile"})

    def put(self, request):
        rider = RiderProfile.objects.get(user=request.user)
        if not rider:
            return Response(
                {"detail": "Rider profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            serializer = RiderSerializer(rider, data=request.data)
        except RiderProfile.DoesNotExist:
            serializer = RiderSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(rider=rider)
            return Response(serializer.data)
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPassword(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not user.check_password(old_password):
            return Response({"detail": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response({"detail": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not user.check_password(old_password):
            return Response({"detail": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response({"detail": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)


class RateMovbay(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        serializer = RateMovbaySerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
                "success": "True",
                "data": serializer.data}, status=200
            )

        else:
            return Response({
                "success": "False",
                "error": serializer.errors
            }, status=400)
