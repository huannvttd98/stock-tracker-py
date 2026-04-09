import os
from dotenv import load_dotenv

load_dotenv()


# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Data source
DATA_SOURCE = os.getenv("DATA_SOURCE", "vnstock")

# Filtering
TOP_VOLUME_COUNT = int(os.getenv("TOP_VOLUME_COUNT", "10"))

# Scheduling
SCHEDULE_INTERVAL_MINUTES = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "5"))

# Performance
FETCH_BATCH_SIZE = int(os.getenv("FETCH_BATCH_SIZE", "50"))
FETCH_WORKERS = int(os.getenv("FETCH_WORKERS", "10"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
SYMBOLS_CACHE_PATH = os.path.join(DATA_DIR, "symbols_cache.json")


def validate():
    errors = []
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        errors.append("TELEGRAM_BOT_TOKEN is not configured")
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "your_chat_id_here":
        errors.append("TELEGRAM_CHAT_ID is not configured")
    return errors
