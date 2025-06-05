from .base import PaymentMethod

class CardPayment(PaymentMethod):
    def validate(self):
        return 'wallet_type' in self.data  # 'google_pay' or 'apple_pay'
    
    def get_processor_data(self):
        return {
            'type': 'digital_wallet',
            'wallet_type': self.data['wallet_type'],
            'token': self.data.get('token'),
        }