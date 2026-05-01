"""AKShare data fetching functions with rate limiting and error handling."""

import time
from typing import Optional

import pandas as pd
import numpy as np

from src.utils.logger import logger

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    logger.warning("akshare not installed. Data fetching will not work.")

# Rate limiting
_last_request_time = 0.0
DEFAULT_DELAY = 0.3


def _rate_limit(delay: float = DEFAULT_DELAY):
    """Simple rate limiter."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < delay:
        time.sleep(delay - elapsed)
    _last_request_time = time.time()


def _safe_call(func, *args, retries: int = 3, delay: float = DEFAULT_DELAY, **kwargs) -> Optional[pd.DataFrame]:
    """Call an AKShare function with retries and rate limiting."""
    if not HAS_AKSHARE:
        logger.error("akshare not installed")
        return None

    for attempt in range(retries):
        try:
            _rate_limit(delay * (2 ** attempt))  # exponential backoff
            result = func(*args, **kwargs)
            if result is not None and len(result) > 0:
                return result
            logger.warning(f"Empty result from {func.__name__}, attempt {attempt + 1}")
        except Exception as e:
            logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay * (2 ** attempt))

    logger.error(f"{func.__name__} failed after {retries} attempts")
    return None


def normalize_code(symbol: str) -> tuple[str, str]:
    """Normalize stock code to (stock_code, exchange).

    Args:
        symbol: e.g. "300658", "300658.SZ", "600519"

    Returns:
        (stock_code, exchange) e.g. ("300658.SZ", "SZ")
    """
    symbol = symbol.strip()

    # Already has exchange suffix
    if "." in symbol:
        parts = symbol.split(".")
        return symbol, parts[1]

    # Determine exchange from prefix
    if symbol.startswith(("60", "68")):
        return f"{symbol}.SH", "SH"
    elif symbol.startswith(("00", "30")):
        return f"{symbol}.SZ", "SZ"
    elif symbol.startswith(("4", "8")):
        return f"{symbol}.BJ", "BJ"
    else:
        # Default to SZ
        return f"{symbol}.SZ", "SZ"


def extract_symbol(stock_code: str) -> str:
    """Extract pure symbol from stock_code. e.g. '300658.SZ' -> '300658'."""
    return stock_code.split(".")[0] if "." in stock_code else stock_code


def detect_board(symbol: str) -> str:
    """Detect board from stock code prefix."""
    if symbol.startswith("60"):
        return "沪市主板"
    elif symbol.startswith("00"):
        return "深市主板"
    elif symbol.startswith("30"):
        return "创业板"
    elif symbol.startswith("68"):
        return "科创板"
    elif symbol.startswith(("4", "8")):
        return "北交所"
    return "未知"


# ============================================================
# Stock List
# ============================================================

def fetch_stock_list() -> Optional[pd.DataFrame]:
    """Fetch A-share stock list with basic info.

    Returns DataFrame with columns:
        stock_code, symbol, stock_name, exchange, board, industry, list_date, is_st
    """
    logger.info("Fetching A-share stock list...")

    # Try ak.stock_info_a_code_name()
    df = _safe_call(ak.stock_info_a_code_name)
    if df is None:
        return None

    # Normalize column names
    col_map = {}
    for col in df.columns:
        cl = col.lower()
        if "代码" in cl or "code" in cl:
            col_map[col] = "symbol"
        elif "名称" in cl or "name" in cl:
            col_map[col] = "stock_name"
    df = df.rename(columns=col_map)

    if "symbol" not in df.columns or "stock_name" not in df.columns:
        logger.error(f"Unexpected stock list columns: {df.columns.tolist()}")
        return None

    # Add derived columns
    df["stock_code"] = df["symbol"].apply(lambda x: normalize_code(x)[0])
    df["exchange"] = df["symbol"].apply(lambda x: normalize_code(x)[1])
    df["board"] = df["symbol"].apply(detect_board)

    # Try to get industry info
    industry_df = _fetch_stock_industry()
    if industry_df is not None:
        df = df.merge(industry_df[["symbol", "industry", "area", "list_date"]], on="symbol", how="left")

    # ST detection — try to detect from name
    df["is_st"] = df["stock_name"].str.contains(r"ST|st|\*ST", case=False, na=False).astype(int)
    df["is_active"] = 1
    df["data_source"] = "akshare"
    df["updated_at"] = pd.Timestamp.now()

    logger.info(f"Fetched {len(df)} stocks")
    return df


def _fetch_stock_industry() -> Optional[pd.DataFrame]:
    """Fetch stock industry info from akshare."""
    try:
        df = _safe_call(ak.stock_board_industry_name_em)
        if df is None:
            return None

        # This gives industry boards, not per-stock. Try alternative.
        # Use stock_individual_info_em for each stock is too slow.
        # Try stock_zh_a_spot_em for spot data with industry
        spot_df = _safe_call(ak.stock_zh_a_spot_em)
        if spot_df is None:
            return None

        col_map = {}
        for col in spot_df.columns:
            cl = col.lower()
            if "代码" in cl:
                col_map[col] = "symbol"
            elif "行业" in cl or "industry" in cl:
                col_map[col] = "industry"
            elif "地域" in cl or "area" in cl:
                col_map[col] = "area"
            elif "上市日期" in cl or "上市时间" in cl:
                col_map[col] = "list_date"
        spot_df = spot_df.rename(columns=col_map)

        if "symbol" in spot_df.columns:
            keep_cols = [c for c in ["symbol", "industry", "area", "list_date"] if c in spot_df.columns]
            return spot_df[keep_cols].drop_duplicates(subset=["symbol"])

    except Exception as e:
        logger.warning(f"Failed to fetch industry info: {e}")

    return None


def fetch_stock_list_with_spot() -> Optional[pd.DataFrame]:
    """Fetch stock list with real-time spot data (includes industry, market cap, etc.)."""
    logger.info("Fetching stock list with spot data...")

    spot_df = _safe_call(ak.stock_zh_a_spot_em)
    if spot_df is None:
        return None

    # Normalize column names
    col_map = {}
    for col in spot_df.columns:
        cl = col.lower()
        if "代码" in cl:
            col_map[col] = "symbol"
        elif "名称" in cl:
            col_map[col] = "stock_name"
        elif "行业" in cl:
            col_map[col] = "industry"
        elif "地域" in cl:
            col_map[col] = "area"
        elif "最新价" in cl:
            col_map[col] = "latest_close"
        elif "涨跌幅" in cl:
            col_map[col] = "pct_chg"
        elif "成交额" in cl:
            col_map[col] = "amount"
        elif "总市值" in cl:
            col_map[col] = "total_mv"
        elif "流通市值" in cl:
            col_map[col] = "circ_mv"
        elif "市盈率" in cl and "动态" in cl:
            col_map[col] = "pe_ttm"
        elif "市净率" in cl:
            col_map[col] = "pb"
        elif "换手率" in cl:
            col_map[col] = "turnover_rate"
        elif "量比" in cl:
            col_map[col] = "volume_ratio"
    spot_df = spot_df.rename(columns=col_map)

    if "symbol" not in spot_df.columns:
        logger.error(f"Spot data columns: {spot_df.columns.tolist()}")
        return None

    # Add standard columns
    spot_df["stock_code"] = spot_df["symbol"].apply(lambda x: normalize_code(str(x))[0])
    spot_df["exchange"] = spot_df["symbol"].apply(lambda x: normalize_code(str(x))[1])
    spot_df["board"] = spot_df["symbol"].apply(lambda x: detect_board(str(x)))
    spot_df["is_st"] = spot_df["stock_name"].astype(str).str.contains(r"ST|st|\*ST", case=False, na=False).astype(int)
    spot_df["is_active"] = 1
    spot_df["data_source"] = "akshare"
    spot_df["updated_at"] = pd.Timestamp.now()

    logger.info(f"Fetched spot data for {len(spot_df)} stocks")
    return spot_df


# ============================================================
# Daily Bars
# ============================================================

def fetch_daily_bars(
    symbol: str,
    start_date: str = "20230101",
    end_date: str = "",
    adjust: str = "qfq",
) -> Optional[pd.DataFrame]:
    """Fetch daily OHLCV for a single stock.

    Args:
        symbol: Pure symbol like "300658" or stock_code like "300658.SZ"
        start_date: YYYYMMDD
        end_date: YYYYMMDD
        adjust: "qfq" (前复权), "hfq" (后复权), "" (不复权)
    """
    sym = extract_symbol(symbol)

    try:
        df = _safe_call(
            ak.stock_zh_a_hist,
            symbol=sym,
            period="daily",
            start_date=start_date,
            end_date=end_date or pd.Timestamp.now().strftime("%Y%m%d"),
            adjust=adjust,
        )

        if df is None or len(df) == 0:
            return None

        # Normalize columns
        col_map = {}
        for col in df.columns:
            cl = col.lower()
            if "日期" in cl or "date" in cl:
                col_map[col] = "trade_date"
            elif "开盘" in cl:
                col_map[col] = "open"
            elif "最高" in cl:
                col_map[col] = "high"
            elif "最低" in cl:
                col_map[col] = "low"
            elif "收盘" in cl:
                col_map[col] = "close"
            elif "成交量" in cl:
                col_map[col] = "volume"
            elif "成交额" in cl:
                col_map[col] = "amount"
            elif "涨跌幅" in cl:
                col_map[col] = "pct_chg"
            elif "涨跌额" in cl:
                col_map[col] = "change"
            elif "换手率" in cl:
                col_map[col] = "turnover_rate"
        df = df.rename(columns=col_map)

        # Add stock_code
        stock_code, _ = normalize_code(symbol)
        df["stock_code"] = stock_code
        df["trade_date"] = pd.to_datetime(df["trade_date"])

        # Convert pct_chg to decimal if it's in percentage
        if "pct_chg" in df.columns:
            if df["pct_chg"].abs().max() > 1:
                df["pct_chg"] = df["pct_chg"] / 100.0

        # Sort by date
        df = df.sort_values("trade_date").reset_index(drop=True)

        return df

    except Exception as e:
        logger.error(f"Failed to fetch daily bars for {symbol}: {e}")
        return None


# ============================================================
# Daily Basic Indicators
# ============================================================

def fetch_daily_basic(date: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Fetch daily basic indicators for all stocks on a given date.

    Uses ak.stock_zh_a_spot_em as a proxy for latest basic indicators.
    """
    logger.info("Fetching daily basic indicators...")

    # Use spot data as proxy for latest basics
    spot_df = _safe_call(ak.stock_zh_a_spot_em)
    if spot_df is None:
        return None

    # Normalize columns
    col_map = {}
    for col in spot_df.columns:
        cl = col.lower()
        if "代码" in cl:
            col_map[col] = "symbol"
        elif "名称" in cl:
            col_map[col] = "stock_name"
        elif "最新价" in cl:
            col_map[col] = "close"
        elif "涨跌幅" in cl:
            col_map[col] = "pct_chg"
        elif "成交量" in cl:
            col_map[col] = "volume"
        elif "成交额" in cl:
            col_map[col] = "amount"
        elif "振幅" in cl:
            col_map[col] = "amplitude"
        elif "最高" in cl:
            col_map[col] = "high"
        elif "最低" in cl:
            col_map[col] = "low"
        elif "今开" in cl:
            col_map[col] = "open"
        elif "昨收" in cl:
            col_map[col] = "pre_close"
        elif "换手率" in cl:
            col_map[col] = "turnover_rate"
        elif "量比" in cl:
            col_map[col] = "volume_ratio"
        elif "市盈率" in cl and "动态" in cl:
            col_map[col] = "pe_ttm"
        elif "市盈率" in cl:
            col_map[col] = "pe"
        elif "市净率" in cl:
            col_map[col] = "pb"
        elif "总市值" in cl:
            col_map[col] = "total_mv"
        elif "流通市值" in cl:
            col_map[col] = "circ_mv"
        elif "市销率" in cl and "动态" in cl:
            col_map[col] = "ps_ttm"
        elif "市销率" in cl:
            col_map[col] = "ps"
    spot_df = spot_df.rename(columns=col_map)

    if "symbol" not in spot_df.columns:
        logger.error(f"Spot data columns: {spot_df.columns.tolist()}")
        return None

    # Add stock_code
    spot_df["stock_code"] = spot_df["symbol"].apply(lambda x: normalize_code(str(x))[0])
    spot_df["trade_date"] = pd.Timestamp.now().normalize()

    logger.info(f"Fetched basic indicators for {len(spot_df)} stocks")
    return spot_df


