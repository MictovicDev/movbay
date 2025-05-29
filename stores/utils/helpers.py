from django.core.exceptions import ValidationError
import os

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