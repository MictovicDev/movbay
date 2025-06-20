from payment.methods import PaymentMethod, WalletPayment, ApplePayPayment, GooglePayPayment, CardPayment

class PaymentMethodFactory:
    """Factory for creating payment methods"""
    
    _methods = {
        'wallet': WalletPayment,
        'apple_pay': ApplePayPayment,
        'google_pay': GooglePayPayment,
        'card': CardPayment,
    }
    
    @classmethod
    def create_method(cls, method_name: str) -> PaymentMethod:
        """Create a payment method instance"""
        method_class = cls._methods.get(method_name.lower())
        if not method_class:
            raise ValueError(f"Unsupported payment method: {method_name}")
        return method_class()
    
    @classmethod
    def register_method(cls, name: str, method_class: type):
        """Register a new payment method"""
        cls._methods[name.lower()] = method_class