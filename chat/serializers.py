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
    user_online = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = '__all__'
        # Or explicitly:
        # fields = ['id', 'sender', 'receiver', 'messages', 'user_online', 'last_seen']

    def _get_other_user(self, obj):
        """Helper: figure out who the 'other user' is in the conversation"""
        request_user = self.context["request"].user
        if obj.sender == request_user:
            return obj.receiver.owner if hasattr(obj.receiver, "owner") else obj.receiver
        return obj.sender

    def _get_online_data(self, obj):
        """
        Helper: fetch online status and last_seen together,
        cache result so we don’t hit Redis twice for the same user.
        """
        if not hasattr(self, "_online_cache"):
            self._online_cache = {}

        other_user = self._get_other_user(obj)
        user_id = other_user.id

        if user_id not in self._online_cache:
            last_seen = get_user_last_seen(user_id)
            online_status = False

            if last_seen:
                # User is online if last_seen is within the last 5 min (300s)
                from django.utils import timezone
                delta = timezone.now() - last_seen
                online_status = delta.total_seconds() < 200

            self._online_cache[user_id] = {
                "online": online_status,
                "last_seen": last_seen,
            }

        return self._online_cache[user_id]

    def get_user_online(self, obj):
        return self._get_online_data(obj)["online"]

    def get_last_seen(self, obj):
        last_seen = self._get_online_data(obj)["last_seen"]
        return last_seen.isoformat() if last_seen else None

        
        
