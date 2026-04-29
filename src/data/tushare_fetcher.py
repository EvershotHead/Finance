"""Tushare 数据获取模块 - 使用 tushare 获取 A 股数据"""

import time
from typing import Optional

import pandas as pd
import numpy as np

from src.data.base_fetcher import BaseFetcher, FetchResult
from src.utils.logger import get_logger

logger = get_logger("Tushare")


class TushareFetcher(BaseFetcher):
    """Tushare 数据获取器

    需要有效的 Tushare Token
    """

    source_name = "tushare"

    def __init__(self, token: str = ""):
        self.pro = None
        self.token = token
        if token:
            try:
                import tushare as ts
                ts.set_token(token)
                self.pro = ts.pro_api()
                logger.info("Tushare 初始化成功")
            except Exception as e:
                logger.error(f"Tushare 初始化失败: {e}")
        else:
            logger.warning("Tushare Token 未设置，Tushare 数据源不可用")

    def _ensure_pro(self):
        """确保 pro_api 可用"""
        if self.pro is None:
            raise RuntimeError("Tushare 未初始化，请提供有效的 Token")

    def fetch_daily(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> FetchResult:
        """获取股票日行情数据

        Tushare 使用 ts_code 格式如 300658.SZ
        """
        if self.pro is None:
            return FetchResult(success=False, source=self.source_name, data_type="daily", error="Tushare未初始化")

        try:
            from src.data.validators import parse_stock_code
            code_info = parse_stock_code(stock_code)
            ts_code = code_info["tushare_code"]

            sd = start_date.replace("-", "")
            ed = end_date.replace("-", "")

            logger.info(f"[Tushare] 获取日行情: {ts_code}, {sd}~{ed}")

            df = self.pro.daily(ts_code=ts_code, start_date=sd, end_date=ed)

            if df is None or df.empty:
                return FetchResult(
                    success=False, source=self.source_name, data_type="daily",
                    error=f"Tushare 返回空数据: {ts_code}"
                )

            # 标准化列名
            col_map = {
                "trade_date": "date", "open": "open", "close": "close",
                "high": "high", "low": "low", "vol": "volume",
                "amount": "amount", "pct_chg": "pct_change", "change": "change",
                "turnover_rate": "turnover_rate",
            }
            df = df.rename(columns=col_map)

            # 日期处理
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

            # amount 单位转换：Tushare 的 amount 单位是千元
            if "amount" in df.columns:
                df["amount"] = df["amount"] * 1000

            # volume 单位转换：Tushare 的 vol 单位是手（100股）
            if "volume" in df.columns:
                df["volume"] = df["volume"] * 100

            # 处理复权
            if adjust in ("qfq", "hfq"):
                try:
                    adj_df = self.pro.adj_factor(ts_code=ts_code, start_date=sd, end_date=ed)
                    if adj_df is not None and not adj_df.empty:
                        adj_df["trade_date"] = pd.to_datetime(adj_df["trade_date"])
                        adj_df = adj_df.rename(columns={"trade_date": "date", "adj_factor": "adj_factor"})
                        df = df.merge(adj_df[["date", "adj_factor"]], on="date", how="left")

                        if adjust == "qfq":
                            # 前复权：用最新复权因子调整
                            latest_factor = df["adj_factor"].iloc[-1]
                            for col in ["open", "high", "low", "close"]:
                                if col in df.columns:
                                    df[col] = df[col] * df["adj_factor"] / latest_factor
                        elif adjust == "hfq":
                            # 后复权：用最早复权因子调整
                            earliest_factor = df["adj_factor"].iloc[0]
                            for col in ["open", "high", "low", "close"]:
                                if col in df.columns:
                                    df[col] = df[col] * df["adj_factor"] / earliest_factor

                        df = df.drop(columns=["adj_factor"], errors="ignore")
                except Exception as e:
                    logger.warning(f"复权因子获取失败，使用未复权数据: {e}")

            logger.info(f"[Tushare] 日行情获取成功: {ts_code}, {len(df)} 条")
            return FetchResult(success=True, data=df, source=self.source_name, data_type="daily")

        except Exception as e:
            error_msg = f"Tushare 获取日行情失败: {stock_code}, 错误: {str(e)}"
            logger.error(error_msg)
            return FetchResult(success=False, source=self.source_name, data_type="daily", error=error_msg)

    def fetch_index_daily(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """获取指数日行情数据"""
        if self.pro is None:
            return FetchResult(success=False, source=self.source_name, data_type="index", error="Tushare未初始化")

        try:
            from src.data.validators import parse_benchmark_code
            code_info = parse_benchmark_code(index_code)
            ts_code = code_info["tushare_code"]

            sd = start_date.replace("-", "")
            ed = end_date.replace("-", "")

            logger.info(f"[Tushare] 获取指数行情: {ts_code}, {sd}~{ed}")

            df = self.pro.index_daily(ts_code=ts_code, start_date=sd, end_date=ed)

            if df is None or df.empty:
                return FetchResult(
                    success=False, source=self.source_name, data_type="index",
                    error=f"Tushare 返回空指数数据: {ts_code}"
                )

            col_map = {
                "trade_date": "date", "open": "open", "close": "close",
                "high": "high", "low": "low", "vol": "volume",
                "amount": "amount",
            }
            df = df.rename(columns=col_map)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

            logger.info(f"[Tushare] 指数行情获取成功: {ts_code}, {len(df)} 条")
            return FetchResult(success=True, data=df, source=self.source_name, data_type="index")

        except Exception as e:
            error_msg = f"Tushare 获取指数行情失败: {index_code}, 错误: {str(e)}"
            logger.error(error_msg)
            return FetchResult(success=False, source=self.source_name, data_type="index", error=error_msg)

    def fetch_fundamental(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """获取基本面指标数据"""
        if self.pro is None:
            return FetchResult(success=False, source=self.source_name, data_type="fundamental", error="Tushare未初始化")

        warnings = []
        try:
            from src.data.validators import parse_stock_code
            code_info = parse_stock_code(stock_code)
            ts_code = code_info["tushare_code"]

            sd = start_date.replace("-", "")
            ed = end_date.replace("-", "")

            logger.info(f"[Tushare] 获取基本面指标: {ts_code}")

            # daily_basic 包含 PE/PB/PS/市值等
            df = self.pro.daily_basic(ts_code=ts_code, start_date=sd, end_date=ed)

            if df is not None and not df.empty:
                col_map = {
                    "trade_date": "date", "pe": "pe", "pe_ttm": "pe_ttm",
                    "pb": "pb", "ps": "ps", "ps_ttm": "ps_ttm",
                    "dv_ratio": "dv_ratio", "dv_ttm": "dv_ttm",
                    "total_mv": "total_mv", "circ_mv": "circ_mv",
                    "turnover_rate": "turnover_rate", "volume_ratio": "volume_ratio",
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)

                logger.info(f"[Tushare] 基本面指标获取成功: {ts_code}, {len(df)} 条")
                return FetchResult(success=True, data=df, source=self.source_name, data_type="fundamental", warnings=warnings)
            else:
                return FetchResult(
                    success=False, source=self.source_name, data_type="fundamental",
                    error="daily_basic 返回空数据", warnings=warnings
                )

        except Exception as e:
            error_msg = f"Tushare 获取基本面数据失败: {stock_code}, 错误: {str(e)}"
            logger.error(error_msg)
            return FetchResult(success=False, source=self.source_name, data_type="fundamental", error=error_msg, warnings=warnings)

    def fetch_financial(
        self,
        stock_code: str,
    ) -> FetchResult:
        """获取财务指标数据"""
        if self.pro is None:
            return FetchResult(success=False, source=self.source_name, data_type="financial", error="Tushare未初始化")

        warnings = []
        try:
            from src.data.validators import parse_stock_code
            code_info = parse_stock_code(stock_code)
            ts_code = code_info["tushare_code"]

            logger.info(f"[Tushare] 获取财务指标: {ts_code}")

            # 获取主要财务指标
            df = self.pro.fina_indicator(ts_code=ts_code)

            if df is not None and not df.empty:
                col_map = {
                    "ann_date": "date", "end_date": "report_date",
                    "roe": "roe", "roa": "roa",
                    "grossprofit_margin": "gross_margin",
                    "netprofit_margin": "net_margin",
                    "debt_to_assets": "debt_ratio",
                    "or_yoy": "revenue_yoy", "netprofit_yoy": "net_profit_yoy",
                    "eps": "eps", "bps": "bps",
                    "ocfps": "ocfps",
                    "cfps": "cfps",
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")

                logger.info(f"[Tushare] 财务指标获取成功: {ts_code}, {len(df)} 条")
                return FetchResult(success=True, data=df, source=self.source_name, data_type="financial", warnings=warnings)
            else:
                return FetchResult(
                    success=False, source=self.source_name, data_type="financial",
                    error="fina_indicator 返回空数据", warnings=warnings
                )

        except Exception as e:
            error_msg = f"Tushare 获取财务数据失败: {stock_code}, 错误: {str(e)}"
            logger.error(error_msg)
            return FetchResult(success=False, source=self.source_name, data_type="financial", error=error_msg, warnings=warnings)

    def fetch_money_flow(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """获取资金流数据"""
        if self.pro is None:
            return FetchResult(success=False, source=self.source_name, data_type="money_flow", error="Tushare未初始化")

        warnings = []
        try:
            from src.data.validators import parse_stock_code
            code_info = parse_stock_code(stock_code)
            ts_code = code_info["tushare_code"]

            sd = start_date.replace("-", "")
            ed = end_date.replace("-", "")

            logger.info(f"[Tushare] 获取资金流数据: {ts_code}")

            df = self.pro.moneyflow(ts_code=ts_code, start_date=sd, end_date=ed)

            if df is not None and not df.empty:
                col_map = {
                    "trade_date": "date",
                    "buy_elg_amount": "super_large_buy",
                    "sell_elg_amount": "super_large_sell",
                    "buy_lg_amount": "large_buy",
                    "sell_lg_amount": "large_sell",
                    "buy_md_amount": "medium_buy",
                    "sell_md_amount": "medium_sell",
                    "buy_sm_amount": "small_buy",
                    "sell_sm_amount": "small_sell",
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)

                logger.info(f"[Tushare] 资金流数据获取成功: {ts_code}, {len(df)} 条")
                return FetchResult(success=True, data=df, source=self.source_name, data_type="money_flow", warnings=warnings)
            else:
                return FetchResult(
                    success=False, source=self.source_name, data_type="money_flow",
                    error="moneyflow 返回空数据", warnings=warnings
                )

        except Exception as e:
            error_msg = f"Tushare 获取资金流数据失败: {stock_code}, 错误: {str(e)}"
            logger.error(error_msg)
            return FetchResult(success=False, source=self.source_name, data_type="money_flow", error=error_msg, warnings=warnings)