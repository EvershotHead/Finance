"""图表生成模块 - Plotly 交互式图表工厂"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.visualization.style import (
    COLORS, COLOR_CYCLE, FONT_FAMILY, create_figure, get_layout
)
from src.utils.logger import get_logger

logger = get_logger("Charts")


def plot_candlestick(df: pd.DataFrame, title: str = "K线图", show_volume: bool = True) -> go.Figure:
    """绘制 K 线图（可选附带成交量）"""
    if show_volume:
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            vertical_spacing=0.03, row_heights=[0.7, 0.3],
        )
    else:
        fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df["date"], open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            increasing_line_color=COLORS["up"],
            decreasing_line_color=COLORS["down"],
            name="K线",
        ),
        row=1 if show_volume else None, col=1,
    )

    if show_volume and "volume" in df.columns:
        colors = [COLORS["up"] if c >= o else COLORS["down"]
                  for c, o in zip(df["close"], df["open"])]
        fig.add_trace(
            go.Bar(x=df["date"], y=df["volume"], marker_color=colors, name="成交量", showlegend=False),
            row=2, col=1,
        )
        fig.update_yaxes(title_text="成交量", row=2, col=1)

    layout = get_layout(title=title, height=600 if show_volume else 500)
    fig.update_layout(**layout)
    fig.update_xaxes(rangeslider_visible=False)
    return fig


def plot_price(df: pd.DataFrame, title: str = "收盘价走势图", ma_cols: list[str] = None) -> go.Figure:
    """绘制收盘价走势图"""
    fig = create_figure(title=title)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["close"], mode="lines", name="收盘价",
        line=dict(color=COLORS["stock"], width=2),
    ))
    if ma_cols:
        for i, col in enumerate(ma_cols):
            if col in df.columns:
                fig.add_trace(go.Scatter(
                    x=df["date"], y=df[col], mode="lines", name=col.upper(),
                    line=dict(color=COLOR_CYCLE[(i + 1) % len(COLOR_CYCLE)], width=1, dash="dash"),
                ))
    fig.update_yaxes(title_text="价格")
    return fig


def plot_volume(df: pd.DataFrame, title: str = "成交量柱状图") -> go.Figure:
    """绘制成交量柱状图"""
    fig = create_figure(title=title)
    if "volume" in df.columns:
        colors = [COLORS["up"] if c >= o else COLORS["down"]
                  for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(x=df["date"], y=df["volume"], marker_color=colors, name="成交量"))
    fig.update_yaxes(title_text="成交量")
    return fig


def plot_cumulative_returns(stock_df, index_df=None, stock_name="股票", index_name="基准", title="累计收益率曲线"):
    """绘制累计收益率曲线"""
    fig = create_figure(title=title)
    if "cumulative_return" in stock_df.columns:
        fig.add_trace(go.Scatter(
            x=stock_df["date"], y=stock_df["cumulative_return"] * 100,
            mode="lines", name=stock_name, line=dict(color=COLORS["stock"], width=2),
        ))
    if index_df is not None and "index_cumulative_return" in index_df.columns:
        fig.add_trace(go.Scatter(
            x=index_df["date"], y=index_df["index_cumulative_return"] * 100,
            mode="lines", name=index_name, line=dict(color=COLORS["benchmark"], width=2, dash="dash"),
        ))
    fig.update_yaxes(title_text="累计收益率 (%)")
    return fig


def plot_net_value(stock_df, index_df=None, stock_name="股票", index_name="基准", title="净值曲线"):
    """绘制净值曲线"""
    fig = create_figure(title=title)
    if "simple_return" in stock_df.columns:
        stock_nv = (1 + stock_df["simple_return"].fillna(0)).cumprod()
        fig.add_trace(go.Scatter(
            x=stock_df["date"], y=stock_nv, mode="lines", name=stock_name,
            line=dict(color=COLORS["stock"], width=2),
        ))
    if index_df is not None and "index_simple_return" in index_df.columns:
        index_nv = (1 + index_df["index_simple_return"].fillna(0)).cumprod()
        fig.add_trace(go.Scatter(
            x=index_df["date"], y=index_nv, mode="lines", name=index_name,
            line=dict(color=COLORS["benchmark"], width=2, dash="dash"),
        ))
    fig.add_hline(y=1.0, line_dash="dot", line_color="gray", opacity=0.5)
    fig.update_yaxes(title_text="净值")
    return fig


def plot_drawdown(df: pd.DataFrame, title: str = "回撤曲线") -> go.Figure:
    """绘制回撤曲线"""
    fig = create_figure(title=title)
    if "drawdown" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["drawdown"] * 100,
            fill="tozeroy", fillcolor="rgba(214,39,40,0.3)",
            line=dict(color=COLORS["danger"], width=1), name="回撤",
        ))
    fig.update_yaxes(title_text="回撤 (%)")
    return fig


def plot_returns_distribution(returns: pd.Series, title: str = "收益率分布") -> go.Figure:
    """绘制收益率直方图 + KDE"""
    fig = create_figure(title=title)
    rc = returns.dropna()
    fig.add_trace(go.Histogram(
        x=rc * 100, histnorm="probability density", nbinsx=80,
        marker_color=COLORS["primary"], opacity=0.6, name="收益率分布",
    ))
    try:
        from scipy import stats
        kde = stats.gaussian_kde(rc * 100)
        xr = np.linspace(rc.min() * 100, rc.max() * 100, 200)
        fig.add_trace(go.Scatter(x=xr, y=kde(xr), mode="lines", name="KDE",
                                 line=dict(color=COLORS["danger"], width=2)))
    except Exception:
        pass
    fig.update_xaxes(title_text="日收益率 (%)")
    fig.update_yaxes(title_text="概率密度")
    return fig


def plot_qq(returns: pd.Series, title: str = "Q-Q 图") -> go.Figure:
    """绘制 Q-Q 图"""
    fig = create_figure(title=title, height=500, width=500)
    rc = returns.dropna().values
    n = len(rc)
    sr = np.sort(rc)
    from scipy import stats
    theory = stats.norm.ppf(np.arange(1, n + 1) / (n + 1))
    fig.add_trace(go.Scatter(
        x=theory * 100, y=sr * 100, mode="markers", name="实际分位数",
        marker=dict(color=COLORS["primary"], size=3, opacity=0.6),
    ))
    mn = min(theory.min(), sr.min()) * 100
    mx = max(theory.max(), sr.max()) * 100
    fig.add_trace(go.Scatter(
        x=[mn, mx], y=[mn, mx], mode="lines", name="正态参考线",
        line=dict(color=COLORS["danger"], width=2, dash="dash"),
    ))
    fig.update_xaxes(title_text="理论分位数 (%)")
    fig.update_yaxes(title_text="实际分位数 (%)")
    return fig


def plot_scatter_with_regression(x, y, x_label="X", y_label="Y", title="散点图", alpha=None, beta=None):
    """绘制散点图 + 回归线"""
    fig = create_figure(title=title)
    fig.add_trace(go.Scatter(
        x=x * 100, y=y * 100, mode="markers", name="数据点",
        marker=dict(color=COLORS["primary"], size=4, opacity=0.4),
    ))
    if beta is not None:
        xl = np.linspace(x.min(), x.max(), 100)
        yl = alpha + beta * xl
        fig.add_trace(go.Scatter(
            x=xl * 100, y=yl * 100, mode="lines", name=f"回归线 (β={beta:.3f})",
            line=dict(color=COLORS["danger"], width=2),
        ))
    fig.update_xaxes(title_text=f"{x_label} (%)")
    fig.update_yaxes(title_text=f"{y_label} (%)")
    return fig


def plot_rolling_metric(df, col, title="滚动指标", y_label="值"):
    """绘制滚动指标曲线"""
    fig = create_figure(title=title)
    if col in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df[col], mode="lines", name=col,
            line=dict(color=COLORS["primary"], width=1.5),
        ))
    fig.update_yaxes(title_text=y_label)
    return fig


def plot_var_threshold(df, var_95, var_99, title="VaR 阈值与收益率"):
    """绘制收益率与 VaR 阈值"""
    fig = create_figure(title=title)
    if "simple_return" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["simple_return"] * 100, mode="lines", name="日收益率",
            line=dict(color=COLORS["primary"], width=0.8, opacity=0.6),
        ))
    fig.add_hline(y=var_95 * 100, line_dash="dash", line_color=COLORS["warning"],
                  annotation_text=f"VaR 95%: {var_95*100:.2f}%")
    fig.add_hline(y=var_99 * 100, line_dash="dash", line_color=COLORS["danger"],
                  annotation_text=f"VaR 99%: {var_99*100:.2f}%")
    fig.update_yaxes(title_text="收益率 (%)")
    return fig


def plot_acf_pacf(acf_vals, pacf_vals, title="ACF / PACF"):
    """绘制 ACF/PACF 图"""
    fig = make_subplots(rows=1, cols=2, subplot_titles=["自相关函数 (ACF)", "偏自相关函数 (PACF)"])
    lags = np.arange(len(acf_vals))
    ci = 1.96 / np.sqrt(max(len(acf_vals), 1))
    for i, (vals, name, color) in enumerate([
        (acf_vals, "ACF", COLORS["primary"]),
        (pacf_vals, "PACF", COLORS["secondary"]),
    ]):
        fig.add_trace(go.Bar(x=lags, y=vals, name=name, marker_color=color), row=1, col=i + 1)
        fig.add_hline(y=ci, line_dash="dash", line_color="red", row=1, col=i + 1)
        fig.add_hline(y=-ci, line_dash="dash", line_color="red", row=1, col=i + 1)
    layout = get_layout(title=title, height=400)
    fig.update_layout(**layout)
    return fig


def plot_radar(scores: dict, title: str = "综合评分雷达图") -> go.Figure:
    """绘制雷达图"""
    cats = list(scores.keys())
    vals = list(scores.values())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]],
        fill="toself", fillcolor="rgba(31,119,180,0.3)",
        line=dict(color=COLORS["primary"], width=2), name="评分",
    ))
    layout = get_layout(title=title, height=500, width=500)
    layout["polar"] = {
        "radialaxis": {"visible": True, "range": [0, 100]},
        "angularaxis": {"tickfont": {"family": FONT_FAMILY, "size": 11}},
    }
    fig.update_layout(**layout)
    return fig


def plot_strategy_comparison(strategy_nv, benchmark_nv, dates,
                             strategy_name="策略", benchmark_name="买入持有", title="策略回测对比"):
    """绘制策略净值对比图"""
    fig = create_figure(title=title)
    fig.add_trace(go.Scatter(
        x=dates, y=strategy_nv, mode="lines", name=strategy_name,
        line=dict(color=COLORS["primary"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=benchmark_nv, mode="lines", name=benchmark_name,
        line=dict(color=COLORS["benchmark"], width=2, dash="dash"),
    ))
    fig.update_yaxes(title_text="净值")
    return fig