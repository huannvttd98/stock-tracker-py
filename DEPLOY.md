# Deploy Stock Tracker len Ubuntu Server

## 1. Yeu cau

- Ubuntu 24.04 LTS
- CPU: 1 core (toi thieu)
- RAM: 1GB
- Disk: 20GB
- Python 3.12+ (co san tren Ubuntu 24.04)
- Git
- Quyen sudo

## 2. Cai dat moi truong

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

## 3. Clone du an

```bash
cd /opt
sudo git clone <URL_REPO> stock-tracker
sudo chown -R $USER:$USER /opt/stock-tracker
cd /opt/stock-tracker
```

## 4. Tao virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Cau hinh

```bash
cp .env.example .env
nano .env
```

Dien cac gia tri:

```ini
# Telegram bot (bat buoc)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# So ma top KL gui moi 5 phut (mac dinh: 10)
TOP_VOLUME_COUNT=10

# Watchlist: chi bao khi bien dong >= X% (mac dinh: 2%)
WATCHLIST_ALERT_PCT=2.0

# Dot bien KL: bao khi KL >= Xx trung binh 20 phien (mac dinh: 2x)
VOLUME_SPIKE_MULTIPLIER=2.0

# Chu ky quet (phut)
SCHEDULE_INTERVAL_MINUTES=5

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

> Neu chua co chat_id, chay `python3 main.py --setup` de thiet lap qua QR code.

## 6. Test thu

```bash
source /opt/stock-tracker/.venv/bin/activate

# Test gui tin nhan Telegram (top KL)
python3 main.py --test

# Test gui bao cao cuoi ngay
python3 main.py --report
```

## 7. Chay bang systemd

Tao service file:

```bash
sudo nano /etc/systemd/system/stock-tracker.service
```

Noi dung:

```ini
[Unit]
Description=Vietnam Stock Tracker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/stock-tracker
ExecStart=/opt/stock-tracker/.venv/bin/python3 main.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal
EnvironmentFile=/opt/stock-tracker/.env

[Install]
WantedBy=multi-user.target
```

> Thay `User=root` bang user thuc te cua ban.

Kich hoat service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable stock-tracker
sudo systemctl start stock-tracker
sudo systemctl status stock-tracker
```

## 8. Ung dung se tu dong chay

Khi service start, app se:

| Tinh nang | Lich chay |
|---|---|
| Top KL + Tran/San + Dot bien KL | Moi 5 phut (trong gio giao dich) |
| Canh bao gia muc tieu (/alert) | Moi 5 phut (kiem tra va gui thong bao) |
| Bao cao cuoi ngay | 15:05 Thu 2 - Thu 6 |
| Telegram bot (lenh /top, /gia...) | Luon luon lang nghe |
| Watchlist alerts | Moi 5 phut (kiem tra ma da theo doi) |

### Lenh Telegram bot

Gui truc tiep cho bot tren Telegram:

```
/top         - Top 10 KL giao dich lon nhat
/gia VNM     - Xem gia 1 ma bat ky
/tran        - Cac ma dang cham tran
/san         - Cac ma dang cham san
/goiy        - Goi y ma nen theo doi
/pt VNM      - Phan tich ky thuat + MACD + bieu do nen
/ls VNM      - Lich su gia 10 phien (hoac /ls VNM 20)
/ss VNM VIC HPG - So sanh nhieu ma (toi da 5)
/alert VNM >50000 - Canh bao khi gia tang len 50,000
/alert VNM <20000 - Canh bao khi gia giam xuong 20,000
/alert       - Xem danh sach canh bao dang hoat dong
/nganh       - Bao cao tong hop theo nganh
/nganh ngan hang - Xem chi tiet 1 nganh
/report      - Bao cao tong hop thi truong
/export      - Xuat du lieu CSV gui qua Telegram
/hocpt       - Giai thich cach doc phan tich ky thuat
/watch VNM   - Them ma vao watchlist ca nhan
/unwatch VNM - Bo ma khoi watchlist
/list        - Xem watchlist cua ban
/help        - Xem tat ca lenh
```

## 9. Xem log

```bash
# Log realtime
sudo journalctl -u stock-tracker -f

# Log file
tail -f /opt/stock-tracker/logs/stock_tracker.log
```

## 10. Quan ly service

```bash
# Dung
sudo systemctl stop stock-tracker

# Khoi dong lai
sudo systemctl restart stock-tracker

# Tat tu dong chay khi boot
sudo systemctl disable stock-tracker
```

## 11. Cap nhat code

```bash
cd /opt/stock-tracker
sudo systemctl stop stock-tracker
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl start stock-tracker
```

## 12. Cau truc du lieu

App luu du lieu tai `data/`:

```
data/
  price_history.db    # Lich su gia OHLCV hang ngay (SQLite, tu dong tao)
  volume_history.db   # KL giao dich hang ngay (SQLite, tu dong tao)
  watchlist.db        # Watchlist ca nhan (SQLite, tu dong tao)
  alerts.db           # Canh bao gia muc tieu (SQLite, tu dong tao)
  symbols_cache.json  # Cache danh sach ma (lam moi moi 24h)
  charts/             # Bieu do nen PNG (tam thoi)
```

> Du lieu SQLite se tu dong duoc tao khi app chay lan dau.
> Phat hien dot bien KL can it nhat 3 ngay du lieu de tinh trung binh.
> Phan tich ky thuat (RSI, MACD) can it nhat 14-35 phien du lieu.
