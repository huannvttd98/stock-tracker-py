# Vietnam Stock Tracker - Project Plan

## Muc tieu

Xay dung ung dung Python giam sat toan bo co phieu HOSE/HNX (~700+ ma),
tinh % loi nhuan, gui canh bao qua Telegram cho cac ma tang >1%.
Chay tu dong moi 5 phut trong gio giao dich.

---

## Cong nghe su dung

| Thanh phan | Cong nghe | Ly do |
|------------|-----------|-------|
| Du lieu gia | `vnstock` (chinh), `yfinance` (du phong) | vnstock thiet ke rieng cho VN, khong rate-limit, khong can API key |
| Bieu do | `matplotlib` | Tao PNG gui qua Telegram |
| Lap lich | `APScheduler` | Ho tro timezone Asia/Ho_Chi_Minh, xu ly missed-fire |
| Telegram | `requests` truc tiep Bot API | Don gian hon thu vien python-telegram-bot |
| Danh sach ma | `vnstock.Listing().all_symbols()` | Cache daily trong JSON |

---

## Cau truc thu muc

```
stock-tracker/
  main.py                         # Entry point + scheduler
  config.py                       # Load .env config
  requirements.txt                # Thu vien Python
  .env.example                    # Mau cau hinh
  .env                            # Cau hinh thuc (gitignored)
  .gitignore
  README.md                       # Huong dan cai dat + setup Telegram bot
  PLAN.md                         # File nay
  
  src/
    __init__.py
    data/
      __init__.py
      symbol_manager.py           # Lay & cache danh sach ma HOSE/HNX
      price_fetcher.py            # Abstract base class
      vnstock_fetcher.py          # vnstock implementation (chinh)
      yfinance_fetcher.py         # yfinance fallback
    analysis/
      __init__.py
      profit_calculator.py        # Tinh % loi nhuan, loc > 1%
    charting/
      __init__.py
      chart_generator.py          # Tao bieu do PNG bang matplotlib
    notifications/
      __init__.py
      telegram_bot.py             # Gui tin nhan + anh qua Telegram
    utils/
      __init__.py
      logger.py                   # Rotating file + console logging, @timed decorator
      market_hours.py             # Kiem tra gio giao dich VN (9:00-11:30, 13:00-14:45)
      cache.py                    # File-based cache voi TTL
  
  data/
    symbols_cache.json            # Tu dong tao
    charts/                       # Luu tam bieu do PNG
  
  logs/                           # Log file
```

---

## Thu vien (requirements.txt)

```
vnstock>=3.0.9             # Du lieu thi truong VN
yfinance>=0.2.36           # Du phong
pandas>=1.5.0              # Xu ly du lieu
matplotlib>=3.5.0          # Tao bieu do
requests>=2.28.0           # HTTP cho Telegram API
apscheduler>=3.10.0        # Lap lich
python-dotenv>=1.0.0       # Doc file .env
```

---

## Luong du lieu (moi chu ky 5 phut)

```
[1. Symbol Manager]
    Load danh sach ma tu cache (lam moi neu > 24h)
    ~700+ ma HOSE/HNX
        |
        v
[2. Price Fetcher]
    Lay gia bang ThreadPoolExecutor (10 workers, batch 50 ma)
    vnstock Quote(symbol).history()
    -> DataFrame: symbol, open, high, low, close, volume
        |
        v
[3. Profit Calculator]
    profit_pct = (close - open) / open * 100
    Loc: chi giu ma co profit_pct > 1%
    Sap xep giam dan theo profit_pct
        |
        v
[4. Chart Generator]  (chi cho cac ma da loc ~20-50 ma)
    Tao bieu do PNG cho tung ma
    Luu vao data/charts/{symbol}_{date}.png
        |
        v
[5. Telegram Notifier]
    Gui tin tong hop: "Tim thay 28 ma tang >1%"
    Gui tung ma: "{SYMBOL}: +2.5% | Mo: 25,000 | Dong: 25,625"
    Dinh kem bieu do PNG
    Gioi han: toi da 20 ma/lan gui
```

---

## Cau hinh (.env)

```env
# === Telegram ===
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# === Nguon du lieu ===
DATA_SOURCE=vnstock          # hoac "yfinance"

# === Nguong loc ===
PROFIT_THRESHOLD=1.0         # phan tram
MAX_TELEGRAM_SYMBOLS=20      # so ma toi da gui Telegram

# === Lap lich ===
SCHEDULE_INTERVAL_MINUTES=5

# === Hieu nang ===
FETCH_BATCH_SIZE=50
FETCH_WORKERS=10

# === Logging ===
LOG_LEVEL=INFO
```

---

## Chi tiet tung module

### 1. config.py
- Doc .env bang python-dotenv
- Cung cap cac hang so cau hinh cho toan bo ung dung
- Validation gia tri (dam bao token/chat_id khong rong)

### 2. src/utils/logger.py
- Python logging voi RotatingFileHandler (5MB, 3 backups)
- Format: `[2026-04-09 10:05:32] [INFO] [module_name] Message`
- Console handler co mau
- Decorator `@timed` do thoi gian thuc thi ham

### 3. src/utils/cache.py
- Doc/ghi JSON file voi timestamp
- Kiem tra TTL (mac dinh 24h cho symbol list)
- Xoa cache khi corrupt

