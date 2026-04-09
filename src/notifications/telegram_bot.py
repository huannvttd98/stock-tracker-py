import requests

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def _url(self, method: str) -> str:
        return TELEGRAM_API.format(token=self.token, method=method)

    def send_message(self, text: str, disable_preview: bool = False) -> bool:
        try:
            resp = requests.post(
                self._url("sendMessage"),
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": disable_preview,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return True
            logger.error(f"Telegram sendMessage failed: {resp.status_code} {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Telegram sendMessage error: {e}")
            return False

    def send_alert(self, messages: list) -> bool:
        success = True
        for msg in messages:
            if not self.send_message(msg, disable_preview=True):
                success = False
        logger.info(f"Sent {len(messages)} message(s) to Telegram")
        return success
