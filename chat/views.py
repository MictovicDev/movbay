from django.shortcuts import render
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .serializers import MessageSerializer, ConversationSerializer
from .models import  Conversation
from rest_framework import status
from .utils.chatupdate import ChatUpdateHandler
from rest_framework.views import APIView
from rest_framework.response import Response
from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404
from django.db.models import Q
from asgiref.sync import sync_to_async
from .models import Message
from channels.layers import get_channel_layer
from django.db import transaction
import asyncio
from .tasks import save_message_to_db
from django.utils import timezone
from asgiref.sync import async_to_sync
from stores.models import Product

class ConversationView(APIView):
    def get(self, request):
        # Fetch all conversations where the user is involved
        conversations = Conversation.objects.filter(sender=request.user)

        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data, status=200)

 

class ConversationDetailView(APIView):
    def get(self, request, room_name):
        # Fetch all conversations where the user is involved
        try:
            conversation = get_object_or_404(Conversation, room_name=room_name)
            serializer = ConversationSerializer(conversation)
            return Response(serializer.data, status=200)
        except Exception as e:
            return Response(str(e), status=400)
        


class FastMessageCreateView(APIView):
    
    def post(self, request, product_id):
        data = request.data
        user = request.user
        content = data.get("content")
        product = data.get('product')
        if not content:
            return Response({"error": "Content is required"}, status=400)
        product = get_object_or_404(Product, id=product_id)
        timestamp = timezone.now().isoformat()
        room_name = f"user_{user.id}_{product.store.id}"
        # Create message object for immediate response
        message_data = {
            "content": content,
            "chat_id": room_name,
            "sender": str(user.id),
            "receiver": product.store.id,
            "timestamp": timestamp,
            "status": "sending"  # pending, sent, delivered, read
        }
        
        
        try:
            # 1. Send immediately via WebSocket
            self._send_ws_message_immediate(room_name, message_data)
           
            # 2. Queue for database persistence (async)
            save_message_to_db.delay(user.id, product.id, content, timestamp)
           
            # 3. Return immediate response
            return Response(message_data, status=201)
           
        except Exception as e:
            return Response({"error": str(e)}, status=400)
   
    def _send_ws_message_immediate(self, room_name, message_data):
        print(room_name)
        channel_layer = get_channel_layer()
        if channel_layer:
            # Convert async function to sync
            try:
                async_to_sync(channel_layer.group_send)(room_name, {
                "type": "chat_message",
                "message": message_data
             })
            except Exception as e:
                print(str(e))