# ============================================================
# Index Data
# ============================================================

INDEX_MAP = {
    "hs300": ("000300", "沪深300"),
    "zz500": ("000905", "中证500"),
    "zz1000": ("000852", "中证1000"),
    "sh_composite": ("000001", "上证指数"),
    "sz_component": ("399001", "深证成指"),
    "gem": ("399006", "创业板指"),
    "star50": ("000688", "科创50"),
}


def fetch_index_daily(
    index_code: str = "000300",
    start_date: str = "20230101",
    end_date: str = "",
) -> Optional[pd.DataFrame]:
    """Fetch daily data for an index."""
    logger.info(f"Fetching index {index_code} daily data...")

    try:
        df = _safe_call(
            ak.stock_zh_index_daily_em,
            symbol=f"sh{index_code}" if index_code.startswith("0") else f"sz{index_code}",
        )

        if df is None or len(df) == 0:
            # Try alternative
            df = _safe_call(ak.index_zh_a_hist, symbol=index_code, period="daily",
                          start_date=start_date,
                          end_date=end_date or pd.Timestamp.now().strftime("%Y%m%d"))

        if df is None or len(df) == 0:
            return None

        # Normalize columns
        col_map = {}
        for col in df.columns:
            cl = col.lower()
            if "日期" in cl or "date" in cl:
                col_map[col] = "trade_date"
            elif "开盘" in cl:
                col_map[col] = "open"
            elif "最高" in cl:
                col_map[col] = "high"
            elif "最低" in cl:
                col_map[col] = "low"
            elif "收盘" in cl:
                col_map[col] = "close"
            elif "成交量" in cl:
                col_map[col] = "volume"
            elif "成交额" in cl:
                col_map[col] = "amount"
        df = df.rename(columns=col_map)

        df["index_code"] = index_code
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date").reset_index(drop=True)

        # Filter by date
        if start_date:
            df = df[df["trade_date"] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df["trade_date"] <= pd.Timestamp(end_date)]

        return df

    except Exception as e:
        logger.error(f"Failed to fetch index {index_code}: {e}")
        return None


