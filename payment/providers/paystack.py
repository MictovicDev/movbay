import requests
from decimal import Decimal
from typing import Dict, Any
import logging
from .base import PaymentProvider
import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)

class PaystackProvider(PaymentProvider):
    def __init__(self):
        self.secret_key = os.getenv('PAYSTACK_SECRET_KEY')
        self.public_key = os.getenv('PAYSTACK_PUBLIC_KEY')
        self.base_url = "https://api.paystack.co"
    
    def _get_headers(self):
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_payment(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize Paystack payment"""
        url = f"{self.base_url}/transaction/initialize"
        
        payload = {
            'email': transaction_data['email'],
            'amount': int(Decimal(transaction_data['amount'])  * 100), #in kobo
            'currency': transaction_data.get('currency', 'NGN'),
            'reference': str(transaction_data['reference_id']),
            'metadata': transaction_data.get('metadata', {}),
        }
        print(payload.get('amount'))
        
        if transaction_data.get('payment_method') == 'apple_pay':
            payload['channels'] = ['apple_pay']
        elif transaction_data.get('payment_method') == 'google_pay':
            payload['channels'] = ['google_pay']
        
        try:
            response = requests.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if e.response is not None:
                logger.error(f"Paystack response: {e.response.text}")
                logger.error(f"Paystack initialization error: {e}")
                return {'status': False, 'message': str(e)}
    
    def verify_payment(self, reference: str) -> Dict[str, Any]:
        """Verify Paystack payment"""
        url = f"{self.base_url}/transaction/verify/{reference}"
        
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Paystack verification error: {e}")
            return {'status': False, 'message': str(e)}
    
    def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Paystack webhook"""
        event = payload.get('event')
        data = payload.get('data', {})
        
        if event == 'charge.success':
            return {
                'status': 'completed',
                'reference': data.get('reference'),
                'provider_reference': data.get('id'),
                'amount': Decimal(data.get('amount', 0)) / 100,  # Convert from kobo
            }
        elif event in ['charge.failed', 'charge.cancelled']:
            return {
                'status': 'failed',
                'reference': data.get('reference'),
                'provider_reference': data.get('id'),
            }
        
        return {'status': 'unknown', 'event': event}