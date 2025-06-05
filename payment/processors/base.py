from abc import ABC, abstractmethod

class PaymentProcessor(ABC):
    @abstractmethod
    def charge(self, amount):
        pass
    
    @abstractmethod
    def create_dedicated_account(self, amount):
        pass