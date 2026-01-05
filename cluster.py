import time
from config import CLUSTER_WINDOW_MIN

def detect_cluster(trades, current_trade):
    cutoff = current_trade["timestamp"] - (CLUSTER_WINDOW_MIN * 60)

    same_market = [
        t for t in trades
        if t["market"] == current_trade["market"]
        and t["timestamp"] >= cutoff
        and t["wallet"] != current_trade["wallet"]
        and t.get("outcome") == current_trade.get("outcome")
        and t["usd"] >= current_trade["usd"] * 0.8
    ]

    return len(same_market) >= 1
