from django.urls import path
from . import views



urlpatterns = [
    path('fund-wallet/', views.FundWallet.as_view(), name='fund_wallet')
    ]