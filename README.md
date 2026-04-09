# Vietnam Stock Tracker

Giam sat toan bo co phieu HOSE/HNX (~700+ ma), tinh % loi nhuan, gui canh bao qua Telegram cho cac ma tang >1%. Chay tu dong moi 5 phut trong gio giao dich.

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
# Chay 1 lan (test)
python main.py --once

# Chay lien tuc (scheduler moi 5 phut)
python main.py
```

## Cau truc

```
stock-tracker/
  main.py               # Entry point + scheduler
  config.py             # Cau hinh tu .env
  src/
    data/               # Lay du lieu gia, danh sach ma
    analysis/           # Tinh % loi nhuan
    charting/           # Tao bieu do PNG
    notifications/      # Gui Telegram
    utils/              # Logger, cache, gio giao dich
  data/                 # Cache + charts
  logs/                 # Log files
```
