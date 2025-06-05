from abc import ABC, abstractmethod

class PaymentMethod(ABC):
    def __init__(self, data):
        self.data = data
    
    @abstractmethod
    def validate(self):
        """Validate payment method data"""
        pass
    
    @abstractmethod
    def get_processor_data(self):
        """Format data for processor"""
        pass