"""Result formatting for display in Streamlit."""

import pandas as pd
import numpy as np

from src.utils.formatting import COLUMN_FORMAT, fmt_pct, fmt_mv, fmt_number, fmt_score


# Columns to display in results table (in order)
DISPLAY_COLUMNS = [
    "stock_code", "stock_name", "industry", "board",
    "latest_close", "latest_pct_chg", "total_mv", "circ_mv",
    "pe_ttm", "pb", "roe",
    "ret_20d", "ret_60d", "ret_120d",
    "volatility_120d", "max_drawdown_120d", "beta_120d", "sharpe_120d",
    "avg_amount_20d", "turnover_rate_20d",
    "total_score", "risk_score", "liquidity_score",
    "value_score", "quality_score", "technical_score", "data_quality_score",
]


def format_results_table(df: pd.DataFrame, columns: list[str] = None) -> pd.DataFrame:
    """Format a results DataFrame for display.

    Args:
        df: Results DataFrame
        columns: Columns to include (default: DISPLAY_COLUMNS)

    Returns:
        Formatted DataFrame with display column names
    """
    if columns is None:
        columns = [c for c in DISPLAY_COLUMNS if c in df.columns]

    display = df[columns].copy()

    # Rename columns to Chinese
    rename_map = {}
    for col in columns:
        if col in COLUMN_FORMAT:
            rename_map[col] = COLUMN_FORMAT[col][0]
    display = display.rename(columns=rename_map)

    return display


def format_single_stock(row: pd.Series) -> dict:
    """Format a single stock row for detailed display."""
    info = {}
    for col in DISPLAY_COLUMNS:
        if col in row.index:
            label = COLUMN_FORMAT.get(col, (col, None, 0))[0]
            value = row[col]
            if pd.isna(value):
                info[label] = "-"
            else:
                info[label] = value
    return info


def add_rank_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a rank column (1-based) to the DataFrame."""
    df = df.copy()
    df.insert(0, "排名", range(1, len(df) + 1))
    return df


__all__ = ["format_results_table", "format_single_stock", "add_rank_column", "DISPLAY_COLUMNS"]
