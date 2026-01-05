import time
from db import init_db, cur, conn
from fetch import fetch_trades
from analyzer import analyze_trade
from alerts import send_alert
from cluster import detect_cluster
from config import CLUSTER_WINDOW_MIN
from wallet_graph import init_wallet_graph_tables, add_funding_source
from exit_tracking import init_exit_tracking_tables, record_position, record_exit, detect_suspicious_exits
from narratives import save_narratives
from post_event_review import record_alert
from sanity_filter import init_sanity_filter_tables, sanity_check, record_filtered_alert
from market_sensitivity import get_market_sensitivity, get_required_signals

def load_or_create_wallet(t):
    wallet_address = t.get("trader") or t.get("wallet")
    
    cur.execute("SELECT first_seen FROM wallets WHERE address = ?", (wallet_address,))
    result = cur.fetchone()
    
    if result:
        return {"first_seen": result[0]}
    else:
        first_seen = int(time.time())
        cur.execute("INSERT INTO wallets (address, first_seen, total_trades, total_volume) VALUES (?, ?, 0, 0)",
                   (wallet_address, first_seen))
        conn.commit()
        return {"first_seen": first_seen}

def normalize_trade(trade):
    """Convert GraphQL trade format to internal format"""
    market = trade.get("market", {})
    return {
        "id": trade.get("id"),
        "trader": trade.get("trader"),
        "wallet": trade.get("trader"),  # Alias for alerts
        "market": market.get("id", ""),
        "market_question": market.get("question", ""),
        "market_category": market.get("category", ""),
        "market_conditionId": market.get("conditionId", ""),
        "market_endDate": market.get("endDate", ""),
        "market_liquidity": market.get("liquidity", "0"),
        "amountUSD": float(trade.get("amountUSD", 0)),
        "usd": float(trade.get("amountUSD", 0)),  # Alias for alerts
        "price": float(trade.get("price", 0)),
        "timestamp": int(trade.get("timestamp", 0)),
        "outcome": trade.get("outcome", ""),
        "transactionHash": trade.get("transactionHash", "")
    }

def get_recent_wallets_for_analysis(all_trades, current_trade, window_minutes=120):
    """Get list of recent wallet addresses for wallet graph analysis"""
    cutoff = current_trade["timestamp"] - (window_minutes * 60)
    recent_wallets = []
    for t in all_trades:
        if t.get("timestamp", 0) >= cutoff:
            wallet = t.get("wallet") or t.get("trader")
            if wallet:
                recent_wallets.append(wallet)
    return recent_wallets

def get_market_stats(market_id, all_trades, current_trade):
    """Get market statistics for analysis"""
    # Get average trade size for this market
    cur.execute("SELECT AVG(usd) FROM trades WHERE market = ?", (market_id,))
    result = cur.fetchone()
    avg_usd = result[0] if result and result[0] else 0
    
    # Count recent wallets for clustering (S4)
    recent_wallet_count = 0
    if all_trades:
        cutoff = current_trade["timestamp"] - (CLUSTER_WINDOW_MIN * 60)
        recent_wallets = set()
        for t in all_trades:
            if (t.get("market") == market_id 
                and t.get("timestamp", 0) >= cutoff
                and t.get("outcome") == current_trade.get("outcome")):
                recent_wallets.add(t.get("wallet") or t.get("trader"))
        recent_wallet_count = len(recent_wallets)
    
    return {
        "avg_usd": avg_usd,
        "recent_wallet_count": recent_wallet_count
    }

