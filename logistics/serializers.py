from rest_framework import serializers
from users.models import RiderProfile
from .models import Ride, DeliveryPreference, BankDetail, KYC
from users.models import RiderProfile






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
        
        
from rest_framework import serializers


class DeliveryPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPreference
        fields = '__all__'
        read_only_fields = ('rider',)

class BankDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetail
        fields = '__all__'
        read_only_fields = ('rider',)

class KYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYC
        fields = '__all__'
        read_only_fields = ('rider', 'nin', 'proof_of_address', 'drivers_licence')
        extra_kwargs = {
            'nin_file': {'write_only': True},
            'proof_of_address_file': {'write_only': True},
            'drivers_licence_file': {'write_only': True},
        }
        
        

class RiderSerializer(serializers.ModelSerializer):
    kyc_verification = KYCSerializer()
    delivery_preference = DeliveryPreferenceSerializer()
    bank_details = BankDetailSerializer()
    
    class Meta:
        model = RiderProfile
        fields = '__all__'