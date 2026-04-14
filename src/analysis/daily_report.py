import pandas as pd

from src.analysis.profit_calculator import _format_volume
from src.analysis.ceiling_floor import detect_ceiling_floor
from src.analysis.stock_suggestion import suggest_stocks, format_suggestions
from src.data.volume_history import detect_volume_spikes
from src.analysis.technical import analyze_symbol
from src.data.price_history import get_all_close_prices, get_tracking_stats
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

    # Tracking stats
    stats = get_tracking_stats()

    lines = [
        f"<b>📊 BAO CAO CUOI NGAY</b>",
        f"<i>🕐 {now}</i>\n",
        f"Tong: <b>{total}</b> ma | "
        f"🟢 Tang: <b>{up}</b> | 🔴 Giam: <b>{down}</b> | ⚪ Dung: <b>{flat}</b>",
        f"📅 Da theo doi: <b>{stats['total_sessions']}</b> phien"
        f" | Tu: <b>{stats['first_date']}</b>"
        f" | <b>{stats['total_symbols']}</b> ma\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Top tang
    lines.append("\n<b>🚀 TOP TANG</b>")
    for _, row in top_up.iterrows():
        sym = row.get("symbol", "")
        if not sym or str(sym) == "nan":
            continue
        change = row["close"] - row["open"]
        lines.append(
            f"  <b>{sym}</b> +{row['profit_pct']:.2f}% "
            f"| <code>{row['close']:,.0f}</code> (<code>+{change:,.0f}</code>) "
            f"| KL: {_format_volume(row['volume'])}"
        )

    # Top giam
    lines.append("\n<b>📉 TOP GIAM</b>")
    for _, row in top_down.iterrows():
        sym = row.get("symbol", "")
        if not sym or str(sym) == "nan":
            continue
        change = row["close"] - row["open"]
        lines.append(
            f"  <b>{sym}</b> {row['profit_pct']:.2f}% "
            f"| <code>{row['close']:,.0f}</code> (<code>{change:,.0f}</code>) "
            f"| KL: {_format_volume(row['volume'])}"
        )

    # Top KL
    lines.append("\n<b>📊 TOP KHOI LUONG</b>")
    for _, row in top_vol.iterrows():
        sym = row.get("symbol", "")
        if not sym or str(sym) == "nan":
            continue
        sign = "+" if row["profit_pct"] >= 0 else ""
        lines.append(
            f"  <b>{sym}</b> {_format_volume(row['volume'])} "
            f"| {sign}{row['profit_pct']:.2f}%"
        )

    # Tran/San
    if not ceiling.empty:
        lines.append(f"\n<b>🔴 CHAM TRAN ({len(ceiling)} ma)</b>")
        for _, row in ceiling.head(10).iterrows():
            sym = row.get("symbol", "")
            if not sym or str(sym) == "nan":
                continue
            lines.append(f"  <b>{sym}</b> <code>{row['close']:,.0f}</code> | KL: {_format_volume(row['volume'])}")

    if not floor.empty:
        lines.append(f"\n<b>🟢 CHAM SAN ({len(floor)} ma)</b>")
        for _, row in floor.head(10).iterrows():
            sym = row.get("symbol", "")
            if not sym or str(sym) == "nan":
                continue
            lines.append(f"  <b>{sym}</b> <code>{row['close']:,.0f}</code> | KL: {_format_volume(row['volume'])}")

    # Dot bien KL
    if not spikes.empty:
        lines.append(f"\n<b>⚡ DOT BIEN KHOI LUONG ({len(spikes)} ma)</b>")
        for _, row in spikes.head(10).iterrows():
            sym = row.get("symbol", "")
            if not sym or str(sym) == "nan":
                continue
            lines.append(
                f"  <b>{sym}</b> KL: {_format_volume(row['volume'])} "
                f"(<b>{row['volume_ratio']:.1f}x</b> TB) "
                f"| {'+' if row['profit_pct'] >= 0 else ''}{row['profit_pct']:.2f}%"
            )

    # Tin hieu ky thuat
    ta_lines = _build_technical_section(df)
    if ta_lines:
        lines.extend(ta_lines)

    # Goi y theo doi
    suggestions = suggest_stocks(df.copy())
    if not suggestions.empty:
        lines.append(format_suggestions(suggestions))

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━")

    # Split into messages under 4096 chars
    return _split_messages(lines)


def _build_technical_section(df: pd.DataFrame) -> list:
    """Build technical analysis section for daily report."""
    close_data = get_all_close_prices(days=30)
    if not close_data:
        return []

    buy_signals = []
    sell_signals = []

    for symbol in df["symbol"].tolist():
        closes = close_data.get(symbol)
        if not closes or len(closes) < 21:
            continue
        result = analyze_symbol(closes)
        if not result:
            continue
        if result["score"] >= 3:
            buy_signals.append((symbol, result))
        elif result["score"] <= -3:
            sell_signals.append((symbol, result))

    if not buy_signals and not sell_signals:
        return []

    lines = []

    if buy_signals:
        buy_signals.sort(key=lambda x: x[1]["score"], reverse=True)
        lines.append(f"\n<b>📈 TIN HIEU MUA ({len(buy_signals)} ma)</b>")
        for symbol, r in buy_signals[:10]:
            signals = " | ".join(r["signals"])
            lines.append(f"  <b>{symbol}</b> ({signals})")

    if sell_signals:
        sell_signals.sort(key=lambda x: x[1]["score"])
        lines.append(f"\n<b>📉 TIN HIEU BAN ({len(sell_signals)} ma)</b>")
        for symbol, r in sell_signals[:10]:
            signals = " | ".join(r["signals"])
            lines.append(f"  <b>{symbol}</b> ({signals})")

    return lines


def _split_messages(lines: list) -> list:
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
