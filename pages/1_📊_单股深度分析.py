"""单股深度分析页面 — 整合 FinanceWeb 深度分析功能."""

import os
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import streamlit as st

# Page config must be first
st.set_page_config(page_title="单股深度分析", page_icon="📊", layout="wide")

# ============================================================
# Imports (from finweb_src, FinanceWeb's renamed package)
# ============================================================
from finweb_src.config import config
from finweb_src.data.data_manager import DataManager
from finweb_src.data.validators import parse_stock_code, parse_benchmark_code
from finweb_src.analysis.preprocessing import preprocess
from finweb_src.analysis.performance import analyze_performance
from finweb_src.analysis.return_distribution import analyze_return_distribution
from finweb_src.analysis.risk_metrics import analyze_risk
from finweb_src.analysis.benchmark_comparison import analyze_benchmark
from finweb_src.analysis.ols_capm import analyze_ols_capm
from finweb_src.analysis.factor_models import analyze_factor_model
from finweb_src.analysis.time_series_tests import analyze_time_series
from finweb_src.analysis.arma_model import analyze_arma
from finweb_src.analysis.volatility_models import analyze_garch
from finweb_src.analysis.technical_indicators import analyze_technical
from finweb_src.analysis.liquidity import analyze_liquidity
from finweb_src.analysis.fundamental import analyze_fundamental
from finweb_src.analysis.rolling_analysis import analyze_rolling
from finweb_src.analysis.backtesting import backtest_dual_ma, backtest_rsi, backtest_bollinger
from finweb_src.analysis.scoring import calculate_score
from finweb_src.report.interpretation import generate_conclusion_summary
from finweb_src.report.generator import generate_json_report, generate_markdown_report, generate_html_report, generate_csv_export
from finweb_src.visualization.charts import (
    plot_candlestick, plot_price, plot_volume, plot_cumulative_returns,
    plot_net_value, plot_drawdown, plot_returns_distribution, plot_qq,
    plot_scatter_with_regression, plot_rolling_metric, plot_acf_pacf
)
from finweb_src.utils.date_utils import get_default_start_date, get_default_end_date
from finweb_src.utils.logger import get_logger

logger = get_logger("DeepAnalysis")


def _get_result(results: dict, key: str, field: str, default=None):
    """从 results 字典中提取分析结果（兼容 dataclass 和 dict）"""
    obj = results.get(key)
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


