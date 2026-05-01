"""Percentile-based scoring system for stock screening."""

from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
import yaml

from src.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WEIGHTS_PATH = PROJECT_ROOT / "configs" / "scoring_weights.yaml"

# Winsorization limits
WINSORIZE_LOWER = 0.01
WINSORIZE_UPPER = 0.99

# Sub-score component definitions
# (column_name, direction, description)
SCORE_COMPONENTS = {
    "return_score": [
        ("ret_20d", "higher_better"),
        ("ret_60d", "higher_better"),
        ("ret_120d", "higher_better"),
        ("sharpe_120d", "higher_better"),
    ],
    "risk_score": [
        ("volatility_120d", "lower_better"),
        ("max_drawdown_120d", "higher_better"),  # less negative = better
        ("beta_120d", "lower_better"),  # closer to 1 or lower
    ],
    "liquidity_score": [
        ("avg_amount_20d", "higher_better"),
        ("turnover_rate_20d", "moderate"),  # moderate is best
        ("amihud_illiquidity_20d", "lower_better"),
    ],
    "value_score": [
        ("pe_ttm", "pe_special"),
        ("pb", "lower_better_positive"),
    ],
    "quality_score": [
        ("roe", "higher_better"),
        ("gross_margin", "higher_better"),
        ("operating_cashflow_to_net_profit", "higher_better"),
    ],
    "growth_score": [
        ("revenue_growth_yoy", "higher_better"),
        ("net_profit_growth_yoy", "higher_better"),
    ],
    "technical_score": [
        ("is_ma_bullish", "higher_better"),
        ("rsi_14", "moderate_rsi"),
        ("macd_hist", "higher_better"),
    ],
}


def winsorize(series: pd.Series, lower: float = WINSORIZE_LOWER, upper: float = WINSORIZE_UPPER) -> pd.Series:
    """Winsorize a series to limit extreme values."""
    valid = series.dropna()
    if len(valid) < 10:
        return series
    lo = valid.quantile(lower)
    hi = valid.quantile(upper)
    return series.clip(lo, hi)


def percentile_rank(series: pd.Series, higher_better: bool = True) -> pd.Series:
    """Compute percentile rank (0-100). Higher = better score."""
    valid = series.dropna()
    if len(valid) == 0:
        return pd.Series(np.nan, index=series.index)
    ranks = series.rank(pct=True, na_option="keep") * 100
    if not higher_better:
        ranks = 100 - ranks
    return ranks


def compute_sub_score(
    df: pd.DataFrame,
    components: list[tuple[str, str]],
) -> pd.Series:
    """Compute a sub-score from multiple components using percentile averaging."""
    scores = []

    for col, direction in components:
        if col not in df.columns:
            continue

        series = df[col].astype(float)

        if direction == "higher_better":
            s = percentile_rank(winsorize(series), higher_better=True)
        elif direction == "lower_better":
            s = percentile_rank(winsorize(series), higher_better=False)
        elif direction == "lower_better_positive":
            # Lower is better, but only for positive values
            masked = series.where(series > 0, np.nan)
            s = percentile_rank(winsorize(masked), higher_better=False)
        elif direction == "higher_better_positive":
            masked = series.where(series > 0, np.nan)
            s = percentile_rank(winsorize(masked), higher_better=True)
        elif direction == "pe_special":
            s = _pe_special_score(series)
        elif direction == "moderate":
            s = _moderate_score(series)
        elif direction == "moderate_rsi":
            s = _rsi_score(series)
        else:
            s = percentile_rank(winsorize(series), higher_better=True)

        scores.append(s)

    if not scores:
        return pd.Series(np.nan, index=df.index)

    # Average percentiles across components
    score_df = pd.concat(scores, axis=1)
    return score_df.mean(axis=1)


def _pe_special_score(pe: pd.Series) -> pd.Series:
    """Special scoring for PE: negative/NaN = low score, reasonable range = high score."""
    scores = pd.Series(np.nan, index=pe.index)

    # Negative PE → low score
    neg_mask = pe < 0
    scores[neg_mask] = 15

    # NaN PE → low score
    nan_mask = pe.isna()
    scores[nan_mask] = 20

    # PE > 200 → low score
    extreme_mask = pe > 200
    scores[extreme_mask] = 20

    # PE in [0, 200] → percentile-based (lower PE in range = higher score)
    valid_mask = (pe > 0) & (pe <= 200) & pe.notna()
    if valid_mask.any():
        valid_pe = pe[valid_mask]
        # Invert: lower PE = higher score
        ranks = percentile_rank(valid_pe, higher_better=False)
        scores[valid_mask] = ranks

    return scores


