from abc import ABC, abstractmethod
import requests
from decimal import Decimal
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class PaymentProvider(ABC):
    """Abstract base class for payment providers"""
    
    @abstractmethod
    def initialize_payment(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize payment with the provider"""
        pass
    
    @abstractmethod
    def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify payment status with the provider"""
        pass
    
    @abstractmethod
    def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook from the provider"""
        pass