# models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Payment(models.Model):

    PAYMENT_METHODS = [
        ('wallet', 'Wallet'),
        ('apple_pay', 'Apple Pay'),
        ('google_pay', 'Google Pay'),
        ('card', 'Credit/Debit Card'),
    ]

    PAYMENT_PROVIDERS = [
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
    ]

    PAYMENT_TYPE = [
        ('fund-wallet', 'Fund-Wallet'),
        ('normal-payment', 'Normal-Payment'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    method = models.CharField(
        max_length=20, choices=PAYMENT_METHODS, blank=True, null=True)
    provider = models.CharField(
        max_length=20, choices=PAYMENT_PROVIDERS, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    transaction_id = models.CharField(max_length=100, blank=True)
    success = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=250, blank=True,
                            null=True, choices=PAYMENT_TYPE)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHODS, blank=True, null=True)
    payment_provider = models.CharField(
        max_length=20, choices=PAYMENT_PROVIDERS, blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', blank=True, null=True)
    reference = models.CharField(
        max_length=100, unique=True, blank=True, null=True)
    provider_reference = models.CharField(
        max_length=100, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Payment"


class Transactions(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True)
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.owner.username} Transactions"
