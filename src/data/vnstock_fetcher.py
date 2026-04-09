import time as _time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import pandas as pd

import config
from src.data.price_fetcher import PriceFetcher
from src.utils.logger import setup_logger, timed

logger = setup_logger(__name__)


class VnstockFetcher(PriceFetcher):

    @timed
    def fetch_batch(self, symbols: List[str], start: str, end: str) -> pd.DataFrame:
        all_frames = []
        batches = [
            symbols[i:i + config.FETCH_BATCH_SIZE]
            for i in range(0, len(symbols), config.FETCH_BATCH_SIZE)
        ]

        for batch_idx, batch in enumerate(batches):
            logger.info(f"Fetching batch {batch_idx + 1}/{len(batches)} ({len(batch)} symbols)")
            frames = self._fetch_parallel(batch, start, end)
            all_frames.extend(frames)

        if not all_frames:
            return pd.DataFrame()

        return pd.concat(all_frames, ignore_index=True)

    def _fetch_parallel(self, symbols: List[str], start: str, end: str) -> list:
        frames = []
        with ThreadPoolExecutor(max_workers=config.FETCH_WORKERS) as executor:
            futures = {
                executor.submit(self._fetch_single, sym, start, end): sym
                for sym in symbols
            }
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        frames.append(df)
                except Exception as e:
                    logger.warning(f"Failed to fetch {sym}: {e}")
        return frames

    def _fetch_single(self, symbol: str, start: str, end: str, retries: int = 3) -> pd.DataFrame:
        from vnstock import Quote

        for attempt in range(retries):
            try:
                quote = Quote(symbol=symbol)
                df = quote.history(start=start, end=end, interval="1D")

                if df is None or df.empty:
                    return pd.DataFrame()

                df["symbol"] = symbol
                return df
            except Exception as e:
                if attempt < retries - 1:
                    delay = 2 ** attempt
                    logger.debug(f"Retry {attempt + 1} for {symbol} in {delay}s: {e}")
                    _time.sleep(delay)
                else:
                    raise
        return pd.DataFrame()
