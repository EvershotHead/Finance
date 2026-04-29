"""风险指标测试"""
import numpy as np
import pandas as pd


def test_max_drawdown():
    """测试最大回撤计算"""
    close = pd.Series([100, 110, 90, 95, 80, 100])
    cummax = close.cummax()
    drawdown = (close - cummax) / cummax
    max_dd = float(drawdown.min())
    # 最大回撤应为 (80-110)/110
    assert abs(max_dd - (-30/110)) < 1e-4


def test_var_historical():
    """测试历史VaR"""
    np.random.seed(42)
    ret = pd.Series(np.random.normal(0, 0.02, 1000))
    var_95 = float(ret.quantile(0.05))
    assert var_95 < 0  # VaR应为负数
    assert abs(var_95) < 0.1  # 应在合理范围


def test_sharpe_ratio():
    """测试Sharpe比率"""
    ann_ret = 0.15
    ann_vol = 0.20
    rf = 0.02
    sharpe = (ann_ret - rf) / ann_vol
    assert abs(sharpe - 0.65) < 1e-10


def test_sortino_ratio():
    """测试Sortino比率"""
    ret = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
    rf = 0.0
    mean_ret = ret.mean()
    downside = ret[ret < 0]
    downside_std = downside.std() if len(downside) > 0 else 0
    if downside_std > 0:
        sortino = mean_ret / downside_std
        assert sortino > 0