from django.db import models
from django.contrib.auth import get_user_model
from stores.models import Store, Product, Status

User = get_user_model()



class Conversation(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='sender')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='receiver')
    room_name = models.CharField(max_length=250, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['receiver']),
            models.Index(fields=['room_name']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Conversation Between {self.sender} and {self.receiver}"
    
    


class Message(models.Model):
    chatbox = models.ForeignKey(Conversation, on_delete=models.CASCADE, blank=True, null=True, related_name='messages')
    content = models.TextField()
    sender = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='message_sender')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='message_receiver')
    delivered = models.BooleanField(default=False)
    seen = models.BooleanField(default=False)
    # is_sender = models.BooleanField(default=False)
    # is_receiver = models.BooleanField(default=False)
    status = models.ForeignKey(Status, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    

    class Meta:
        indexes = [
            models.Index(fields=['chatbox']),
            models.Index(fields=['sender']),
            models.Index(fields=['receiver']),
        ]

    def __str__(self):
        return f"Message Between {self.sender} and {self.receiver}"


