from django.db import models
from django.contrib.auth.models import (AbstractBaseUser, PermissionsMixin)
import uuid
from .manager import UserManager
from django.core.validators import EmailValidator
import secrets
from django.utils import timezone
from datetime import timedelta
from phonenumber_field.modelfields import PhoneNumberField
import uuid
from cloudinary.models import CloudinaryField
import random, string



# def generate_unique_referral_code():
#         characters = string.ascii_uppercase + string.digits
#         while True:
#             code = ''.join(random.choices(characters, k=8))
#             if not User.objects.filter(referral_code=code).exists():
#                 return code

class User(AbstractBaseUser,PermissionsMixin):
    roles = (
        ("User","User"),
        ("Rider","Rider")
    )
    referral_code = models.CharField(max_length=50, unique=True,null=True)
    referred_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals'
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    fullname = models.CharField(max_length=250, blank=True, null=True, db_index=True)
    username = models.CharField(max_length=250, unique=True, db_index=True)
    email = models.EmailField(
        unique=True,
        db_index=True,
        validators=[EmailValidator(message="Enter a valid email address"),]
    )
    is_active = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    phone_number = PhoneNumberField(blank=True, null=True)
    user_type = models.CharField(choices=roles, max_length=5, blank=True, null=True)
    secret = models.CharField(max_length=500, blank=True, null=True)
    
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number', 'username']


    def __str__(self):
        return self.username
    
    def has_perm(self, perm, obj=None):
        return True
    
    
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4()).replace('-', '')[:10]
        super().save(*args, **kwargs)

    
    @property
    def is_staff(self):
        return self.is_admin
    
    
    
    


class PasswordResetToken(models.Model):
    """Store tokens for password reset"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_hex(32)
        
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)
            
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if the token is valid (not expired and not used)"""
        return not self.used and self.expires_at > timezone.now()
    
    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
        ]



class LoginAttempt(models.Model):
    email = models.EmailField()
    success = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)

    def __str__(self):
        return f"Login attempt for {self.email} at {self.timestamp} ({'Success' if self.success else 'Failed'})"

    @classmethod
    def check_failed_attempts(cls, email, time_window_minutes=15, max_attempts=5):
        from django.utils import timezone
        from datetime import timedelta
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        failed_attempts = cls.objects.filter(
            email=email, success=False, timestamp__gte=time_threshold
        ).count()
        return failed_attempts >= max_attempts
    
    

class UserProfile(models.Model):
    profile_picture = CloudinaryField('image', blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile')
    address = models.CharField(max_length=250, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.email} - Customer Profile"
    
    

    
   
  
class RiderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rider_profile')
    license_number = models.CharField(max_length=50, unique=True)
    vehicle_type = models.CharField(max_length=50)
    is_available = models.BooleanField(default=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    duration_minutes = models.IntegerField(null=True)
    fare_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    online = models.BooleanField(default=False)
    

    def __str__(self):
        return f"{self.user.email} - Driver Profile"