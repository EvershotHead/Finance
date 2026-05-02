"""Parquet file storage operations."""

from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.utils.logger import logger


def save_df(df: pd.DataFrame, path: Path, index: bool = False) -> Path:
    """Save DataFrame to Parquet file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=index, engine="pyarrow")
    logger.debug(f"Saved {len(df)} rows to {path}")
    return path


def load_df(path: Path, columns: Optional[list[str]] = None) -> Optional[pd.DataFrame]:
    """Load DataFrame from Parquet file. Returns None if file doesn't exist."""
    if not path.exists():
        logger.warning(f"Parquet file not found: {path}")
        return None
    try:
        df = pd.read_parquet(path, columns=columns, engine="pyarrow")
        logger.debug(f"Loaded {len(df)} rows from {path}")
        return df
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return None


def exists(path: Path) -> bool:
    """Check if Parquet file exists and is non-empty."""
    return path.exists() and path.stat().st_size > 0


def last_updated(path: Path) -> Optional[datetime]:
    """Return file modification time."""
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime)


def row_count(path: Path) -> int:
    """Return number of rows without loading full file."""
    if not path.exists():
        return 0
    try:
        pf = pq.ParquetFile(path)
        return pf.metadata.num_rows
    except Exception:
        return 0


def merge_incremental(
    new_df: pd.DataFrame,
    path: Path,
    key_cols: list[str],
    how: str = "outer",
) -> pd.DataFrame:
    """Merge new data with existing data, keeping latest by key columns."""
    existing = load_df(path)
    if existing is None or len(existing) == 0:
        merged = new_df
    else:
        # Combine and keep latest by key
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=key_cols, keep="last")
        merged = combined

    save_df(merged, path)
    logger.info(f"Merged into {path}: {len(new_df)} new rows, {len(merged)} total")
    return merged


__all__ = ["save_df", "load_df", "exists", "last_updated", "row_count", "merge_incremental"]
