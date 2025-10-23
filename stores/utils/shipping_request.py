import requests, json, os
from logistics.models import Shipment




def create_shipment_model(response):
    data = response.json()
    try:
        ship_to = data.get('data')['ship_to']
        ship_from = data.get('data')['ship_from']
        courier = data.get('data')['courier']
        payment = data.get('data')['payment']
        items = data.get('data')['items']
        tracking_url = data.get('data')['tracking_url']
        order_id = data.get('data')['order_id']
        shipment = Shipment.objects.create(
            ship_to=ship_to, ship_from=ship_from, courier=courier, payment=payment, items=items, tracking_url=tracking_url, order_id=order_id)
        return shipment
    except Exception as e:
        return {"message": f"Error {e}"}



def shipping_request(delivery):
    url = 'https://api.shipbubble.com/v1/shipping/labels'
    API_KEY = os.getenv('API_KEY')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        'request_token': delivery.request.token,
        'service_code': delivery.service_code,
        'courier_id': delivery.courier_id,
    }
    try:
        print(json.dumps(payload, indent=4))
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        print("response Status:", response.status_code)
        print(json.dumps(data, indent=4))
        if response.status_code == '200':
             create_shipment_model(response)
        else:
            print('Response Data Not 200')
        return data
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Error response:", e.response.text)
        return None
    except Exception as e:
        print("Error Booking a Shipment:", e)
        return None