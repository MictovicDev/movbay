# myapp/routing.py
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/payment-webhook/$", consumers.PaymentConsumer.as_asgi()),
    
]


