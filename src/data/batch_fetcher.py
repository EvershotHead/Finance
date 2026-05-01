"""Batch data fetching with stop mechanism, resume capability, and time-based cache."""

import time
import json
import threading
from datetime import datetime, date
from typing import Optional, Callable

import pandas as pd

from src.data import akshare_fetcher as akf
from src.data.universe_manager import load_universe
from src.data.data_manager import get_manager
from src.storage import parquet_store
from src.utils.logger import logger
from src.utils.date_utils import date_range_years, today_str

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROGRESS_FILE = PROJECT_ROOT / "data" / "fetch_progress.json"


def _is_cache_fresh(cache_path: Path, max_age_hours: float = 4.0) -> bool:
    """Check if a cached file is still fresh.

    Data fetched today is considered fresh for `max_age_hours`.
    After that window, it should be refreshed.
    """
    if not cache_path.exists():
        return False
    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
    age_hours = (datetime.now() - mtime).total_seconds() / 3600
    return age_hours < max_age_hours


def _save_progress(progress: dict):
    """Save fetch progress to disk for resume capability."""
    try:
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.debug(f"Failed to save progress: {e}")


def _load_progress() -> dict:
    """Load fetch progress from disk."""
    try:
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


class StopFlag:
    """Thread-safe stop flag for interrupting batch operations."""

    def __init__(self):
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def is_stopped(self) -> bool:
        return self._stop.is_set()

    def reset(self):
        self._stop.clear()


# Global stop flag
_global_stop = StopFlag()


def get_stop_flag() -> StopFlag:
    return _global_stop


class BatchFetcher:
    """Batch data fetching with progress, stop, resume, and caching."""

    def __init__(
        self,
        rate_limit: float = 0.3,
        batch_size: int = 50,
        batch_sleep: float = 2.0,
        max_retries: int = 2,
        data_source: str = "akshare",
        stop_flag: Optional[StopFlag] = None,
    ):
        self.rate_limit = rate_limit
        self.batch_size = batch_size
        self.batch_sleep = batch_sleep
        self.max_retries = max_retries
        self.data_source = data_source
        self.manager = get_manager(data_source=data_source)
        self._failures: list[dict] = []
        self._stop = stop_flag or _global_stop
        self._skipped = 0

    @property
    def failures(self) -> list[dict]:
        return self._failures.copy()

    def fetch_all_daily_bars(
        self,
        universe_df: pd.DataFrame,
        start_date: str = "",
        end_date: str = "",
        limit: Optional[int] = None,
        skip_cached: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> dict:
        """Fetch daily bars for all stocks in universe.

        Features:
        - Stop mechanism: checks stop flag between each stock
        - Resume: skips stocks with fresh cached data
        - Cache: daily bar files cached for ~4 hours

        Args:
            universe_df: DataFrame with stock_code, symbol columns
            start_date: YYYYMMDD
            end_date: YYYYMMDD
            limit: Only fetch first N stocks
            skip_cached: Skip stocks with fresh cached data
            progress_callback: callback(current, total, status_msg)
        """
        if not start_date:
            start_date, end_date = date_range_years(3)

        symbols = universe_df["symbol"].tolist()
        if limit:
            symbols = symbols[:limit]

        total = len(symbols)
        success = 0
        self._failures = []
        self._skipped = 0
        stop_reason = ""

        # Load previous progress for resume
        prev_progress = _load_progress()
        prev_date = prev_progress.get("date", "")
        today = today_str("%Y%m%d")
        is_continuation = (prev_date == today and prev_progress.get("type") == "daily_bars")

        if is_continuation:
            logger.info(f"Resuming from previous session: {prev_progress.get('success', 0)} already done")

        logger.info(f"Batch fetching daily bars for {total} stocks ({start_date} to {end_date})")

        for i, sym in enumerate(symbols):
            # Check stop flag
            if self._stop.is_stopped():
                stop_reason = "user_stopped"
                logger.info(f"Stop flag detected at {i}/{total}, stopping...")
                break

            stock_code = akf.normalize_code(sym)[0]
            cache_path = RAW_DIR / "daily_bar" / f"{stock_code.replace('.', '_')}.parquet"

            # Resume: skip if already cached and fresh
            if skip_cached and _is_cache_fresh(cache_path, max_age_hours=4.0):
                self._skipped += 1
                success += 1
                if progress_callback and i % 100 == 0:
                    progress_callback(i + 1, total, f"[跳过] {stock_code} (已有缓存)")
                continue

            if progress_callback and i % 10 == 0:
                progress_callback(i + 1, total, f"[获取] {stock_code} ({i+1}/{total})")

            try:
                df = self.manager.get_daily_bars(sym, start_date, end_date, use_cache=False)
                if df is not None and len(df) > 0:
                    success += 1
                else:
                    self._failures.append({"symbol": sym, "error": "empty result"})
            except Exception as e:
                self._failures.append({"symbol": sym, "error": str(e)})
                logger.warning(f"Failed to fetch daily bars for {sym}: {e}")

            # Rate limiting
            if (i + 1) % self.batch_size == 0:
                # Save progress checkpoint
                _save_progress({
                    "date": today,
                    "type": "daily_bars",
                    "last_index": i + 1,
                    "success": success,
                    "total": total,
                })
                logger.info(f"Progress checkpoint: {i + 1}/{total}, sleeping {self.batch_sleep}s...")
                time.sleep(self.batch_sleep)
            else:
                time.sleep(self.rate_limit)

        result = {
            "total": total,
            "success": success,
            "fail": total - success - self._skipped,
            "skipped": self._skipped,
            "stop_reason": stop_reason,
            "failures": self._failures,
        }

        # Clear progress on completion
        if not stop_reason:
            _save_progress({"date": today, "type": "daily_bars", "status": "completed"})

        logger.info(f"Batch fetch complete: {success}/{total} success, {self._skipped} skipped, {total - success - self._skipped} failed")
        return result

    def fetch_all_daily_basic(
        self,
        limit: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> dict:
        """Fetch daily basic indicators for all stocks.

        Uses Tushare daily_basic(trade_date=...) for all stocks at once if available,
        otherwise falls back to AKShare spot data. No per-stock iteration needed.
        """
        logger.info(f"Fetching daily basic indicators (source: {self.data_source})...")

        if progress_callback:
            progress_callback(1, 2, f"获取全市场基础指标 (数据源: {self.data_source})...")

        df = self.manager.get_daily_basic_all()

        if progress_callback:
            progress_callback(2, 2, "保存数据...")

        if df is not None and len(df) > 0:
            logger.info(f"Daily basic: got {len(df)} stocks")
            return {"total": len(df), "success": len(df), "fail": 0, "failures": []}

        return {"total": 0, "success": 0, "fail": 1, "failures": [{"error": "Failed to fetch daily basic"}]}

    def fetch_index_data(
        self,
        start_date: str = "",
        end_date: str = "",
    ) -> dict:
        """Fetch index daily data for all configured indices."""
        if not start_date:
            start_date, end_date = date_range_years(3)

        indices = ["000300", "000905", "000852", "000001", "399001", "399006"]
        success = 0

        for idx_code in indices:
            try:
                df = self.manager.get_index_daily(idx_code, start_date, end_date)
                if df is not None:
                    success += 1
            except Exception as e:
                logger.warning(f"Failed to fetch index {idx_code}: {e}")

        return {"total": len(indices), "success": success, "fail": len(indices) - success}


__all__ = ["BatchFetcher", "StopFlag", "get_stop_flag"]
