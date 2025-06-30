from django.db import models
from django.contrib.auth import get_user_model
# Create your models here.

User = get_user_model()

class Wallet(models.Model):
    balance = models.PositiveBigIntegerField(default=0)
    owner = models.OneToOneField(User, on_delete=models.CASCADE)
    total_deposit = models.PositiveBigIntegerField(default=0)
    total_withdrawal = models.PositiveBigIntegerField(default=0)
    
    
    def __str__(self):
        return f"{self.owner.username} Wallet"
    
    
class WalletTransactions(models.Model):
    content = models.TextField()
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='wallet_transactions')
    
    
    def __str__(self):
        return f"{self.wallet.owner} Wallet Transactions"