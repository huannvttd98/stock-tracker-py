import os
import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def generate_chart(symbol: str, price_data: pd.DataFrame, output_dir: str = None) -> str:
    if output_dir is None:
        output_dir = config.CHARTS_DIR

    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    filename = f"{symbol}_{today}.png"
    filepath = os.path.join(output_dir, filename)

    price_data = price_data.copy()
    price_data.columns = [c.lower() for c in price_data.columns]

    profit_pct = 0
    if "profit_pct" in price_data.columns:
        profit_pct = price_data["profit_pct"].iloc[-1]

    fig, ax1 = plt.subplots(figsize=(8, 4))

    # Price line
    if "time" in price_data.columns:
        x = price_data["time"]
    elif "date" in price_data.columns:
        x = price_data["date"]
    else:
        x = range(len(price_data))

    ax1.plot(x, price_data["close"], color="green", linewidth=1.5, label="Close")
    ax1.set_ylabel("Gia (VND)")
    ax1.set_title(f"{symbol} - {today} | +{profit_pct:.2f}%")

    # Volume bars
    if "volume" in price_data.columns:
        ax2 = ax1.twinx()
        ax2.bar(x, price_data["volume"], color="gray", alpha=0.3, label="Volume")
        ax2.set_ylabel("Volume")

    fig.tight_layout()
    fig.savefig(filepath, dpi=100)
    plt.close(fig)

    logger.info(f"Chart saved: {filepath}")
    return filepath


def cleanup_old_charts(output_dir: str = None, max_age_hours: int = 24):
    if output_dir is None:
        output_dir = config.CHARTS_DIR

    if not os.path.exists(output_dir):
        return

    now = time.time()
    max_age_secs = max_age_hours * 3600
    removed = 0

    for f in os.listdir(output_dir):
        if not f.endswith(".png"):
            continue
        path = os.path.join(output_dir, f)
        if now - os.path.getmtime(path) > max_age_secs:
            os.remove(path)
            removed += 1

    if removed:
        logger.info(f"Cleaned up {removed} old chart(s)")
