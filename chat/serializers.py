from rest_framework import serializers
from .models import  Message, Conversation
from users.serializers import UserSerializer, UserProfileSerializer
from stores.serializers import ClientStoreSerializer, ProductSerializer, ProductImageSerializer
from stores.models import Store, Product, Status
from django.contrib.auth import get_user_model


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
    
    class Meta:
        model = Conversation
        fields = '__all__'

        
        
