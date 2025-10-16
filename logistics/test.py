import requests
import json

# API endpoint
url = "https://api.shipbubble.com/v1/shipping/labels/categories"

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
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # raises an error for non-2xx responses
    data = response.json()
    print("Response Status:", response.status_code)
    print(json.dumps(data, indent=4))
except requests.exceptions.RequestException as e:
    print("Request failed:", e)


{
    "status": "success",
    "message": "Retrieved successfully",
    "data": [
        {
            "category_id": 98190590,
            "category": "Hot food"
        },
        {
            "category_id": 24032950,
            "category": "Dry food and supplements"
        },
        {
            "category_id": 77179563,
            "category": "Electronics and gadgets"
        },
        {
            "category_id": 2178251,
            "category": "Groceries"
        },
        {
            "category_id": 67658572,
            "category": "Sensitive items (ATM cards, documents)"
        },
        {
            "category_id": 20754594,
            "category": "Light weight items"
        },
        {
            "category_id": 67008831,
            "category": "Machinery"
        },
        {
            "category_id": 57487393,
            "category": "Medical supplies"
        },
        {
            "category_id": 99652979,
            "category": "Health and beauty"
        },
        {
            "category_id": 25590994,
            "category": "Furniture and fittings"
        },
        {
            "category_id": 74794423,
            "category": "Fashion wears"
        }
    ]
}