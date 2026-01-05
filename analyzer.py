import time
from config import FRESH_WALLET_DAYS, LARGE_BET_USD, CLUSTER_WINDOW_MIN
from wallet_graph import are_wallets_related, get_wallet_cluster
from exit_tracking import check_early_exit_pattern, detect_suspicious_exits

def is_fresh(wallet):
    """S1: Check if wallet is fresh (first seen within FRESH_WALLET_DAYS)"""
    if not wallet or not wallet.get("first_seen"):
        return True  # New wallet, definitely fresh
    age_days = (time.time() - wallet["first_seen"]) / 86400
    return age_days < FRESH_WALLET_DAYS

def check_size_anomaly(trade_usd, market_avg_usd):
    """S2: Check if trade size is far above normal for that market"""
    if not market_avg_usd or market_avg_usd == 0:
        return False
    return trade_usd >= (market_avg_usd * 3)

def is_sensitive_market(market_prob, market_category):
    """S3: Check if market is sensitive with tight probability"""
    sensitive_categories = ["POLITICS", "WAR", "GEOPOLITICS"]
    is_tight = market_prob < 0.15 or market_prob > 0.85
    return is_tight and market_category in sensitive_categories

def check_temporal_clustering(recent_wallet_count):
    """S4: Check if multiple wallets bet on same outcome in short time window"""
    return recent_wallet_count >= 3

def check_shared_funding(wallet_address, recent_wallets):
    """S5: Check if wallet shares funding sources with other recent traders"""
    if not recent_wallets:
        return False
    
    wallet_address = wallet_address or ""
    for other_wallet in recent_wallets:
        if other_wallet and other_wallet != wallet_address:
            if are_wallets_related(wallet_address, other_wallet):
                return True
    return False

def analyze_trade(trade, wallet, market_stats, recent_wallets=None):
    """Analyze a single trade and return which signals fired"""
    signals = []
    
    # Handle both normalized and raw trade formats
    trade_usd = float(trade.get("amountUSD") or trade.get("usd", 0))
    market_prob = float(trade.get("price", 0))
    market_category = trade.get("market_category") or trade.get("market", {}).get("category", "")
    wallet_address = trade.get("trader") or trade.get("wallet", "")
    
    # S1: Fresh Wallet, Big Bet
    if is_fresh(wallet) and trade_usd >= LARGE_BET_USD:
        signals.append("FRESH_WALLET_BIG_BET")
    
    # S2: Size Anomaly
    market_avg_usd = market_stats.get("avg_usd", 0)
    if check_size_anomaly(trade_usd, market_avg_usd):
        signals.append("SIZE_ANOMALY")
    
    # S3: Sensitive Market Focus
    if is_sensitive_market(market_prob, market_category):
        signals.append("TIGHT_SENSITIVE_MARKET")
    
    # S4: Temporal Clustering
    recent_wallet_count = market_stats.get("recent_wallet_count", 0)
    if check_temporal_clustering(recent_wallet_count):
        signals.append("TEMPORAL_CLUSTERING")
    
    # S5: Shared Funding (Wallet Graph Analysis)
    if recent_wallets and check_shared_funding(wallet_address, recent_wallets):
        signals.append("SHARED_FUNDING_SOURCE")
    
    # S6: Early Exit Pattern (Exit Timing)
    market_id = trade.get("market") or trade.get("market", {}).get("id", "")
    if market_id and check_early_exit_pattern(wallet_address, market_id):
        signals.append("EARLY_EXIT_PATTERN")
    
    return signals
