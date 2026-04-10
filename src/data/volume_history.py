import os
import sqlite3
from datetime import datetime

import pandas as pd

import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

DB_PATH = os.path.join(config.DATA_DIR, "volume_history.db")
AVG_DAYS = 20  # So phien tinh trung binh


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_volume (
            symbol TEXT,
            date TEXT,
            volume REAL,
            PRIMARY KEY (symbol, date)
        )
    """)
    return conn


def save_daily_volumes(df: pd.DataFrame):
    """Save today's volume data to history."""
    if df.empty:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    conn = _get_conn()
    count = 0

    for _, row in df.iterrows():
        symbol = row.get("symbol", "")
        volume = row.get("volume", 0)
        if not symbol or not volume:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO daily_volume (symbol, date, volume) VALUES (?, ?, ?)",
            (symbol, today, volume),
        )
        count += 1

    conn.commit()
    conn.close()
    logger.info(f"Saved {count} volume records for {today}")


def get_avg_volumes() -> dict:
    """Return dict {symbol: avg_volume} over last N days."""
    conn = _get_conn()
    cursor = conn.execute(f"""
        SELECT symbol, AVG(volume) as avg_vol, COUNT(*) as days
        FROM daily_volume
        WHERE date >= date('now', '-{AVG_DAYS} days')
        GROUP BY symbol
        HAVING days >= 3
    """)
    result = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return result


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
