from celery import shared_task
from users.utils.email import EmailManager
from payment.factories import ProcessorFactory
from .models import UserProfile
import cloudinary.uploader
import os

@shared_task
def send_welcome_email_async(from_email, to_emails, subject, html_content):
    sender = EmailManager(from_email, to_emails, subject, html_content)
    sender.send_email()
    
    

@shared_task
def save_profile_picture(profile_id, file_data, file_name):
    try:
        profile = UserProfile.objects.get(id=profile_id)
        if file_data:
            base_name, ext = os.path.splitext(file_name)
            print(base_name)
            public_id = f"profile_pictures/{base_name}"
            upload_result = cloudinary.uploader.upload(
            file_data,
            public_id=public_id,        # Sets the Cloudinary public ID (folder + name)
            resource_type="image",      # Explicitly tell Cloudinary this is an image
            overwrite=True              # Optional: overwrite if it already exists
        )
            image_url = upload_result.get("secure_url")
            profile.profile_picture = image_url  
            profile.save()
    except Exception as e:
        print(f"Error saving profile picture: {str(e)}")

    