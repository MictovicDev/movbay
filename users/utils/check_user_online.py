import redis
from django.utils import timezone
from datetime import datetime, timedelta
import os

redis_client = redis.Redis.from_url(
    os.getenv('REDIS_URL', 'redis://localhost:6379'))

def is_user_online(user_id, threshold_minutes=5):
    """
    Check if a user is considered online based on their last_seen timestamp
    
    Args:
        user_id: The user's ID
        threshold_minutes: Minutes after which user is considered offline (default: 5)
    
    Returns:
        bool: True if user is online, False otherwise
    """
    try:
        # Get last_seen from Redis
        last_seen_str = redis_client.get(f"last_seen:{user_id}")
        
        if not last_seen_str:
            return False
            
        # Parse the ISO timestamp
        last_seen = datetime.fromisoformat(last_seen_str.decode())
        
        # Make timezone-aware if needed
        if last_seen.tzinfo is None:
            last_seen = timezone.make_aware(last_seen)
            
        # Check if within threshold
        threshold = timezone.now() - timedelta(minutes=threshold_minutes)
        return last_seen > threshold
        
    except Exception as e:
        # Log error but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error checking online status for user {user_id}: {e}")
        return False

def get_user_last_seen(user_id):
    """Get the actual last_seen timestamp for a user"""
    try:
        last_seen_str = redis_client.get(f"last_seen:{user_id}")
        if last_seen_str:
            return datetime.fromisoformat(last_seen_str.decode())
        return None
    except Exception:
        return None