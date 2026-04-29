"""收益率计算测试"""
import numpy as np
import pandas as pd


def test_simple_return():
    """测试简单收益率计算"""
    close = pd.Series([100, 105, 102, 108, 110])
    ret = close.pct_change().dropna()
    assert len(ret) == 4
    assert abs(ret.iloc[0] - 0.05) < 1e-10
    assert abs(ret.iloc[1] - (-3/105)) < 1e-8


def test_log_return():
    """测试对数收益率计算"""
    close = pd.Series([100, 105, 102, 108, 110])
    log_ret = np.log(close / close.shift(1)).dropna()
    assert len(log_ret) == 4
    assert abs(log_ret.iloc[0] - np.log(105/100)) < 1e-10


def test_cumulative_return():
    """测试累计收益率"""
    ret = pd.Series([0.05, -0.03, 0.06])
    cum = (1 + ret).cumprod() - 1
    expected = (1.05 * 0.97 * 1.06) - 1
    assert abs(cum.iloc[-1] - expected) < 1e-10


def test_annualized_return():
    """测试年化收益率"""
    total_return = 0.5
    n_days = 252 * 3
    ann_ret = (1 + total_return) ** (252 / n_days) - 1
    expected = (1.5 ** (1/3)) - 1
    assert abs(ann_ret - expected) < 1e-10


def test_empty_series():
    """测试空序列"""
    close = pd.Series([], dtype=float)
    ret = close.pct_change().dropna()
    assert len(ret) == 0