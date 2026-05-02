"""模块13：滚动窗口分析"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from finweb_src.utils.logger import get_logger

logger = get_logger("Rolling")


@dataclass
class RollingResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_rolling(stock_df: pd.DataFrame, index_df: pd.DataFrame = None,
                    rf_annual: float = 0.02, windows: list[int] = None) -> RollingResult:
    """滚动窗口分析

    Args:
        stock_df: 股票数据（含 simple_return）
        index_df: 基准数据（含 index_simple_return）
        rf_annual: 年化无风险利率
        windows: 滚动窗口列表，默认 [20, 60, 120]
    """
    result = RollingResult()
    try:
        if windows is None:
            windows = [20, 60, 120]

        ret = stock_df["simple_return"].dropna()
        if len(ret) < max(windows):
            result.error = f"数据量不足: {len(ret)}，需要至少{max(windows)}条"
            return result

        td = 252
        data = {}
        rolling_df = pd.DataFrame({"date": stock_df["date"].iloc[ret.index]})

        for w in windows:
            if len(ret) < w:
                continue

            # 滚动收益率
            rr = ret.rolling(w).sum()
            rolling_df[f"return_{w}d"] = rr

            # 滚动波动率
            rv = ret.rolling(w).std() * np.sqrt(td)
            rolling_df[f"volatility_{w}d"] = rv

            # 滚动Sharpe (仅对60/120日)
            if w >= 60:
                rf_daily = (1 + rf_annual) ** (1 / td) - 1
                ann_ret = ret.rolling(w).mean() * td
                rs = (ann_ret - rf_annual) / rv
                rolling_df[f"sharpe_{w}d"] = rs

            # 滚动Beta/Alpha (需要基准)
            if index_df is not None and "index_simple_return" in index_df.columns and w >= 60:
                br = index_df["index_simple_return"].reindex(ret.index)
                roll_cov = ret.rolling(w).cov(br)
                roll_var = br.rolling(w).var()
                roll_beta = roll_cov / roll_var.replace(0, np.nan)
                rolling_df[f"beta_{w}d"] = roll_beta

                rf_daily = (1 + rf_annual) ** (1 / td) - 1
                roll_alpha = (ret.rolling(w).mean() - roll_beta * br.rolling(w).mean()) * td
                rolling_df[f"alpha_{w}d"] = roll_alpha

                # 滚动相关系数
                roll_corr = ret.rolling(w).corr(br)
                rolling_df[f"corr_{w}d"] = roll_corr

        # 滚动最大回撤
        cumret = (1 + ret).cumprod()
        rolling_max = cumret.rolling(120, min_periods=20).max()
        rolling_dd = (cumret - rolling_max) / rolling_max
        rolling_df["drawdown_120d"] = rolling_dd

        # 统计摘要
        for col in rolling_df.columns:
            if col == "date":
                continue
            vals = rolling_df[col].dropna()
            if not vals.empty:
                data[f"{col}_均值"] = round(float(vals.mean()), 4)
                data[f"{col}_最新"] = round(float(vals.iloc[-1]), 4) if not np.isnan(vals.iloc[-1]) else None

        result.data = data
        result.figures["rolling_df"] = rolling_df
        result.success = True

        # 中文解读
        parts = []
        for w in [60, 120]:
            key = f"volatility_{w}d_最新"
            if key in data and data[key] is not None:
                vol = data[key]
                parts.append(f"{w}日滚动年化波动率: {vol*100:.2f}%")
            key2 = f"sharpe_{w}d_最新"
            if key2 in data and data[key2] is not None:
                sh = data[key2]
                parts.append(f"{w}日滚动Sharpe: {sh:.3f}")
            key3 = f"beta_{w}d_最新"
            if key3 in data and data[key3] is not None:
                beta = data[key3]
                parts.append(f"{w}日滚动Beta: {beta:.3f}")

        if parts:
            parts.append("滚动指标可以反映风险收益特征随时间的变化趋势。")
        result.interpretation = "\n".join(parts) if parts else "滚动分析数据不足。"

    except Exception as e:
        result.error = f"滚动分析失败: {str(e)}"
        logger.error(result.error)

    return result