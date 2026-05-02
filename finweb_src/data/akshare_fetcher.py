"""AKShare 数据获取模块 - 使用 akshare 获取 A 股数据

注意（2026-04 更新）：AKShare 1.18+ 删除/变更了若干接口，本模块改用以下策略：
- 日线：优先 stock_zh_a_daily（新浪，稳定且支持日期范围+复权），降级到 stock_zh_a_hist（东财）
- 指数：优先 stock_zh_index_daily（新浪，需本地过滤日期），降级到 index_zh_a_hist（东财）
- 基本面（PE/PB/市值）：使用 stock_value_em（原 stock_a_lg_indicator 已删除）
- 财务摘要：使用 stock_financial_abstract_ths
- 资金流：stock_individual_fund_flow
"""

import time
from typing import Optional

import pandas as pd
import numpy as np

from finweb_src.data.base_fetcher import BaseFetcher, FetchResult
from finweb_src.utils.logger import get_logger

logger = get_logger("AKShare")


def _exchange_prefix(stock_code: str) -> str:
    """根据 6 位股票代码推断交易所前缀（用于新浪/腾讯接口的 sz/sh/bj 前缀）。"""
    code = str(stock_code).strip()
    if code.startswith("6") or code.startswith("9"):
        return "sh"
    if code.startswith(("0", "2", "3")):
        return "sz"
    if code.startswith(("4", "8")):
        return "bj"
    return "sz"


def _index_prefix(index_code: str) -> str:
    """指数代码前缀：000xxx/880xxx → sh，399xxx → sz。"""
    code = str(index_code).strip()
    if code.startswith("399"):
        return "sz"
    return "sh"


