from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile, RiderProfile
from django.contrib.auth import get_user_model
from wallet.models import Wallet
from logistics.models import KYC, BankDetail, DeliveryPreference
import logging 

# Configure logger if not already done
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a profile for the user based on their user_type when the user is created.
    """
    if created:
        try:
            if instance.user_type == 'Rider':
                rider, _ = RiderProfile.objects.get_or_create(user=instance)
                KYC.objects.create(rider=rider)
                DeliveryPreference.objects.create(rider=rider)
                BankDetail.objects.create(rider=rider)
            elif instance.user_type == 'User':
                UserProfile.objects.get_or_create(user=instance)
        except Exception as e:
            # Log error in production (e.g., using logging module)
            print(f"Error creating profile for {instance.email}: {str(e)}")
            
            
@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Create a wallet for the user when the user is created.
    """
    if created:
        try:
            Wallet.objects.create(owner=instance)
        except Exception as e:
            # Log error in production (e.g., using logging module)
            print(f"Error  wallet for {instance.email}: {str(e)}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    
    """
    Save the associated profile when the user is updated.
    """
    try:
        if instance.user_type == 'User' and hasattr(instance, 'customer_profile'):
            instance.customer_profile.save()
        elif instance.user_type == 'Rider' and hasattr(instance, 'driver_profile'):
            instance.driver_profile.save()
            
    except Exception as e:
        # Log error in production
        print(f"Error saving profile for {instance.email}: {str(e)}")
        
        
