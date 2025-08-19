from rest_framework import serializers
from .models import  Message, Conversation
from users.serializers import UserSerializer
from stores.serializers import ClientStoreSerializer, ProductSerializer
from stores.models import Store




class ChatStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['name', 'category','store_image_url','description', 'owner', 'address1']



class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.id", read_only=True)
    receiver = serializers.CharField(source="receiver.id", read_only=True)
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['chatbox', 'content', 'sender', 'receiver', 'delivered','product', 'seen', 'is_sender', 'is_receiver','status', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    # receiver = ClientStoreSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = '__all__'
        

   
   

        
        
