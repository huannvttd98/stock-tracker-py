import os
from io import BytesIO

from typing import Optional

import pandas as pd
import mplfinance as mpf

import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

CHARTS_DIR = os.path.join(config.DATA_DIR, "charts")


def generate_candlestick(symbol: str, hist: pd.DataFrame) -> Optional[bytes]:
    """
    Generate candlestick chart PNG from OHLCV history.
    Returns PNG bytes or None on failure.
    """
    if hist.empty or len(hist) < 3:
        return None

    os.makedirs(CHARTS_DIR, exist_ok=True)

    try:
        df = hist.copy()
        df.index = pd.DatetimeIndex(df["date"])
        df = df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        df = df[["Open", "High", "Low", "Close", "Volume"]]

        style = mpf.make_mpf_style(
            base_mpf_style="nightclouds",
            marketcolors=mpf.make_marketcolors(
                up="#26a69a", down="#ef5350",
                edge="inherit", wick="inherit",
                volume={"up": "#26a69a80", "down": "#ef535080"},
            ),
            figcolor="#1e1e2e",
            facecolor="#1e1e2e",
            gridcolor="#333344",
            gridstyle="--",
        )

        buf = BytesIO()
        mpf.plot(
            df,
            type="candle",
            volume=True,
            style=style,
            title=f"\n{symbol} - {len(df)} phien",
            ylabel="Gia (VND)",
            ylabel_lower="KL",
            figsize=(10, 6),
            tight_layout=True,
            savefig=dict(fname=buf, dpi=120, bbox_inches="tight"),
        )
        buf.seek(0)
        return buf.read()
    except Exception as e:
        logger.error(f"Chart error for {symbol}: {e}")
        return None
