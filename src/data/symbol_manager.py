import os

import config
from src.utils.cache import read_cache, write_cache
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

STATIC_FALLBACK_PATH = os.path.join(config.DATA_DIR, "symbols_static.json")


def get_all_symbols() -> list:
    cached = read_cache(config.SYMBOLS_CACHE_PATH)
    if cached:
        logger.info(f"Loaded {len(cached)} symbols from cache")
        return cached

    symbols = _fetch_from_vnstock()
    if symbols:
        write_cache(config.SYMBOLS_CACHE_PATH, symbols)
        return symbols

    # Fallback to static file
    static = read_cache(STATIC_FALLBACK_PATH, ttl=999_999_999)
    if static:
        logger.warning(f"Using static fallback: {len(static)} symbols")
        return static

    logger.error("No symbol data available")
    return []


def _fetch_from_vnstock() -> list:
    try:
        from vnstock import Listing

        listing = Listing(source='VCI')
        df = listing.all_symbols(show_log=False)

        # Filter HOSE and HNX only
        if "comGroupCode" in df.columns:
            df = df[df["comGroupCode"].isin(["HOSE", "HNX"])]

        symbols = df["ticker"].tolist() if "ticker" in df.columns else df.iloc[:, 0].tolist()
        logger.info(f"Fetched {len(symbols)} symbols from vnstock")
        return symbols
    except Exception as e:
        logger.error(f"Failed to fetch symbols from vnstock: {e}")
        return []
