"""数据管理器 - 统一数据获取入口，支持自动降级、缓存、代码解析"""

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from finweb_src.config import config
from finweb_src.data.base_fetcher import FetchResult
from finweb_src.data.akshare_fetcher import AKShareFetcher
from finweb_src.data.tushare_fetcher import TushareFetcher
from finweb_src.data.validators import parse_stock_code, parse_benchmark_code, check_data_quality
from finweb_src.data.cache import get_cached, set_cached
from finweb_src.utils.logger import get_logger

logger = get_logger("DataManager")


@dataclass
class StockDataBundle:
    """股票数据集合"""
    stock_code: str
    stock_name: str
    code_info: dict
    daily: Optional[pd.DataFrame] = None
    index_daily: Optional[pd.DataFrame] = None
    fundamental: Optional[pd.DataFrame] = None
    financial: Optional[pd.DataFrame] = None
    money_flow: Optional[pd.DataFrame] = None
    warnings: list[str] = field(default_factory=list)
    data_quality: dict = field(default_factory=dict)
    source_used: str = ""


class DataManager:
    """统一数据管理器

    功能：
    1. 自动解析股票代码（纯代码/带后缀）
    2. 支持 AKShare / Tushare / 自动选择
    3. 失败自动降级
    4. 文件级缓存
    5. 数据质量检查
    """

    def __init__(self, source: str = "auto", tushare_token: str = ""):
        """
        Args:
            source: 数据源选择 'auto'/'akshare'/'tushare'
            tushare_token: Tushare Token
        """
        self.source = source
        self._fetchers = {}

        # 初始化 AKShare
        try:
            self._fetchers["akshare"] = AKShareFetcher()
        except Exception as e:
            logger.warning(f"AKShare 初始化失败: {e}")

        # 初始化 Tushare
        token = tushare_token or config.tushare_token
        if token:
            self._fetchers["tushare"] = TushareFetcher(token=token)

        logger.info(f"DataManager 初始化完成，可用数据源: {list(self._fetchers.keys())}")

    def _get_fetchers_order(self) -> list[str]:
        """获取数据源尝试顺序"""
        available = list(self._fetchers.keys())
        if self.source == "auto":
            # 优先 AKShare（免费）
            order = []
            if "akshare" in available:
                order.append("akshare")
            if "tushare" in available:
                order.append("tushare")
            return order
        elif self.source in available:
            return [self.source] + [f for f in available if f != self.source]
        else:
            logger.warning(f"指定数据源 {self.source} 不可用，使用自动模式")
            return available

    def _try_fetch(self, method: str, *args, **kwargs) -> FetchResult:
        """尝试从数据源获取数据，失败自动降级"""
        for source_name in self._get_fetchers_order():
            fetcher = self._fetchers.get(source_name)
            if fetcher is None:
                continue
            try:
                fetch_func = getattr(fetcher, method)
                result = fetch_func(*args, **kwargs)
                if result.success:
                    return result
                else:
                    logger.warning(f"[{source_name}] {method} 失败: {result.error}")
            except Exception as e:
                logger.warning(f"[{source_name}] {method} 异常: {str(e)}")

        return FetchResult(success=False, data_type=method, error="所有数据源均获取失败")

    def fetch_all(
        self,
        stock_code: str,
        stock_name: str = "",
        start_date: str = "",
        end_date: str = "",
        benchmark_code: str = "000300",
        adjust: str = "qfq",
    ) -> StockDataBundle:
        """获取股票全部数据

        Args:
            stock_code: 股票代码
            stock_name: 股票名称（仅用于报告显示）
            start_date: 起始日期
            end_date: 结束日期
            benchmark_code: 基准指数代码
            adjust: 复权方式

        Returns:
            StockDataBundle 数据集合
        """
        # 解析股票代码
        code_info = parse_stock_code(stock_code)
        pure_code = code_info["pure_code"]

        if not stock_name:
            stock_name = pure_code

        bundle = StockDataBundle(
            stock_code=pure_code,
            stock_name=stock_name,
            code_info=code_info,
        )

        logger.info(f"开始获取数据: {stock_name}({pure_code}), {start_date}~{end_date}")

        # 1. 获取股票日行情（优先，核心数据）
        cached = get_cached(pure_code, "daily", start_date, end_date, adjust=adjust)
        if cached is not None:
            bundle.daily = cached
            bundle.source_used = "cache"
        else:
            result = self._try_fetch("fetch_daily", pure_code, start_date, end_date, adjust)
            if result.success and result.data is not None:
                bundle.daily = result.data
                bundle.source_used = result.source
                set_cached(result.data, pure_code, "daily", start_date, end_date, adjust=adjust)
            else:
                bundle.warnings.append(f"日行情数据获取失败: {result.error}")
                logger.error(f"日行情获取失败，无法继续分析: {result.error}")
                return bundle  # 核心数据缺失，提前返回

        # 2. 获取基准指数行情
        bench_info = parse_benchmark_code(benchmark_code)
        bench_code = bench_info["pure_code"]
        cached = get_cached(bench_code, "index", start_date, end_date)
        if cached is not None:
            bundle.index_daily = cached
        else:
            result = self._try_fetch("fetch_index_daily", bench_code, start_date, end_date)
            if result.success and result.data is not None:
                bundle.index_daily = result.data
                set_cached(result.data, bench_code, "index", start_date, end_date)
            else:
                bundle.warnings.append(f"基准指数数据获取失败: {result.error}")

        # 3. 获取基本面指标
        cached = get_cached(pure_code, "fundamental", start_date, end_date)
        if cached is not None:
            bundle.fundamental = cached
        else:
            result = self._try_fetch("fetch_fundamental", pure_code, start_date, end_date)
            if result.success and result.data is not None:
                bundle.fundamental = result.data
                set_cached(result.data, pure_code, "fundamental", start_date, end_date)
            else:
                bundle.warnings.append(f"基本面数据获取失败: {result.error}")

        # 4. 获取财务指标
        cached = get_cached(pure_code, "financial", start_date, end_date)
        if cached is not None:
            bundle.financial = cached
        else:
            result = self._try_fetch("fetch_financial", pure_code)
            if result.success and result.data is not None:
                bundle.financial = result.data
                set_cached(result.data, pure_code, "financial", start_date, end_date)
            else:
                bundle.warnings.append(f"财务数据获取失败: {result.error}")

        # 5. 获取资金流数据
        cached = get_cached(pure_code, "money_flow", start_date, end_date)
        if cached is not None:
            bundle.money_flow = cached
        else:
            result = self._try_fetch("fetch_money_flow", pure_code, start_date, end_date)
            if result.success and result.data is not None:
                bundle.money_flow = result.data
                set_cached(result.data, pure_code, "money_flow", start_date, end_date)
            else:
                bundle.warnings.append(f"资金流数据获取失败: {result.error}")

        # 数据质量检查
        if bundle.daily is not None:
            bundle.data_quality["daily"] = check_data_quality(bundle.daily, "日行情")
        if bundle.index_daily is not None:
            bundle.data_quality["index"] = check_data_quality(bundle.index_daily, "基准指数")

        logger.info(f"数据获取完成: {stock_name}, 日行情={len(bundle.daily) if bundle.daily is not None else 0}条, "
                     f"基准={len(bundle.index_daily) if bundle.index_daily is not None else 0}条, "
                     f"警告={len(bundle.warnings)}条")

        return bundle