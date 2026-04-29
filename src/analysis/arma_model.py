"""模块8：ARMA 模型"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA

from src.utils.logger import get_logger

logger = get_logger("ARMA")


@dataclass
class ARMAResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_arma(returns: pd.Series, max_p: int = 3, max_q: int = 3,
                 forecast_days: int = 5) -> ARMAResult:
    """ARMA 模型分析

    自动搜索最优 (p, q) 组合
    """
    result = ARMAResult()
    try:
        rc = returns.dropna()
        if len(rc) < 100:
            result.error = f"样本量不足: {len(rc)}，ARMA建议至少100个观测值"
            return result

        best_aic = np.inf
        best_bic = np.inf
        best_order = (0, 0)
        best_model = None
        all_results = []

        for p in range(max_p + 1):
            for q in range(max_q + 1):
                if p == 0 and q == 0:
                    continue
                try:
                    model = ARIMA(rc, order=(p, 0, q)).fit()
                    all_results.append({
                        "p": p, "q": q,
                        "AIC": round(float(model.aic), 2),
                        "BIC": round(float(model.bic), 2),
                    })
                    if model.aic < best_aic:
                        best_aic = model.aic
                        best_bic = model.bic
                        best_order = (p, q)
                        best_model = model
                except Exception:
                    continue

        if best_model is None:
            result.error = "所有ARMA模型拟合失败"
            return result

        data = {
            "best_order": {"p": best_order[0], "q": best_order[1]},
            "AIC": round(float(best_model.aic), 4),
            "BIC": round(float(best_model.bic), 4),
            "parameters": {},
            "p_values": {},
            "model_comparison": all_results[:10],  # 前10个
        }

        for name, val in best_model.params.items():
            data["parameters"][name] = round(float(val), 6)
        for name, val in best_model.pvalues.items():
            data["p_values"][name] = round(float(val), 6)

        # 残差诊断
        resid = best_model.resid
        data["残差均值"] = round(float(resid.mean()), 6)
        data["残差标准差"] = round(float(resid.std()), 6)

        from scipy.stats import jarque_bera
        jb_stat, jb_p = jarque_bera(resid)
        data["残差JB_p值"] = round(float(jb_p), 6)

        # 预测
        try:
            forecast = best_model.forecast(steps=forecast_days)
            data["forecast"] = [round(float(v), 6) for v in forecast]
        except Exception:
            data["forecast"] = []

        result.data = data
        result.success = True

        parts = []
        parts.append(f"最优模型: ARMA({best_order[0]}, {best_order[1]})")
        parts.append(f"AIC = {data['AIC']:.2f}，BIC = {data['BIC']:.2f}")
        if data["forecast"]:
            parts.append(f"未来{forecast_days}日收益率预测: {[f'{v*100:.4f}%' for v in data['forecast']]}")
        parts.append("⚠️ 收益率预测的可解释性和可靠性通常较弱，仅作参考，不构成投资建议。")

        result.interpretation = "\n".join(parts)

    except Exception as e:
        result.error = f"ARMA分析失败: {str(e)}"
        logger.error(result.error)

    return result