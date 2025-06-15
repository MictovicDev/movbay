from celery import shared_task
import base64
from io import BytesIO
from .models import Cart, CartItem
from cloudinary.uploader import upload
import os
import cloudinary
from .models import Store

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



@shared_task
def upload_store_files( store_id, file_data):
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
def create_cart(cart, user):
    for item in cart:
        Cart.objects.create(user=user)
        CartItem.objects.create()
       