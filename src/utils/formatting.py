"""Number and currency formatting utilities."""

import pandas as pd
import numpy as np


def fmt_pct(value: float, decimals: int = 2) -> str:
    """Format as percentage string."""
    if pd.isna(value) or value is None:
        return "-"
    return f"{value * 100:.{decimals}f}%"


def fmt_pct_raw(value: float, decimals: int = 2) -> str:
    """Format a value already in percentage units."""
    if pd.isna(value) or value is None:
        return "-"
    return f"{value:.{decimals}f}%"


def fmt_yi(value: float, decimals: int = 2) -> str:
    """Format value in 亿元 (100M CNY)."""
    if pd.isna(value) or value is None:
        return "-"
    yi = value / 1e8
    return f"{yi:.{decimals}f}亿"


def fmt_wan(value: float, decimals: int = 2) -> str:
    """Format value in 万元 (10K CNY)."""
    if pd.isna(value) or value is None:
        return "-"
    wan = value / 1e4
    return f"{wan:.{decimals}f}万"


def fmt_number(value: float, decimals: int = 2) -> str:
    """Format a number with fixed decimals."""
    if pd.isna(value) or value is None:
        return "-"
    return f"{value:.{decimals}f}"


def fmt_score(value: float) -> str:
    """Format score with 1 decimal."""
    if pd.isna(value) or value is None:
        return "-"
    return f"{value:.1f}"


def fmt_mv(value: float) -> str:
    """Format market value: use 亿 for >= 1e8, 万 for >= 1e4."""
    if pd.isna(value) or value is None:
        return "-"
    if abs(value) >= 1e8:
        return f"{value / 1e8:.2f}亿"
    if abs(value) >= 1e4:
        return f"{value / 1e4:.2f}万"
    return f"{value:.2f}"


