import os
import sqlite3

import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

DB_PATH = os.path.join(config.DATA_DIR, "alerts.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            target_price REAL NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)
    return conn


def add_alert(chat_id: str, symbol: str, direction: str, target_price: float) -> int:
    """Add a price alert. direction: '>' or '<'. Returns alert id."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO price_alert (chat_id, symbol, direction, target_price) VALUES (?, ?, ?, ?)",
            (str(chat_id), symbol.upper(), direction, target_price),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_alerts(chat_id: str) -> list:
    """Get all active alerts for a chat_id."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT id, symbol, direction, target_price FROM price_alert "
            "WHERE chat_id = ? AND active = 1 ORDER BY symbol",
            (str(chat_id),),
        )
        return [{"id": r[0], "symbol": r[1], "direction": r[2], "target_price": r[3]}
                for r in cursor.fetchall()]
    finally:
        conn.close()


def get_all_active_alerts() -> list:
    """Get all active alerts across all users."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT id, chat_id, symbol, direction, target_price FROM price_alert WHERE active = 1"
        )
        return [{"id": r[0], "chat_id": r[1], "symbol": r[2], "direction": r[3], "target_price": r[4]}
                for r in cursor.fetchall()]
    finally:
        conn.close()


def deactivate_alert(alert_id: int):
    """Mark an alert as triggered (inactive)."""
    conn = _get_conn()
    try:
        conn.execute("UPDATE price_alert SET active = 0 WHERE id = ?", (alert_id,))
        conn.commit()
    finally:
        conn.close()


def remove_alert(chat_id: str, alert_id: int) -> bool:
    """Remove a specific alert by id."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "DELETE FROM price_alert WHERE id = ? AND chat_id = ?",
            (alert_id, str(chat_id)),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
