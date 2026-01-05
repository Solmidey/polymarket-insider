"""
Risk Scoring Dashboard - Calculate and display risk scores for markets and wallets
"""
import json
from datetime import datetime, timedelta
from db import cur, conn
from analyzer import analyze_trade
from wallet_graph import find_shared_funding_clusters
from exit_tracking import get_wallet_exit_stats, detect_suspicious_exits

def calculate_market_risk_score(market_id, hours_window=24):
    """
    Calculate risk score for a market (0-100)
    
    Factors:
    - Number of suspicious trades
    - Wallet clustering
    - Trade size anomalies
    - Exit patterns
    """
    cutoff_timestamp = int((datetime.now() - timedelta(hours=hours_window)).timestamp())
    
    # Get trades for this market
    cur.execute("""
        SELECT wallet, usd, price, timestamp
        FROM trades
        WHERE market = ? AND timestamp >= ?
    """, (market_id, cutoff_timestamp))
    
    trades = cur.fetchall()
    
    if not trades:
        return {"risk_score": 0, "factors": {}}
    
    risk_factors = {
        "total_trades": len(trades),
        "unique_wallets": len(set(t[0] for t in trades)),
        "total_volume": sum(t[1] for t in trades),
        "suspicious_exits": 0,
        "wallet_clusters": 0,
        "size_anomalies": 0
    }
    
    # Check for suspicious exits
    suspicious_exits = detect_suspicious_exits(market_id)
    risk_factors["suspicious_exits"] = len(suspicious_exits)
    
    # Check for wallet clusters
    wallets_in_market = [t[0] for t in trades]
    clusters = find_shared_funding_clusters(min_shared=1)
    market_clusters = sum(1 for cluster in clusters if any(w in cluster for w in wallets_in_market))
    risk_factors["wallet_clusters"] = market_clusters
    
    # Calculate average trade size
    avg_trade_size = risk_factors["total_volume"] / risk_factors["total_trades"]
    
    # Count size anomalies (trades 3x+ average)
    risk_factors["size_anomalies"] = sum(
        1 for t in trades if t[1] >= (avg_trade_size * 3)
    )
    
    # Calculate risk score (0-100)
    risk_score = min(100, (
        (risk_factors["suspicious_exits"] * 15) +
        (risk_factors["wallet_clusters"] * 20) +
        (risk_factors["size_anomalies"] * 10) +
        (min(risk_factors["total_volume"] / 50000, 30)) +  # Volume factor
        (min(risk_factors["unique_wallets"] / 10, 25))  # Wallet diversity
    ))
    
    return {
        "risk_score": round(risk_score, 2),
        "risk_level": get_risk_level(risk_score),
        "factors": risk_factors,
        "market": market_id
    }

def calculate_wallet_risk_score(wallet_address):
    """
    Calculate risk score for a wallet (0-100)
    
    Factors:
    - Fresh wallet status
    - Exit patterns
    - Trade frequency
    - Association with clusters
    """
    # Get wallet stats
    cur.execute("""
        SELECT COUNT(*), SUM(usd), AVG(usd)
        FROM trades
        WHERE wallet = ?
    """, (wallet_address,))
    
    trade_stats = cur.fetchone()
    if not trade_stats or not trade_stats[0]:
        return {"risk_score": 0, "factors": {}}
    
    trade_count, total_volume, avg_trade_size = trade_stats
    
    # Get exit stats
    exit_stats = get_wallet_exit_stats(wallet_address)
    
    risk_factors = {
        "total_trades": trade_count,
        "total_volume": total_volume or 0,
        "avg_trade_size": avg_trade_size or 0,
        "exit_count": exit_stats["total_exits"] if exit_stats else 0,
        "avg_hold_time": exit_stats["avg_hold_time_hours"] if exit_stats else 0,
        "in_cluster": False
    }
    
    # Check if wallet is in a cluster
    clusters = find_shared_funding_clusters(min_shared=1)
    for cluster in clusters:
        if wallet_address in cluster:
            risk_factors["in_cluster"] = True
            break
    
    # Calculate risk score
    risk_score = min(100, (
        (min(trade_count / 10, 20)) +  # Trade frequency
        (min((total_volume or 0) / 20000, 25)) +  # Volume
        (15 if exit_stats and exit_stats["avg_hold_time_hours"] < 6 else 0) +  # Early exits
        (20 if risk_factors["in_cluster"] else 0) +  # Cluster membership
        (10 if avg_trade_size and avg_trade_size > 5000 else 0)  # Large trades
    ))
    
    return {
        "risk_score": round(risk_score, 2),
        "risk_level": get_risk_level(risk_score),
        "factors": risk_factors,
        "wallet": wallet_address
    }

