"""数据预处理模块 - 清洗、对齐、复权、收益率计算"""

import warnings
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from src.data.data_manager import StockDataBundle
from src.utils.logger import get_logger

logger = get_logger("Preprocessing")

warnings.filterwarnings("ignore", category=RuntimeWarning)


@dataclass
class ProcessedData:
    """预处理后的数据"""
    stock_df: pd.DataFrame  # 股票数据（含收益率）
    index_df: Optional[pd.DataFrame] = None  # 基准指数数据（含收益率）
    fundamental_df: Optional[pd.DataFrame] = None
    financial_df: Optional[pd.DataFrame] = None
    money_flow_df: Optional[pd.DataFrame] = None
    aligned: bool = False
    warnings: list[str] = field(default_factory=list)
    # 元数据
    stock_name: str = ""
    stock_code: str = ""
    start_date: str = ""
    end_date: str = ""
    benchmark_name: str = ""
    data_source: str = ""
    total_days: int = 0


def preprocess(bundle: StockDataBundle, benchmark_name: str = "沪深300") -> ProcessedData:
    """对 StockDataBundle 执行完整的数据预处理流程

    Steps:
        1. 日期转换与排序
        2. 去重
        3. 缺失值处理
        4. 对齐股票和基准交易日
        5. 计算收益率

    Args:
        bundle: 原始数据集合
        benchmark_name: 基准指数名称

    Returns:
        ProcessedData 预处理后的数据
    """
    if bundle.daily is None or bundle.daily.empty:
        logger.error("股票日行情数据为空，无法进行预处理")
        return ProcessedData(
            stock_df=pd.DataFrame(),
            warnings=["股票日行情数据为空"],
        )

    result = ProcessedData(
        stock_df=bundle.daily.copy(),
        index_df=bundle.index_daily.copy() if bundle.index_daily is not None else None,
        fundamental_df=bundle.fundamental.copy() if bundle.fundamental is not None else None,
        financial_df=bundle.financial.copy() if bundle.financial is not None else None,
        money_flow_df=bundle.money_flow.copy() if bundle.money_flow is not None else None,
        stock_name=bundle.stock_name,
        stock_code=bundle.stock_code,
        data_source=bundle.source_used,
        benchmark_name=benchmark_name,
    )

    result.warnings.extend(bundle.warnings)

    # Step 1: 日期处理
    result.stock_df = _process_dates(result.stock_df)
    if result.index_df is not None:
        result.index_df = _process_dates(result.index_df)

    # Step 2: 去重
    result.stock_df = _remove_duplicates(result.stock_df)
    if result.index_df is not None:
        result.index_df = _remove_duplicates(result.index_df)

    # Step 3: 排序
    result.stock_df = result.stock_df.sort_values("date").reset_index(drop=True)
    if result.index_df is not None:
        result.index_df = result.index_df.sort_values("date").reset_index(drop=True)

    # Step 4: 对齐交易日
    if result.index_df is not None and not result.index_df.empty:
        result.stock_df, result.index_df = _align_trading_days(result.stock_df, result.index_df)
        result.aligned = True

    # Step 5: 计算收益率
    result.stock_df = _calculate_returns(result.stock_df, prefix="")
    if result.index_df is not None and not result.index_df.empty:
        result.index_df = _calculate_returns(result.index_df, prefix="index_")

    # Step 6: 如果已对齐，计算超额收益率
    if result.aligned and "index_simple_return" in result.index_df.columns:
        result.stock_df["excess_return"] = (
            result.stock_df["simple_return"] - result.index_df["index_simple_return"]
        )

    # 记录元数据
    if not result.stock_df.empty:
        result.start_date = str(result.stock_df["date"].min().date())
        result.end_date = str(result.stock_df["date"].max().date())
        result.total_days = len(result.stock_df)

    logger.info(f"预处理完成: {result.stock_name}, {result.total_days} 个交易日, "
                f"{result.start_date}~{result.end_date}")

    return result


def _process_dates(df: pd.DataFrame) -> pd.DataFrame:
    """日期处理：转换为 datetime，处理异常"""
    if "date" not in df.columns:
        # 尝试用 index
        if df.index.name == "date" or "date" in str(df.index.dtype):
            df = df.reset_index()
        else:
            logger.warning("数据中找不到 date 列")
            return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    return df


def _remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """去重"""
    before = len(df)
    df = df.drop_duplicates(subset=["date"], keep="first")
    after = len(df)
    if before > after:
        logger.info(f"去除重复数据: {before - after} 条")
    return df


def _align_trading_days(
    stock_df: pd.DataFrame, index_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """按交易日对齐股票和基准数据

    以两者交集的交易日为准
    """
    stock_dates = set(stock_df["date"].dt.date)
    index_dates = set(index_df["date"].dt.date)
    common_dates = sorted(stock_dates & index_dates)

    if not common_dates:
        logger.warning("股票和基准没有共同交易日")
        return stock_df, index_df

    common_dt = pd.to_datetime(common_dates)

    stock_df = stock_df[stock_df["date"].isin(common_dt)].reset_index(drop=True)
    index_df = index_df[index_df["date"].isin(common_dt)].reset_index(drop=True)

    logger.info(f"交易日对齐: 共同交易日 {len(common_dates)} 天")
    return stock_df, index_df


def _calculate_returns(df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    """计算各类收益率

    Args:
        df: 包含 close 列的 DataFrame
        prefix: 列名前缀（如 'index_' 用于基准数据）
    """
    if "close" not in df.columns or df["close"].isna().all():
        logger.warning(f"收盘价数据缺失，无法计算收益率")
        return df

    close = df["close"].astype(float)

    # 简单收益率
    simple_ret = close.pct_change()
    df[f"{prefix}simple_return"] = simple_ret

    # 对数收益率
    df[f"{prefix}log_return"] = np.log(close / close.shift(1))

    # 累计收益率
    df[f"{prefix}cumulative_return"] = (1 + simple_ret).cumprod() - 1

    # 标记极端收益率（±2σ、±3σ），但不删除
    if not simple_ret.dropna().empty:
        mean = simple_ret.mean()
        std = simple_ret.std()
        df[f"{prefix}extreme_2sigma"] = (simple_ret > mean + 2 * std) | (simple_ret < mean - 2 * std)
        df[f"{prefix}extreme_3sigma"] = (simple_ret > mean + 3 * std) | (simple_ret < mean - 3 * std)
        extreme_2s = df[f"{prefix}extreme_2sigma"].sum()
        extreme_3s = df[f"{prefix}extreme_3sigma"].sum()
        if extreme_2s > 0:
            logger.info(f"极端收益率（±2σ）: {extreme_2s} 天")
        if extreme_3s > 0:
            logger.info(f"极端收益率（±3σ）: {extreme_3s} 天")

    return df