import requests
import pandas as pd

from src.utils.logger import setup_logger, timed

logger = setup_logger(__name__)

CAFEF_URL = "https://banggia.cafef.vn/stockhandler.ashx"

# CafeF field mapping
# a=symbol, b=ref(open), c=ceiling, d=floor
# e=close(last matched), v=high, w=low
# k=change, totalvolume=total volume
# x=foreign buy volume, y=foreign sell volume
FIELD_MAP = {
    "a": "symbol",
    "b": "open",
    "c": "ceiling",
    "d": "floor",
    "e": "close",
    "v": "high",
    "w": "low",
    "k": "change",
    "totalvolume": "volume",
    "x": "foreign_buy",
    "y": "foreign_sell",
}


class CafefFetcher:

    @timed
    def fetch_all(self) -> pd.DataFrame:
        """Fetch all HOSE + HNX stocks in 2 requests."""
        all_data = []

        for center, exchange in [(1, "HOSE"), (2, "HNX")]:
            try:
                resp = requests.get(
                    CAFEF_URL,
                    params={"center": center},
                    timeout=15,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info(f"Fetched {len(data)} symbols from {exchange}")
                all_data.extend(data)
            except Exception as e:
                logger.error(f"Failed to fetch {exchange}: {e}")

        if not all_data:
            return pd.DataFrame()

        rows = []
        for item in all_data:
            row = {std: item.get(raw, 0) for raw, std in FIELD_MAP.items()}
            if not row["close"] or not isinstance(row["symbol"], str) or not row["symbol"].strip():
                continue
            # CafeF prices are in 1000 VND
            for col in ["open", "close", "high", "low", "ceiling", "floor", "change"]:
                row[col] = row[col] * 1000
            rows.append(row)

        df = pd.DataFrame(rows)

        # Filter by minimum volume
        import config
        before = len(df)
        df = df[df["volume"] >= config.MIN_VOLUME]
        logger.info(f"Total: {len(df)} symbols (filtered {before - len(df)} with KL < {config.MIN_VOLUME:,})")
        return df
