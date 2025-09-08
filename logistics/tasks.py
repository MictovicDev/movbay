from celery import shared_task
from io import BytesIO
from cloudinary.uploader import upload
from users.models import RiderProfile
from base64 import b64decode
from logistics.models import KYC
import logging
import time

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def upload_rider_files(self, kyc_id, file_data):
    try:
        kyc = KYC.objects.get(id=kyc_id)
    except KYC.DoesNotExist:
        logger.error(f"KYC with id {kyc_id} not found")
        return

    updates = {}
    for file_type, file_bytes in file_data.items():
        try:
            # Create a unique public ID for each file
            public_id = f"rider_kyc/{kyc.rider.user.id}_{file_type}_{int(time.time())}"

            # Upload to Cloudinary
            upload_result = upload(
                BytesIO(file_bytes),
                public_id=public_id,
                resource_type="auto"  # Auto-detect file type
            )

            if not upload_result.get('secure_url'):
                raise ValueError("No secure URL returned from Cloudinary")

            # Map file types to model fields
            field_map = {
                'nin': 'nin_url',
                'proof_of_address': 'poa_url',
                'drivers_licence': 'drivers_licence_url'
            }

            if file_type not in field_map:
                logger.warning(f"Unknown file type: {file_type}")
                continue

            updates[field_map[file_type]] = upload_result['secure_url']
            logger.info(f"Successfully uploaded {file_type} for rider {kyc.rider.user.id}")

        except Exception as e:
            logger.error(f"Failed to upload {file_type}: {str(e)}")
            # Retry the entire task if any file fails
            self.retry(exc=e, countdown=60 * self.request.retries)
            return

    # Apply all updates at once
    if updates:
        try:
            KYC.objects.filter(id=kyc_id).update(**updates)
            logger.info(f"Successfully updated KYC documents for rider {kyc.rider.user.id}")
        except Exception as e:
            logger.error(f"Failed to update KYC record: {str(e)}")
            self.retry(exc=e, countdown=60 * self.request.retries)