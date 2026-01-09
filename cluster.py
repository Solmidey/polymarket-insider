import time
from db import get_conn
from config import (
    CLUSTER_TIME_WINDOW_MIN,
    CLUSTER_MIN_WALLETS,
    CLUSTER_MIN_TOTAL_USD
)

def detect_cluster(market: str):
    """
    Returns True if clustered wallet activity is detected for a market.
    """
    since_ts = int(time.time()) - (CLUSTER_TIME_WINDOW_MIN * 60)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT wallet, SUM(usd)
        FROM trades
        WHERE market = ?
          AND timestamp >= ?
        GROUP BY wallet
    """, (market, since_ts))

    rows = cur.fetchall()
    conn.close()

    unique_wallets = len(rows)
    total_usd = sum(r[1] for r in rows)

    if unique_wallets >= CLUSTER_MIN_WALLETS and total_usd >= CLUSTER_MIN_TOTAL_USD:
        return True, {
            "wallets": unique_wallets,
            "total_usd": total_usd
        }

    return False, None
