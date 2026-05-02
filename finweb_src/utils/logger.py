"""Logging configuration using loguru."""

import sys
from pathlib import Path
from loguru import logger

# Only configure handlers if not already done (avoid overwriting stock_quant's logger)
if not logger._core.handlers:
    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )

    # File handler
    LOG_DIR = Path(__file__).resolve().parent.parent.parent / "outputs" / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.add(
        LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        encoding="utf-8",
    )

def get_logger(name: str = "finweb"):
    """获取带有模块名称的 logger 实例"""
    return logger.bind(module=name)


__all__ = ["logger", "get_logger"]
