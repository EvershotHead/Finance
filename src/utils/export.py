"""导出工具模块 - JSON/CSV/Excel/HTML/Markdown 导出"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("Export")


class NumpyEncoder(json.JSONEncoder):
    """处理 numpy/pandas 类型的 JSON 编码器"""

    def default(self, obj: Any) -> Any:
        import numpy as np

        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Timestamp):
            return obj.strftime("%Y-%m-%d")
        if isinstance(obj, (datetime, date)):
            return obj.strftime("%Y-%m-%d")
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        if isinstance(obj, pd.Series):
            return obj.to_dict()
        if isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def ensure_dir(path: str) -> Path:
    """确保目录存在"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_json(data: dict, filepath: str) -> str:
    """保存 JSON 文件

    Args:
        data: 要保存的字典数据
        filepath: 文件路径

    Returns:
        保存的文件路径
    """
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
    logger.info(f"JSON 已保存: {filepath}")
    return filepath


def save_csv(df: pd.DataFrame, filepath: str, index: bool = True) -> str:
    """保存 CSV 文件"""
    ensure_dir(os.path.dirname(filepath))
    df.to_csv(filepath, encoding="utf-8-sig", index=index)
    logger.info(f"CSV 已保存: {filepath}")
    return filepath


def save_excel(df: pd.DataFrame, filepath: str, sheet_name: str = "Sheet1") -> str:
    """保存 Excel 文件"""
    ensure_dir(os.path.dirname(filepath))
    df.to_excel(filepath, sheet_name=sheet_name, index=True, engine="openpyxl")
    logger.info(f"Excel 已保存: {filepath}")
    return filepath


def save_markdown(content: str, filepath: str) -> str:
    """保存 Markdown 文件"""
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Markdown 已保存: {filepath}")
    return filepath


def save_html(content: str, filepath: str) -> str:
    """保存 HTML 文件"""
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"HTML 已保存: {filepath}")
    return filepath


def generate_timestamp() -> str:
    """生成时间戳字符串"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")