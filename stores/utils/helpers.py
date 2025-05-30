from django.core.exceptions import ValidationError
import os
from celery import shared_task
import cloudinary
from concurrent.futures import ThreadPoolExecutor


def user_file_path(instance, filename):
    # uploads/user_<id>/<filename>
    return f"Store/Products/Videos/user_{instance.id}/{filename}"



def validate_video_file_extension(value):
    max_size_mb = 20
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.mp4', '.avi', '.mov', '.wmv']
    if ext not in valid_extensions:
        raise ValidationError('Unsupported file extension.')
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Max file size is {max_size_mb} MB")
    

def upload_single_image(image_data, ProductImage):
    """Helper function for parallel upload"""
    try:
        upload_result = cloudinary.uploader.upload(
            image_data,
            folder=f'products/{image_data["product_id"]}',
            transformation={'quality': 'auto', 'fetch_format': 'auto'}
        )
        return ProductImage(
            product_id=image_data['product_id'],
            image_url=upload_result['secure_url'],
            order=image_data['order']
        )
    except Exception as e:
        print(f"Upload failed: {e}")
        return None



# @shared_task
# def upload_product_images(product_id, images, ProductImage):
#     """Background task to upload images"""
#     uploaded_images = []
    
#     for image_data in images:
#         try:
#             # Decode base64 image or handle file path
#             upload_result = cloudinary.uploader.upload(
#                 image_data,
#                 transformation={'quality': 'auto', 'fetch_format': 'auto'}
#             )
            
#             uploaded_images.append({
#                 'product_id': product_id,
#                 'image_url': upload_result['secure_url'],
#             })
#         except Exception as e:
#             print(f"Upload failed: {e}")
#     if uploaded_images:
#         product_images = [
#             ProductImage(
#                 product=img['product_id'],
#                 image_url=img['image_url'],
#                 order=img['order'],
#                 status='completed'
#             )
#             for img in uploaded_images
#         ]
#         ProductImage.objects.bulk_create(product_images)
    
#     return len(uploaded_images)