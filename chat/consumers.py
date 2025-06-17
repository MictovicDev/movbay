# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
import asyncio
import redis
from django.conf import settings
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        self.debounce_delay = 2
        self.user = None
        self.user_group_name = None

    async def connect(self):
        """Handle WebSocket connection"""
        # Get user from URL or token
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            # Reject anonymous users
            await self.close()
            return
        
        # Create user-specific group name
        self.user_group_name = f"user_{self.user.id}"
        
        # Join user group for personal notifications
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        
        # Optional: Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected successfully'
        }))

    async def send_chat_update(self, chat_id, message_data):
        # Set a key that expires after debounce_delay
        debounce_key = f"chat_update_debounce:{chat_id}"
        
        # Store the latest update data
        update_key = f"chat_update_data:{chat_id}"
        self.redis_client.setex(update_key, self.debounce_delay + 1, 
                               json.dumps(message_data))
        
        # If debounce key doesn't exist, this is first update in the window
        if not self.redis_client.exists(debounce_key):
            self.redis_client.setex(debounce_key, self.debounce_delay, "1")
            
            # Schedule the actual update after delay
            asyncio.create_task(self._delayed_chat_update(chat_id))
    
    async def _delayed_chat_update(self, chat_id):
        await asyncio.sleep(self.debounce_delay)
        
        # Get the latest update data
        update_key = f"chat_update_data:{chat_id}"
        data = self.redis_client.get(update_key)
        
        if data:
            message_data = json.loads(data)
            # Send to all users in the chat
            await self.channel_layer.group_send(
                f"user_{self.user_id}",
                {
                    'type': 'chat_list_update',
                    'chat_id': chat_id,
                    'last_message': message_data,
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            # Clean up
            self.redis_client.delete(update_key)


class MessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.store_id = self.scope['url_route']['kwargs']['store_id']
        self.group_name = f"Chat{self}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def status_created(self, event):
        await self.send(text_data=json.dumps({
            "type": "status.created",
            "data": event["status"]
        }))