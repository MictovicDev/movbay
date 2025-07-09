# myapp/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
   re_path(r'^ws/track-order/(?P<tracking_code>[A-Z0-9]+)/$', consumers.TrackingConsumer.as_asgi()),

]