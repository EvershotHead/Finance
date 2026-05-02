"""模块2：收益率分布分析"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from finweb_src.utils.logger import get_logger

logger = get_logger("ReturnDist")


@dataclass
class DistributionResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_return_distribution(returns: pd.Series) -> DistributionResult:
    """分析收益率分布特征

    Args:
        returns: 日收益率序列（simple_return）
    """
    result = DistributionResult()
    try:
        rc = returns.dropna()
        if len(rc) < 30:
            result.error = f"样本量不足: {len(rc)}条，需要至少30条"
            return result

        n = len(rc)
        mean = float(rc.mean())
        median = float(rc.median())
        std = float(rc.std())
        skew = float(rc.skew())
        kurt = float(rc.kurtosis())  # excess kurtosis

        # 分位数
        quantiles = {}
        for q in [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]:
            quantiles[f"{q*100:.0f}%"] = round(float(rc.quantile(q)), 6)

        # 正态性检验
        jb_stat, jb_p = stats.jarque_bera(rc)

        sw_stat, sw_p = None, None
        if n <= 5000:
            try:
                sw_stat, sw_p = stats.shapiro(rc)
            except Exception:
                pass

        # 极端值统计
        mean_r = rc.mean()
        std_r = rc.std()
        extreme_2s = int(((rc > mean_r + 2*std_r) | (rc < mean_r - 2*std_r)).sum())
        extreme_3s = int(((rc > mean_r + 3*std_r) | (rc < mean_r - 3*std_r)).sum())

        data = {
            "样本量": n,
            "均值": round(mean, 6),
            "中位数": round(median, 6),
            "标准差": round(std, 6),
            "偏度": round(skew, 4),
            "峰度(超额)": round(kurt, 4),
            "Jarque-Bera统计量": round(float(jb_stat), 4),
            "Jarque-Bera p值": round(float(jb_p), 6),
            "分位数": quantiles,
            "超过±2σ天数": extreme_2s,
            "超过±3σ天数": extreme_3s,
        }

        if sw_stat is not None:
            data["Shapiro-Wilk统计量"] = round(float(sw_stat), 4)
            data["Shapiro-Wilk p值"] = round(float(sw_p), 6)

        result.data = data
        result.success = True

        # 中文解读
        parts = []
        parts.append(f"共 {n} 个交易日的收益率数据。")
        parts.append(f"日均收益率为 {mean*100:.4f}%，中位数为 {median*100:.4f}%。")
        parts.append(f"偏度为 {skew:.4f}，{'左偏（负偏）' if skew < -0.5 else '右偏（正偏）' if skew > 0.5 else '接近对称'}。")
        parts.append(f"超额峰度为 {kurt:.4f}，{'存在尖峰厚尾特征' if kurt > 1 else '峰度接近正态' if abs(kurt) < 1 else '存在平峰特征'}。")

        if jb_p < 0.05:
            parts.append(f"Jarque-Bera 检验 p值={jb_p:.4f} < 0.05，拒绝正态分布假设，收益率分布显著偏离正态。")
        else:
            parts.append(f"Jarque-Bera 检验 p值={jb_p:.4f} >= 0.05，不能拒绝正态分布假设。")

        if sw_p is not None:
            if sw_p < 0.05:
                parts.append(f"Shapiro-Wilk 检验 p值={sw_p:.4f} < 0.05，同样拒绝正态性。")
            else:
                parts.append(f"Shapiro-Wilk 检验 p值={sw_p:.4f} >= 0.05，不能拒绝正态性。")

        if kurt > 3:
            parts.append("⚠️ 厚尾特征明显，极端收益率出现概率高于正态分布预期，VaR等风险指标可能低估尾部风险。")

        if extreme_3s > 0:
            parts.append(f"共有 {extreme_3s} 个交易日的收益率超过均值±3倍标准差，需要关注极端波动风险。")

        result.interpretation = "\n".join(parts)

    except Exception as e:
        result.error = f"收益率分布分析失败: {str(e)}"
        logger.error(result.error)

    return result