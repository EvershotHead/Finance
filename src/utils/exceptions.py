"""Custom exceptions for stock quant analyzer."""


class StockAnalyzerError(Exception):
    """Base exception."""


class DataFetchError(StockAnalyzerError):
    """Error fetching data from external source."""

    def __init__(self, source: str, message: str, symbol: str = ""):
        self.source = source
        self.symbol = symbol
        super().__init__(f"[{source}] {message}" + (f" (symbol={symbol})" if symbol else ""))


class DataQualityError(StockAnalyzerError):
    """Data quality check failed."""


class ScreenerError(StockAnalyzerError):
    """Error in screening engine."""


class FilterParseError(ScreenerError):
    """Error parsing filter DSL."""


class ConfigError(StockAnalyzerError):
    """Configuration error."""


class StorageError(StockAnalyzerError):
    """Storage read/write error."""


class FeatureStoreError(StockAnalyzerError):
    """Feature store not available or corrupted."""


__all__ = [
    "StockAnalyzerError", "DataFetchError", "DataQualityError",
    "ScreenerError", "FilterParseError", "ConfigError",
    "StorageError", "FeatureStoreError",
]
