"""
Auto-generate Twitter/YouTube/Telegram content from alerts
Content Trigger - Automatically generates compelling hooks and drafts
"""
from datetime import datetime
from market_sensitivity import get_market_sensitivity, get_sensitivity_emoji

def generate_compelling_hook(trade, signals, sensitivity):
    """
    Generate a compelling hook like: 
    "Polymarket is pricing a 7% chance of X — and multiple new wallets just piled in. That's not random."
    """
    market = trade.get("market_question", "Unknown Market")
    price = trade.get("price", 0)
    price_percent = price * 100
    
    # Count fresh wallets signal
    has_fresh_wallets = "FRESH_WALLET_BIG_BET" in signals
    has_clustering = "TEMPORAL_CLUSTERING" in signals
    signal_count = len(signals)
    
    # Build hook based on signals
    if has_fresh_wallets and has_clustering:
        hook = f"Polymarket is pricing a {price_percent:.1f}% chance of {market[:60]}...\n\nAnd multiple new wallets just piled in.\n\nThat's not random."
    elif has_fresh_wallets:
        hook = f"Polymarket is pricing a {price_percent:.1f}% chance of {market[:60]}...\n\nA brand new wallet just placed a massive bet.\n\nThat's not random."
    elif has_clustering:
        hook = f"Polymarket is pricing a {price_percent:.1f}% chance of {market[:60]}...\n\nMultiple wallets just coordinated bets in minutes.\n\nThat's not random."
    else:
        hook = f"Polymarket is pricing a {price_percent:.1f}% chance of {market[:60]}...\n\n{signal_count} suspicious signals just fired.\n\nThat's not random."
    
    return hook

def generate_twitter_thread(alert_data):
    """
    Generate a Twitter thread from alert data
    
    Args:
        alert_data: Dictionary containing alert information
    
    Returns:
        List of tweet strings (thread)
    """
    trade = alert_data.get("trade", {})
    signals = alert_data.get("signals", [])
    wallet = trade.get("wallet", "Unknown")
    market = trade.get("market_question", "Unknown Market")
    amount = trade.get("usd", 0)
    price = trade.get("price", 0)
    
    # Get sensitivity
    market_category = trade.get("market_category", "")
    sensitivity = get_market_sensitivity(market, market_category)
    emoji = get_sensitivity_emoji(sensitivity['level'])
    
    thread = []
    
    # Tweet 1: Compelling Hook
    hook = generate_compelling_hook(trade, signals, sensitivity)
    thread.append(hook)
    
    # Tweet 2: The Evidence
    signal_descriptions = {
        "FRESH_WALLET_BIG_BET": "New wallet, big bet",
        "SIZE_ANOMALY": "Trade size anomaly",
        "TIGHT_SENSITIVE_MARKET": "Sensitive market focus",
        "TEMPORAL_CLUSTERING": "Coordinated timing",
        "SHARED_FUNDING_SOURCE": "Shared funding",
        "EARLY_EXIT_PATTERN": "Early exit pattern"
    }
    
    signal_list = "\n• ".join([signal_descriptions.get(s, s) for s in signals])
    thread.append(
        f"{emoji} {sensitivity['level']} PRIORITY\n\n"
        f"Red flags detected:\n"
        f"• {signal_list}\n\n"
        f"{len(signals)} signals fired simultaneously."
    )
    
    # Tweet 3: The Numbers
    thread.append(
        f"💰 THE TRADE:\n\n"
        f"• ${amount:,.0f} bet\n"
        f"• {price*100:.1f}¢ entry price\n"
        f"• Wallet: {wallet[:15]}...\n\n"
        f"Pattern suggests insider information."
    )
    
    # Tweet 4: Why This Matters
    thread.append(
        f"🔍 WHY THIS MATTERS:\n\n"
        f"When {len(signals)} signals fire together, it's rarely coincidence.\n\n"
        f"We're tracking this wallet and market movement.\n\n"
        f"#Polymarket #PredictionMarkets"
    )
    
    return thread

def generate_youtube_short_hook(alert_data):
    """
    Generate a YouTube Short hook (punchy, 15-30 seconds)
    
    Args:
        alert_data: Dictionary containing alert information
    
    Returns:
        String with short hook script
    """
    trade = alert_data.get("trade", {})
    signals = alert_data.get("signals", [})
    market = trade.get("market_question", "Unknown Market")
    price = trade.get("price", 0)
    amount = trade.get("usd", 0)
    
    hook = generate_compelling_hook(trade, signals, {})
    
    script = f"""
# YOUTUBE SHORT HOOK (15-30 seconds)

## HOOK (0:00 - 0:05)
{hook}

## THE EVIDENCE (0:05 - 0:20)
{len(signals)} suspicious signals just fired on Polymarket.

A ${amount:,.0f} bet at {price*100:.1f}¢ triggered our insider trading detection.

This isn't random trading behavior.

## CALL TO ACTION (0:20 - 0:30)
Follow for more real-time alerts on prediction market anomalies.

#Polymarket #InsiderTrading #Crypto
"""
    
    return script.strip()

