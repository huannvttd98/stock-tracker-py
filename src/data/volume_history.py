"""Volume analysis - delegates to price_history for data storage."""
import pandas as pd

from src.data.price_history import get_avg_volumes
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def detect_volume_spikes(df: pd.DataFrame, multiplier: float = 2.0) -> pd.DataFrame:
    """Find symbols where today's volume >= multiplier * avg volume."""
    if df.empty:
        return pd.DataFrame()

    avg_volumes = get_avg_volumes()
    if not avg_volumes:
        logger.info("No historical volume data yet, skipping spike detection")
        return pd.DataFrame()

    spikes = []
    for _, row in df.iterrows():
        symbol = row.get("symbol", "")
        volume = row.get("volume", 0)
        avg_vol = avg_volumes.get(symbol)

        if not avg_vol or avg_vol == 0:
            continue

        ratio = volume / avg_vol
        if ratio >= multiplier:
            spike_row = row.copy()
            spike_row["avg_volume"] = avg_vol
            spike_row["volume_ratio"] = round(ratio, 1)
            spikes.append(spike_row)

    if not spikes:
        return pd.DataFrame()

    result = pd.DataFrame(spikes)
    result = result.sort_values("volume_ratio", ascending=False)
    logger.info(f"Detected {len(result)} volume spikes (>= {multiplier}x avg)")
    return result
