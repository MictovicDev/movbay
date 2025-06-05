from django.db import models
from stores.models import Order
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()




class Scan(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='scan', blank=True, null=True)
    qr_data = models.CharField(max_length=255, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    manual_code = models.CharField(max_length=10, blank=True, null=True)
    is_valid = models.BooleanField(default=True)
    
    
    def __str__(self):
        return f"{self.data}"