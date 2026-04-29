"""数据获取基类 - 定义统一的数据获取接口"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class FetchResult:
    """数据获取结果"""
    success: bool
    data: Optional[pd.DataFrame] = None
    source: str = ""
    data_type: str = ""
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


class BaseFetcher(ABC):
    """数据获取抽象基类

    所有数据源（AKShare、Tushare）必须实现此接口
    """

    source_name: str = "base"

    @abstractmethod
    def fetch_daily(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> FetchResult:
        """获取股票日行情数据

        Args:
            stock_code: 股票代码（已解析的纯6位代码）
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            adjust: 复权方式 qfq(前复权)/hfq(后复权)/空字符串(不复权)

        Returns:
            FetchResult，data 包含标准列: date, open, high, low, close, volume, amount
        """
        pass

    @abstractmethod
    def fetch_index_daily(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """获取指数日行情数据

        Args:
            index_code: 指数代码
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            FetchResult，data 包含标准列: date, open, high, low, close, volume, amount
        """
        pass

    @abstractmethod
    def fetch_fundamental(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """获取基本面指标数据（PE/PB/PS/市值等）

        Returns:
            FetchResult，data 包含可用的基本面指标
        """
        pass

    @abstractmethod
    def fetch_financial(
        self,
        stock_code: str,
    ) -> FetchResult:
        """获取财务指标数据（ROE/ROA/毛利率等）

        Returns:
            FetchResult，data 包含可用的财务指标
        """
        pass

    def fetch_money_flow(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """获取资金流数据（可选实现）

        Returns:
            FetchResult，data 包含资金流数据
        """
        return FetchResult(
            success=False,
            source=self.source_name,
            data_type="money_flow",
            error=f"{self.source_name} 不支持资金流数据获取",
        )