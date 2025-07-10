from django.db import models
from django.contrib.auth import get_user_model
# Create your models here.


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
    