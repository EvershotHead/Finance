"""Stock comparison logic."""

import pandas as pd
import numpy as np

from src.utils.logger import logger

# Dimensions for comparison
DIMENSIONS = {
    "收益": ["ret_5d", "ret_20d", "ret_60d", "ret_120d", "ret_252d"],
    "风险": ["volatility_120d", "max_drawdown_120d", "beta_120d", "sharpe_120d"],
    "估值": ["pe_ttm", "pb", "ps_ttm", "total_mv"],
    "基本面": ["roe", "roa", "gross_margin", "net_margin", "revenue_growth_yoy", "net_profit_growth_yoy"],
    "流动性": ["avg_amount_20d", "turnover_rate_20d", "amihud_illiquidity_20d"],
    "评分": ["total_score", "risk_score", "liquidity_score", "value_score", "quality_score", "technical_score"],
}


def compare_stocks(
    features_df: pd.DataFrame,
    stock_codes: list[str],
    dimensions: list[str] = None,
) -> dict:
    """Compare multiple stocks across specified dimensions.

    Args:
        features_df: Full features DataFrame
        stock_codes: List of stock_code values to compare
        dimensions: List of dimension names (from DIMENSIONS keys)

    Returns:
        dict with comparison data
    """
    if dimensions is None:
        dimensions = list(DIMENSIONS.keys())

    # Filter to selected stocks
    selected = features_df[features_df["stock_code"].isin(stock_codes)].copy()

    if len(selected) == 0:
        return {"error": "No matching stocks found"}

    # Build comparison data
    comparison = {
        "stocks": selected[["stock_code", "stock_name"]].to_dict(orient="records") if "stock_name" in selected.columns else [],
        "dimensions": {},
    }

    for dim_name in dimensions:
        fields = DIMENSIONS.get(dim_name, [])
        available = [f for f in fields if f in selected.columns]
        if available:
            comparison["dimensions"][dim_name] = selected[["stock_code"] + available].to_dict(orient="records")

    return comparison


def build_radar_data(
    features_df: pd.DataFrame,
    stock_codes: list[str],
) -> list[dict]:
    """Build radar chart data for stock comparison.

    Returns list of dicts with stock_code, stock_name, and score dimensions.
    """
    selected = features_df[features_df["stock_code"].isin(stock_codes)].copy()

    score_cols = ["return_score", "risk_score", "liquidity_score",
                  "value_score", "quality_score", "technical_score"]
    available = [c for c in score_cols if c in selected.columns]

    radar_data = []
    for _, row in selected.iterrows():
        entry = {
            "stock_code": row.get("stock_code", ""),
            "stock_name": row.get("stock_name", ""),
        }
        for col in available:
            entry[col] = row.get(col, 0)
        radar_data.append(entry)

    return radar_data


__all__ = ["compare_stocks", "build_radar_data", "DIMENSIONS"]
