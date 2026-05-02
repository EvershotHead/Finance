"""数据缓存模块 - 文件级缓存管理"""

import os
import time
import hashlib
from pathlib import Path
from typing import Optional

import pandas as pd

from finweb_src.config import config
from finweb_src.utils.logger import get_logger

logger = get_logger("Cache")

CACHE_DIR = Path(__file__).parent.parent.parent / "data_cache"


def _make_key(stock_code: str, data_type: str, start_date: str, end_date: str, **kwargs) -> str:
    """生成缓存键"""
    raw = f"{stock_code}_{data_type}_{start_date}_{end_date}"
    if kwargs:
        raw += "_" + "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_path(key: str) -> Path:
    """获取缓存文件路径"""
    return CACHE_DIR / f"{key}.parquet"


def get_cached(stock_code: str, data_type: str, start_date: str, end_date: str, **kwargs) -> Optional[pd.DataFrame]:
    """从缓存获取数据

    Args:
        stock_code: 股票代码
        data_type: 数据类型（如 daily, index, fundamental 等）
        start_date: 起始日期
        end_date: 结束日期

    Returns:
        缓存的 DataFrame，如果不存在或过期则返回 None
    """
    if not config.data.cache_enabled:
        return None

    key = _make_key(stock_code, data_type, start_date, end_date, **kwargs)
    path = _cache_path(key)

    if not path.exists():
        return None

    # 检查是否过期
    file_age_hours = (time.time() - path.stat().st_mtime) / 3600
    if file_age_hours > config.data.cache_expire_hours:
        logger.debug(f"缓存已过期: {key}")
        path.unlink(missing_ok=True)
        return None

    try:
        df = pd.read_parquet(path)
        logger.debug(f"命中缓存: {data_type} {stock_code} ({len(df)}行)")
        return df
    except Exception as e:
        logger.warning(f"缓存读取失败: {e}")
        return None


def set_cached(df: pd.DataFrame, stock_code: str, data_type: str, start_date: str, end_date: str, **kwargs) -> None:
    """写入缓存

    Args:
        df: 要缓存的 DataFrame
        stock_code: 股票代码
        data_type: 数据类型
        start_date: 起始日期
        end_date: 结束日期
    """
    if not config.data.cache_enabled or df is None or df.empty:
        return

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _make_key(stock_code, data_type, start_date, end_date, **kwargs)
    path = _cache_path(key)

    try:
        df.to_parquet(path)
        logger.debug(f"缓存已写入: {data_type} {stock_code} ({len(df)}行)")
    except Exception as e:
        logger.warning(f"缓存写入失败: {e}")


def clear_cache() -> int:
    """清空所有缓存

    Returns:
        删除的文件数量
    """
    count = 0
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.parquet"):
            f.unlink()
            count += 1
    logger.info(f"已清除缓存: {count} 个文件")
    return count