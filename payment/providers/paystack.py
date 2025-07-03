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
        print(transaction_data.get('amount'))
        
        try:
            response = requests.post(url, json=transaction_data, headers=self._get_headers())
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
    
    def verify_account(self, payload):
        account_no = payload.get('account_number')
        bank_code = payload.get('bank_code')
        url = f"{self.base_url}/bank/resolve?account_number={account_no}&bank_code={bank_code}"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Paystack verification error: {e}")
            return {'status': False, 'message': str(e)}
               
    def create_transfer_recipient(self, payload):
        url = f"{self.base_url}/transferrecipient"
        print(payload)
        try:
            response = requests.post(url, json=payload, headers=self._get_headers())
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Paystack verification error: {e}")
            return {'status': False, 'message': str(e)}
        
    def transfer(self, payload):
        url = f"{self.base_url}/transfer"
        try:
            response = requests.post(url, json=payload, headers=self._get_headers())
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Paystack verification error: {e}")
            return {'status': False, 'message': str(e)}
            
        
      
         