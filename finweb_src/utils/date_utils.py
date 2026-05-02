"""日期工具模块 - 日期解析、格式化、交易日相关"""

from datetime import datetime, date, timedelta
from typing import Union
import re


def parse_date(date_str: Union[str, date, datetime]) -> datetime:
    """解析日期字符串为 datetime 对象

    支持格式: YYYY-MM-DD, YYYYMMDD, YYYY/MM/DD, YYYY年MM月DD日
    """
    if isinstance(date_str, datetime):
        return date_str
    if isinstance(date_str, date):
        return datetime.combine(date_str, datetime.min.time())

    s = str(date_str).strip()

    # YYYY-MM-DD 或 YYYY/MM/DD
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    # YYYY年MM月DD日
    match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日?", s)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    raise ValueError(f"无法解析日期: {date_str}")


def format_date(dt: Union[str, date, datetime], fmt: str = "%Y-%m-%d") -> str:
    """格式化日期为字符串"""
    if isinstance(dt, str):
        dt = parse_date(dt)
    if isinstance(dt, datetime):
        return dt.strftime(fmt)
    if isinstance(dt, date):
        return dt.strftime(fmt)
    return str(dt)


def to_date_str(dt: Union[str, date, datetime]) -> str:
    """统一转为 YYYY-MM-DD 格式字符串"""
    return format_date(dt, "%Y-%m-%d")


def get_default_start_date(years: int = 3) -> str:
    """获取默认起始日期（往前推指定年数）"""
    dt = datetime.now() - timedelta(days=years * 365)
    return format_date(dt)


def get_default_end_date() -> str:
    """获取默认结束日期（今天）"""
    return format_date(datetime.now())


def date_range_years(start: str, end: str) -> float:
    """计算日期区间年数"""
    s = parse_date(start)
    e = parse_date(end)
    return (e - s).days / 365.25


def trading_days_estimate(years: float) -> int:
    """估算交易日数量（约252天/年）"""
    return int(years * 252)