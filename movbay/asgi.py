"""
ASGI config for movbay project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.asgi import get_asgi_application
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import stores.routing
import chat.routing
import payment.routing
import logistics.routing
from chat.middleware import JWTAuthMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

django_env = os.getenv('DJANGO_ENV')

print('Me' + django_env)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f"movbay.settings.{django_env}")


application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # Handles standard HTTP requests
    "websocket": JWTAuthMiddleware(
        URLRouter(
            stores.routing.websocket_urlpatterns + chat.routing.websocket_urlpatterns + payment.routing.websocket_urlpatterns + logistics.routing.websocket_urlpatterns
        )
    ),
})
