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


def filter_profitable(df: pd.DataFrame, threshold: float = 1.0) -> pd.DataFrame:
    if df.empty or "profit_pct" not in df.columns:
        return pd.DataFrame()

    filtered = df[df["profit_pct"] > threshold].copy()
    filtered = filtered.sort_values("profit_pct", ascending=False)
    logger.info(f"Filtered {len(filtered)} symbols with profit > {threshold}%")
    return filtered


def generate_summary(filtered_df: pd.DataFrame) -> str:
    if filtered_df.empty:
        return "Khong tim thay ma nao tang hon nguong."

    count = len(filtered_df)
    lines = [f"Tim thay {count} ma tang hon nguong:\n"]

    for _, row in filtered_df.iterrows():
        symbol = row.get("symbol", "???")
        pct = row.get("profit_pct", 0)
        open_price = row.get("open", 0)
        close_price = row.get("close", 0)
        lines.append(
            f"  {symbol}: +{pct:.2f}% | Mo: {open_price:,.0f} | Dong: {close_price:,.0f}"
        )

    return "\n".join(lines)
