from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

from django.db import models

class Device(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    
    def __str__(self):
        return f"{self.user} Token"

    
    
