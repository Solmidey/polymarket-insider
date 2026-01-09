# confidence.py

SIGNAL_WEIGHTS = {
    "fresh_wallet": 25,
    "large_trade": 30,
    "low_probability_entry": 20,
    "high_sensitivity_market": 15,
    "clustered_activity": 25,
    "test_mode": 0,
}

MAX_SCORE = 100


def compute_confidence(signals: list) -> int:
    """
    Compute confidence score (0–100) based on triggered signals.
    """
    score = 0

    for s in signals:
        score += SIGNAL_WEIGHTS.get(s, 0)

    return min(score, MAX_SCORE)
