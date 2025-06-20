from abc import ABC, abstractmethod
from typing import Dict, Any

class PaymentMethod(ABC):
    """Abstract base class for payment methods"""
    
    @abstractmethod
    def prepare_payment_data(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payment data specific to this method"""
        pass
    
    @abstractmethod
    def validate_payment_data(self, transaction_data: Dict[str, Any]) -> bool:
        """Validate payment data for this method"""
        pass