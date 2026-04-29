"""模块5：OLS/CAPM 回归分析"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.utils.logger import get_logger

logger = get_logger("OLS_CAPM")


@dataclass
class OLSResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_ols_capm(stock_returns: pd.Series, index_returns: pd.Series,
                     rf_annual: float = 0.02) -> OLSResult:
    """OLS CAPM 回归分析

    模型: R_i - R_f = alpha + beta * (R_m - R_f) + epsilon

    Args:
        stock_returns: 股票日收益率
        index_returns: 基准指数日收益率
        rf_annual: 年化无风险利率
    """
    result = OLSResult()
    try:
        sr = stock_returns.dropna()
        br = index_returns.dropna()

        # 对齐
        idx = sr.index.intersection(br.index)
        sr = sr.loc[idx].reset_index(drop=True)
        br = br.loc[idx].reset_index(drop=True)

        if len(sr) < 30:
            result.error = f"样本量不足: {len(sr)}"
            return result

        td = 252
        rf_daily = (1 + rf_annual) ** (1 / td) - 1

        # 超额收益
        y = sr - rf_daily
        x = br - rf_daily
        x_const = sm.add_constant(x)

        # OLS 回归
        model = sm.OLS(y, x_const).fit()

        alpha = float(model.params.iloc[0])
        beta = float(model.params.iloc[1])
        alpha_ann = float(alpha * td)

        # 模型诊断
        dw = float(sm.stats.stattools.durbin_watson(model.resid))
        omni_stat, omni_p = sm.stats.omni_normtest(model.resid)
        jb_stat, jb_p, skew, kurt = sm.stats.jarque_bera(model.resid)

        data = {
            "alpha": round(alpha, 8),
            "beta": round(beta, 4),
            "alpha_年化": round(alpha_ann, 6),
            "alpha_p值": round(float(model.pvalues.iloc[0]), 6),
            "beta_p值": round(float(model.pvalues.iloc[1]), 6),
            "alpha_t统计量": round(float(model.tvalues.iloc[0]), 4),
            "beta_t统计量": round(float(model.tvalues.iloc[1]), 4),
            "R_squared": round(float(model.rsquared), 4),
            "Adj_R_squared": round(float(model.rsquared_adj), 4),
            "F_statistic": round(float(model.fvalue), 4),
            "Prob_F": round(float(model.f_pvalue), 6),
            "AIC": round(float(model.aic), 4),
            "BIC": round(float(model.bic), 4),
            "Durbin_Watson": round(dw, 4),
            "Omnibus_stat": round(float(omni_stat), 4),
            "Omnibus_p值": round(float(omni_p), 6),
            "Jarque_Bera_stat": round(float(jb_stat), 4),
            "Jarque_Bera_p值": round(float(jb_p), 6),
            "残差偏度": round(float(skew), 4),
            "残差峰度": round(float(kurt), 4),
            "残差均值": round(float(model.resid.mean()), 8),
            "残差标准差": round(float(model.resid.std()), 6),
            "样本量": len(sr),
        }

        # 保存残差
        result.data = data
        result.success = True

        # 中文解读
        parts = []
        parts.append("CAPM 模型: R_i - R_f = α + β × (R_m - R_f) + ε")
        parts.append(f"Beta = {beta:.4f}，{'系统性风险高于市场' if beta > 1 else '系统性风险低于市场' if beta < 1 else '与市场一致'}。")
        if beta < 0:
            parts.append("⚠️ Beta 为负，说明该股票与市场走势方向相反，属于防御性或特殊品种。")

        alpha_sig = data["alpha_p值"] < 0.05
        parts.append(f"Alpha = {alpha:.6f}（年化 {alpha_ann*100:.4f}%），{'统计显著' if alpha_sig else '不显著'}（p={data['alpha_p值']:.4f}）。")

        if alpha_sig and alpha_ann > 0:
            parts.append("该股票具有统计显著的正向超额收益能力（Alpha）。")
        elif alpha_sig and alpha_ann < 0:
            parts.append("该股票存在统计显著的负向 Alpha，表现不及预期。")
        else:
            parts.append("Alpha 不显著，无法确定是否存在超额收益能力。")

        parts.append(f"R² = {data['R_squared']:.4f}，{'市场因素解释了大部分收益波动' if data['R_squared'] > 0.5 else '市场因素解释力有限' if data['R_squared'] < 0.3 else '市场因素解释力中等'}。")
        parts.append(f"F检验 p值 = {data['Prob_F']:.6f}，模型整体{'显著' if data['Prob_F'] < 0.05 else '不显著'}。")

        if dw < 1.5 or dw > 2.5:
            parts.append(f"⚠️ Durbin-Watson = {dw:.3f}，残差可能存在自相关。")
        else:
            parts.append(f"Durbin-Watson = {dw:.3f}，残差无明显自相关。")

        if jb_p < 0.05:
            parts.append("残差不服从正态分布（JB检验拒绝），标准误可能不准确。")

        result.interpretation = "\n".join(parts)

    except Exception as e:
        result.error = f"OLS/CAPM 分析失败: {str(e)}"
        logger.error(result.error)

    return result