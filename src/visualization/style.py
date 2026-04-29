"""可视化样式配置 - 中文主题、颜色、字体配置"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ===== 中文字体配置 =====
FONT_FAMILY = "Microsoft YaHei, SimHei, PingFang SC, Arial, sans-serif"

# ===== 颜色方案 =====
COLORS = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e",
    "success": "#2ca02c",
    "danger": "#d62728",
    "warning": "#ff9800",
    "info": "#17a2b8",
    "up": "#d62728",       # A股 涨为红
    "down": "#2ca02c",     # A股 跌为绿
    "stock": "#1f77b4",
    "benchmark": "#ff7f0e",
    "neutral": "#7f7f7f",
}

# 多色循环
COLOR_CYCLE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


def get_layout(title: str = "", height: int = 500, width: int = None) -> dict:
    """获取标准 Plotly 布局配置

    Args:
        title: 图表标题
        height: 图表高度
        width: 图表宽度

    Returns:
        layout 字典
    """
    layout = {
        "title": {
            "text": title,
            "font": {"family": FONT_FAMILY, "size": 16},
            "x": 0.5,
            "xanchor": "center",
        },
        "font": {"family": FONT_FAMILY, "size": 12},
        "template": "plotly_white",
        "height": height,
        "margin": {"l": 60, "r": 30, "t": 60, "b": 50},
        "legend": {
            "font": {"family": FONT_FAMILY, "size": 11},
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
        },
        "xaxis": {
            "title": {"font": {"family": FONT_FAMILY, "size": 12}},
            "tickfont": {"family": FONT_FAMILY, "size": 10},
        },
        "yaxis": {
            "title": {"font": {"family": FONT_FAMILY, "size": 12}},
            "tickfont": {"family": FONT_FAMILY, "size": 10},
        },
    }
    if width:
        layout["width"] = width
    return layout


def create_figure(title: str = "", height: int = 500, **kwargs) -> go.Figure:
    """创建标准 Figure

    Args:
        title: 图表标题
        height: 图表高度

    Returns:
        配置好的 go.Figure
    """
    fig = go.Figure()
    layout = get_layout(title=title, height=height, **kwargs)
    fig.update_layout(**layout)
    return fig


def create_subplots(
    rows: int, cols: int,
    titles: list[str] = None,
    height: int = 600,
    title: str = "",
    **kwargs,
) -> go.Figure:
    """创建子图

    Args:
        rows: 行数
        cols: 列数
        titles: 子图标题列表
        height: 图表高度
        title: 主标题
    """
    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=titles,
        **kwargs,
    )
    layout = get_layout(title=title, height=height)
    fig.update_layout(**layout)
    return fig


def format_number(value: float, decimals: int = 4, percent: bool = False) -> str:
    """格式化数字

    Args:
        value: 数值
        decimals: 小数位数
        percent: 是否百分比显示
    """
    if value is None:
        return "N/A"
    try:
        if percent:
            return f"{value * 100:.{decimals - 2}f}%"
        if abs(value) >= 1e8:
            return f"{value / 1e8:.{decimals}f}亿"
        if abs(value) >= 1e4:
            return f"{value / 1e4:.{decimals}f}万"
        return f"{value:.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)