# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
import asyncio
import redis
from django.utils import timezone
import logging
from uuid import UUID
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID objects."""
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)
    
# class UUIDEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, uuid.UUID):
#             return str(obj)   # convert UUID -> str
#         return super().default(obj)

class MessageConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_client = None  # Initialize in connect()
        self.debounce_delay = 2
        self.user = None
        self.user_group_name = None
        self.room_name = None
        self.debounce_tasks = {}  # Track running tasks

    async def connect(self):
        """Handle WebSocket connection."""
        try:
            self.user = self.scope.get("user")
            self.room_name = self.scope["url_route"]["kwargs"]["room_name"]

            # Check authentication
            if not self.user or self.user.is_anonymous:
                await self.close(code=4001)  # Unauthorized
                return

            # Initialize Redis connection
            self.redis_client = redis.Redis.from_url(
                "redis://localhost:6379/0", 
                decode_responses=True  # Automatically decode responses
            )

            self.user_group_name = self.room_name

            # Join room group
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )

            await self.accept()

            # Send connection confirmation
            await self.send_json({
                'type': 'connection_established',
                'message': 'Connected successfully',
                'room_name': self.room_name,
                'user_id': self.user.id  # Now handled by UUIDEncoder
            })

            # Fetch and send initial conversations/messages
            try:
                conversations_data = await self.get_user_conversation()
                await self.send_json({
                    'type': 'initial_data',
                    'messages': conversations_data
                })
            except Exception as e:
                logger.error(f"Error fetching initial data: {e}")
                await self.send_json({
                    'type': 'error',
                    'message': 'Failed to load initial data'
                })

        except Exception as e:
            logger.error(f"Connection error: {e}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'user_group_name') and self.user_group_name:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        
        # Cancel any pending debounce tasks
        for task in self.debounce_tasks.values():
            if not task.done():
                task.cancel()
        
        # Close Redis connection if it exists
        if self.redis_client:
            await self.redis_client.aclose() if hasattr(self.redis_client, 'aclose') else None

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            print(message_type)
            if message_type == 'chat_message':
                print(True)
                # Handle incoming chat messages
                await self.handle_chat_message(data)
            elif message_type == 'ping':
                # Handle ping/pong for connection health
                await self.send_json({'type': 'pong'})
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_json({
                'type': 'error',
                'message': 'Invalid JSON format'
            })
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_json({
                'type': 'error',
                'message': 'Message processing failed'
            })

    async def handle_chat_message(self, data):
        """Handle chat message processing."""
        # Implement your chat message logic here
        chat_id = data.get('chat_id')
        message_content = data.get('message')
        
        if not chat_id or not message_content:
            await self.send_json({
                'type': 'error',
                'message': 'Missing chat_id or message content'
            })
            return
        
        # Process the message (save to database, etc.)
        # Then trigger debounced update
        message_data = {
            'content': message_content,
            'user_id': self.user.id,  # UUIDEncoder will handle this
            'timestamp': timezone.now().isoformat()
        }
        
        await self.send_chat_update(chat_id, message_data)

    @database_sync_to_async
    def get_user_conversation(self):
        """Fetch all conversations and messages for the user."""
        try:
            from chat.models import Conversation, Message
            from .serializers import MessageSerializer
            print(self.room_name)
            conversation = get_object_or_404(Conversation, room_name=self.room_name)
            print(conversation)
            messages = Message.objects.filter(
                chatbox=conversation
            ).select_related('sender', 'receiver', 'chatbox').order_by("created_at")

            # No request context needed for this serializer

            return MessageSerializer(messages, many=True).data
            
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return []

    async def chat_message(self, event):
        print('called')
        await self.send_json(event["message"])

    async def send_json(self, data):
        """Send JSON data with UUID handling."""
        await self.send(text_data=json.dumps(data, cls=UUIDEncoder))
    