import pandas as pd

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def calculate_profits(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()

    # Normalize column names to lowercase
    df.columns = [c.lower() for c in df.columns]

    if "open" not in df.columns or "close" not in df.columns:
        logger.error(f"Missing open/close columns. Available: {list(df.columns)}")
        return pd.DataFrame()

    df["profit_pct"] = (df["close"] - df["open"]) / df["open"] * 100
    df["profit_pct"] = df["profit_pct"].round(2)
    return df


def filter_by_volume(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df.columns = [c.lower() for c in df.columns]

    if "volume" not in df.columns:
        logger.error(f"Missing volume column. Available: {list(df.columns)}")
        return pd.DataFrame()

    filtered = df.sort_values("volume", ascending=False).head(top_n).copy()
    logger.info(f"Top {len(filtered)} symbols by volume")
    return filtered


def _format_volume(vol: float) -> str:
    if vol >= 1_000_000:
        return f"{vol / 1_000_000:.1f}M"
    if vol >= 1_000:
        return f"{vol / 1_000:.0f}K"
    return f"{vol:,.0f}"


def generate_summary(filtered_df: pd.DataFrame) -> list:
    """Return list of message strings, each under Telegram's 4096 char limit."""
    if filtered_df.empty:
        return ["Khong tim thay ma nao dat nguong khoi luong."]

    from datetime import datetime

    count = len(filtered_df)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    header = (
        "<b>🔥 CO PHIEU KHOI LUONG LON</b>\n"
        f"<i>🕐 {now} | {count} ma</i>\n"
    )

    items = []
    for idx, (_, row) in enumerate(filtered_df.iterrows(), 1):
        symbol = row.get("symbol", "???")
        pct = row.get("profit_pct", 0)
        open_price = row.get("open", 0)
        close_price = row.get("close", 0)
        high_price = row.get("high", 0)
        low_price = row.get("low", 0)
        volume = row.get("volume", 0)

        change = close_price - open_price
        sign = "+" if change >= 0 else ""
        pct_sign = "+" if pct >= 0 else ""
        vol_str = _format_volume(volume)

        detail_url = f"https://finance.vietstock.vn/{symbol}/tai-chinh.htm"

        item = (
            f"<b>{idx}. {symbol}</b>  📊 {vol_str}\n"
            f"   <code>{open_price:,.0f}</code> → <code>{close_price:,.0f}</code>"
            f" ({sign}{change:,.0f} | {pct_sign}{pct:.2f}%)\n"
            f"   H: <code>{high_price:,.0f}</code> | L: <code>{low_price:,.0f}</code>\n"
            f"   🔗 <a href=\"{detail_url}\">{symbol} chi tiet</a>"
        )
        items.append(item)

    # Split into messages under 4096 chars
    messages = []
    current = header + "━━━━━━━━━━━━━━━━━━━━━━━━\n"

    for item in items:
        if len(current) + len(item) + 30 > 4096:
            current += "━━━━━━━━━━━━━━━━━━━━━━━━"
            messages.append(current)
            current = ""
        current += item + "\n\n"

    current += "━━━━━━━━━━━━━━━━━━━━━━━━"
    messages.append(current)

    return messages
