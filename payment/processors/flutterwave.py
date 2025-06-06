from .base import PaymentProcessor

class FlutterWaveProcessor(PaymentProcessor):
    def charge(self, amount):
        return f"stripe_tx_{amount}"
    
    def create_dedicated_account(self, data):
        return super().create_dedicated_account(data)