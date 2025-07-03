from .base import PaymentMethod
from .wallet_payment import WalletPayment
from .apple_pay import ApplePayPayment
from .google_pay import GooglePayPayment
from .card_payment import CardPayment
from .bank_transfer import BankTransfer
__all__ = [
    'PaymentMethod', 
    'WalletPayment', 
    'ApplePayPayment', 
    'GooglePayPayment', 
    'CardPayment',
    'BankTransfer',
]