from django.urls import path
from . import views



urlpatterns = [
    path('payment', views.InitializePayment.as_view(), name='initialize_payment')
    
    ]