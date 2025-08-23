from abc import ABC, abstractmethod
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import Dict
import requests
import requests
import logging
from django.conf import settings
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .models import Address, Parcel, ShippingRate, Shipment
from django.shortcuts import get_object_or_404
from stores.models import Product, Order
BASE_DIR = Path(__file__).resolve().parent.parent


print(BASE_DIR)

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


logger = logging.getLogger(__name__)


class SpeedyDispatch(LogisticsService):
    def __init__(self):

        self.api_key = os.getenv('TERMINAL_TEST_SECRET_KEY')
        self.base_url = 'https://sandbox.terminal.africa/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def deliver(self, package_id: str) -> str:
        pass

    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make HTTP request to Terminal Africa API"""
        url = f"{self.base_url}/{endpoint}"

        try:
            if method.upper() == "GET":
                response = requests.get(
                    url=url,
                    params=params,
                    headers=self.headers,
                    timeout=30
                )
            else:  # POST, PUT, DELETE, etc.
                response = requests.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    params=params,
                    headers=self.headers,
                    timeout=30
                )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Terminal Africa API Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"API request failed: {str(e)}")
        

    def create_pickupaddress(self, product_id: int = None, order_id: int = None) -> Dict:
        # print(self.api_key)
        """Create address on Terminal Africa"""
        print(product_id)
        if product_id:
            product = get_object_or_404(Product, id=product_id)
            store = product.store
        elif order_id:
            order = get_object_or_404(Order, id=order_id)
            store = order.store
        else:
            raise ValueError("Either product_id or order_id must be provided.")
        print(store.owner.email)
        pickup_address = {
                    "first_name": store.name,
                    "last_name": store.owner.username,
                    "fullname": store.owner.fullname,
                    "phone": str(store.owner.phone_number),
                    "email": store.owner.email,
                    "country": store.country,
                    "city": store.city,
                    "state": store.state,
                    # "zip": order.delivery.postal_code,
                    "line1": store.address1,
                    "line2": store.address2,
                }
        return self._make_request('POST', 'addresses', pickup_address)
    
    
    def create_deliveryaddress(self, delivery_details:dict) -> Dict:
        """Create address on Terminal Africa"""
        print(delivery_details.get('email_address'))
        
        delivery_address = {
                    "first_name": delivery_details.get('fullname'),
                    "last_name": delivery_details.get('fullname'),
                    "phone": delivery_details.get('phone_number'),
                    "email": delivery_details.get('email_address'),
                    "country": delivery_details.get('country'),
                    "city": delivery_details.get('city'),
                    "state": delivery_details.get('state'),
                    # "zip": delivery_details.get(''),
                    "line1": delivery_details.get('delivery_address'),
                    "line2": delivery_details.get('alternative_address'),
                }
        print("Payload to Terminal:", delivery_address)
        return self._make_request('POST', 'addresses', delivery_address)
    

    def create_parcel(self, order_items, weight, packaging_id) -> Dict:
        """Create parcel on Terminal Africa"""
        product_ids = [item["product"] for item in order_items]
        products = Product.objects.in_bulk(product_ids)  # one DB query for all products

        payload = {
            "description": "This is a Delivery From Movbay, Please Handle with Care",
            "items": [
                {
                    "name": products[order_item["product"]].title,
                    "description": products[order_item["product"]].description,
                    "quantity": order_item["quantity"],
                    "weight": weight / len(order_items),  # evenly distribute weight
                    "currency": "NGN",
                    "value": order_item["amount"]
                }
                for order_item in order_items
            ],
            "packaging": packaging_id,  # Use an actual packaging ID from your account
            "weight_unit": "kg",
        }

        return self._make_request('POST', 'parcels', payload)

    def create_package(self, package: Dict):
        return self._make_request('POST', 'packaging', package)

    def get_shipping_rates(self, pickup_address_id: str, delivery_address_id: str,
                       parcel_id: str = None, currency: str = "NGN", 
                       cash_on_delivery: bool = False) -> Dict:
        """Get shipping rates from Terminal Africa"""
        params = {
            'pickup_address': pickup_address_id,
            'delivery_address': delivery_address_id,
            'parcel_id': parcel_id,
            'currency': currency,
            'cash_on_delivery': cash_on_delivery,
        }
        
        return self._make_request('GET', 'rates/shipment', params=params)

    def create_shipment(self, rate_id: str, pickup_date: str,
                        pickup_time: str = 'morning', delivery_note: str = '',
                        metadata: Dict = None) -> Dict:
        """Create shipment on Terminal Africa"""
        payload = {
            'rate_id': rate_id,
            'pickup_date': pickup_date,
            'pickup_time': pickup_time,
            'delivery_note': delivery_note,
            'metadata': metadata or {}
        }

        return self._make_request('POST', '/shipments', payload)

    def track_shipment(self, shipment_id: str) -> Dict:
        """Track shipment on Terminal Africa"""
        return self._make_request('GET', f'/shipments/{shipment_id}/track')

    def cancel_shipment(self, shipment_id: str) -> Dict:
        """Cancel shipment on Terminal Africa"""
        return self._make_request('POST', f'/shipments/{shipment_id}/cancel')

    def validate_address(self, address_id: str) -> Dict:
        """Validate address on Terminal Africa"""
        return self._make_request('POST', f'/addresses/{address_id}/validate')

    def get_carriers(self, country: str = 'NG') -> Dict:
        """Get available carriers for a country"""
        return self._make_request('GET', f'/carriers?country={country}')
