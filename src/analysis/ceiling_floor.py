import pandas as pd

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def detect_ceiling_floor(df: pd.DataFrame) -> tuple:
    """Return (ceiling_df, floor_df) for stocks hitting ceiling/floor price."""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    cols = [c.lower() for c in df.columns]
    df.columns = cols

    if "ceiling" not in cols or "floor" not in cols or "close" not in cols:
        logger.warning("Missing ceiling/floor/close columns")
        return pd.DataFrame(), pd.DataFrame()

    # Drop rows with invalid symbol
    if "symbol" in cols:
        df = df[df["symbol"].notna() & (df["symbol"] != "")].copy()

    # Ceiling: close >= ceiling (tang tran)
    ceiling = df[df["close"] >= df["ceiling"]].copy()
    ceiling = ceiling.sort_values("volume", ascending=False)

    # Floor: close <= floor (giam san)
    floor = df[df["close"] <= df["floor"]].copy()
    floor = floor.sort_values("volume", ascending=False)

    logger.info(f"Ceiling: {len(ceiling)} symbols, Floor: {len(floor)} symbols")
    return ceiling, floor
