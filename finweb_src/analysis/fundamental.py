"""模块12：基本面分析"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from finweb_src.utils.logger import get_logger

logger = get_logger("Fundamental")


@dataclass
class FundamentalResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_fundamental(fundamental_df: pd.DataFrame = None,
                        financial_df: pd.DataFrame = None) -> FundamentalResult:
    """基本面分析

    Args:
        fundamental_df: 基本面指标数据（PE/PB/PS/市值等）
        financial_df: 财务指标数据（ROE/ROA/毛利率等）
    """
    result = FundamentalResult()
    try:
        data = {}
        warnings = []

        if fundamental_df is not None and not fundamental_df.empty:
            fd = fundamental_df.copy()

            # 估值指标
            for col in ["pe_ttm", "pe", "pb", "ps_ttm", "ps"]:
                if col in fd.columns:
                    vals = fd[col].astype(float).dropna()
                    if not vals.empty:
                        data[f"{col}_最新"] = round(float(vals.iloc[-1]), 4)
                        data[f"{col}_均值"] = round(float(vals.mean()), 4)
                        data[f"{col}_分位数"] = round(float((vals < vals.iloc[-1]).mean()), 4)

            # 市值
            for col in ["total_mv", "circ_mv"]:
                if col in fd.columns:
                    vals = fd[col].astype(float).dropna()
                    if not vals.empty:
                        data[f"{col}_最新"] = round(float(vals.iloc[-1]), 2)

            # 股息率
            for col in ["dv_ratio", "dv_ttm"]:
                if col in fd.columns:
                    vals = fd[col].astype(float).dropna()
                    if not vals.empty:
                        data[f"{col}_最新"] = round(float(vals.iloc[-1]), 4)

            # 换手率
            if "turnover_rate" in fd.columns:
                tr = fd["turnover_rate"].astype(float).dropna()
                if not tr.empty:
                    data["换手率_均值"] = round(float(tr.mean()), 4)
                    data["换手率_最新"] = round(float(tr.iloc[-1]), 4)
        else:
            warnings.append("基本面指标数据不可用")

        if financial_df is not None and not financial_df.empty:
            fin = financial_df.copy()

            for col in ["roe", "roa", "gross_margin", "net_margin", "debt_ratio",
                        "revenue_yoy", "net_profit_yoy", "eps", "bps"]:
                if col in fin.columns:
                    vals = fin[col].astype(float).dropna()
                    if not vals.empty:
                        data[f"财务_{col}_最新"] = round(float(vals.iloc[-1]), 4)
                        if len(vals) > 1:
                            data[f"财务_{col}_趋势"] = "上升" if vals.iloc[-1] > vals.iloc[-2] else "下降"
        else:
            warnings.append("财务指标数据不可用")

        result.data = data
        result.warnings = warnings
        result.success = len(data) > 0

        parts = []
        if "pe_ttm_最新" in data:
            pe = data["pe_ttm_最新"]
            q = data["pe_ttm_分位数"]
            parts.append(f"PE(TTM) = {pe:.2f}，历史分位数 {q*100:.1f}%，{'估值偏高' if q > 0.7 else '估值偏低' if q < 0.3 else '估值适中'}。")
        if "pb_最新" in data:
            pb = data["pb_最新"]
            parts.append(f"PB = {pb:.2f}。")
        if "财务_roe_最新" in data:
            parts.append(f"ROE = {data['财务_roe_最新']:.2f}%")
        if "财务_roa_最新" in data:
            parts.append(f"ROA = {data['财务_roa_最新']:.2f}%")
        if warnings:
            parts.append(f"⚠️ {'；'.join(warnings)}，基本面分析部分仅供参考。")
        if not parts:
            parts.append("由于当前数据源未能获取完整财务数据，基本面分析部分仅供参考。")

        result.interpretation = "\n".join(parts)

    except Exception as e:
        result.error = f"基本面分析失败: {str(e)}"
        logger.error(result.error)

    return result