import base64
import io
import os
import sys
import time
import webbrowser

import requests
import qrcode
import qrcode.image.pil

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
POLL_INTERVAL = 2
POLL_TIMEOUT = 120  # 2 minutes


def _api(token: str, method: str, **params):
    url = TELEGRAM_API.format(token=token, method=method)
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"Telegram API error: {data.get('description', 'Unknown')}")
    return data["result"]


def _get_bot_info(token: str) -> dict:
    return _api(token, "getMe")


def _generate_qr_html(url: str, bot_username: str):
    """Generate QR code as HTML page and open in browser."""
    import config

    # Generate QR as PNG in memory
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Setup Telegram Bot</title>
<style>
  body {{ background: #0f1117; color: #e1e4e8; font-family: 'Segoe UI', sans-serif;
         display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 16px;
           padding: 40px; text-align: center; max-width: 440px; }}
  h1 {{ color: #58a6ff; font-size: 22px; margin-bottom: 8px; }}
  .bot {{ color: #3fb950; font-size: 18px; margin-bottom: 24px; }}
  .qr {{ background: white; border-radius: 12px; padding: 16px; display: inline-block; margin-bottom: 24px; }}
  .qr img {{ width: 280px; height: 280px; display: block; }}
  .steps {{ text-align: left; color: #8b949e; font-size: 14px; line-height: 2; }}
  .steps b {{ color: #e1e4e8; }}
  .link {{ margin-top: 20px; }}
  .link a {{ color: #58a6ff; text-decoration: none; font-size: 13px; word-break: break-all; }}
  .link a:hover {{ text-decoration: underline; }}
  .waiting {{ margin-top: 24px; padding: 12px; background: #1c2128; border-radius: 8px;
              color: #d29922; font-size: 14px; animation: pulse 2s infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
</style></head><body>
<div class="card">
  <h1>Setup Telegram Bot</h1>
  <div class="bot">@{bot_username}</div>
  <div class="qr"><img src="data:image/png;base64,{qr_b64}" alt="QR Code"></div>
  <div class="steps">
    <b>1.</b> Mo Telegram tren dien thoai<br>
    <b>2.</b> Quet ma QR phia tren<br>
    <b>3.</b> Nhan <b>Start</b> hoac gui <b>/start</b>
  </div>
  <div class="link">Hoac mo link: <a href="{url}" target="_blank">{url}</a></div>
  <div class="waiting">Dang cho ket noi... (quay lai terminal sau khi gui /start)</div>
</div></body></html>"""

    html_path = os.path.join(config.BASE_DIR, "setup_telegram.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    webbrowser.open(f"file:///{os.path.abspath(html_path)}")
    print(f"  Da mo trang QR code trong trinh duyet.")
    return html_path


def _flush_old_updates(token: str) -> int:
    """Clear pending updates, return latest update_id."""
    try:
        updates = _api(token, "getUpdates", offset=-1)
        if updates:
            return updates[-1]["update_id"]
    except Exception:
        pass
    return 0


def _poll_for_start(token: str, last_update_id: int) -> str:
    """Poll for /start message, return chat_id."""
    print(f"\nDang cho ban quet QR va gui /start... (timeout {POLL_TIMEOUT}s)")
    start_time = time.time()

    while time.time() - start_time < POLL_TIMEOUT:
        try:
            updates = _api(token, "getUpdates", offset=last_update_id + 1, timeout=5)
            for update in updates:
                last_update_id = update["update_id"]
                message = update.get("message", {})
                text = message.get("text", "")
                chat = message.get("chat", {})
                chat_id = str(chat.get("id", ""))

                if text.startswith("/start") and chat_id:
                    user = message.get("from", {})
                    name = user.get("first_name", "") or user.get("username", "")
                    print(f"\n  Ket noi thanh cong voi: {name} (chat_id: {chat_id})")
                    return chat_id
        except Exception as e:
            logger.debug(f"Poll error: {e}")

        time.sleep(POLL_INTERVAL)

    return ""


def _save_to_env(token: str, chat_id: str):
    """Save or update TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file."""
    import config
    env_path = os.path.join(config.BASE_DIR, ".env")

    # Read existing content
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Update or append values
    token_found = False
    chat_id_found = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TELEGRAM_BOT_TOKEN="):
            new_lines.append(f"TELEGRAM_BOT_TOKEN={token}\n")
            token_found = True
        elif stripped.startswith("TELEGRAM_CHAT_ID="):
            new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
            chat_id_found = True
        else:
            new_lines.append(line)

    if not token_found:
        new_lines.append(f"TELEGRAM_BOT_TOKEN={token}\n")
    if not chat_id_found:
        new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"  Da luu vao {env_path}")


def _send_welcome(token: str, chat_id: str):
    """Send confirmation message to the connected chat."""
    url = TELEGRAM_API.format(token=token, method="sendMessage")
    requests.post(url, json={
        "chat_id": chat_id,
        "text": "✅ Ket noi thanh cong!\nBot Stock Tracker da san sang gui canh bao cho ban.",
    }, timeout=10)


def run_setup(token: str = None):
    """Interactive Telegram setup via QR code."""
    print("\n=== SETUP TELEGRAM BOT ===\n")

    # 1. Get token
    if not token:
        token = input("Nhap Bot Token (tu @BotFather): ").strip()
    if not token:
        print("Loi: Token khong duoc de trong.")
        return False

    # 2. Verify token & get bot info
    try:
        bot = _get_bot_info(token)
    except Exception as e:
        print(f"Loi: Token khong hop le - {e}")
        return False

    bot_username = bot.get("username", "")
    print(f"  Bot: @{bot_username}")

    # 3. Generate QR code and open in browser
    bot_url = f"https://t.me/{bot_username}?start=setup"
    _generate_qr_html(bot_url, bot_username)
    print(f"  Link: {bot_url}")

    # 4. Flush old updates & poll for /start
    last_id = _flush_old_updates(token)
    chat_id = _poll_for_start(token, last_id)

    if not chat_id:
        print("\n  Het thoi gian cho. Vui long thu lai.")
        return False

    # 5. Save to .env
    _save_to_env(token, chat_id)

    # 6. Send welcome message
    _send_welcome(token, chat_id)

    print("\n  Setup hoan tat! Chay `python main.py --once` de test.\n")
    return True
