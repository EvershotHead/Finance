"""Manual update orchestrator — runs all update steps in sequence."""

from typing import Optional, Callable

from src.jobs import update_universe, update_daily_data, compute_features
from src.data.data_manager import get_manager
from src.data.batch_fetcher import StopFlag, get_stop_flag
from src.utils.logger import logger


def run_full_update(
    limit: Optional[int] = None,
    history_years: int = 3,
    data_source: str = "akshare",
    stop_flag: Optional[StopFlag] = None,
    progress_callback: Optional[Callable[[str, float, str], None]] = None,
) -> dict:
    """Run full data update: universe → daily data → features.

    Args:
        limit: Only update first N stocks (for debugging)
        history_years: Years of history
        data_source: "akshare", "tushare", or "auto"
        stop_flag: StopFlag to interrupt fetching
        progress_callback: callback(step_name, progress_pct, status_msg)

    Returns:
        dict with results from each step
    """
    results = {}

    if stop_flag is None:
        stop_flag = get_stop_flag()
    stop_flag.reset()  # Clear any previous stop request

    # Configure data source
    manager = get_manager(data_source=data_source)
    logger.info(f"Data source: {data_source}, Tushare available: {manager.has_tushare}")

    def _progress(step: str, pct: float, msg: str):
        if progress_callback:
            progress_callback(step, pct, msg)

    # Step 1: Update universe
    _progress("universe", 0.0, "正在更新股票池...")
    if stop_flag.is_stopped():
        results["stopped"] = True
        return results
    try:
        ok = update_universe.run(data_source=data_source)
        results["universe"] = "success" if ok else "failed"
    except Exception as e:
        logger.error(f"Universe update failed: {e}")
        results["universe"] = f"error: {e}"

    # Step 2: Update daily data
    _progress("daily_data", 0.2, "正在更新行情数据...")
    if stop_flag.is_stopped():
        results["stopped"] = True
        return results
    try:
        daily_result = update_daily_data.run(
            limit=limit, history_years=history_years, data_source=data_source,
            stop_flag=stop_flag, progress_callback=None,
        )
        results["daily_data"] = daily_result
        if daily_result.get("stopped"):
            results["stopped"] = True
            # Still compute features for whatever data we have
    except Exception as e:
        logger.error(f"Daily data update failed: {e}")
        results["daily_data"] = f"error: {e}"

    # Step 3: Compute features (always run, even if stopped — use whatever data exists)
    _progress("features", 0.7, "正在计算选股因子...")
    try:
        features_df = compute_features.run(limit=limit, data_source=data_source)
        results["features"] = f"success: {len(features_df)} stocks" if features_df is not None else "failed"
    except Exception as e:
        logger.error(f"Feature computation failed: {e}")
        results["features"] = f"error: {e}"

    _progress("done", 1.0, "更新完成!" if not results.get("stopped") else "更新已停止，已处理数据已保存")
    logger.info(f"=== Full update complete: {results} ===")
    return results


def run_incremental_update(
    progress_callback: Optional[Callable[[str, float, str], None]] = None,
) -> dict:
    """Run incremental update: refresh basic indicators and recompute features."""
    results = {}

    def _progress(step: str, pct: float, msg: str):
        if progress_callback:
            progress_callback(step, pct, msg)

    _progress("basic", 0.0, "正在更新基础指标...")
    try:
        basic_result = update_daily_data.run(limit=None)
        results["daily_data"] = basic_result
    except Exception as e:
        results["daily_data"] = f"error: {e}"

    _progress("features", 0.5, "正在重新计算因子...")
    try:
        features_df = compute_features.run()
        results["features"] = f"success: {len(features_df)} stocks" if features_df is not None else "failed"
    except Exception as e:
        results["features"] = f"error: {e}"

    _progress("done", 1.0, "增量更新完成!")
    return results


__all__ = ["run_full_update", "run_incremental_update"]
