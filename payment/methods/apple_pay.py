from .base import PaymentMethod
from typing import Dict, Any

class ApplePayPayment(PaymentMethod):
    def prepare_payment_data(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare Apple Pay payment data"""
        transaction_data['payment_type'] = 'apple_pay'
        transaction_data['channels'] = ['apple_pay']
        return transaction_data
    
    def validate_payment_data(self, transaction_data: Dict[str, Any]) -> bool:
        """Validate Apple Pay payment data"""
        required_fields = ['email', 'amount', 'reference']
        return all(field in transaction_data for field in required_fields)