class AKShareFetcher(BaseFetcher):
    """AKShare 数据获取器（免费，无需 token）。"""

    source_name = "akshare"

    def __init__(self):
        try:
            import akshare as ak
            self.ak = ak
            logger.info(f"AKShare 初始化成功，版本 {getattr(ak, '__version__', 'unknown')}")
        except ImportError:
            self.ak = None
            logger.error("akshare 未安装，请运行: pip install akshare")

    # ------------------------------------------------------------------
    # 日线
    # ------------------------------------------------------------------
    def fetch_daily(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> FetchResult:
        """获取股票日行情数据。

        优先尝试新浪 ``stock_zh_a_daily``（带日期范围+复权），
        失败再降级到东财 ``stock_zh_a_hist``。
        """
        if self.ak is None:
            return FetchResult(success=False, source=self.source_name, data_type="daily",
                               error="akshare 未安装")

        sd_dash = start_date  # YYYY-MM-DD
        ed_dash = end_date
        sd_compact = start_date.replace("-", "")
        ed_compact = end_date.replace("-", "")
        adj = adjust if adjust in ("qfq", "hfq") else ""

        attempts = []

        # 主路径：新浪 stock_zh_a_daily
        try:
            sina_symbol = f"{_exchange_prefix(stock_code)}{stock_code}"
            logger.info(f"[AKShare] 日行情(新浪): {sina_symbol}, {sd_compact}~{ed_compact}, adjust={adj or 'none'}")
            df = self.ak.stock_zh_a_daily(
                symbol=sina_symbol,
                start_date=sd_compact,
                end_date=ed_compact,
                adjust=adj,
            )
            df = self._normalize_sina_daily(df)
            if df is not None and not df.empty:
                logger.info(f"[AKShare] 日行情获取成功(新浪): {stock_code}, {len(df)} 条")
                return FetchResult(success=True, data=df, source=self.source_name, data_type="daily")
            attempts.append("sina 返回空")
        except Exception as e:
            attempts.append(f"sina 失败: {e}")
            logger.warning(f"[AKShare] 新浪日行情失败: {e}")

        # 降级：东财 stock_zh_a_hist
        try:
            logger.info(f"[AKShare] 日行情(东财降级): {stock_code}")
            df = self.ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=sd_compact,
                end_date=ed_compact,
                adjust=adj if adj else None,
            )
            df = self._normalize_em_daily(df)
            if df is not None and not df.empty:
                logger.info(f"[AKShare] 日行情获取成功(东财): {stock_code}, {len(df)} 条")
                return FetchResult(success=True, data=df, source=self.source_name, data_type="daily")
            attempts.append("eastmoney 返回空")
        except Exception as e:
            attempts.append(f"eastmoney 失败: {e}")
            logger.warning(f"[AKShare] 东财日行情失败: {e}")

        return FetchResult(
            success=False, source=self.source_name, data_type="daily",
            error=f"AKShare 日行情全部失败: {'; '.join(attempts)}",
        )

    @staticmethod
    def _normalize_sina_daily(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
        """新浪 stock_zh_a_daily 列：date,open,high,low,close,volume,amount,outstanding_share,turnover。"""
        if df is None or df.empty:
            return df
        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        # 新浪 turnover 即换手率（小数，转百分比与东财对齐）
        if "turnover" in df.columns and "turnover_rate" not in df.columns:
            df["turnover_rate"] = df["turnover"].astype(float) * 100.0
        # 派生 pct_change（百分比）和 change
        if "close" in df.columns:
            close = df["close"].astype(float)
            df["pct_change"] = close.pct_change() * 100.0
            df["change"] = close.diff()
            df["amplitude"] = ((df["high"].astype(float) - df["low"].astype(float))
                               / close.shift(1)) * 100.0
        df = df.sort_values("date").reset_index(drop=True)
        return df

    @staticmethod
    def _normalize_em_daily(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
        """东财 stock_zh_a_hist 中文列名 → 英文。"""
        if df is None or df.empty:
            return df
        col_map = {
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
            "成交额": "amount", "振幅": "amplitude", "涨跌幅": "pct_change",
            "涨跌额": "change", "换手率": "turnover_rate",
        }
        df = df.rename(columns=col_map).copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df

    # ------------------------------------------------------------------
    # 指数日线
    # ------------------------------------------------------------------
    def fetch_index_daily(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """获取指数日行情数据。

        优先 ``stock_zh_index_daily``（新浪，返回全部历史，本地按日期裁剪），
        降级到 ``index_zh_a_hist``（东财）。
        """
        if self.ak is None:
            return FetchResult(success=False, source=self.source_name, data_type="index",
                               error="akshare 未安装")

        sd_compact = start_date.replace("-", "")
        ed_compact = end_date.replace("-", "")
        attempts = []

        # 主路径：新浪
        try:
            sym = f"{_index_prefix(index_code)}{index_code}"
            logger.info(f"[AKShare] 指数行情(新浪): {sym}")
            df = self.ak.stock_zh_index_daily(symbol=sym)
            df = self._normalize_index_df(df, start_date, end_date)
            if df is not None and not df.empty:
                logger.info(f"[AKShare] 指数获取成功(新浪): {index_code}, {len(df)} 条")
                return FetchResult(success=True, data=df, source=self.source_name, data_type="index")
            attempts.append("sina 空")
        except Exception as e:
            attempts.append(f"sina 失败: {e}")
            logger.warning(f"[AKShare] 新浪指数失败: {e}")

        # 降级：东财
        try:
            logger.info(f"[AKShare] 指数行情(东财降级): {index_code}")
            df = self.ak.index_zh_a_hist(
                symbol=index_code, period="daily",
                start_date=sd_compact, end_date=ed_compact,
            )
            df = self._normalize_index_df(df, start_date, end_date)
            if df is not None and not df.empty:
                logger.info(f"[AKShare] 指数获取成功(东财): {index_code}, {len(df)} 条")
                return FetchResult(success=True, data=df, source=self.source_name, data_type="index")
            attempts.append("eastmoney 空")
        except Exception as e:
            attempts.append(f"eastmoney 失败: {e}")
            logger.warning(f"[AKShare] 东财指数失败: {e}")

        return FetchResult(
            success=False, source=self.source_name, data_type="index",
            error=f"AKShare 指数全部失败: {'; '.join(attempts)}",
        )

    @staticmethod
    def _normalize_index_df(df: Optional[pd.DataFrame], start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        if df is None or df.empty:
            return df
        col_map = {
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
            "成交额": "amount",
        }
        df = df.rename(columns=col_map).copy()
        if "date" not in df.columns and df.index.name in ("date", "Date"):
            df = df.reset_index().rename(columns={df.index.name or "index": "date"})
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            sd = pd.to_datetime(start_date)
            ed = pd.to_datetime(end_date)
            df = df[(df["date"] >= sd) & (df["date"] <= ed)]
            df = df.sort_values("date").reset_index(drop=True)
        return df

    # ------------------------------------------------------------------
    # 基本面（PE/PB/市值）
    # ------------------------------------------------------------------
    def fetch_fundamental(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        """获取每日估值/市值指标。

        使用 ``stock_value_em``（替代已删除的 ``stock_a_lg_indicator``）。
        返回列：数据日期/当日收盘价/总市值/流通市值/PE(TTM)/PE(静)/市净率/PEG值/市现率/市销率。
        """
        if self.ak is None:
            return FetchResult(success=False, source=self.source_name, data_type="fundamental",
                               error="akshare 未安装")

        warnings = []
        try:
            logger.info(f"[AKShare] 估值指标 stock_value_em: {stock_code}")
            raw = self.ak.stock_value_em(symbol=stock_code)
            if raw is None or raw.empty:
                return FetchResult(
                    success=False, source=self.source_name, data_type="fundamental",
                    error=f"stock_value_em 返回空: {stock_code}",
                )

            col_map = {
                "数据日期": "date",
                "当日收盘价": "close",
                "当日涨跌幅": "pct_change",
                "总市值": "total_mv",
                "流通市值": "circ_mv",
                "总股本": "total_share",
                "流通股本": "float_share",
                "PE(TTM)": "pe_ttm",
                "PE(静)": "pe",
                "市净率": "pb",
                "PEG值": "peg",
                "市现率": "pcf",
                "市销率": "ps",
            }
            df = raw.rename(columns={k: v for k, v in col_map.items() if k in raw.columns}).copy()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                sd = pd.to_datetime(start_date)
                ed = pd.to_datetime(end_date)
                filtered = df[(df["date"] >= sd) & (df["date"] <= ed)].reset_index(drop=True)
                if filtered.empty:
                    warnings.append("区间内无估值数据，回退为最近 60 条")
                    df = df.tail(60).reset_index(drop=True)
                else:
                    df = filtered

            logger.info(f"[AKShare] 估值指标成功: {stock_code}, {len(df)} 条")
            return FetchResult(
                success=True, data=df, source=self.source_name,
                data_type="fundamental", warnings=warnings,
            )

        except Exception as e:
            error_msg = f"AKShare 获取基本面失败: {stock_code}, 错误: {e}"
            logger.error(error_msg)
            return FetchResult(success=False, source=self.source_name,
                               data_type="fundamental", error=error_msg, warnings=warnings)

    # ------------------------------------------------------------------
    # 财务摘要
    # ------------------------------------------------------------------
    def fetch_financial(self, stock_code: str) -> FetchResult:
        """获取财务摘要（按年度）。"""
        if self.ak is None:
            return FetchResult(success=False, source=self.source_name, data_type="financial",
                               error="akshare 未安装")

        warnings = []
        try:
            logger.info(f"[AKShare] 财务摘要 stock_financial_abstract_ths: {stock_code}")
            df = None
            try:
                df = self.ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按年度")
            except Exception as e:
                warnings.append(f"stock_financial_abstract_ths 失败: {e}")

            if (df is None or df.empty):
                try:
                    df = self.ak.stock_financial_abstract(symbol=stock_code)
                    warnings.append("已降级到 stock_financial_abstract")
                except Exception as e:
                    warnings.append(f"stock_financial_abstract 失败: {e}")

            if df is None or df.empty:
                return FetchResult(
                    success=False, source=self.source_name, data_type="financial",
                    error="财务数据获取失败", warnings=warnings,
                )

            logger.info(f"[AKShare] 财务摘要成功: {stock_code}, {len(df)} 条")
            return FetchResult(success=True, data=df, source=self.source_name,
                               data_type="financial", warnings=warnings)

        except Exception as e:
            error_msg = f"AKShare 获取财务失败: {stock_code}, 错误: {e}"
            logger.error(error_msg)
            return FetchResult(success=False, source=self.source_name,
                               data_type="financial", error=error_msg, warnings=warnings)

    # ------------------------------------------------------------------
    # 资金流
    # ------------------------------------------------------------------
    def fetch_money_flow(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        if self.ak is None:
            return FetchResult(success=False, source=self.source_name, data_type="money_flow",
                               error="akshare 未安装")

        warnings = []
        try:
            market = _exchange_prefix(stock_code)  # sz/sh/bj
            if market == "bj":
                market = "bj"  # akshare 资金流支持 bj
            logger.info(f"[AKShare] 资金流: {stock_code}, market={market}")
            df = self.ak.stock_individual_fund_flow(stock=stock_code, market=market)
            if df is None or df.empty:
                return FetchResult(
                    success=False, source=self.source_name, data_type="money_flow",
                    error="资金流数据为空", warnings=warnings,
                )

            col_map = {
                "日期": "date", "收盘价": "close", "涨跌幅": "pct_change",
                "主力净流入-净额": "main_net_inflow",
                "超大单净流入-净额": "super_large_net_inflow",
                "大单净流入-净额": "large_net_inflow",
                "中单净流入-净额": "medium_net_inflow",
                "小单净流入-净额": "small_net_inflow",
            }
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}).copy()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                sd = pd.to_datetime(start_date)
                ed = pd.to_datetime(end_date)
                df = df[(df["date"] >= sd) & (df["date"] <= ed)]
                df = df.sort_values("date").reset_index(drop=True)

            if df.empty:
                # 资金流接口仅保留最近约 120 个交易日，区间过早会全部被过滤掉
                return FetchResult(
                    success=False, source=self.source_name, data_type="money_flow",
                    error="资金流数据在所选区间内为空（akshare 仅提供最近约 120 个交易日）",
                    warnings=warnings,
                )

            logger.info(f"[AKShare] 资金流成功: {stock_code}, {len(df)} 条")
            return FetchResult(success=True, data=df, source=self.source_name,
                               data_type="money_flow", warnings=warnings)

        except Exception as e:
            error_msg = f"AKShare 获取资金流失败: {stock_code}, 错误: {e}"
            logger.error(error_msg)
            return FetchResult(success=False, source=self.source_name,
                               data_type="money_flow", error=error_msg, warnings=warnings)
