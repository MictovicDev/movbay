from django.contrib import admin
from .views import (
    RegisterView,
    UserTokenObtainPairView, ActivateAccountView, ProfileView)
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
# from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path('', RegisterView.as_view(), name='register_view'),
    path('login/', UserTokenObtainPairView.as_view(), name='token_obtain_pair_email'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('activate/', ActivateAccountView.as_view(), name='activate-account'),
    path('profile/', ProfileView.as_view(), name='profile')
   
]

