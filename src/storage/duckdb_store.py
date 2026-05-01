"""DuckDB store for efficient querying of feature store data."""

from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils.logger import logger

# DuckDB is optional — degrade gracefully
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False
    logger.warning("DuckDB not installed. Will use pandas for queries.")


class DuckDBStore:
    """DuckDB-based query layer over Parquet files."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._conn = None

    def _get_conn(self):
        if not HAS_DUCKDB:
            return None
        if self._conn is None:
            self._conn = duckdb.connect(":memory:")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def query_features(
        self,
        parquet_path: Path,
        stock_codes: Optional[list[str]] = None,
        fields: Optional[list[str]] = None,
        where: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """Query feature store parquet with optional filters."""
        if not parquet_path.exists():
            logger.warning(f"Feature file not found: {parquet_path}")
            return None

        conn = self._get_conn()
        if conn is None:
            return self._fallback_query(parquet_path, stock_codes, fields, where, limit)

        try:
            # Build query
            select = "*" if not fields else ", ".join(fields)
            query = f"SELECT {select} FROM read_parquet('{parquet_path.as_posix()}')"

            conditions = []
            if stock_codes:
                codes_str = ", ".join(f"'{c}'" for c in stock_codes)
                conditions.append(f"stock_code IN ({codes_str})")
            if where:
                conditions.append(where)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            if limit:
                query += f" LIMIT {limit}"

            result = conn.execute(query).fetchdf()
            logger.debug(f"DuckDB query returned {len(result)} rows")
            return result

        except Exception as e:
            logger.error(f"DuckDB query failed: {e}")
            return self._fallback_query(parquet_path, stock_codes, fields, where, limit)

    def _fallback_query(
        self,
        parquet_path: Path,
        stock_codes: Optional[list[str]] = None,
        fields: Optional[list[str]] = None,
        where: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """Fallback: load with pandas and filter."""
        try:
            df = pd.read_parquet(parquet_path, engine="pyarrow")
            if stock_codes:
                df = df[df["stock_code"].isin(stock_codes)]
            if fields:
                available = [f for f in fields if f in df.columns]
                df = df[available]
            if limit:
                df = df.head(limit)
            return df
        except Exception as e:
            logger.error(f"Fallback query failed: {e}")
            return None

    def register_view(self, name: str, parquet_path: Path) -> bool:
        """Register a parquet file as a named view."""
        conn = self._get_conn()
        if conn is None or not parquet_path.exists():
            return False
        try:
            conn.execute(
                f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{parquet_path.as_posix()}')"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to register view {name}: {e}")
            return False


__all__ = ["DuckDBStore", "HAS_DUCKDB"]
