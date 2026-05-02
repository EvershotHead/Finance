"""模块14：简单策略回测"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from finweb_src.utils.logger import get_logger

logger = get_logger("Backtest")


@dataclass
class BacktestResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def _calc_stats(signals, returns, commission=0.0003):
    """计算策略统计指标"""
    trades = signals.diff().abs().fillna(0)
    cost = trades * commission
    sr = signals.shift(1).fillna(0) * returns - cost
    cum_ret = float((1 + sr).prod() - 1)
    n = len(sr)
    ann_ret = float((1 + cum_ret) ** (252 / n) - 1) if n > 0 else 0
    ann_vol = float(sr.std() * np.sqrt(252))
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    cummax = (1 + sr).cumprod().cummax()
    dd = ((1 + sr).cumprod() - cummax) / cummax
    max_dd = float(dd.min())
    tc = int(trades.sum() / 2)
    wr = float((sr[sr != 0] > 0).mean()) if (sr != 0).any() else 0
    return {
        "累计收益率": round(cum_ret, 6), "年化收益率": round(ann_ret, 6),
        "年化波动率": round(ann_vol, 6), "Sharpe": round(sharpe, 4),
        "最大回撤": round(max_dd, 6), "交易次数": tc, "胜率": round(wr, 4),
        "_sr": sr,
    }


def _interp(stats, name):
    p = [f"{name}回测结果：", f"累计收益: {stats['累计收益率']*100:.2f}%",
         f"年化收益: {stats['年化收益率']*100:.2f}%", f"最大回撤: {abs(stats['最大回撤'])*100:.2f}%",
         f"Sharpe: {stats['Sharpe']:.4f}", f"交易次数: {stats['交易次数']}",
         f"胜率: {stats['胜率']*100:.1f}%",
         f"同期买入持有: {stats.get('bh_cum',0)*100:.2f}%",
         "\n⚠️ 简单技术策略回测仅用于学习和辅助分析，不构成投资建议，且历史表现不代表未来。"]
    return "\n".join(p)


def backtest_dual_ma(df, fast=20, slow=60, commission=0.0003):
    """双均线策略"""
    result = BacktestResult()
    try:
        close = df["close"].astype(float)
        ret = close.pct_change().fillna(0)
        ma_f, ma_s = close.rolling(fast).mean(), close.rolling(slow).mean()
        sig = (ma_f > ma_s).astype(int); sig.iloc[:slow] = 0
        stats = _calc_stats(sig, ret, commission)
        stats["策略名称"] = f"双均线(MA{fast}/MA{slow})"
        stats["strategy_nv"] = (1 + stats.pop("_sr").fillna(0)).cumprod()
        stats["benchmark_nv"] = (1 + ret).cumprod()
        stats["bh_cum"] = float(stats["benchmark_nv"].iloc[-1] - 1)
        result.data = stats; result.success = True
        result.interpretation = _interp(stats, stats["策略名称"])
    except Exception as e:
        result.error = f"双均线回测失败: {e}"; logger.error(result.error)
    return result


def backtest_rsi(df, period=14, buy_th=30, sell_th=70, commission=0.0003):
    """RSI策略"""
    result = BacktestResult()
    try:
        close = df["close"].astype(float)
        ret = close.pct_change().fillna(0)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
        sig = pd.Series(0, index=df.index); pos = 0
        for i in range(period, len(rsi)):
            if rsi.iloc[i] < buy_th and pos == 0: pos = 1
            elif rsi.iloc[i] > sell_th and pos == 1: pos = 0
            sig.iloc[i] = pos
        stats = _calc_stats(sig, ret, commission)
        stats["策略名称"] = f"RSI({period},{buy_th}/{sell_th})"
        stats["strategy_nv"] = (1 + stats.pop("_sr").fillna(0)).cumprod()
        stats["benchmark_nv"] = (1 + ret).cumprod()
        stats["bh_cum"] = float(stats["benchmark_nv"].iloc[-1] - 1)
        result.data = stats; result.success = True
        result.interpretation = _interp(stats, stats["策略名称"])
    except Exception as e:
        result.error = f"RSI回测失败: {e}"; logger.error(result.error)
    return result


def backtest_bollinger(df, period=20, std_mult=2.0, commission=0.0003):
    """布林带策略"""
    result = BacktestResult()
    try:
        close = df["close"].astype(float)
        ret = close.pct_change().fillna(0)
        mid = close.rolling(period).mean()
        lower = mid - std_mult * close.rolling(period).std()
        sig = pd.Series(0, index=df.index); pos = 0
        for i in range(period, len(close)):
            if close.iloc[i] < lower.iloc[i] and pos == 0: pos = 1
            elif close.iloc[i] > mid.iloc[i] and pos == 1: pos = 0
            sig.iloc[i] = pos
        stats = _calc_stats(sig, ret, commission)
        stats["策略名称"] = "布林带策略"
        stats["strategy_nv"] = (1 + stats.pop("_sr").fillna(0)).cumprod()
        stats["benchmark_nv"] = (1 + ret).cumprod()
        stats["bh_cum"] = float(stats["benchmark_nv"].iloc[-1] - 1)
        result.data = stats; result.success = True
        result.interpretation = _interp(stats, stats["策略名称"])
    except Exception as e:
        result.error = f"布林带回测失败: {e}"; logger.error(result.error)
    return result