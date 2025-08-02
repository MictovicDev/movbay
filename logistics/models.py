from django.db import models
from django.contrib.auth import get_user_model
from users.models import RiderProfile
from cloudinary.models import CloudinaryField
from stores.models import Order

User = get_user_model()


    
class Ride(models.Model):
    
    courier_options = (
        ('Bike', 'Bike'),
        ('Vehicle', 'Vehicle')
    )
    rider = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, related_name='ride')
    duration_minutes = models.IntegerField(null=True)
    fare_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    locked = models.BooleanField(default=False)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    out_for_delivery = models.BooleanField(default=False)
    courier_type = models.CharField(max_length=250, blank=True, null=True)
    
    
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
    
    
    
    
    
    
    
    