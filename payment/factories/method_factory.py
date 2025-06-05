from ..methods import CardPayment, BankTransfer, WalletPayment, GooglePayment, ApplePay

class PaymentMethodFactory:
    @staticmethod
    def create_method(method_type, data):
        methods = {
            'card': CardPayment,
            'bank_transfer': BankTransfer,
            'mobile_wallet': WalletPayment,
            'google_wallet': GooglePayment,
            'apple_pay': ApplePay,
            
        }
        
        method_class = methods.get(method_type)
        if not method_class:
            raise ValueError(f"Unknown payment method: {method_type}")
        
        return method_class(data)