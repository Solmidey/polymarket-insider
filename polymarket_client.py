import os
import requests

BASE_URL = "https://clob.polymarket.com"

API_KEY = os.getenv("POLYMARKET_API_KEY")

def pm_get(path, params=None, auth=False):
    headers = {
        "Accept": "application/json"
    }

    # Only attach auth if explicitly requested
    if auth and API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    url = f"{BASE_URL}{path}"
    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

