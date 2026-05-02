"""Comparison visualization charts."""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def plot_comparison_bar(
    df: pd.DataFrame,
    stock_codes: list[str],
    field: str,
    title: str = "",
) -> go.Figure:
    """Bar chart comparing a field across stocks."""
    selected = df[df["stock_code"].isin(stock_codes)].copy()
    if field not in selected.columns:
        return _empty_chart(f"无{field}数据")

    selected["标签"] = selected.apply(
        lambda r: f"{r.get('stock_name', '')}({r.get('stock_code', '')})", axis=1
    )
    selected = selected.sort_values(field, ascending=False)

    fig = px.bar(selected, x="标签", y=field, title=title or field,
                 color=field, color_continuous_scale="RdYlGn")
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def plot_comparison_radar(scores: list[dict]) -> go.Figure:
    """Radar chart for multi-stock comparison."""
    categories = ["return_score", "risk_score", "liquidity_score",
                  "value_score", "quality_score", "technical_score"]
    labels = ["收益", "风险", "流动性", "估值", "质量", "技术"]
    colors = px.colors.qualitative.Set2

    fig = go.Figure()
    for i, stock in enumerate(scores):
        values = [stock.get(c, 0) or 0 for c in categories]
        values.append(values[0])
        fig.add_trace(go.Scatterpolar(
            r=values, theta=labels + [labels[0]], fill="toself",
            name=stock.get("stock_name", stock.get("stock_code", f"Stock {i}")),
            line_color=colors[i % len(colors)], opacity=0.7,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="多维评分雷达图", height=500,
        margin=dict(l=60, r=60, t=60, b=60),
    )
    return fig


def _empty_chart(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    fig.update_layout(height=300)
    return fig


__all__ = ["plot_comparison_bar", "plot_comparison_radar"]
