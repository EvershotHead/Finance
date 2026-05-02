"""Factor distribution and analysis charts."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def plot_factor_distribution(df: pd.DataFrame, field: str, title: str = "") -> go.Figure:
    """Plot histogram of a factor."""
    if field not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text=f"无{field}数据", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    data = df[field].dropna()
    fig = px.histogram(data, nbins=50, title=title or f"{field} 分布",
                       labels={"value": field, "count": "数量"})
    fig.update_layout(height=350, showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def plot_factor_boxplot(df: pd.DataFrame, field: str, group_by: str = "board") -> go.Figure:
    """Plot boxplot of a factor grouped by category."""
    if field not in df.columns or group_by not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="数据不足", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    fig = px.box(df, x=group_by, y=field, title=f"{field} by {group_by}")
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def plot_factor_correlation(df: pd.DataFrame, fields: list[str]) -> go.Figure:
    """Plot correlation heatmap for selected factors."""
    available = [f for f in fields if f in df.columns]
    if len(available) < 2:
        fig = go.Figure()
        fig.add_annotation(text="数据不足", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    corr = df[available].corr()
    fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                    title="因子相关性矩阵")
    fig.update_layout(height=500, margin=dict(l=20, r=20, t=40, b=20))
    return fig


__all__ = ["plot_factor_distribution", "plot_factor_boxplot", "plot_factor_correlation"]
