"""Shared test fixtures."""

import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def sample_features_df():
    """Create a sample features DataFrame for testing."""
    np.random.seed(42)
    n = 100

    df = pd.DataFrame({
        "stock_code": [f"{i:06d}.SZ" for i in range(1, n + 1)],
        "symbol": [f"{i:06d}" for i in range(1, n + 1)],
        "stock_name": [f"测试股票{i}" for i in range(1, n + 1)],
        "exchange": "SZ",
        "board": np.random.choice(["沪市主板", "深市主板", "创业板", "科创板"], n),
        "industry": np.random.choice(["银行", "医药", "科技", "消费", "制造"], n),
        "is_st": 0,
        "listing_days": np.random.randint(100, 3000, n),
        "latest_close": np.random.uniform(5, 100, n),
        "latest_pct_chg": np.random.uniform(-0.05, 0.05, n),
        "total_mv": np.random.uniform(1e9, 1e12, n),
        "circ_mv": np.random.uniform(5e8, 5e11, n),
        "pe_ttm": np.random.uniform(-20, 100, n),
        "pb": np.random.uniform(0.5, 10, n),
        "roe": np.random.uniform(-10, 30, n),
        "ret_5d": np.random.uniform(-0.1, 0.1, n),
        "ret_20d": np.random.uniform(-0.2, 0.3, n),
        "ret_60d": np.random.uniform(-0.3, 0.5, n),
        "ret_120d": np.random.uniform(-0.4, 0.6, n),
        "ret_252d": np.random.uniform(-0.5, 1.0, n),
        "volatility_20d": np.random.uniform(0.1, 0.8, n),
        "volatility_120d": np.random.uniform(0.15, 0.6, n),
        "max_drawdown_20d": np.random.uniform(-0.3, -0.01, n),
        "max_drawdown_120d": np.random.uniform(-0.5, -0.05, n),
        "beta_120d": np.random.uniform(0.3, 1.8, n),
        "sharpe_120d": np.random.uniform(-1, 2, n),
        "avg_amount_5d": np.random.uniform(1e6, 1e10, n),
        "avg_amount_20d": np.random.uniform(1e6, 1e10, n),
        "avg_amount_60d": np.random.uniform(1e6, 1e10, n),
        "turnover_rate_20d": np.random.uniform(0.1, 15, n),
        "volume_ratio": np.random.uniform(0.3, 3, n),
        "ma5": np.random.uniform(5, 100, n),
        "ma20": np.random.uniform(5, 100, n),
        "ma60": np.random.uniform(5, 100, n),
        "ma120": np.random.uniform(5, 100, n),
        "rsi_14": np.random.uniform(20, 80, n),
        "macd_hist": np.random.uniform(-1, 1, n),
        "is_ma_bullish": np.random.choice([True, False], n),
        "data_quality_score": np.random.uniform(50, 100, n),
        "gross_margin": np.random.uniform(10, 60, n),
        "revenue_growth_yoy": np.random.uniform(-20, 50, n),
        "net_profit_growth_yoy": np.random.uniform(-30, 60, n),
        "amihud_illiquidity_20d": np.random.uniform(1e-10, 1e-6, n),
    })

    # Make some PE negative
    df.loc[0, "pe_ttm"] = -5
    df.loc[1, "pe_ttm"] = np.nan

    return df


@pytest.fixture
def sample_filter_config():
    """Sample filter configuration dict."""
    return {
        "universe": {
            "market": "A股",
            "exclude_st": True,
            "exclude_suspended": True,
            "min_listing_days": 180,
            "min_data_quality_score": 60,
        },
        "stages": [
            {
                "name": "流动性筛选",
                "logic": "AND",
                "rules": [
                    {"field": "avg_amount_20d", "operator": ">=", "value": 5e7},
                ],
            },
            {
                "name": "估值筛选",
                "logic": "AND",
                "rules": [
                    {"field": "pe_ttm", "operator": "between", "value": [0, 50]},
                ],
            },
        ],
        "ranking": {
            "score_model": "balanced",
            "sort_by": "total_score",
            "ascending": False,
            "top_n": 20,
        },
    }
