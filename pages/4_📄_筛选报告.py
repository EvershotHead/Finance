"""筛选报告页面 — 查看和导出完整筛选报告."""

import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="筛选报告", page_icon="📄", layout="wide")

st.title("📄 筛选报告")
st.caption("查看和导出筛选结果的完整报告 | 仅供学习和辅助分析，不构成投资建议")

from src.storage import feature_store
from src.screener.screening_engine import ScreeningEngine
from src.screener.explanations import generate_reasons, generate_risks
from src.visualization.screener_charts import (
    plot_industry_distribution, plot_score_distribution, plot_risk_return_scatter,
)
from src.utils.formatting import COLUMN_FORMAT

# Check for results
result = st.session_state.get("screener_results")
config = st.session_state.get("screener_config", {})

if result is None:
    st.info("请先在智能选股页面运行筛选。")
    st.stop()

candidates = result.candidates
if len(candidates) == 0:
    st.warning("筛选结果为空。")
    st.stop()

# ============================================================
# Report Content
# ============================================================

# 1. Basic Info
st.header("1. 筛选任务基本信息")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("筛选前股票数量", f"{result.total_before}")
with col2:
    st.metric("筛选后股票数量", f"{result.total_after}")
with col3:
    if "latest_trade_date" in candidates.columns:
        latest = candidates["latest_trade_date"].dropna().max()
        st.metric("数据日期", str(latest)[:10] if pd.notna(latest) else "未知")

# 2. Screening Conditions
st.header("2. 筛选条件")
if result.stage_results:
    for stage in result.stage_results:
        name = stage.name if hasattr(stage, "name") else stage.get("name", "")
        before = stage.count_before if hasattr(stage, "count_before") else stage.get("count_before", 0)
        after = stage.count_after if hasattr(stage, "count_after") else stage.get("count_after", 0)
        removed = stage.removed if hasattr(stage, "removed") else stage.get("removed", 0)
        st.markdown(f"- **{name}**: {before} → {after} (剔除 {removed})")

# 3. Overview Charts
st.header("3. 筛选结果概览")
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(plot_industry_distribution(candidates), use_container_width=True)
with col2:
    st.plotly_chart(plot_score_distribution(candidates), use_container_width=True)

st.plotly_chart(plot_risk_return_scatter(candidates), use_container_width=True)

# 4. Candidate List
st.header("4. 候选股票列表")
display_cols = [c for c in ["stock_code", "stock_name", "industry", "latest_close",
                            "pe_ttm", "pb", "roe", "ret_20d", "ret_120d",
                            "volatility_120d", "total_score"] if c in candidates.columns]
st.dataframe(candidates[display_cols], use_container_width=True, hide_index=True)

# 5. Detailed Explanations
st.header("5. 重点候选股票解释")
for i, (_, row) in enumerate(candidates.head(10).iterrows(), 1):
    name = row.get("stock_name", "")
    code = row.get("stock_code", "")
    with st.expander(f"{i}. {name} ({code}) — 评分: {row.get('total_score', 0):.1f}", expanded=(i <= 3)):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**入选原因**")
            reasons = row.get("reasons", [])
            if isinstance(reasons, list):
                for r in reasons:
                    st.markdown(f"- {r}")
        with col_b:
            st.markdown("**风险提示**")
            risks = row.get("risks", [])
            if isinstance(risks, list):
                for r in risks:
                    st.warning(r)

# 6. Data Limitations
st.header("6. 数据说明")
st.markdown("""
- 本报告数据来源于 AKShare，可能存在延迟
- 部分财务数据可能缺失，已标注在数据质量评分中
- 资金流数据暂不可用
- 所有收益率均基于前复权价格计算
""")

# 7. Disclaimer
st.header("7. 免责声明")
st.error("""
**免责声明**: 本报告仅供学习和辅助分析使用，不构成任何投资建议。
股票市场存在风险，投资需谨慎。过去的业绩不代表未来表现。
本系统不推荐买入、卖出或持有任何股票。
""")

# ============================================================
# Export
# ============================================================
st.divider()
st.subheader("导出报告")

# Generate markdown report
md_lines = [
    "# A股智能选股筛选报告\n\n",
    f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
    f"**筛选前**: {result.total_before} 只 | **筛选后**: {result.total_after} 只\n\n",
    "## 候选股票\n\n",
    "| 排名 | 代码 | 名称 | 行业 | 收盘价 | PE | 20日收益 | 评分 |\n",
    "|------|------|------|------|--------|-----|----------|------|\n",
]

for i, (_, row) in enumerate(candidates.head(50).iterrows(), 1):
    md_lines.append(
        f"| {i} | {row.get('stock_code', '')} | {row.get('stock_name', '')} | "
        f"{row.get('industry', '')} | {row.get('latest_close', 0):.2f} | "
        f"{row.get('pe_ttm', 0):.2f} | "
        f"{row.get('ret_20d', 0)*100:.2f}% | {row.get('total_score', 0):.1f} |\n"
    )

md_lines.append("\n\n---\n**免责声明**: 本报告仅供学习和辅助分析，不构成投资建议。\n")
md_content = "".join(md_lines)

col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "📥 下载 Markdown 报告",
        md_content,
        file_name=f"screener_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
    )

with col2:
    # HTML version
    html_content = md_content.replace("\n", "<br>")
    html_full = f"<html><body><pre style='font-family: sans-serif;'>{html_content}</pre></body></html>"
    st.download_button(
        "📥 下载 HTML 报告",
        html_full,
        file_name=f"screener_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
        mime="text/html",
    )

# Footer
st.markdown("---")
st.caption("免责声明: 本报告仅供学习和辅助分析，不构成投资建议。投资有风险，入市需谨慎。")
