import pandas as pd

from src.analysis.profit_calculator import _format_volume
from src.analysis.ceiling_floor import detect_ceiling_floor
from src.data.volume_history import detect_volume_spikes
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def generate_daily_report(df: pd.DataFrame) -> list:
    """Generate end-of-day market summary. Returns list of messages."""
    if df.empty:
        return ["Khong co du lieu de tao bao cao."]

    from datetime import datetime
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    total = len(df)
    up = len(df[df["profit_pct"] > 0])
    down = len(df[df["profit_pct"] < 0])
    flat = total - up - down

    # Top gainers / losers
    top_up = df.sort_values("profit_pct", ascending=False).head(5)
    top_down = df.sort_values("profit_pct", ascending=True).head(5)
    top_vol = df.sort_values("volume", ascending=False).head(5)

    # Ceiling / Floor
    ceiling, floor = detect_ceiling_floor(df.copy())

    # Volume spikes
    spikes = detect_volume_spikes(df.copy())

    lines = [
        f"<b>📊 BAO CAO CUOI NGAY</b>",
        f"<i>🕐 {now}</i>\n",
        f"Tong: <b>{total}</b> ma | "
        f"🟢 Tang: <b>{up}</b> | 🔴 Giam: <b>{down}</b> | ⚪ Dung: <b>{flat}</b>\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Top tang
    lines.append("\n<b>🚀 TOP TANG</b>")
    for _, row in top_up.iterrows():
        lines.append(
            f"  <b>{row['symbol']}</b> +{row['profit_pct']:.2f}% "
            f"| <code>{row['close']:,.0f}</code> | KL: {_format_volume(row['volume'])}"
        )

    # Top giam
    lines.append("\n<b>📉 TOP GIAM</b>")
    for _, row in top_down.iterrows():
        lines.append(
            f"  <b>{row['symbol']}</b> {row['profit_pct']:.2f}% "
            f"| <code>{row['close']:,.0f}</code> | KL: {_format_volume(row['volume'])}"
        )

    # Top KL
    lines.append("\n<b>📊 TOP KHOI LUONG</b>")
    for _, row in top_vol.iterrows():
        sign = "+" if row["profit_pct"] >= 0 else ""
        lines.append(
            f"  <b>{row['symbol']}</b> {_format_volume(row['volume'])} "
            f"| {sign}{row['profit_pct']:.2f}%"
        )

    # Tran/San
    if not ceiling.empty:
        lines.append(f"\n<b>🔴 CHAM TRAN ({len(ceiling)} ma)</b>")
        for _, row in ceiling.head(10).iterrows():
            lines.append(f"  <b>{row['symbol']}</b> <code>{row['close']:,.0f}</code> | KL: {_format_volume(row['volume'])}")

    if not floor.empty:
        lines.append(f"\n<b>🟢 CHAM SAN ({len(floor)} ma)</b>")
        for _, row in floor.head(10).iterrows():
            lines.append(f"  <b>{row['symbol']}</b> <code>{row['close']:,.0f}</code> | KL: {_format_volume(row['volume'])}")

    # Dot bien KL
    if not spikes.empty:
        lines.append(f"\n<b>⚡ DOT BIEN KHOI LUONG ({len(spikes)} ma)</b>")
        for _, row in spikes.head(10).iterrows():
            lines.append(
                f"  <b>{row['symbol']}</b> KL: {_format_volume(row['volume'])} "
                f"(<b>{row['volume_ratio']:.1f}x</b> TB) "
                f"| {'+' if row['profit_pct'] >= 0 else ''}{row['profit_pct']:.2f}%"
            )

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━")

    # Split into messages under 4096 chars
    messages = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 2 > 4096:
            messages.append(current)
            current = ""
        current += line + "\n"
    if current:
        messages.append(current)

    return messages
