# Vietnam Stock Tracker

Giam sat toan bo co phieu HOSE/HNX (~700+ ma), tinh % loi nhuan, gui canh bao qua Telegram cho cac ma tang >1%. Chay tu dong moi 5 phut trong gio giao dich.

---

## Huong dan doc du an

> Neu ban moi tiep can du an, hay doc theo thu tu duoi day de nam duoc toan bo kien truc va luong du lieu.

### Buoc 1: Hieu cau hinh va entry point

1. **`config.py`** — Doc truoc nhat. File nay load bien moi truong tu `.env` va dinh nghia cac hang so dung trong toan bo du an: Telegram token, chat ID, nguong volume, tan suat lap lich...
2. **`main.py`** — Diem khoi dau cua ung dung. Doc ham `main()` (dong 160+) de hieu cac che do chay: `--once`, `--test`, `--report`, `--setup`, va che do scheduler. Sau do doc ham `run_tracking_cycle()` (dong 12–88) — day la ham cot loi, goi tuan tu qua tat ca module theo dung thu tu xu ly du lieu.

### Buoc 2: Luong du lieu (`src/data/`)

Doc theo thu tu du lieu di chuyen trong he thong:

3. **`src/data/cafef_fetcher.py`** — Nguon du lieu chinh. Fetch gia tat ca co phieu HOSE/HNX tu CafeF API, tra ve DataFrame voi cac cot: symbol, open, high, low, close, volume (don vi: 1000 VND).
4. **`src/data/price_history.py`** — Luu lich su gia vao SQLite. Cac ham `save_daily_prices()`, `get_price_history()`, `get_all_close_prices()` duoc goi boi nhieu module khac.
5. **`src/data/volume_history.py`** — Phat hien dot bien khoi luong (`detect_volume_spikes()`). So sanh volume hom nay voi trung binh nhieu ngay truoc.
6. **`src/data/symbol_manager.py`** — Quan ly danh sach ma co phieu, cache vao `data/symbols_cache.json` (lam moi moi 24h).
7. **`src/data/watchlist.py`** — Watchlist rieng tung user (theo chat_id), luu trong SQLite. Cho phep nguoi dung theo doi ma cu the.
8. **`src/data/yfinance_fetcher.py`** — Du phong: fetch du lieu tu Yahoo Finance khi CafeF khong kha dung.

### Buoc 3: Phan tich (`src/analysis/`)

Du lieu sau khi fetch se di qua cac module phan tich:

9. **`src/analysis/profit_calculator.py`** — Tinh `profit_pct = (close - open) / open * 100`. Loc top N theo volume, format tin nhan tong hop.
10. **`src/analysis/ceiling_floor.py`** — Phat hien ma cham tran (tang kich bien) va cham san (giam kich bien).
11. **`src/analysis/technical.py`** — Phan tich ky thuat: RSI (14 phien), MA crossover (SMA 5/20), Bollinger Bands (20 phien), MACD (12,26,9). Ham `analyze_symbol()` tra ve diem tong hop.
12. **`src/analysis/stock_suggestion.py`** — He thong cham diem goi y co phieu. Ket hop: dot bien KL (3 diem), % gia (2 diem), gan tran (2 diem), tin hieu ky thuat (2 diem). Ma dat >= 3 diem moi duoc goi y.
13. **`src/analysis/daily_report.py`** — Tao bao cao cuoi ngay tong hop: top tang/giam, tran/san, dot bien KL, tin hieu ky thuat, goi y.

### Buoc 4: Gui thong bao (`src/notifications/`)

14. **`src/notifications/telegram_bot.py`** — Lop `TelegramNotifier` boc Telegram Bot API. Hai ham chinh: `send_message()` va `send_alert()` (gui nhieu tin nhan).
15. **`src/notifications/telegram_commands.py`** — Bot xu ly lenh tu nguoi dung: `/top`, `/gia <MA>`, `/tran`, `/san`, `/goiy`, `/pt <MA>` (phan tich ky thuat + MACD + bieu do nen), `/ls <MA>` (lich su gia), `/ss <MA1 MA2...>` (so sanh ma), `/alert <MA >GIA>` (canh bao gia), `/nganh` (bao cao nganh), `/report` (bao cao tong hop), `/export` (xuat CSV), `/watch`, `/unwatch`, `/list`, `/hocpt`. Chay polling trong background thread.
16. **`src/notifications/telegram_setup.py`** — Setup bot lan dau: tao QR code de link Telegram, poll cho den khi user gui `/start`, tu dong luu `chat_id` vao `.env`.

