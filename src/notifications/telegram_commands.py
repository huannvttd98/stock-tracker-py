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
        elif cmd == "/pt":
            self._cmd_phantich(chat_id, args)
        elif cmd == "/hocpt":
            self._cmd_hocpt(chat_id)
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
            "/pt <b>MA</b> - Phan tich ky thuat (VD: /pt VNM)\n"
            "/hocpt - Giai thich cach phan tich ky thuat\n"
            "/watch <b>MA</b> - Them ma vao watchlist\n"
            "/unwatch <b>MA</b> - Bo ma khoi watchlist\n"
            "/list - Xem watchlist cua ban"
        ))

    def _cmd_hocpt(self, chat_id):
        self._send(chat_id, (
            "<b>📚 RSI (Relative Strength Index)</b>\n\n"
            "Do suc manh tang/giam cua gia trong 14 phien.\n"
            "Thang diem: 0 - 100\n\n"
            "• RSI &lt;= 30 → <b>Qua ban</b> (gia giam qua nhieu, co the bat day)\n"
            "• RSI &gt;= 70 → <b>Qua mua</b> (gia tang qua nhieu, co the dieu chinh)\n"
            "• RSI 30-70 → Binh thuong\n\n"
            "<i>VD: RSI = 25 → Co phieu bi ban thao manh, co the la co hoi mua.</i>"
        ))
        self._send(chat_id, (
            "<b>📚 MA CROSSOVER (Giao cat trung binh dong)</b>\n\n"
            "So sanh 2 duong trung binh:\n"
            "• <b>MA5</b>: Trung binh gia dong 5 phien (ngan han)\n"
            "• <b>MA20</b>: Trung binh gia dong 20 phien (trung han)\n\n"
            "Tin hieu:\n"
            "• MA5 cat len MA20 → <b>Golden Cross</b> 🟢 (xu huong tang)\n"
            "• MA5 cat xuong MA20 → <b>Death Cross</b> 🔴 (xu huong giam)\n"
            "• MA5 &gt; MA20 → Dang trong xu huong tang\n"
            "• MA5 &lt; MA20 → Dang trong xu huong giam\n\n"
            "<i>VD: MA5 vua vuot len MA20 → Golden Cross, tin hieu mua.</i>"
        ))
        self._send(chat_id, (
            "<b>📚 BOLLINGER BANDS (Dai bang Bollinger)</b>\n\n"
            "3 duong bao quanh gia:\n"
            "• <b>Bang tren</b>: MA20 + 2 do lech chuan\n"
            "• <b>Bang giua</b>: MA20\n"
            "• <b>Bang duoi</b>: MA20 - 2 do lech chuan\n\n"
            "Doc vi tri (0% = bang duoi, 100% = bang tren):\n"
            "• Gia &gt;= 100% → <b>Breakout len</b> (tang manh hoac qua mua)\n"
            "• Gia &lt;= 0% → <b>Breakout xuong</b> (giam manh hoac co hoi mua)\n"
            "• Gia 20-80% → Binh thuong\n\n"
            "<i>VD: Vi tri = 5% → Gia gan bang duoi, co the bat day.</i>"
        ))
        self._send(chat_id, (
            "<b>📚 CACH DOC KET QUA /pt</b>\n\n"
            "Moi chi bao duoc cham diem:\n"
            "• Diem duong (+) → tin hieu MUA\n"
            "• Diem am (-) → tin hieu BAN\n\n"
            "Tong hop:\n"
            "🟢 <b>TICH CUC</b>: Nhieu tin hieu mua (>= +3 diem)\n"
            "🟡 <b>NGHIENG TANG/GIAM</b>: Tin hieu nhe\n"
            "🔴 <b>TIEU CUC</b>: Nhieu tin hieu ban (&lt;= -3 diem)\n"
            "⚪ <b>TRUNG TINH</b>: Khong co tin hieu ro\n\n"
            "<i>Luu y: Day la cong cu ho tro, khong phai loi khuyen dau tu.</i>"
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

    def _cmd_phantich(self, chat_id, args):
        if not args:
            return self._send(chat_id, "Dung: /pt <b>MA</b>\nVD: /pt VNM")

        symbol = args[0].upper()

        from src.data.price_history import get_price_history
        from src.analysis.technical import calc_rsi, detect_ma_crossover, get_ma_position, calc_bollinger, interpret_rsi, interpret_bollinger

        hist = get_price_history(symbol, days=30)
        if hist.empty or len(hist) < 5:
            return self._send(chat_id, f"Chua du du lieu cho <b>{symbol}</b> (can it nhat 5 phien).")

        closes = hist["close"].tolist()
        current = closes[-1]

        # RSI
        rsi = calc_rsi(closes)
        rsi_text = f"RSI(14): <b>{rsi}</b> - {interpret_rsi(rsi)}" if rsi else "RSI: chua du du lieu (14 phien)"

        # MA
        ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else None
        ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        crossover = detect_ma_crossover(closes)
        ma_pos = get_ma_position(closes)

        ma_lines = []
        if ma5:
            ma_lines.append(f"MA5: <code>{ma5:,.0f}</code>")
        if ma20:
            ma_lines.append(f"MA20: <code>{ma20:,.0f}</code>")
        if crossover == "GOLDEN_CROSS":
            ma_lines.append("⬆️ <b>GOLDEN CROSS</b> (tin hieu mua)")
        elif crossover == "DEATH_CROSS":
            ma_lines.append("⬇️ <b>DEATH CROSS</b> (tin hieu ban)")
        elif ma_pos == "ABOVE":
            ma_lines.append("MA5 > MA20 (xu huong tang)")
        elif ma_pos == "BELOW":
            ma_lines.append("MA5 < MA20 (xu huong giam)")
        ma_text = "\n   ".join(ma_lines) if ma_lines else "Chua du du lieu (20 phien)"

        # Bollinger
        bb = calc_bollinger(closes)
        if bb:
            bb_text = (
                f"Upper: <code>{bb['upper']:,.0f}</code> | Mid: <code>{bb['middle']:,.0f}</code> | Lower: <code>{bb['lower']:,.0f}</code>\n"
                f"   Vi tri: <b>{bb['position']:.0%}</b> - {interpret_bollinger(bb)}"
            )
        else:
            bb_text = "Chua du du lieu (20 phien)"

        # Overall
        score_total = 0
        if rsi and rsi <= 30: score_total += 2
        elif rsi and rsi >= 70: score_total -= 2
        if crossover == "GOLDEN_CROSS": score_total += 3
        elif crossover == "DEATH_CROSS": score_total -= 3
        if bb and bb["position"] <= 0.2: score_total += 1
        elif bb and bb["position"] >= 0.8: score_total -= 1

        if score_total >= 3:
            verdict = "🟢 <b>TICH CUC</b> - Nhieu tin hieu mua"
        elif score_total <= -3:
            verdict = "🔴 <b>TIEU CUC</b> - Nhieu tin hieu ban"
        elif score_total > 0:
            verdict = "🟡 <b>NGHIENG TANG</b>"
        elif score_total < 0:
            verdict = "🟡 <b>NGHIENG GIAM</b>"
        else:
            verdict = "⚪ <b>TRUNG TINH</b>"

        url = f"https://finance.vietstock.vn/{symbol}/tai-chinh.htm"
        self._send(chat_id, (
            f"<b>📊 PHAN TICH: {symbol}</b>\n"
            f"Gia hien tai: <code>{current:,.0f}</code>\n"
            f"Du lieu: {len(closes)} phien\n\n"
            f"<b>RSI</b>\n   {rsi_text}\n\n"
            f"<b>MA Crossover</b>\n   {ma_text}\n\n"
            f"<b>Bollinger Bands</b>\n   {bb_text}\n\n"
            f"<b>Tong hop:</b> {verdict}\n\n"
            f"🔗 <a href=\"{url}\">Xem chi tiet {symbol}</a>"
        ))

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
