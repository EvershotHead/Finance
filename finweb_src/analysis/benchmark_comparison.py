"""模块4：相对基准表现分析"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from finweb_src.utils.logger import get_logger

logger = get_logger("Benchmark")


@dataclass
class BenchmarkResult:
    success: bool = False
    data: dict = field(default_factory=dict)
    interpretation: str = ""
    figures: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


def analyze_benchmark(stock_df: pd.DataFrame, index_df: pd.DataFrame,
                      rf_annual: float = 0.02) -> BenchmarkResult:
    """分析股票相对基准的表现

    Args:
        stock_df: 股票数据（含 simple_return, cumulative_return）
        index_df: 基准数据（含 index_simple_return, index_cumulative_return）
        rf_annual: 年化无风险利率
    """
    result = BenchmarkResult()
    try:
        if stock_df is None or index_df is None:
            result.error = "股票或基准数据为空"
            return result

        sr = stock_df["simple_return"].dropna()
        br = index_df["index_simple_return"].dropna() if "index_simple_return" in index_df.columns else None

        if br is None or len(sr) == 0:
            result.error = "缺少收益率数据"
            return result

        # 对齐长度
        min_len = min(len(sr), len(br))
        sr = sr.iloc[-min_len:].reset_index(drop=True)
        br = br.iloc[-min_len:].reset_index(drop=True)

        n = min_len
        td = 252

        # 累计收益
        stock_cum = float((1 + sr).prod() - 1)
        bench_cum = float((1 + br).prod() - 1)
        excess_cum = stock_cum - bench_cum

        # 年化
        ann_factor = n / td
        stock_ann = float((1 + stock_cum) ** (1 / ann_factor) - 1) if ann_factor > 0 else 0
        bench_ann = float((1 + bench_cum) ** (1 / ann_factor) - 1) if ann_factor > 0 else 0
        excess_ann = stock_ann - bench_ann

        # 超额收益
        excess = sr - br
        tracking_error = float(excess.std() * np.sqrt(td))
        info_ratio = excess_ann / tracking_error if tracking_error != 0 else 0

        # Beta / Alpha / 相关系数
        cov_matrix = np.cov(sr, br)
        beta = float(cov_matrix[0, 1] / cov_matrix[1, 1]) if cov_matrix[1, 1] != 0 else 1
        alpha = float(sr.mean() - beta * br.mean())
        alpha_ann = float(alpha * td)
        corr = float(np.corrcoef(sr, br)[0, 1])

        # R-squared
        ss_res = ((sr - (alpha + beta * br)) ** 2).sum()
        ss_tot = ((sr - sr.mean()) ** 2).sum()
        r_squared = float(1 - ss_res / ss_tot) if ss_tot != 0 else 0

        # 上行/下行捕获率
        up_mask = br > 0
        down_mask = br < 0
        up_capture = float(sr[up_mask].mean() / br[up_mask].mean()) if up_mask.any() and br[up_mask].mean() != 0 else 0
        down_capture = float(sr[down_mask].mean() / br[down_mask].mean()) if down_mask.any() and br[down_mask].mean() != 0 else 0

        # 胜率
        win_rate = float((sr > br).mean())

        # t检验：超额收益是否显著
        t_stat, t_p = stats.ttest_1samp(excess, 0)

        data = {
            "股票累计收益率": round(stock_cum, 6),
            "基准累计收益率": round(bench_cum, 6),
            "超额收益率(累计)": round(excess_cum, 6),
            "股票年化收益率": round(stock_ann, 6),
            "基准年化收益率": round(bench_ann, 6),
            "年化超额收益": round(excess_ann, 6),
            "Beta": round(beta, 4),
            "Alpha(日)": round(alpha, 6),
            "Alpha(年化)": round(alpha_ann, 6),
            "相关系数": round(corr, 4),
            "R-squared": round(r_squared, 4),
            "Tracking_Error": round(tracking_error, 6),
            "Information_Ratio": round(info_ratio, 4),
            "上行捕获率": round(up_capture, 4),
            "下行捕获率": round(down_capture, 4),
            "胜率(股票>基准)": round(win_rate, 4),
            "超额收益t统计量": round(float(t_stat), 4),
            "超额收益p值": round(float(t_p), 6),
            "样本量": n,
        }

        # 滚动相关和Beta
        if n >= 60:
            roll_corr = sr.rolling(60).corr(br)
            roll_beta = sr.rolling(60).cov(br) / br.rolling(60).var()
            data["滚动相关系数均值(60日)"] = round(float(roll_corr.mean()), 4)
            data["滚动Beta均值(60日)"] = round(float(roll_beta.mean()), 4)

        result.data = data
        result.success = True

        # 中文解读
        parts = []
        parts.append(f"在 {n} 个交易日内，股票累计收益 {stock_cum*100:.2f}%，基准累计收益 {bench_cum*100:.2f}%。")
        parts.append(f"超额收益为 {excess_cum*100:.2f}%，年化超额收益 {excess_ann*100:.2f}%。")
        parts.append(f"Beta = {beta:.3f}，{'系统性风险高于市场' if beta > 1.2 else '系统性风险低于市场' if beta < 0.8 else '系统性风险接近市场'}。")
        parts.append(f"年化 Alpha = {alpha_ann*100:.4f}%，{'具有正向超额收益能力' if alpha_ann > 0 else '未能产生正向超额收益'}。")
        parts.append(f"相关系数 = {corr:.3f}，{'与基准高度相关' if corr > 0.7 else '与基准中度相关' if corr > 0.4 else '与基准相关性较低'}。")
        parts.append(f"上行捕获率 = {up_capture:.3f}，{'上涨时跑赢基准' if up_capture > 1 else '上涨时跑输基准'}。")
        parts.append(f"下行捕获率 = {down_capture:.3f}，{'下跌时抗跌性好' if down_capture < 1 else '下跌时跌幅超过基准'}。")
        parts.append(f"Information Ratio = {info_ratio:.3f}，{'每单位主动风险获得较好的超额收益' if info_ratio > 0.5 else '主动管理效率一般'}。")

        if t_p < 0.05:
            parts.append(f"超额收益 t 检验 p值={t_p:.4f} < 0.05，超额收益统计显著。")
        else:
            parts.append(f"超额收益 t 检验 p值={t_p:.4f} >= 0.05，超额收益不显著。")

        result.interpretation = "\n".join(parts)

    except Exception as e:
        result.error = f"基准比较分析失败: {str(e)}"
        logger.error(result.error)

    return result