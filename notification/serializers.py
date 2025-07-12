from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from .models import Device


class DeviceSerializer(ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Device
        fields = '__all__'