import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from market_sensitivity import get_market_sensitivity, get_sensitivity_emoji

def send_alert(trade, signals):
    # Get market sensitivity
    market_question = trade.get('market_question', '')
    market_category = trade.get('market_category', '')
    sensitivity = get_market_sensitivity(market_question, market_category)
    emoji = get_sensitivity_emoji(sensitivity['level'])
    
    # Build alert text with sensitivity indicator
    sensitivity_line = f"{emoji} *{sensitivity['level']} PRIORITY*"
    if sensitivity['matched_keywords']:
        sensitivity_line += f" ({', '.join(sensitivity['matched_keywords'][:2])})"
    
    text = f"""
🚨 *POSSIBLE INFORMED TRADING*

{sensitivity_line}

Market: {market_question}
Price: {trade['price']*100:.1f}¢
Trade Size: ${trade['usd']:,.0f}

Wallet: {trade['wallet']}
Signals:
- {' | '.join(signals)}
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    })

def format_alert(trade, signals=None):
    """
    Safe formatter for dry-run / testing without Telegram.
    """
    usd = trade.get("usd") or trade.get("size", 0) * trade.get("price", 0)

    lines = [
        "🚨 POSSIBLE INFORMED TRADING",
        f"Market: {trade.get('title') or trade.get('market_question')}",
        f"Price: {trade.get('price')}",
        f"Size (USD): ${usd:,.2f}",
        f"Wallet: {trade.get('proxyWallet') or trade.get('wallet')}",
    ]

    if signals:
        lines.append("Signals:")
        for s in signals:
            lines.append(f"- {s}")

    return "\n".join(lines)
