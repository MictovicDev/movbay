from django.urls import path
from . import views



urlpatterns = [
    path('fund-wallet/', views.FundWallet.as_view(), name='fund_wallet'),
    path('web-hook/', views.PaystackWebhookView.as_view(), name='webhook'),
    path('verify-payment/', views.VerifyTransaction.as_view(), name='payment-verification'),
    path('test-handler', views.TestHandler.as_view(), name='test'),
    path('purchase-product/<str:pk>/', views.PurchasePaymentView.as_view(), name='purchase_product')
   
    ]