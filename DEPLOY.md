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
# Cap nhat he thong
sudo apt update && sudo apt upgrade -y

# Cai cac goi can thiet (Python 3.12 da co san tren Ubuntu 24.04)
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

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TOP_VOLUME_COUNT=10
SCHEDULE_INTERVAL_MINUTES=5
```

> Neu chua co chat_id, chay `python3 main.py --setup` de thiet lap qua QR code.

## 6. Test thu

```bash
source /opt/stock-tracker/.venv/bin/activate

# Chay 1 lan de test (gui Telegram)
python3 main.py --test
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

## 8. Xem log

```bash
# Log cua systemd
sudo journalctl -u stock-tracker -f

# Log cua ung dung
tail -f /opt/stock-tracker/logs/stock_tracker.log
```

## 9. Cac lenh quan ly

```bash
# Dung service
sudo systemctl stop stock-tracker

# Khoi dong lai
sudo systemctl restart stock-tracker

# Tat tu dong chay khi boot
sudo systemctl disable stock-tracker
```

## 10. Cap nhat code

```bash
cd /opt/stock-tracker
sudo systemctl stop stock-tracker
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl start stock-tracker
```
