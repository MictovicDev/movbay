from django.contrib import admin
from .views import (
    RegisterView, ActivateAccountView, ProfileView, UserTokenView, GetReferral, RiderProfileAPIView, DeleteAccountView, ChangePasswordView)
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
# from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path('', RegisterView.as_view(), name='register_view'),
    path('login/', UserTokenView.as_view(), name='token_obtain_pair_email'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('delete-account/', DeleteAccountView.as_view()),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('activate/', ActivateAccountView.as_view(), name='activate-account'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('referrals/', GetReferral.as_views(), name='referral'),
    path('riderprofile/', RiderProfileAPIView.as_view(), name='riderprofile')

]
