"""Data schema definitions using Pydantic."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class StockInfo(BaseModel):
    """Stock basic info."""
    stock_code: str
    symbol: str
    stock_name: str
    exchange: str  # SH, SZ, BJ
    board: Optional[str] = None  # 主板, 创业板, 科创板, 北交所
    industry: Optional[str] = None
    area: Optional[str] = None
    list_date: Optional[str] = None
    is_st: bool = False
    is_active: bool = True
    data_source: str = "akshare"
    updated_at: Optional[datetime] = None


class DailyBar(BaseModel):
    """Daily bar data."""
    trade_date: date
    stock_code: str
    open: float
    high: float
    low: float
    close: float
    pre_close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None
    pct_chg: Optional[float] = None
    adj_factor: Optional[float] = None
    adj_close: Optional[float] = None


class DailyBasic(BaseModel):
    """Daily basic indicators."""
    trade_date: date
    stock_code: str
    turnover_rate: Optional[float] = None
    turnover_rate_f: Optional[float] = None
    volume_ratio: Optional[float] = None
    pe: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    ps_ttm: Optional[float] = None
    total_share: Optional[float] = None
    float_share: Optional[float] = None
    free_share: Optional[float] = None
    total_mv: Optional[float] = None
    circ_mv: Optional[float] = None
    dividend_yield: Optional[float] = None


class FeatureStoreMeta(BaseModel):
    """Feature store metadata."""
    latest_trade_date: Optional[date] = None
    stock_count: int = 0
    feature_count: int = 0
    updated_at: Optional[datetime] = None
    data_source: str = ""
    history_years: int = 3


__all__ = ["StockInfo", "DailyBar", "DailyBasic", "FeatureStoreMeta"]
