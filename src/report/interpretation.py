"""中文解读文本生成模块 - 为各分析模块生成通俗易懂的中文解读"""

from typing import Any


def _safe_get(obj, field, default=None):
    """安全获取对象属性或字典值（兼容 dataclass 和 dict）"""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


def generate_conclusion_summary(all_results: dict) -> dict:
    """基于所有分析结果生成核心结论摘要

    Args:
        all_results: 所有分析模块的结果字典

    Returns:
        包含 summary, strengths, risks, limitations 的字典
    """
    summary = []
    strengths = []
    risks = []
    limitations = []

    # 行情表现
    perf = all_results.get("performance")
    if _safe_get(perf, "success"):
        d = _safe_get(perf, "data", {})
        ann_ret = d.get("区间年化收益率", 0) or 0
        ann_vol = d.get("区间年化波动率", 0) or 0
        max_dd = abs(d.get("最大回撤", 0) or 0)
        summary.append(f"区间年化收益率 {ann_ret*100:.2f}%，年化波动率 {ann_vol*100:.2f}%，最大回撤 {max_dd*100:.2f}%。")
        if ann_ret > 0.1:
            strengths.append("年化收益表现较好")
        if ann_vol > 0.4:
            risks.append("年化波动率较高，价格波动剧烈")
        if max_dd > 0.5:
            risks.append(f"最大回撤达 {max_dd*100:.1f}%，历史风险极高")

    # 风险指标
    risk = all_results.get("risk_metrics")
    if _safe_get(risk, "success"):
        d = _safe_get(risk, "data", {})
        sharpe = d.get("Sharpe_Ratio", 0) or 0
        summary.append(f"Sharpe Ratio = {sharpe:.3f}。")
        if sharpe > 1:
            strengths.append("风险调整后收益较好（Sharpe>1）")
        elif sharpe < 0:
            risks.append("风险调整后收益为负")

    # 基准比较
    bench = all_results.get("benchmark_comparison")
    if _safe_get(bench, "success"):
        d = _safe_get(bench, "data", {})
        beta = d.get("Beta", 1) or 1
        alpha_ann = d.get("Alpha_年化", 0) or 0
        summary.append(f"Beta = {beta:.3f}，年化Alpha = {alpha_ann*100:.4f}%。")
        if alpha_ann > 0.02:
            strengths.append("存在正向超额收益能力")
        if beta > 1.5:
            risks.append("Beta较高，系统性风险大于市场")

    # 技术面
    tech = all_results.get("technical_indicators")
    if _safe_get(tech, "success"):
        d = _safe_get(tech, "data", {})
        macd_state = d.get("MACD状态", "")
        rsi14 = d.get("RSI14_状态", "")
        summary.append(f"技术面：MACD {macd_state}，RSI(14) {rsi14}。")

    # 基本面
    fund = all_results.get("fundamental")
    if _safe_get(fund, "success"):
        d = _safe_get(fund, "data", {})
        if "pe_ttm_最新" in d:
            summary.append(f"PE(TTM) = {d['pe_ttm_最新']:.2f}。")
    else:
        limitations.append("基本面数据不完整")

    # 数据完整性
    warnings = all_results.get("warnings", [])
    if warnings:
        limitations.append(f"数据获取过程中有 {len(warnings)} 项警告")

    limitations.append("本报告基于历史数据分析，不构成投资建议，历史表现不代表未来。")

    return {
        "summary": summary,
        "strengths": strengths,
        "risks": risks,
        "limitations": limitations,
    }