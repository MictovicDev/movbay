from django.core.exceptions import ValidationError
import os
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


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
    


def notify_status_created(status):
    channel_layer = get_channel_layer()
    group_name = f"store_{status.store.id}_statuses"

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "status.created",
            "status": {
                "id": status.id,
                "image": status.image.url,  # or status.image if it’s a URL already
                "store": status.store.id,
                "created_at": status.created_at.isoformat(),
            },
        },
    )