def generate_youtube_script(alert_data):
    """
    Generate a YouTube video script from alert data
    
    Args:
        alert_data: Dictionary containing alert information
    
    Returns:
        String containing full script
    """
    trade = alert_data.get("trade", {})
    signals = alert_data.get("signals", [})
    wallet = trade.get("wallet", "Unknown")
    market = trade.get("market_question", "Unknown Market")
    amount = trade.get("usd", 0)
    price = trade.get("price", 0)
    timestamp = trade.get("timestamp", 0)
    
    date_str = datetime.fromtimestamp(timestamp).strftime("%B %d, %Y at %I:%M %p") if timestamp else "Recently"
    
    script = f"""
# POLYMARKET INSIDER TRADING ALERT - {date_str}

## INTRO (0:00 - 0:30)
Hey everyone, welcome back. We just detected something very suspicious on Polymarket.

A wallet just made a massive bet that triggered our insider trading detection system. 
Let me break down exactly what we found.

## THE ALERT (0:30 - 1:30)
At {date_str}, wallet address {wallet} placed a ${amount:,.2f} bet on the market:
"{market}"

This trade was executed at {price*100:.1f} cents, and it immediately set off multiple red flags in our detection system.

## THE SIGNALS (1:30 - 3:00)
Our system detected {len(signals)} suspicious signals:

"""
    
    for i, signal in enumerate(signals, 1):
        signal_desc = {
            "FRESH_WALLET_BIG_BET": "A brand new wallet immediately placing a large bet",
            "SIZE_ANOMALY": "Trade size far above normal for this market",
            "TIGHT_SENSITIVE_MARKET": "Betting on a sensitive market with tight probability",
            "TEMPORAL_CLUSTERING": "Multiple wallets betting on the same outcome in a short window",
            "SHARED_FUNDING_SOURCE": "Wallet shares funding sources with other suspicious traders",
            "EARLY_EXIT_PATTERN": "Wallet has pattern of exiting positions very quickly"
        }.get(signal, signal)
        
        script += f"{i}. {signal_desc}\n"
    
    script += f"""
## WHY THIS MATTERS (3:00 - 4:00)
When multiple signals fire at once, it's a strong indicator of potential insider information.

This wallet didn't just make a big bet - they made a big bet in a way that suggests 
they might know something the rest of the market doesn't.

## WHAT TO WATCH (4:00 - 4:30)
We're tracking this wallet and monitoring:
- If they exit their position early
- If the market moves in their favor
- If other related wallets show similar patterns

## OUTRO (4:30 - 5:00)
If you found this interesting, make sure to subscribe and hit the notification bell.
We're building tools to detect insider trading on prediction markets, and this is 
exactly the kind of activity we're looking for.

Remember, this is for educational purposes. Always do your own research.

Thanks for watching, and I'll see you in the next one.
"""
    
    return script.strip()

def generate_telegram_explainer(alert_data):
    """
    Generate a Telegram explainer post
    
    Args:
        alert_data: Dictionary containing alert information
    
    Returns:
        String with Telegram explainer
    """
    trade = alert_data.get("trade", {})
    signals = alert_data.get("signals", [})
    wallet = trade.get("wallet", "Unknown")
    market = trade.get("market_question", "Unknown Market")
    amount = trade.get("usd", 0)
    price = trade.get("price", 0)
    
    # Get sensitivity
    market_category = trade.get("market_category", "")
    sensitivity = get_market_sensitivity(market, market_category)
    emoji = get_sensitivity_emoji(sensitivity['level'])
    
    hook = generate_compelling_hook(trade, signals, sensitivity)
    
    explainer = f"""
{emoji} *{sensitivity['level']} PRIORITY ALERT*

{hook}

━━━━━━━━━━━━━━━━━━━━

*THE EVIDENCE:*

{len(signals)} suspicious signals detected:
"""
    
    signal_descriptions = {
        "FRESH_WALLET_BIG_BET": "🆕 New wallet, immediate large bet",
        "SIZE_ANOMALY": "📊 Trade size far above normal",
        "TIGHT_SENSITIVE_MARKET": "🎯 Sensitive market with tight odds",
        "TEMPORAL_CLUSTERING": "⏰ Coordinated timing (multiple wallets)",
        "SHARED_FUNDING_SOURCE": "🔗 Shared funding sources",
        "EARLY_EXIT_PATTERN": "🚪 Early exit pattern detected"
    }
    
    for signal in signals:
        desc = signal_descriptions.get(signal, f"• {signal}")
        explainer += f"{desc}\n"
    
    explainer += f"""
━━━━━━━━━━━━━━━━━━━━

*TRADE DETAILS:*
• Market: {market[:80]}
• Bet Size: ${amount:,.0f}
• Entry Price: {price*100:.1f}¢
• Wallet: `{wallet}`

━━━━━━━━━━━━━━━━━━━━

*WHY THIS MATTERS:*

When multiple signals fire simultaneously, it suggests coordinated activity or insider information.

We're tracking this wallet and monitoring market movements.

#PolymarketInsider #PredictionMarkets
"""
    
    return explainer.strip()