def get_risk_level(score):
    """Convert risk score to level"""
    if score >= 70:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 30:
        return "MEDIUM"
    elif score >= 10:
        return "LOW"
    else:
        return "MINIMAL"

def generate_dashboard_data(hours_window=24):
    """Generate complete dashboard data"""
    cutoff_timestamp = int((datetime.now() - timedelta(hours=hours_window)).timestamp())
    
    # Get all active markets
    cur.execute("""
        SELECT DISTINCT market
        FROM trades
        WHERE timestamp >= ?
    """, (cutoff_timestamp,))
    
    markets = [row[0] for row in cur.fetchall()]
    
    # Get all active wallets
    cur.execute("""
        SELECT DISTINCT wallet
        FROM trades
        WHERE timestamp >= ?
    """, (cutoff_timestamp,))
    
    wallets = [row[0] for row in cur.fetchall()]
    
    # Calculate risk scores
    market_risks = []
    for market in markets:
        risk = calculate_market_risk_score(market, hours_window)
        market_risks.append(risk)
    
    wallet_risks = []
    for wallet in wallets[:50]:  # Limit to top 50 for performance
        risk = calculate_wallet_risk_score(wallet)
        wallet_risks.append(risk)
    
    # Sort by risk score
    market_risks.sort(key=lambda x: x["risk_score"], reverse=True)
    wallet_risks.sort(key=lambda x: x["risk_score"], reverse=True)
    
    # Calculate summary stats
    critical_markets = sum(1 for m in market_risks if m["risk_level"] == "CRITICAL")
    high_risk_wallets = sum(1 for w in wallet_risks if w["risk_level"] in ["CRITICAL", "HIGH"])
    
    return {
        "timestamp": int(datetime.now().timestamp()),
        "window_hours": hours_window,
        "summary": {
            "total_markets": len(markets),
            "critical_markets": critical_markets,
            "total_wallets": len(wallets),
            "high_risk_wallets": high_risk_wallets
        },
        "top_risk_markets": market_risks[:10],
        "top_risk_wallets": wallet_risks[:20],
        "all_markets": market_risks,
        "all_wallets": wallet_risks
    }

def display_dashboard(hours_window=24):
    """Display dashboard in console"""
    data = generate_dashboard_data(hours_window)
    
    print("=" * 80)
    print("POLYMARKET RISK SCORING DASHBOARD")
    print("=" * 80)
    print(f"\nTime Window: Last {hours_window} hours")
    print(f"Generated: {datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Markets: {data['summary']['total_markets']}")
    print(f"Critical Risk Markets: {data['summary']['critical_markets']}")
    print(f"Total Wallets: {data['summary']['total_wallets']}")
    print(f"High Risk Wallets: {data['summary']['high_risk_wallets']}")
    
    print("\n" + "=" * 80)
    print("TOP 10 RISK MARKETS")
    print("=" * 80)
    for i, market in enumerate(data['top_risk_markets'], 1):
        print(f"\n{i}. {market['market'][:50]}")
        print(f"   Risk Score: {market['risk_score']} ({market['risk_level']})")
        print(f"   Trades: {market['factors']['total_trades']} | "
              f"Wallets: {market['factors']['unique_wallets']} | "
              f"Volume: ${market['factors']['total_volume']:,.2f}")
        print(f"   Clusters: {market['factors']['wallet_clusters']} | "
              f"Suspicious Exits: {market['factors']['suspicious_exits']}")
    
    print("\n" + "=" * 80)
    print("TOP 20 RISK WALLETS")
    print("=" * 80)
    for i, wallet in enumerate(data['top_risk_wallets'], 1):
        print(f"\n{i}. {wallet['wallet'][:20]}...")
        print(f"   Risk Score: {wallet['risk_score']} ({wallet['risk_level']})")
        print(f"   Trades: {wallet['factors']['total_trades']} | "
              f"Volume: ${wallet['factors']['total_volume']:,.2f}")
        print(f"   In Cluster: {wallet['factors']['in_cluster']} | "
              f"Avg Hold: {wallet['factors']['avg_hold_time']:.1f}h")
    
    print("\n" + "=" * 80)
    
    return data

def export_dashboard_json(filename="risk_dashboard.json", hours_window=24):
    """Export dashboard data to JSON"""
    data = generate_dashboard_data(hours_window)
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Dashboard data exported to {filename}")
    return filename
