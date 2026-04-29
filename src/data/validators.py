"""数据校验模块 - 验证股票代码、数据完整性等"""

import re
from typing import Optional

import pandas as pd

from src.utils.logger import get_logger
from src.utils.exceptions import DataValidationError

logger = get_logger("Validator")

# 标准列名映射
STANDARD_COLUMNS = {
    "date": ["date", "日期", "trade_date", "datetime"],
    "open": ["open", "开盘", "开盘价"],
    "high": ["high", "最高", "最高价"],
    "low": ["low", "最低", "最低价"],
    "close": ["close", "收盘", "收盘价"],
    "volume": ["volume", "成交量", "vol"],
    "amount": ["amount", "成交额", "turnover"],
}


def parse_stock_code(code: str) -> dict:
    """解析股票代码，自动识别交易所

    Args:
        code: 股票代码，支持纯代码如 '300658' 或带后缀 '300658.SZ'

    Returns:
        包含解析结果的字典:
        - pure_code: 纯6位代码
        - suffix: .SH/.SZ/.BJ
        - tushare_code: Tushare 格式代码
        - akshare_code: AKShare 格式代码
    """
    code = str(code).strip().upper()

    # 去除可能的前缀
    code = code.replace("SH.", "").replace("SZ.", "").replace("BJ.", "")

    # 如果带后缀
    suffix = ""
    if "." in code:
        parts = code.split(".")
        pure_code = parts[0]
        raw_suffix = parts[1]
        suffix_map = {"SH": ".SH", "SZ": ".SZ", "BJ": ".BJ"}
        suffix = suffix_map.get(raw_suffix, "")
    else:
        pure_code = code

    # 确保是6位数字
    if not re.match(r"^\d{6}$", pure_code):
        raise DataValidationError(
            field="stock_code",
            message=f"无效的股票代码格式: {code}，需要6位数字"
        )

    # 自动识别交易所
    if not suffix:
        if pure_code.startswith("6"):
            suffix = ".SH"
        elif pure_code.startswith("0") or pure_code.startswith("3"):
            suffix = ".SZ"
        elif pure_code.startswith("8") or pure_code.startswith("4"):
            suffix = ".BJ"
        else:
            suffix = ".SZ"  # 默认

    # Tushare 格式: 000001.SZ
    tushare_code = f"{pure_code}{suffix}"

    # AKShare 格式: 深圳市场用 sz 前缀, 上海市场用 sh 前缀
    exchange = suffix.replace(".", "").lower()
    akshare_code = f"{exchange}{pure_code}"

    return {
        "pure_code": pure_code,
        "suffix": suffix,
        "tushare_code": tushare_code,
        "akshare_code": akshare_code,
        "exchange": exchange,
    }


def parse_benchmark_code(code: str) -> dict:
    """解析基准指数代码

    Args:
        code: 指数代码，如 '000300', '沪深300'

    Returns:
        包含 tushare_code 和 akshare_code 的字典
    """
    code = str(code).strip()

    # 名称到代码映射
    name_to_code = {
        "沪深300": "000300", "上证指数": "000001", "深证成指": "399001",
        "创业板指": "399006", "中证500": "000905", "中证1000": "000852",
    }

    pure_code = name_to_code.get(code, code).replace(".SH", "").replace(".SZ", "")

    if not re.match(r"^\d{6}$", pure_code):
        raise DataValidationError(
            field="benchmark_code",
            message=f"无效的指数代码: {code}"
        )

    # 判断指数交易所
    if pure_code.startswith("000") or pure_code.startswith("880"):
        suffix = ".SH"
    elif pure_code.startswith("399"):
        suffix = ".SZ"
    else:
        suffix = ".SH"

    tushare_code = f"{pure_code}{suffix}"
    exchange = suffix.replace(".", "").lower()
    akshare_code = f"{exchange}{pure_code}"

    return {
        "pure_code": pure_code,
        "suffix": suffix,
        "tushare_code": tushare_code,
        "akshare_code": akshare_code,
    }


def validate_dataframe(df: pd.DataFrame, required_cols: list[str], name: str = "数据") -> tuple[bool, list[str]]:
    """校验 DataFrame 是否包含必要列

    Args:
        df: 待校验的 DataFrame
        required_cols: 必须包含的列名列表
        name: 数据名称，用于日志

    Returns:
        (是否通过, 缺失列列表)
    """
    if df is None or df.empty:
        logger.warning(f"{name}: 数据为空")
        return False, required_cols

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        logger.warning(f"{name}: 缺失列 {missing}")
        return False, missing

    return True, []


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """标准化列名为英文小写

    Args:
        df: 原始 DataFrame

    Returns:
        列名标准化后的 DataFrame
    """
    rename_map = {}
    for std_name, aliases in STANDARD_COLUMNS.items():
        for col in df.columns:
            if str(col).lower().strip() in [a.lower() for a in aliases]:
                if col != std_name:
                    rename_map[col] = std_name
                break

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def check_data_quality(df: pd.DataFrame, name: str = "数据") -> dict:
    """检查数据质量

    Returns:
        包含数据质量报告的字典
    """
    report = {
        "name": name,
        "total_rows": len(df),
        "total_cols": len(df.columns),
        "missing_values": {},
        "duplicate_dates": 0,
        "date_range": None,
    }

    if df.empty:
        return report

    # 缺失值统计
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        report["missing_values"] = missing.to_dict()

    # 日期重复
    if "date" in df.columns:
        report["duplicate_dates"] = df["date"].duplicated().sum()
        report["date_range"] = {
            "start": str(df["date"].min()),
            "end": str(df["date"].max()),
        }

    return report