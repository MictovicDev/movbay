from rest_framework import serializers
from .models import  Message, Conversation
from users.serializers import UserSerializer
from stores.serializers import ClientStoreSerializer
from stores.models import Store







class ConversationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = ClientStoreSerializer(read_only=True)
    class Meta:
        model = Conversation
        fields = '__all__'
        


# class ChatBoxSerializer(serializers.ModelSerializer):
    
#     class Meta:
#         model = ChatBox
#         fields = '__all__'
   
   
class ChatStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['name', 'category','store_image_url','description', 'owner', 'address1']
        
        
class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = ChatStoreSerializer(read_only=True)
    class Meta:
        model = Message
        fields = '__all__'