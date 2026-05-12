import threading
import time
import traceback

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
            resp = requests.post(
                self._url("sendMessage"),
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                logger.error(
                    f"Telegram sendMessage failed: {resp.status_code} {resp.text} "
                    f"(text_len={len(text)})"
                )
                return False
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False

    def _send_photo(self, chat_id, photo_bytes: bytes, caption: str = ""):
        try:
            files = {"photo": ("chart.png", photo_bytes, "image/png")}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            requests.post(self._url("sendPhoto"), data=data, files=files, timeout=15)
        except Exception as e:
            logger.error(f"Send photo error: {e}")

    def _send_document(self, chat_id, doc_bytes: bytes, filename: str, caption: str = ""):
        try:
            files = {"document": (filename, doc_bytes)}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            requests.post(self._url("sendDocument"), data=data, files=files, timeout=15)
        except Exception as e:
            logger.error(f"Send document error: {e}")

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
        elif cmd == "/report":
            self._cmd_report(chat_id)
        elif cmd == "/alert":
            self._cmd_alert(chat_id, args)
        elif cmd == "/ls":
            self._cmd_lichsu(chat_id, args)
        elif cmd == "/ss":
            self._cmd_sosanh(chat_id, args)
        elif cmd == "/nganh":
            self._cmd_nganh(chat_id, args)
        elif cmd == "/export":
            self._cmd_export(chat_id)
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
            "/pt <b>MA</b> - Phan tich ky thuat + bieu do (VD: /pt VNM)\n"
            "/ls <b>MA</b> - Lich su gia 10 phien (VD: /ls VNM)\n"
            "/ss <b>MA1 MA2 ...</b> - So sanh nhieu ma (VD: /ss VNM VIC HPG)\n"
            "/alert <b>MA &gt;GIA</b> - Canh bao gia (VD: /alert VNM &gt;50000)\n"
            "/nganh - Bao cao theo nganh\n"
            "/report - Bao cao tong hop thi truong\n"
            "/export - Xuat du lieu CSV\n"
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

        # Price range position
        day_range = row["high"] - row["low"]
        if day_range > 0:
            range_pos = (row["close"] - row["low"]) / day_range * 100
        else:
            range_pos = 50

        # Ceiling/floor distance
        ceil_dist = (row["ceiling"] - row["close"]) / row["close"] * 100 if row["close"] > 0 else 0
        floor_dist = (row["close"] - row["floor"]) / row["close"] * 100 if row["close"] > 0 else 0

        # Emoji for trend
        if pct >= 3:
            trend_emoji = "🟢🟢"
        elif pct >= 0.5:
            trend_emoji = "🟢"
        elif pct <= -3:
            trend_emoji = "🔴🔴"
        elif pct <= -0.5:
            trend_emoji = "🔴"
        else:
            trend_emoji = "⚪"

        lines = [
            f"<b>📈 {symbol}</b> {trend_emoji}\n",
            f"<b>Gia:</b> <code>{row['close']:,.0f}</code> ({c_sign}{change:,.0f} | {sign}{pct:.2f}%)",
            f"<b>Mo:</b> <code>{row['open']:,.0f}</code>",
            f"<b>Cao:</b> <code>{row['high']:,.0f}</code> | <b>Thap:</b> <code>{row['low']:,.0f}</code>",
            f"<b>Bien do:</b> <code>{day_range:,.0f}</code> ({range_pos:.0f}% tu thap)",
            f"<b>Tran:</b> <code>{row['ceiling']:,.0f}</code> (+{ceil_dist:.1f}%) | <b>San:</b> <code>{row['floor']:,.0f}</code> (-{floor_dist:.1f}%)",
            f"<b>KL:</b> <b>{vol}</b>",
        ]

        # Sector
        from src.data.sector_map import get_sector_for_symbol
        sector = get_sector_for_symbol(symbol)
        if sector:
            lines.append(f"<b>Nganh:</b> {sector}")

        # Foreign flow from CafeF data
        fb = row.get("foreign_buy", 0) or 0
        fs = row.get("foreign_sell", 0) or 0
        if fb or fs:
            fn = fb - fs
            fn_sign = "+" if fn >= 0 else ""
            lines.append(
                f"<b>🌐 Ngoai:</b> Mua <code>{_format_volume(fb)}</code>"
                f" | Ban <code>{_format_volume(fs)}</code>"
                f" | Rong <b>{fn_sign}{_format_volume(fn)}</b>"
            )

        # Technical analysis from history
        from src.data.price_history import get_price_history
        from src.analysis.technical import (
            calc_rsi, calc_macd, get_ma_position, calc_bollinger,
            calc_support_resistance, calc_ma_multi, classify_trend,
        )

        hist = get_price_history(symbol, days=40)
        if not hist.empty and len(hist) >= 15:
            closes = hist["close"].tolist()

            rsi = calc_rsi(closes)
            ma_pos = get_ma_position(closes)
            macd = calc_macd(closes)
            bb = calc_bollinger(closes)

            lines.append("\n<b>📊 Ky thuat</b>")

            if rsi is not None:
                if rsi >= 70:
                    rsi_tag = "⚠️ Qua mua"
                elif rsi <= 30:
                    rsi_tag = "💡 Qua ban"
                elif rsi >= 60:
                    rsi_tag = "Manh"
                elif rsi <= 40:
                    rsi_tag = "Yeu"
                else:
                    rsi_tag = "Trung tinh"
                lines.append(f"  RSI(14): <b>{rsi:.1f}</b> - {rsi_tag}")

            if ma_pos == "ABOVE":
                lines.append("  MA: MA5 ↑ MA20 (xu huong tang)")
            elif ma_pos == "BELOW":
                lines.append("  MA: MA5 ↓ MA20 (xu huong giam)")

            if macd:
                if macd["crossover"] == "BULLISH":
                    lines.append("  MACD: 🟢 Bullish Cross")
                elif macd["crossover"] == "BEARISH":
                    lines.append("  MACD: 🔴 Bearish Cross")
                else:
                    hist_val = macd["histogram"]
                    h_sign = "+" if hist_val >= 0 else ""
                    lines.append(f"  MACD: {h_sign}{hist_val:.0f}")

            if bb:
                pos = bb["position"]
                if pos >= 1.0:
                    lines.append("  BB: ⚠️ Tren bang tren")
                elif pos <= 0.0:
                    lines.append("  BB: 💡 Duoi bang duoi")
                else:
                    lines.append(f"  BB: {pos:.0%} (0%=day, 100%=dinh)")

            # 5-day trend summary
            if len(hist) >= 5:
                last5 = hist.tail(5)
                first_c = last5.iloc[0]["close"]
                last_c = last5.iloc[-1]["close"]
                if first_c > 0:
                    trend_5d = (last_c - first_c) / first_c * 100
                    t_sign = "+" if trend_5d >= 0 else ""
                    lines.append(f"  5 phien: {t_sign}{trend_5d:.2f}%")

            # Trend classification
            trend_cls = classify_trend(closes)
            if trend_cls:
                trend_map = {
                    "TANG MANH": "🟢🟢 Tang manh",
                    "TANG": "🟢 Tang",
                    "DI NGANG": "⚪ Di ngang",
                    "GIAM": "🔴 Giam",
                    "GIAM MANH": "🔴🔴 Giam manh",
                }
                lines.append(f"  <b>Xu huong:</b> {trend_map.get(trend_cls, trend_cls)}")

            # MA multi
            ma_multi = calc_ma_multi(closes)
            if ma_multi:
                ma_parts = []
                for k in ["ma20", "ma50"]:
                    if k in ma_multi:
                        ma_parts.append(f"{k.upper()}: <code>{ma_multi[k]:,.0f}</code>")
                if ma_parts:
                    lines.append(f"  {' | '.join(ma_parts)}")

            # Support / Resistance
            sr = calc_support_resistance(closes)
            if sr:
                lines.append(
                    f"  Ho tro: <code>{sr['support']:,.0f}</code>"
                    f" | Khang cu: <code>{sr['resistance']:,.0f}</code>"
                )

        # Fundamental data
        try:
            from src.data.fundamental import get_fundamental
            fund = get_fundamental(symbol, row["close"])
            has_fund = any(fund.get(k) for k in ("pe", "pb", "eps", "roe"))
            if has_fund:
                lines.append("\n<b>📋 Co ban</b>")
                fund_parts = []
                if fund["pe"]:
                    fund_parts.append(f"P/E: <b>{fund['pe']:.1f}</b>")
                if fund["pb"]:
                    fund_parts.append(f"P/B: <b>{fund['pb']:.2f}</b>")
                if fund_parts:
                    lines.append(f"  {' | '.join(fund_parts)}")
                if fund["eps"]:
                    lines.append(f"  EPS: <code>{fund['eps']:,.0f}</code>")
                if fund["bvps"]:
                    lines.append(f"  BVPS: <code>{fund['bvps']:,.0f}</code>")
                if fund["roe"]:
                    lines.append(f"  ROE: <b>{fund['roe']:.1f}%</b>")
                company = fund.get("company", {})
                if company.get("name"):
                    lines.append(f"  {company['name']}")
        except Exception:
            pass

        lines.append(f"\n🔗 <a href=\"{url}\">Xem chi tiet</a>")

        self._send(chat_id, "\n".join(lines))

    def _cmd_tran(self, chat_id):
        df = self._fetch_data()
        if df is None:
            return self._send(chat_id, "Khong lay duoc du lieu.")

        ceiling, _ = detect_ceiling_floor(df)
        if ceiling.empty:
            return self._send(chat_id, "Khong co ma nao cham tran hom nay.")

        lines = [f"<b>🔴 {len(ceiling)} MA CHAM TRAN</b>\n"]
        for _, row in ceiling.head(20).iterrows():
            sym = row.get("symbol", "")
            if not sym or str(sym) == "nan":
                continue
            vol = _format_volume(row["volume"])
            lines.append(f"<b>{sym}</b> | <code>{row['close']:,.0f}</code> | KL: {vol}")
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
            sym = row.get("symbol", "")
            if not sym or str(sym) == "nan":
                continue
            vol = _format_volume(row["volume"])
            lines.append(f"<b>{sym}</b> | <code>{row['close']:,.0f}</code> | KL: {vol}")
        self._send(chat_id, "\n".join(lines))

    def _cmd_phantich(self, chat_id, args):
        if not args:
            return self._send(chat_id, "Dung: /pt <b>MA</b>\nVD: /pt VNM")

        symbol = args[0].upper()

        from src.data.price_history import get_price_history
        from src.analysis.technical import calc_rsi, detect_ma_crossover, get_ma_position, calc_bollinger, interpret_rsi, interpret_bollinger, calc_macd, interpret_macd

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
            ma_lines.append("MA5 ↑ MA20 (xu huong tang)")
        elif ma_pos == "BELOW":
            ma_lines.append("MA5 ↓ MA20 (xu huong giam)")
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

        # MACD
        macd_data = calc_macd(closes)
        if macd_data:
            macd_text = (
                f"MACD: <b>{macd_data['macd']}</b> | Signal: <b>{macd_data['signal']}</b>\n"
                f"   Histogram: <b>{macd_data['histogram']}</b> - {interpret_macd(macd_data)}"
            )
        else:
            macd_text = "Chua du du lieu (35 phien)"

        # Overall
        score_total = 0
        if rsi and rsi <= 30: score_total += 2
        elif rsi and rsi >= 70: score_total -= 2
        if crossover == "GOLDEN_CROSS": score_total += 3
        elif crossover == "DEATH_CROSS": score_total -= 3
        if bb and bb["position"] <= 0.2: score_total += 1
        elif bb and bb["position"] >= 0.8: score_total -= 1
        if macd_data and macd_data["crossover"] == "BULLISH": score_total += 2
        elif macd_data and macd_data["crossover"] == "BEARISH": score_total -= 2

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
            f"<b>MACD</b>\n   {macd_text}\n\n"
            f"<b>Tong hop:</b> {verdict}\n\n"
            f"🔗 <a href=\"{url}\">Xem chi tiet {symbol}</a>"
        ))

        # Send candlestick chart
        from src.charting.chart_generator import generate_candlestick
        chart_bytes = generate_candlestick(symbol, hist)
        if chart_bytes:
            self._send_photo(chat_id, chart_bytes, f"📈 {symbol} - {len(hist)} phien")

    def _cmd_report(self, chat_id):
        from src.analysis.daily_report import generate_daily_report
        from src.data.price_history import save_daily_prices

        self._send(chat_id, "⏳ Dang tao bao cao, vui long cho...")

        try:
            df = self._fetch_data()
            if df is None:
                return self._send(chat_id, "Khong lay duoc du lieu.")

            save_daily_prices(df)
            messages = generate_daily_report(df)
            for msg in messages:
                self._send(chat_id, msg)
        except Exception as e:
            logger.error(f"Report error:\n{traceback.format_exc()}")
            self._send(chat_id, f"❌ Loi khi tao bao cao: {e}")

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

    # === NEW: /alert ===
    def _cmd_alert(self, chat_id, args):
        import re
        from src.data.price_alert import add_alert, get_alerts

        # /alert without args: show current alerts
        if not args:
            alerts = get_alerts(str(chat_id))
            if not alerts:
                return self._send(chat_id,
                    "Chua co canh bao nao.\n\n"
                    "Dung: /alert <b>MA &gt;GIA</b> hoac /alert <b>MA &lt;GIA</b>\n"
                    "VD: /alert VNM &gt;50000\n"
                    "VD: /alert HPG &lt;20000"
                )
            lines = [f"<b>🔔 CANH BAO GIA ({len(alerts)})</b>\n"]
            for a in alerts:
                lines.append(f"#{a['id']} <b>{a['symbol']}</b> {a['direction']} <code>{a['target_price']:,.0f}</code>")
            self._send(chat_id, "\n".join(lines))
            return

        raw = " ".join(args)
        match = re.match(r"([A-Za-z]+)\s*([><])\s*([\d,.]+)", raw)
        if not match:
            return self._send(chat_id,
                "Sai cu phap.\n\n"
                "Dung: /alert <b>MA &gt;GIA</b> hoac /alert <b>MA &lt;GIA</b>\n"
                "VD: /alert VNM &gt;50000"
            )

        symbol = match.group(1).upper()
        direction = match.group(2)
        price = float(match.group(3).replace(",", ""))

        alert_id = add_alert(str(chat_id), symbol, direction, price)
        arrow = "tang len" if direction == ">" else "giam xuong"
        self._send(chat_id,
            f"✅ Da dat canh bao #{alert_id}:\n"
            f"<b>{symbol}</b> khi gia {arrow} <code>{price:,.0f}</code>"
        )

    # === NEW: /ls ===
    def _cmd_lichsu(self, chat_id, args):
        if not args:
            return self._send(chat_id, "Dung: /ls <b>MA</b>\nVD: /ls VNM")

        symbol = args[0].upper()
        days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10

        from src.data.price_history import get_price_history
        hist = get_price_history(symbol, days=days + 5)
        if hist.empty:
            return self._send(chat_id, f"Chua co du lieu lich su cho <b>{symbol}</b>.")

        hist = hist.tail(days)
        lines = [f"<b>📜 LICH SU: {symbol} ({len(hist)} phien)</b>\n"]
        lines.append("<code>Ngay       | Dong      | +/-  %</code>")
        lines.append("<code>———————————|———————————|————————</code>")

        prev_close = None
        for _, row in hist.iterrows():
            date_str = row["date"][-5:]  # MM-DD
            close = row["close"]
            if prev_close and prev_close > 0:
                pct = (close - prev_close) / prev_close * 100
                sign = "+" if pct >= 0 else ""
                pct_str = f"{sign}{pct:.1f}%"
            else:
                pct_str = "  —"
            lines.append(f"<code>{date_str}      | {close:>9,.0f} | {pct_str:>6}</code>")
            prev_close = close

        self._send(chat_id, "\n".join(lines))

        # Send chart
        from src.charting.chart_generator import generate_candlestick
        chart_bytes = generate_candlestick(symbol, hist)
        if chart_bytes:
            self._send_photo(chat_id, chart_bytes, f"📈 {symbol} - {len(hist)} phien")

    # === NEW: /ss ===
    def _cmd_sosanh(self, chat_id, args):
        if len(args) < 2:
            return self._send(chat_id, "Dung: /ss <b>MA1 MA2 ...</b>\nVD: /ss VNM VIC HPG")

        symbols = [a.upper() for a in args[:5]]  # Max 5

        df = self._fetch_data()
        if df is None:
            return self._send(chat_id, "Khong lay duoc du lieu.")

        from src.data.price_history import get_price_history
        from src.analysis.technical import calc_rsi

        lines = [f"<b>📊 SO SANH: {' vs '.join(symbols)}</b>\n"]
        lines.append("<code>Ma    | Gia       | +/-%    | KL       | RSI</code>")
        lines.append("<code>——————|———————————|—————————|——————————|————</code>")

        for sym in symbols:
            match = df[df["symbol"] == sym]
            if match.empty:
                lines.append(f"<code>{sym:<5} | Khong tim thay</code>")
                continue

            row = match.iloc[0]
            pct = row.get("profit_pct", 0)
            sign = "+" if pct >= 0 else ""
            vol = _format_volume(row["volume"])

            hist = get_price_history(sym, days=30)
            rsi_val = "—"
            if not hist.empty and len(hist) >= 15:
                rsi = calc_rsi(hist["close"].tolist())
                if rsi is not None:
                    rsi_val = f"{rsi:.0f}"

            lines.append(
                f"<code>{sym:<5} | {row['close']:>9,.0f} | {sign}{pct:>5.2f}%  | {vol:>8} | {rsi_val:>3}</code>"
            )

        self._send(chat_id, "\n".join(lines))

    # === NEW: /nganh ===
    def _cmd_nganh(self, chat_id, args):
        from src.data.sector_map import SECTORS, get_sector_for_symbol

        df = self._fetch_data()
        if df is None:
            return self._send(chat_id, "Khong lay duoc du lieu.")

        # If specific sector requested
        if args:
            keyword = " ".join(args).lower()
            matched_sector = None
            for sname in SECTORS:
                if keyword in sname.lower():
                    matched_sector = sname
                    break
            if not matched_sector:
                sector_list = "\n".join(f"• {s}" for s in SECTORS.keys())
                return self._send(chat_id, f"Khong tim thay nganh '{keyword}'.\n\n<b>Cac nganh:</b>\n{sector_list}")

            sector_symbols = SECTORS[matched_sector]
            sector_df = df[df["symbol"].isin(sector_symbols)]
            if sector_df.empty:
                return self._send(chat_id, f"Khong co du lieu cho nganh <b>{matched_sector}</b>.")

            avg_pct = sector_df["profit_pct"].mean()
            sign = "+" if avg_pct >= 0 else ""
            lines = [f"<b>🏢 {matched_sector}</b> (TB: {sign}{avg_pct:.2f}%)\n"]
            for _, row in sector_df.sort_values("profit_pct", ascending=False).iterrows():
                s = "+" if row["profit_pct"] >= 0 else ""
                vol = _format_volume(row["volume"])
                lines.append(f"<b>{row['symbol']}</b> {s}{row['profit_pct']:.2f}% | <code>{row['close']:,.0f}</code> | KL: {vol}")
            self._send(chat_id, "\n".join(lines))
            return

        # Overview of all sectors
        sector_stats = []
        for sname, syms in SECTORS.items():
            sector_df = df[df["symbol"].isin(syms)]
            if sector_df.empty:
                continue
            avg_pct = sector_df["profit_pct"].mean()
            up = len(sector_df[sector_df["profit_pct"] > 0])
            down = len(sector_df[sector_df["profit_pct"] < 0])
            total = len(sector_df)
            sector_stats.append((sname, avg_pct, up, down, total))

        sector_stats.sort(key=lambda x: x[1], reverse=True)

        lines = ["<b>🏢 BAO CAO NGANH</b>\n"]
        for sname, avg_pct, up, down, total in sector_stats:
            sign = "+" if avg_pct >= 0 else ""
            emoji = "🟢" if avg_pct > 0.5 else "🔴" if avg_pct < -0.5 else "⚪"
            lines.append(f"{emoji} <b>{sname}</b>: {sign}{avg_pct:.2f}% ({up}↑ {down}↓ / {total})")

        self._send(chat_id, "\n".join(lines))

    # === NEW: /export ===
    def _cmd_export(self, chat_id):
        import io
        from datetime import datetime

        self._send(chat_id, "⏳ Dang xuat du lieu...")

        df = self._fetch_data()
        if df is None:
            return self._send(chat_id, "Khong lay duoc du lieu.")

        export_df = df[["symbol", "open", "close", "high", "low", "ceiling", "floor", "volume", "profit_pct"]].copy()
        export_df = export_df.sort_values("profit_pct", ascending=False)
        export_df.columns = ["Ma", "Mo", "Dong", "Cao", "Thap", "Tran", "San", "KL", "% Loi nhuan"]

        buf = io.BytesIO()
        export_df.to_csv(buf, index=False, encoding="utf-8-sig")
        buf.seek(0)

        today = datetime.now().strftime("%Y%m%d")
        filename = f"stock_data_{today}.csv"
        self._send_document(chat_id, buf.read(), filename, f"📊 Du lieu {len(export_df)} ma - {today}")

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
