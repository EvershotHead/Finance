"""Generate interpretation text for screener results."""

import pandas as pd

from src.utils.formatting import fmt_pct, fmt_number


def generate_summary(candidates: pd.DataFrame, total_before: int) -> str:
    """Generate a summary interpretation of the screening results."""
    n = len(candidates)
    pass_rate = n / total_before * 100 if total_before > 0 else 0

    lines = [
        f"本次筛选从 {total_before} 只股票中筛选出 {n} 只候选股票，通过率 {pass_rate:.1f}%。",
    ]

    # Score stats
    if "total_score" in candidates.columns:
        scores = candidates["total_score"].dropna()
        if len(scores) > 0:
            lines.append(f"综合评分均值 {scores.mean():.1f} 分，中位数 {scores.median():.1f} 分。")

    # Industry concentration
    if "industry" in candidates.columns:
        top_industry = candidates["industry"].value_counts().head(3)
        if len(top_industry) > 0:
            ind_str = "、".join([f"{ind}({cnt}只)" for ind, cnt in top_industry.items()])
            lines.append(f"行业集中度较高的有: {ind_str}。")

    # Risk profile
    if "volatility_120d" in candidates.columns:
        vol = candidates["volatility_120d"].dropna()
        if len(vol) > 0:
            lines.append(f"120日波动率均值 {vol.mean()*100:.1f}%。")

    return "\n".join(lines)


__all__ = ["generate_summary"]
