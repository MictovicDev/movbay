from celery import shared_task
from io import BytesIO
from .models import Product
from cloudinary.uploader import upload
import cloudinary
from .models import Store, Status
from django.shortcuts import get_object_or_404
import base64, io, logging, requests
from notification.utils.fcm_utils import send_expo_push_notification
from .models import OrderTracking
import cloudinary.uploader
from stores.models import Store
from django.core.files.base import ContentFile
import logging
from users.utils.email import EmailManager
from logistics.service import SpeedyDispatch
# from .utils.create_speedy_dispatch import handle_speedy_dispatch
from typing import List, Dict, Any
from celery import shared_task
from django.db import transaction
from django.shortcuts import get_object_or_404
from logistics.service import SpeedyDispatch
from .utils.calculate_order_package import calculate_order_package
from logistics.models import ShippingRate, Address, Parcel
from stores.models import Product
import logging
from django.utils import timezone

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)





@shared_task
def upload_image(serialized_images, product_id):
    from .models import ProductImage
    for image_data in serialized_images:
        image_bytes = base64.b64decode(image_data["file_content"])
        image_file = BytesIO(image_bytes)
        image_file.name = image_data["filename"]

        upload_result = upload(
            image_file,
            folder=f'products/{product_id}',
        )
        ProductImage.objects.create(
            product_id=product_id,
            image_url=upload_result['secure_url'],
        )



@shared_task
def upload_single_image(image_data):
    try:
        from stores.models import ProductImage
        # Decode the base64 string back to bytes
        image_bytes = base64.b64decode(image_data["file_content"])
        image_file = BytesIO(image_bytes)
        image_file.name = image_data["filename"]

        upload_result = upload(
            image_file,
            folder=f'products/{image_data["product_id"]}',
        )
        product_image = ProductImage.objects.create(
            product_id=image_data['product_id'],
            image_url=upload_result['secure_url'],
        )
        return product_image.id
    except Exception as e:
        print(f"Upload failed: {e}")
        return None


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def upload_video(self, video_data, product_id):
    logger.info(f"Starting video upload for product_id: {product_id}")

    try:
        product = Product.objects.get(id=product_id)
        logger.debug("Decoding base64 video data")
        video_bytes = base64.b64decode(video_data)
        video_file = BytesIO(video_bytes)
        video_file.name = product.title

        logger.info("Uploading to cloud storage")
        upload_result = upload(
            video_file,
            folder=f'products/video/{product_id}',
            resource_type="video"
        )
        logger.info(f"upload_result: {upload_result} ({type(upload_result)})")

        logger.debug("Updating product model")

        product.video_url = upload_result["secure_url"]
        product.save()

        logger.info(f"Successfully uploaded video for product {product.id}")
        return product.id

    except (requests.exceptions.RequestException, ConnectionError) as e:
        logger.warning(f"Temporary network error: {e}, retrying...")
        raise self.retry(exc=e)

    except Exception as e:
        logger.error(f"Upload failed permanently: {e}")
        return None


@shared_task
def upload_store_files(store_id, file_data):
    try:
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            print('Store Does not exist')
        if file_data:
            for file in file_data:
                public_id = f"store_details/{store_id}"
                upload_result = cloudinary.uploader.upload(
                    file_data[file],
                    public_id=public_id,
                    overwrite=True
                )
                image_url = upload_result.get("secure_url")
                if file == 'cac':
                    store.cac_url = image_url
                    store.save()
                elif file == 'nin':
                    store.nin_url = image_url
                    store.save()
                else:
                    store.store_image_url = image_url
                    store.save()
    except Exception as e:
        print(f"Error saving profile picture: {str(e)}")


@shared_task
def send_order_complete_email_async(from_email, to_emails, subject, html_content):
    sender = EmailManager(from_email, to_emails, subject, html_content)
    sender.send_email()




@shared_task
def upload_status_files(status_id, image):
    """
    This
    """
    try:
        try:
            status = Status.objects.get(id=status_id)
        except Status.DoesNotExist:
            print(f"Status with ID {status_id} not found.")
            return
        if image:
            public_id = f"status_details/{status.id}"
            video_bytes = base64.b64decode(image)
            image_bytes = BytesIO(video_bytes)
            # image_data = base64.b64decode(image)
            # image_file = io.BytesIO(image_data)
            upload_result = cloudinary.uploader.upload(
                image_bytes,
                public_id=public_id,
                overwrite=True
            )
            image_url = upload_result.get("secure_url")
            print(image_url)
            status.image_url = image_url
            status.save()
    except Exception as e:
        print(f"Error saving profile picture: {str(e)}")


@shared_task
def send_push_notification(token, title, notification_type, data):
    try:
        send_expo_push_notification(token, title, notification_type, data)
    except Exception as e:
        print(f"Error {str(e)}")
        
        

@shared_task
def update_to_enroute(order_tracking_id):
   try:
        order_tracking = get_object_or_404(OrderTracking, id=order_tracking_id)
        order_tracking.rider_en_route = True
        order_tracking.save()
   except OrderTracking.DoesNotExist:
        logger.info("Error Tracking Order")



@shared_task
def update_to_arriving(order_tracking):
    try:
        order_tracking.order_accepted = True
        order_tracking.save()
    except OrderTracking.DoesNotExist:
        logger.info("Error Tracking Order")
        
        
@shared_task
def delete_expired_statuses():
    Status.objects.filter(expires_at__lte=timezone.now()).delete()     

logger = logging.getLogger(__name__)

