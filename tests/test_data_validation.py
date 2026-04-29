"""数据校验测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.validators import parse_stock_code, parse_benchmark_code


def test_parse_stock_code_sz():
    """测试深交所股票代码解析"""
    r = parse_stock_code("300658")
    assert r["pure_code"] == "300658"
    assert r["suffix"] == ".SZ"
    assert r["tushare_code"] == "300658.SZ"


def test_parse_stock_code_sh():
    """测试上交所股票代码解析"""
    r = parse_stock_code("600000")
    assert r["pure_code"] == "600000"
    assert r["suffix"] == ".SH"
    assert r["tushare_code"] == "600000.SH"


def test_parse_stock_code_with_suffix():
    """测试带后缀的股票代码"""
    r = parse_stock_code("000001.SZ")
    assert r["pure_code"] == "000001"
    assert r["suffix"] == ".SZ"


def test_parse_benchmark_code():
    """测试基准指数代码解析"""
    r = parse_benchmark_code("000300")
    assert r["pure_code"] == "000300"
    assert r["tushare_code"] == "000300.SH"


def test_parse_benchmark_by_name():
    """测试按名称解析基准指数"""
    r = parse_benchmark_code("沪深300")
    assert r["pure_code"] == "000300"