from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from .models import Device, Notification


class DeviceSerializer(ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Device
        fields = '__all__'
        
        
class NotificationSerializer(ModelSerializer):
    
    class Meta:
        model = Notification
        fields = '__all__'