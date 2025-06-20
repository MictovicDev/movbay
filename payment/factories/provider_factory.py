from ..providers import PaymentProvider, PaystackProvider, FlutterwaveProvider


class PaymentProviderFactory:
    """Factory for creating payment providers"""
    
    _providers = {
        'paystack': PaystackProvider,
        'flutterwave': FlutterwaveProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_name: str) -> PaymentProvider:
        """Create a payment provider instance"""
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unsupported payment provider: {provider_name}")
        return provider_class()
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a new payment provider"""
        cls._providers[name.lower()] = provider_class