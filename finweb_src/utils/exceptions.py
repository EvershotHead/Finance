"""自定义异常模块 - 统一异常处理"""

from typing import Optional


class StockQuantError(Exception):
    """项目基础异常类"""

    def __init__(self, message: str, module: str = "", details: Optional[str] = None):
        self.message = message
        self.module = module
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.module:
            parts.insert(0, f"[{self.module}]")
        if self.details:
            parts.append(f"详情: {self.details}")
        return " ".join(parts)


class DataFetchError(StockQuantError):
    """数据获取失败异常"""

    def __init__(self, source: str, stock_code: str, message: str = "数据获取失败"):
        super().__init__(
            message=message,
            module="DataFetcher",
            details=f"数据源={source}, 股票代码={stock_code}",
        )
        self.source = source
        self.stock_code = stock_code


class DataValidationError(StockQuantError):
    """数据校验失败异常"""

    def __init__(self, field: str, message: str = "数据校验失败"):
        super().__init__(message=message, module="DataValidator", details=f"字段={field}")
        self.field = field


class InsufficientDataError(StockQuantError):
    """数据量不足异常"""

    def __init__(self, required: int, actual: int, module: str = ""):
        super().__init__(
            message=f"数据量不足: 需要至少{required}条数据, 实际仅有{actual}条",
            module=module,
        )
        self.required = required
        self.actual = actual


class ModelConvergenceError(StockQuantError):
    """模型收敛失败异常"""

    def __init__(self, model_name: str, message: str = "模型未能收敛"):
        super().__init__(message=message, module=model_name, details="请检查数据或调整模型参数")
        self.model_name = model_name


class AnalysisError(StockQuantError):
    """分析过程异常"""

    def __init__(self, module: str, message: str, details: Optional[str] = None):
        super().__init__(message=message, module=module, details=details)


class ConfigError(StockQuantError):
    """配置错误异常"""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message=message, module="Config", details=details)