import requests
import time
from config import SUBGRAPH_URL
from db import get_last_timestamp

QUERY = """
query GetTrades($first: Int!, $timestamp: BigInt!) {
  trades(
    first: $first
    orderBy: timestamp
    orderDirection: desc
    where: { timestamp_gte: $timestamp }
  ) {
    id
    trader
    market {
      id
      question
      category
      conditionId
      endDate
      liquidity
    }
    outcome
    amountUSD
    price
    timestamp
    transactionHash
  }
}
"""

def fetch_trades(since_timestamp=None, limit=100):
    """
    Fetch trades from Polymarket subgraph.
    
    Args:
        since_timestamp: Only fetch trades after this timestamp (default: last processed)
        limit: Maximum number of trades to fetch (default: 100)
    
    Returns:
        List of trade dictionaries
    """
    if since_timestamp is None:
        since_timestamp = get_last_timestamp()
    
    # If no previous timestamp, get trades from last hour
    if since_timestamp == 0:
        since_timestamp = int(time.time()) - 3600
    
    variables = {
        "first": limit,
        "timestamp": str(since_timestamp)
    }
    
    try:
        r = requests.post(
            SUBGRAPH_URL,
            json={"query": QUERY, "variables": variables},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        
        if "errors" in data:
            print(f"GraphQL errors: {data['errors']}")
            return []
        
        trades = data.get("data", {}).get("trades", [])
        
        # Update last timestamp if we got trades
        if trades:
            latest_timestamp = max(int(t.get("timestamp", 0)) for t in trades)
            from db import set_last_timestamp
            set_last_timestamp(latest_timestamp)
        
        return trades
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching trades: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
