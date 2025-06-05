# models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Payment(models.Model):
    CARD = 'card'
    BANK_TRANSFER = 'bank_transfer'
    MOVBAY_WALLET = 'mobile_wallet'
    GOOGLE_PAY = 'google_pay'
    APPLE_PAY = 'apple_pay'
    
    METHOD_CHOICES = [
        (CARD, 'Credit/Debit Card'),
        (BANK_TRANSFER, 'Bank Transfer'),
        (MOVBAY_WALLET, 'Mobile Wallet'),
        (GOOGLE_PAY, 'Google Pay'),
        (APPLE_PAY, 'Apple Pay'),
    ]
    
   
    FLUTTERWAVE = 'flutterwave'
    PAYSTACK = 'paystack'
    
    
    PROCESSOR_CHOICES = [
        (FLUTTERWAVE, 'Flutterwave'),
        (PAYSTACK, 'Paystack'),
        
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    processor = models.CharField(max_length=20, choices=PROCESSOR_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    transaction_id = models.CharField(max_length=100, blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    
    def __str__(self):
        return f"{self.user.username}"