def fetch_index_components(index_name: str = "hs300") -> Optional[list[str]]:
    """Fetch index constituent stock codes."""
    code_map = {
        "hs300": "000300",
        "zz500": "000905",
        "zz1000": "000852",
    }
    idx_code = code_map.get(index_name)
    if not idx_code:
        logger.warning(f"Unknown index: {index_name}")
        return None

    try:
        df = _safe_call(ak.index_stock_cons, symbol=idx_code)
        if df is None:
            return None

        # Find code column
        for col in df.columns:
            if "代码" in col or "code" in col.lower():
                return df[col].tolist()

    except Exception as e:
        logger.warning(f"Failed to fetch {index_name} components: {e}")

    return None


# ============================================================
# Financial Data (best effort)
# ============================================================

def fetch_financial_indicator(symbol: str) -> Optional[pd.DataFrame]:
    """Fetch financial indicators for a single stock (best effort)."""
    sym = extract_symbol(symbol)

    # Try new THS format first (returns long-format metrics)
    try:
        df = _safe_call(ak.stock_financial_abstract_new_ths, symbol=sym, indicator="按报告期")
        if df is not None and len(df) > 0:
            df["symbol"] = sym
            return df
    except Exception as e:
        logger.debug(f"Financial abstract (new ths) failed for {sym}: {e}")

    # Fallback: old format (returns wide-format with date columns)
    try:
        df = _safe_call(ak.stock_financial_abstract, symbol=sym)
        if df is not None and len(df) > 0:
            df["symbol"] = sym
            return df
    except Exception as e:
        logger.debug(f"Financial abstract (old) failed for {sym}: {e}")

    return None


def fetch_moneyflow(symbol: str) -> Optional[pd.DataFrame]:
    """Fetch money flow data for a single stock (best effort)."""
    sym = extract_symbol(symbol)

    try:
        df = _safe_call(ak.stock_individual_fund_flow, stock=sym, market="sz" if sym.startswith(("0", "3")) else "sh")
        if df is not None and len(df) > 0:
            df["symbol"] = sym
            return df
    except Exception as e:
        logger.debug(f"Money flow failed for {sym}: {e}")

    return None


__all__ = [
    "fetch_stock_list", "fetch_stock_list_with_spot",
    "fetch_daily_bars", "fetch_daily_basic",
    "fetch_index_daily", "fetch_index_components",
    "fetch_financial_indicator", "fetch_moneyflow",
    "normalize_code", "extract_symbol", "detect_board",
    "INDEX_MAP",
]
