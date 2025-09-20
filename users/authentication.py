import logging
from django.utils import timezone
import redis
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
import os

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(
    os.getenv('REDIS_URL', 'redis://localhost:6379'))


class LastSeenJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        print('🔍 AUTHENTICATION METHOD CALLED!')
        print(f'🌐 Request path: {request.path}')
        print(f'📝 Request method: {request.method}')
        
        auth_header = request.headers.get("Authorization")
        print(f'🔑 Authorization header: {auth_header[:50] + "..." if auth_header and len(auth_header) > 50 else auth_header}')
        
        logger.debug("LastSeenJWTAuthentication.authenticate called")
        logger.debug("Request path: %s %s", request.method, request.path)
        logger.debug("Authorization header = %s", auth_header)
        
        result = super().authenticate(request)
        print(f'🔍 Super authenticate result: {result}')
        logger.debug("super().authenticate returned = %s", repr(result))
        
        if result is not None:
            user, token = result
            print(f'✅ User authenticated: {user} (ID: {user.pk})')
            logger.info("User authenticated: %s (ID: %s)", user, user.pk)
            
            try:
                # Update Redis immediately
                timestamp = timezone.now().isoformat()
                redis_client.set(
                    f"last_seen:{user.pk}", timestamp, ex=86400)  # 24h TTL
                print(f'📊 Redis updated for user {user.pk} at {timestamp}')
                logger.debug("Updated Redis last_seen for user %s", user.pk)
            except Exception as e:
                print(f'❌ Redis update failed: {e}')
                logger.exception("Failed to update Redis last_seen: %s", e)
            
            return user, token
        else:
            print('❌ Authentication failed or no token provided')
            logger.debug("Authentication failed - no valid token")
            
        return None