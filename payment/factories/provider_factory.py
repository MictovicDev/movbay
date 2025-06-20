from ..providers import PaymentProvider, PaystackProvider, FlutterwaveProvider


class PaymentProviderFactory:
    """Factory for creating payment providers"""
    
    providers = {
        'paystack': PaystackProvider,
        'flutterwave': FlutterwaveProvider,
    }
    
    
    @staticmethod
    def create_provider(provider_name: str) -> PaymentProvider:
        provider_class = PaymentProviderFactory.providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unsupported payment provider: {provider_name}")
        return provider_class()
    
  