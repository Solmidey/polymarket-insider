"""
Market-wide Cluster Heatmap - Visualize clustering patterns across markets
"""
import json
from collections import defaultdict
from db import cur, conn
from datetime import datetime, timedelta

def generate_cluster_heatmap_data(hours_window=24):
    """
    Generate heatmap data showing clustering intensity across markets
    
    Args:
        hours_window: Time window to analyze (default: 24 hours)
    
    Returns:
        Dictionary with heatmap data for visualization
    """
    cutoff_timestamp = int((datetime.now() - timedelta(hours=hours_window)).timestamp())
    
    # Get all trades in the window
    cur.execute("""
        SELECT market, wallet, timestamp, usd, price
        FROM trades
        WHERE timestamp >= ?
        ORDER BY timestamp
    """, (cutoff_timestamp,))
    
    trades = cur.fetchall()
    
    # Group by market
    market_data = defaultdict(lambda: {
        "trades": [],
        "wallets": set(),
        "total_volume": 0,
        "cluster_score": 0
    })
    
    for market, wallet, timestamp, usd, price in trades:
        market_data[market]["trades"].append({
            "wallet": wallet,
            "timestamp": timestamp,
            "usd": usd,
            "price": price
        })
        market_data[market]["wallets"].add(wallet)
        market_data[market]["total_volume"] += usd
    
    # Calculate cluster scores for each market
    heatmap_data = []
    
    for market, data in market_data.items():
        # Cluster score based on:
        # 1. Number of unique wallets
        # 2. Trade concentration (many trades in short time)
        # 3. Volume concentration
        
        wallet_count = len(data["wallets"])
        trade_count = len(data["trades"])
        
        # Time concentration: check if trades are clustered in time
        if trade_count > 1:
            timestamps = sorted([t["timestamp"] for t in data["trades"]])
            time_spread = timestamps[-1] - timestamps[0]
            time_concentration = trade_count / max(time_spread / 3600, 1)  # trades per hour
        else:
            time_concentration = 0
        
        # Calculate cluster score (0-100)
        cluster_score = min(100, (
            (wallet_count * 10) +  # More wallets = higher score
            (time_concentration * 5) +  # Time concentration
            (min(data["total_volume"] / 10000, 50))  # Volume factor
        ))
        
        heatmap_data.append({
            "market": market,
            "wallet_count": wallet_count,
            "trade_count": trade_count,
            "total_volume": data["total_volume"],
            "cluster_score": round(cluster_score, 2),
            "time_concentration": round(time_concentration, 2),
            "avg_trade_size": round(data["total_volume"] / trade_count if trade_count > 0 else 0, 2)
        })
    
    # Sort by cluster score
    heatmap_data.sort(key=lambda x: x["cluster_score"], reverse=True)
    
    return {
        "timestamp": int(datetime.now().timestamp()),
        "window_hours": hours_window,
        "markets": heatmap_data,
        "total_markets": len(heatmap_data)
    }

def get_market_cluster_details(market_id, hours_window=24):
    """Get detailed clustering information for a specific market"""
    cutoff_timestamp = int((datetime.now() - timedelta(hours=hours_window)).timestamp())
    
    cur.execute("""
        SELECT wallet, timestamp, usd, price
        FROM trades
        WHERE market = ? AND timestamp >= ?
        ORDER BY timestamp
    """, (market_id, cutoff_timestamp))
    
    trades = cur.fetchall()
    
    if not trades:
        return None
    
    # Group trades by time windows (1 hour buckets)
    time_buckets = defaultdict(list)
    wallets_in_market = set()
    total_volume = 0
    
    for wallet, timestamp, usd, price in trades:
        bucket = timestamp // 3600  # Hour bucket
        time_buckets[bucket].append({
            "wallet": wallet,
            "timestamp": timestamp,
            "usd": usd,
            "price": price
        })
        wallets_in_market.add(wallet)
        total_volume += usd
    
    # Find peak activity window
    peak_bucket = max(time_buckets.items(), key=lambda x: len(x[1])) if time_buckets else None
    
    return {
        "market": market_id,
        "total_trades": len(trades),
        "unique_wallets": len(wallets_in_market),
        "total_volume": total_volume,
        "time_buckets": len(time_buckets),
        "peak_activity": {
            "hour": datetime.fromtimestamp(peak_bucket[0] * 3600).isoformat() if peak_bucket else None,
            "trade_count": len(peak_bucket[1]) if peak_bucket else 0
        },
        "wallets": list(wallets_in_market)
    }

def export_heatmap_json(filename="heatmap_data.json", hours_window=24):
    """Export heatmap data to JSON file"""
    data = generate_cluster_heatmap_data(hours_window)
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Heatmap data exported to {filename}")
    return filename

def get_top_clustered_markets(limit=10, hours_window=24):
    """Get top N most clustered markets"""
    heatmap_data = generate_cluster_heatmap_data(hours_window)
    return heatmap_data["markets"][:limit]
