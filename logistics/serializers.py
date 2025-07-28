from rest_framework import serializers
from users.models import RiderProfile
from .models import Ride


class GoOnline_OfflineSerializer(serializers.ModelSerializer):
    online = serializers.BooleanField(required=True)
    class Meta:
        model = RiderProfile
        fields = ['online']
        
        
    

class UpdateLatLongSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)

    class Meta:
        model = RiderProfile
        fields = ['latitude', 'longitude']
        
        
class RideSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Ride
        fields = '__all__'