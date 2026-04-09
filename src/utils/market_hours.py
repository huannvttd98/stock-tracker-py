from datetime import datetime, timedelta, timezone

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Vietnam timezone UTC+7
VN_TZ = timezone(timedelta(hours=7))

# Trading sessions (with 15-min buffer on each side)
MORNING_START = (8, 45)   # 9:00 - 15min
MORNING_END = (11, 45)    # 11:30 + 15min
AFTERNOON_START = (12, 45)  # 13:00 - 15min
AFTERNOON_END = (15, 0)   # 14:45 + 15min


def is_market_open() -> bool:
    now = datetime.now(VN_TZ)

    # Monday=0, Friday=4
    if now.weekday() > 4:
        logger.info("Weekend - market closed")
        return False

    hour, minute = now.hour, now.minute
    current = (hour, minute)

    if MORNING_START <= current <= MORNING_END:
        return True
    if AFTERNOON_START <= current <= AFTERNOON_END:
        return True

    logger.info(f"Outside trading hours: {hour:02d}:{minute:02d} ICT")
    return False
