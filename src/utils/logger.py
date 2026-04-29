"""日志模块 - 使用 loguru 提供统一日志管理"""

import sys
from loguru import logger

# 移除默认处理器
logger.remove()

# 控制台输出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# 文件输出
logger.add(
    "outputs/logs/app_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    encoding="utf-8",
)


def get_logger(name: str = "stock_quant"):
    """获取带有模块名称的 logger 实例"""
    return logger.bind(module=name)