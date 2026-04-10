import pandas as pd

from src.data.volume_history import get_avg_volumes
from src.analysis.profit_calculator import _format_volume
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Diem cho tung tin hieu
SCORE_VOLUME_SPIKE = 3       # KL dot bien (>= 2x TB)
SCORE_PRICE_UP = 2           # Gia tang > 1%
SCORE_NEAR_CEILING = 2       # Gia gan tran (>= 95% khoang tran)
SCORE_HIGH_VOLUME = 1        # Top 5% KL thi truong
SCORE_PRICE_UP_WITH_VOL = 3  # Tang gia + KL dot bien (combo)


def suggest_stocks(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Score and rank stocks by multiple signals. Higher score = stronger signal."""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    required = {"symbol", "open", "close", "high", "low", "ceiling", "floor", "volume", "profit_pct"}
    if not required.issubset(set(df.columns)):
        logger.warning(f"Missing columns for suggestion. Have: {list(df.columns)}")
        return pd.DataFrame()

    # Skip stocks with no trading
    df = df[df["volume"] > 0].copy()
    if df.empty:
        return pd.DataFrame()

    avg_volumes = get_avg_volumes()

    # Volume percentile threshold (top 5%)
    vol_95 = df["volume"].quantile(0.95)

    scores = []
    for _, row in df.iterrows():
        symbol = row["symbol"]
        score = 0
        signals = []

        avg_vol = avg_volumes.get(symbol, 0)
        vol_ratio = (row["volume"] / avg_vol) if avg_vol > 0 else 0

        # 1. KL dot bien
        if vol_ratio >= 2.0:
            score += SCORE_VOLUME_SPIKE
            signals.append(f"KL {vol_ratio:.1f}x TB")

        # 2. Gia tang > 1%
        if row["profit_pct"] > 1.0:
            score += SCORE_PRICE_UP
            signals.append(f"+{row['profit_pct']:.1f}%")

        # 3. Gan tran (close >= 95% khoang tu floor den ceiling)
        price_range = row["ceiling"] - row["floor"]
        if price_range > 0:
            position = (row["close"] - row["floor"]) / price_range
            if position >= 0.95:
                score += SCORE_NEAR_CEILING
                signals.append("Gan tran")

        # 4. Top 5% KL thi truong
        if row["volume"] >= vol_95:
            score += SCORE_HIGH_VOLUME
            signals.append("KL top 5%")

        # 5. Combo: tang gia + KL dot bien (tin hieu manh nhat)
        if row["profit_pct"] > 1.0 and vol_ratio >= 2.0:
            score += SCORE_PRICE_UP_WITH_VOL
            signals.append("COMBO")

        if score >= 3:
            scores.append({
                "symbol": symbol,
                "close": row["close"],
                "profit_pct": row["profit_pct"],
                "volume": row["volume"],
                "avg_volume": avg_vol,
                "volume_ratio": round(vol_ratio, 1),
                "score": score,
                "signals": " | ".join(signals),
            })

    if not scores:
        return pd.DataFrame()

    result = pd.DataFrame(scores)
    result = result.sort_values("score", ascending=False).head(top_n)
    logger.info(f"Suggested {len(result)} stocks (score >= 3)")
    return result


def format_suggestions(suggestions: pd.DataFrame) -> str:
    """Format suggestion list for Telegram message."""
    if suggestions.empty:
        return ""

    lines = [f"\n<b>💡 GOI Y THEO DOI ({len(suggestions)} ma)</b>\n"]

    for idx, (_, row) in enumerate(suggestions.iterrows(), 1):
        symbol = row["symbol"]
        score = int(row["score"])
        pct = row["profit_pct"]
        vol = _format_volume(row["volume"])
        signals = row["signals"]
        stars = "⭐" * min(score // 2, 5)

        sign = "+" if pct >= 0 else ""
        url = f"https://finance.vietstock.vn/{symbol}/tai-chinh.htm"

        lines.append(
            f"  <b>{idx}. {symbol}</b> {stars} ({score} diem)\n"
            f"     <code>{row['close']:,.0f}</code> ({sign}{pct:.2f}%) | KL: {vol}\n"
            f"     {signals}\n"
            f"     🔗 <a href=\"{url}\">{symbol} chi tiet</a>"
        )

    return "\n".join(lines)
