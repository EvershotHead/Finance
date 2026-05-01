"""Factor calculation library — all screening factors organized by category."""

from typing import Optional

import pandas as pd
import numpy as np

from src.utils.logger import logger


# ============================================================
# Price Factors
# ============================================================

def price_position_52w(high_252d: float, low_252d: float, close: float) -> Optional[float]:
    """Current price position in 52-week range [0, 1]."""
    if pd.isna(high_252d) or pd.isna(low_252d) or high_252d == low_252d:
        return None
    return (close - low_252d) / (high_252d - low_252d)


def distance_to_high(close: float, high: float) -> Optional[float]:
    """Distance from current price to a high. Negative means below high."""
    if pd.isna(high) or high == 0:
        return None
    return (close - high) / high


def distance_to_low(close: float, low: float) -> Optional[float]:
    """Distance from current price to a low."""
    if pd.isna(low) or low == 0:
        return None
    return (close - low) / low


# ============================================================
# Return Factors
# ============================================================

def compute_returns(close_series: pd.Series, windows: list[int]) -> dict[str, Optional[float]]:
    """Compute returns for multiple windows from a close price series."""
    result = {}
    n = len(close_series)
    for w in windows:
        col_name = f"ret_{w}d"
        if n > w and close_series.iloc[-w - 1] != 0:
            result[col_name] = close_series.iloc[-1] / close_series.iloc[-w - 1] - 1
        else:
            result[col_name] = None
    return result


def momentum(close_series: pd.Series, window: int) -> Optional[float]:
    """Momentum = return over window."""
    n = len(close_series)
    if n <= window or close_series.iloc[-window - 1] == 0:
        return None
    return close_series.iloc[-1] / close_series.iloc[-window - 1] - 1


def relative_strength(stock_returns: pd.Series, bench_returns: pd.Series, window: int) -> Optional[float]:
    """Relative strength vs benchmark over window."""
    if len(stock_returns) < window or len(bench_returns) < window:
        return None
    stock_ret = stock_returns.iloc[-window:].sum()
    bench_ret = bench_returns.iloc[-window:].sum()
    return stock_ret - bench_ret


def ytd_return(close_series: pd.Series, trade_dates: pd.Series) -> Optional[float]:
    """Year-to-date return."""
    year_start = pd.Timestamp(f"{pd.Timestamp.now().year}-01-01")
    mask = trade_dates >= year_start
    if mask.sum() < 2:
        return None
    first = close_series[mask].iloc[0]
    last = close_series.iloc[-1]
    if first == 0:
        return None
    return last / first - 1


# ============================================================
# Risk Factors
# ============================================================

def volatility(returns: pd.Series, window: int, annualize: bool = True) -> Optional[float]:
    """Annualized volatility over window."""
    if len(returns) < window:
        return None
    vol = returns.iloc[-window:].std()
    if annualize:
        vol *= np.sqrt(252)
    return vol


def downside_volatility(returns: pd.Series, window: int, threshold: float = 0.0) -> Optional[float]:
    """Downside volatility (only negative returns)."""
    if len(returns) < window:
        return None
    r = returns.iloc[-window:]
    downside = r[r < threshold]
    if len(downside) < 5:
        return 0.0
    return downside.std() * np.sqrt(252)


def max_drawdown(close_series: pd.Series, window: int) -> Optional[float]:
    """Maximum drawdown over window (negative value)."""
    n = len(close_series)
    if n < window:
        return None
    prices = close_series.iloc[-window:]
    peak = prices.cummax()
    drawdown = (prices - peak) / peak
    return drawdown.min()


def var_95(returns: pd.Series, window: int) -> Optional[float]:
    """Value at Risk (95%) over window."""
    if len(returns) < window:
        return None
    return returns.iloc[-window:].quantile(0.05)


def cvar_95(returns: pd.Series, window: int) -> Optional[float]:
    """Conditional VaR (95%) over window."""
    if len(returns) < window:
        return None
    r = returns.iloc[-window:]
    var = r.quantile(0.05)
    return r[r <= var].mean() if (r <= var).any() else var


def beta(stock_returns: pd.Series, bench_returns: pd.Series, window: int) -> Optional[float]:
    """Beta relative to benchmark over window."""
    if len(stock_returns) < window or len(bench_returns) < window:
        return None
    s = stock_returns.iloc[-window:]
    b = bench_returns.iloc[-window:]
    # Align
    min_len = min(len(s), len(b))
    s = s.iloc[-min_len:]
    b = b.iloc[-min_len:]
    cov = np.cov(s.dropna(), b.dropna())
    if cov.shape != (2, 2) or cov[1, 1] == 0:
        return None
    return cov[0, 1] / cov[1, 1]


def sharpe_ratio(returns: pd.Series, window: int, rf_annual: float = 0.02) -> Optional[float]:
    """Annualized Sharpe ratio over window."""
    if len(returns) < window:
        return None
    r = returns.iloc[-window:]
    rf_daily = rf_annual / 252
    excess = r - rf_daily
    if excess.std() == 0:
        return None
    return (excess.mean() / excess.std()) * np.sqrt(252)


def sortino_ratio(returns: pd.Series, window: int, rf_annual: float = 0.02) -> Optional[float]:
    """Annualized Sortino ratio over window."""
    if len(returns) < window:
        return None
    r = returns.iloc[-window:]
    rf_daily = rf_annual / 252
    excess = r - rf_daily
    downside = excess[excess < 0]
    if len(downside) == 0 or downside.std() == 0:
        return None
    return (excess.mean() / downside.std()) * np.sqrt(252)


