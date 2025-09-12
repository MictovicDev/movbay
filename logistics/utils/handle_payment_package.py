from wallet.models import Wallet
from payment.models import Payment
from decimal import Decimal
from rest_framework.exceptions import ValidationError, NotFound
from users.models import RiderProfile
from payment.utils.helper import generate_tx_ref
from stores.utils.get_store_cordinate import get_coordinates_from_address
from logistics.utils.eta import get_eta_distance_and_fare
from django.db import transaction
from base64 import b64encode
from ..tasks import upload_delivery_images
import logging
from logistics.models import Ride
from stores.tasks import send_push_notification

import os


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def notify_driver(driver, summary):
    """Send push notifications to available drivers"""
    errors = []
    try:
        try:
            devices = driver.user.device.all()
            if devices:
                device_token = devices[0].token
                logger.info(
                    f"Sending notification to: {device_token}")
                send_push_notification.delay(
                    token=device_token,
                    title='New Ride Alert on movbay',
                    notification_type="Ride Alert",
                    data='You have a new ride suggestion on Movbay, check it out and start earning'
                )
        except Exception as e:
            errors.append(
                f"Failed to notify driver {driver} {str(e)}")
            logger.error(f"Notification error: {str(e)}")

        if errors:
            logger.warning(f"Some notifications failed: {errors}")
    except Exception as e:
        logger.error(f"Critical error in notify_drivers: {str(e)}")
        raise


def handle_payment(payment_method, amount, user, data, serializer, pk):
    try:
        if payment_method == 'wallet':
            platform_wallet, _ = Wallet.objects.get_or_create(owner__email=os.getenv('ADMIN_MAIL', None))
            sender_wallet = user.wallet
            print(platform_wallet, sender_wallet)
            print("BALANCE:", sender_wallet.balance, "AMOUNT:", amount, type(amount))
            print(user.wallet)
            if Decimal(sender_wallet.balance) < Decimal(amount):
                print(True)
                raise ValidationError({"wallet": "Insufficient Funds"})
            sender_wallet.balance -= amount
            sender_wallet.save()
            #WalletTransactions.objects.create(content='Payment For Purchase Made Succesfully', type='Item-Purchase', wallet=sender_wallet, amount=amount, status='completed', reference_code=reference)
            platform_wallet.balance += amount
            platform_wallet.save()
            try:
                rider = RiderProfile.objects.get(id=pk)
            except RiderProfile.DoesNotExist:
                raise NotFound({"rider": "Rider not found."})

            # --- Address validation ---
            print(data)
            destination_address = data.get("drop_address", None)
            if not destination_address:
                raise ValidationError(
                    {"drop_address": "Destination address is required."})

            rider_latitude = rider.latitude
            rider_longitude = rider.longitude
            destination_coords = get_coordinates_from_address(
                destination_address)
            destination = (destination_coords.get('latitude'),
                        destination_coords.get('longitude'))
            origin = (rider_latitude, rider_longitude)

            if not rider_latitude or not rider_longitude or not destination:
                raise ValidationError(
                    {"coordinates": "Unable to resolve one or more addresses."})

            summary = get_eta_distance_and_fare(origin, destination)

            # --- Save delivery ---
            delivery = serializer.save(owner=user)

            # --- Handle package images ---
            package_images = data.pop("packageimages", None) or []
            for image in package_images:
                if image:
                    try:
                        serialized_image = {
                            "file_content": b64encode(image.read()).decode("utf-8"),
                            "filename": image.name,
                        }
                        upload_delivery_images.delay(
                            delivery.id, serialized_image)
                    except Exception as e:
                        logger.warning(
                            f"Image upload failed for delivery {delivery.id}: {str(e)}")
            Ride.objects.create(rider=rider.user, distance_km=summary.get('distance_km'), duration_minutes=summary.get(
                'duration_minutes'), fare_amount=summary.get('fare_amount'))

            # --- Notify drivers only after DB commit ---
            transaction.on_commit(lambda: notify_driver(rider, summary))   
            Payment.objects.create(
                user=user,
                amount=amount,
                currency="NGN",
            # reference=reference,
                transaction_id=generate_tx_ref('PAY'),
                status='completed',
                payment_method='wallet'
            )
            return {"status":"Completed"}
    
        elif payment_method == 'package_delivery':
            
            Payment.objects.create(
                user=user,
                amount=amount,
                currency="NGN",
                # reference=reference,
                transaction_id=generate_tx_ref('PAY'),
                status='completed',
                payment_method='wallet'
            )
            return {"status":"Completed"}
            
    except Exception as e:
        print(str(e))
        return {"status":"Failed"}
            