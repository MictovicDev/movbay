import requests
import json

# API endpoint
url = "https://api.shipbubble.com/v1/shipping/address/validate"

# Replace with your actual API key
API_KEY = "sb_sandbox_dd3534a4e9ec96843afddab0b0cdf408680fe6e7134b4ffb96e1b8f805084f7c"

# Headers
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"  # remove if not required
}

# Sample payload
payload = {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+2348012345678",
    "address": "Ogor Street, Port-Harcourt, Rivers, Nigeria",
    # "latitude": 6.6018,    # optional
    # "longitude": 3.3515    # optional
}

# Send POST request
try:
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # raises an error for non-2xx responses
    data = response.json()
    print("Response Status:", response.status_code)
    print(json.dumps(data, indent=4))
except requests.exceptions.RequestException as e:
    print("Request failed:", e)
