import os
from dotenv import load_dotenv

# =========================
# Load environment variables
# =========================

# This loads variables from a .env file into the environment
load_dotenv()

# =========================
# External APIs
# =========================

DATA_API_BASE = "https://data-api.polymarket.com"

# Telegram (loaded from environment variables)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError(
        "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables"
    )

# =========================
# Core Detection Thresholds
# =========================

FRESH_WALLET_DAYS = 7
LARGE_BET_USD = 5000
CLUSTER_WINDOW_MIN = 120

# =========================
# Sanity Filter Thresholds
# =========================

MIN_MARKET_LIQUIDITY = 10_000          # Minimum USD liquidity to allow alerts
MAX_PRICE_JUMP_SINGLE_TRADE = 0.20     # Max price change from single trade (20%)
HIGH_FREQ_TRADER_THRESHOLD = 50        # Trades/day considered HFT

# =========================
# Cluster Detection
# =========================

CLUSTER_TIME_WINDOW_MIN = 15    # minutes
CLUSTER_MIN_WALLETS = 3         # unique wallets
CLUSTER_MIN_TOTAL_USD = 3000    # combined size
