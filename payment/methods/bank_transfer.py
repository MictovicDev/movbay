from . import PaymentMethod
from typing import Dict, Any

class BankTransfer(PaymentMethod):
    def prepare_payment_data(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare card payment data"""
        transaction_data['channels'] = ['bank_transfer']
        return transaction_data
    
    def validate_payment_data(self, transaction_data: Dict[str, Any]) -> bool:
        """Validate card payment data"""
        required_fields = ['email', 'amount', 'reference']
        return all(field in transaction_data for field in required_fields)