"""
Exit Timing Tracking - Detect if wallets dump positions post-event
"""
import time
from db import cur, conn

def init_exit_tracking_tables():
    """Initialize tables for exit timing tracking"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet TEXT,
            market TEXT,
            outcome TEXT,
            entry_price REAL,
            entry_amount REAL,
            entry_timestamp INTEGER,
            exit_price REAL,
            exit_timestamp INTEGER,
            profit_loss REAL,
            exit_delay_hours REAL,
            status TEXT DEFAULT 'open'
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_events (
            market TEXT PRIMARY KEY,
            event_timestamp INTEGER,
            event_type TEXT,
            resolution_price REAL
        )
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_positions_wallet ON positions(wallet)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_positions_market ON positions(market)
    """)
    
    conn.commit()

def record_position(wallet, market, outcome, entry_price, entry_amount, timestamp):
    """Record a new position (buy trade)"""
    cur.execute("""
        INSERT INTO positions 
        (wallet, market, outcome, entry_price, entry_amount, entry_timestamp, status)
        VALUES (?, ?, ?, ?, ?, ?, 'open')
    """, (wallet, market, outcome, entry_price, entry_amount, timestamp))
    conn.commit()

def record_exit(wallet, market, outcome, exit_price, exit_timestamp):
    """Record an exit (sell trade) and close matching positions"""
    # Find matching open positions
    cur.execute("""
        SELECT id, entry_price, entry_amount, entry_timestamp
        FROM positions
        WHERE wallet = ? AND market = ? AND outcome = ? AND status = 'open'
        ORDER BY entry_timestamp ASC
    """, (wallet, market, outcome))
    
    positions = cur.fetchall()
    
    if not positions:
        return None
    
    # Close the oldest matching position (FIFO)
    pos_id, entry_price, entry_amount, entry_timestamp = positions[0]
    
    # Calculate profit/loss
    profit_loss = (exit_price - entry_price) * entry_amount
    
    # Calculate exit delay (hours after entry)
    exit_delay_hours = (exit_timestamp - entry_timestamp) / 3600
    
    # Update position
    cur.execute("""
        UPDATE positions
        SET exit_price = ?,
            exit_timestamp = ?,
            profit_loss = ?,
            exit_delay_hours = ?,
            status = 'closed'
        WHERE id = ?
    """, (exit_price, exit_timestamp, profit_loss, exit_delay_hours, pos_id))
    
    conn.commit()
    
    return {
        "position_id": pos_id,
        "profit_loss": profit_loss,
        "exit_delay_hours": exit_delay_hours,
        "entry_price": entry_price,
        "exit_price": exit_price
    }

def record_market_event(market, event_timestamp, event_type="resolution", resolution_price=None):
    """Record a market event (resolution, major news, etc.)"""
    cur.execute("""
        INSERT OR REPLACE INTO market_events
        (market, event_timestamp, event_type, resolution_price)
        VALUES (?, ?, ?, ?)
    """, (market, event_timestamp, event_type, resolution_price))
    conn.commit()

def detect_suspicious_exits(market, hours_before_event=24, hours_after_event=48):
    """
    Detect wallets that exited positions suspiciously close to market events
    
    Args:
        market: Market ID to check
        hours_before_event: Flag exits within this many hours before event
        hours_after_event: Flag exits within this many hours after event
    
    Returns:
        List of suspicious exit records
    """
    # Get market event timestamp
    cur.execute("""
        SELECT event_timestamp, event_type
        FROM market_events
        WHERE market = ?
    """, (market,))
    event_data = cur.fetchone()
    
    if not event_data:
        return []
    
    event_timestamp, event_type = event_data
    
    # Find exits near the event
    time_before = event_timestamp - (hours_before_event * 3600)
    time_after = event_timestamp + (hours_after_event * 3600)
    
    cur.execute("""
        SELECT wallet, outcome, entry_price, exit_price, profit_loss,
               exit_timestamp, exit_delay_hours
        FROM positions
        WHERE market = ? 
        AND status = 'closed'
        AND exit_timestamp >= ? 
        AND exit_timestamp <= ?
        ORDER BY exit_timestamp
    """, (market, time_before, time_after))
    
    suspicious_exits = []
    for row in cur.fetchall():
        wallet, outcome, entry_price, exit_price, profit_loss, exit_timestamp, exit_delay_hours = row
        
        # Calculate time relative to event
        hours_from_event = (exit_timestamp - event_timestamp) / 3600
        
        suspicious_exits.append({
            "wallet": wallet,
            "outcome": outcome,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "profit_loss": profit_loss,
            "exit_timestamp": exit_timestamp,
            "exit_delay_hours": exit_delay_hours,
            "hours_from_event": hours_from_event,
            "event_type": event_type
        })
    
    return suspicious_exits

def get_wallet_exit_stats(wallet):
    """Get exit timing statistics for a wallet"""
    cur.execute("""
        SELECT 
            COUNT(*) as total_exits,
            AVG(exit_delay_hours) as avg_hold_time,
            SUM(profit_loss) as total_profit_loss,
            AVG(profit_loss) as avg_profit_loss
        FROM positions
        WHERE wallet = ? AND status = 'closed'
    """, (wallet,))
    
    result = cur.fetchone()
    if not result or not result[0]:
        return None
    
    return {
        "total_exits": result[0],
        "avg_hold_time_hours": result[1] or 0,
        "total_profit_loss": result[2] or 0,
        "avg_profit_loss": result[3] or 0
    }

def check_early_exit_pattern(wallet, market):
    """
    Check if wallet has pattern of exiting positions very quickly (potential insider)
    
    Returns:
        True if wallet has suspicious early exit pattern
    """
    cur.execute("""
        SELECT AVG(exit_delay_hours), COUNT(*)
        FROM positions
        WHERE wallet = ? AND market = ? AND status = 'closed'
    """, (wallet, market))
    
    result = cur.fetchone()
    if not result or not result[1]:
        return False
    
    avg_hold_time, exit_count = result[1], result[0]
    
    # Suspicious if average hold time < 6 hours and multiple exits
    return avg_hold_time < 6 and exit_count >= 2
