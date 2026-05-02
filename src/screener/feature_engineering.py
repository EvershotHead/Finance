"""Feature engineering pipeline — compute all factors for the stock universe."""

from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

from src.screener import factor_library as fl
from src.storage import parquet_store, feature_store
from src.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"


def compute_all_features(
    universe_df: pd.DataFrame,
    daily_basic_df: Optional[pd.DataFrame] = None,
    progress_callback=None,
) -> pd.DataFrame:
    """Compute all screening features for the entire universe.

    This is the main pipeline that calls factor_library functions.

    Args:
        universe_df: DataFrame with stock_code, symbol, stock_name, etc.
        daily_basic_df: Daily basic indicators (PE, PB, market cap, etc.)
        progress_callback: callback(current, total, msg)

    Returns:
        DataFrame with all computed features
    """
    logger.info(f"Computing features for {len(universe_df)} stocks...")

    # Start with universe info
    features = universe_df.copy()

    # Merge basic indicators if available
    if daily_basic_df is not None and len(daily_basic_df) > 0:
        # Deduplicate basic data
        basic_cols = [c for c in daily_basic_df.columns if c not in features.columns or c in ("stock_code",)]
        basic_subset = daily_basic_df[basic_cols].drop_duplicates(subset=["stock_code"], keep="last")
        features = features.merge(basic_subset, on="stock_code", how="left", suffixes=("", "_basic"))

    # Compute per-stock factors from daily bars
    factor_records = []
    symbols = features["symbol"].tolist() if "symbol" in features.columns else features["stock_code"].tolist()
    total = len(symbols)

    for i, sym in enumerate(symbols):
        if progress_callback and i % 100 == 0:
            progress_callback(i, total, f"计算因子: {sym}")

        stock_code = features.loc[
            features["symbol"] == sym, "stock_code"
        ].iloc[0] if "symbol" in features.columns else sym

        record = _compute_stock_factors(stock_code)
        factor_records.append(record)

    # Merge factor records
    factor_df = pd.DataFrame(factor_records)
    if len(factor_df) > 0:
        # Drop overlapping columns before merge
        overlap = [c for c in factor_df.columns if c in features.columns and c not in ("stock_code", "symbol")]
        features = features.drop(columns=overlap, errors="ignore")
        features = features.merge(factor_df, on=["stock_code"], how="left", suffixes=("", "_factor"))

    # Compute derived features
    features = _compute_derived_features(features)

    # Add listing days
    if "list_date" in features.columns:
        features["listing_days"] = (
            pd.Timestamp.now() - pd.to_datetime(features["list_date"], errors="coerce")
        ).dt.days

    # Mark quality indicators
    features = _mark_quality(features)

    logger.info(f"Feature computation complete: {len(features)} stocks, {len(features.columns)} features")
    return features


