import requests
from django.conf import settings


class PaymentMethod:
    def initialize_transaction(self, email, amount, user_id, gateway):
        raise NotImplementedError("initialize_transaction must be implemented")


class CardPayment(PaymentMethod):
    def initialize_transaction(self, email, amount, user_id, gateway):
        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}' if gateway == 'paystack' else f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'email': email,
            'amount': int(float(amount) * 100),  # Convert to kobo/cents
            'channels': ['card'],
            'metadata': {'user_id': user_id, 'payment_method': 'card', 'gateway': gateway}
        }

        raise Exception(
            data.get('message', 'Transaction initialization failed'))


class DigitalWalletPayment(PaymentMethod):
    def __init__(self, wallet_type):
        self.wallet_type = wallet_type  # 'apple_pay' or 'google_pay'

    def initialize_transaction(self, email, amount, user_id, gateway):
        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}' if gateway == 'paystack' else f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'email': email,
            'amount': int(float(amount) * 100),
            'channels': [self.wallet_type],
            'currency': 'USD',  # Required for Apple Pay/Google Pay
            'metadata': {'user_id': user_id, 'payment_method': self.wallet_type, 'gateway': gateway}
        }


class BankTransferPayment(PaymentMethod):
    def initialize_transaction(self, email, amount, user_id, gateway):
        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}' if gateway == 'paystack' else f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'email': email,
            'amount': int(float(amount) * 100),
            'channels': ['bank_transfer'],
            'metadata': {'user_id': user_id, 'payment_method': 'bank_transfer', 'gateway': gateway}
        }


class PaymentFactory:
    @staticmethod
    def create_payment_method(method, gateway='paystack'):
        try:
            if method == 'card':
                return CardPayment()
            elif method in ['apple_pay', 'google_pay']:
                return DigitalWalletPayment(method)
            elif method == 'bank_transfer':
                return BankTransferPayment()
            raise ValueError(f"Invalid payment method: {method}")
        except Exception as e:
            if gateway == 'paystack':
                # Fallback to Flutterwave
                return PaymentFactory.create_payment_method(method, gateway='flutterwave')
            raise e