def process_shipping_rates(rates_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process and format shipping rates for frontend."""
    processed_rates = []
    for rate in rates_data:
        processed_rate = {
            'rate_id': rate.get('rate_id'),
            'carrier_name': rate.get('carrier_name'),
            'carrier_logo': rate.get('carrier_logo'),
            'amount': rate.get('amount'),
            'currency': rate.get('currency'),
            'delivery_time': rate.get('delivery_time'),
            'pickup_time': rate.get('pickup_time'),
            'service_description': rate.get('carrier_rate_description'),
            'dropoff_required': rate.get('dropoff_required', False),
            'includes_insurance': rate.get('includes_insurance', False),
            'recommended': rate.get('metadata', {}).get('recommended', False)
        }
        processed_rates.append(processed_rate)
    processed_rates.sort(key=lambda x: x['amount'])
    logger.debug("Processed shipping rates: %s", processed_rates)
    return processed_rates

def get_best_rate(rates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Select the best shipping rate (recommended or cheapest)."""
    recommended_rate = next((r for r in rates if r.get("recommended")), None)
    return recommended_rate or min(rates, key=lambda r: r["amount"])

@shared_task(bind=True, ignore_result=False)
def handle_speedy_dispatch_task(self, user_id: int, product_id: int, delivery_details: Dict[str, Any], order_items_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Handle Speedy dispatch logic as a background task.

    Args:
        user_id: ID of the authenticated user.
        product_id: ID of the product being shipped.
        delivery_details: Dictionary containing delivery address details.
        order_items_data: Serialized order items data.

    Returns:
        Dictionary with task result or error details.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        # Validate inputs
        if not product_id or not delivery_details or not order_items_data:
            logger.error("Invalid input: user_id=%s, product_id=%s, delivery_details=%s, order_items=%s",
                         user_id, product_id, delivery_details, order_items_data)
            return {"status": "error", "error": "Invalid input data"}

        user = get_object_or_404(User, id=user_id)
        product = get_object_or_404(Product, id=product_id)
        dispatch = SpeedyDispatch()
        logger.info(order_items_data)
        # Deserialize order_items if needed (depends on how order_items is passed)
        # Assuming order_items_data is a list of dicts; adjust based on your model
        order_items = order_items_data  # Modify this if order_items needs deserialization

        with transaction.atomic():
            # Step 1: Calculate package details
            payload = calculate_order_package(order_items)
            logger.info("Package payload calculated for product %s", product_id)

            # Step 2: Create addresses
            pickup_result = dispatch.create_pickupaddress(product_id)
            if not pickup_result.get('status'):
                logger.error("Failed to create pickup address for product %s", product_id)
                return {"status": "error", "error": "Failed to create pickup address"}
            pickup_address_id = pickup_result['data']['address_id']
            pickup_address = Address.objects.create(
                user=user, terminal_address_id=pickup_address_id, store=product.store
            )

            delivery_result = dispatch.create_deliveryaddress(delivery_details)
            if not delivery_result.get('status'):
                logger.error("Failed to create delivery address for product %s", product_id)
                return {"status": "error", "error": "Failed to create delivery address"}
            delivery_address_id = delivery_result['data']['address_id']
            delivery_address = Address.objects.create(
                user=user, terminal_address_id=delivery_address_id
            )

            # Step 3: Create package
            package_result = dispatch.create_package(payload)
            if not package_result.get('status'):
                logger.error("Failed to create package for product %s", product_id)
                return {"status": "error", "error": "Failed to create package"}

            # Step 4: Create parcel
            parcel_result = dispatch.create_parcel(
                order_items,
                payload.get('weight'),
                package_result['data']['packaging_id']
            )
            if not parcel_result.get('status'):
                logger.error("Failed to create parcel for product %s", product_id)
                return {"status": "error", "error": "Failed to create parcel"}
            parcel = Parcel.objects.create(
                user=user, terminal_parcel_id=parcel_result['data']['parcel_id']
            )
            logger.info("Parcel created: %s", parcel.terminal_parcel_id)

            # Step 5: Get shipping rates
            rates_result = dispatch.get_shipping_rates(
                pickup_address_id,
                delivery_address_id,
                parcel_result['data']['parcel_id']
            )
            if not rates_result.get('status') or not rates_result.get('data'):
                logger.error("No shipping rates available for product %s", product_id)
                return {"status": "error", "error": "No shipping rates available"}

            # Step 6: Process rates and select best option
            rates = process_shipping_rates(rates_result['data'])
            best_rate = get_best_rate(rates)
            logger.info("Best rate selected for product %s: %s", product_id, best_rate)

            # Step 7: Save best rate to database
            ShippingRate.objects.create(
                terminal_rate_id=best_rate['rate_id'],
                pickup_address=pickup_address,
                delivery_address=delivery_address,
                parcel=parcel,
                carrier_name=best_rate['carrier_name'],
                currency=best_rate['currency'],
                delivery_time=best_rate['delivery_time'],
                pickup_time=best_rate['pickup_time'],
                total=best_rate['amount']
            )

        # Return task result
        return {
            "status": "success",
            "message": "Shipping rates retrieved successfully",
            "data": {
                "rates": rates,
                "pickup_address_id": pickup_address_id,
                "delivery_address_id": delivery_address_id,
                "parcel_id": parcel_result['data']['parcel_id']
            }
        }

    except (ValueError, KeyError, Product.DoesNotExist, User.DoesNotExist) as e:
        logger.error("Speedy dispatch task error for product %s: %s", product_id, str(e), exc_info=True)
        return {"status": "error", "error": f"Speedy dispatch failed: {str(e)}"}
    except Exception as e:
        logger.critical("Unexpected error in speedy dispatch task for product %s: %s", product_id, str(e), exc_info=True)
        self.retry(countdown=60, max_retries=3)  # Retry up to 3 times with 60s delay
        return {"status": "error", "error": "An unexpected error occurred"}
        
    
