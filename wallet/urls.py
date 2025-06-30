# scanner/urls.py
from django.urls import path
from . import views 


urlpatterns = [
   path('', views.WalletDetailView.as_view(), name='wallet')
]