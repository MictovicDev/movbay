from celery import shared_task
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Conversation, Message
import logging
import asyncio
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from stores.models import Product, Status
from django.db.models import Q
User = get_user_model()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@shared_task
def save_message_to_db(user_id, timestamp, content, room_name, product_id=None):
    """Background task to save message to database"""
    try:
        with transaction.atomic():

            user = get_object_or_404(User, id=user_id)

            if not product_id:
                conversation = get_object_or_404(
                    Conversation, room_name=room_name)
                if conversation.sender == user:
                    other_user = conversation.receiver
                elif conversation.receiver == user:
                    other_user = conversation.sender
                else:
                    other_user = None  # user not in this conversation
                message = Message.objects.create(
                    chatbox=conversation,
                    sender=user,
                    receiver=other_user,
                    content=content,
                    created_at=timestamp
                )

            elif product_id:
                product = get_object_or_404(Product, id=product_id)
                conversation = get_object_or_404(
                    Conversation, room_name=room_name)
                if conversation.sender == user:
                    other_user = conversation.receiver
                elif conversation.receiver.owner == user:
                    other_user = conversation.sender
                else:
                    other_user = None  # user not in this conversation

                message = Message.objects.create(
                    chatbox=conversation,
                    sender=user,
                    receiver=other_user,
                    product=product,
                    content=content,
                    created_at=timestamp
                )

            # Notify clients that message is persisted
            update_message_status.delay(message.id, "sent")

    except Exception as e:
        # Handle failure - notify client
        print(str(e))
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
def notify_message_failed():
    """Update message status via WebSocket"""
    channel_layer = get_channel_layer()
    asyncio.run(channel_layer.group_send("message_updates", {
        "type": "message_status_update",
    }))