def _moderate_score(series: pd.Series) -> pd.Series:
    """Score where moderate values are best (bell curve)."""
    valid = series.dropna()
    if len(valid) < 5:
        return pd.Series(50, index=series.index)

    median = valid.median()
    std = valid.std()
    if std == 0:
        return pd.Series(50, index=series.index)

    # Score based on distance from median
    z_scores = (series - median).abs() / std
    # Convert to 0-100 where 0 distance = 100
    scores = (1 - z_scores.clip(0, 3) / 3) * 100
    scores[series.isna()] = np.nan
    return scores


def _rsi_score(rsi: pd.Series) -> pd.Series:
    """RSI scoring: 40-60 is neutral (moderate score), oversold/overbought get lower scores."""
    scores = pd.Series(np.nan, index=rsi.index)

    nan_mask = rsi.isna()
    scores[nan_mask] = 30

    # Neutral zone
    neutral = (rsi >= 40) & (rsi <= 60)
    scores[neutral] = 80

    # Mild zones
    mild_bull = (rsi > 60) & (rsi <= 70)
    scores[mild_bull] = 70

    mild_bear = (rsi >= 30) & (rsi < 40)
    scores[mild_bear] = 60

    # Strong zones
    overbought = rsi > 70
    scores[overbought] = 40

    oversold = rsi < 30
    scores[oversold] = 50  # Could be opportunity

    return scores


def load_weights(profile: str = "balanced") -> dict:
    """Load scoring weights from YAML config."""
    try:
        with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
            configs = yaml.safe_load(f)
        if profile in configs:
            return configs[profile]["weights"]
        logger.warning(f"Profile '{profile}' not found, using balanced")
        return configs["balanced"]["weights"]
    except Exception as e:
        logger.error(f"Failed to load scoring weights: {e}")
        # Fallback
        return {
            "return_score": 0.15, "risk_score": 0.20, "liquidity_score": 0.15,
            "value_score": 0.15, "quality_score": 0.15, "growth_score": 0.10,
            "technical_score": 0.05, "data_quality_score": 0.05,
        }


def compute_scores(
    df: pd.DataFrame,
    weights_profile: str = "balanced",
    industry_col: str = "industry",
) -> pd.DataFrame:
    """Compute all sub-scores and total score.

    Args:
        df: Features DataFrame
        weights_profile: Name of weight profile from YAML
        industry_col: Column name for industry (for industry percentiles)

    Returns:
        DataFrame with score columns added
    """
    df = df.copy()
    weights = load_weights(weights_profile)

    # Compute each sub-score
    for score_name, components in SCORE_COMPONENTS.items():
        if score_name in weights and weights[score_name] > 0:
            df[score_name] = compute_sub_score(df, components)
        elif score_name not in df.columns:
            df[score_name] = np.nan

    # Ensure data_quality_score exists
    if "data_quality_score" not in df.columns:
        df["data_quality_score"] = 70  # default

    # Compute weighted total score
    total = pd.Series(0, index=df.index, dtype=float)
    total_weight = 0

    for score_name, weight in weights.items():
        if score_name in df.columns and weight > 0:
            valid = df[score_name].notna()
            total[valid] += df[score_name][valid] * weight
            total_weight += weight

    # Normalize
    if total_weight > 0:
        total = total / total_weight * 100

    # Handle case where all sub-scores are NaN
    all_nan = df[[c for c in weights if c in df.columns]].isna().all(axis=1)
    total[all_nan] = np.nan

    df["total_score"] = total.clip(0, 100)

    return df


def available_profiles() -> dict[str, str]:
    """Return available scoring profiles with descriptions."""
    try:
        with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
            configs = yaml.safe_load(f)
        return {k: v.get("description", k) for k, v in configs.items()}
    except Exception:
        return {"balanced": "均衡型"}


__all__ = [
    "compute_scores", "compute_sub_score", "load_weights",
    "winsorize", "percentile_rank", "available_profiles",
    "SCORE_COMPONENTS",
]
