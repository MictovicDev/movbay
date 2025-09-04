# scanner/urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('', views.WalletDetailView.as_view(), name='wallet'),
    path('withdrawal/', views.Withdrawal.as_view(), name='withdrawal'),
    path('approve-withdrawal/<str:pk>/',
         views.ApproveWithdrawal.as_view(), name='approve-withdrawal'),
    path('transactions/', views.TransactionHistory.as_view(),
         name='transaction-history')
]
