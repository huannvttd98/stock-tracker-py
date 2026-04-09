import time as _time
from typing import List

import pandas as pd
import yfinance as yf

from src.data.price_fetcher import PriceFetcher
from src.utils.logger import setup_logger, timed

logger = setup_logger(__name__)

CHUNK_SIZE = 80
CHUNK_DELAY = 2


class YfinanceFetcher(PriceFetcher):

    @timed
    def fetch_batch(self, symbols: List[str], start: str, end: str) -> pd.DataFrame:
        vn_symbols = [f"{s}.VN" for s in symbols]
        chunks = [
            vn_symbols[i:i + CHUNK_SIZE]
            for i in range(0, len(vn_symbols), CHUNK_SIZE)
        ]

        all_frames = []
        for idx, chunk in enumerate(chunks):
            logger.info(f"yfinance chunk {idx + 1}/{len(chunks)} ({len(chunk)} symbols)")
            try:
                df = yf.download(
                    tickers=chunk,
                    start=start,
                    end=end,
                    group_by="ticker",
                    threads=True,
                    progress=False,
                )
                frames = self._parse_download(df, chunk)
                all_frames.extend(frames)
            except Exception as e:
                logger.error(f"yfinance chunk {idx + 1} failed: {e}")

            if idx < len(chunks) - 1:
                _time.sleep(CHUNK_DELAY)

        if not all_frames:
            return pd.DataFrame()

        return pd.concat(all_frames, ignore_index=True)

    def _parse_download(self, df: pd.DataFrame, symbols: List[str]) -> list:
        frames = []
        if df.empty:
            return frames

        for vn_sym in symbols:
            sym = vn_sym.replace(".VN", "")
            try:
                if len(symbols) == 1:
                    sub = df.copy()
                else:
                    sub = df[vn_sym].copy()

                sub = sub.dropna(subset=["Close"])
                if sub.empty:
                    continue

                sub = sub.reset_index()
                sub["symbol"] = sym
                sub.columns = [c.lower() for c in sub.columns]
                frames.append(sub)
            except (KeyError, Exception) as e:
                logger.debug(f"Skip {sym}: {e}")
        return frames
