"""
Market Resolution Checker - Check if markets have resolved
"""
import requests
from config import SUBGRAPH_URL

MARKET_QUERY = """
query GetMarket($marketId: ID!) {
  market(id: $marketId) {
    id
    question
    endDate
    resolution
    resolutionSource
    isResolved
    outcomeTokenPrices
  }
}
"""

def check_market_resolution(market_id):
    """
    Check if a market has been resolved
    
    Args:
        market_id: Market ID to check
    
    Returns:
        Dict with resolution info or None if not resolved
    """
    variables = {"marketId": market_id}
    
    try:
        r = requests.post(
            SUBGRAPH_URL,
            json={"query": MARKET_QUERY, "variables": variables},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        
        if "errors" in data:
            return None
        
        market = data.get("data", {}).get("market")
        if not market:
            return None
        
        is_resolved = market.get("isResolved", False)
        if not is_resolved:
            return None
        
        # Determine outcome
        outcome_prices = market.get("outcomeTokenPrices", [])
        if outcome_prices and len(outcome_prices) >= 2:
            yes_price = float(outcome_prices[0] or 0)
            no_price = float(outcome_prices[1] or 0)
            
            if yes_price > 0.5:
                outcome = "YES"
                resolution_price = yes_price
            elif no_price > 0.5:
                outcome = "NO"
                resolution_price = no_price
            else:
                outcome = "UNKNOWN"
                resolution_price = 0.5
        else:
            outcome = market.get("resolution", "UNKNOWN")
            resolution_price = 1.0 if outcome == "YES" else 0.0
        
        return {
            "market": market_id,
            "outcome": outcome,
            "resolution_price": resolution_price,
            "timestamp": int(market.get("endDate", 0)) if market.get("endDate") else None,
            "resolution_source": market.get("resolutionSource", "")
        }
        
    except Exception as e:
        print(f"Error checking market resolution: {e}")
        return None

def get_market_prices(market_id):
    """
    Get current market prices to track peak prices
    
    Args:
        market_id: Market ID
    
    Returns:
        Dict with current prices
    """
    variables = {"marketId": market_id}
    
    try:
        r = requests.post(
            SUBGRAPH_URL,
            json={"query": MARKET_QUERY, "variables": variables},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        
        if "errors" in data:
            return None
        
        market = data.get("data", {}).get("market")
        if not market:
            return None
        
        outcome_prices = market.get("outcomeTokenPrices", [])
        if outcome_prices and len(outcome_prices) >= 2:
            return {
                "yes_price": float(outcome_prices[0] or 0),
                "no_price": float(outcome_prices[1] or 0),
                "timestamp": int(market.get("endDate", 0)) if market.get("endDate") else None
            }
        
        return None
        
    except Exception as e:
        print(f"Error getting market prices: {e}")
        return None
