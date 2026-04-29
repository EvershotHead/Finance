"""模块7：时间序列检验"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.stattools import acf, pacf

from src.utils.logger import get_logger

logger = get_logger("TSTests")


@dataclass
class TSTestResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_time_series(returns: pd.Series, prices: pd.Series = None) -> TSTestResult:
    """时间序列检验：ADF、KPSS、Ljung-Box、ARCH LM

    Args:
        returns: 日收益率序列
        prices: 价格序列（可选，用于ADF/KPSS对价格的检验）
    """
    result = TSTestResult()
    try:
        rc = returns.dropna()
        if len(rc) < 30:
            result.error = f"样本量不足: {len(rc)}"
            return result

        data = {}

        # ===== ADF 检验 =====
        try:
            adf_stat, adf_p, adf_lags, adf_nobs, adf_crit, _ = adfuller(rc, maxlag=20, autolag="AIC")
            data["ADF_收益率"] = {
                "statistic": round(float(adf_stat), 4),
                "p_value": round(float(adf_p), 6),
                "lags": int(adf_lags),
                "nobs": int(adf_nobs),
                "critical_values": {k: round(float(v), 4) for k, v in adf_crit.items()},
            }
        except Exception as e:
            data["ADF_收益率"] = {"error": str(e)}

        if prices is not None:
            try:
                p_adf_stat, p_adf_p, p_adf_lags, p_adf_nobs, p_adf_crit, _ = adfuller(prices.dropna(), maxlag=20, autolag="AIC")
                data["ADF_价格"] = {
                    "statistic": round(float(p_adf_stat), 4),
                    "p_value": round(float(p_adf_p), 6),
                    "lags": int(p_adf_lags),
                    "nobs": int(p_adf_nobs),
                    "critical_values": {k: round(float(v), 4) for k, v in p_adf_crit.items()},
                }
            except Exception as e:
                data["ADF_价格"] = {"error": str(e)}

        # ===== KPSS 检验 =====
        try:
            kpss_stat, kpss_p, kpss_lags, kpss_crit = kpss(rc, regression="c", nlags="auto")
            data["KPSS_收益率"] = {
                "statistic": round(float(kpss_stat), 4),
                "p_value": round(float(kpss_p), 6),
                "lags": int(kpss_lags),
                "critical_values": {k: round(float(v), 4) for k, v in kpss_crit.items()},
            }
        except Exception as e:
            data["KPSS_收益率"] = {"error": str(e)}

        if prices is not None:
            try:
                p_kpss_stat, p_kpss_p, p_kpss_lags, p_kpss_crit = kpss(prices.dropna(), regression="c", nlags="auto")
                data["KPSS_价格"] = {
                    "statistic": round(float(p_kpss_stat), 4),
                    "p_value": round(float(p_kpss_p), 6),
                    "lags": int(p_kpss_lags),
                    "critical_values": {k: round(float(v), 4) for k, v in p_kpss_crit.items()},
                }
            except Exception as e:
                data["KPSS_价格"] = {"error": str(e)}

        # ===== Ljung-Box 检验 =====
        for lag in [5, 10, 20]:
            if lag >= len(rc) - 1:
                continue
            try:
                lb = acorr_ljungbox(rc, lags=[lag], return_df=True)
                data[f"LjungBox_r_lag{lag}"] = {
                    "statistic": round(float(lb["lb_stat"].iloc[0]), 4),
                    "p_value": round(float(lb["lb_pvalue"].iloc[0]), 6),
                }
            except Exception:
                pass

            # 平方收益率（检验波动聚集）
            try:
                lb2 = acorr_ljungbox(rc ** 2, lags=[lag], return_df=True)
                data[f"LjungBox_r2_lag{lag}"] = {
                    "statistic": round(float(lb2["lb_stat"].iloc[0]), 4),
                    "p_value": round(float(lb2["lb_pvalue"].iloc[0]), 6),
                }
            except Exception:
                pass

        # ===== ARCH LM 检验 =====
        try:
            arch_stat, arch_p, _, _ = het_arch(rc, nlags=5)
            data["ARCH_LM"] = {
                "statistic": round(float(arch_stat), 4),
                "p_value": round(float(arch_p), 6),
            }
        except Exception as e:
            data["ARCH_LM"] = {"error": str(e)}

        # ===== ACF/PACF =====
        try:
            acf_vals = acf(rc, nlags=30, fft=True)
            pacf_vals = pacf(rc, nlags=30)
            data["acf_values"] = acf_vals.tolist()
            data["pacf_values"] = pacf_vals.tolist()
        except Exception:
            data["acf_values"] = []
            data["pacf_values"] = []

        result.data = data
        result.success = True

        # 中文解读
        parts = []

        # ADF 解读
        if "ADF_收益率" in data and "statistic" in data["ADF_收益率"]:
            adf = data["ADF_收益率"]
            if adf["p_value"] < 0.05:
                parts.append(f"收益率序列 ADF 检验拒绝单位根（p={adf['p_value']:.4f}），序列平稳。")
            else:
                parts.append(f"收益率序列 ADF 检验未能拒绝单位根（p={adf['p_value']:.4f}）。")

        if "ADF_价格" in data and "statistic" in data["ADF_价格"]:
            adf_p = data["ADF_价格"]
            if adf_p["p_value"] >= 0.05:
                parts.append(f"价格序列 ADF 未能拒绝单位根（p={adf_p['p_value']:.4f}），价格非平稳，这是预期结果。")

        # KPSS 解读
        if "KPSS_收益率" in data and "statistic" in data["KPSS_收益率"]:
            kpss_d = data["KPSS_收益率"]
            if kpss_d["p_value"] >= 0.05:
                parts.append(f"收益率序列 KPSS 检验不能拒绝平稳假设（p={kpss_d['p_value']:.4f}）。")
            else:
                parts.append(f"收益率序列 KPSS 检验拒绝平稳假设（p={kpss_d['p_value']:.4f}），可能需要进一步检查。")

        # Ljung-Box 解读
        if "LjungBox_r_lag10" in data:
            lb = data["LjungBox_r_lag10"]
            if lb["p_value"] < 0.05:
                parts.append(f"收益率存在自相关（Ljung-Box lag10, p={lb['p_value']:.4f}）。")
            else:
                parts.append(f"收益率无显著自相关（Ljung-Box lag10, p={lb['p_value']:.4f}）。")

        if "LjungBox_r2_lag10" in data:
            lb2 = data["LjungBox_r2_lag10"]
            if lb2["p_value"] < 0.05:
                parts.append(f"平方收益率存在自相关（Ljung-Box lag10, p={lb2['p_value']:.4f}），存在波动聚集现象，适合GARCH建模。")
            else:
                parts.append(f"平方收益率无显著自相关，波动聚集特征不明显。")

        # ARCH LM 解读
        if "ARCH_LM" in data and "statistic" in data["ARCH_LM"]:
            arch = data["ARCH_LM"]
            if arch["p_value"] < 0.05:
                parts.append(f"ARCH LM 检验显著（p={arch['p_value']:.4f}），存在ARCH效应，建议使用GARCH模型。")
            else:
                parts.append(f"ARCH LM 检验不显著（p={arch['p_value']:.4f}），无明显ARCH效应。")

        result.interpretation = "\n".join(parts)

    except Exception as e:
        result.error = f"时间序列检验失败: {str(e)}"
        logger.error(result.error)

    return result