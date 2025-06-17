import jwt
from urllib.parse import parse_qs
from django.conf import settings
from channels.db import database_sync_to_async



@database_sync_to_async
def get_user(user_id):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser
    User = get_user_model()
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    Custom middleware for authenticating WebSocket connections via JWT.
    Usage:
        application = ProtocolTypeRouter({
            "websocket": JWTAuthMiddleware(URLRouter(...))
        })
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Parse query string for token
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        from django.contrib.auth.models import AnonymousUser
        # Default to anonymous user
        scope["user"] = AnonymousUser()
        
        if token:
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user = await get_user(payload.get("user_id"))
                scope["user"] = user
            except jwt.PyJWTError:
                pass  # token invalid, keep anonymous user
        
        # Call the inner application
        return await self.inner(scope, receive, send)