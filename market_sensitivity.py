"""
Market Sensitivity Ranking - Prioritize alerts by market type
Hardcoded priority levels:
1. Coups / War / Regime Change (CRITICAL)
2. Elections / Resignations (HIGH)
3. Sanctions / Arrests (MEDIUM-HIGH)
4. AI / Tech bans (MEDIUM)
5. Celebrity events (LOW)
"""
import re

# Priority 1: CRITICAL - Coups / War / Regime Change
CRITICAL_KEYWORDS = [
    "coup", "coup d'etat", "military coup", "regime change", "overthrow",
    "war", "invasion", "conflict", "military action", "armed conflict",
    "assassination", "assassinate", "killed", "murdered",
    "revolution", "uprising", "rebellion", "insurgency",
    "nuclear", "nuclear war", "nuclear weapon",
    "civil war", "civil unrest", "civil conflict"
]

# Priority 2: HIGH - Elections / Resignations
HIGH_KEYWORDS = [
    "election", "presidential election", "vote", "voting", "ballot",
    "resign", "resignation", "step down", "stepdown",
    "impeach", "impeachment", "removed from office",
    "prime minister", "president", "chancellor",
    "referendum", "plebiscite"
]

# Priority 3: MEDIUM-HIGH - Sanctions / Arrests
MEDIUM_HIGH_KEYWORDS = [
    "sanction", "sanctions", "embargo", "trade ban",
    "arrest", "arrested", "indictment", "indicted",
    "charges", "charged", "prosecution", "prosecute",
    "trial", "conviction", "sentenced",
    "freeze assets", "asset freeze", "seized"
]

# Priority 4: MEDIUM - AI / Tech bans
MEDIUM_KEYWORDS = [
    "ai ban", "artificial intelligence ban", "chatgpt ban", "openai ban",
    "tech ban", "technology ban", "export ban", "export control",
    "semiconductor", "chip ban", "chip export",
    "regulation", "regulate", "regulatory"
]

# Priority 5: LOW - Celebrity events
LOW_KEYWORDS = [
    "celebrity", "actor", "actress", "singer", "musician",
    "award", "oscar", "grammy", "emmy",
    "divorce", "marriage", "engagement",
    "death", "died", "passes away"
]

def get_market_sensitivity(market_question, market_category=""):
    """
    Get sensitivity ranking for a market
    
    Args:
        market_question: Market question text
        market_category: Market category (optional)
    
    Returns:
        Dict with:
            - priority: 1-5 (1 = highest priority)
            - level: "CRITICAL", "HIGH", "MEDIUM-HIGH", "MEDIUM", "LOW", "NORMAL"
            - score: 100-0 (100 = highest priority)
            - matched_keywords: List of matched keywords
    """
    if not market_question:
        return {
            "priority": 5,
            "level": "NORMAL",
            "score": 0,
            "matched_keywords": []
        }
    
    text = (market_question + " " + market_category).lower()
    matched_keywords = []
    
    # Check Priority 1: CRITICAL
    for keyword in CRITICAL_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            matched_keywords.append(keyword)
            return {
                "priority": 1,
                "level": "CRITICAL",
                "score": 100,
                "matched_keywords": matched_keywords
            }
    
    # Check Priority 2: HIGH
    for keyword in HIGH_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            matched_keywords.append(keyword)
            return {
                "priority": 2,
                "level": "HIGH",
                "score": 80,
                "matched_keywords": matched_keywords
            }
    
    # Check Priority 3: MEDIUM-HIGH
    for keyword in MEDIUM_HIGH_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            matched_keywords.append(keyword)
            return {
                "priority": 3,
                "level": "MEDIUM-HIGH",
                "score": 60,
                "matched_keywords": matched_keywords
            }
    
    # Check Priority 4: MEDIUM
    for keyword in MEDIUM_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            matched_keywords.append(keyword)
            return {
                "priority": 4,
                "level": "MEDIUM",
                "score": 40,
                "matched_keywords": matched_keywords
            }
    
    # Check Priority 5: LOW
    for keyword in LOW_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            matched_keywords.append(keyword)
            return {
                "priority": 5,
                "level": "LOW",
                "score": 20,
                "matched_keywords": matched_keywords
            }
    
    # Default: NORMAL priority
    return {
        "priority": 5,
        "level": "NORMAL",
        "score": 0,
        "matched_keywords": []
    }

def get_required_signals(sensitivity):
    """
    Get required number of signals based on market sensitivity
    
    Args:
        sensitivity: Sensitivity dict from get_market_sensitivity()
    
    Returns:
        Required number of signals:
        - Rank 1-2 (CRITICAL, HIGH): 1 signal
        - Rank 3 (MEDIUM-HIGH): 2 signals
        - Rank 4-5 (MEDIUM, LOW, NORMAL): 3 signals (stronger evidence)
    """
    priority = sensitivity["priority"]
    
    if priority <= 2:  # CRITICAL or HIGH
        return 1
    elif priority == 3:  # MEDIUM-HIGH
        return 2
    else:  # MEDIUM, LOW, or NORMAL (rank 4-5)
        return 3

def should_lower_alert_threshold(sensitivity):
    """
    Determine if alert threshold should be lowered for high-sensitivity markets
    
    Args:
        sensitivity: Sensitivity dict from get_market_sensitivity()
    
    Returns:
        True if threshold should be lowered (1 signal instead of 2)
    """
    # For CRITICAL and HIGH priority markets, lower threshold to 1 signal
    return sensitivity["priority"] <= 2

def get_sensitivity_emoji(level):
    """Get emoji for sensitivity level"""
    emoji_map = {
        "CRITICAL": "🔥",
        "HIGH": "⚠️",
        "MEDIUM-HIGH": "📊",
        "MEDIUM": "📈",
        "LOW": "💬",
        "NORMAL": "📝"
    }
    return emoji_map.get(level, "📝")
