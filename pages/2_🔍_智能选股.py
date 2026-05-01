"""智能选股与多因子筛选系统 — 主页面."""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# Page config must be first
st.set_page_config(page_title="智能选股", page_icon="🔍", layout="wide")

# ============================================================
# Imports
# ============================================================
from src.storage import feature_store
from src.screener.screening_engine import ScreeningEngine
from src.screener.presets import available_presets, get_preset_display, load_preset
from src.screener.scoring import available_profiles
from src.screener.filter_dsl import SUPPORTED_OPERATORS
from src.screener.result_formatter import format_results_table, add_rank_column
from src.screener.comparison import compare_stocks, build_radar_data, DIMENSIONS
from src.visualization.screener_charts import (
    plot_funnel, plot_industry_distribution, plot_market_cap_distribution,
    plot_score_distribution, plot_risk_return_scatter, plot_valuation_bubble,
    plot_score_bar, plot_radar, plot_multi_stock_bar,
)
from src.data.universe_manager import POOLS, universe_info
from src.jobs.manual_update import run_full_update
from src.utils.formatting import COLUMN_FORMAT
from src.utils.export import export_csv, export_excel, export_json, export_markdown
from src.utils.logger import logger

from datetime import datetime

# ============================================================
# Header
# ============================================================
st.title("🔍 A股智能选股与多因子筛选系统")
st.caption("从全市场股票中筛选符合你偏好的候选股票 | 筛选结果仅供学习和辅助分析，不构成投资建议")

# ============================================================
# Session State Init
# ============================================================
if "screener_results" not in st.session_state:
    st.session_state["screener_results"] = None
if "selected_for_comparison" not in st.session_state:
    st.session_state["selected_for_comparison"] = []
if "screening_engine" not in st.session_state:
    st.session_state["screening_engine"] = ScreeningEngine()

engine: ScreeningEngine = st.session_state["screening_engine"]

