import netfix
import requests
import time
from config import DATA_API_BASE
from db import get_last_timestamp, set_last_timestamp

def fetch_trades(limit=100):
    """
    Fetch recent trades from Polymarket public data API
    """
    params = {
        "limit": limit
    }

    try:
        r = requests.get(
            f"{DATA_API_BASE}/trades",
            params=params,
            timeout=20
        )
        r.raise_for_status()
        trades = r.json()

        if not trades:
            return []

        latest_timestamp = max(int(t["timestamp"]) for t in trades)
        set_last_timestamp(latest_timestamp)

        return trades

    except Exception as e:
        print(f"Error fetching trades: {e}")
        return []

