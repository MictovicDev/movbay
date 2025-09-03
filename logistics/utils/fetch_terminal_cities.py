import requests
from rapidfuzz import process
import os


TERMINAL_API_KEY = os.getenv('TERMINAL_API_KEY')
TERMINAL_API_SECRET = os.getenv('TERMINAL_TEST_SECRET_KEY') 


print(TERMINAL_API_SECRET)


# Quick mapping of state → capital (can expand this dictionary as needed)
STATE_CAPITALS = {
    "AB": "Umuahia",          # Abia
    "AD": "Yola",             # Adamawa
    "AK": "Uyo",              # Akwa Ibom
    "AN": "Awka",             # Anambra
    "BA": "Bauchi",           # Bauchi
    "BY": "Yenagoa",          # Bayelsa
    "BE": "Makurdi",          # Benue
    "BO": "Maiduguri",        # Borno
    "CR": "Calabar",          # Cross River
    "DE": "Asaba",            # Delta
    "EB": "Abakaliki",        # Ebonyi
    "ED": "Benin City",       # Edo
    "EK": "Ado Ekiti",        # Ekiti
    "EN": "Enugu",            # Enugu
    "FC": "Abuja",            # Federal Capital Territory
    "GO": "Gombe",            # Gombe
    "IM": "Owerri",           # Imo
    "JI": "Dutse",            # Jigawa
    "KD": "Kaduna",           # Kaduna
    "KN": "Kano",             # Kano
    "KT": "Katsina",          # Katsina
    "KE": "Kebbi",            # Kebbi
    "KO": "Lokoja",           # Kogi
    "KW": "Ilorin",           # Kwara
    "LA": "Ikeja",            # Lagos
    "NA": "Lafia",            # Nasarawa
    "NI": "Minna",            # Niger
    "OG": "Abeokuta",         # Ogun
    "ON": "Akure",            # Ondo
    "OS": "Osogbo",           # Osun
    "OY": "Ibadan",           # Oyo
    "PL": "Jos",              # Plateau
    "RI": "Port Harcourt",    # Rivers
    "SO": "Sokoto",           # Sokoto
    "TA": "Jalingo",          # Taraba
    "YO": "Damaturu",         # Yobe
    "ZA": "Gusau",
    "FC": "Abuja",
}


def fetch_terminal_cities(country_code="NG", state_code=None):
    url = "https://sandbox.terminal.africa/v1/cities"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TERMINAL_API_SECRET}"
    }
    params = {
        "country_code": country_code,
        "state_code": state_code
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()  # raise error for non-200s
        return response.json().get("data", [])
    except requests.RequestException as e:
        print(f"Error fetching cities from Terminal Africa: {e}")
        return []

def map_city_fuzzy(store_city, terminal_cities, state_code=None, threshold=70):
    """
    Fuzzy match user city to the closest Terminal-supported city.
    Falls back to the state capital if no good match is found.
    """
    if not terminal_cities:
        return None

    city_dict = {c["name"]: c for c in terminal_cities}
    city_names = list(city_dict.keys())

    # Try fuzzy match
    match, score, _ = process.extractOne(store_city, city_names)
    if score >= threshold:
        return city_dict[match]

    # Fallback: use state capital if available in list
    if state_code and state_code in STATE_CAPITALS:
        capital = STATE_CAPITALS[state_code]
        if capital in city_dict:
            print(f"No strong match for '{store_city}', falling back to state capital '{capital}'")
            return city_dict[capital]

    return None

# Example usage
# if __name__ == "__main__":
#     # Fetch all cities in Rivers state (RI)
#     state_code = "ZA"
#     cities = fetch_terminal_cities("NG", state_code)

#     # Suppose the store entered a city not recognized
#     store_city = "Zaria"  # Example of a misspelled or unrecognized city
#     matched = map_city_fuzzy(store_city, cities, state_code)

#     if matched:
#         print("Matched City:", matched)
#     else:
#         print(f"No close match found for '{store_city}' and no fallback capital available")