### 4. src/data/symbol_manager.py
- `get_all_symbols()` -> DataFrame (ticker, name, exchange)
- Su dung vnstock Listing().all_symbols(source='VCI')
- Cache vao data/symbols_cache.json (refresh moi 24h)
- Loc chi HOSE va HNX (bo UPCOM)
- Fallback: static JSON file neu API fail

### 5. src/data/price_fetcher.py (Abstract)
```python
class PriceFetcher(ABC):
    @abstractmethod
    def fetch_batch(self, symbols: List[str], start: str, end: str) -> pd.DataFrame:
        """Tra ve DataFrame: symbol, time, open, high, low, close, volume"""
        pass
```

### 6. src/data/vnstock_fetcher.py
- Implements PriceFetcher
- ThreadPoolExecutor voi FETCH_WORKERS workers
- Xu ly tung batch FETCH_BATCH_SIZE ma
- Retry voi exponential backoff (1s, 2s, 4s)
- Log warning va skip khi 1 ma loi

### 7. src/data/yfinance_fetcher.py
- Implements PriceFetcher (du phong)
- Them suffix `.VN` cho moi ma
- yf.download(tickers=batch) theo chunk 80 ma
- Delay 2s giua cac chunk tranh rate-limit

### 8. src/analysis/profit_calculator.py
- `calculate_profits(df)` -> them cot profit_pct
- `filter_profitable(df, threshold=1.0)` -> loc va sap xep
- `generate_summary(filtered_df)` -> tao van ban tong hop cho Telegram

### 9. src/charting/chart_generator.py
- `generate_chart(symbol, price_data, output_dir)` -> duong dan file PNG
- Bieu do duong gia (xanh), volume (xam)
- Tieu de: "{SYMBOL} - {date} | +{profit}%"
- Kich thuoc: 800x400px
- Doc charts cu hon 24h

### 10. src/notifications/telegram_bot.py
- `TelegramNotifier(token, chat_id)`
- `send_message(text)` -> bool
- `send_photo(photo_path, caption)` -> bool
- `send_alert_batch(results)` -> gui toan bo ket qua
- Rate-limit: 0.05s delay giua cac tin
- Log loi nhung khong crash

### 11. src/utils/market_hours.py
- `is_market_open()` -> bool
- Gio giao dich HOSE/HNX: Thu 2-6, 9:00-11:30 va 13:00-14:45 ICT
- Them buffer 15 phut moi ben

### 12. main.py
- `run_tracking_cycle()` - 1 chu ky: fetch -> tinh -> ve -> gui
- `--once` flag: chay 1 lan roi thoat (de test)
- APScheduler BackgroundScheduler voi interval 5 phut
- Chi chay trong gio giao dich
- Bat moi exception o muc cao nhat, log traceback

---

## Chien luoc hieu nang

| Van de | Giai phap |
|--------|-----------|
| 700+ API calls | ThreadPoolExecutor, 10 workers, batch 50 |
| Danh sach ma it thay doi | Cache daily trong JSON |
| Tao bieu do | Chi tao cho ma da loc (khong phai 700+) |
| Telegram rate limit | Gioi han 20 ma, delay 0.05s giua tin |
| Gui trung lap | Skip neu cung ma da gui trong 15 phut |
| Ngoai gio giao dich | Bo qua chu ky, log info |

---

## Xu ly loi

- **1 ma fetch fail**: log warning, skip, tiep tuc
- **API fail hoan toan**: retry 3 lan voi exponential backoff, gui Telegram bao loi
- **Telegram fail**: log error, khong crash (chu ky sau gui lai)
- **Ngoai gio giao dich**: skip chu ky, log info
- **Cache corrupt**: xoa va fetch lai

---

## Thu tu implement

### Phase 1: Nen tang
1. Tao thu muc project, venv, requirements.txt, cai dat deps
2. config.py + .env.example + .gitignore
3. src/utils/logger.py
4. src/utils/cache.py

### Phase 2: Tang du lieu
5. src/data/symbol_manager.py
6. src/data/price_fetcher.py (abstract)
7. src/data/vnstock_fetcher.py
8. src/data/yfinance_fetcher.py

### Phase 3: Phan tich + Xuat
9. src/analysis/profit_calculator.py
10. src/charting/chart_generator.py
11. src/notifications/telegram_bot.py

### Phase 4: Tich hop
12. src/utils/market_hours.py
13. main.py
14. README.md

---

## Kiem tra

1. `python main.py --once` - test 1 chu ky
2. Kiem tra logs/stock_tracker.log
3. Xac nhan Telegram nhan duoc tin + bieu do
4. Test voi PROFIT_THRESHOLD=0.0 de xem toan bo ma
5. Test ngoai gio giao dich: phai skip
6. Chay scheduler 15+ phut trong gio giao dich

---

## Huong dan setup Telegram Bot

1. Mo Telegram, tim `@BotFather`
2. Gui `/newbot`, dat ten bot
3. Copy bot token (dang `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. Gui 1 tin nhan bat ky cho bot
5. Truy cap `https://api.telegram.org/bot<TOKEN>/getUpdates` -> lay `chat.id`
6. Dien token va chat_id vao file `.env`
