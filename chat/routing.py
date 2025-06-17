# myapp/routing.py
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<store_id>\d+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/message/$', consumers.MessageConsumer.as_asgi()),
]