# ============================================================
# Session State (fw_ prefixed to avoid conflict with screener)
# ============================================================
def init_session_state():
    """初始化 session_state"""
    defaults = {
        "fw_analyzed": False,
        "fw_stock_data": None,
        "fw_processed_data": None,
        "fw_results": {},
        "fw_meta": {},
        "fw_warnings": [],
        "fw_last_analyzed_code": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # If a new stock code was passed from screener, reset analysis state
    current_code = st.session_state.get("fw_stock_code", "")
    last_code = st.session_state.get("fw_last_analyzed_code", "")
    if current_code and current_code != last_code:
        st.session_state["fw_analyzed"] = False
        st.session_state["fw_results"] = {}
        st.session_state["fw_meta"] = {}
        st.session_state["fw_warnings"] = []
        st.session_state["fw_last_analyzed_code"] = current_code


def render_sidebar():
    """渲染侧边栏输入区"""
    st.sidebar.title("📊 分析参数设置")

    # 返回选股按钮
    if st.sidebar.button("🔙 返回选股", use_container_width=True):
        st.switch_page("pages/2_🔍_智能选股.py")

    st.sidebar.markdown("---")

    # 基本信息 — 使用 key= 参数支持从 session_state 预填充
    st.sidebar.subheader("股票信息")
    stock_name = st.sidebar.text_input(
        "股票名称",
        value=st.session_state.get("fw_stock_name", "延江股份"),
        key="fw_stock_name",
        help="仅用于报告显示",
    )
    stock_code = st.sidebar.text_input(
        "股票代码",
        value=st.session_state.get("fw_stock_code", "300658"),
        key="fw_stock_code",
        help="如 300658 或 300658.SZ",
    )

    # 日期设置
    st.sidebar.subheader("分析区间")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "起始日期",
            value=get_default_start_date(years=3),
            max_value=datetime.now().date()
        )
    with col2:
        end_date = st.date_input(
            "结束日期",
            value=get_default_end_date(),
            max_value=datetime.now().date()
        )

    # 基准指数
    st.sidebar.subheader("基准设置")
    benchmark_options = {
        "沪深300": "000300",
        "上证指数": "000001",
        "深证成指": "399001",
        "创业板指": "399006",
        "中证500": "000905",
        "中证1000": "000852",
    }
    benchmark_name = st.sidebar.selectbox("基准指数", list(benchmark_options.keys()), index=0)
    benchmark_code = benchmark_options[benchmark_name]

    # 数据源
    st.sidebar.subheader("数据源设置")
    source_options = ["自动选择", "AKShare", "Tushare"]
    data_source = st.sidebar.selectbox("数据源", source_options, index=0)

    # Tushare Token
    tushare_token = st.sidebar.text_input(
        "Tushare Token",
        value=os.getenv("TUSHARE_TOKEN", ""),
        type="password",
        help="若使用 Tushare 数据源请填写 Token"
    )

    # 高级参数
    st.sidebar.subheader("高级参数")
    adj_type = st.sidebar.selectbox("复权方式", ["前复权", "后复权", "不复权"], index=0)
    rf_annual = st.sidebar.number_input("无风险利率(年化%)", value=2.0, min_value=0.0, max_value=10.0) / 100
    garch_dist = st.sidebar.selectbox("GARCH分布", ["t", "normal"], index=0)

    # 耗时模型开关
    st.sidebar.subheader("耗时模型")
    run_arma = st.sidebar.checkbox("ARMA模型", value=False)
    run_garch = st.sidebar.checkbox("GARCH模型", value=True)
    run_factor = st.sidebar.checkbox("多因子模型", value=True)
    run_backtest = st.sidebar.checkbox("策略回测", value=True)

    # 开始分析按钮
    st.sidebar.markdown("---")
    start_analysis = st.sidebar.button("🚀 开始分析", type="primary", use_container_width=True)

    return {
        "stock_name": stock_name,
        "stock_code": stock_code,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "benchmark_name": benchmark_name,
        "benchmark_code": benchmark_code,
        "data_source": data_source,
        "tushare_token": tushare_token,
        "adj_type": adj_type,
        "rf_annual": rf_annual,
        "garch_dist": garch_dist,
        "run_arma": run_arma,
        "run_garch": run_garch,
        "run_factor": run_factor,
        "run_backtest": run_backtest,
        "start_analysis": start_analysis,
    }


