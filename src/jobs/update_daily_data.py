"""Job: Update daily bar and basic indicator data."""

from typing import Optional, Callable

from src.data.universe_manager import load_universe
from src.data.batch_fetcher import BatchFetcher, StopFlag
from src.data.data_quality import clean_daily_bars
from src.storage import parquet_store
from src.utils.logger import logger
from src.utils.date_utils import date_range_years

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"


def run(
    limit: Optional[int] = None,
    history_years: int = 3,
    data_source: str = "akshare",
    stop_flag: Optional[StopFlag] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """Update daily bar and basic indicator data.

    Args:
        limit: Only update first N stocks (for debugging)
        history_years: Years of history to fetch
        data_source: "akshare", "tushare", or "auto"
        stop_flag: StopFlag to interrupt fetching
        progress_callback: callback(current, total, status_msg)

    Returns:
        dict with results summary
    """
    logger.info(f"=== Updating daily data (source: {data_source}) ===")

    # Load universe
    universe = load_universe()
    if universe is None:
        logger.error("Universe not available. Run update_universe first.")
        return {"error": "Universe not available"}

    start_date, end_date = date_range_years(history_years)

    fetcher = BatchFetcher(data_source=data_source, stop_flag=stop_flag)

    # Step 1: Fetch index data
    logger.info("Step 1/3: Fetching index data...")
    if progress_callback:
        progress_callback(1, 3, "获取指数数据...")
    index_result = fetcher.fetch_index_data(start_date, end_date)
    logger.info(f"Index data: {index_result['success']}/{index_result['total']} success")

    # Check stop
    if stop_flag and stop_flag.is_stopped():
        return {"index": index_result, "daily_basic": {"success": 0}, "daily_bars": {"success": 0}, "stopped": True}

    # Step 2: Fetch daily basic indicators (PE/PB/市值 etc.)
    logger.info("Step 2/3: Fetching daily basic indicators...")
    if progress_callback:
        progress_callback(2, 3, "获取每日基础指标(PE/PB/市值)...")
    basic_result = fetcher.fetch_all_daily_basic(limit=limit, progress_callback=progress_callback)
    logger.info(f"Daily basic: {basic_result['success']}/{basic_result['total']} success")

    # Check stop
    if stop_flag and stop_flag.is_stopped():
        return {"index": index_result, "daily_basic": basic_result, "daily_bars": {"success": 0}, "stopped": True}

    # Step 3: Fetch daily bars
    logger.info("Step 3/3: Fetching daily bars...")
    if progress_callback:
        progress_callback(3, 3, "获取日K线数据...")
    bar_result = fetcher.fetch_all_daily_bars(
        universe, start_date, end_date, limit=limit, skip_cached=True, progress_callback=progress_callback,
    )
    logger.info(f"Daily bars: {bar_result['success']}/{bar_result['total']} success")

    result = {
        "index": index_result,
        "daily_basic": basic_result,
        "daily_bars": bar_result,
        "total_failures": len(bar_result.get("failures", [])),
        "stopped": bool(stop_flag and stop_flag.is_stopped()),
    }

    logger.info(f"=== Daily data update complete: {bar_result['success']}/{bar_result['total']} stocks ===")
    return result


if __name__ == "__main__":
    run(limit=10)
