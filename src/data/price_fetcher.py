from abc import ABC, abstractmethod
from typing import List

import pandas as pd


class PriceFetcher(ABC):
    @abstractmethod
    def fetch_batch(self, symbols: List[str], start: str, end: str) -> pd.DataFrame:
        """Return DataFrame with columns: symbol, time, open, high, low, close, volume"""
        pass
