# Payment method choices
PAYMENT_METHODS = [
    ('wallet', 'Wallet'),
    ('apple_pay', 'Apple Pay'),
    ('google_pay', 'Google Pay'),
    ('card', 'Credit/Debit Card'),
]

# Payment provider choices
PAYMENT_PROVIDERS = [
    ('paystack', 'Paystack'),
    ('flutterwave', 'Flutterwave'),
]

# Payment status choices
PAYMENT_STATUS = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
]

# Supported currencies
SUPPORTED_CURRENCIES = ['NGN', 'USD', 'GHS', 'KES', 'UGX']