from .models import Driver
from .utils.haversine import haversine
def get_nearby_drivers(store_lat, store_lng, radius_km=5):
    """
    Returns a list of available drivers within `radius_km` from store.
    """
    candidates = Driver.objects.filter(is_online=True)
    nearby = []

    for driver in candidates:
        distance = haversine(store_lat, store_lng, driver.latitude, driver.longitude)
        if distance <= radius_km:
            nearby.append({
                "driver_id": driver.id,
                "distance_km": round(distance, 2),
                "lat": driver.latitude,
                "lng": driver.longitude
            })
    
    return sorted(nearby, key=lambda x: x["distance_km"])
