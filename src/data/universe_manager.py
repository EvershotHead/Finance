"""Stock pool / universe management."""

from pathlib import Path
from typing import Optional

import pandas as pd

from src.data import akshare_fetcher as akf
from src.storage import parquet_store
from src.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UNIVERSE_DIR = PROJECT_ROOT / "data" / "raw" / "stock_list"
UNIVERSE_PATH = UNIVERSE_DIR / "universe.parquet"


def get_universe(pool_name: str = "all_a", custom_csv: Optional[Path] = None) -> Optional[pd.DataFrame]:
    """Get stock universe by pool name.

    Args:
        pool_name: One of all_a, sh_main, sz_main, gem, star, bse, hs300, zz500, zz1000, custom
        custom_csv: Path to custom CSV file (for pool_name="custom")

    Returns:
        DataFrame with stock_code, symbol, stock_name, exchange, board columns
    """
    # Load full universe
    universe = load_universe()
    if universe is None:
        logger.warning("Universe not available. Please update stock pool first.")
        return None

    if pool_name == "all_a":
        return universe

    if pool_name == "sh_main":
        return universe[universe["board"] == "沪市主板"]

    if pool_name == "sz_main":
        return universe[universe["board"] == "深市主板"]

    if pool_name == "gem":  # 创业板
        return universe[universe["board"] == "创业板"]

    if pool_name == "star":  # 科创板
        return universe[universe["board"] == "科创板"]

    if pool_name == "bse":  # 北交所
        return universe[universe["board"] == "北交所"]

    # Index-based pools
    if pool_name in ("hs300", "zz500", "zz1000"):
        components = akf.fetch_index_components(pool_name)
        if components:
            return universe[universe["symbol"].isin(components)]
        logger.warning(f"Failed to fetch {pool_name} components, returning all A-shares")
        return universe

    # Custom CSV
    if pool_name == "custom" and custom_csv:
        return _load_custom_pool(custom_csv, universe)

    logger.warning(f"Unknown pool: {pool_name}, returning all A-shares")
    return universe


def update_universe(data_source: str = "akshare") -> Optional[pd.DataFrame]:
    """Fetch and save the latest stock universe.

    Args:
        data_source: "akshare", "tushare", or "auto"
    """
    logger.info(f"Updating stock universe (source: {data_source})...")

    from src.data.data_manager import get_manager
    manager = get_manager(data_source=data_source)

    # Use DataManager which handles Tushare/AKShare routing
    df = manager.get_stock_list(force_refresh=True)

    if df is None:
        logger.error("Failed to fetch stock list from all sources")
        return None

    # Ensure required columns
    required = ["stock_code", "symbol", "stock_name", "exchange"]
    for col in required:
        if col not in df.columns:
            logger.error(f"Missing required column: {col}")
            return None

    # Save
    UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)
    parquet_store.save_df(df, UNIVERSE_PATH)
    logger.info(f"Saved universe: {len(df)} stocks")

    return df


def load_universe() -> Optional[pd.DataFrame]:
    """Load saved universe from local storage."""
    return parquet_store.load_df(UNIVERSE_PATH)


def universe_info() -> dict:
    """Get info about saved universe."""
    df = load_universe()
    if df is None:
        return {"available": False, "count": 0}

    return {
        "available": True,
        "count": len(df),
        "updated_at": parquet_store.last_updated(UNIVERSE_PATH),
        "boards": df["board"].value_counts().to_dict() if "board" in df.columns else {},
    }


def _load_custom_pool(csv_path: Path, universe: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Load custom stock pool from CSV."""
    try:
        custom = pd.read_csv(csv_path, encoding="utf-8-sig")
        # Find code column
        code_col = None
        for col in custom.columns:
            if "代码" in col or "code" in col.lower() or "symbol" in col.lower():
                code_col = col
                break
        if code_col is None:
            code_col = custom.columns[0]

        codes = custom[code_col].astype(str).tolist()
        # Normalize codes
        normalized = [akf.normalize_code(c)[0] for c in codes]

        return universe[universe["stock_code"].isin(normalized)]

    except Exception as e:
        logger.error(f"Failed to load custom pool: {e}")
        return None


POOLS = {
    "all_a": "全部A股",
    "sh_main": "沪市主板",
    "sz_main": "深市主板",
    "gem": "创业板",
    "star": "科创板",
    "bse": "北交所",
    "hs300": "沪深300",
    "zz500": "中证500",
    "zz1000": "中证1000",
    "custom": "自定义(上传CSV)",
}

__all__ = [
    "get_universe", "update_universe", "load_universe",
    "universe_info", "POOLS", "UNIVERSE_PATH",
]
