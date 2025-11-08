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
from rest_framework.response import Response

import os


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def handle_payment(payment_method, provider_name, amount, user, package):
    """Handles payment processing for package delivery."""
    try:
        with transaction.atomic():  # everything inside is all-or-nothing
            print(amount)
            if payment_method == 'wallet':
                # Get platform wallet
                platform_wallet, _ = Wallet.objects.get_or_create(
                    owner__email=os.getenv('ADMIN_EMAIL', None)
                )
                print(platform_wallet)
                sender_wallet = user.wallet
                if Decimal(sender_wallet.balance) < Decimal(amount):
                    raise ValidationError({"wallet": "Insufficient Funds"})

                # Deduct from sender
                sender_wallet.balance -= Decimal(amount)
                print(sender_wallet.balance)
                # ✅ should be +=, not -=
                sender_wallet.total_withdrawal += Decimal(amount)
                sender_wallet.save()

                # Credit platform wallet
                platform_wallet.balance += Decimal(amount)
                platform_wallet.total_deposit += Decimal(amount)
                platform_wallet.save()

                # Check package address
                if not package.drop_address:
                    raise ValidationError(
                        {"drop_address": "Destination address is required."}
                    )

                # Record payment
                Payment.objects.create(
                    user=user,
                    amount=Decimal(amount),
                    currency="NGN",
                    transaction_id=generate_tx_ref('PAY'),
                    status='completed',
                    payment_method='wallet'
                )
                return {"status": "Completed"}

            elif payment_method == 'package_delivery':
                ride = package.package_ride.first()
                ride.paid = True
                ride.save()
                devices = ride.rider.device.first()
                device_token = devices.token
                send_push_notification.delay(
                    token=device_token,
                    title='Payment Made Succesfully',
                    notification_type="Payment",
                    data='Payment made succesfully proceed to pickup'
                )
                Payment.objects.create(
                    user=user,
                    amount=Decimal(amount),
                    currency="NGN",
                    transaction_id=generate_tx_ref('PAY'),
                    status='completed',
                    payment_method='package_delivery'
                )
                return {"status": "Completed"}

    except ValidationError as e:
        # Re-raise validation errors (atomic will rollback)
        raise
    except Exception as e:
        print(str(e))
        return {"status": "Failed"}
