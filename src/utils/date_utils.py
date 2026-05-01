"""Date utility functions."""

from datetime import datetime, date, timedelta
from typing import Optional, Union

import pandas as pd


def today() -> date:
    """Return today's date."""
    return date.today()


def today_str(fmt: str = "%Y%m%d") -> str:
    """Return today's date as string."""
    return today().strftime(fmt)


def parse_date(d: Union[str, date, datetime, pd.Timestamp]) -> date:
    """Parse various date types to date object."""
    if isinstance(d, str):
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(d, fmt).date()
            except ValueError:
                continue
        return pd.Timestamp(d).date()
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, pd.Timestamp):
        return d.date()
    return d


def date_range_years(years: int, end_date: Optional[Union[str, date]] = None) -> tuple[str, str]:
    """Return (start_date, end_date) string pair for N years of history."""
    end = parse_date(end_date) if end_date else today()
    start = end - timedelta(days=years * 365)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def days_between(d1: Union[str, date], d2: Union[str, date]) -> int:
    """Return number of days between two dates."""
    return (parse_date(d2) - parse_date(d1)).days


def is_valid_trade_date(d: Union[str, date]) -> bool:
    """Check if a date is a weekday (rough check, not accounting for holidays)."""
    dt = parse_date(d)
    return dt.weekday() < 5


def format_date(d: Union[str, date, datetime], fmt: str = "%Y-%m-%d") -> str:
    """Format a date to string."""
    return parse_date(d).strftime(fmt)


__all__ = [
    "today", "today_str", "parse_date", "date_range_years",
    "days_between", "is_valid_trade_date", "format_date",
]
