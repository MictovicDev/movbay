from django.db import models
from django.contrib.auth import get_user_model
# Create your models here.

User = get_user_model()


class Wallet(models.Model):
    balance = models.PositiveBigIntegerField(default=0)
    owner = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='wallet')
    total_deposit = models.PositiveBigIntegerField(default=0)
    total_withdrawal = models.PositiveBigIntegerField(default=0)
    reference_code = models.CharField(max_length=250, blank=True, null=True)
    recipient_code = models.CharField(max_length=250, blank=True, null=True)

    def __str__(self):
        return f"{self.owner.username} Wallet"


class WalletTransactions(models.Model):

    Transaction_type = (
        ('Withdrawal', 'Withdrawal'),
        ('Item-Purchase', 'Item-Purchase'),
        ('Account-Funded', 'Account-Funded')
    )
    
    Status = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    content = models.TextField()
    type = models.CharField(
        max_length=250, choices=Transaction_type, blank=True, null=True)
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name='wallet_transactions')
    completed = models.BooleanField(default=False)
    amount = models.PositiveBigIntegerField(blank=True, null=True)
    transaction_code = models.CharField(max_length=250, blank=True, null=True)
    transaction_id = models.CharField(max_length=250, blank=True, null=True)
    status = models.CharField(max_length=250, choices=Status, blank=True, null=True)
    reference_code = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"{self.wallet.owner} Wallet Transactions"
