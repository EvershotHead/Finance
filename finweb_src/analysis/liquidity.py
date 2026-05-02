"""模块11：流动性分析"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from finweb_src.utils.logger import get_logger

logger = get_logger("Liquidity")


@dataclass
class LiquidityResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_liquidity(df: pd.DataFrame) -> LiquidityResult:
    """流动性分析

    Args:
        df: 包含 date, close, volume, amount, simple_return 的 DataFrame
    """
    result = LiquidityResult()
    try:
        if df is None or df.empty:
            result.error = "数据为空"
            return result

        data = {}

        # 成交量统计
        if "volume" in df.columns:
            vol = df["volume"].astype(float)
            data["成交量均值"] = round(float(vol.mean()), 0)
            data["成交量中位数"] = round(float(vol.median()), 0)
            data["成交量标准差"] = round(float(vol.std()), 0)
            data["成交量变异系数"] = round(float(vol.std() / vol.mean()), 4) if vol.mean() > 0 else 0

            # 近20日成交额相对历史分位数
            if len(vol) >= 20:
                recent_20 = float(vol.iloc[-20:].mean())
                percentile = float((vol < recent_20).mean())
                data["近20日成交量分位数"] = round(percentile, 4)

        # 成交额统计
        if "amount" in df.columns:
            amt = df["amount"].astype(float)
            data["成交额均值"] = round(float(amt.mean()), 0)
            data["成交额中位数"] = round(float(amt.median()), 0)

        # Amihud 非流动性指标
        if "simple_return" in df.columns and "amount" in df.columns:
            ret = df["simple_return"].astype(float)
            amt = df["amount"].astype(float).replace(0, np.nan)
            amihud = (ret.abs() / amt).dropna()
            if not amihud.empty:
                data["Amihud_均值"] = round(float(amihud.mean()), 10)
                data["Amihud_中位数"] = round(float(amihud.median()), 10)

        # 换手率
        if "turnover_rate" in df.columns:
            tr = df["turnover_rate"].astype(float).dropna()
            if not tr.empty:
                data["换手率均值"] = round(float(tr.mean()), 4)
                data["换手率标准差"] = round(float(tr.std()), 4)

        # 量价相关性
        if "volume" in df.columns and "close" in df.columns:
            corr = float(df["volume"].astype(float).corr(df["close"].astype(float)))
            data["量价相关系数"] = round(corr, 4)

        result.data = data
        result.success = True

        parts = []
        if "成交量均值" in data:
            parts.append(f"成交量均值: {data['成交量均值']:.0f}")
        if "近20日成交量分位数" in data:
            p = data["近20日成交量分位数"]
            parts.append(f"近20日成交量处于历史 {p*100:.1f}% 分位，{'成交量近期放大' if p > 0.7 else '成交量近期萎缩' if p < 0.3 else '成交量近期正常'}。")
        if "Amihud_均值" in data:
            parts.append(f"Amihud非流动性指标均值: {data['Amihud_均值']:.2e}")
        if "量价相关系数" in data:
            c = data["量价相关系数"]
            parts.append(f"量价相关系数: {c:.4f}，{'量价配合' if c > 0.3 else '量价背离' if c < -0.3 else '量价关系不明显'}。")

        result.interpretation = "\n".join(parts) if parts else "流动性数据不足，无法完成分析。"

    except Exception as e:
        result.error = f"流动性分析失败: {str(e)}"
        logger.error(result.error)

    return result