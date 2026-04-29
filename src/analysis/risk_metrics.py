"""模块3：风险指标分析"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from src.utils.logger import get_logger

logger = get_logger("RiskMetrics")


@dataclass
class RiskResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def _max_drawdown_details(close: pd.Series) -> dict:
    """计算最大回撤详情"""
    cummax = close.cummax()
    drawdown = (close - cummax) / cummax
    max_dd = float(drawdown.min())
    max_dd_idx = drawdown.idxmin()

    # 找回撤开始点
    peak_idx = close[:max_dd_idx].idxmax() if max_dd_idx > 0 else 0
    # 找修复点
    recovery_mask = close[max_dd_idx:] >= close[peak_idx]
    recovery_idx = recovery_mask.idxmax() if recovery_mask.any() else None

    return {
        "最大回撤": round(max_dd, 6),
        "最大回撤开始索引": int(peak_idx),
        "最大回撤最低点索引": int(max_dd_idx),
        "最大回撤修复索引": int(recovery_idx) if recovery_idx is not None else None,
        "drawdown_series": drawdown,
    }


def analyze_risk(df: pd.DataFrame, rf_annual: float = 0.02) -> RiskResult:
    """全面风险指标分析

    Args:
        df: 包含 date, close, simple_return 列的 DataFrame
        rf_annual: 年化无风险利率
    """
    result = RiskResult()
    try:
        if df is None or df.empty or "simple_return" not in df.columns:
            result.error = "数据为空或缺少收益率列"
            return result

        close = df["close"].astype(float)
        ret = df["simple_return"].dropna()
        n = len(ret)
        td = 252

        rf_daily = (1 + rf_annual) ** (1 / td) - 1
        excess = ret - rf_daily

        data = {}

        # ===== 回撤 =====
        dd_info = _max_drawdown_details(close)
        data["最大回撤"] = dd_info["最大回撤"]
        if "date" in df.columns:
            si, mi = dd_info["最大回撤开始索引"], dd_info["最大回撤最低点索引"]
            data["最大回撤开始日期"] = str(df.iloc[si]["date"].date())
            data["最大回撤最低点日期"] = str(df.iloc[mi]["date"].date())
            if dd_info["最大回撤修复索引"] is not None:
                data["最大回撤修复日期"] = str(df.iloc[dd_info["最大回撤修复索引"]]["date"].date())
            else:
                data["最大回撤修复日期"] = "尚未修复"

        # ===== 波动率 =====
        ann_vol = float(ret.std() * np.sqrt(td))
        data["年化波动率"] = round(ann_vol, 6)

        # 下行波动率
        downside_ret = ret[ret < 0]
        downside_vol = float(downside_ret.std() * np.sqrt(td)) if len(downside_ret) > 0 else 0
        data["下行波动率"] = round(downside_vol, 6)

        # ===== VaR =====
        # 历史模拟法
        data["VaR_95_历史"] = round(float(ret.quantile(0.05)), 6)
        data["VaR_99_历史"] = round(float(ret.quantile(0.01)), 6)

        # 参数法
        z_95 = stats.norm.ppf(0.05)
        z_99 = stats.norm.ppf(0.01)
        data["VaR_95_参数法"] = round(float(ret.mean() + z_95 * ret.std()), 6)
        data["VaR_99_参数法"] = round(float(ret.mean() + z_99 * ret.std()), 6)

        # Cornish-Fisher VaR
        try:
            s = float(ret.skew())
            k = float(ret.kurtosis())
            z_cf_95 = z_95 + (z_95**2 - 1) * s / 6 + (z_95**3 - 3*z_95) * k / 24 - (2*z_95**3 - 5*z_95) * s**2 / 36
            z_cf_99 = z_99 + (z_99**2 - 1) * s / 6 + (z_99**3 - 3*z_99) * k / 24 - (2*z_99**3 - 5*z_99) * s**2 / 36
            data["VaR_95_CF"] = round(float(ret.mean() + z_cf_95 * ret.std()), 6)
            data["VaR_99_CF"] = round(float(ret.mean() + z_cf_99 * ret.std()), 6)
        except Exception:
            data["VaR_95_CF"] = "计算失败"
            data["VaR_99_CF"] = "计算失败"

        # ===== CVaR / Expected Shortfall =====
        data["CVaR_95"] = round(float(ret[ret <= ret.quantile(0.05)].mean()), 6)
        data["CVaR_99"] = round(float(ret[ret <= ret.quantile(0.01)].mean()), 6)

        # ===== 收益风险比 =====
        mean_ret = float(ret.mean())
        ann_ret = float((1 + ret).prod() ** (td / n) - 1)

        data["Sharpe_Ratio"] = round((ann_ret - rf_annual) / ann_vol, 4) if ann_vol != 0 else 0
        data["Sortino_Ratio"] = round((ann_ret - rf_annual) / downside_vol, 4) if downside_vol != 0 else 0
        data["Calmar_Ratio"] = round(ann_ret / abs(dd_info["最大回撤"]), 4) if dd_info["最大回撤"] != 0 else 0

        # Sterling Ratio
        try:
            data["Sterling_Ratio"] = round((ann_ret - rf_annual) / (abs(dd_info["最大回撤"]) - 0.1), 4)
        except Exception:
            data["Sterling_Ratio"] = "N/A"

        # Omega Ratio
        try:
            threshold = rf_daily
            gains = ret[ret > threshold] - threshold
            losses = threshold - ret[ret <= threshold]
            data["Omega_Ratio"] = round(float(gains.sum() / losses.sum()), 4) if losses.sum() != 0 else "N/A"
        except Exception:
            data["Omega_Ratio"] = "N/A"

        # Ulcer Index
        try:
            drawdown_pct = dd_info["drawdown_series"]
            data["Ulcer_Index"] = round(float(np.sqrt((drawdown_pct ** 2).mean())), 6)
        except Exception:
            data["Ulcer_Index"] = "N/A"

        result.data = data
        result.success = True

        # 中文解读
        parts = []
        parts.append(f"年化波动率为 {ann_vol*100:.2f}%，下行波动率为 {downside_vol*100:.2f}%。")
        parts.append(f"最大回撤为 {abs(dd_info['最大回撤'])*100:.2f}%。")
        parts.append(f"历史模拟 VaR(95%) = {data['VaR_95_历史']*100:.2f}%，表示95%概率下日亏损不超过该值。")
        parts.append(f"历史模拟 VaR(99%) = {data['VaR_99_历史']*100:.2f}%。")
        parts.append(f"CVaR(95%) = {data['CVaR_95']*100:.2f}%，即当损失超过VaR时的平均损失。")
        parts.append(f"Sharpe Ratio = {data['Sharpe_Ratio']}，{'风险调整后收益较好' if data['Sharpe_Ratio'] > 1 else '风险调整后收益一般' if data['Sharpe_Ratio'] > 0 else '风险调整后收益为负'}。")
        parts.append(f"Sortino Ratio = {data['Sortino_Ratio']}，仅考虑下行风险的收益风险比。")
        parts.append(f"Calmar Ratio = {data['Calmar_Ratio']}，年化收益与最大回撤之比。")

        if abs(dd_info['最大回撤']) > 0.5:
            parts.append("⚠️ 最大回撤超过50%，历史风险极高。")

        result.interpretation = "\n".join(parts)

    except Exception as e:
        result.error = f"风险指标分析失败: {str(e)}"
        logger.error(result.error)

    return result