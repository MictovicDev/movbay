from .base import PaymentMethod

class BankTransfer(PaymentMethod):
    def validate(self):
        return 'bank_code' in self.data
    
    def get_processor_data(self):
        return {
            'type': 'bank_transfer',
            'bank_code': self.data['bank_code'],
            'account_number': self.data.get('account_number'),
        }

