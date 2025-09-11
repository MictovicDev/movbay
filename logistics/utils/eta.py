# utils/google_maps.py
import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv



BASE_DIR = Path(__file__).resolve().parent.parent

print(BASE_DIR)

load_dotenv(BASE_DIR / ".env")

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')



def get_eta_distance_and_fare(origin, destination):
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    params = {
        "origins": f"{origin[0]},{origin[1]}",  # (lat, lng)
        "destinations": f"{destination[0]},{destination[1]}",
        "key": GOOGLE_MAPS_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    try:
        row = data["rows"][0]["elements"][0]
        distance_meters = row["distance"]["value"]
        duration_seconds = row["duration"]["value"]

        # Convert to km and minutes
        distance_km = distance_meters / 1000
        duration_minutes = duration_seconds / 60

        
            
        base_fare = 300  # Naira
        rate_per_km = 200  # Naira per km
        
        total_fare = base_fare + (rate_per_km * distance_km)

        return {
            "distance_km": round(distance_km, 2),
            "duration_minutes": round(duration_minutes),
            "fare_amount": int(total_fare)
        }

    except Exception as e:
        print("Google API Error:", e)
        return None
