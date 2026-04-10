import threading
import time

import requests

import config
from src.data.cafef_fetcher import CafefFetcher
from src.data.watchlist import add_symbol, remove_symbol, get_watchlist
from src.analysis.profit_calculator import calculate_profits, _format_volume
from src.analysis.ceiling_floor import detect_ceiling_floor
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramCommandBot:
    def __init__(self, token: str):
        self.token = token
        self.offset = 0
        self._running = False

    def _url(self, method: str) -> str:
        return TELEGRAM_API.format(token=self.token, method=method)

    def _send(self, chat_id, text: str):
        try:
            requests.post(
                self._url("sendMessage"),
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Send error: {e}")

    def _get_updates(self) -> list:
        try:
            resp = requests.get(
                self._url("getUpdates"),
                params={"offset": self.offset, "timeout": 30},
                timeout=35,
            )
            if resp.status_code == 200:
                return resp.json().get("result", [])
        except Exception as e:
            logger.debug(f"getUpdates error: {e}")
        return []

    def _handle_message(self, msg: dict):
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        if not text.startswith("/"):
            return

        parts = text.split()
        cmd = parts[0].lower().split("@")[0]  # handle /cmd@botname
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "/start" or cmd == "/help":
            self._cmd_help(chat_id)
        elif cmd == "/top":
            self._cmd_top(chat_id)
        elif cmd == "/gia":
            self._cmd_gia(chat_id, args)
        elif cmd == "/tran":
            self._cmd_tran(chat_id)
        elif cmd == "/san":
            self._cmd_san(chat_id)
        elif cmd == "/goiy":
            self._cmd_goiy(chat_id)
        elif cmd == "/watch":
            self._cmd_watch(chat_id, args)
        elif cmd == "/unwatch":
            self._cmd_unwatch(chat_id, args)
        elif cmd == "/list":
            self._cmd_list(chat_id)

    def _cmd_help(self, chat_id):
        self._send(chat_id, (
            "<b>📋 LENH BOT</b>\n\n"
            "/top - Top 10 KL giao dich lon nhat\n"
            "/gia <b>MA</b> - Xem gia 1 ma (VD: /gia VNM)\n"
            "/tran - Cac ma dang cham tran\n"
            "/san - Cac ma dang cham san\n"
            "/goiy - Goi y ma nen theo doi\n"
            "/watch <b>MA</b> - Them ma vao watchlist\n"
            "/unwatch <b>MA</b> - Bo ma khoi watchlist\n"
            "/list - Xem watchlist cua ban"
        ))

    def _cmd_top(self, chat_id):
        df = self._fetch_data()
        if df is None:
            return self._send(chat_id, "Khong lay duoc du lieu.")

        top = df.sort_values("volume", ascending=False).head(10)
        lines = ["<b>📊 TOP 10 KHOI LUONG</b>\n"]
        for idx, (_, row) in enumerate(top.iterrows(), 1):
            sym = row["symbol"]
            vol = _format_volume(row["volume"])
            pct = row.get("profit_pct", 0)
            sign = "+" if pct >= 0 else ""
            lines.append(f"{idx}. <b>{sym}</b> | KL: {vol} | {sign}{pct:.2f}%")
        self._send(chat_id, "\n".join(lines))

    def _cmd_gia(self, chat_id, args):
        if not args:
            return self._send(chat_id, "Dung: /gia <b>MA</b>\nVD: /gia VNM")

        symbol = args[0].upper()
        df = self._fetch_data()
        if df is None:
            return self._send(chat_id, "Khong lay duoc du lieu.")

        match = df[df["symbol"] == symbol]
        if match.empty:
            return self._send(chat_id, f"Khong tim thay ma <b>{symbol}</b>")

        row = match.iloc[0]
        pct = row.get("profit_pct", 0)
        sign = "+" if pct >= 0 else ""
        change = row["close"] - row["open"]
        c_sign = "+" if change >= 0 else ""
        vol = _format_volume(row["volume"])
        url = f"https://finance.vietstock.vn/{symbol}/tai-chinh.htm"

        self._send(chat_id, (
            f"<b>📈 {symbol}</b>\n\n"
            f"Gia: <code>{row['close']:,.0f}</code> ({c_sign}{change:,.0f} | {sign}{pct:.2f}%)\n"
            f"Mo: <code>{row['open']:,.0f}</code>\n"
            f"Cao: <code>{row['high']:,.0f}</code> | Thap: <code>{row['low']:,.0f}</code>\n"
            f"Tran: <code>{row['ceiling']:,.0f}</code> | San: <code>{row['floor']:,.0f}</code>\n"
            f"KL: <b>{vol}</b>\n\n"
            f"🔗 <a href=\"{url}\">Xem chi tiet</a>"
        ))

    def _cmd_tran(self, chat_id):
        df = self._fetch_data()
        if df is None:
            return self._send(chat_id, "Khong lay duoc du lieu.")

        ceiling, _ = detect_ceiling_floor(df)
        if ceiling.empty:
            return self._send(chat_id, "Khong co ma nao cham tran hom nay.")

        lines = [f"<b>🔴 {len(ceiling)} MA CHAM TRAN</b>\n"]
        for _, row in ceiling.head(20).iterrows():
            vol = _format_volume(row["volume"])
            lines.append(f"<b>{row['symbol']}</b> | <code>{row['close']:,.0f}</code> | KL: {vol}")
        self._send(chat_id, "\n".join(lines))

    def _cmd_san(self, chat_id):
        df = self._fetch_data()
        if df is None:
            return self._send(chat_id, "Khong lay duoc du lieu.")

        _, floor = detect_ceiling_floor(df)
        if floor.empty:
            return self._send(chat_id, "Khong co ma nao cham san hom nay.")

        lines = [f"<b>🟢 {len(floor)} MA CHAM SAN</b>\n"]
        for _, row in floor.head(20).iterrows():
            vol = _format_volume(row["volume"])
            lines.append(f"<b>{row['symbol']}</b> | <code>{row['close']:,.0f}</code> | KL: {vol}")
        self._send(chat_id, "\n".join(lines))

    def _cmd_goiy(self, chat_id):
        from src.analysis.stock_suggestion import suggest_stocks, format_suggestions
        df = self._fetch_data()
        if df is None:
            return self._send(chat_id, "Khong lay duoc du lieu.")

        suggestions = suggest_stocks(df)
        if suggestions.empty:
            return self._send(chat_id, "Chua co du lieu lich su de goi y (can it nhat 3 ngay).")

        text = format_suggestions(suggestions)
        self._send(chat_id, text)

    def _cmd_watch(self, chat_id, args):
        if not args:
            return self._send(chat_id, "Dung: /watch <b>MA</b>\nVD: /watch VNM")
        symbol = args[0].upper()
        add_symbol(str(chat_id), symbol)
        self._send(chat_id, f"Da them <b>{symbol}</b> vao watchlist.")

    def _cmd_unwatch(self, chat_id, args):
        if not args:
            return self._send(chat_id, "Dung: /unwatch <b>MA</b>")
        symbol = args[0].upper()
        if remove_symbol(str(chat_id), symbol):
            self._send(chat_id, f"Da bo <b>{symbol}</b> khoi watchlist.")
        else:
            self._send(chat_id, f"<b>{symbol}</b> khong co trong watchlist.")

    def _cmd_list(self, chat_id):
        symbols = get_watchlist(str(chat_id))
        if not symbols:
            return self._send(chat_id, "Watchlist trong. Dung /watch <b>MA</b> de them.")
        self._send(chat_id, f"<b>📋 WATCHLIST ({len(symbols)} ma)</b>\n\n" + ", ".join(symbols))

    def _fetch_data(self):
        try:
            fetcher = CafefFetcher()
            df = fetcher.fetch_all()
            if df.empty:
                return None
            return calculate_profits(df)
        except Exception as e:
            logger.error(f"Fetch data error: {e}")
            return None

    def start_polling(self):
        """Start polling in a background thread."""
        self._running = True
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()
        logger.info("Telegram command bot started (polling)")

    def stop_polling(self):
        self._running = False

    def _poll_loop(self):
        while self._running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self.offset = update["update_id"] + 1
                    if "message" in update:
                        self._handle_message(update["message"])
            except Exception as e:
                logger.error(f"Poll error: {e}")
                time.sleep(5)
