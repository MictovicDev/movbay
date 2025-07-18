from celery import shared_task
from io import BytesIO
from .models import Product
from cloudinary.uploader import upload
import cloudinary
from .models import Store, Status
from django.shortcuts import get_object_or_404
import base64, io, logging, requests
from notification.utils.fcm_utils import send_expo_push_notification



logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
                    store.cac = image_url
                    store.save()
                elif file == 'nin':
                    store.nin = image_url
                    store.save()
                else:
                    store.store_image = image_url
                    store.save()
    except Exception as e:
        print(f"Error saving profile picture: {str(e)}")


@shared_task
def upload_status_files(status_id, image):
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
def send_push_notification(token, title, notification_type):
    try:
        send_expo_push_notification(token, title, notification_type)
    except Exception as e:
        print(f"Error {str(e)}")
    
        
        