# ============================================================
# Sidebar — Data Management
# ============================================================
with st.sidebar:
    st.header("📊 数据管理")

    # Feature store status
    meta = feature_store.get_metadata()
    if meta.stock_count > 0:
        st.success(f"✅ 数据就绪")
        st.caption(f"最新交易日: {meta.latest_trade_date}")
        st.caption(f"股票数量: {meta.stock_count}")
        st.caption(f"特征数量: {meta.feature_count}")
        st.caption(f"更新时间: {meta.updated_at.strftime('%Y-%m-%d %H:%M') if meta.updated_at else '未知'}")
    else:
        st.warning("⚠️ 暂无数据，请先更新")

    st.divider()

    # ============================================================
    # Data Source Selection
    # ============================================================
    st.subheader("数据源配置")
    data_source = st.radio(
        "选择数据源",
        ["AKShare（免费）", "Tushare（需Token）", "自动（优先Tushare）"],
        index=0,
        help="AKShare 无需配置即可使用；Tushare 需要注册获取 Token",
    )

    # Store in session state
    if data_source.startswith("AKShare"):
        st.session_state["data_source"] = "akshare"
    elif data_source.startswith("Tushare"):
        st.session_state["data_source"] = "tushare"
    else:
        st.session_state["data_source"] = "auto"

    # Tushare token input (show when Tushare is selected)
    if st.session_state.get("data_source") in ("tushare", "auto"):
        tushare_token = st.text_input(
            "Tushare Token",
            value=st.session_state.get("tushare_token", ""),
            type="password",
            help="在 tushare.pro 注册后获取 Token",
            placeholder="请输入你的 Tushare Token",
        )
        if tushare_token:
            st.session_state["tushare_token"] = tushare_token
            import os
            os.environ["TUSHARE_TOKEN"] = tushare_token
            st.caption("✅ Token 已配置")
        else:
            st.caption("⚠️ 请输入 Tushare Token")

    st.divider()

    # Update controls
    st.subheader("数据更新")
    update_limit = st.number_input("限制更新数量（调试用，0=全部）", min_value=0, value=0, step=10)

    # Initialize stop flag in session state
    from src.data.batch_fetcher import StopFlag
    if "stop_flag" not in st.session_state:
        st.session_state["stop_flag"] = StopFlag()

    col_update, col_stop = st.columns([3, 1])
    with col_update:
        start_update = st.button("🔄 一键完整更新", use_container_width=True)
    with col_stop:
        stop_update = st.button("⏹ 停止", use_container_width=True)

    if stop_update:
        st.session_state["stop_flag"].stop()
        st.warning("已发送停止信号，当前操作将在处理完当前股票后停止...")

    if start_update:
        # Reset stop flag
        sf = st.session_state["stop_flag"]
        sf.reset()

        progress_bar = st.progress(0)
        status_text = st.empty()
        detail_text = st.empty()

        ds = st.session_state.get("data_source", "akshare")
        ds_name = {"akshare": "AKShare", "tushare": "Tushare", "auto": "自动(Tushare优先)"}.get(ds, ds)
        detail_text.caption(f"📡 数据源: {ds_name}")

        def _progress(step, pct, msg):
            progress_bar.progress(pct)
            status_text.caption(msg)
            if "失败" in msg or "error" in msg.lower():
                detail_text.warning(msg)
            elif "完成" in msg or "停止" in msg:
                detail_text.success(msg)

        with st.spinner("正在更新数据... (点击「停止」可中断)"):
            results = run_full_update(
                limit=update_limit if update_limit > 0 else None,
                data_source=ds,
                stop_flag=sf,
                progress_callback=_progress,
            )

        # Show summary
        was_stopped = results.get("stopped", False)
        bar_result = results.get("daily_bars", {})

        if was_stopped:
            st.warning("更新已被用户中断")
            if isinstance(bar_result, dict):
                success = bar_result.get("success", 0)
                skipped = bar_result.get("skipped", 0)
                st.info(f"已处理: {success} 只股票 (其中 {skipped} 只使用缓存)")
        elif isinstance(bar_result, dict):
            success = bar_result.get("success", 0)
            fail = bar_result.get("fail", 0)
            total = bar_result.get("total", 0)
            skipped = bar_result.get("skipped", 0)
            st.success(f"更新完成! {success}/{total} 成功, {fail} 失败, {skipped} 跳过(缓存)")
            if fail > 0:
                failures = bar_result.get("failures", [])
                fail_symbols = [f.get("symbol", "") for f in failures[:10]]
                st.warning(f"失败股票(前10): {', '.join(fail_symbols)}")
        else:
            st.success("更新完成!")

        # Reload engine features
        engine._features = None
        st.rerun()

    st.divider()

    # ============================================================
    # Sidebar — Screening Mode
    # ============================================================
    st.header("🎯 筛选设置")

    screen_mode = st.radio(
        "筛选模式",
        ["预设模板", "自定义筛选", "高级多级筛选"],
        index=0,
    )

    # Preset selection
    if screen_mode == "预设模板":
        presets = get_preset_display()
        preset_key = st.selectbox(
            "选择预设模板",
            options=list(presets.keys()),
            format_func=lambda x: presets[x],
        )
        # Show preset description
        preset_info = available_presets().get(preset_key, {})
        if preset_info.get("description"):
            st.caption(preset_info["description"])
        if preset_info.get("risk_warning"):
            st.warning(preset_info["risk_warning"])

    st.divider()

    # ============================================================
    # Sidebar — Common Parameters
    # ============================================================
    st.subheader("基础参数")

    # Pool selection
    pool_options = list(POOLS.keys())
    pool_name = st.selectbox("股票池", pool_options, format_func=lambda x: POOLS[x])

    # Exclude options
    exclude_st = st.checkbox("排除 ST 股票", value=True)
    exclude_suspended = st.checkbox("排除停牌股票", value=True)
    min_listing_days = st.number_input("最小上市天数", min_value=0, value=180, step=30)
    min_quality_score = st.slider("最小数据质量分数", 0, 100, 60, 5)

    # Top N
    top_n = st.number_input("返回 Top N", min_value=10, max_value=500, value=50, step=10)

    # Sort
    sort_options = {
        "total_score": "综合评分",
        "risk_score": "风险评分",
        "return_score": "收益评分",
        "liquidity_score": "流动性评分",
        "value_score": "估值评分",
        "quality_score": "质量评分",
        "ret_20d": "近20日收益",
        "ret_120d": "近120日收益",
        "sharpe_120d": "Sharpe",
        "roe": "ROE",
    }
    sort_by = st.selectbox("排序方式", list(sort_options.keys()), format_func=lambda x: sort_options[x])

    st.divider()

    # ============================================================
    # Sidebar — Custom Filters (simplified)
    # ============================================================
    custom_filters = {}
    if screen_mode == "自定义筛选":
        st.subheader("估值筛选")
        pe_range = st.slider("PE(TTM) 区间", -50, 500, (0, 30))
        pb_range = st.slider("PB 区间", 0.0, 20.0, (0.0, 3.0))

        st.subheader("收益筛选")
        ret_20d_min = st.number_input("近20日收益率下限(%)", value=-100.0, step=5.0)
        ret_120d_min = st.number_input("近120日收益率下限(%)", value=-100.0, step=5.0)

        st.subheader("风险筛选")
        vol_max = st.slider("120日波动率上限(%)", 0, 200, 100)
        mdd_min = st.number_input("120日最大回撤下限(%)", value=-100.0, step=5.0)

        st.subheader("流动性筛选")
        min_amount = st.number_input("20日均成交额下限(万)", value=5000, step=1000)

        custom_filters = {
            "pe_range": pe_range,
            "pb_range": pb_range,
            "ret_20d_min": ret_20d_min / 100,
            "ret_120d_min": ret_120d_min / 100,
            "vol_max": vol_max / 100,
            "mdd_min": mdd_min / 100,
            "min_amount": min_amount * 1e4,
        }

    # ============================================================
    # Sidebar — Advanced Multi-level Filters
    # ============================================================
    advanced_rules = []
    if screen_mode == "高级多级筛选":
        st.subheader("多级筛选规则")

        # Available fields for filtering
        filter_fields = [
            "latest_close", "pe_ttm", "pb", "roe", "ret_20d", "ret_60d", "ret_120d",
            "volatility_120d", "max_drawdown_120d", "avg_amount_20d", "turnover_rate_20d",
            "beta_120d", "sharpe_120d", "total_score", "risk_score", "total_mv", "circ_mv",
        ]

        num_rules = st.number_input("规则数量", 1, 10, 3)
        for i in range(num_rules):
            col1, col2, col3 = st.columns([3, 2, 3])
            with col1:
                field = st.selectbox(f"字段 {i+1}", filter_fields, key=f"adv_field_{i}")
            with col2:
                op = st.selectbox(f"操作符", [">=", "<=", ">", "<", "between", "top_pct", "bottom_pct"], key=f"adv_op_{i}")
            with col3:
                if op == "between":
                    v1 = st.number_input(f"最小值", value=0.0, key=f"adv_v1_{i}")
                    v2 = st.number_input(f"最大值", value=100.0, key=f"adv_v2_{i}")
                    value = [v1, v2]
                else:
                    value = st.number_input(f"值", value=0.0, key=f"adv_val_{i}")
            advanced_rules.append({"field": field, "operator": op, "value": value})

    # ============================================================
    # Sidebar — Run Button
    # ============================================================
    st.divider()
    run_button = st.button("🚀 运行筛选", type="primary", use_container_width=True)


