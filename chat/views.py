from django.shortcuts import render
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .serializers import MessageSerializer, ConversationSerializer
from .models import Conversation
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
from stores.models import Product, Status, Store
from rest_framework.permissions import IsAuthenticated


class ConversationView(APIView):
    def get(self, request):
        # Fetch all conversations where the user is involved
        conversations = Conversation.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user)
        )

        serializer = ConversationSerializer(
            conversations, many=True, context={'request': request})
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


class ProductMessageCreateView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        product_id = data.get("product_id")
        content = data.get("content")
        if not content:
            return Response({"error": "Content is required"}, status=400)

        product = get_object_or_404(Product, id=product_id)
        room_name = f"user_{str(user.id)[:5]}_{str(product.store.owner.id)[:5]}"
        
        conversation = Conversation.objects.filter(
            Q(sender=user, receiver=product.store.owner) |
            Q(sender=product.store.owner, receiver=user)
        ).first()
        
        if not conversation:
            conversation = Conversation.objects.create(
                sender=user,
                receiver=product.store.owner,
                room_name=room_name
            )
        room_name = conversation.room_name
        print(room_name)
        timestamp = timezone.now()
        # Create an unsaved Message instance
        message = Message(
            content=content,
            sender=user,
            receiver=product.store.owner,
            product=product,
            chatbox=conversation,
            created_at=timestamp,
        )
        
        # Serialize the instance
        serializer = MessageSerializer(message)
        try:
            # 1. Send immediately via WebSocket
            self._send_ws_message_immediate(
                room_name, serializer.data
            )

            # 2. Persist asynchronously in DB
            save_message_to_db.delay(
                user_id=str(user.id), timestamp=timestamp.isoformat(), content=content, room_name=room_name, product_id=product.id
            )

            # 3. Return serialized message immediately
            return Response(serializer.data, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

    def _send_ws_message_immediate(self, room_name, message_data):
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                async_to_sync(channel_layer.group_send)(
                    room_name,
                    {
                        "type": "chat_message",
                        "message": message_data,
                    },
                )
            except Exception as e:
                print(str(e))


class DirectMessageCreateView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        user = request.user
        data = request.data
        
        content = data.get("content")
        if not content:
            return Response({"error": "Content is required"}, status=400)

        timestamp = timezone.now()

        conversation, _ = Conversation.objects.get_or_create(
            room_name=room_name
        )
        if conversation.sender == request.user:
            other_user = conversation.receiver
        elif conversation.receiver == request.user:
            other_user = conversation.sender
        else:
            other_user = None  # user not in this conversation
        # Create an unsaved Message instance
        message = Message(
            content=content,
            sender=user,
            receiver=other_user,
            chatbox=conversation,
            created_at=timestamp,
        )
        print(room_name)
        # Serialize the instance
        serializer = MessageSerializer(message)
        try:
            # 1. Send immediately via WebSocket
            self._send_ws_message_immediate(
                room_name, serializer.data
            )

            # 2. Persist asynchronously in DB
            save_message_to_db.delay(
                user_id=str(user.id), timestamp=timestamp.isoformat(), content=content, room_name=room_name
            )

            # 3. Return serialized message immediately
            return Response(serializer.data, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

    def _send_ws_message_immediate(self, room_name, message_data):
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                async_to_sync(channel_layer.group_send)(
                    room_name,
                    {
                        "type": "chat_message",
                        "message": message_data,
                    },
                )
            except Exception as e:
                print(str(e))
