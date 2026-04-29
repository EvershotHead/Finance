"""模块6：多因子模型"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.utils.logger import get_logger

logger = get_logger("FactorModels")


@dataclass
class FactorResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_factor_model(stock_df: pd.DataFrame, index_df: pd.DataFrame = None,
                         rf_annual: float = 0.02) -> FactorResult:
    """简化多因子模型分析

    使用可从本地计算的因子：
    - 市场因子：基准指数收益率
    - 动量因子：过去20日收益率
    - 波动率因子：20日滚动波动率
    - 流动性因子：换手率或成交额变化率
    """
    result = FactorResult()
    try:
        sr = stock_df["simple_return"].dropna()
        if len(sr) < 60:
            result.error = f"样本量不足: {len(sr)}"
            return result

        td = 252
        rf_daily = (1 + rf_annual) ** (1 / td) - 1
        y = sr - rf_daily

        # 构建因子
        factors = pd.DataFrame(index=sr.index)

        # 市场因子
        if index_df is not None and "index_simple_return" in index_df.columns:
            br = index_df["index_simple_return"].reindex(sr.index).fillna(0)
            factors["MKT"] = br - rf_daily

        # 动量因子
        factors["MOM"] = sr.rolling(20).sum().fillna(0)

        # 波动率因子
        factors["VOL"] = sr.rolling(20).std().fillna(0)

        # 流动性因子（成交量变化率）
        if "volume" in stock_df.columns:
            vol = stock_df["volume"].astype(float)
            factors["LIQ"] = vol.pct_change(20).reindex(sr.index).fillna(0)

        # 对齐
        common_idx = y.dropna().index.intersection(factors.dropna().index)
        y_clean = y.loc[common_idx]
        X_clean = factors.loc[common_idx]
        X_const = sm.add_constant(X_clean)

        # OLS 回归
        model = sm.OLS(y_clean, X_const).fit()

        data = {
            "factors": {},
            "R_squared": round(float(model.rsquared), 4),
            "Adj_R_squared": round(float(model.rsquared_adj), 4),
            "AIC": round(float(model.aic), 4),
            "BIC": round(float(model.bic), 4),
            "F_statistic": round(float(model.fvalue), 4),
            "Prob_F": round(float(model.f_pvalue), 6),
            "样本量": len(y_clean),
        }

        for i, name in enumerate(model.params.index):
            data["factors"][name] = {
                "coefficient": round(float(model.params.iloc[i]), 6),
                "p_value": round(float(model.pvalues.iloc[i]), 6),
                "t_value": round(float(model.tvalues.iloc[i]), 4),
            }

        # 因子相关性
        corr = X_clean.corr()
        data["factor_correlation"] = {
            f"{r}_{c}": round(float(corr.loc[r, c]), 4)
            for r in corr.index for c in corr.columns
        }

        result.data = data
        result.success = True

        # 中文解读
        parts = []
        parts.append(f"多因子模型: 超额收益 = α + Σβᵢ×因子ᵢ + ε")
        parts.append(f"R² = {data['R_squared']:.4f}，Adj-R² = {data['Adj_R_squared']:.4f}")
        parts.append(f"F检验 p值 = {data['Prob_F']:.6f}，模型整体{'显著' if data['Prob_F'] < 0.05 else '不显著'}。")

        for name, info in data["factors"].items():
            if name == "const":
                continue
            sig = "显著" if info["p_value"] < 0.05 else "不显著"
            parts.append(f"  {name}: 系数={info['coefficient']:.6f}, t={info['t_value']:.4f}, p={info['p_value']:.4f} ({sig})")

        result.interpretation = "\n".join(parts)

    except Exception as e:
        result.error = f"多因子模型分析失败: {str(e)}"
        logger.error(result.error)

    return result