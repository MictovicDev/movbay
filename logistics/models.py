from django.db import models
from django.contrib.auth import get_user_model
# Create your models here.


User = get_user_model()

class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    
    
class Ride(models.Model):
    rider = models.ForeignKey(User, on_delete=models.CASCADE)
    pickup_lat = models.DecimalField(max_digits=10, decimal_places=8)
    pickup_lng = models.DecimalField(max_digits=11, decimal_places=8)
    dropoff_lat = models.DecimalField(max_digits=10, decimal_places=8)
    dropoff_lng = models.DecimalField(max_digits=11, decimal_places=8)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    duration_minutes = models.IntegerField(null=True)
    fare_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Ride {self.id} - {self.rider.username}"
    