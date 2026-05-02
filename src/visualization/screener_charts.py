"""Visualization charts for the stock screener."""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_funnel(stage_results: list) -> go.Figure:
    """Plot screening funnel chart."""
    names = [s.name if hasattr(s, "name") else s.get("name", "") for s in stage_results]
    values = [s.count_after if hasattr(s, "count_after") else s.get("count_after", 0) for s in stage_results]

    fig = go.Figure(go.Funnel(
        y=names,
        x=values,
        textinfo="value+percent initial",
        marker=dict(color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]),
    ))
    fig.update_layout(
        title="筛选漏斗",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_industry_distribution(df: pd.DataFrame) -> go.Figure:
    """Plot industry distribution bar chart."""
    if "industry" not in df.columns:
        return _empty_chart("无行业数据")

    counts = df["industry"].value_counts().head(20)

    fig = px.bar(
        x=counts.values,
        y=counts.index,
        orientation="h",
        labels={"x": "股票数量", "y": "行业"},
        title="行业分布",
    )
    fig.update_layout(
        height=max(400, len(counts) * 25),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_market_cap_distribution(df: pd.DataFrame) -> go.Figure:
    """Plot market cap distribution histogram."""
    col = "total_mv"
    if col not in df.columns:
        return _empty_chart("无市值数据")

    mv = df[col].dropna() / 1e8  # 转换为亿
    mv = mv[mv > 0]

    fig = px.histogram(
        mv,
        nbins=50,
        labels={"value": "总市值(亿元)", "count": "股票数量"},
        title="市值分布",
    )
    fig.update_layout(
        height=350,
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_score_distribution(df: pd.DataFrame, score_col: str = "total_score") -> go.Figure:
    """Plot score distribution histogram."""
    if score_col not in df.columns:
        return _empty_chart(f"无{score_col}数据")

    scores = df[score_col].dropna()

    if len(scores) == 0:
        return _empty_chart(f"无有效{score_col}数据")

    fig = px.histogram(
        scores,
        nbins=30,
        labels={"value": "评分", "count": "股票数量"},
        title="综合评分分布",
        color_discrete_sequence=["#1f77b4"],
    )
    fig.add_vline(x=scores.mean(), line_dash="dash", line_color="red",
                  annotation_text=f"均值: {scores.mean():.1f}")
    fig.update_layout(
        height=350,
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_risk_return_scatter(df: pd.DataFrame) -> go.Figure:
    """Plot risk-return scatter chart."""
    x_col = "volatility_120d"
    y_col = "ret_120d"
    if x_col not in df.columns or y_col not in df.columns:
        return _empty_chart("无风险收益数据")

    plot_df = df.dropna(subset=[x_col, y_col]).copy()

    if len(plot_df) == 0:
        return _empty_chart("无有效风险收益数据")

    # Convert to percentage for display
    plot_df["波动率(%)"] = plot_df[x_col] * 100
    plot_df["收益率(%)"] = plot_df[y_col] * 100
    plot_df["股票"] = plot_df["stock_name"] + "(" + plot_df["stock_code"] + ")" if "stock_name" in plot_df.columns else plot_df["stock_code"]

    # Handle market cap — fill NaN with median or default
    has_mv = "total_mv" in plot_df.columns
    if has_mv:
        plot_df["市值(亿)"] = plot_df["total_mv"] / 1e8
        mv_valid = plot_df["市值(亿)"].dropna()
        if len(mv_valid) > 0:
            plot_df["市值(亿)"] = plot_df["市值(亿)"].fillna(mv_valid.median())
        else:
            plot_df["市值(亿)"] = 10
    else:
        plot_df["市值(亿)"] = 10

    color_col = "total_score" if "total_score" in plot_df.columns and plot_df["total_score"].notna().any() else None

    fig = px.scatter(
        plot_df,
        x="波动率(%)",
        y="收益率(%)",
        size="市值(亿)",
        color=color_col,
        hover_name="股票",
        title="风险收益散点图",
        color_continuous_scale="RdYlGn",
        size_max=30,
    )
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def plot_valuation_bubble(df: pd.DataFrame) -> go.Figure:
    """Plot valuation-growth bubble chart."""
    x_col = "pe_ttm"
    y_col = "roe"
    if x_col not in df.columns or y_col not in df.columns:
        return _empty_chart("无估值数据")

    plot_df = df.dropna(subset=[x_col, y_col]).copy()
    plot_df = plot_df[(plot_df[x_col] > 0) & (plot_df[x_col] < 200)]

    if len(plot_df) == 0:
        return _empty_chart("无有效估值数据")

    plot_df["股票"] = plot_df["stock_name"] + "(" + plot_df["stock_code"] + ")" if "stock_name" in plot_df.columns else plot_df["stock_code"]

    # Handle market cap
    has_mv = "total_mv" in plot_df.columns
    if has_mv:
        plot_df["市值(亿)"] = plot_df["total_mv"] / 1e8
        mv_valid = plot_df["市值(亿)"].dropna()
        if len(mv_valid) > 0:
            plot_df["市值(亿)"] = plot_df["市值(亿)"].fillna(mv_valid.median())
        else:
            plot_df["市值(亿)"] = 10
    else:
        plot_df["市值(亿)"] = 10

    color_col = "total_score" if "total_score" in plot_df.columns and plot_df["total_score"].notna().any() else None

    fig = px.scatter(
        plot_df,
        x=x_col,
        y=y_col,
        size="市值(亿)",
        color=color_col,
        hover_name="股票",
        title="估值-盈利气泡图",
        labels={x_col: "PE(TTM)", y_col: "ROE(%)"},
        color_continuous_scale="RdYlGn",
        size_max=30,
    )
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def plot_score_bar(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Plot top N stocks by total score."""
    if "total_score" not in df.columns:
        return _empty_chart("无评分数据")

    top = df.nlargest(top_n, "total_score").copy()
    top["标签"] = top["stock_name"] + "(" + top["stock_code"] + ")" if "stock_name" in top.columns else top["stock_code"]

    fig = px.bar(
        top,
        x="total_score",
        y="标签",
        orientation="h",
        title=f"Top {top_n} 综合评分",
        labels={"total_score": "综合评分", "标签": ""},
        color="total_score",
        color_continuous_scale="RdYlGn",
    )
    fig.update_layout(
        height=max(400, top_n * 25),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_radar(stock_scores: list[dict]) -> go.Figure:
    """Plot radar chart for stock comparison.

    Only includes score dimensions that have at least one non-zero value.
    """
    all_categories = ["return_score", "risk_score", "liquidity_score",
                      "value_score", "quality_score", "technical_score"]
    all_labels = ["收益", "风险", "流动性", "估值", "质量", "技术"]

    # Filter out categories where ALL stocks have 0 or NaN
    active_categories = []
    active_labels = []
    for cat, label in zip(all_categories, all_labels):
        has_value = any(
            stock.get(cat) is not None and not pd.isna(stock.get(cat)) and stock.get(cat, 0) > 0
            for stock in stock_scores
        )
        if has_value:
            active_categories.append(cat)
            active_labels.append(label)

    if not active_categories:
        # No valid data at all
        fig = go.Figure()
        fig.add_annotation(text="无有效评分数据", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        fig.update_layout(height=400)
        return fig

    fig = go.Figure()
    colors = px.colors.qualitative.Set2

    for i, stock in enumerate(stock_scores):
        values = [stock.get(c, 0) or 0 for c in active_categories]
        values.append(values[0])  # close the polygon
        label = stock.get("stock_name", stock.get("stock_code", f"Stock {i}"))

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=active_labels + [active_labels[0]],
            fill="toself",
            name=label,
            line_color=colors[i % len(colors)],
            opacity=0.7,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="多维评分雷达图",
        height=500,
        margin=dict(l=60, r=60, t=60, b=60),
    )
    return fig


def plot_multi_stock_bar(
    df: pd.DataFrame,
    stock_codes: list[str],
    field: str,
    title: str = "",
) -> go.Figure:
    """Plot bar chart comparing a single field across stocks."""
    selected = df[df["stock_code"].isin(stock_codes)].copy()
    if field not in selected.columns:
        return _empty_chart(f"无{field}数据")

    selected["标签"] = selected["stock_name"] + "(" + selected["stock_code"] + ")" if "stock_name" in selected.columns else selected["stock_code"]
    selected = selected.sort_values(field, ascending=False)

    fig = px.bar(
        selected,
        x="标签",
        y=field,
        title=title or field,
        labels={field: title or field, "标签": ""},
        color=field,
        color_continuous_scale="RdYlGn",
    )
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def _empty_chart(message: str) -> go.Figure:
    """Return an empty chart with a message."""
    fig = go.Figure()
    fig.add_annotation(text=message, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                       font=dict(size=16, color="gray"))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
    return fig


__all__ = [
    "plot_funnel", "plot_industry_distribution", "plot_market_cap_distribution",
    "plot_score_distribution", "plot_risk_return_scatter", "plot_valuation_bubble",
    "plot_score_bar", "plot_radar", "plot_multi_stock_bar",
]