def run_analysis(params: dict):
    """执行完整分析流程"""
    progress_bar = st.progress(0, text="准备中...")

    try:
        # 1. 数据获取
        progress_bar.progress(10, text="获取股票数据...")

        source_map = {"自动选择": "auto", "AKShare": "akshare", "Tushare": "tushare"}
        dm = DataManager(
            source=source_map.get(params["data_source"], "auto"),
            tushare_token=params["tushare_token"]
        )

        adj_map = {"前复权": "qfq", "后复权": "hfq", "不复权": "none"}
        stock_bundle = dm.fetch_all(
            stock_code=params["stock_code"],
            stock_name=params["stock_name"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            benchmark_code=params["benchmark_code"],
            adjust=adj_map[params["adj_type"]]
        )

        if stock_bundle is None or stock_bundle.daily is None or stock_bundle.daily.empty:
            st.error("❌ 获取股票数据失败，请检查股票代码和日期范围")
            return False

        st.session_state["fw_stock_data"] = stock_bundle

        # 2. 基准数据已在 fetch_all 中获取
        progress_bar.progress(20, text="获取基准指数数据...")
        if stock_bundle.index_daily is None or stock_bundle.index_daily.empty:
            st.warning("⚠️ 基准指数数据获取失败，部分分析将跳过")

        # 3. 数据预处理
        progress_bar.progress(30, text="数据预处理...")
        processed = preprocess(stock_bundle, benchmark_name=params["benchmark_name"])
        st.session_state["fw_processed_data"] = processed

        stock_df = processed.stock_df
        if stock_df is None or stock_df.empty:
            st.error("❌ 数据预处理失败，无有效数据")
            return False

        returns = stock_df["simple_return"].dropna()
        rf = params["rf_annual"]

        warnings = []
        results = {}

        # 4. 各模块分析
        progress_bar.progress(40, text="行情表现分析...")
        results["performance"] = analyze_performance(stock_df, rf)

        progress_bar.progress(45, text="收益率分布分析...")
        results["return_distribution"] = analyze_return_distribution(returns)

        progress_bar.progress(50, text="风险指标分析...")
        results["risk_metrics"] = analyze_risk(stock_df, rf)

        progress_bar.progress(55, text="基准比较分析...")
        if processed.index_df is not None and not processed.index_df.empty and "simple_return" in processed.index_df.columns:
            results["benchmark_comparison"] = analyze_benchmark(
                stock_df, processed.index_df, rf
            )

        progress_bar.progress(60, text="OLS/CAPM分析...")
        if processed.index_df is not None and not processed.index_df.empty and "simple_return" in processed.index_df.columns:
            index_returns = processed.index_df["simple_return"].dropna()
            aligned_stock, aligned_index = returns.align(index_returns, join="inner")
            if len(aligned_stock) > 30:
                results["ols_capm"] = analyze_ols_capm(aligned_stock, aligned_index, rf)

        progress_bar.progress(65, text="时间序列检验...")
        results["time_series_tests"] = analyze_time_series(returns, stock_df["close"])

        progress_bar.progress(70, text="技术指标分析...")
        results["technical_indicators"] = analyze_technical(stock_df)

        progress_bar.progress(75, text="流动性分析...")
        results["liquidity"] = analyze_liquidity(stock_df)

        # 基本面分析
        progress_bar.progress(78, text="基本面分析...")
        if stock_bundle.fundamental is not None or stock_bundle.financial is not None:
            results["fundamental"] = analyze_fundamental(
                stock_bundle.fundamental, stock_bundle.financial
            )

        # 多因子模型
        if params["run_factor"] and processed.index_df is not None and not processed.index_df.empty:
            progress_bar.progress(80, text="多因子模型...")
            results["factor_models"] = analyze_factor_model(stock_df, processed.index_df, rf)

        # GARCH 模型
        if params["run_garch"]:
            progress_bar.progress(85, text="GARCH波动率模型...")
            results["garch"] = analyze_garch(
                returns * 100,
                model_type="GARCH",
                p=1, q=1,
                dist=params["garch_dist"]
            )

        # ARMA 模型
        if params["run_arma"]:
            progress_bar.progress(88, text="ARMA模型...")
            results["arma_model"] = analyze_arma(returns, max_p=3, max_q=3, forecast_days=5)

        # 滚动分析
        progress_bar.progress(90, text="滚动分析...")
        if processed.index_df is not None and not processed.index_df.empty:
            results["rolling_analysis"] = analyze_rolling(stock_df, processed.index_df, rf)

        # 策略回测
        if params["run_backtest"]:
            progress_bar.progress(93, text="策略回测...")
            bt_results = []
            for func in [backtest_dual_ma, backtest_rsi, backtest_bollinger]:
                try:
                    r = func(stock_df)
                    if r.success:
                        bt_results.append(r)
                except Exception as e:
                    logger.warning(f"回测失败: {e}")
            if bt_results:
                results["backtesting"] = bt_results[0]

        # 综合评分
        progress_bar.progress(96, text="综合评分...")
        perf_result = results.get("performance")
        risk_result = results.get("risk_metrics")
        bench_result = results.get("benchmark_comparison")
        liq_result = results.get("liquidity")
        fund_result = results.get("fundamental")

        perf_data = getattr(perf_result, "data", {}) if perf_result else {}
        risk_data = getattr(risk_result, "data", {}) if risk_result else {}
        bench_data = getattr(bench_result, "data", {}) if bench_result else {}
        liq_data = getattr(liq_result, "data", {}) if liq_result else {}
        fund_data = getattr(fund_result, "data", {}) if fund_result else {}

        score_data, score_interp = calculate_score(
            perf_data, risk_data, bench_data, liq_data, fund_data, warnings
        )
        results["score"] = {
            "success": True,
            "data": score_data,
            "interpretation": score_interp
        }

        # 结论汇总
        results["conclusion"] = generate_conclusion_summary(results)

        # 保存结果
        meta = {
            "stock_name": params["stock_name"],
            "stock_code": params["stock_code"],
            "start_date": params["start_date"],
            "end_date": params["end_date"],
            "benchmark": params["benchmark_name"],
            "data_source": params["data_source"],
        }

        st.session_state["fw_results"] = results
        st.session_state["fw_meta"] = meta
        st.session_state["fw_warnings"] = warnings
        st.session_state["fw_analyzed"] = True
        st.session_state["fw_last_analyzed_code"] = params["stock_code"]

        progress_bar.progress(100, text="✅ 分析完成!")
        return True

    except Exception as e:
        logger.exception("分析过程出错")
        st.error(f"❌ 分析过程出错: {e}")
        return False


def render_results():
    """渲染分析结果"""
    results = st.session_state.get("fw_results", {})
    meta = st.session_state.get("fw_meta", {})
    processed = st.session_state.get("fw_processed_data")

    if not results:
        st.info("请在左侧设置参数后点击「开始分析」")
        return

    stock_df = processed.stock_df if processed else None

    # Tab 页面
    tabs = st.tabs([
        "📋 总览", "📈 行情收益", "⚠️ 风险指标", "🎯 基准比较",
        "📉 OLS/CAPM", "🔬 时间序列", "📊 GARCH", "📐 技术指标",
        "💰 基本面", "💧 流动性", "🔄 策略回测", "⭐ 综合结论", "📥 报告导出"
    ])

    with tabs[0]:
        render_overview_tab(meta, results, stock_df)
    with tabs[1]:
        render_performance_tab(results, stock_df)
    with tabs[2]:
        render_risk_tab(results, stock_df)
    with tabs[3]:
        render_benchmark_tab(results, processed)
    with tabs[4]:
        render_ols_tab(results)
    with tabs[5]:
        render_ts_tab(results)
    with tabs[6]:
        render_garch_tab(results)
    with tabs[7]:
        render_technical_tab(results, stock_df)
    with tabs[8]:
        render_fundamental_tab(results)
    with tabs[9]:
        render_liquidity_tab(results)
    with tabs[10]:
        render_backtest_tab(results)
    with tabs[11]:
        render_conclusion_tab(results)
    with tabs[12]:
        render_export_tab(meta, results, stock_df)


def _render_data_table(key, results, columns=["指标", "值"]):
    """通用：渲染数据表格"""
    data = _get_result(results, key, "data", {})
    if data and isinstance(data, dict):
        items = []
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                continue
            items.append((k, str(v) if not isinstance(v, str) else v))
        df = pd.DataFrame(items, columns=columns)
        st.dataframe(df, hide_index=True)


def render_overview_tab(meta, results, stock_df):
    """总览 Tab"""
    st.subheader("📊 分析概览")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("股票名称", meta.get("stock_name", "-"))
    with col2:
        st.metric("股票代码", meta.get("stock_code", "-"))
    with col3:
        st.metric("基准指数", meta.get("benchmark", "-"))
    with col4:
        st.metric("数据源", meta.get("data_source", "-"))

    perf = _get_result(results, "performance", "data", {})
    risk = _get_result(results, "risk_metrics", "data", {})

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("区间累计收益", f"{perf.get('区间累计收益率', 0)*100:.2f}%")
    with col2:
        st.metric("年化收益", f"{perf.get('区间年化收益率', 0)*100:.2f}%")
    with col3:
        st.metric("年化波动率", f"{perf.get('区间年化波动率', 0)*100:.2f}%")
    with col4:
        st.metric("最大回撤", f"{abs(risk.get('最大回撤', 0))*100:.2f}%")
    with col5:
        st.metric("Sharpe比率", f"{risk.get('Sharpe_Ratio', 0):.3f}")

    if stock_df is not None:
        st.subheader("价格走势")
        fig = plot_price(stock_df, title="收盘价走势")
        st.plotly_chart(fig, use_container_width=True)


def render_performance_tab(results, stock_df):
    """行情表现 Tab"""
    success = _get_result(results, "performance", "success", False)
    if not success:
        st.warning("行情表现分析数据不可用")
        return

    st.subheader("📈 行情表现分析")
    st.info(_get_result(results, "performance", "interpretation", ""))

    st.subheader("详细指标")
    _render_data_table("performance", results)

    if stock_df is not None:
        col1, col2 = st.columns(2)
        with col1:
            fig = plot_cumulative_returns(stock_df, title="累计收益率")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = plot_volume(stock_df, title="成交量")
            st.plotly_chart(fig, use_container_width=True)


def render_risk_tab(results, stock_df):
    """风险指标 Tab"""
    success = _get_result(results, "risk_metrics", "success", False)
    if not success:
        st.warning("风险指标分析数据不可用")
        return

    st.subheader("⚠️ 风险指标分析")
    st.info(_get_result(results, "risk_metrics", "interpretation", ""))
    _render_data_table("risk_metrics", results)

    if stock_df is not None:
        fig = plot_drawdown(stock_df, title="回撤曲线")
        st.plotly_chart(fig, use_container_width=True)


def render_benchmark_tab(results, processed):
    """基准比较 Tab"""
    success = _get_result(results, "benchmark_comparison", "success", False)
    if not success:
        st.warning("基准比较分析数据不可用")
        return

    st.subheader("🎯 基准比较分析")
    st.info(_get_result(results, "benchmark_comparison", "interpretation", ""))
    _render_data_table("benchmark_comparison", results)

    if processed and processed.stock_df is not None and processed.index_df is not None:
        fig = plot_net_value(processed.stock_df, processed.index_df, title="股票 vs 基准 净值曲线")
        st.plotly_chart(fig, use_container_width=True)


def render_ols_tab(results):
    """OLS/CAPM Tab"""
    success = _get_result(results, "ols_capm", "success", False)
    if not success:
        st.warning("OLS/CAPM 分析数据不可用")
        return

    st.subheader("📉 OLS/CAPM 回归分析")
    st.info(_get_result(results, "ols_capm", "interpretation", ""))
    _render_data_table("ols_capm", results)


def render_ts_tab(results):
    """时间序列检验 Tab"""
    success = _get_result(results, "time_series_tests", "success", False)
    if not success:
        st.warning("时间序列检验数据不可用")
        return

    st.subheader("🔬 时间序列检验")
    st.info(_get_result(results, "time_series_tests", "interpretation", ""))
    _render_data_table("time_series_tests", results, columns=["检验", "结果"])


def render_garch_tab(results):
    """GARCH Tab"""
    success = _get_result(results, "garch", "success", False)
    if not success:
        st.warning("GARCH 模型数据不可用")
        return

    st.subheader("📊 GARCH 波动率模型")
    st.info(_get_result(results, "garch", "interpretation", ""))
    _render_data_table("garch", results, columns=["参数", "值"])


def render_technical_tab(results, stock_df):
    """技术指标 Tab"""
    success = _get_result(results, "technical_indicators", "success", False)
    if not success:
        st.warning("技术指标分析数据不可用")
        return

    st.subheader("📐 技术指标分析")
    st.info(_get_result(results, "technical_indicators", "interpretation", ""))
    _render_data_table("technical_indicators", results)


def render_fundamental_tab(results):
    """基本面 Tab"""
    success = _get_result(results, "fundamental", "success", False)
    if not success:
        st.warning("基本面分析数据不可用（可能数据源未提供）")
        return

    st.subheader("💰 基本面分析")
    st.info(_get_result(results, "fundamental", "interpretation", ""))
    _render_data_table("fundamental", results)


def render_liquidity_tab(results):
    """流动性 Tab"""
    success = _get_result(results, "liquidity", "success", False)
    if not success:
        st.warning("流动性分析数据不可用")
        return

    st.subheader("💧 流动性分析")
    st.info(_get_result(results, "liquidity", "interpretation", ""))
    _render_data_table("liquidity", results)


def render_backtest_tab(results):
    """策略回测 Tab"""
    success = _get_result(results, "backtesting", "success", False)
    if not success:
        st.warning("策略回测数据不可用")
        return

    st.subheader("🔄 策略回测")
    st.info(_get_result(results, "backtesting", "interpretation", ""))

    data = _get_result(results, "backtesting", "data", {})
    if data:
        strategy_name = data.pop("策略名称", "策略") if isinstance(data, dict) else "策略"
        st.markdown(f"**策略**: {strategy_name}")
        if isinstance(data, dict):
            df = pd.DataFrame(list(data.items()), columns=["指标", "值"])
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.warning("⚠️ 简单技术策略回测仅用于学习和辅助分析，不构成投资建议，历史表现不代表未来。")


def render_conclusion_tab(results):
    """综合结论 Tab"""
    score = results.get("score", {})
    conclusion = results.get("conclusion", {})

    st.subheader("⭐ 综合评分")

    if score.get("success"):
        data = score.get("data", {})
        total = data.get("总分", 0)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"<h1 style='text-align:center;color:#1f77b4;'>{total}/100</h1>", unsafe_allow_html=True)

        scores = data.get("各维度得分", {})
        if scores:
            st.subheader("各维度得分")
            for name, s in scores.items():
                st.progress(s / 20 if "收益" in name or "风险" in name else s / 15, text=f"{name}: {s}分")

        st.info(score.get("interpretation", ""))

    if conclusion:
        st.subheader("📋 核心结论")
        for s in conclusion.get("summary", []):
            st.write(f"- {s}")

        if conclusion.get("strengths"):
            st.subheader("✅ 优点")
            for s in conclusion["strengths"]:
                st.write(f"- {s}")

        if conclusion.get("risks"):
            st.subheader("⚠️ 风险点")
            for s in conclusion["risks"]:
                st.write(f"- {s}")