# Column display config: (display_name, format_func, width)
COLUMN_FORMAT = {
    # 基础信息
    "stock_code": ("股票代码", None, 100),
    "symbol": ("代码", None, 80),
    "stock_name": ("股票名称", None, 100),
    "exchange": ("交易所", None, 60),
    "board": ("板块", None, 80),
    "industry": ("行业", None, 100),
    "area": ("地域", None, 60),
    "list_date": ("上市日期", None, 90),
    "is_st": ("是否ST", None, 60),
    "listing_days": ("上市天数", None, 70),
    # 价格
    "latest_close": ("最新价", fmt_number, 80),
    "latest_open": ("今开", fmt_number, 70),
    "latest_high": ("最高", fmt_number, 70),
    "latest_low": ("最低", fmt_number, 70),
    "latest_pct_chg": ("涨跌幅", fmt_pct_raw, 80),
    "latest_trade_date": ("数据日期", None, 90),
    # 市值与估值
    "total_mv": ("总市值(万元)", fmt_mv, 100),
    "circ_mv": ("流通市值(万元)", fmt_mv, 100),
    "pe": ("PE", fmt_number, 70),
    "pe_ttm": ("PE(TTM)", fmt_number, 80),
    "pb": ("PB", fmt_number, 70),
    "ps": ("PS", fmt_number, 70),
    "ps_ttm": ("PS(TTM)", fmt_number, 80),
    "dividend_yield": ("股息率(%)", fmt_pct_raw, 80),
    "turnover_rate": ("换手率(%)", fmt_pct_raw, 80),
    "turnover_rate_latest": ("最新换手率(%)", fmt_pct_raw, 90),
    "volume_ratio": ("量比", fmt_number, 60),
    # 收益率
    "ret_1d": ("1日收益", fmt_pct, 80),
    "ret_3d": ("3日收益", fmt_pct, 80),
    "ret_5d": ("5日收益", fmt_pct, 80),
    "ret_10d": ("10日收益", fmt_pct, 80),
    "ret_20d": ("20日收益", fmt_pct, 80),
    "ret_60d": ("60日收益", fmt_pct, 80),
    "ret_120d": ("120日收益", fmt_pct, 80),
    "ret_252d": ("252日收益", fmt_pct, 80),
    # 风险
    "volatility_20d": ("20日波动率", fmt_pct, 90),
    "volatility_60d": ("60日波动率", fmt_pct, 90),
    "volatility_120d": ("120日波动率", fmt_pct, 90),
    "volatility_252d": ("252日波动率", fmt_pct, 90),
    "max_drawdown_20d": ("20日最大回撤", fmt_pct, 90),
    "max_drawdown_60d": ("60日最大回撤", fmt_pct, 90),
    "max_drawdown_120d": ("120日最大回撤", fmt_pct, 100),
    "max_drawdown_252d": ("252日最大回撤", fmt_pct, 100),
    "beta_120d": ("Beta(120日)", fmt_number, 80),
    "beta_252d": ("Beta(252日)", fmt_number, 80),
    "sharpe_120d": ("Sharpe(120日)", fmt_number, 90),
    "sharpe_252d": ("Sharpe(252日)", fmt_number, 90),
    "sortino_120d": ("Sortino(120日)", fmt_number, 90),
    "calmar_252d": ("Calmar(252日)", fmt_number, 90),
    "var_95_120d": ("VaR(95%)", fmt_pct, 80),
    "cvar_95_120d": ("CVaR(95%)", fmt_pct, 80),
    # 流动性
    "avg_volume_5d": ("5日均量", fmt_number, 80),
    "avg_volume_20d": ("20日均量", fmt_number, 80),
    "avg_volume_60d": ("60日均量", fmt_number, 80),
    "avg_amount_5d": ("5日均额", fmt_yi, 80),
    "avg_amount_20d": ("20日均额(万元)", fmt_yi, 100),
    "avg_amount_60d": ("60日均额", fmt_yi, 90),
    "turnover_rate_5d": ("5日换手率(%)", fmt_pct_raw, 90),
    "turnover_rate_20d": ("20日换手率(%)", fmt_pct_raw, 100),
    "turnover_rate_60d": ("60日换手率(%)", fmt_pct_raw, 90),
    "amount_ratio_20d": ("成交额比(20日)", fmt_number, 90),
    "amihud_illiquidity_20d": ("Amihud非流动性", fmt_number, 100),
    # 基本面
    "roe": ("ROE(%)", fmt_pct_raw, 70),
    "roa": ("ROA(%)", fmt_pct_raw, 70),
    "gross_margin": ("毛利率(%)", fmt_pct_raw, 80),
    "net_margin": ("净利率(%)", fmt_pct_raw, 80),
    "operating_margin": ("营业利润率(%)", fmt_pct_raw, 90),
    "revenue_growth_yoy": ("营收同比增长(%)", fmt_pct_raw, 100),
    "net_profit_growth_yoy": ("净利润同比增长(%)", fmt_pct_raw, 110),
    "debt_to_asset": ("资产负债率(%)", fmt_pct_raw, 90),
    "current_ratio": ("流动比率", fmt_number, 70),
    "quick_ratio": ("速动比率", fmt_number, 70),
    "eps": ("每股收益", fmt_number, 70),
    "bps": ("每股净资产", fmt_number, 80),
    # 技术指标
    "ma5": ("MA5", fmt_number, 60),
    "ma10": ("MA10", fmt_number, 60),
    "ma20": ("MA20", fmt_number, 60),
    "ma60": ("MA60", fmt_number, 60),
    "ma120": ("MA120", fmt_number, 70),
    "ma250": ("MA250", fmt_number, 70),
    "rsi_6": ("RSI(6)", fmt_number, 70),
    "rsi_14": ("RSI(14)", fmt_number, 70),
    "rsi_24": ("RSI(24)", fmt_number, 70),
    "macd": ("MACD", fmt_number, 70),
    "macd_signal": ("MACD信号", fmt_number, 70),
    "macd_hist": ("MACD柱", fmt_number, 70),
    "bollinger_position": ("布林位置", fmt_number, 70),
    "atr_14": ("ATR(14)", fmt_number, 70),
    "price_above_ma20": ("站上MA20", None, 70),
    "price_above_ma60": ("站上MA60", None, 70),
    "is_ma_bullish": ("均线多头", None, 70),
    "macd_golden_cross": ("MACD金叉", None, 70),
    "new_high_20d": ("20日新高", None, 70),
    "new_high_60d": ("60日新高", None, 70),
    "new_low_60d": ("60日新低", None, 70),
    # 评分
    "total_score": ("综合评分", fmt_score, 80),
    "return_score": ("收益评分", fmt_score, 80),
    "risk_score": ("风险评分", fmt_score, 80),
    "liquidity_score": ("流动性评分", fmt_score, 90),
    "value_score": ("估值评分", fmt_score, 80),
    "quality_score": ("质量评分", fmt_score, 80),
    "growth_score": ("成长评分", fmt_score, 80),
    "technical_score": ("技术评分", fmt_score, 80),
    "moneyflow_score": ("资金流评分", fmt_score, 80),
    "data_quality_score": ("数据质量评分", fmt_score, 90),
    # 其他
    "reasons": ("入选原因", None, 200),
    "risks": ("风险提示", None, 200),
    "data_warnings": ("数据警告", None, 150),
}


def get_column_rename_map(columns: list[str] = None) -> dict:
    """Return a dict mapping column names to Chinese display names.

    Args:
        columns: If provided, only return mappings for these columns.
                 If None, return all mappings.
    """
    if columns is None:
        return {k: v[0] for k, v in COLUMN_FORMAT.items()}
    return {col: COLUMN_FORMAT[col][0] for col in columns if col in COLUMN_FORMAT}


def get_display_columns(df: pd.DataFrame) -> dict:
    """Return mapping of column names to display names for columns present in df."""
    return {col: COLUMN_FORMAT[col][0] for col in df.columns if col in COLUMN_FORMAT}


__all__ = [
    "fmt_pct", "fmt_pct_raw", "fmt_yi", "fmt_wan", "fmt_number",
    "fmt_score", "fmt_mv", "COLUMN_FORMAT", "get_display_columns",
    "get_column_rename_map",
]
