import json
import os
import time

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

DEFAULT_TTL = 24 * 60 * 60  # 24 hours


def read_cache(path: str, ttl: int = DEFAULT_TTL):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        logger.warning(f"Cache corrupt, deleting: {path}")
        os.remove(path)
        return None

    timestamp = data.get("timestamp", 0)
    if time.time() - timestamp > ttl:
        logger.info(f"Cache expired: {path}")
        return None

    return data.get("payload")


def write_cache(path: str, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {"timestamp": time.time(), "payload": payload}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Cache written: {path}")
