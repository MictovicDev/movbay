from .base import PaymentProcessor
import requests
import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent


load_dotenv(BASE_DIR / ".env")


class PayStackProcessor(PaymentProcessor):
    
    def __init__(self):
        self.url = "https://api.paystack.co/"
        self.headers = {
            "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET')}",
            "Content-Type": "application/json"
        }
        

    def create_dedicated_account(self, data):
        response = requests.post(self.url, headers=self.headers, json=data)
        

        
       
    
    
    