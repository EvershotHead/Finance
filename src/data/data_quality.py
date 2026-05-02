"""Data quality checks and cleaning."""

from typing import Optional

import pandas as pd
import numpy as np

from src.utils.logger import logger


def clean_daily_bars(df: pd.DataFrame) -> pd.DataFrame:

    """Clean daily bar data.

    - Standardize dates
    - Remove duplicates
    - Convert types
    - Mark anomalies
    """
    if df is None or len(df) == 0:
        return df

    df = df.copy()

    # Date standardization
    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"])

    # Stock code standardization
    if "stock_code" in df.columns:
        df["stock_code"] = df["stock_code"].astype(str).str.strip()

    # Numeric columns
    numeric_cols = ["open", "high", "low", "close", "volume", "amount", "pct_chg", "pre_close"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remove duplicates
    if "stock_code" in df.columns and "trade_date" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["stock_code", "trade_date"], keep="last")
        if len(df) < before:
            logger.debug(f"Removed {before - len(df)} duplicate daily bar rows")

    # Sort
    sort_cols = [c for c in ["stock_code", "trade_date"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    return df


def clean_daily_basic(df: pd.DataFrame) -> pd.DataFrame:
    """Clean daily basic indicator data."""
    if df is None or len(df) == 0:
        return df

    df = df.copy()

    # Date standardization
    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"])

    if "stock_code" in df.columns:
        df["stock_code"] = df["stock_code"].astype(str).str.strip()

    # Numeric conversion
    float_cols = [c for c in df.columns if c not in ("stock_code", "trade_date", "stock_name")]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remove duplicates
    if "stock_code" in df.columns and "trade_date" in df.columns:
        df = df.drop_duplicates(subset=["stock_code", "trade_date"], keep="last")

    return df


def compute_data_quality_score(row: pd.Series) -> float:
    """Compute data quality score for a stock (0-100)."""
    score = 100.0

    # Missing price data penalty
    if row.get("missing_price_days", 0) > 10:
        score -= min(row["missing_price_days"], 30)

    # Missing basic data penalty
    if row.get("missing_basic_days", 0) > 10:
        score -= min(row["missing_basic_days"] * 0.5, 15)

    # ST penalty
    if row.get("is_st", 0):
        score -= 10

    # Recent listing penalty
    if row.get("listing_days", 999) < 90:
        score -= 15
    elif row.get("listing_days", 999) < 180:
        score -= 5

    # Negative PE penalty
    if row.get("has_negative_pe", False):
        score -= 5

    # Low liquidity penalty
    if row.get("has_low_liquidity", False):
        score -= 10

    # Suspended days penalty
    suspended = row.get("suspended_days_60d", 0)
    if suspended > 5:
        score -= min(suspended * 2, 20)

    return max(0, min(100, score))


def compute_quality_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute quality indicators for each stock in features DataFrame."""
    df = df.copy()

    # Data quality score
    if "data_quality_score" not in df.columns:
        df["data_quality_score"] = df.apply(compute_data_quality_score, axis=1)

    # Generate warnings
    def _get_warnings(row):
        warnings = []
        if row.get("is_st", 0):
            warnings.append("ST股票")
        if row.get("has_negative_pe", False):
            warnings.append("PE为负")
        if row.get("has_extreme_pe", False):
            warnings.append("PE极高")
        if row.get("has_low_liquidity", False):
            warnings.append("流动性不足")
        if row.get("listing_days", 999) < 180:
            warnings.append("上市时间较短")
        if row.get("suspended_days_60d", 0) > 3:
            warnings.append("近期有停牌")
        return "; ".join(warnings) if warnings else ""

    df["data_warnings"] = df.apply(_get_warnings, axis=1)

    return df


__all__ = [
    "clean_daily_bars", "clean_daily_basic",
    "compute_data_quality_score", "compute_quality_indicators",
]
