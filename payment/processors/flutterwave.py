from .base import PaymentProcessor

class FlutterWaveProcessor(PaymentProcessor):
    def charge(self, amount):
        return f"stripe_tx_{amount}"