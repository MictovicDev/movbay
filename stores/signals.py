from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile, RiderProfile
from django.contrib.auth import get_user_model
from .models import Order, OrderTracking
from .tasks import update_to_enroute
from notification.models import Notification


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
            status = instance.status
            print(instance)
            print(status)
            order_tracking, _ = OrderTracking.objects.get_or_create(
                order=instance)
            if status == 'processing':
                print('Entered')
                try:
                    order_tracking.order_accepted = True
                    order_tracking.save()
                except Exception as e:
                    logger.info(str(e))
            elif status == 'out_for_delivery':
               order_tracking.item_picked = True
               order_tracking.save()
               update_to_enroute.apply_async((order_tracking.id,), countdown=180)


            elif status == 'completed':
                order_tracking.completed = True
                order_tracking.save()
        except Exception as e:
            # Log error in production (e.g., using logging module)
            print(f"Error creating profile for {instance}: {str(e)}")
