from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .serializers import MessageSerializer, ConversationSerializer
from .models import Conversation, Message
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from channels.layers import get_channel_layer
from django.utils import timezone
from asgiref.sync import async_to_sync
from stores.models import Product, Status, Store
from django.contrib.auth import get_user_model
import uuid
import json
from users.utils.check_user_online import get_user_last_seen
from stores.tasks import send_push_notification

User = get_user_model()

class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID objects."""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)

class ProductMessageCreateView(APIView):
    #authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        product_id = data.get("product_id")
        content = data.get("content")
        if not content:
            return Response({"error": "Content is required"}, status=400)

        product = get_object_or_404(Product, id=product_id)
        room_name = f"user_{str(user.id)[:5]}_{str(product.store.id)}"
        
        conversation, _ = Conversation.objects.get_or_create(
            sender=user,
            receiver=product.store,
            room_name=room_name
        )
        room_name = conversation.room_name
        timestamp = timezone.now()

        # Option 1: Save the message first, then serialize
        message = Message.objects.create(
            content=content,
            sender=user,
            receiver=product.store,
            product=product,
            chatbox=conversation,
            created_at=timestamp,
        )
        other_user = product.store.owner
        serializer = MessageSerializer(message)
        
        
        try:
            # 1. Send immediately via WebSocket
            self._send_ws_message_immediate(
                room_name, serializer.data
            )
            
            # 2. Check if recipient is online
            last_seen = get_user_last_seen(other_user.id)
            user_online = False
            if last_seen:
                delta = timezone.now() - last_seen
                user_online = delta.total_seconds() < 200  # 5 min threshold

            if not user_online:
                # 🔔 Send push/email notification
                self._send_offline_notification(other_user, serializer.data)

            # 3. Return serialized message
            return Response(serializer.data, status=201)

            # 2. Since we already saved above, no need for async task
            # But if you want to keep async pattern, pass the saved message ID
            # save_message_to_db.delay(message_id=str(message.id))

            # 3. Return serialized message
            return Response(serializer.data, status=201)

        except Exception as e:
            # If WebSocket fails, delete the saved message to maintain consistency
            message.delete()
            return Response({"error": str(e)}, status=400)

    def _send_ws_message_immediate(self, room_name, message_data):
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                # Ensure UUIDs are converted to strings before sending
                json_safe_data = json.loads(json.dumps(message_data, cls=UUIDEncoder))
                
                async_to_sync(channel_layer.group_send)(
                    room_name,
                    {
                        "type": "chat_message",
                        "message": json_safe_data,
                    },
                )
            except Exception as e:
                print(f"WebSocket error: {str(e)}")
                
    def _send_offline_notification(self, user, message_data):
        """
        Send a notification to a user who is not online.
        You can integrate FCM, OneSignal, or just send an email here.
        """
        print(f"📩 Sending offline notification to {user.email} -> {message_data}")
        message = 'You have a new message regarding your product.'
        send_push_notification.delay(
                                token=user.device.all()[0].token,
                                title="New Message",
                                notification_type="Message Alert",
                                data=message
                            )
                
class StatusMessageCreateView(APIView):
    #authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        status_id = data.get("status_id")
        content = data.get("content")
        if not content:
            return Response({"error": "Content is required"}, status=400)

        store_status = get_object_or_404(Status, id=status_id)
        room_name = f"user_{str(user.id)[:5]}_{str(store_status.store.id)}"
        
        conversation, _ = Conversation.objects.get_or_create(
            sender=user,
            receiver=store_status.store,
            room_name=room_name
        )
        room_name = conversation.room_name
        timestamp = timezone.now()

        # Option 1: Save the message first, then serialize
        message = Message.objects.create(
            content=content,
            sender=user,
            receiver=store_status.store,
            status = store_status,
            chatbox=conversation,
            created_at=timestamp,
        )
        
        serializer = MessageSerializer(message)
        
        
        try:
            # 1. Send immediately via WebSocket
            self._send_ws_message_immediate(
                room_name, serializer.data
            )

            # 2. Since we already saved above, no need for async task
            # But if you want to keep async pattern, pass the saved message ID
            # save_message_to_db.delay(message_id=str(message.id))

            # 3. Return serialized message
            return Response(serializer.data, status=201)

        except Exception as e:
            # If WebSocket fails, delete the saved message to maintain consistency
            message.delete()
            return Response({"error": str(e)}, status=400)

    def _send_ws_message_immediate(self, room_name, message_data):
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                # Ensure UUIDs are converted to strings before sending
                json_safe_data = json.loads(json.dumps(message_data, cls=UUIDEncoder))
                
                async_to_sync(channel_layer.group_send)(
                    room_name,
                    {
                        "type": "chat_message",
                        "message": json_safe_data,
                    },
                )
            except Exception as e:
                print(f"WebSocket error: {str(e)}")



class DirectMessageCreateView(APIView):
    #authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        user = request.user
        data = request.data
        user = User.objects.get(email=user.email)
        
        content = data.get("content")
        if not content:
            return Response({"error": "Content is required"}, status=400)

        timestamp = timezone.now()
        conversation, _ = Conversation.objects.get_or_create(room_name=room_name)
        if conversation.sender == request.user:
            other_user = conversation.receiver
        elif getattr(conversation.receiver, "owner", None) == request.user:
            other_user = conversation.sender
        else:
            other_user = None

        # Save the message first
        message = Message.objects.create(
            content=content,
            sender=user,
            receiver=other_user,
            chatbox=conversation,
            created_at=timestamp,
        )
        
        serializer = MessageSerializer(message)
        
        try:
            # 1. Send immediately via WebSocket
            self._send_ws_message_immediate(room_name, serializer.data)
            # 2. Check if recipient is online
            last_seen = get_user_last_seen(other_user.id)
            user_online = False
            if last_seen:
                delta = timezone.now() - last_seen
                user_online = delta.total_seconds() < 200  # 5 min threshold

            if not user_online:
                # 🔔 Send push/email notification
                print('Yeah')
                self._send_offline_notification(other_user, serializer.data)

            # 3. Return serialized message
            return Response(serializer.data, status=201)

        except Exception as e:
            print(e)
            message.delete()  # Cleanup on failure
            return Response({"error": str(e)}, status=400)

    def _send_ws_message_immediate(self, room_name, message_data):
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                # Ensure UUIDs are converted to strings
                json_safe_data = json.loads(json.dumps(message_data, cls=UUIDEncoder))
                
                async_to_sync(channel_layer.group_send)(
                    room_name,
                    {
                        "type": "chat_message",
                        "message": json_safe_data,
                    },
                )
            except Exception as e:
                print(f"WebSocket error: {str(e)}")
                
    def _send_offline_notification(self, user, message_data):
        """
        Send a notification to a user who is not online.
        You can integrate FCM, OneSignal, or just send an email here.
        """
        if isinstance(user, Store):
            user = user.owner
            print("This is a Store object")
        print(f"📩 Sending offline notification to {user.email} -> {message_data}")
        message = 'You have a new message regarding your product.'
        print(message)
        print(user.device.all()[0].token)
        send_push_notification.delay(
                                token=user.device.all()[0].token,
                                title="New Message",
                                notification_type="Message Alert",
                                data=message
                            )

# Your other views remain the same
class ConversationView(APIView):
    def get(self, request):
        user = request.user
        filters = Q(sender=user)

        if hasattr(user, "store"):  # only add if store exists
            filters |= Q(receiver=user.store)

        conversations = Conversation.objects.filter(filters)
        serializer = ConversationSerializer(
            conversations, many=True, context={'request': request}
        )
        return Response(serializer.data, status=200)
    
    

class ConversationDetailView(APIView):
    """
    Endpoint Used to get all Conversatons in a particular room
    """
    def get(self, request, room_name):
        try:
            conversation = get_object_or_404(Conversation, room_name=room_name)
            serializer = ConversationSerializer(conversation, context={'request': request})
            return Response(serializer.data, status=200)
        except Exception as e:
            return Response(str(e), status=400)