import os
import sqlite3

import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

DB_PATH = os.path.join(config.DATA_DIR, "watchlist.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            chat_id TEXT,
            symbol TEXT,
            PRIMARY KEY (chat_id, symbol)
        )
    """)
    return conn


def add_symbol(chat_id: str, symbol: str) -> bool:
    symbol = symbol.upper().strip()
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (chat_id, symbol) VALUES (?, ?)",
            (str(chat_id), symbol),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def remove_symbol(chat_id: str, symbol: str) -> bool:
    symbol = symbol.upper().strip()
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE chat_id = ? AND symbol = ?",
            (str(chat_id), symbol),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_watchlist(chat_id: str) -> list:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT symbol FROM watchlist WHERE chat_id = ? ORDER BY symbol",
            (str(chat_id),),
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def get_all_watched_symbols() -> dict:
    """Return {symbol: [chat_id, ...]} for all watched symbols."""
    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT chat_id, symbol FROM watchlist")
        result = {}
        for chat_id, symbol in cursor.fetchall():
            result.setdefault(symbol, []).append(chat_id)
        return result
    finally:
        conn.close()
