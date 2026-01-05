import sqlite3

conn = sqlite3.connect("polymarket.db", check_same_thread=False)
cur = conn.cursor()

def init_db():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS wallets (
        address TEXT PRIMARY KEY,
        first_seen INTEGER,
        total_trades INTEGER,
        total_volume REAL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id TEXT PRIMARY KEY,
        wallet TEXT,
        market TEXT,
        usd REAL,
        price REAL,
        timestamp INTEGER
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS state (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
        market TEXT,
        wallet TEXT,
        fired_timestamp INTEGER,
        fired_price REAL,
        signals TEXT,
        peak_price REAL,
        peak_timestamp INTEGER,
        outcome TEXT,
        outcome_timestamp INTEGER,
        hours_to_outcome REAL,
        price_change REAL,
        peak_price_change REAL,
        profit_loss REAL,
        is_correct BOOLEAN,
        status TEXT DEFAULT 'pending'
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_alerts_market ON alerts(market)
    """)
    
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)
    """)

    conn.commit()

def get_last_timestamp():
    """Get the timestamp of the last processed trade"""
    cur.execute("SELECT value FROM state WHERE key = 'last_timestamp'")
    result = cur.fetchone()
    return int(result[0]) if result and result[0] else 0

def set_last_timestamp(timestamp):
    """Update the last processed timestamp"""
    cur.execute("""
        INSERT OR REPLACE INTO state (key, value) 
        VALUES ('last_timestamp', ?)
    """, (str(timestamp),))
    conn.commit()
