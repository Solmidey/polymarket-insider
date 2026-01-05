"""
Sanity Filter - Reduce false positives by filtering out noise
Blocks alerts when:
1. Market liquidity is tiny
2. Odds jump on one trade only
3. Wallet is known high-frequency trader
"""
import time
from datetime import datetime, timedelta
from db import cur, conn
from config import MIN_MARKET_LIQUIDITY, MAX_PRICE_JUMP_SINGLE_TRADE, HIGH_FREQ_TRADER_THRESHOLD

def init_sanity_filter_tables():
    """Initialize tables for tracking filtered alerts"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS filtered_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT,
            wallet TEXT,
            signals TEXT,
            filter_reason TEXT,
            timestamp INTEGER
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallet_trade_frequency (
            wallet TEXT PRIMARY KEY,
            trades_last_24h INTEGER,
            last_updated INTEGER
        )
    """)
    
    conn.commit()

def check_market_liquidity(market_id, market_data):
    """
    Check if market has sufficient liquidity
    
    Args:
        market_id: Market ID
        market_data: Market data from trade (includes liquidity field)
    
    Returns:
        Tuple of (is_valid, reason)
    """
    liquidity_str = market_data.get("market_liquidity") or market_data.get("market", {}).get("liquidity", "0")
    
    try:
        liquidity = float(liquidity_str)
    except (ValueError, TypeError):
        # If liquidity not available, check recent trade volume
        cur.execute("""
            SELECT SUM(usd) FROM trades 
            WHERE market = ? AND timestamp >= ?
        """, (market_id, int(time.time()) - 86400))
        result = cur.fetchone()
        liquidity = result[0] if result and result[0] else 0
    
    if liquidity < MIN_MARKET_LIQUIDITY:
        return False, f"Market liquidity too low: ${liquidity:,.0f} < ${MIN_MARKET_LIQUIDITY:,.0f}"
    
    return True, None

def check_price_jump_single_trade(market_id, current_price, current_trade_usd, recent_trades):
    """
    Check if odds jumped significantly on just one trade
    
    Args:
        market_id: Market ID
        current_price: Price of current trade
        current_trade_usd: Size of current trade
        recent_trades: List of recent trades for this market
    
    Returns:
        Tuple of (is_valid, reason)
    """
    if not recent_trades or len(recent_trades) < 2:
        return True, None  # Not enough data to check
    
    # Get prices before current trade
    prices_before = [t.get("price", 0) for t in recent_trades if t.get("market") == market_id]
    
    if not prices_before:
        return True, None
    
    # Calculate average price before this trade
    avg_price_before = sum(prices_before) / len(prices_before)
    
    # Check if price jumped significantly
    price_change = abs(current_price - avg_price_before)
    
    if price_change > MAX_PRICE_JUMP_SINGLE_TRADE:
        # Check if this single trade caused the jump
        # If current trade is much larger than recent average, it might be the cause
        recent_avg_size = sum(t.get("usd", 0) for t in recent_trades) / len(recent_trades)
        
        if current_trade_usd > recent_avg_size * 5:  # 5x larger than average
            return False, f"Price jumped {price_change*100:.1f}% on single large trade (${current_trade_usd:,.0f})"
    
    return True, None

def is_high_frequency_trader(wallet_address):
    """
    Check if wallet is a high-frequency trader
    
    Args:
        wallet_address: Wallet address to check
    
    Returns:
        Tuple of (is_hft, reason)
    """
    # Check cached frequency
    cur.execute("""
        SELECT trades_last_24h, last_updated
        FROM wallet_trade_frequency
        WHERE wallet = ?
    """, (wallet_address,))
    
    result = cur.fetchone()
    
    if result:
        trades_count, last_updated = result
        # Use cached value if less than 1 hour old
        if last_updated and (time.time() - last_updated) < 3600:
            if trades_count >= HIGH_FREQ_TRADER_THRESHOLD:
                return True, f"High-frequency trader: {trades_count} trades in last 24h"
            return False, None
    
    # Calculate fresh frequency
    cutoff = int(time.time()) - 86400  # Last 24 hours
    
    cur.execute("""
        SELECT COUNT(*) FROM trades
        WHERE wallet = ? AND timestamp >= ?
    """, (wallet_address, cutoff))
    
    result = cur.fetchone()
    trades_count = result[0] if result else 0
    
    # Update cache
    cur.execute("""
        INSERT OR REPLACE INTO wallet_trade_frequency
        (wallet, trades_last_24h, last_updated)
        VALUES (?, ?, ?)
    """, (wallet_address, trades_count, int(time.time())))
    conn.commit()
    
    if trades_count >= HIGH_FREQ_TRADER_THRESHOLD:
        return True, f"High-frequency trader: {trades_count} trades in last 24h"
    
    return False, None

def sanity_check(trade, signals, recent_trades):
    """
    Run all sanity checks on an alert
    
    Args:
        trade: Trade data
        signals: List of signals that fired
        recent_trades: Recent trades for context
    
    Returns:
        Tuple of (should_alert, filter_reason)
        should_alert: True if alert should be sent, False if filtered
        filter_reason: Reason for filtering (None if passed)
    """
    market_id = trade.get("market", "")
    wallet_address = trade.get("wallet") or trade.get("trader", "")
    current_price = float(trade.get("price", 0))
    current_trade_usd = float(trade.get("usd", 0) or trade.get("amountUSD", 0))
    
    # Check 1: Market liquidity
    is_valid, reason = check_market_liquidity(market_id, trade)
    if not is_valid:
        return False, reason
    
    # Check 2: Price jump on single trade
    is_valid, reason = check_price_jump_single_trade(market_id, current_price, current_trade_usd, recent_trades)
    if not is_valid:
        return False, reason
    
    # Check 3: High-frequency trader
    is_hft, reason = is_high_frequency_trader(wallet_address)
    if is_hft:
        return False, reason
    
    # All checks passed
    return True, None

def record_filtered_alert(market, wallet, signals, filter_reason):
    """Record an alert that was filtered out"""
    signals_str = "|".join(signals)
    cur.execute("""
        INSERT INTO filtered_alerts
        (market, wallet, signals, filter_reason, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (market, wallet, signals_str, filter_reason, int(time.time())))
    conn.commit()

def get_filter_stats():
    """Get statistics on filtered alerts"""
    cur.execute("""
        SELECT 
            COUNT(*) as total_filtered,
            COUNT(DISTINCT filter_reason) as unique_reasons
        FROM filtered_alerts
    """)
    
    result = cur.fetchone()
    if not result or not result[0]:
        return None
    
    total, unique_reasons = result
    
    # Get breakdown by reason
    cur.execute("""
        SELECT filter_reason, COUNT(*) as count
        FROM filtered_alerts
        GROUP BY filter_reason
        ORDER BY count DESC
    """)
    
    reasons = cur.fetchall()
    
    return {
        "total_filtered": total,
        "unique_reasons": unique_reasons,
        "breakdown": [{"reason": r[0], "count": r[1]} for r in reasons]
    }
