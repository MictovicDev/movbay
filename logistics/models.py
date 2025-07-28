from django.db import models
from django.contrib.auth import get_user_model
from users.models import RiderProfile
from cloudinary.models import CloudinaryField

User = get_user_model()


    
class Ride(models.Model):
    rider = models.ForeignKey(User, on_delete=models.CASCADE)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    duration_minutes = models.IntegerField(null=True)
    fare_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    
    def __str__(self):
        return f"Ride {self.id} - {self.rider.username}"
    
    
    
class DeliveryPreference(models.Model):
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE)
    auto_accept = models.BooleanField(default=False)
    night_mode_availability = models.BooleanField(default=False)
    delivery_notifications = models.BooleanField(default=False)
    
    
    
    def __str__(self):
        return f"{self.rider.user} Delivery Preferences"
    
    
class BankDetail(models.Model):
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE)
    account_name = models.CharField(max_length=250, blank=True, null=True)
    account_number = models.CharField(max_length=250, blank=True, null=True)
    bank_name = models.CharField(max_length=250, blank=True, null=True)
    
    def __str__(self):
        return f"{self.rider.user} Bank details"
    
    


class KYC(models.Model):
    rider = models.ForeignKey(RiderProfile, on_delete=models.CASCADE)
    nin = CloudinaryField('store/pp', blank=True, null=True)
    proof_of_address = CloudinaryField('store/pp', blank=True, null=True)
    drivers_licence = CloudinaryField('store/pp', blank=True, null=True)
    vehicle_type = models.CharField(max_length=250, blank=True, null=True)
    
    
    def __str__(self):
        return f"{self.rider.user} Bank details"
    
    
    
    