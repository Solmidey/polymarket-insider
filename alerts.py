import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_alert(trade, signals, confidence):
    text = f"""
🚨 POSSIBLE INFORMED TRADING

Confidence: *{confidence}/100*

Market: {trade['market_question']}
Price: {trade['price']*100:.1f}¢
Trade Size: ${trade['usd']:.2f}

Wallet: {trade['wallet']}
Signals: {", ".join(signals)}
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }

    r = requests.post(url, json=payload)

    print("[TELEGRAM STATUS]", r.status_code)
    print("[TELEGRAM RESPONSE]", r.text)

    r.raise_for_status()