def generate_twitter_summary(alert_data):
    """Generate a single Twitter summary tweet with hook"""
    trade = alert_data.get("trade", {})
    signals = alert_data.get("signals", [})
    market = trade.get("market_question", "Unknown Market")
    price = trade.get("price", 0)
    
    hook = generate_compelling_hook(trade, signals, {})
    
    return f"{hook}\n\n{len(signals)} signals detected.\n\n#Polymarket #InsiderTrading"

def save_narratives(alert_data, output_dir="narratives"):
    """
    Auto-generate and save all content formats as drafts
    Content Trigger - Automatically creates compelling hooks
    """
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(datetime.now().timestamp())
    
    # Generate all content formats
    twitter_thread = generate_twitter_thread(alert_data)
    twitter_summary = generate_twitter_summary(alert_data)
    youtube_short_hook = generate_youtube_short_hook(alert_data)
    youtube_script = generate_youtube_script(alert_data)
    telegram_explainer = generate_telegram_explainer(alert_data)
    
    # Save Twitter thread
    with open(f"{output_dir}/twitter_thread_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write("\n\n--- TWEET BREAK ---\n\n".join(twitter_thread))
    
    # Save Twitter summary
    with open(f"{output_dir}/twitter_summary_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write(twitter_summary)
    
    # Save YouTube Short hook
    with open(f"{output_dir}/youtube_short_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write(youtube_short_hook)
    
    # Save YouTube full script
    with open(f"{output_dir}/youtube_script_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write(youtube_script)
    
    # Save Telegram explainer
    with open(f"{output_dir}/telegram_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write(telegram_explainer)
    
    # Save all-in-one draft
    with open(f"{output_dir}/draft_all_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("CONTENT DRAFTS - AUTO-GENERATED\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("TWITTER/X THREAD:\n")
        f.write("-" * 80 + "\n")
        f.write("\n\n--- TWEET BREAK ---\n\n".join(twitter_thread))
        f.write("\n\n" + "=" * 80 + "\n\n")
        
        f.write("TWITTER/X SUMMARY:\n")
        f.write("-" * 80 + "\n")
        f.write(twitter_summary)
        f.write("\n\n" + "=" * 80 + "\n\n")
        
        f.write("YOUTUBE SHORT HOOK:\n")
        f.write("-" * 80 + "\n")
        f.write(youtube_short_hook)
        f.write("\n\n" + "=" * 80 + "\n\n")
        
        f.write("TELEGRAM EXPLAINER:\n")
        f.write("-" * 80 + "\n")
        f.write(telegram_explainer)
        f.write("\n\n" + "=" * 80 + "\n\n")
        
        f.write("YOUTUBE FULL SCRIPT:\n")
        f.write("-" * 80 + "\n")
        f.write(youtube_script)
    
    print(f"✅ Content drafts saved to {output_dir}/")
    print(f"   • Twitter thread: twitter_thread_{timestamp}.txt")
    print(f"   • Twitter summary: twitter_summary_{timestamp}.txt")
    print(f"   • YouTube Short: youtube_short_{timestamp}.txt")
    print(f"   • Telegram: telegram_{timestamp}.txt")
    print(f"   • All-in-one: draft_all_{timestamp}.txt")
    
    return {
        "twitter_thread": twitter_thread,
        "twitter_summary": twitter_summary,
        "youtube_short_hook": youtube_short_hook,
        "youtube_script": youtube_script,
        "telegram_explainer": telegram_explainer
    }