# ============================================================
# Main Area — Run Screening
# ============================================================
if run_button:
    if not feature_store.is_available():
        st.error("❌ 暂无数据！请先在侧边栏点击「一键完整更新」获取数据。")
        st.stop()

    with st.spinner("正在加载特征数据..."):
        engine.load_features()

    # Build config
    if screen_mode == "预设模板":
        config = load_preset(preset_key)
        if config is None:
            st.error(f"预设模板 '{preset_key}' 加载失败")
            st.stop()
        # Apply common overrides
        config.setdefault("universe", {})
        if exclude_st:
            config["universe"]["exclude_st"] = True
        if min_listing_days > 0:
            config["universe"]["min_listing_days"] = min_listing_days
        if min_quality_score > 0:
            config["universe"]["min_data_quality_score"] = min_quality_score
        config.setdefault("ranking", {})["top_n"] = top_n
        config["ranking"]["sort_by"] = sort_by

    elif screen_mode == "自定义筛选":
        config = {
            "universe": {
                "market": "A股",
                "exclude_st": exclude_st,
                "exclude_suspended": exclude_suspended,
                "min_listing_days": min_listing_days,
                "min_data_quality_score": min_quality_score,
            },
            "stages": [
                {"name": "估值筛选", "logic": "AND", "rules": [
                    {"field": "pe_ttm", "operator": "between", "value": list(custom_filters["pe_range"])},
                    {"field": "pb", "operator": "between", "value": list(custom_filters["pb_range"])},
                ]},
                {"name": "收益筛选", "logic": "AND", "rules": [
                    {"field": "ret_20d", "operator": ">=", "value": custom_filters["ret_20d_min"]},
                    {"field": "ret_120d", "operator": ">=", "value": custom_filters["ret_120d_min"]},
                ]},
                {"name": "风险筛选", "logic": "AND", "rules": [
                    {"field": "volatility_120d", "operator": "<=", "value": custom_filters["vol_max"]},
                    {"field": "max_drawdown_120d", "operator": ">=", "value": custom_filters["mdd_min"]},
                ]},
                {"name": "流动性筛选", "logic": "AND", "rules": [
                    {"field": "avg_amount_20d", "operator": ">=", "value": custom_filters["min_amount"]},
                ]},
            ],
            "ranking": {
                "score_model": "balanced",
                "sort_by": sort_by,
                "ascending": False,
                "top_n": top_n,
            },
        }

    elif screen_mode == "高级多级筛选":
        config = {
            "universe": {
                "market": "A股",
                "exclude_st": exclude_st,
                "exclude_suspended": exclude_suspended,
                "min_listing_days": min_listing_days,
                "min_data_quality_score": min_quality_score,
            },
            "stages": [
                {"name": f"规则 {i+1}", "logic": "AND", "rules": [rule]}
                for i, rule in enumerate(advanced_rules)
            ],
            "ranking": {
                "score_model": "balanced",
                "sort_by": sort_by,
                "ascending": False,
                "top_n": top_n,
            },
        }

    # Execute screening
    with st.spinner("正在筛选..."):
        result = engine.run_custom(config)

    if result is None:
        st.error("筛选失败，请检查数据和配置。")
        st.stop()

    # Store in session state
    st.session_state["screener_results"] = result
    st.session_state["screener_config"] = config

