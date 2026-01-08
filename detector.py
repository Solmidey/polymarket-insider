from db import is_fresh_wallet, mark_wallet_seen

# --------------------
# CONFIG
# --------------------

MIN_USD_SIZE = 2500
LOW_PROB_THRESHOLD = 0.15   # 15%
HIGH_CONFIDENCE_SCORE = 3   # signals required


# --------------------
# CORE DETECTOR
# --------------------

def detect_insider(trade):
    """
    Returns (is_suspicious: bool, signals: list[str])
    """

    signals = []

    # ---------
    # Validate fields
    # ---------
    size = trade.get("size")
    price = trade.get("price")
    wallet = trade.get("proxyWallet")
    title = trade.get("title", "")

    if not size or not price or not wallet:
        return False, []

    usd_size = size * price

    # ---------
    # SIGNAL 1: Large trade
    # ---------
    if usd_size >= MIN_USD_SIZE:
        signals.append("large_trade")

    # ---------
    # SIGNAL 2: Low probability entry
    # ---------
    if price <= LOW_PROB_THRESHOLD:
        signals.append("low_probability_entry")

    # ---------
    # SIGNAL 3: Fresh wallet
    # ---------
    if is_fresh_wallet(wallet):
        signals.append("fresh_wallet")

    # ---------
    # SIGNAL 4: Sensitive market keywords
    # ---------
    sensitive_keywords = [
        "election",
        "war",
        "military",
        "coup",
        "court",
        "sec",
        "indictment",
        "fed",
        "interest rate"
    ]

    title_lower = title.lower()
    if any(k in title_lower for k in sensitive_keywords):
        signals.append("high_sensitivity_market")

    # ---------
    # SCORE DECISION
    # ---------
    is_suspicious = len(signals) >= HIGH_CONFIDENCE_SCORE

    # ---------
    # Persist wallet behavior
    # ---------
    mark_wallet_seen(wallet, usd_size)

    return is_suspicious, signals


