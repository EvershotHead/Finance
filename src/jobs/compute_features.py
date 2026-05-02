"""Job: Compute all screening factors and generate feature store."""

from typing import Optional, Callable

import pandas as pd

from src.data.universe_manager import load_universe
from src.data.data_manager import get_manager
from src.data.data_quality import clean_daily_bars, clean_daily_basic, compute_quality_indicators
from src.storage import parquet_store, feature_store
from src.utils.logger import logger
from src.utils.date_utils import date_range_years

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
DAILY_BAR_DIR = RAW_DIR / "daily_bar"


def _find_stocks_with_data() -> list[str]:
    """Find all stock codes that have cached daily bar data."""
    if not DAILY_BAR_DIR.exists():
        return []
    files = list(DAILY_BAR_DIR.glob("*.parquet"))
    # Extract stock_code from filename: "000001_SZ.parquet" -> "000001.SZ"
    codes = []
    for f in files:
        name = f.stem  # e.g. "000001_SZ"
        parts = name.split("_")
        if len(parts) == 2:
            codes.append(f"{parts[0]}.{parts[1]}")
    return codes


def run(
    limit: Optional[int] = None,
    data_source: str = "akshare",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Optional[pd.DataFrame]:
    """Compute all factors and generate stock_features_latest.parquet.

    Only processes stocks that have cached daily bar data.
    """
    logger.info("=== Computing features ===")

    universe = load_universe()
    if universe is None:
        logger.error("Universe not available")
        return None

    # Find stocks with actual daily bar data
    stocks_with_data = _find_stocks_with_data()
    logger.info(f"Found {len(stocks_with_data)} stocks with cached daily bar data")

    if not stocks_with_data:
        logger.warning("No stocks have daily bar data. Run daily data update first.")
        # Return universe with empty features
        features = universe.copy()
        features["data_quality_score"] = 0
        feature_store.save_latest_features(features)
        return features

    # Filter universe to only stocks with data
    if limit:
        stocks_with_data = stocks_with_data[:limit]

    universe_with_data = universe[universe["stock_code"].isin(stocks_with_data)].copy()
    logger.info(f"Computing features for {len(universe_with_data)} stocks (universe has {len(universe)} total)")

    # Load basic indicators
    basic_path = RAW_DIR / "daily_basic" / "daily_basic_latest.parquet"
    basic_df = parquet_store.load_df(basic_path)

    if basic_df is not None:
        # Merge universe with basic data
        universe_with_data = universe_with_data.merge(
            basic_df.drop(columns=["stock_name"], errors="ignore"),
            on="stock_code",
            how="left",
            suffixes=("", "_basic"),
        )

    # Compute factors only for stocks with data
    features = _compute_basic_factors(universe_with_data, progress_callback)

    # Compute quality indicators
    features = compute_quality_indicators(features)

    # Save
    feature_store.save_latest_features(features)
    logger.info(f"=== Features computed: {len(features)} stocks ===")

    return features


def _compute_basic_factors(
    df: pd.DataFrame,
    progress_callback: Optional[Callable] = None,
) -> pd.DataFrame:
    """Compute basic price/return/volatility factors from daily bar data."""
    symbols = df["symbol"].tolist() if "symbol" in df.columns else df["stock_code"].tolist()
    total = len(symbols)
    factor_rows = []

    for i, sym in enumerate(symbols):
        stock_code = df.loc[df["symbol"] == sym, "stock_code"].iloc[0] if "symbol" in df.columns else sym

        if progress_callback and i % 100 == 0:
            progress_callback(i, total, f"计算因子: {stock_code} ({i+1}/{total})")

        try:
            # Load daily bars from cache
            cache_path = DAILY_BAR_DIR / f"{stock_code.replace('.', '_')}.parquet"
            bars = parquet_store.load_df(cache_path)

            if bars is None or len(bars) < 5:
                factor_rows.append({"stock_code": stock_code, "symbol": sym})
                continue

            bars = bars.sort_values("trade_date").reset_index(drop=True)
            latest = bars.iloc[-1]

            row = {
                "stock_code": stock_code,
                "symbol": sym,
                "latest_trade_date": latest.get("trade_date"),
                "latest_close": latest.get("close"),
                "latest_pct_chg": latest.get("pct_chg"),
            }

            # Price history
            close = bars["close"].values
            n = len(close)
            for w in [5, 20, 60, 120, 252]:
                if n > w:
                    row[f"price_{w}d_ago"] = close[-w - 1]
                    row[f"ret_{w}d"] = (close[-1] / close[-w - 1] - 1) if close[-w - 1] != 0 else None

            # Volatility
            if "pct_chg" in bars.columns and n > 20:
                returns = bars["pct_chg"].dropna()
                for w in [20, 60, 120, 252]:
                    if len(returns) >= w:
                        row[f"volatility_{w}d"] = returns.iloc[-w:].std() * (252 ** 0.5)

            # Max drawdown
            for w in [20, 60, 120, 252]:
                if n > w:
                    window = close[-w:]
                    peak = pd.Series(window).cummax()
                    drawdown = (pd.Series(window) - peak) / peak
                    row[f"max_drawdown_{w}d"] = drawdown.min()

            # Moving averages
            for ma in [5, 10, 20, 60, 120, 250]:
                if n >= ma:
                    row[f"ma{ma}"] = close[-ma:].mean()

            # Price position
            if n >= 252:
                high_252 = bars["high"].iloc[-252:].max()
                low_252 = bars["low"].iloc[-252:].min()
                row["high_252d"] = high_252
                row["low_252d"] = low_252
                if high_252 != low_252:
                    row["price_position_52w"] = (close[-1] - low_252) / (high_252 - low_252)

            # Volume averages
            if "volume" in bars.columns:
                vol = bars["volume"].values
                for w in [5, 20, 60]:
                    if n >= w:
                        row[f"avg_volume_{w}d"] = vol[-w:].mean()

            if "amount" in bars.columns:
                amt = bars["amount"].values
                for w in [5, 20, 60]:
                    if n >= w:
                        row[f"avg_amount_{w}d"] = amt[-w:].mean()

            # Turnover rate
            if "turnover_rate" in bars.columns:
                tr = bars["turnover_rate"].astype(float)
                row["turnover_rate_latest"] = tr.iloc[-1]
                for w in [5, 20, 60]:
                    if n >= w:
                        row[f"turnover_rate_{w}d"] = tr.iloc[-w:].mean()

            # RSI
            if n >= 15:
                delta = pd.Series(close).diff()
                gain = delta.clip(lower=0)
                loss = (-delta).clip(lower=0)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()
                rs = avg_gain / avg_loss.replace(0, float('nan'))
                rsi_val = 100 - (100 / (1 + rs))
                row["rsi_14"] = rsi_val.iloc[-1] if not pd.isna(rsi_val.iloc[-1]) else None

            # Trend flags
            ma20 = row.get("ma20")
            ma60 = row.get("ma60")
            ma120 = row.get("ma120")
            c = close[-1]

            if ma20 is not None and not pd.isna(ma20):
                row["price_above_ma20"] = bool(c > ma20)
            if ma60 is not None and not pd.isna(ma60):
                row["price_above_ma60"] = bool(c > ma60)
            if ma120 is not None and not pd.isna(ma120):
                row["price_above_ma120"] = bool(c > ma120)
            if ma20 is not None and ma60 is not None and not pd.isna(ma20) and not pd.isna(ma60):
                row["ma20_above_ma60"] = bool(ma20 > ma60)
            if ma60 is not None and ma120 is not None and not pd.isna(ma60) and not pd.isna(ma120):
                row["ma60_above_ma120"] = bool(ma60 > ma120)

            factor_rows.append(row)

        except Exception as e:
            logger.debug(f"Factor computation failed for {sym}: {e}")
            factor_rows.append({"stock_code": stock_code, "symbol": sym})

    # Merge factors back
    factor_df = pd.DataFrame(factor_rows)
    if len(factor_df) > 0:
        # Drop overlapping columns before merge
        drop_cols = [c for c in factor_df.columns if c in df.columns and c not in ("stock_code", "symbol")]
        features = df.drop(columns=drop_cols, errors="ignore")
        features = features.merge(factor_df, on=["stock_code", "symbol"], how="left", suffixes=("", "_factor"))
    else:
        features = df

    return features


__all__ = ["run"]
