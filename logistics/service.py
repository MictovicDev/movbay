from abc import ABC, abstractmethod
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import Dict
import requests
BASE_DIR = Path(__file__).resolve().parent.parent


dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path, override=True)

django_env = os.getenv('DJANGO_ENV')

# Abstract base class for logistics services
class LogisticsService(ABC):
    @abstractmethod
    def deliver(self, package_id: str) -> str:
        pass

# Concrete implementations for each logistics aspect
class MovbayExpress(LogisticsService):
    def deliver(self, package_id: str) -> str:
        return f"MovbayExpress: Delivering package {package_id} with express shipping."


class SpeedyDispatch(LogisticsService):
    """SpeedyDispatch Is For External Logistics API, in our Case Terminal

    Args:
        LogisticsService (_type_): _description_
    """
    def __init__(self):
        self.base_url = 'https://sandbox.terminal.africa/v1'
        self.secret_key = os.getenv('TERMINAL_TEST_SECRET_KEY')
        
   
    def create_package(self) -> Dict:
        headers = {
        "Authorization": f"Bearer {self.secret_key}",
        "Content-Type": "application/json"
        }
        
        data = {
            "height": 20,          # in cm
            "length": 30,          # in cm
            "name": "Medium Box",
            "size_unit": "cm",
            "type": "box",         # box, envelope, soft-packaging
            "width": 15,           # in cm
            "weight": 2,           # in kg
            "weight_unit": "kg"
        }
        url = self.base_url + 'v1/packaging'
        response = requests.post(url, headers=headers, json=data)

        # Print the response
        print("Status Code:", response.status_code)
        print("Response Body:", response.json())
        return 
        
    
    def deliver(self, package_id: str) -> str:
        return f"SpeedyDispatch: Dispatching package {package_id} with high-speed delivery."


class PickupHub(LogisticsService):
    def deliver(self, package_id: str) -> str:
        return f"PickupHub: Package {package_id} ready for pickup at the hub."
    

# Factory class to create logistics service instances
class LogisticsFactory:
    @staticmethod
    def get_logistics_service(service_type: str) -> LogisticsService:
        service_type = service_type.lower()
        if service_type == "movbay_express":
            return MovbayExpress()
        elif service_type == "speedy_dispatch":
            return SpeedyDispatch()
        elif service_type == "pickup_hub":
            return PickupHub()
        else:
            raise ValueError(f"Unknown logistics service type: {service_type}")