# ============================================================
# Display Results
# ============================================================
result = st.session_state.get("screener_results")

if result is not None and len(result.candidates) > 0:
    candidates = result.candidates

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("筛选前", f"{result.total_before} 只")
    with col2:
        st.metric("筛选后", f"{result.total_after} 只")
    with col3:
        if "latest_trade_date" in candidates.columns:
            latest_date = candidates["latest_trade_date"].dropna().max()
            st.metric("数据日期", str(latest_date)[:10] if pd.notna(latest_date) else "未知")
    with col4:
        if "total_score" in candidates.columns:
            avg_score = candidates["total_score"].mean()
            st.metric("平均评分", f"{avg_score:.1f}")

    st.divider()

    # Tabs
    tabs = st.tabs([
        "📊 筛选总览", "📋 候选股票", "📈 风险收益",
        "💰 估值基本面", "🔄 流动性", "📉 技术趋势",
        "⚖️ 批量对比", "📥 导出",
    ])

    # ---- Tab 1: Overview ----
    with tabs[0]:
        col1, col2 = st.columns(2)

        with col1:
            # Funnel chart
            if result.stage_results:
                st.plotly_chart(plot_funnel(result.stage_results), use_container_width=True)

        with col2:
            # Score distribution
            st.plotly_chart(plot_score_distribution(candidates), use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(plot_industry_distribution(candidates), use_container_width=True)
        with col4:
            st.plotly_chart(plot_market_cap_distribution(candidates), use_container_width=True)

    # ---- Tab 2: Candidate List ----
    with tabs[1]:
        st.subheader("候选股票列表")

        # Format and display
        display_df = format_results_table(candidates)
        display_df = add_rank_column(display_df)

        st.dataframe(display_df, use_container_width=True, height=600)

        # Detailed view for individual stocks
        st.subheader("个股详情")
        if "stock_code" in candidates.columns:
            selected_code = st.selectbox(
                "选择股票查看详情",
                candidates["stock_code"].tolist(),
                format_func=lambda x: f"{x} - {candidates[candidates['stock_code']==x]['stock_name'].iloc[0] if 'stock_name' in candidates.columns else x}",
            )

            if selected_code:
                stock_row = candidates[candidates["stock_code"] == selected_code].iloc[0]

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**入选原因**")
                    reasons = stock_row.get("reasons", [])
                    if isinstance(reasons, list):
                        for r in reasons:
                            st.markdown(f"- {r}")
                    else:
                        st.info("暂无入选原因数据")

                with col_b:
                    st.markdown("**风险提示**")
                    risks = stock_row.get("risks", [])
                    if isinstance(risks, list):
                        for r in risks:
                            st.warning(r)
                    else:
                        st.info("暂无风险提示数据")

                # Deep analysis button
                st.divider()
                stock_name = stock_row.get("stock_name", "")
                if st.button(f"🔬 一键深度分析: {stock_name} ({selected_code})", type="primary"):
                    st.session_state["current_stock_code"] = selected_code
                    st.session_state["current_stock_name"] = stock_name
                    st.switch_page("pages/1_📊_单股深度分析.py")

    # ---- Tab 3: Risk-Return ----
    with tabs[2]:
        st.plotly_chart(plot_risk_return_scatter(candidates), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if "ret_120d" in candidates.columns:
                st.subheader("收益排行")
                top_ret = candidates.nlargest(10, "ret_120d")[["stock_code", "stock_name", "ret_120d"]].copy()
                top_ret["ret_120d"] = top_ret["ret_120d"].apply(lambda x: f"{x*100:.2f}%")
                st.dataframe(top_ret, use_container_width=True, hide_index=True)

        with col2:
            if "volatility_120d" in candidates.columns:
                st.subheader("低波动排行")
                low_vol = candidates.nsmallest(10, "volatility_120d")[["stock_code", "stock_name", "volatility_120d"]].copy()
                low_vol["volatility_120d"] = low_vol["volatility_120d"].apply(lambda x: f"{x*100:.2f}%")
                st.dataframe(low_vol, use_container_width=True, hide_index=True)

    # ---- Tab 4: Valuation ----
    with tabs[3]:
        st.plotly_chart(plot_valuation_bubble(candidates), use_container_width=True)

        val_cols = [c for c in ["pe_ttm", "pb", "roe", "total_mv"] if c in candidates.columns]
        if val_cols:
            st.subheader("估值指标统计")
            stats = candidates[val_cols].describe().T
            st.dataframe(stats, use_container_width=True)

    # ---- Tab 5: Liquidity ----
    with tabs[4]:
        liq_cols = [c for c in ["avg_amount_20d", "turnover_rate_20d", "liquidity_score"] if c in candidates.columns]
        if liq_cols:
            st.subheader("流动性指标")
            display_liq = candidates[["stock_code", "stock_name"] + liq_cols].copy()
            if "avg_amount_20d" in display_liq.columns:
                display_liq["avg_amount_20d"] = display_liq["avg_amount_20d"].apply(lambda x: f"{x/1e8:.2f}亿" if pd.notna(x) else "-")
            st.dataframe(display_liq, use_container_width=True, hide_index=True)

    # ---- Tab 6: Technical ----
    with tabs[5]:
        tech_cols = [c for c in ["is_ma_bullish", "rsi_14", "macd_hist", "technical_score"] if c in candidates.columns]
        if tech_cols:
            st.subheader("技术指标")
            display_tech = candidates[["stock_code", "stock_name"] + tech_cols].copy()
            st.dataframe(display_tech, use_container_width=True, hide_index=True)

        if "technical_score" in candidates.columns:
            st.plotly_chart(
                plot_score_bar(candidates[["stock_code", "stock_name", "technical_score"]].rename(
                    columns={"technical_score": "total_score"}), top_n=15),
                use_container_width=True,
            )

    # ---- Tab 7: Comparison ----
    with tabs[6]:
        st.subheader("批量对比")
        if "stock_code" in candidates.columns:
            compare_codes = st.multiselect(
                "选择 2-10 只股票进行对比",
                candidates["stock_code"].tolist(),
                max_selections=10,
                format_func=lambda x: f"{x} - {candidates[candidates['stock_code']==x]['stock_name'].iloc[0] if 'stock_name' in candidates.columns else x}",
            )

            if len(compare_codes) >= 2:
                # Radar chart
                radar_data = build_radar_data(candidates, compare_codes)
                if radar_data:
                    st.plotly_chart(plot_radar(radar_data), use_container_width=True)

                # Comparison bar charts
                for field, title in [
                    ("ret_20d", "近20日收益率"), ("ret_120d", "近120日收益率"),
                    ("volatility_120d", "120日波动率"), ("pe_ttm", "PE(TTM)"),
                    ("roe", "ROE"), ("total_score", "综合评分"),
                ]:
                    if field in candidates.columns:
                        st.plotly_chart(
                            plot_multi_stock_bar(candidates, compare_codes, field, title),
                            use_container_width=True,
                        )

                # Store for comparison page
                st.session_state["selected_for_comparison"] = compare_codes
            else:
                st.info("请至少选择 2 只股票进行对比")

    # ---- Tab 8: Export ----

    def _generate_markdown_report(df: pd.DataFrame, result) -> str:
        """Generate a markdown report from screening results."""
        lines = [
            "# A股智能选股筛选报告\n",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"**筛选前股票数量**: {result.total_before}\n",
            f"**筛选后股票数量**: {result.total_after}\n\n",
            "## 候选股票列表\n\n",
            "| 排名 | 代码 | 名称 | 行业 | 收盘价 | PE(TTM) | 20日收益 | 120日波动率 | 综合评分 |\n",
            "|------|------|------|------|--------|---------|----------|------------|----------|\n",
        ]
        for i, (_, row) in enumerate(df.head(50).iterrows(), 1):
            code = row.get("stock_code", "")
            name = row.get("stock_name", "")
            industry = row.get("industry", "")
            close = f"{row.get('latest_close', 0):.2f}" if pd.notna(row.get("latest_close")) else "-"
            pe = f"{row.get('pe_ttm', 0):.2f}" if pd.notna(row.get("pe_ttm")) else "-"
            ret = f"{row.get('ret_20d', 0)*100:.2f}%" if pd.notna(row.get("ret_20d")) else "-"
            vol = f"{row.get('volatility_120d', 0)*100:.2f}%" if pd.notna(row.get("volatility_120d")) else "-"
            score = f"{row.get('total_score', 0):.1f}" if pd.notna(row.get("total_score")) else "-"
            lines.append(f"| {i} | {code} | {name} | {industry} | {close} | {pe} | {ret} | {vol} | {score} |\n")
        lines.append("\n---\n")
        lines.append("**免责声明**: 本报告仅供学习和辅助分析，不构成任何投资建议。投资有风险，入市需谨慎。\n")
        return "".join(lines)

    with tabs[7]:
        st.subheader("导出筛选结果")

        export_cols = [c for c in candidates.columns if c not in ("reasons", "risks")]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            csv_data = candidates[export_cols].to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "📥 下载 CSV",
                csv_data,
                file_name=f"screener_result_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

        with col2:
            import io
            buffer = io.BytesIO()
            candidates[export_cols].to_excel(buffer, index=False, engine="openpyxl")
            st.download_button(
                "📥 下载 Excel",
                buffer.getvalue(),
                file_name=f"screener_result_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        with col3:
            import json
            json_data = {
                "meta": {
                    "generated_at": datetime.now().isoformat(),
                    "total_stocks": len(candidates),
                },
                "results": candidates[export_cols].where(candidates[export_cols].notna(), None).to_dict(orient="records"),
            }
            st.download_button(
                "📥 下载 JSON",
                json.dumps(json_data, ensure_ascii=False, indent=2, default=str),
                file_name=f"screener_result_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
            )

        with col4:
            md_content = _generate_markdown_report(candidates, result)
            st.download_button(
                "📥 下载 Markdown",
                md_content,
                file_name=f"screener_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
            )

elif result is not None and len(result.candidates) == 0:
    st.warning("⚠️ 筛选结果为空。请尝试放宽筛选条件。")
else:
    # No screening run yet
    st.info("👈 请在左侧设置筛选参数，然后点击「运行筛选」按钮。")

    # Show feature store info
    if feature_store.is_available():
        meta = feature_store.get_metadata()
        st.success(f"✅ Feature Store 已就绪: {meta.stock_count} 只股票, {meta.feature_count} 个特征")
    else:
        st.warning("⚠️ Feature Store 为空。请点击左侧「一键完整更新」获取数据。")


# Footer
st.markdown("---")
st.caption("数据来源: AKShare / Tushare | 仅供学习研究使用 | 不构成投资建议")
