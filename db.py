import sqlite3
import time

DB_PATH = "polymarket.db"


# ======================
# CONNECTION
# ======================

def get_conn():
    """
    Always return a new connection.
    Safer for multithreaded / async environments.
    """
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ======================
# INITIALIZATION
# ======================

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Wallet tracking (fresh wallet detection)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            address TEXT PRIMARY KEY,
            first_seen INTEGER,
            total_trades INTEGER DEFAULT 0,
            total_volume REAL DEFAULT 0
        )
    """)

    # Raw trades storage (optional but useful)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            wallet TEXT,
            market TEXT,
            usd REAL,
            price REAL,
            timestamp INTEGER
        )
    """)

    # Global state (last processed timestamp, etc.)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Alerts + post-event evaluation
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
        CREATE INDEX IF NOT EXISTS idx_alerts_market
        ON alerts(market)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_status
        ON alerts(status)
    """)

    conn.commit()
    conn.close()


# ======================
# STATE HELPERS
# ======================

def get_last_timestamp() -> int:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT value FROM state WHERE key = 'last_timestamp'")
    row = cur.fetchone()

    conn.close()
    return int(row[0]) if row and row[0] else 0


def set_last_timestamp(timestamp: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO state (key, value)
        VALUES ('last_timestamp', ?)
    """, (str(timestamp),))

    conn.commit()
    conn.close()


# ======================
# WALLET HELPERS (CRITICAL)
# ======================

def is_fresh_wallet(wallet: str) -> bool:
    """
    Returns True if wallet has never been seen before.
    """
    if not wallet:
        return False

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT address FROM wallets WHERE address = ?",
        (wallet,)
    )
    row = cur.fetchone()

    conn.close()
    return row is None


def mark_wallet_seen(wallet: str, usd: float, timestamp: int | None = None):
    """
    Records wallet activity and updates trade count + volume.
    """
    if not wallet:
        return

    if timestamp is None:
        timestamp = int(time.time())

    conn = get_conn()
    cur = conn.cursor()

    # Insert if first time
    cur.execute("""
        INSERT OR IGNORE INTO wallets (address, first_seen, total_trades, total_volume)
        VALUES (?, ?, 0, 0)
    """, (wallet, timestamp))

    # Update stats
    cur.execute("""
        UPDATE wallets
        SET
            total_trades = total_trades + 1,
            total_volume = total_volume + ?
        WHERE address = ?
    """, (usd, wallet))

    conn.commit()
    conn.close()


# ======================
# OPTIONAL HELPERS
# ======================

def get_wallet_stats(wallet: str):
    """
    Returns wallet stats for analysis / scoring.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT first_seen, total_trades, total_volume
        FROM wallets
        WHERE address = ?
    """, (wallet,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "first_seen": row[0],
        "total_trades": row[1],
        "total_volume": row[2],
    }

