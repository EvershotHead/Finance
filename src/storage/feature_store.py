"""Feature store management — load/save latest and daily features."""

from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd

from src.storage import parquet_store
from src.storage.schemas import FeatureStoreMeta
from src.utils.logger import logger

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FEATURE_DIR = PROJECT_ROOT / "data" / "feature_store"
LATEST_PATH = FEATURE_DIR / "stock_features_latest.parquet"
DAILY_PATH = FEATURE_DIR / "stock_features_daily.parquet"
INDUSTRY_PCT_PATH = FEATURE_DIR / "industry_percentiles.parquet"
QUALITY_PATH = FEATURE_DIR / "data_quality.parquet"


def ensure_dirs():
    """Ensure feature store directories exist."""
    FEATURE_DIR.mkdir(parents=True, exist_ok=True)


def load_latest_features(
    stock_codes: Optional[list[str]] = None,
    fields: Optional[list[str]] = None,
) -> Optional[pd.DataFrame]:
    """Load latest features for screening."""
    df = parquet_store.load_df(LATEST_PATH, columns=fields)
    if df is not None and stock_codes:
        df = df[df["stock_code"].isin(stock_codes)]
    return df


def save_latest_features(df: pd.DataFrame) -> Path:
    """Save latest features."""
    ensure_dirs()
    path = parquet_store.save_df(df, LATEST_PATH)
    logger.info(f"Saved latest features: {len(df)} stocks")
    return path


def load_daily_features(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stock_codes: Optional[list[str]] = None,
) -> Optional[pd.DataFrame]:
    """Load daily features."""
    df = parquet_store.load_df(DAILY_PATH)
    if df is None:
        return None
    if "trade_date" in df.columns:
        if start_date:
            df = df[df["trade_date"] >= start_date]
        if end_date:
            df = df[df["trade_date"] <= end_date]
    if stock_codes:
        df = df[df["stock_code"].isin(stock_codes)]
    return df


def save_daily_features(df: pd.DataFrame) -> Path:
    """Save daily features."""
    ensure_dirs()
    return parquet_store.save_df(df, DAILY_PATH)


def save_industry_percentiles(df: pd.DataFrame) -> Path:
    """Save industry percentile data."""
    ensure_dirs()
    return parquet_store.save_df(df, INDUSTRY_PCT_PATH)


def load_industry_percentiles() -> Optional[pd.DataFrame]:
    """Load industry percentile data."""
    return parquet_store.load_df(INDUSTRY_PCT_PATH)


def save_quality_data(df: pd.DataFrame) -> Path:
    """Save data quality info."""
    ensure_dirs()
    return parquet_store.save_df(df, QUALITY_PATH)


def load_quality_data() -> Optional[pd.DataFrame]:
    """Load data quality info."""
    return parquet_store.load_df(QUALITY_PATH)


def get_metadata() -> FeatureStoreMeta:
    """Get feature store metadata."""
    df = load_latest_features()
    if df is None:
        return FeatureStoreMeta()

    latest_date = None
    if "latest_trade_date" in df.columns and len(df) > 0:
        latest_date = df["latest_trade_date"].dropna().max()

    return FeatureStoreMeta(
        latest_trade_date=latest_date,
        stock_count=len(df),
        feature_count=len(df.columns),
        updated_at=parquet_store.last_updated(LATEST_PATH),
        data_source="akshare",
    )


def is_available() -> bool:
    """Check if feature store is available."""
    return parquet_store.exists(LATEST_PATH)


__all__ = [
    "load_latest_features", "save_latest_features",
    "load_daily_features", "save_daily_features",
    "save_industry_percentiles", "load_industry_percentiles",
    "save_quality_data", "load_quality_data",
    "get_metadata", "is_available",
    "LATEST_PATH", "DAILY_PATH", "FEATURE_DIR",
]
