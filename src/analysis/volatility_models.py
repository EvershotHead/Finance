"""模块9：GARCH 波动率模型"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from src.utils.logger import get_logger
from src.utils.exceptions import ModelConvergenceError

logger = get_logger("GARCH")


@dataclass
class GARCHResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_garch(returns: pd.Series, model_type: str = "GARCH",
                  p: int = 1, q: int = 1, dist: str = "t") -> GARCHResult:
    """GARCH 波动率建模

    Args:
        returns: 日收益率序列
        model_type: GARCH / EGARCH / GJR-GARCH
        p, q: 模型阶数
        dist: 分布假设 normal / t
    """
    result = GARCHResult()
    try:
        try:
            from arch import arch_model
        except ImportError:
            result.error = "arch 包未安装，请运行: pip install arch"
            return result

        rc = returns.dropna()
        if len(rc) < 100:
            result.error = f"样本量不足: {len(rc)}，GARCH 建议至少100个观测值"
            return result

        # 收益率乘以100（百分比）
        y = rc * 100

        # 选择模型
        vol_model = model_type.upper().replace("-", "").replace("_", "")
        if vol_model == "GJRGARCH":
            vol_model = "GARCH"

        am = arch_model(y, vol=vol_model if vol_model in ("GARCH", "EGARCH") else "GARCH",
                        p=p, o=1 if "GJR" in model_type.upper() or "EGARCH" in model_type.upper() else 0,
                        q=q, dist=dist)

        # EGARCH 特殊处理
        if "EGARCH" in model_type.upper():
            am = arch_model(y, vol="EGARCH", p=p, o=0, q=q, dist=dist)
        elif "GJR" in model_type.upper():
            am = arch_model(y, vol="GARCH", p=p, o=1, q=q, dist=dist)

        fitted = am.fit(disp="off", show_warning=False)

        # 参数
        params = fitted.params
        data = {
            "model_type": model_type,
            "distribution": dist,
            "log_likelihood": round(float(fitted.loglikelihood), 4),
            "AIC": round(float(fitted.aic), 4),
            "BIC": round(float(fitted.bic), 4),
            "parameters": {},
            "p_values": {},
        }

        for name, val in params.items():
            data["parameters"][name] = round(float(val), 6)
        for name, val in fitted.pvalues.items():
            data["p_values"][name] = round(float(val), 6)

        # 波动持续性
        alpha = float(params.get("alpha[1]", 0))
        beta = float(params.get("beta[1]", 0))
        gamma = float(params.get("gamma[1]", 0)) if "gamma[1]" in params.index else 0
        omega = float(params.get("omega", 0))

        data["alpha"] = round(alpha, 6)
        data["beta"] = round(beta, 6)
        data["gamma"] = round(gamma, 6)
        data["omega"] = round(omega, 6)
        data["alpha_plus_beta"] = round(alpha + beta, 6)

        # 半衰期
        if alpha + beta < 1 and alpha + beta > 0:
            half_life = np.log(0.5) / np.log(alpha + beta)
            data["half_life"] = round(float(half_life), 2)
        else:
            data["half_life"] = "N/A（持续性≥1）"

        # 条件波动率
        cond_vol = fitted.conditional_volatility / 100  # 转回小数
        data["conditional_volatility_mean"] = round(float(cond_vol.mean()), 6)
        data["conditional_volatility_std"] = round(float(cond_vol.std()), 6)

        # 预测
        try:
            forecast = fitted.forecast(horizon=20)
            # 获取最后一行的条件方差预测
            forecast_var = forecast.variance.iloc[-1] / 10000  # 转回小数
            forecast_vol = np.sqrt(forecast_var)
            data["forecast_vol_5d"] = round(float(forecast_vol.iloc[:5].mean()), 6)
            data["forecast_vol_20d"] = round(float(forecast_vol.mean()), 6)
        except Exception as e:
            data["forecast_vol_5d"] = "预测失败"
            data["forecast_vol_20d"] = "预测失败"
            result.warnings.append(f"波动率预测失败: {str(e)}")

        result.data = data
        result.success = True

        # 中文解读
        parts = []
        parts.append(f"使用 {model_type}({p},{q}) 模型，分布假设: {dist}。")
        parts.append(f"Alpha(短期冲击) = {alpha:.6f}，Beta(持续性) = {beta:.6f}。")
        parts.append(f"Alpha + Beta = {alpha + beta:.4f}，{'波动持续性很高' if alpha + beta > 0.95 else '波动持续性中等' if alpha + beta > 0.8 else '波动持续性较低'}。")

        if isinstance(data["half_life"], float):
            parts.append(f"半衰期 = {data['half_life']:.1f} 个交易日，即冲击衰减一半需要 {data['half_life']:.0f} 天。")

        if "EGARCH" in model_type.upper() or "GJR" in model_type.upper():
            if gamma != 0:
                parts.append(f"Gamma = {gamma:.6f}，{'存在杠杆效应/非对称波动（负面冲击比正面冲击影响更大）' if gamma > 0 else '非对称效应不明显'}。")

        parts.append(f"AIC = {data['AIC']:.2f}，BIC = {data['BIC']:.2f}。")

    except Exception as e:
        result.error = f"GARCH 建模失败: {str(e)}"
        logger.error(result.error)
        result.warnings.append("GARCH 模型未收敛或报错，建议使用滚动波动率作为替代。")

    return result