def _compute_stock_factors(stock_code: str) -> dict:
    """Compute factors for a single stock from cached daily bars."""
    record = {"stock_code": stock_code}

    # Load cached daily bars
    cache_path = RAW_DIR / "daily_bar" / f"{stock_code.replace('.', '_')}.parquet"
    bars = parquet_store.load_df(cache_path)

    if bars is None or len(bars) < 5:
        return record

    bars = bars.sort_values("trade_date").reset_index(drop=True)
    close = bars["close"].astype(float)
    n = len(close)
    latest = bars.iloc[-1]

    # Latest price info
    record["latest_trade_date"] = latest.get("trade_date")
    record["latest_close"] = latest.get("close")
    record["latest_open"] = latest.get("open")
    record["latest_high"] = latest.get("high")
    record["latest_low"] = latest.get("low")
    record["latest_pct_chg"] = latest.get("pct_chg")

    # Price history
    for w in [5, 20, 60, 120, 252]:
        if n > w:
            record[f"price_{w}d_ago"] = close.iloc[-w - 1]
            if close.iloc[-w - 1] != 0:
                record[f"ret_{w}d"] = close.iloc[-1] / close.iloc[-w - 1] - 1

    # Returns for other windows
    for w in [1, 3, 10]:
        if n > w and close.iloc[-w - 1] != 0:
            record[f"ret_{w}d"] = close.iloc[-1] / close.iloc[-w - 1] - 1

    # High/low tracking
    for w in [20, 60, 252]:
        if n >= w:
            record[f"high_{w}d"] = bars["high"].astype(float).iloc[-w:].max()
            record[f"low_{w}d"] = bars["low"].astype(float).iloc[-w:].min()

    # Price position 52w
    if n >= 252:
        h = record.get("high_252d", np.nan)
        l = record.get("low_252d", np.nan)
        if h and l and h != l:
            record["price_position_52w"] = (close.iloc[-1] - l) / (h - l)
            record["distance_to_52w_high"] = (close.iloc[-1] - h) / h
            record["distance_to_52w_low"] = (close.iloc[-1] - l) / l

    # Returns and volatility
    if "pct_chg" in bars.columns:
        returns = bars["pct_chg"].astype(float) / 100.0 if bars["pct_chg"].abs().max() > 1 else bars["pct_chg"].astype(float)
        returns = returns.dropna()

        for w in [20, 60, 120, 252]:
            if len(returns) >= w:
                r = returns.iloc[-w:]
                record[f"volatility_{w}d"] = r.std() * np.sqrt(252)
                record[f"downside_volatility_{w}d"] = fl.downside_volatility(returns, w)
                record[f"var_95_{w}d"] = fl.var_95(returns, w) if w == 120 else None
                record[f"cvar_95_{w}d"] = fl.cvar_95(returns, w) if w == 120 else None

                # Sharpe
                rf_daily = 0.02 / 252
                excess = r - rf_daily
                if excess.std() > 0:
                    record[f"sharpe_{w}d"] = (excess.mean() / excess.std()) * np.sqrt(252)

                # Sortino (120d)
                if w == 120:
                    record["sortino_120d"] = fl.sortino_ratio(returns, w)

    # Max drawdown
    for w in [20, 60, 120, 252]:
        if n >= w:
            mdd = fl.max_drawdown(close, w)
            record[f"max_drawdown_{w}d"] = mdd

    # Calmar
    if n >= 252 and "pct_chg" in bars.columns:
        returns = bars["pct_chg"].astype(float)
        if returns.abs().max() > 1:
            returns = returns / 100.0
        record["calmar_252d"] = fl.calmar_ratio(returns.dropna(), close, 252)

    # Moving averages
    for ma in [5, 10, 20, 60, 120, 250]:
        if n >= ma:
            record[f"ma{ma}"] = close.iloc[-ma:].mean()

    # EMA
    if n >= 26:
        ema12 = fl.ema(close, 12)
        ema26 = fl.ema(close, 26)
        record["ema12"] = ema12.iloc[-1]
        record["ema26"] = ema26.iloc[-1]

    # MACD
    if n >= 35:
        macd_line, signal_line, hist = fl.macd(close)
        record["macd"] = macd_line.iloc[-1]
        record["macd_signal"] = signal_line.iloc[-1]
        record["macd_hist"] = hist.iloc[-1]
        record["macd_golden_cross"] = fl.golden_cross(macd_line, signal_line)
        record["macd_dead_cross"] = fl.dead_cross(macd_line, signal_line)

    # RSI
    for period in [6, 14, 24]:
        if n >= period + 1:
            record[f"rsi_{period}"] = fl.rsi(close, period)

    # Bollinger
    if n >= 20:
        bb_mid, bb_upper, bb_lower = fl.bollinger_bands(close)
        record["bollinger_mid"] = bb_mid.iloc[-1]
        record["bollinger_upper"] = bb_upper.iloc[-1]
        record["bollinger_lower"] = bb_lower.iloc[-1]
        bp = fl.bollinger_position(close.iloc[-1], bb_upper.iloc[-1], bb_lower.iloc[-1])
        record["bollinger_position"] = bp

    # ATR
    if n >= 14 and all(c in bars.columns for c in ["high", "low", "close"]):
        record["atr_14"] = fl.atr(
            bars["high"].astype(float), bars["low"].astype(float), close, 14
        )

    # Trend flags
    ma20 = record.get("ma20")
    ma60 = record.get("ma60")
    ma120 = record.get("ma120")
    c = close.iloc[-1]

    if ma20 is not None and not pd.isna(ma20):
        record["price_above_ma20"] = c > ma20
    if ma60 is not None and not pd.isna(ma60):
        record["price_above_ma60"] = c > ma60
    if ma120 is not None and not pd.isna(ma120):
        record["price_above_ma120"] = c > ma120
    if ma20 is not None and ma60 is not None and not pd.isna(ma20) and not pd.isna(ma60):
        record["ma20_above_ma60"] = ma20 > ma60
    if ma60 is not None and ma120 is not None and not pd.isna(ma60) and not pd.isna(ma120):
        record["ma60_above_ma120"] = ma60 > ma120
    record["is_ma_bullish"] = fl.is_ma_bullish(c, ma20 or 0, ma60 or 0, ma120 or 0)

    # New highs/lows
    if n >= 20:
        record["new_high_20d"] = c >= bars["high"].astype(float).iloc[-20:].max()
    if n >= 60:
        record["new_high_60d"] = c >= bars["high"].astype(float).iloc[-60:].max()
        record["new_low_60d"] = c <= bars["low"].astype(float).iloc[-60:].min()

    # Volume factors
    if "volume" in bars.columns:
        vol = bars["volume"].astype(float)
        for w in [5, 20, 60]:
            if n >= w:
                record[f"avg_volume_{w}d"] = vol.iloc[-w:].mean()
        if n >= 60:
            record["zero_volume_days_60d"] = (vol.iloc[-60:] == 0).sum()

    # Amount factors
    if "amount" in bars.columns:
        amt = bars["amount"].astype(float)
        for w in [5, 20, 60]:
            if n >= w:
                record[f"avg_amount_{w}d"] = amt.iloc[-w:].mean()
        # Amount ratio
        if n >= 20 and record.get("avg_amount_20d", 0) > 0:
            record["amount_ratio_20d"] = amt.iloc[-1] / record["avg_amount_20d"]

    # Amihud illiquidity
    if "pct_chg" in bars.columns and "amount" in bars.columns and n >= 20:
        returns = bars["pct_chg"].astype(float)
        if returns.abs().max() > 1:
            returns = returns / 100.0
        amounts = bars["amount"].astype(float)
        record["amihud_illiquidity_20d"] = fl.amihud_illiquidity(returns, amounts, 20)

    # Turnover rate
    if "turnover_rate" in bars.columns:
        tr = bars["turnover_rate"].astype(float)
        record["turnover_rate_latest"] = tr.iloc[-1]
        for w in [5, 20, 60]:
            if n >= w:
                record[f"turnover_rate_{w}d"] = tr.iloc[-w:].mean()

    # Technical score placeholder
    tech_scores = []
    if record.get("is_ma_bullish"):
        tech_scores.append(80)
    rsi_val = record.get("rsi_14")
    if rsi_val is not None and not pd.isna(rsi_val):
        if 40 <= rsi_val <= 60:
            tech_scores.append(70)
        elif rsi_val < 30:
            tech_scores.append(60)
        elif rsi_val > 70:
            tech_scores.append(40)
        else:
            tech_scores.append(55)
    if record.get("macd_golden_cross"):
        tech_scores.append(75)
    if tech_scores:
        record["technical_score"] = np.mean(tech_scores)

    return record


