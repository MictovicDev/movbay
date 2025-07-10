import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv



BASE_DIR = Path(__file__).resolve().parent.parent

print(BASE_DIR)

load_dotenv(BASE_DIR / ".env")

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

print(GOOGLE_MAPS_API_KEY)

def get_coordinates_from_address(address):
    """
    Uses Google Geocoding API to get coordinates for an address.
    This function is now crucial for the backend.
    """
    if not GOOGLE_MAPS_API_KEY:
        print("ERROR: GOOGLE_MAPS_BACKEND_API_KEY is not set.")
        return None

    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY,
        "region": "ng" # Restrict to Nigeria for better results
    }
    try:
        response = requests.get(GEOCODING_URL, params=params)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()

        if data["status"] == "OK" and data["results"]:
            location = data["results"][0]["geometry"]["location"]
            return {"latitude": location["lat"], "longitude": location["lng"]}
        elif data["status"] == "ZERO_RESULTS":
            print(f"Geocoding found no results for address: '{address}'")
            return None
        else:
            print(f"Error geocoding address '{address}': {data.get('error_message', data['status'])}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Network or API error during geocoding: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Failed to decode JSON response from Geocoding API for address: '{address}'")
        return None