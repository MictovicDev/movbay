from rest_framework import serializers
from users.models import RiderProfile
from .models import Ride, DeliveryPreference, BankDetail, KYC
from users.models import RiderProfile
from stores.serializers import OrderSerializer
from .models import Address, Parcel, ShippingRate, Shipment, ShipmentTracking, PackageDelivery, DeliveryImages





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
    order = OrderSerializer(required=False)
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
        
    

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['id', 'user', 'terminal_address_id', 'is_validated', 'created_at', 'updated_at']

class ParcelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcel
        fields = '__all__'
        read_only_fields = ['id', 'user', 'terminal_parcel_id', 'created_at', 'updated_at']

class ShippingRateSerializer(serializers.ModelSerializer):
    pickup_address = AddressSerializer(read_only=True)
    delivery_address = AddressSerializer(read_only=True)
    parcel = ParcelSerializer(read_only=True)
    
    class Meta:
        model = ShippingRate
        fields = '__all__'
        read_only_fields = ['id', 'terminal_rate_id', 'created_at']
        
        

class TotalFareSerializer(serializers.Serializer):
    total_fare = serializers.DecimalField(max_digits=10, decimal_places=2)


class ShipmentTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentTracking
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

class ShipmentSerializer(serializers.ModelSerializer):
    rate = ShippingRateSerializer(read_only=True)
    tracking_events = ShipmentTrackingSerializer(many=True, read_only=True)
    
    class Meta:
        model = Shipment
        fields = '__all__'
        read_only_fields = ['id', 'user', 'terminal_shipment_id', 'tracking_number', 
                           'current_location', 'status', 'created_at', 'updated_at']

class GetRatesSerializer(serializers.Serializer):
    pickup_address_id = serializers.UUIDField()
    delivery_address_id = serializers.UUIDField()
    parcel_id = serializers.UUIDField()
    shipment_purpose = serializers.ChoiceField(
        choices=[('personal', 'Personal'), ('commercial', 'Commercial')],
        default='personal'
    )

class CreateShipmentSerializer(serializers.Serializer):
    rate_id = serializers.UUIDField()
    pickup_date = serializers.DateField()
    pickup_time = serializers.ChoiceField(
        choices=Shipment.PICKUP_TIME_CHOICES,
        default='morning'
    )
    delivery_note = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)
    
    
    




class PackageDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageDelivery
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "delivered_at"]


class GetNearbyRidersSerializer(serializers.Serializer):
    pickup_address = serializers.CharField(max_length=500)
    delivery_address = serializers.CharField(max_length=500)


class NewRiderSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)
    fullname = serializers.CharField(source='user.fullname', required=False) 
    phone_number = serializers.CharField(source='user.phone_number', required=False)  
    #profile_ 
    
    class Meta:
        model = RiderProfile
        fields = ['username', 'fullname', 'phone_number','address', 'latitude', 'longitude', 'online', 'verified']
        
class GetNearbyRidesResponseSerializer(serializers.Serializer):
    riders = NewRiderSerializer(many=True)
    distance_km = serializers.FloatField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    

class GetPriceEstimateSerializer(serializers.Serializer):
    pickup_address = serializers.CharField(max_length=500)
    delivery_address = serializers.CharField(max_length=500)



class PackageImages(serializers.ModelSerializer):
    image_url = serializers.URLField(required=False)
    image = serializers.ImageField(required=False)
    
    
    class Meta:
        model = DeliveryImages
        fields = ['delivery', 'image', 'image_url', 'uploaded_at']

class PackageDeliveryCreateSerializer(serializers.ModelSerializer):
    package_images = PackageImages(many=True, required=False)
    
    class Meta:
        model = PackageDelivery
        exclude = ["id", "created_at", "updated_at", "delivered_at", "rider"]
        # read_only_fields = ["rider", "status"]