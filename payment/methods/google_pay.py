from .base import PaymentMethod

class GooglePayment(PaymentMethod):
    def validate(self):
        return 'phone_number' in self.data
    
    def get_processor_data(self):
        return {
            'type': 'mobile_wallet',
            'phone_number': self.data['phone_number'],
            'wallet_provider': self.data.get('wallet_provider', 'mpesa'),
        }


# methods/digital_wallet.py
