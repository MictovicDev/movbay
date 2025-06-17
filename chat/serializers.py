from rest_framework import serializers
from .models import ChatBox, Message





class ChatBoxSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ChatBox
        fields = '__all__'
        
        
class MessageSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Message
        fields = '__all__'