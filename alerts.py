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