### Buoc 5: Bao cao & tien ich

17. **`src/report/html_report.py`** — Tao bao cao HTML tuong tac (dark theme), ho tro tim kiem, sap xep, loc du lieu.
18. **`src/utils/logger.py`** — Logging ra console + file (rotating). Decorator `@timed` do thoi gian thuc thi ham.
19. **`src/utils/market_hours.py`** — Kiem tra gio giao dich VN: sang 08:45-11:45, chieu 12:45-15:00 (ICT), thu 2-6.
20. **`src/utils/cache.py`** — Cache don gian dua tren file JSON voi TTL (mac dinh 24h).

### So do luong du lieu

```
CafeF API ──fetch──> DataFrame (OHLCV)
                         │
                    save to SQLite
                         │
                ┌────────┼────────────┬──────────────┐
                v        v            v              v
          profit_pct  ceiling/floor  volume_spikes  technical
                │        │            │         (RSI/MA/BB/MACD)
                └────────┴────────────┴──────────────┘
                                │
                    ┌───────────┼───────────┐
                    v           v           v
              Telegram Bot   Daily Report  HTML Report
              (real-time)    (15:05 daily)  (report.html)
                  │
     ┌────────────┼────────────────────┐
     v            v                    v
  /top /gia    /pt (chart+MACD)     /alert (gia muc tieu)
  /tran /san   /ls (lich su)        /nganh (sector)
  /goiy        /ss (so sanh)        /export (CSV)
```

---

## Cai dat

```bash
# Clone va tao virtual environment
cd stock-tracker
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

# Cai thu vien
pip install -r requirements.txt
```

> Luu y: Luon kich hoat venv truoc khi chay bat ky lenh nao (`activate`).

## Cau hinh

```bash
# Copy file mau
cp .env.example .env
# Sua .env: dien TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID
```

## Setup Telegram Bot

### Cach 1: Tu dong qua QR code (khuyen dung)

1. Mo Telegram, tim `@BotFather`, gui `/newbot` de tao bot
2. Copy bot token
3. Chay lenh setup:
   ```bash
   python main.py --setup
   ```
4. Nhap bot token khi duoc hoi (hoac dien san trong `.env`)
5. Quet ma QR hien tren terminal bang Telegram
6. Gui `/start` cho bot -> app tu dong luu `chat_id` vao `.env`

### Cach 2: Thu cong

1. Mo Telegram, tim `@BotFather`
2. Gui `/newbot`, dat ten bot
3. Copy bot token (dang `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. Gui 1 tin nhan bat ky cho bot cua ban
5. Truy cap `https://api.telegram.org/bot<TOKEN>/getUpdates` -> lay `chat.id`
6. Dien token va chat_id vao file `.env`

## Su dung

```bash
# Kich hoat virtual environment truoc khi chay
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Linux/Mac

# Chay 1 lan (test)
python main.py --once

# Chay lien tuc (scheduler moi 5 phut)
python main.py

# Chay test (bo qua gio giao dich)
python main.py --test

# Tao bao cao ngay
python main.py --report

# Setup Telegram bot
python main.py --setup
```

## Cau truc

```
stock-tracker/
  main.py               # Entry point + scheduler
  config.py             # Cau hinh tu .env
  src/
    data/               # Lay du lieu gia, danh sach ma, canh bao gia, nganh
    analysis/           # Tinh % loi nhuan, phan tich ky thuat (RSI, MA, BB, MACD)
    charting/           # Tao bieu do nen (candlestick) PNG
    notifications/      # Gui Telegram + command bot
    report/             # Bao cao HTML
    utils/              # Logger, cache, gio giao dich
  data/                 # Cache + charts
  logs/                 # Log files
```
