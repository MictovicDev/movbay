from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile, RiderProfile
from django.contrib.auth import get_user_model
from .models import Order, OrderTracking

import logging

# Configure logger if not already done
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def update_order_tracking_model(sender, instance, created, **kwargs):
    """
    This model helps to update Order Model Tracking.
    """
    if not created:
        try:
            print(instance)
            print(dir(instance))
            status = instance.status
            print(status)
            order_tracking, _ = OrderTracking.objects.get_or_create(
                order=instance)
            if status == 'processing':
                try:

                    order_tracking.processing = True
                    order_tracking.save()
                except OrderTracking.DoesNotExist:
                    logger.info("Error Tracking Order")
            elif status == 'out_for_delivery':
                print(True)
                order_tracking.out_for_delivery = True
                order_tracking.save()

            elif status == 'completed':
                order_tracking.completed = True
                order_tracking.save()
        except Exception as e:
            # Log error in production (e.g., using logging module)
            print(f"Error creating profile for {instance}: {str(e)}")
