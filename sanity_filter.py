def sanity_check_trade(trade):
    """
    Lightweight validation to reject malformed or useless trades
    This should NEVER touch the database.
    """

    required_fields = [
        "proxyWallet",
        "size",
        "price",
        "title",
        "timestamp"
    ]

    for field in required_fields:
        if field not in trade:
            return False

    # Reject zero or negative trades
    if trade["size"] <= 0:
        return False

    if trade["price"] <= 0 or trade["price"] >= 1:
        return False

    # Reject empty or junk titles
    if not trade["title"] or len(trade["title"]) < 10:
        return False

    # Reject obviously tiny noise trades
    usd_value = trade["size"] * trade["price"]
    if usd_value < 5:
        return False

    return True
