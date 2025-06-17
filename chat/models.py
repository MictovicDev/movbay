from django.db import models
from django.contrib.auth import get_user_model
from stores.models import Store, Product

User = get_user_model()

class ChatBox(models.Model):
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True, related_name='sender'
    )
    receiver = models.ForeignKey(
        Store, on_delete=models.CASCADE, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['receiver']),
            models.Index(fields=['product']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Chat Between {self.sender.fullname} and {self.receiver.name}"


class Message(models.Model):
    chatbox = models.ForeignKey(
        ChatBox, on_delete=models.CASCADE, blank=True, null=True, related_name='messages'
    )
    content = models.TextField()
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True
    )
    receiver = models.ForeignKey(
        Store, on_delete=models.CASCADE, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True) 

    class Meta:
        indexes = [
            models.Index(fields=['chatbox']),
            models.Index(fields=['sender']),
            models.Index(fields=['receiver']),
        ]

    def __str__(self):
        return f"Message Between {self.sender.fullname} and {self.receiver.name}"
