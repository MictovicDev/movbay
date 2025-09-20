from rest_framework import serializers
from .models import  Message, Conversation
from users.serializers import UserSerializer, UserProfileSerializer
from stores.serializers import ClientStoreSerializer, ProductSerializer, ProductImageSerializer
from stores.models import Store, Product, Status
from django.contrib.auth import get_user_model
import redis, os
from users.utils.check_user_online import is_user_online, get_user_last_seen
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class ChatStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['name', 'category','store_image_url','description', 'store_image', 'owner', 'address1']



class MessageUserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    user_profile = UserProfileSerializer()
    class Meta:
        model = User
        fields = ['id','user_profile']
        
        
class MessageProductSerializer(serializers.ModelSerializer):
    product_images = ProductImageSerializer(many=True)
    class Meta:
        model = Product
        fields = ['id','product_images', 'title', 'description', 'category']
        
        
class MessageStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ['id', 'store', 'image', 'image_url', 'content']
    

class MessageSerializer(serializers.ModelSerializer):
    sender = MessageUserSerializer(read_only=True)
    receiver = serializers.SerializerMethodField()
    product = MessageProductSerializer(read_only=True)
    status = MessageStatusSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['chatbox', 'content', 'sender', 'receiver', 'delivered','product', 'created_at', 'status']
        
    def get_receiver(self, obj):
        if isinstance(obj.receiver, Store):
            return ChatStoreSerializer(obj.receiver).data
        elif isinstance(obj.receiver, User):
            return MessageUserSerializer(obj.receiver).data
        return None


class ConversationSerializer(serializers.ModelSerializer):
    sender = MessageUserSerializer(read_only=True)
    receiver = ChatStoreSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    user_online = serializers.SerializerMethodField()  # New field to check if other user is online
    
    class Meta:
        model = Conversation
        fields = '__all__'
        
    def get_user_online(self, obj):
        request_user = self.context["request"].user

        # Determine the "other" user in the conversation
        if obj.sender == request_user:
            other_user = obj.receiver.owner if hasattr(obj.receiver, "owner") else obj.receiver
        else:
            other_user = obj.sender

        # Debug logging
        logger.info(f"Checking online status for user: {other_user.username}")
        online_status = is_user_online(other_user.id)
        logger.info(f"User {other_user.id} online status: {online_status}")
        
        return online_status
    
    def get_last_seen(self, obj):
        """Optional: Get the actual last_seen timestamp"""
        request_user = self.context["request"].user

        if obj.sender == request_user:
            other_user = obj.receiver.owner if hasattr(obj.receiver, "owner") else obj.receiver
        else:
            other_user = obj.sender

        last_seen = get_user_last_seen(other_user.id)
        return last_seen.isoformat() if last_seen else None

        
        
