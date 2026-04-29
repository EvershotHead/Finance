"""模块15：综合评分"""

from dataclasses import dataclass, field
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger("Scoring")


@dataclass
class ScoreResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def _score_return(perf: dict) -> float:
    """收益表现评分 (满分20)"""
    score = 0
    ann_ret = perf.get("区间年化收益率", 0)
    if ann_ret > 0.15: score += 10
    elif ann_ret > 0.05: score += 7
    elif ann_ret > 0: score += 4
    else: score += 1
    win_rate = perf.get("胜率", 0)
    if win_rate > 0.55: score += 5
    elif win_rate > 0.50: score += 3
    else: score += 1
    cum = perf.get("区间累计收益率", 0)
    if cum > 0.3: score += 5
    elif cum > 0: score += 3
    else: score += 1
    return min(score, 20)


def _score_risk(risk: dict) -> float:
    """风险控制评分 (满分20)"""
    score = 0
    max_dd = abs(risk.get("最大回撤", -1))
    if max_dd < 0.15: score += 8
    elif max_dd < 0.30: score += 5
    elif max_dd < 0.50: score += 3
    else: score += 1
    sharpe = risk.get("Sharpe_Ratio", 0)
    if sharpe > 1.5: score += 7
    elif sharpe > 0.5: score += 5
    elif sharpe > 0: score += 3
    else: score += 1
    sortino = risk.get("Sortino_Ratio", 0)
    if sortino > 1.5: score += 5
    elif sortino > 0.5: score += 3
    else: score += 1
    return min(score, 20)


def _score_benchmark(bench: dict) -> float:
    """基准比较评分 (满分15)"""
    score = 0
    excess = bench.get("年化超额收益", 0)
    if excess > 0.05: score += 6
    elif excess > 0: score += 4
    else: score += 1
    ir = bench.get("Information_Ratio", 0)
    if ir > 0.5: score += 4
    elif ir > 0: score += 2
    else: score += 1
    up_cap = bench.get("上行捕获率", 1)
    down_cap = bench.get("下行捕获率", 1)
    if up_cap > 1 and down_cap < 1: score += 5
    elif up_cap > 1 or down_cap < 1: score += 3
    else: score += 1
    return min(score, 15)


def _score_liquidity(liq: dict) -> float:
    """流动性评分 (满分10)"""
    score = 5
    if liq.get("近20日成交量分位数", 0.5) > 0.3: score += 3
    if liq.get("量价相关系数", 0) > 0.2: score += 2
    return min(score, 10)


def _score_volatility_stability(perf: dict, risk: dict) -> float:
    """波动率稳定性评分 (满分10)"""
    ann_vol = perf.get("区间年化波动率", 0.3)
    if ann_vol < 0.20: return 10
    elif ann_vol < 0.30: return 7
    elif ann_vol < 0.40: return 5
    return 2


def _score_valuation(fund: dict) -> float:
    """估值水平评分 (满分10)"""
    score = 5
    pe_q = fund.get("pe_ttm_分位数", 0.5)
    if isinstance(pe_q, (int, float)):
        if pe_q < 0.3: score += 3
        elif pe_q < 0.7: score += 1
    pb_q = fund.get("pb_分位数", 0.5)
    if isinstance(pb_q, (int, float)):
        if pb_q < 0.3: score += 2
        elif pb_q < 0.7: score += 1
    return min(score, 10)


def _score_fundamental_quality(fund: dict) -> float:
    """基本面质量评分 (满分10)"""
    score = 3
    roe = fund.get("财务_roe_最新", 0)
    if isinstance(roe, (int, float)):
        if roe > 15: score += 3
        elif roe > 8: score += 2
    debt = fund.get("财务_debt_ratio_最新", 50)
    if isinstance(debt, (int, float)):
        if debt < 50: score += 2
        elif debt < 70: score += 1
    if fund.get("财务_revenue_yoy_趋势") == "上升": score += 2
    return min(score, 10)


def _score_data_completeness(warnings: list) -> float:
    """数据完整性评分 (满分5)"""
    return max(1, 5 - len(warnings))


def calculate_score(perf_data, risk_data, bench_data, liq_data, fund_data, warnings):
    """计算综合评分"""
    scores = {
        "收益表现": _score_return(perf_data),
        "风险控制": _score_risk(risk_data),
        "相对基准": _score_benchmark(bench_data) if bench_data else 0,
        "流动性": _score_liquidity(liq_data) if liq_data else 3,
        "波动率稳定性": _score_volatility_stability(perf_data, risk_data),
        "估值水平": _score_valuation(fund_data) if fund_data else 3,
        "基本面质量": _score_fundamental_quality(fund_data) if fund_data else 3,
        "数据完整性": _score_data_completeness(warnings),
    }
    total = sum(scores.values())

    strengths = []
    risks = []
    for k, v in scores.items():
        max_map = {"收益表现": 20, "风险控制": 20, "相对基准": 15,
                   "流动性": 10, "波动率稳定性": 10, "估值水平": 10,
                   "基本面质量": 10, "数据完整性": 5}
        ratio = v / max_map.get(k, 10)
        if ratio > 0.7: strengths.append(k)
        elif ratio < 0.4: risks.append(k)

    ann_ret = perf_data.get("区间年化收益率", 0)
    ann_vol = perf_data.get("区间年化波动率", 0.3)
    max_dd = abs(risk_data.get("最大回撤", -0.5))
    sharpe = risk_data.get("Sharpe_Ratio", 0)

    if max_dd < 0.2 and ann_vol < 0.25:
        investor = "稳健型投资者"
    elif ann_ret > 0.1 and max_dd < 0.4:
        investor = "平衡型投资者"
    elif ann_ret > 0.15:
        investor = "激进型投资者"
    else:
        investor = "需要进一步评估，建议谨慎投资"

    parts = [f"综合评分: {total}/100"]
    for k, v in scores.items():
        max_map = {"收益表现": 20, "风险控制": 20, "相对基准": 15,
                   "流动性": 10, "波动率稳定性": 10, "估值水平": 10,
                   "基本面质量": 10, "数据完整性": 5}
        parts.append(f"  {k}: {v}/{max_map.get(k, 10)}")
    parts.append(f"适合投资者类型: {investor}")
    parts.append("\n⚠️ 本评分仅为辅助分析工具，不构成投资建议。")

    return {
        "总分": total,
        "各维度得分": scores,
        "优点": strengths,
        "风险点": risks,
        "适合投资者类型": investor,
    }, "\n".join(parts)