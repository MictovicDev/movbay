from typing import Dict, Any
from .base import PaymentProvider
import requests
import logging

logger = logging.getLogger(__name__)

class FlutterwaveProvider(PaymentProvider):
    def __init__(self):
        from django.conf import settings
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.public_key = settings.FLUTTERWAVE_PUBLIC_KEY
        self.base_url = "https://api.flutterwave.com/v3"
    
    def _get_headers(self):
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_payment(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize Flutterwave payment"""
        url = f"{self.base_url}/payments"
        
        payload = {
            'tx_ref': transaction_data['reference'],
            'amount': str(transaction_data['amount']),
            'currency': transaction_data.get('currency', 'NGN'),
            'redirect_url': transaction_data.get('callback_url'),
            'customer': {
                'email': transaction_data['email'],
                'name': transaction_data.get('customer_name', ''),
            },
            'customizations': {
                'title': 'Payment',
                'description': 'Payment for services',
            },
            'meta': transaction_data.get('metadata', {}),
        }
        
        # Handle different payment methods
        if transaction_data.get('payment_method') == 'apple_pay':
            payload['payment_options'] = 'applepay'
        elif transaction_data.get('payment_method') == 'google_pay':
            payload['payment_options'] = 'googlepay'
        
        try:
            response = requests.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Flutterwave initialization error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify Flutterwave payment"""
        url = f"{self.base_url}/transactions/verify_by_reference"
        params = {'tx_ref': reference}
        
        try:
            response = requests.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Flutterwave verification error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Flutterwave webhook"""
        event = payload.get('event')
        data = payload.get('data', {})
        
        if event == 'charge.completed' and data.get('status') == 'successful':
            return {
                'status': 'completed',
                'reference': data.get('tx_ref'),
                'provider_reference': data.get('id'),
                'amount': Decimal(str(data.get('amount', 0))),
            }
        elif event == 'charge.completed' and data.get('status') == 'failed':
            return {
                'status': 'failed',
                'reference': data.get('tx_ref'),
                'provider_reference': data.get('id'),
            }
        
        return {'status': 'unknown', 'event': event}