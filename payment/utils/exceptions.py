class PaymentError(Exception):
    """Base payment exception"""
    pass

class UnsupportedProviderError(PaymentError):
    """Raised when an unsupported payment provider is used"""
    pass

class UnsupportedMethodError(PaymentError):
    """Raised when an unsupported payment method is used"""
    pass

class PaymentInitializationError(PaymentError):
    """Raised when payment initialization fails"""
    pass

class PaymentVerificationError(PaymentError):
    """Raised when payment verification fails"""
    pass