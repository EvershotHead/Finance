"""配置管理模块 - 使用 Pydantic 管理全局配置"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"

# 加载 .env 文件
load_dotenv(PROJECT_ROOT / ".env")


class DataConfig(BaseModel):
    """数据源配置"""
    default: str = Field(default="auto", description="默认数据源: auto/akshare/tushare")
    cache_enabled: bool = Field(default=True, description="是否启用缓存")
    cache_expire_hours: int = Field(default=24, description="缓存过期时间(小时)")


class AnalysisConfig(BaseModel):
    """分析参数配置"""
    trading_days_per_year: int = Field(default=252, description="年化交易日数")
    default_risk_free_rate: float = Field(default=0.02, description="默认无风险利率(年化)")
    var_confidence_levels: list[float] = Field(default=[0.95, 0.99], description="VaR置信度")
    rolling_windows: list[int] = Field(default=[20, 60, 120], description="滚动窗口大小")
    arma_max_p: int = Field(default=3, description="ARMA最大p值")
    arma_max_q: int = Field(default=3, description="ARMA最大q值")
    garch_model: str = Field(default="GARCH", description="GARCH模型类型")
    garch_p: int = Field(default=1, description="GARCH p参数")
    garch_q: int = Field(default=1, description="GARCH q参数")
    garch_distribution: str = Field(default="t", description="GARCH分布假设")
    backtest_commission: float = Field(default=0.0003, description="回测交易费率")


class TechnicalConfig(BaseModel):
    """技术指标参数配置"""
    ma_periods: list[int] = Field(default=[5, 10, 20, 60, 120], description="均线周期")
    ema_periods: list[int] = Field(default=[12, 26], description="EMA周期")
    macd_signal: int = Field(default=9, description="MACD信号线周期")
    rsi_periods: list[int] = Field(default=[6, 14, 24], description="RSI周期")
    bollinger_period: int = Field(default=20, description="布林带周期")
    bollinger_std: float = Field(default=2.0, description="布林带标准差倍数")
    atr_period: int = Field(default=14, description="ATR周期")


class OutputConfig(BaseModel):
    """输出配置"""
    decimal_places: int = Field(default=4, description="小数位数")
    chart_theme: str = Field(default="plotly_white", description="图表主题")


class AppConfig(BaseModel):
    """应用总配置"""
    data: DataConfig = Field(default_factory=DataConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    technical: TechnicalConfig = Field(default_factory=TechnicalConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    benchmarks: dict[str, str] = Field(
        default={
            "000300": "沪深300",
            "000001": "上证指数",
            "399001": "深证成指",
            "399006": "创业板指",
            "000905": "中证500",
            "000852": "中证1000",
        },
        description="基准指数映射"
    )
    default_period_days: int = Field(default=1095, description="默认分析区间(天)")

    @property
    def tushare_token(self) -> str:
        """从环境变量获取 Tushare Token"""
        return os.getenv("TUSHARE_TOKEN", "")


def load_config() -> AppConfig:
    """加载配置文件

    优先从 config.yaml 加载，使用默认值填充缺失字段
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return AppConfig(
            data=DataConfig(**raw.get("data_source", {})),
            analysis=AnalysisConfig(**raw.get("analysis", {})),
            technical=TechnicalConfig(**raw.get("technical", {})),
            output=OutputConfig(**raw.get("output", {})),
            benchmarks=raw.get("benchmarks", AppConfig.model_fields["benchmarks"].default),
            default_period_days=raw.get("default_period_days", 1095),
        )
    return AppConfig()


# 全局配置单例
config = load_config()