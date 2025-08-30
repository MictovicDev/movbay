from rest_framework.serializers import ModelSerializer
from .models import Wallet, WalletTransactions




class WalletSerializer(ModelSerializer):
    
    class Meta:
        model = Wallet
        fields = '__all__'
        
        

class WalletTransactionSerializer(ModelSerializer):
    
    class Meta:
        model = WalletTransactions
        fields = '__all__'