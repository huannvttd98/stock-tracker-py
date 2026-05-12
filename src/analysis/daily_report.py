import html

import pandas as pd

from src.analysis.profit_calculator import _format_volume
from src.analysis.ceiling_floor import detect_ceiling_floor
from src.analysis.stock_suggestion import suggest_stocks, format_suggestions
from src.data.volume_history import detect_volume_spikes
from src.analysis.technical import analyze_symbol
from src.data.price_history import get_all_close_prices, get_tracking_stats
from src.data.sector_map import SECTORS
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _fmt_signed(val: float) -> str:
    """Format a number with sign and K/M suffix."""
    sign = "+" if val > 0 else ""
    abs_val = abs(val)
    if abs_val >= 1_000_000:
        return f"{sign}{val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{sign}{val / 1_000:.0f}K"
    return f"{sign}{val:,.0f}"


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

    # Market breadth bar
    breadth_lines = _build_market_breadth(df, up, down, flat, total)
    if breadth_lines:
        lines.extend(breadth_lines)

    # Sector ranking
    sector_lines = _build_sector_ranking(df)
    if sector_lines:
        lines.extend(sector_lines)

    # Foreign flow summary
    foreign_lines = _build_foreign_flow(df)
    if foreign_lines:
        lines.extend(foreign_lines)

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


def _build_market_breadth(df: pd.DataFrame, up: int, down: int, flat: int, total: int) -> list:
    """Build visual market breadth bar."""
    if total <= 0:
        return []
    bar_len = 20
    up_bars = round(up / total * bar_len)
    down_bars = round(down / total * bar_len)
    flat_bars = bar_len - up_bars - down_bars
    bar = "🟩" * up_bars + "⬜" * flat_bars + "🟥" * down_bars
    up_pct = up / total * 100
    down_pct = down / total * 100
    return [
        f"\n<b>📊 DO RONG THI TRUONG</b>",
        bar,
        f"Tang: {up_pct:.0f}% ({up}) | Giam: {down_pct:.0f}% ({down}) | Dung: {flat}",
    ]


def _build_sector_ranking(df: pd.DataFrame) -> list:
    """Build sector performance ranking."""
    sector_stats = []
    for sname, syms in SECTORS.items():
        sector_df = df[df["symbol"].isin(syms)]
        if sector_df.empty:
            continue
        avg_pct = sector_df["profit_pct"].mean()
        total_vol = sector_df["volume"].sum()
        up_count = len(sector_df[sector_df["profit_pct"] > 0])
        total_count = len(sector_df)
        sector_stats.append({
            "name": sname, "avg_pct": avg_pct,
            "total_vol": total_vol, "up": up_count, "total": total_count,
        })

    if not sector_stats:
        return []

    sector_stats.sort(key=lambda x: x["avg_pct"], reverse=True)

    lines = ["\n<b>🏢 XEP HANG NGANH</b>"]

    # Top 3 tang
    for i, s in enumerate(sector_stats[:3]):
        medal = ["🥇", "🥈", "🥉"][i]
        sign = "+" if s["avg_pct"] >= 0 else ""
        lines.append(
            f"{medal} <b>{s['name']}</b> {sign}{s['avg_pct']:.2f}%"
            f" ({s['up']}/{s['total']}↑)"
            f" KL: {_format_volume(s['total_vol'])}"
        )

    # Bottom 3 giam (reversed so worst is first)
    bottom = [s for s in sector_stats if s["avg_pct"] < 0]
    if bottom:
        bottom.sort(key=lambda x: x["avg_pct"])
        lines.append("")
        for s in bottom[:3]:
            lines.append(
                f"📉 <b>{s['name']}</b> {s['avg_pct']:.2f}%"
                f" ({s['up']}/{s['total']}↑)"
            )

    return lines


