from .base import PaymentMethod
from typing import Dict, Any

class WalletPayment(PaymentMethod):
    
    def prepare_payment_data(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare wallet payment data"""
        # Add wallet-specific data
        transaction_data['payment_type'] = 'wallet'
        transaction_data['channels'] = 'bank_transfer'
        
        return transaction_data
    
    def validate_payment_data(self, transaction_data: Dict[str, Any]) -> bool:
        """Validate wallet payment data"""
        required_fields = ['email', 'amount', 'reference']
        return all(field in transaction_data for field in required_fields)
