from celery import shared_task
import base64
from io import BytesIO
from cloudinary.uploader import upload

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
    
# @shared_task
# def auto_post_to_story(image_data):
#     try:
        
#         # Decode the base64 string back to bytes
#         image_bytes = base64.b64decode(image_data["file_content"])
#         image_file = BytesIO(image_bytes)
#         image_file.name = image_data["filename"]

#         upload_result = upload(
#             image_file,
#             folder=f'products/{image_data["product_id"]}',
#         )
#         product_image = ProductImage.objects.create(
#             product_id=image_data['product_id'],
#             image_url=upload_result['secure_url'],
#         )
#         return product_image.id
#     except Exception as e:
#         print(f"Upload failed: {e}")
#         return None
