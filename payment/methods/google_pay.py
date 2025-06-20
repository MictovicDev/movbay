from . import PaymentMethod
from typing import Dict, Any

class GooglePayPayment(PaymentMethod):
    def prepare_payment_data(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare Google Pay payment data"""
        transaction_data['payment_type'] = 'google_pay'
        transaction_data['channels'] = ['google_pay']
        return transaction_data
    
    def validate_payment_data(self, transaction_data: Dict[str, Any]) -> bool:
        """Validate Google Pay payment data"""
        required_fields = ['email', 'amount', 'reference']
        return all(field in transaction_data for field in required_fields)