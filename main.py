import time
import traceback

from fetch import fetch_trades
from detector import detect_insider
from alerts import send_alert
from sanity_filter import sanity_check_trade
from confidence import compute_confidence
from cluster import detect_cluster

from db import (
    init_db,
    record_trade,
    alert_recently_fired,
    record_alert
)

# =========================
# CONFIG
# =========================
POLL_INTERVAL = 30
BATCH_SIZE = 20

TEST_MODE = False            # TRUE only for local testing
TEST_MODE_ONE_SHOT = False
MIN_CONFIDENCE = 60
# =========================


def process_trades():
    trades = fetch_trades(BATCH_SIZE)

    if not trades:
        print("[INFO] No new trades")
        return False

    print(f"[INFO] Processing {len(trades)} trades")

    for t in trades:
        try:
            # -----------------------
            # Sanity filter
            # -----------------------
            if not sanity_check_trade(t):
                continue

            wallet = t["proxyWallet"]
            market = t["title"]
            price = t["price"]
            usd_size = t["size"] * price
            timestamp = t.get("timestamp", int(time.time()))
            trade_id = t.get("transactionHash")

            # -----------------------
            # Record trade (RAW DATA)
            # -----------------------
            record_trade(
                trade_id=trade_id,
                wallet=wallet,
                market=market,
                usd=usd_size,
                price=price,
                timestamp=timestamp
            )

            # -----------------------
            # Base detection
            # -----------------------
            is_insider, signals = detect_insider(t)

            # -----------------------
            # Cluster detection
            # -----------------------
            clustered, info = detect_cluster(market)
            if clustered:
                signals.append("clustered_activity")
                print(
                    f"[CLUSTER] {info['wallets']} wallets | "
                    f"${info['total_usd']:.0f} total"
                )

            # -----------------------
            # TEST MODE OVERRIDE
            # -----------------------
            if TEST_MODE:
                is_insider = True
                signals.append("test_mode")

            if not is_insider:
                continue

            # -----------------------
            # Confidence scoring
            # -----------------------
            confidence = compute_confidence(signals)

            if confidence < MIN_CONFIDENCE:
                print("[SKIP] Low confidence:", confidence, signals)
                continue

            # -----------------------
            # Deduplication
            # -----------------------
            if alert_recently_fired(wallet, market):
                print("[SKIP] Duplicate alert blocked:", wallet, market)
                continue

            # -----------------------
            # ALERT
            # -----------------------
            print("🚨 ALERT TRIGGERED")
            print("Wallet:", wallet)
            print("Market:", market)
            print("USD Size:", round(usd_size, 2))
            print("Confidence:", confidence)
            print("Signals:", signals)
            print("-" * 50)

            send_alert(
                trade={
                    "wallet": wallet,
                    "usd": usd_size,
                    "price": price,
                    "market_question": market,
                    "market_category": ""
                },
                signals=signals,
                confidence=confidence
            )

            # -----------------------
            # Record alert (FIXED)
            # -----------------------
            record_alert(
                wallet=wallet,
                market=market,
                price=price,
                signals=signals,
                confidence=confidence
            )

            # -----------------------
            # Test mode exit
            # -----------------------
            if TEST_MODE and TEST_MODE_ONE_SHOT:
                print("[TEST MODE] One alert sent. Exiting.")
                return True

        except Exception as e:
            print("[ERROR] Failed processing trade")
            print("Trade:", t)
            print("Error:", e)
            traceback.print_exc()

    return False


def main():
    print("🟢 Polymarket Insider Alert System Starting...")

    if TEST_MODE:
        print("⚠️ TEST MODE ENABLED")

    init_db()

    while True:
        try:
            stop = process_trades()
            print("[HEARTBEAT] System alive")

            if stop:
                break

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested")
            break

        except Exception as e:
            print("[FATAL] Main loop error:", e)
            traceback.print_exc()
            time.sleep(10)


if __name__ == "__main__":
    main()
