from .base import PaymentProcessor
import requests
import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent


load_dotenv(BASE_DIR / ".env")



class PayStackProcessor(PaymentProcessor):
    
    def __init__(self, url):
        self.url = url
        self.headers = {
            "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET')}",
            "Content-Type": "application/json"
        }
        
        
    def charge(self, amount):
        return f"stripe_tx_{amount}"
        
    def create_dedicated_account(self, data):
        try:
            response = requests.post(self.url, headers=self.headers, json=data)
            if response.status_code == '200':
                url = 'https://api.paystack.co/dedicated_account'
                return requests.post()
                
            print(response.json())
            return response.json()
        except Exception as e:
            print(e)
        

        
       
    
    
    