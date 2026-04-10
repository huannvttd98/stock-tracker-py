import os
import sqlite3
from datetime import datetime

import pandas as pd

import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

DB_PATH = os.path.join(config.DATA_DIR, "price_history.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_price (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (symbol, date)
        )
    """)
    return conn


def save_daily_prices(df: pd.DataFrame):
    """Save today's OHLCV data to history."""
    if df.empty:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    conn = _get_conn()
    count = 0

    for _, row in df.iterrows():
        symbol = row.get("symbol", "")
        if not symbol or not row.get("close"):
            continue
        conn.execute(
            "INSERT OR REPLACE INTO daily_price (symbol, date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (symbol, today, row.get("open", 0), row.get("high", 0),
             row.get("low", 0), row.get("close", 0), row.get("volume", 0)),
        )
        count += 1

    conn.commit()
    conn.close()
    logger.info(f"Saved {count} price records for {today}")


def get_price_history(symbol: str, days: int = 30) -> pd.DataFrame:
    """Get OHLCV history for a single symbol."""
    conn = _get_conn()
    df = pd.read_sql_query(
        "SELECT date, open, high, low, close, volume FROM daily_price "
        "WHERE symbol = ? AND date >= date('now', ? || ' days') ORDER BY date",
        conn, params=(symbol, f"-{days}"),
    )
    conn.close()
    return df


def get_all_close_prices(days: int = 30) -> dict:
    """Return {symbol: [close_prices]} for all symbols with enough data."""
    conn = _get_conn()
    cursor = conn.execute(
        "SELECT symbol, date, close FROM daily_price "
        "WHERE date >= date('now', ? || ' days') ORDER BY symbol, date",
        (f"-{days}",),
    )

    result = {}
    for symbol, date, close in cursor.fetchall():
        result.setdefault(symbol, []).append(close)

    conn.close()
    return result


def get_avg_volumes(days: int = 20) -> dict:
    """Return {symbol: avg_volume} over last N days."""
    conn = _get_conn()
    cursor = conn.execute(
        "SELECT symbol, AVG(volume) as avg_vol, COUNT(*) as cnt "
        "FROM daily_price WHERE date >= date('now', ? || ' days') "
        "GROUP BY symbol HAVING cnt >= 3",
        (f"-{days}",),
    )
    result = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return result
