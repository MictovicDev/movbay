from django.urls import path, include
from .views import GenerateQRCodeView, ScanView

urlpatterns = [
    path('generate-qr/', GenerateQRCodeView.as_view(), name='generate-qr'),
    path('', ScanView.as_view(), name='scan'),
]