from django.db import models
from django.contrib.auth import get_user_model
from users.models import RiderProfile
from cloudinary.models import CloudinaryField
from stores.models import Order,Store

User = get_user_model()


class Ride(models.Model):
    
    courier_options = (
        ('Bike', 'Bike'),
        ('Vehicle', 'Vehicle')
    )
    
    delivery_options = (
        ('Order', 'Order'),
        ('Package', 'Package')
    )
    
    rider = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='user_ride')
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, related_name='ride')
    package_sender = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='package_sender')
    package_delivery = models.ForeignKey('PackageDelivery', on_delete=models.CASCADE, blank=True, null=True)
    duration_minutes = models.IntegerField(null=True)
    fare_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    locked = models.BooleanField(default=False)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    out_for_delivery = models.BooleanField(default=False)
    courier_type = models.CharField(max_length=250, blank=True, null=True)
    completed = models.BooleanField(default=False)
    delivery_type = models.CharField(max_length=250, choices=delivery_options, blank=True, null=True)
    
    
    def __str__(self):
        return f"Ride {self.id} - {self.rider}"
    
    

class DeliveryPreference(models.Model):
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name='delivery_preference')
    auto_accept = models.BooleanField(default=False)
    night_mode_availability = models.BooleanField(default=False)
    delivery_notifications = models.BooleanField(default=False)
    
    
    
    def __str__(self):
        return f"{self.rider.user} Delivery Preferences"
    
    
class BankDetail(models.Model):
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name='bank_details')
    account_name = models.CharField(max_length=250, blank=True, null=True)
    account_number = models.CharField(max_length=250, blank=True, null=True)
    bank_name = models.CharField(max_length=250, blank=True, null=True)
    
    def __str__(self):
        return f"{self.rider.user} Bank details"
    
    


class KYC(models.Model):
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name='kyc_verification')
    nin = CloudinaryField('store/pp', blank=True, null=True)
    nin_url = models.URLField(null=True)
    proof_of_address = CloudinaryField('store/pp', blank=True, null=True)
    poa_url = models.URLField(null=True)
    drivers_licence = CloudinaryField('store/pp', blank=True, null=True)
    drivers_licence_url = models.URLField(null=True)
    vehicle_type = models.CharField(max_length=250, blank=True, null=True)
    plate_number = models.CharField(max_length=250, blank=True, null=True)
    vehicle_color = models.CharField(max_length=250, blank=True, null=True)
    
    
    def __str__(self):
        return f"{self.rider.user} Bank details"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    terminal_address_id = models.CharField(max_length=100, blank=True, null=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, blank=True, null=True, related_name='store_address')
    
   
    
    def __str__(self):
        return f"{self.user}"


class Parcel(models.Model):
    CURRENCY_CHOICES = [
        ('NGN', 'Nigerian Naira'),
        ('USD', 'US Dollar'),
        ('GBP', 'British Pound'),
        ('EUR', 'Euro'),
    ]
    
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parcels')
    terminal_parcel_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Parcel details
    description = models.CharField(max_length=255)
    # weight = models.DecimalField(max_digits=10, decimal_places=2, help_text="Weight in kg")
    # length = models.DecimalField(max_digits=10, decimal_places=2, help_text="Length in cm")
    # width = models.DecimalField(max_digits=10, decimal_places=2, help_text="Width in cm")
    # height = models.DecimalField(max_digits=10, decimal_places=2, help_text="Height in cm")
    # value = models.DecimalField(max_digits=15, decimal_places=2, help_text="Declared value")
    # currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='NGN')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.description} - {self.weight}kg"

class ShippingRate(models.Model):
    terminal_rate_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    #order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True)
    pickup_address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='pickup_rates')
    delivery_address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='delivery_rates')
    parcel = models.ForeignKey(Parcel, on_delete=models.CASCADE, related_name='rates')
    carrier_name = models.CharField(max_length=100)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['total']
    
    def __str__(self):
        return f"{self.carrier_name} - {self.total} {self.currency}"
    

class Shipment(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    PICKUP_TIME_CHOICES = [
        ('morning', 'Morning (8AM - 12PM)'),
        ('afternoon', 'Afternoon (12PM - 5PM)'),
        ('evening', 'Evening (5PM - 8PM)'),
    ]
    
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shipments')
    terminal_shipment_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Related objects
    rate = models.ForeignKey(ShippingRate, on_delete=models.CASCADE)
    
    # Shipment details
    pickup_date = models.DateField()
    pickup_time = models.CharField(max_length=20, choices=PICKUP_TIME_CHOICES, default='morning')
    delivery_note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Tracking information
    tracking_number = models.CharField(max_length=100, blank=True)
    current_location = models.CharField(max_length=255, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Shipment {self.terminal_shipment_id or self.id} - {self.status}"

class ShipmentTracking(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='tracking_events')
    status = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.shipment.terminal_shipment_id} - {self.status}"
    



class DeliveryImages(models.Model):
    delivery = models.ForeignKey('PackageDelivery', on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('delivery_images/', blank=True, null=True)
    image_url = models.URLField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for Delivery {self.delivery.id}"    


class PackageDelivery(models.Model):
    
    TYPE = (
        ('Document', 'Document'),
        ('Parcel', 'Parcel'),
        ('Envelope', 'Envelope'),
        ('Food', 'Food'),
        ('Fragile', 'Fragile'),
        ('Electronics', 'Electronics'),
        ('Box', 'Box'),
        ('Crate', 'Crate'),
        ('Pallet', 'Pallet'),
        ('Other', 'Other')
        )
    
    RIDE_CHOICES = (
        ('Bike', 'Bike'),
        ('Vehicle', 'Vehicle'),
        )
    
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name='rider', blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='package_delivery', blank=True, null=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    recipient_name = models.CharField(max_length=255)
    pick_address = models.CharField(max_length=500, blank=True, null=True)
    drop_address = models.CharField(max_length=500, blank=True, null=True)
    alternative_drop_address = models.CharField(max_length=500, blank=True, null=True)
    alternative_receipient_name = models.CharField(max_length=255, blank=True, null=True)
    alternative_number = models.CharField(max_length=20, blank=True, null=True)
    #recipient_signature = CloudinaryField('signatures/', blank=True, null=True)
    package_type = models.CharField(max_length=250,  choices=TYPE, blank=True, null=True)
    package_description = models.CharField(max_length=500, blank=True, null=True)
    additional_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    amount = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    rider_preference = models.CharField(max_length=250, choices=RIDE_CHOICES, blank=True, null=True)
    
    def __str__(self):
        return f"Delivery for {self.owner.username} to {self.recipient_name}"
    
    