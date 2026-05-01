"""Unified data manager with auto-fallback between data sources."""

from pathlib import Path
from typing import Optional

import pandas as pd

from src.data import akshare_fetcher as akf
from src.data.universe_manager import load_universe, UNIVERSE_PATH
from src.storage import parquet_store
from src.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"


class DataManager:
    """Unified data manager with caching and fallback.

    Supports:
    - "akshare": Use AKShare only
    - "tushare": Use Tushare only (requires token)
    - "auto": Try Tushare first, fallback to AKShare
    """

    def __init__(self, data_source: str = "akshare"):
        self._data_source = data_source
        self._tushare_fetcher = None
        self._try_load_tushare()

    def set_data_source(self, source: str):
        """Change data source preference."""
        self._data_source = source
        if source in ("tushare", "auto"):
            self._try_load_tushare()

    def _try_load_tushare(self):
        """Try to load Tushare fetcher if token is available."""
        if self._tushare_fetcher is not None:
            return
        try:
            import os
            token = os.environ.get("TUSHARE_TOKEN", "")
            if token:
                from src.data.tushare_fetcher import TushareFetcher
                self._tushare_fetcher = TushareFetcher(token)
                logger.info("Tushare fetcher loaded")
        except Exception as e:
            logger.debug(f"Tushare not available: {e}")

    @property
    def has_tushare(self) -> bool:
        return self._tushare_fetcher is not None

    def _should_use_tushare(self) -> bool:
        """Check if we should try Tushare first."""
        if self._data_source == "tushare":
            return True
        if self._data_source == "auto" and self.has_tushare:
            return True
        return False

    def get_stock_list(self, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """Get stock list with caching."""
        if not force_refresh:
            cached = load_universe()
            if cached is not None:
                return cached

        # Try Tushare first if configured
        if self._should_use_tushare() and self.has_tushare:
            logger.info("Fetching stock list from Tushare...")
            df = self._tushare_fetcher.fetch_stock_list()
            if df is not None and len(df) > 0:
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                parquet_store.save_df(df, UNIVERSE_PATH)
                return df
            if self._data_source == "tushare":
                logger.error("Tushare stock list failed and source is tushare-only")
                return None

        # AKShare
        logger.info("Fetching stock list from AKShare...")
        df = akf.fetch_stock_list_with_spot()
        if df is None:
            df = akf.fetch_stock_list()

        if df is not None:
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            parquet_store.save_df(df, UNIVERSE_PATH)

        return df

    def get_daily_bars(
        self,
        symbol: str,
        start_date: str = "20230101",
        end_date: str = "",
        use_cache: bool = True,
    ) -> Optional[pd.DataFrame]:
        """Get daily bars for a single stock with caching."""
        stock_code, _ = akf.normalize_code(symbol)
        cache_dir = RAW_DIR / "daily_bar"
        cache_path = cache_dir / f"{stock_code.replace('.', '_')}.parquet"

        # Check cache
        if use_cache and parquet_store.exists(cache_path):
            cached = parquet_store.load_df(cache_path)
            if cached is not None and len(cached) > 0:
                cached_max = cached["trade_date"].max()
                if pd.Timestamp(cached_max) >= pd.Timestamp.now() - pd.Timedelta(days=3):
                    return cached

        # Try Tushare first if configured
        if self._should_use_tushare() and self.has_tushare:
            ts_code = akf.normalize_code(symbol)[0]
            df = self._tushare_fetcher.fetch_daily_bars(ts_code, start_date, end_date)
            if df is not None and len(df) > 0:
                cache_dir.mkdir(parents=True, exist_ok=True)
                parquet_store.save_df(df, cache_path)
                return df

        # AKShare
        df = akf.fetch_daily_bars(symbol, start_date, end_date)

        if df is not None and len(df) > 0:
            cache_dir.mkdir(parents=True, exist_ok=True)
            parquet_store.save_df(df, cache_path)

        return df

    def get_daily_basic_all(self, trade_date: str = "") -> Optional[pd.DataFrame]:
        """Get daily basic indicators for ALL stocks on a given date.

        Tushare can fetch ~5360 stocks in one call. AKShare uses spot data.
        """
        # Try Tushare first if configured
        if self._should_use_tushare() and self.has_tushare:
            logger.info("Fetching daily_basic from Tushare (all stocks)...")
            df = self._tushare_fetcher.fetch_daily_basic_all(trade_date)
            if df is not None and len(df) > 0:
                # Save cache
                cache_dir = RAW_DIR / "daily_basic"
                cache_dir.mkdir(parents=True, exist_ok=True)
                parquet_store.save_df(df, cache_dir / "daily_basic_latest.parquet")
                return df

        # AKShare fallback
        logger.info("Fetching daily_basic from AKShare (spot data)...")
        from src.data import akshare_fetcher as akf
        df = akf.fetch_daily_basic()
        if df is not None and len(df) > 0:
            cache_dir = RAW_DIR / "daily_basic"
            cache_dir.mkdir(parents=True, exist_ok=True)
            parquet_store.save_df(df, cache_dir / "daily_basic_latest.parquet")
        return df

    def get_index_daily(
        self,
        index_code: str = "000300",
        start_date: str = "20230101",
        end_date: str = "",
    ) -> Optional[pd.DataFrame]:
        """Get index daily data with caching."""
        cache_dir = RAW_DIR / "index"
        cache_path = cache_dir / f"index_{index_code}.parquet"

        if parquet_store.exists(cache_path):
            cached = parquet_store.load_df(cache_path)
            if cached is not None and len(cached) > 0:
                cached_max = cached["trade_date"].max()
                if pd.Timestamp(cached_max) >= pd.Timestamp.now() - pd.Timedelta(days=3):
                    return cached

        df = akf.fetch_index_daily(index_code, start_date, end_date)
        if df is not None and len(df) > 0:
            cache_dir.mkdir(parents=True, exist_ok=True)
            parquet_store.save_df(df, cache_path)

        return df


# Singleton
_manager = None


def get_manager(data_source: str = "akshare") -> DataManager:
    """Get singleton DataManager instance.

    Args:
        data_source: "akshare", "tushare", or "auto"
    """
    global _manager
    if _manager is None:
        _manager = DataManager(data_source=data_source)
    else:
        _manager.set_data_source(data_source)
    return _manager


__all__ = ["DataManager", "get_manager"]