def _build_foreign_flow(df: pd.DataFrame) -> list:
    """Build foreign flow net summary."""
    has_foreign = "foreign_buy" in df.columns and "foreign_sell" in df.columns
    if not has_foreign:
        return []

    fdf = df.copy()
    fdf["foreign_buy"] = pd.to_numeric(fdf["foreign_buy"], errors="coerce").fillna(0)
    fdf["foreign_sell"] = pd.to_numeric(fdf["foreign_sell"], errors="coerce").fillna(0)
    fdf["foreign_net"] = fdf["foreign_buy"] - fdf["foreign_sell"]

    total_buy = fdf["foreign_buy"].sum()
    total_sell = fdf["foreign_sell"].sum()
    total_net = total_buy - total_sell

    if total_buy == 0 and total_sell == 0:
        return []

    net_emoji = "🟢" if total_net > 0 else "🔴"

    lines = [
        f"\n<b>🌐 DONG TIEN NGOAI</b>",
        f"  Mua: <code>{_format_volume(total_buy)}</code>"
        f" | Ban: <code>{_format_volume(total_sell)}</code>"
        f" | Rong: {net_emoji} <b>{_fmt_signed(total_net)}</b>",
    ]

    # Top 5 foreign net buy
    top_buy = fdf[fdf["foreign_net"] > 0].nlargest(5, "foreign_net")
    if not top_buy.empty:
        lines.append("  <b>Top mua rong:</b>")
        for _, row in top_buy.iterrows():
            sym = row.get("symbol", "")
            if not sym or str(sym) == "nan":
                continue
            lines.append(f"    <b>{sym}</b> {_fmt_signed(row['foreign_net'])}")

    # Top 5 foreign net sell
    top_sell = fdf[fdf["foreign_net"] < 0].nsmallest(5, "foreign_net")
    if not top_sell.empty:
        lines.append("  <b>Top ban rong:</b>")
        for _, row in top_sell.iterrows():
            sym = row.get("symbol", "")
            if not sym or str(sym) == "nan":
                continue
            lines.append(f"    <b>{sym}</b> {_fmt_signed(row['foreign_net'])}")

    # Sector foreign flow
    sector_foreign = []
    for sname, syms in SECTORS.items():
        sdf = fdf[fdf["symbol"].isin(syms)]
        if sdf.empty:
            continue
        snet = sdf["foreign_net"].sum()
        if snet != 0:
            sector_foreign.append((sname, snet))

    if sector_foreign:
        sector_foreign.sort(key=lambda x: x[1], reverse=True)
        lines.append("  <b>Nganh:</b>")
        # Show top 3 buy + top 3 sell
        top_s = sector_foreign[:3]
        bot_s = [s for s in sector_foreign if s[1] < 0][:3]
        for sname, snet in top_s:
            if snet > 0:
                lines.append(f"    🟢 {sname}: {_fmt_signed(snet)}")
        for sname, snet in bot_s:
            lines.append(f"    🔴 {sname}: {_fmt_signed(snet)}")

    return lines


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
            signals = html.escape(" | ".join(r["signals"]))
            lines.append(f"  <b>{symbol}</b> ({signals})")

    if sell_signals:
        sell_signals.sort(key=lambda x: x[1]["score"])
        lines.append(f"\n<b>📉 TIN HIEU BAN ({len(sell_signals)} ma)</b>")
        for symbol, r in sell_signals[:10]:
            signals = html.escape(" | ".join(r["signals"]))
            lines.append(f"  <b>{symbol}</b> ({signals})")

    return lines


def _split_messages(lines: list) -> list:
    # Flatten multi-line entries so a single embedded block can't overflow 4096
    flat = []
    for line in lines:
        flat.extend(str(line).split("\n"))

    messages = []
    current = ""
    for line in flat:
        # Hard-split pathologically long lines (shouldn't happen, but defensive)
        while len(line) > 4096:
            if current:
                messages.append(current)
                current = ""
            messages.append(line[:4096])
            line = line[4096:]
        if len(current) + len(line) + 1 > 4096:
            messages.append(current)
            current = ""
        current += line + "\n"
    if current:
        messages.append(current)

    return messages