def store_trade(trade):
    """Store trade in database"""
    try:
        cur.execute("""
            INSERT OR IGNORE INTO trades (id, wallet, market, usd, price, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            trade.get("id"),
            trade.get("wallet") or trade.get("trader"),
            trade.get("market"),
            trade.get("usd") or trade.get("amountUSD", 0),
            trade.get("price", 0),
            trade.get("timestamp", 0)
        ))
        conn.commit()
    except Exception as e:
        print(f"Error storing trade: {e}")

def determine_trade_direction(trade):
    """
    Determine if trade is a buy (entry) or sell (exit)
    Simplified: if price is low (<0.5), likely buying YES, if high (>0.5), likely selling
    In production, you'd check actual position changes
    """
    price = float(trade.get("price", 0.5))
    # This is a heuristic - in production, check actual position deltas
    # For now, assume trades at low prices are entries, high prices are exits
    return "entry" if price < 0.5 else "exit"

def run():
    init_db()
    init_wallet_graph_tables()
    init_exit_tracking_tables()
    init_sanity_filter_tables()
    
    # Fetch only new trades since last run
    raw_trades = fetch_trades()
    
    if not raw_trades:
        print("No new trades to process")
        return
    
    print(f"Processing {len(raw_trades)} new trades...")
    
    # Normalize all trades
    trades = [normalize_trade(t) for t in raw_trades]
    
    for t in trades:
        # Store trade in DB
        store_trade(t)
        
        # Load or create wallet
        wallet = load_or_create_wallet(t)
        wallet_address = t.get("wallet") or t.get("trader")
        market_id = t.get("market", "")
        outcome = t.get("outcome", "")
        price = float(t.get("price", 0))
        amount = float(t.get("usd", 0))
        timestamp = int(t.get("timestamp", 0))
        
        # Track funding sources (placeholder - can be extended with blockchain API)
        if t.get("transactionHash"):
            add_funding_source(wallet_address, f"tx_{t.get('transactionHash')[:10]}", 
                             amount, timestamp)
        
        # Track positions and exits
        trade_direction = determine_trade_direction(t)
        if trade_direction == "entry":
            record_position(wallet_address, market_id, outcome, price, amount, timestamp)
        else:
            exit_info = record_exit(wallet_address, market_id, outcome, price, timestamp)
            if exit_info:
                # Check for suspicious exit timing
                suspicious = detect_suspicious_exits(market_id)
                if suspicious:
                    print(f"Suspicious exit detected: {wallet_address} exited {market_id}")
        
        # Get market stats
        market_stats = get_market_stats(market_id, trades, t)
        
        # Get recent wallets for wallet graph analysis
        recent_wallets = get_recent_wallets_for_analysis(trades, t)
        
        # Analyze trade
        signals = analyze_trade(t, wallet, market_stats, recent_wallets)
        
        # Get market sensitivity
        market_question = t.get("market_question", "")
        market_category = t.get("market_category", "")
        sensitivity = get_market_sensitivity(market_question, market_category)
        
        # Determine alert threshold based on sensitivity
        # Rank 1-2 (CRITICAL/HIGH): 1 signal required
        # Rank 3 (MEDIUM-HIGH): 2 signals required
        # Rank 4-5 (MEDIUM/LOW/NORMAL): 3 signals required (stronger evidence)
        required_signals = get_required_signals(sensitivity)
        
        # Log signal analysis
        if len(signals) > 0:
            print(f"Signals detected: {len(signals)}/{required_signals} required for {sensitivity['level']} market - {signals}")
        
        # Send alert if threshold met
        if len(signals) >= required_signals:
            print(f"✅ Alert triggered: {len(signals)} signals (required: {required_signals}) - {signals}")
            
            # SANITY FILTER - Reduce false positives
            should_alert, filter_reason = sanity_check(t, signals, trades)
            
            if not should_alert:
                print(f"⚠️  Alert FILTERED: {filter_reason}")
                record_filtered_alert(market_id, wallet_address, signals, filter_reason)
                continue  # Skip this alert
            
            print(f"✅ Alert passed sanity filter")
            print(f"📊 Market Sensitivity: {sensitivity['level']} (Priority {sensitivity['priority']})")
            send_alert(t, signals)
            
            # Record alert for post-event review
            alert_id = record_alert(
                market=market_id,
                wallet=wallet_address,
                fired_timestamp=timestamp,
                fired_price=price,
                signals=signals
            )
            print(f"Alert recorded (ID: {alert_id}) for post-event review")
            
            # Generate narratives for social media
            alert_data = {
                "trade": t,
                "signals": signals,
                "wallet": wallet_address,
                "market": market_id
            }
            save_narratives(alert_data)

if __name__ == "__main__":
    run()
