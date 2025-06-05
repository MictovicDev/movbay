from abc import ABC, abstractmethod
import requests
from django.conf import settings
import uuid

# Abstract base class for payment services
class PaymentService(ABC):
    @abstractmethod
    def initiate_payment(self, amount: float, email: str, reference: str, callback_url: str) -> dict:
        pass

    @abstractmethod
    def verify_payment(self, reference: str) -> dict:
        pass

# Paystack payment service implementation
class PaystackService(PaymentService):
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"

    def initiate_payment(self, amount: float, email: str, reference: str, callback_url: str) -> dict:
        url = f"{self.base_url}/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "amount": int(amount * 100),  # Convert to kobo
            "email": email,
            "reference": reference,
            "callback_url": callback_url
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def verify_payment(self, reference: str) -> dict:
        url = f"{self.base_url}/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

# Flutterwave payment service implementation
class FlutterwaveService(PaymentService):
    def __init__(self):
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.base_url = "https://api.flutterwave.com/v3"

    def initiate_payment(self, amount: float, email: str, reference: str, callback_url: str) -> dict:
        url = f"{self.base_url}/payments"
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "tx_ref": reference,
            "amount": amount,
            "currency": "NGN",
            "redirect_url": callback_url,
            "customer": {"email": email}
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def verify_payment(self, reference: str) -> dict:
        url = f"{self.base_url}/transactions/verify_by_reference?tx_ref={reference}"
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

# Factory class to create payment service instances
class PaymentFactory:
    @staticmethod
    def get_payment_service(service_type: str) -> PaymentService:
        service_type = service_type.lower()
        if service_type == "paystack":
            return PaystackService()
        elif service_type == "flutterwave":
            return FlutterwaveService()
        else:
            raise ValueError(f"Unknown payment service type: {service_type}")