def render_export_tab(meta, results, stock_df):
    """报告导出 Tab"""
    st.subheader("📥 报告导出")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📄 导出 JSON", use_container_width=True):
            path = generate_json_report(meta, results, "outputs/json/result.json")
            st.success(f"已保存: {path}")

    with col2:
        if st.button("📝 导出 Markdown", use_container_width=True):
            path = generate_markdown_report(meta, results, "outputs/reports/report.md")
            st.success(f"已保存: {path}")

    with col3:
        if st.button("🌐 导出 HTML", use_container_width=True):
            path = generate_html_report(meta, results, "outputs/reports/report.html")
            st.success(f"已保存: {path}")

    with col4:
        if st.button("📊 导出 CSV", use_container_width=True):
            if stock_df is not None:
                path = generate_csv_export(stock_df, "outputs/data/stock_data.csv")
                st.success(f"已保存: {path}")
            else:
                st.warning("无数据可导出")

    st.markdown("---")
    st.markdown("""
    ### 免责声明

    本报告基于历史数据自动生成，仅供学习和研究参考，不构成任何投资建议。
    投资者应独立判断并承担投资风险。历史表现不代表未来收益。

    本报告使用的模型和指标均有其假设前提和局限性，实际投资决策应结合更多因素综合考量。
    """)


# ============================================================
# Main
# ============================================================
init_session_state()
params = render_sidebar()

st.title("📈 A股单股深度分析")
st.markdown("---")

if params["start_analysis"]:
    run_analysis(params)

render_results()

st.markdown("---")
st.caption("免责声明: 本页面仅供学习和辅助分析，不构成投资建议。投资有风险，入市需谨慎。")
