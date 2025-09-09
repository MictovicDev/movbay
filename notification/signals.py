from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from stores.models import Order, OrderTracking, StoreFollow
from notification.models import Notification
from django.core.exceptions import ValidationError



@receiver(pre_save, sender=Order)
def track_order_changes(sender, instance, **kwargs):
    if not instance.pk:
        return  # new order, no previous state
    try:
        old_order = Order.objects.get(pk=instance.pk)
        instance._old_status = old_order.status
        
    except Order.DoesNotExist:
        instance._old_status = instance.status

@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    if created:
        # New order notification for store owner
        Notification.objects.create(
            user=instance.store.owner,
            title="New Order Received",
            message=f"Order {instance.order_id} has been placed.",
            link=f"/orders/{instance.pk}/"
        )
    else:
        # Status update notification for buyer
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != instance.status:
            Notification.objects.create(
                user=instance.buyer,
                title="Order Status Updated",
                message=f"Your order {instance.order_id} changed from {old_status} → {instance.status}.",
                link=f"/orders/{instance.pk}/"
            )
