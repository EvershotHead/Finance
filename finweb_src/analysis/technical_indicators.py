"""模块10：技术指标分析"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from finweb_src.utils.logger import get_logger

logger = get_logger("Technical")


@dataclass
class TechnicalResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def compute_ma(df: pd.DataFrame, periods: list[int] = None) -> pd.DataFrame:
    """计算移动均线"""
    if periods is None:
        periods = [5, 10, 20, 60, 120]
    for p in periods:
        df[f"ma{p}"] = df["close"].rolling(p).mean()
    return df


def compute_ema(series: pd.Series, span: int) -> pd.Series:
    """计算指数移动均线"""
    return series.ewm(span=span, adjust=False).mean()


def compute_macd(close: pd.Series, fast=12, slow=26, signal=9) -> tuple:
    """计算 MACD"""
    ema_fast = compute_ema(close, fast)
    ema_slow = compute_ema(close, slow)
    dif = ema_fast - ema_slow
    dea = compute_ema(dif, signal)
    macd_hist = 2 * (dif - dea)
    return dif, dea, macd_hist


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """计算 RSI"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def compute_kdj(df: pd.DataFrame, n=9, m1=3, m2=3) -> tuple:
    """计算 KDJ"""
    low_n = df["low"].rolling(n).min()
    high_n = df["high"].rolling(n).max()
    rsv = (df["close"] - low_n) / (high_n - low_n).replace(0, np.nan) * 100
    k = rsv.ewm(com=m1 - 1, adjust=False).mean()
    d = k.ewm(com=m2 - 1, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def compute_bollinger(close: pd.Series, period=20, std_mult=2) -> tuple:
    """计算布林带"""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


def compute_atr(df: pd.DataFrame, period=14) -> pd.Series:
    """计算 ATR"""
    h_l = df["high"] - df["low"]
    h_c = (df["high"] - df["close"].shift(1)).abs()
    l_c = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([h_l, h_c, l_c], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_obv(df: pd.DataFrame) -> pd.Series:
    """计算 OBV"""
    sign = df["close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (sign * df["volume"]).cumsum()


def analyze_technical(df: pd.DataFrame) -> TechnicalResult:
    """技术指标分析

    Args:
        df: 包含 date, open, high, low, close, volume 的 DataFrame
    """
    result = TechnicalResult()
    try:
        if df is None or df.empty:
            result.error = "数据为空"
            return result

        data = {}
        df = df.copy()
        close = df["close"].astype(float)

        # 均线
        df = compute_ma(df, [5, 10, 20, 60, 120])
        latest_close = float(close.iloc[-1])
        for p in [20, 60]:
            col = f"ma{p}"
            if col in df.columns and not df[col].isna().all():
                ma_val = float(df[col].iloc[-1])
                pos = "上方" if latest_close > ma_val else "下方"
                data[f"价格vs MA{p}"] = f"价格在MA{p}({ma_val:.2f}){pos}"

        # MACD
        dif, dea, macd_hist = compute_macd(close)
        df["dif"], df["dea"], df["macd_hist"] = dif, dea, macd_hist
        data["DIF"] = round(float(dif.iloc[-1]), 4)
        data["DEA"] = round(float(dea.iloc[-1]), 4)
        data["MACD"] = round(float(macd_hist.iloc[-1]), 4)

        # MACD 金叉/死叉
        if len(dif) > 1:
            cross = "金叉" if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2] else \
                    "死叉" if dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2] else \
                    "DIF在DEA上方" if dif.iloc[-1] > dea.iloc[-1] else "DIF在DEA下方"
            data["MACD状态"] = cross

        # RSI
        for p in [6, 14, 24]:
            rsi = compute_rsi(close, p)
            df[f"rsi{p}"] = rsi
            val = float(rsi.iloc[-1])
            data[f"RSI{p}"] = round(val, 2)
            if val > 80:
                data[f"RSI{p}_状态"] = "超买"
            elif val < 20:
                data[f"RSI{p}_状态"] = "超卖"
            else:
                data[f"RSI{p}_状态"] = "正常"

        # KDJ
        k, d, j = compute_kdj(df)
        df["k"], df["d"], df["j"] = k, d, j
        data["K"] = round(float(k.iloc[-1]), 2)
        data["D"] = round(float(d.iloc[-1]), 2)
        data["J"] = round(float(j.iloc[-1]), 2)

        # 布林带
        upper, mid, lower = compute_bollinger(close)
        df["bb_upper"], df["bb_mid"], df["bb_lower"] = upper, mid, lower
        data["布林上轨"] = round(float(upper.iloc[-1]), 2)
        data["布林中轨"] = round(float(mid.iloc[-1]), 2)
        data["布林下轨"] = round(float(lower.iloc[-1]), 2)
        bb_width = float(upper.iloc[-1]) - float(lower.iloc[-1])
        bb_pos = (latest_close - float(lower.iloc[-1])) / bb_width if bb_width > 0 else 0.5
        data["布林带位置"] = round(bb_pos, 2)

        # ATR
        atr = compute_atr(df)
        df["atr"] = atr
        data["ATR"] = round(float(atr.iloc[-1]), 4)
        data["ATR_百分比"] = round(float(atr.iloc[-1] / latest_close * 100), 2)

        # OBV
        obv = compute_obv(df)
        df["obv"] = obv

        # 成交量分析
        if "volume" in df.columns:
            vol = df["volume"].astype(float)
            vol_ma20 = vol.rolling(20).mean()
            vol_ratio = float(vol.iloc[-1] / vol_ma20.iloc[-1]) if vol_ma20.iloc[-1] > 0 else 0
            data["成交量/MA20比"] = round(vol_ratio, 2)
            data["成交量状态"] = "放量" if vol_ratio > 1.5 else "缩量" if vol_ratio < 0.5 else "正常"

        result.data = data
        result.success = True

        # 保存带指标的df用于图表
        result.figures["df_with_indicators"] = df

        # 中文解读
        parts = []
        parts.append(f"最新收盘价: {latest_close:.2f}")
        if "MACD状态" in data:
            parts.append(f"MACD: {data['MACD状态']}，DIF={data['DIF']}, DEA={data['DEA']}")
        if "RSI14_状态" in data:
            parts.append(f"RSI(14)={data['RSI14']}，{data['RSI14_状态']}")
        if "布林带位置" in data:
            pos = data["布林带位置"]
            if pos > 0.8:
                parts.append(f"布林带位置={pos:.2f}，接近上轨，可能面临压力。")
            elif pos < 0.2:
                parts.append(f"布林带位置={pos:.2f}，接近下轨，可能存在支撑。")
            else:
                parts.append(f"布林带位置={pos:.2f}，处于中轨附近。")
        if "成交量状态" in data:
            parts.append(f"成交量: {data['成交量状态']}（/MA20={data['成交量/MA20比']:.2f}）")
        parts.append(f"ATR(14)={data['ATR']:.4f}，占价格比{data['ATR_百分比']:.2f}%")

        result.interpretation = "\n".join(parts)

    except Exception as e:
        result.error = f"技术指标分析失败: {str(e)}"
        logger.error(result.error)

    return result