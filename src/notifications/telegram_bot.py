import time

import requests

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
MESSAGE_DELAY = 0.05


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def _url(self, method: str) -> str:
        return TELEGRAM_API.format(token=self.token, method=method)

    def send_message(self, text: str) -> bool:
        try:
            resp = requests.post(
                self._url("sendMessage"),
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
            if resp.status_code == 200:
                return True
            logger.error(f"Telegram sendMessage failed: {resp.status_code} {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Telegram sendMessage error: {e}")
            return False

    def send_photo(self, photo_path: str, caption: str = "") -> bool:
        try:
            with open(photo_path, "rb") as f:
                resp = requests.post(
                    self._url("sendPhoto"),
                    data={"chat_id": self.chat_id, "caption": caption},
                    files={"photo": f},
                    timeout=30,
                )
            if resp.status_code == 200:
                return True
            logger.error(f"Telegram sendPhoto failed: {resp.status_code} {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Telegram sendPhoto error: {e}")
            return False

    def send_alert_batch(self, summary: str, chart_paths: dict, max_symbols: int = 20):
        self.send_message(summary)
        time.sleep(MESSAGE_DELAY)

        sent = 0
        for symbol, path in chart_paths.items():
            if sent >= max_symbols:
                break
            self.send_photo(path, caption=symbol)
            time.sleep(MESSAGE_DELAY)
            sent += 1

        logger.info(f"Sent {sent} chart(s) to Telegram")
