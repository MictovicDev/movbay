from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Device(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='device')
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} Token"


class Notification(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='notification_sender', blank=True, null=True)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE,
                                 related_name='notification_receiver', null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['receiver']),
            models.Index(fields=['is_read']),
            models.Index(fields=['created_at'])
        ]

    # def __str__(self):
    #     return f"Notification for {self.sender.email} - {self.title}"