def _compute_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived features that need cross-stock data."""
    df = df.copy()

    # Momentum scores
    for w in [20, 60, 120]:
        ret_col = f"ret_{w}d"
        mom_col = f"momentum_{w}d"
        if ret_col in df.columns:
            df[mom_col] = df[ret_col]

    # Liquidity score
    if all(c in df.columns for c in ["avg_amount_20d", "turnover_rate_20d"]):
        df["liquidity_score"] = df.apply(
            lambda r: fl.liquidity_score(
                r.get("avg_amount_20d"),
                r.get("turnover_rate_20d"),
                r.get("volume_ratio_latest") or r.get("volume_ratio"),
            ),
            axis=1,
        )

    return df


def _mark_quality(df: pd.DataFrame) -> pd.DataFrame:
    """Mark data quality indicators."""
    df = df.copy()

    # Negative PE
    if "pe_ttm" in df.columns:
        df["has_negative_pe"] = (df["pe_ttm"] < 0) & df["pe_ttm"].notna()
        df["has_extreme_pe"] = (df["pe_ttm"] > 200) & df["pe_ttm"].notna()

    # Low liquidity
    if "avg_amount_20d" in df.columns:
        df["has_low_liquidity"] = (df["avg_amount_20d"] < 1e7) & df["avg_amount_20d"].notna()

    # Data quality score
    if "data_quality_score" not in df.columns:
        df["data_quality_score"] = 70  # default
        # Adjust based on available data
        score = pd.Series(70, index=df.index)
        if "pe_ttm" in df.columns:
            score = score.where(df["pe_ttm"].notna(), score - 10)
        if "roe" in df.columns:
            score = score.where(df["roe"].notna(), score - 5)
        if "volatility_120d" in df.columns:
            score = score.where(df["volatility_120d"].notna(), score - 5)
        df["data_quality_score"] = score.clip(0, 100)

    return df


__all__ = ["compute_all_features"]
