from celery import shared_task
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Conversation, Message
import logging
import asyncio
from channels.layers import get_channel_layer

User = get_user_model()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



@shared_task
def save_message_to_db(user_id, store_id, content, timestamp):
    """Background task to save message to database"""
    try:
        with transaction.atomic():
            user = User.objects.get(id=user_id)
            conversation, _ = Conversation.objects.get_or_create(
                sender=user,
                receiver_id=store_id,
                room_name=f"user_{user_id}_{store_id}"
            )
            
            # Save with temp_id for client correlation
            message = Message.objects.create(
                chatbox=conversation,
                sender=user,
                receiver_id=store_id,
                content=content,
                created_at=timestamp
            )
            
            # Notify clients that message is persisted
            update_message_status.delay(message.id, "sent")
            
    except Exception as e:
        # Handle failure - notify client
        notify_message_failed.delay(str(e))
        
        
        
@shared_task 
def update_message_status(real_id, status):
    """Update message status via WebSocket"""
    channel_layer = get_channel_layer()
    asyncio.run(channel_layer.group_send("message_updates", {
        "type": "message_status_update",
        "real_id": real_id,
        "status": status
    }))
    
@shared_task 
def notify_message_failed(real_id, status):
    """Update message status via WebSocket"""
    channel_layer = get_channel_layer()
    asyncio.run(channel_layer.group_send("message_updates", {
        "type": "message_status_update",
        "real_id": real_id,
        "status": status
    }))