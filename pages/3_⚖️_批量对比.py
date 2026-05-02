"""批量对比页面 — 选择多只股票进行横向对比."""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="批量对比", page_icon="⚖️", layout="wide")

st.title("⚖️ 批量对比")
st.caption("选择 2-10 只候选股票进行横向对比 | 仅供学习和辅助分析，不构成投资建议")

from src.storage import feature_store
from src.screener.comparison import compare_stocks, build_radar_data, DIMENSIONS
from src.visualization.screener_charts import plot_radar, plot_multi_stock_bar
from src.utils.formatting import COLUMN_FORMAT, get_column_rename_map
from src.utils.export import export_csv
from pathlib import Path
from datetime import datetime

# Load features
features_df = None
if feature_store.is_available():
    features_df = feature_store.load_latest_features()

if features_df is None or len(features_df) == 0:
    st.warning("⚠️ 暂无数据。请先在智能选股页面更新数据。")
    st.stop()

# Stock selection
st.subheader("选择对比股票")

# Check if stocks were selected from screener page
pre_selected = st.session_state.get("selected_for_comparison", [])

# Build options
stock_options = features_df[["stock_code", "stock_name"]].drop_duplicates()
stock_labels = {row["stock_code"]: f"{row['stock_code']} - {row['stock_name']}" for _, row in stock_options.iterrows()}

selected_codes = st.multiselect(
    "选择 2-10 只股票",
    options=list(stock_labels.keys()),
    default=[c for c in pre_selected if c in stock_labels],
    format_func=lambda x: stock_labels.get(x, x),
    max_selections=10,
)

if len(selected_codes) < 2:
    st.info("请至少选择 2 只股票进行对比。")
    st.stop()

# Filter features
selected_df = features_df[features_df["stock_code"].isin(selected_codes)].copy()

# Get column rename map
rename_map = get_column_rename_map()

# ============================================================
# Comparison Tables
# ============================================================
st.divider()
st.subheader("对比表格")

DIMENSION_NAMES = {
    "收益": "📈 收益指标",
    "风险": "📉 风险指标",
    "估值": "💰 估值指标",
    "基本面": "📊 基本面指标",
    "流动性": "🔄 流动性指标",
    "评分": "⭐ 综合评分",
}

for dim_name, fields in DIMENSIONS.items():
    available = [f for f in fields if f in selected_df.columns]
    # Filter out columns that are all NaN
    available = [f for f in available if selected_df[f].notna().any()]
    if not available:
        continue

    display_name = DIMENSION_NAMES.get(dim_name, dim_name)
    with st.expander(display_name, expanded=(dim_name in ["收益", "评分"])):
        display = selected_df[["stock_code", "stock_name"] + available].copy()

        # Rename columns to Chinese
        display = display.rename(columns=rename_map)

        # Format values
        for col in available:
            if col in COLUMN_FORMAT:
                _, fmt_fn, _ = COLUMN_FORMAT[col]
                if fmt_fn:
                    cn_name = rename_map.get(col, col)
                    display[cn_name] = display[cn_name].apply(lambda x: fmt_fn(x) if pd.notna(x) else "-")

        st.dataframe(display.set_index("股票代码"), use_container_width=True)

# ============================================================
# Charts
# ============================================================
st.divider()
st.subheader("可视化对比")

# Radar chart — only include scores that have data
radar_data = build_radar_data(features_df, selected_codes)
if radar_data:
    # Check which score dimensions have data
    score_cols = ["return_score", "risk_score", "liquidity_score",
                  "value_score", "quality_score", "technical_score"]
    has_data = any(
        any(stock.get(c, 0) is not None and stock.get(c, 0) > 0 for stock in radar_data)
        for c in score_cols
    )
    if has_data:
        st.plotly_chart(plot_radar(radar_data), use_container_width=True)
    else:
        st.info("评分数据不足，无法生成雷达图。请先完成数据更新。")

# Bar charts for key metrics
chart_fields = [
    ("ret_20d", "近20日收益率对比"),
    ("ret_120d", "近120日收益率对比"),
    ("volatility_120d", "120日波动率对比"),
    ("pe_ttm", "PE(TTM)对比"),
    ("pb", "PB对比"),
    ("total_mv", "总市值对比"),
    ("roe", "ROE对比"),
    ("total_score", "综合评分对比"),
    ("avg_amount_20d", "20日均成交额对比"),
    ("max_drawdown_120d", "120日最大回撤对比"),
]

cols = st.columns(2)
for i, (field, title) in enumerate(chart_fields):
    if field in features_df.columns and features_df[field].notna().any():
        with cols[i % 2]:
            st.plotly_chart(
                plot_multi_stock_bar(features_df, selected_codes, field, title),
                use_container_width=True,
            )

# ============================================================
# Export
# ============================================================
st.divider()
st.subheader("导出对比结果")

# Export with Chinese column names
export_df = selected_df.rename(columns=rename_map)
csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")
st.download_button(
    "📥 下载对比结果 (CSV)",
    csv_data,
    file_name=f"comparison_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
)

# Footer
st.markdown("---")
st.caption("免责声明: 对比结果仅供学习参考，不构成投资建议。投资有风险，入市需谨慎。")
