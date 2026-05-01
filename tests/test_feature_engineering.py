"""Tests for feature engineering and factor library."""

import pandas as pd
import numpy as np
import pytest

from src.screener.factor_library import (
    price_position_52w, compute_returns, volatility, max_drawdown,
    sharpe_ratio, beta, rsi, ema, macd, bollinger_bands,
    is_ma_bullish, liquidity_score, amihud_illiquidity,
)


class TestPricePosition:
    def test_basic(self):
        assert price_position_52w(100, 50, 75) == 0.5

    def test_at_high(self):
        assert price_position_52w(100, 50, 100) == 1.0

    def test_at_low(self):
        assert price_position_52w(100, 50, 50) == 0.0

    def test_equal_high_low(self):
        assert price_position_52w(100, 100, 100) is None

    def test_nan(self):
        assert price_position_52w(np.nan, 50, 75) is None


class TestReturns:
    def test_basic(self):
        close = pd.Series([100, 105, 110, 108, 115])
        result = compute_returns(close, [1, 2, 4])
        assert abs(result["ret_1d"] - (115 / 108 - 1)) < 1e-6
        assert abs(result["ret_4d"] - (115 / 100 - 1)) < 1e-6

    def test_insufficient_data(self):
        close = pd.Series([100, 105])
        result = compute_returns(close, [5])
        assert result["ret_5d"] is None


class TestVolatility:
    def test_basic(self):
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0, 0.02, 100))
        vol = volatility(returns, 60)
        assert vol is not None
        assert vol > 0

    def test_insufficient_data(self):
        returns = pd.Series([0.01, -0.01])
        assert volatility(returns, 60) is None


class TestMaxDrawdown:
    def test_basic(self):
        close = pd.Series([100, 110, 105, 95, 100])
        mdd = max_drawdown(close, 5)
        assert mdd is not None
        assert mdd <= 0
        assert abs(mdd - (95 - 110) / 110) < 1e-6

    def test_no_drawdown(self):
        close = pd.Series([100, 105, 110, 115, 120])
        mdd = max_drawdown(close, 5)
        assert mdd == 0


class TestSharpe:
    def test_basic(self):
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        sr = sharpe_ratio(returns, 60)
        assert sr is not None

    def test_zero_vol(self):
        returns = pd.Series([0.001] * 100)
        sr = sharpe_ratio(returns, 60)
        # Constant returns have near-zero std, Sharpe should be extremely large or None
        assert sr is None or abs(sr) > 1e10


class TestRSI:
    def test_basic(self):
        np.random.seed(42)
        close = pd.Series(np.cumsum(np.random.normal(0, 1, 50)) + 100)
        val = rsi(close, 14)
        assert val is not None
        assert 0 <= val <= 100

    def test_insufficient_data(self):
        close = pd.Series([100, 101])
        assert rsi(close, 14) is None


class TestMACD:
    def test_basic(self):
        np.random.seed(42)
        close = pd.Series(np.cumsum(np.random.normal(0, 1, 100)) + 100)
        m, s, h = macd(close)
        assert len(m) == 100
        assert len(s) == 100
        assert len(h) == 100


class TestBollinger:
    def test_basic(self):
        np.random.seed(42)
        close = pd.Series(np.cumsum(np.random.normal(0, 1, 50)) + 100)
        mid, upper, lower = bollinger_bands(close)
        assert upper.iloc[-1] > mid.iloc[-1] > lower.iloc[-1]


class TestMABullish:
    def test_bullish(self):
        assert is_ma_bullish(110, 105, 100, 95) is True

    def test_not_bullish(self):
        assert is_ma_bullish(95, 100, 105, 110) is False

    def test_nan(self):
        assert is_ma_bullish(100, np.nan, 100, 100) is False


class TestLiquidityScore:
    def test_high_liquidity(self):
        score = liquidity_score(1e9, 3, 1.2)
        assert score is not None
        assert score >= 70

    def test_low_liquidity(self):
        score = liquidity_score(1e6, 0.1, 0.3)
        assert score is not None
        assert score <= 50

    def test_none_values(self):
        score = liquidity_score(None, None, None)
        assert score is None


class TestAmihud:
    def test_basic(self):
        returns = pd.Series([0.01, -0.02, 0.015, -0.01, 0.005])
        amounts = pd.Series([1e8, 2e8, 1.5e8, 1e8, 2e8])
        result = amihud_illiquidity(returns, amounts, 5)
        assert result is not None
        assert result > 0