def calmar_ratio(returns: pd.Series, close_series: pd.Series, window: int) -> Optional[float]:
    """Calmar ratio = annualized return / abs(max drawdown)."""
    if len(returns) < window:
        return None
    ann_ret = returns.iloc[-window:].mean() * 252
    mdd = max_drawdown(close_series, window)
    if mdd is None or mdd == 0:
        return None
    return ann_ret / abs(mdd)


# ============================================================
# Liquidity Factors
# ============================================================

def amihud_illiquidity(returns: pd.Series, amounts: pd.Series, window: int) -> Optional[float]:
    """Amihud illiquidity = mean(|return| / amount)."""
    if len(returns) < window or len(amounts) < window:
        return None
    r = returns.iloc[-window:].abs()
    a = amounts.iloc[-window:]
    # Avoid division by zero
    valid = a > 0
    if valid.sum() < 5:
        return None
    return (r[valid] / a[valid]).mean()


def liquidity_score(
    avg_amount: Optional[float],
    turnover_rate: Optional[float],
    volume_ratio: Optional[float],
) -> Optional[float]:
    """Simple liquidity score (0-100) based on amount, turnover, volume ratio."""
    scores = []

    if avg_amount is not None and not pd.isna(avg_amount):
        # Score based on amount (higher = more liquid)
        if avg_amount >= 5e8:
            scores.append(100)
        elif avg_amount >= 1e8:
            scores.append(80)
        elif avg_amount >= 5e7:
            scores.append(60)
        elif avg_amount >= 1e7:
            scores.append(40)
        else:
            scores.append(20)

    if turnover_rate is not None and not pd.isna(turnover_rate):
        # Moderate turnover is best
        if 1 <= turnover_rate <= 10:
            scores.append(80)
        elif turnover_rate < 1:
            scores.append(40)
        else:
            scores.append(60)

    if volume_ratio is not None and not pd.isna(volume_ratio):
        if 0.8 <= volume_ratio <= 2.0:
            scores.append(80)
        elif volume_ratio < 0.5:
            scores.append(30)
        else:
            scores.append(60)

    return np.mean(scores) if scores else None


# ============================================================
# Valuation Factors
# ============================================================

def valuation_percentile(values: pd.Series, current_value: float) -> Optional[float]:
    """Compute percentile rank of current value within series."""
    if pd.isna(current_value) or len(values) == 0:
        return None
    valid = values.dropna()
    if len(valid) == 0:
        return None
    return (valid < current_value).sum() / len(valid) * 100


# ============================================================
# Technical Factors
# ============================================================

def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=span, adjust=False).mean()


def macd(close_series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """Compute MACD, signal line, histogram."""
    ema_fast = ema(close_series, fast)
    ema_slow = ema(close_series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def rsi(close_series: pd.Series, period: int = 14) -> Optional[float]:
    """Relative Strength Index."""
    if len(close_series) < period + 1:
        return None
    delta = close_series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val.iloc[-1] if not pd.isna(rsi_val.iloc[-1]) else None


def bollinger_bands(close_series: pd.Series, period: int = 20, std_dev: float = 2.0) -> tuple:
    """Compute Bollinger Bands: mid, upper, lower."""
    mid = close_series.rolling(window=period).mean()
    std = close_series.rolling(window=period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return mid, upper, lower


def bollinger_position(close: float, upper: float, lower: float) -> Optional[float]:
    """Position within Bollinger bands [0, 1]."""
    if pd.isna(upper) or pd.isna(lower) or upper == lower:
        return None
    return (close - lower) / (upper - lower)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Optional[float]:
    """Average True Range."""
    if len(close) < period + 1:
        return None
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean().iloc[-1]


def is_ma_bullish(close: float, ma20: float, ma60: float, ma120: float) -> bool:
    """Check if MAs are in bullish alignment."""
    if any(pd.isna(v) for v in [close, ma20, ma60, ma120]):
        return False
    return close > ma20 > ma60 > ma120


def golden_cross(macd_line: pd.Series, signal_line: pd.Series) -> bool:
    """Check if MACD golden cross just occurred."""
    if len(macd_line) < 2 or len(signal_line) < 2:
        return False
    return (macd_line.iloc[-2] <= signal_line.iloc[-2] and
            macd_line.iloc[-1] > signal_line.iloc[-1])


def dead_cross(macd_line: pd.Series, signal_line: pd.Series) -> bool:
    """Check if MACD dead cross just occurred."""
    if len(macd_line) < 2 or len(signal_line) < 2:
        return False
    return (macd_line.iloc[-2] >= signal_line.iloc[-2] and
            macd_line.iloc[-1] < signal_line.iloc[-1])


__all__ = [
    "price_position_52w", "distance_to_high", "distance_to_low",
    "compute_returns", "momentum", "relative_strength", "ytd_return",
    "volatility", "downside_volatility", "max_drawdown",
    "var_95", "cvar_95", "beta", "sharpe_ratio", "sortino_ratio", "calmar_ratio",
    "amihud_illiquidity", "liquidity_score", "valuation_percentile",
    "ema", "macd", "rsi", "bollinger_bands", "bollinger_position", "atr",
    "is_ma_bullish", "golden_cross", "dead_cross",
]
