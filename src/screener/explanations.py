"""Generate human-readable reasons and risk explanations for each stock."""

import pandas as pd
import numpy as np

from src.utils.formatting import fmt_pct, fmt_pct_raw, fmt_yi, fmt_number


def generate_reasons(row: pd.Series, config: dict = None) -> list[str]:
    """Generate reasons why a stock was selected (at least 3).

    Args:
        row: Feature row for the stock
        config: Filter configuration used

    Returns:
        List of reason strings
    """
    reasons = []

    # Return reasons
    ret_20d = row.get("ret_20d")
    if ret_20d is not None and not pd.isna(ret_20d):
        if ret_20d > 0.05:
            reasons.append(f"近20日收益率{fmt_pct(ret_20d)}，短期表现较强。")
        elif ret_20d > 0:
            reasons.append(f"近20日收益率{fmt_pct(ret_20d)}，近期走势偏正。")

    ret_120d = row.get("ret_120d")
    if ret_120d is not None and not pd.isna(ret_120d) and ret_120d > 0:
        reasons.append(f"近120日收益率{fmt_pct(ret_120d)}，中长期趋势较好。")

    # Risk reasons
    vol = row.get("volatility_120d")
    if vol is not None and not pd.isna(vol):
        total_score = row.get("total_score", 50)
        if vol < 0.3:
            reasons.append(f"120日波动率{fmt_pct(vol)}，风险水平相对较低。")

    # Liquidity reasons
    avg_amt = row.get("avg_amount_20d")
    if avg_amt is not None and not pd.isna(avg_amt):
        if avg_amt >= 1e8:
            reasons.append(f"近20日平均成交额{fmt_yi(avg_amt)}，流动性充裕。")
        elif avg_amt >= 5e7:
            reasons.append(f"近20日平均成交额{fmt_yi(avg_amt)}，流动性尚可。")

    # Valuation reasons
    pe_ttm = row.get("pe_ttm")
    if pe_ttm is not None and not pd.isna(pe_ttm) and 0 < pe_ttm <= 30:
        reasons.append(f"PE(TTM)为{fmt_number(pe_ttm)}，估值处于合理区间。")

    pb = row.get("pb")
    if pb is not None and not pd.isna(pb) and 0 < pb <= 3:
        reasons.append(f"PB为{fmt_number(pb)}，估值相对不高。")

    # Quality reasons
    roe = row.get("roe")
    if roe is not None and not pd.isna(roe) and roe > 10:
        reasons.append(f"ROE为{fmt_pct_raw(roe)}，盈利能力较好。")

    # Technical reasons
    if row.get("is_ma_bullish", False):
        reasons.append("均线呈多头排列，技术趋势向好。")

    rsi = row.get("rsi_14")
    if rsi is not None and not pd.isna(rsi) and 40 <= rsi <= 60:
        reasons.append(f"RSI(14)为{fmt_number(rsi)}，处于中性区间。")

    # Growth reasons
    rev_growth = row.get("revenue_growth_yoy")
    if rev_growth is not None and not pd.isna(rev_growth) and rev_growth > 10:
        reasons.append(f"营收同比增长{fmt_pct_raw(rev_growth)}，成长性较好。")

    # Score reasons
    total_score = row.get("total_score")
    if total_score is not None and not pd.isna(total_score) and total_score >= 70:
        reasons.append(f"综合评分{fmt_number(total_score)}分，整体表现较好。")

    # Ensure at least 3 reasons
    if len(reasons) < 3:
        if total_score is not None and not pd.isna(total_score):
            reasons.append(f"综合评分{fmt_number(total_score)}分，符合筛选条件。")
        reasons.append("满足预设筛选模板的各项条件。")

    return reasons[:6]  # Cap at 6


def generate_risks(row: pd.Series) -> list[str]:
    """Generate risk warnings for a stock.

    Args:
        row: Feature row for the stock

    Returns:
        List of risk strings
    """
    risks = []

    # ST risk
    if row.get("is_st", 0):
        risks.append("该股票为ST股票，存在退市风险。")

    # High drawdown
    mdd = row.get("max_drawdown_120d")
    if mdd is not None and not pd.isna(mdd) and mdd < -0.2:
        risks.append(f"近120日最大回撤{fmt_pct(mdd)}，下行风险较大。")

    # High volatility
    vol = row.get("volatility_120d")
    if vol is not None and not pd.isna(vol) and vol > 0.5:
        risks.append(f"120日波动率{fmt_pct(vol)}，价格波动较大。")

    # Negative PE
    pe = row.get("pe_ttm")
    if pe is not None and not pd.isna(pe) and pe < 0:
        risks.append("PE为负值，公司可能处于亏损状态。")
    elif pe is not None and not pd.isna(pe) and pe > 100:
        risks.append(f"PE(TTM)为{fmt_number(pe)}，估值极高。")

    # Low liquidity
    avg_amt = row.get("avg_amount_20d")
    if avg_amt is not None and not pd.isna(avg_amt) and avg_amt < 2e7:
        risks.append("成交额偏低，可能存在流动性风险。")

    # Short listing
    listing_days = row.get("listing_days", 999)
    if listing_days is not None and not pd.isna(listing_days) and listing_days < 180:
        risks.append("上市时间较短，历史数据样本不足。")

    # High beta
    b = row.get("beta_120d")
    if b is not None and not pd.isna(b) and b > 1.5:
        risks.append(f"Beta为{fmt_number(b)}，系统性风险暴露较高。")

    # Data quality
    dq = row.get("data_quality_score")
    if dq is not None and not pd.isna(dq) and dq < 70:
        risks.append("数据质量评分较低，部分指标可信度下降。")

    # Recent surge
    ret_5d = row.get("ret_5d")
    if ret_5d is not None and not pd.isna(ret_5d) and ret_5d > 0.15:
        risks.append(f"近5日涨幅{fmt_pct(ret_5d)}，短期涨幅较大，可能存在回调风险。")

    # High debt
    debt = row.get("debt_to_asset")
    if debt is not None and not pd.isna(debt) and debt > 70:
        risks.append(f"资产负债率{fmt_pct_raw(debt)}，财务杠杆较高。")

    # Ensure at least 1 risk
    if not risks:
        risks.append("请关注市场整体风险和个股基本面变化。")

    return risks[:5]  # Cap at 5


__all__ = ["generate_reasons", "generate_risks"]
