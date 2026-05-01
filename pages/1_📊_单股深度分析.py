"""单股深度分析页面（占位）."""

import streamlit as st

st.set_page_config(page_title="单股深度分析", page_icon="📊", layout="wide")

st.title("单股深度分析")

# Read params from query string or session_state
stock_code = st.query_params.get("stock_code", "")
stock_name = st.query_params.get("stock_name", "")

if not stock_code and "current_stock_code" in st.session_state:
    stock_code = st.session_state["current_stock_code"]
    stock_name = st.session_state.get("current_stock_name", "")

if stock_code:
    st.info(f"当前分析股票: **{stock_name}** ({stock_code})")
    st.warning("单股深度分析模块尚未实现。请在此基础上扩展 OLS/CAPM/GARCH 等深度分析功能。")
else:
    st.info("请从智能选股页面选择一只股票，或在下方手动输入。")

    col1, col2 = st.columns(2)
    with col1:
        input_code = st.text_input("股票代码", placeholder="例如: 300658")
    with col2:
        input_name = st.text_input("股票名称", placeholder="例如: 延江股份")

    if st.button("开始分析", disabled=not input_code):
        st.session_state["current_stock_code"] = input_code
        st.session_state["current_stock_name"] = input_name
        st.rerun()

st.markdown("---")
st.caption("免责声明: 本页面仅供学习和辅助分析，不构成投资建议。")
