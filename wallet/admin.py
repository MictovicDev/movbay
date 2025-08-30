from django.contrib import admin
from .models import Wallet, WalletTransactions
# Register your models here.

admin.site.register(Wallet)
admin.site.register(WalletTransactions)
