"""Tushare data fetching (optional, requires token)."""

from typing import Optional

import pandas as pd

from src.utils.logger import logger

try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False


class TushareFetcher:
    """Tushare Pro API fetcher."""

    def __init__(self, token: str):
        if not HAS_TUSHARE:
            raise ImportError("tushare not installed")
        self.pro = ts.pro_api(token)
        logger.info("Tushare fetcher initialized")

    def fetch_stock_list(self) -> Optional[pd.DataFrame]:
        """Fetch stock list from Tushare."""
        try:
            df = self.pro.stock_basic(exchange="", list_status="L",
                                       fields="ts_code,symbol,name,area,industry,list_date,market")
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    "ts_code": "stock_code",
                    "name": "stock_name",
                    "market": "board",
                })
                df["exchange"] = df["stock_code"].apply(lambda x: x.split(".")[1])
                df["symbol"] = df["stock_code"].apply(lambda x: x.split(".")[0])
                df["is_st"] = 0
                df["is_active"] = 1
                df["data_source"] = "tushare"
                df["updated_at"] = pd.Timestamp.now()
            return df
        except Exception as e:
            logger.error(f"Tushare stock list failed: {e}")
            return None

    def fetch_daily_bars(
        self,
        ts_code: str,
        start_date: str = "20230101",
        end_date: str = "",
    ) -> Optional[pd.DataFrame]:
        """Fetch daily bars from Tushare.

        Args:
            ts_code: Stock code in Tushare format, e.g. "300658.SZ"
        """
        try:
            df = self.pro.daily(ts_code=ts_code, start_date=start_date,
                               end_date=end_date or pd.Timestamp.now().strftime("%Y%m%d"))
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    "vol": "volume",
                })
                df["stock_code"] = ts_code
                df["trade_date"] = pd.to_datetime(df["trade_date"])
                df["pct_chg"] = df["pct_chg"] / 100.0
                df = df.sort_values("trade_date").reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"Tushare daily bars failed for {ts_code}: {e}")
            return None

    def fetch_daily_basic_single(self, ts_code: str, start_date: str = "", end_date: str = "") -> Optional[pd.DataFrame]:
        """Fetch daily basic indicators for a single stock."""
        try:
            df = self.pro.daily_basic(
                ts_code=ts_code,
                start_date=start_date or pd.Timestamp.now().strftime("%Y%m%d"),
                end_date=end_date or pd.Timestamp.now().strftime("%Y%m%d"),
                fields="ts_code,trade_date,turnover_rate,turnover_rate_f,"
                       "volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,"
                       "total_share,float_share,free_share,"
                       "total_mv,circ_mv,dv_ratio"
            )
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    "ts_code": "stock_code",
                    "dv_ratio": "dividend_yield",
                })
                df["trade_date"] = pd.to_datetime(df["trade_date"])
            return df
        except Exception as e:
            logger.error(f"Tushare daily basic failed for {ts_code}: {e}")
            return None

    def fetch_daily_basic_all(self, trade_date: str = "") -> Optional[pd.DataFrame]:
        """Fetch daily basic indicators for ALL stocks on a given date.

        This is much more efficient than fetching one by one.
        Returns ~5360 rows with PE, PB, total_mv, circ_mv, turnover_rate, etc.

        If trade_date is empty or returns no data, tries up to 5 previous days.
        """
        if not trade_date:
            trade_date = pd.Timestamp.now().strftime("%Y%m%d")

        fields = ("ts_code,trade_date,turnover_rate,turnover_rate_f,"
                  "volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,"
                  "total_share,float_share,free_share,"
                  "total_mv,circ_mv,dv_ratio")

        # Try the requested date, then up to 5 previous days
        for attempt in range(6):
            try_date = (pd.Timestamp(trade_date) - pd.Timedelta(days=attempt)).strftime("%Y%m%d")
            logger.info(f"Tushare: fetching daily_basic for all stocks on {try_date}...")
            try:
                df = self.pro.daily_basic(trade_date=try_date, fields=fields)
                if df is not None and len(df) > 0:
                    df = df.rename(columns={
                        "ts_code": "stock_code",
                        "dv_ratio": "dividend_yield",
                    })
                    df["trade_date"] = pd.to_datetime(df["trade_date"])
                    logger.info(f"Tushare: got daily_basic for {len(df)} stocks on {try_date}")
                    return df
                else:
                    logger.info(f"Tushare: no daily_basic data for {try_date}, trying previous day...")
            except Exception as e:
                logger.warning(f"Tushare daily_basic for {try_date} failed: {e}")

        logger.error("Tushare daily_basic: no data found for any of the last 6 days")
        return None

    def fetch_index_daily(
        self,
        ts_code: str = "000300.SH",
        start_date: str = "20230101",
        end_date: str = "",
    ) -> Optional[pd.DataFrame]:
        """Fetch index daily data."""
        try:
            df = self.pro.index_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date or pd.Timestamp.now().strftime("%Y%m%d"),
            )
            if df is not None and len(df) > 0:
                df = df.rename(columns={"vol": "volume"})
                df["trade_date"] = pd.to_datetime(df["trade_date"])
                df = df.sort_values("trade_date").reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"Tushare index daily failed for {ts_code}: {e}")
            return None

    def fetch_financial(self, ts_code: str, period: str = "") -> Optional[pd.DataFrame]:
        """Fetch financial indicators (ROE, ROA, margins, etc.)."""
        try:
            if not period:
                # Get latest period
                period = pd.Timestamp.now().strftime("%Y") + "1231"
            df = self.pro.fina_indicator(
                ts_code=ts_code,
                period=period,
                fields="ts_code,ann_date,end_date,roe,roa,grossprofit_margin,"
                       "netprofit_margin,debt_to_assets,current_ratio,quick_ratio,"
                       "eps,bps,ocfps,op_yoy,dt_netprofit_yoy"
            )
            return df if df is not None and len(df) > 0 else None
        except Exception as e:
            logger.debug(f"Tushare financial failed for {ts_code}: {e}")
            return None

    def fetch_moneyflow(self, ts_code: str, start_date: str = "", end_date: str = "") -> Optional[pd.DataFrame]:
        """Fetch money flow data."""
        try:
            df = self.pro.moneyflow(
                ts_code=ts_code,
                start_date=start_date or (pd.Timestamp.now() - pd.Timedelta(days=30)).strftime("%Y%m%d"),
                end_date=end_date or pd.Timestamp.now().strftime("%Y%m%d"),
            )
            return df if df is not None and len(df) > 0 else None
        except Exception as e:
            logger.debug(f"Tushare moneyflow failed for {ts_code}: {e}")
            return None


__all__ = ["TushareFetcher", "HAS_TUSHARE"]
