"""模块1：基础行情表现分析"""

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("Performance")


@dataclass
class PerformanceResult:
    """行情表现分析结果"""
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_performance(df: pd.DataFrame, rf_annual: float = 0.02) -> PerformanceResult:
    """分析基础行情表现

    Args:
        df: 包含 date, open, high, low, close, volume, amount, simple_return 的 DataFrame
        rf_annual: 年化无风险利率

    Returns:
        PerformanceResult
    """
    result = PerformanceResult()

    try:
        if df is None or df.empty or "close" not in df.columns:
            result.error = "数据为空或缺少收盘价"
            return result

        close = df["close"].astype(float)
        ret = df["simple_return"].dropna() if "simple_return" in df.columns else close.pct_change().dropna()

        n_days = len(ret)
        trading_days = 252

        # 年化系数
        ann_factor = n_days / trading_days if n_days > 0 else 1

        # 基础统计
        data = {
            "最新收盘价": round(float(close.iloc[-1]), 4),
            "区间最高价": round(float(close.max()), 4),
            "区间最低价": round(float(close.min()), 4),
            "最高价日期": str(df.loc[close.idxmax(), "date"].date()) if "date" in df.columns else "",
            "最低价日期": str(df.loc[close.idxmin(), "date"].date()) if "date" in df.columns else "",
        }

        # 收益率
        cum_ret = float((1 + ret).prod() - 1)
        ann_ret = float((1 + cum_ret) ** (1 / ann_factor) - 1) if ann_factor > 0 else 0
        ann_vol = float(ret.std() * np.sqrt(trading_days))
        mean_daily = float(ret.mean())
        std_daily = float(ret.std())

        data["区间累计收益率"] = round(cum_ret, 6)
        data["区间年化收益率"] = round(ann_ret, 6)
        data["区间年化波动率"] = round(ann_vol, 6)
        data["平均日收益率"] = round(mean_daily, 6)
        data["日收益率标准差"] = round(std_daily, 6)

        # 涨跌统计
        up_days = int((ret > 0).sum())
        down_days = int((ret < 0).sum())
        win_rate = up_days / n_days if n_days > 0 else 0

        data["上涨交易日"] = up_days
        data["下跌交易日"] = down_days
        data["胜率"] = round(win_rate, 4)
        data["最大单日涨幅"] = round(float(ret.max()), 6)
        data["最大单日跌幅"] = round(float(ret.min()), 6)

        # 成交量统计
        if "volume" in df.columns:
            vol = df["volume"].astype(float)
            data["成交量均值"] = round(float(vol.mean()), 0)
            data["成交量标准差"] = round(float(vol.std()), 0)
        if "amount" in df.columns:
            amt = df["amount"].astype(float)
            data["成交额均值"] = round(float(amt.mean()), 0)

        # 价格分位数位置
        current_price = float(close.iloc[-1])
        price_percentile = float((close < current_price).mean())
        data["当前价格分位数"] = round(price_percentile, 4)

        # 计算回撤
        cummax = close.cummax()
        drawdown = (close - cummax) / cummax
        max_dd = float(drawdown.min())
        max_dd_idx = drawdown.idxmin()
        data["最大回撤"] = round(max_dd, 6)

        if "date" in df.columns:
            data["最大回撤开始日期"] = str(df.loc[:max_dd_idx, "date"].iloc[0].date()) if max_dd_idx is not None else ""
            data["最大回撤最低点日期"] = str(df.loc[max_dd_idx, "date"].date()) if max_dd_idx is not None else ""

        result.data = data
        result.success = True

        # 中文解读
        interp_parts = []
        interp_parts.append(f"分析区间共 {n_days} 个交易日。")
        interp_parts.append(f"该股票区间累计收益率为 {cum_ret*100:.2f}%，年化收益率为 {ann_ret*100:.2f}%。")
        interp_parts.append(f"年化波动率为 {ann_vol*100:.2f}%，最大回撤为 {abs(max_dd)*100:.2f}%。")
        interp_parts.append(f"上涨交易日 {up_days} 天，下跌交易日 {down_days} 天，胜率为 {win_rate*100:.1f}%。")
        interp_parts.append(f"当前价格处于历史 {price_percentile*100:.1f}% 分位水平。")

        if ann_vol > 0.4:
            interp_parts.append("⚠️ 年化波动率超过40%，属于高波动品种，风险较高。")
        elif ann_vol > 0.25:
            interp_parts.append("年化波动率处于中等偏高水平。")
        else:
            interp_parts.append("年化波动率相对温和。")

        if abs(max_dd) > 0.5:
            interp_parts.append(f"⚠️ 最大回撤达 {abs(max_dd)*100:.1f}%，回撤风险显著。")

        result.interpretation = "\n".join(interp_parts)

        logger.info(f"基础行情分析完成: 累计收益={cum_ret*100:.2f}%, 年化波动={ann_vol*100:.2f}%, 最大回撤={max_dd*100:.2f}%")

    except Exception as e:
        result.error = f"基础行情分析失败: {str(e)}"
        logger.error(result.error)

    return result