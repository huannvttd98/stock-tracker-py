# Deploy Stock Tracker len Ubuntu Server

## 1. Yeu cau

- Ubuntu 24.04 LTS
- CPU: 1 core (toi thieu)
- RAM: 1GB (toi thieu, nen them swap 1GB)
- Disk: 20GB
- Python 3.12+ (co san tren Ubuntu 24.04)
- Git
- Quyen sudo

## 2. Tao swap (bat buoc voi RAM 1GB)

RAM 1GB vua du nhung co the thieu khi fetch 700+ ma cung luc. Them 1GB swap de phong:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Luu swap vinh vien (tu dong mount khi reboot)
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Kiem tra
free -h
```

## 3. Cai dat moi truong

> Luu y: Ubuntu 24.04 da co san Python 3.12, chi can cai them pip va venv.

```bash
# Cap nhat he thong
sudo apt update && sudo apt upgrade -y

# Cai cac goi can thiet (Python 3.12 da co san tren Ubuntu 24.04)
sudo apt install -y python3 python3-pip python3-venv git

# Kiem tra phien ban
python3 --version   # >= 3.12
```

## 4. Clone du an

```bash
cd /opt
sudo git clone <URL_REPO> stock-tracker
sudo chown -R $USER:$USER /opt/stock-tracker
cd /opt/stock-tracker
```

## 5. Tao virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Cau hinh

```bash
cp .env.example .env
nano .env
```

Dien cac gia tri:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
DATA_SOURCE=vnstock
PROFIT_THRESHOLD=1.0
SCHEDULE_INTERVAL_MINUTES=5
```

> Neu chua co chat_id, chay `python3 main.py --setup` de thiet lap qua QR code.

## 7. Test thu

```bash
# Kich hoat venv
source /opt/stock-tracker/.venv/bin/activate

# Chay 1 lan de test
python3 main.py --test
```

## 8. Chay bang systemd (khuyen dung)

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
User=ubuntu
WorkingDirectory=/opt/stock-tracker
ExecStart=/opt/stock-tracker/.venv/bin/python3 main.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

# Bien moi truong (hoac dung file .env)
EnvironmentFile=/opt/stock-tracker/.env

[Install]
WantedBy=multi-user.target
```

> Thay `User=ubuntu` bang user thuc te cua ban.

Kich hoat service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Bat service
sudo systemctl enable stock-tracker
sudo systemctl start stock-tracker

# Kiem tra trang thai
sudo systemctl status stock-tracker
```

## 9. Xem log

```bash
# Log cua systemd
sudo journalctl -u stock-tracker -f

# Log cua ung dung
tail -f /opt/stock-tracker/logs/stock_tracker.log
```

## 10. Cac lenh quan ly

```bash
# Dung service
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

## 12. (Tuy chon) Cai dat Firewall

```bash
# Chi cho phep SSH
sudo ufw allow OpenSSH
sudo ufw enable
```

## 13. (Tuy chon) Tu dong khoi dong lai hang ngay

Them cron job de restart service moi sang truoc gio giao dich:

```bash
crontab -e
```

Them dong:

```
0 8 * * 1-5 sudo systemctl restart stock-tracker
```

> Restart luc 8:00 sang moi ngay tu Thu 2 - Thu 6.
