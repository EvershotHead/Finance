"""端到端测试 DataManager.fetch_all → preprocess → 各分析模块。
确认 AKShare 路径全程跑通。
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.data_manager import DataManager
from src.analysis.preprocessing import preprocess
from src.analysis.performance import analyze_performance
from src.analysis.risk_metrics import analyze_risk
from src.analysis.benchmark_comparison import analyze_benchmark
from src.analysis.fundamental import analyze_fundamental
from src.analysis.technical_indicators import analyze_technical

# 强制只用 akshare，确认这个路径独立可用
dm = DataManager(source="akshare")
bundle = dm.fetch_all(
    stock_code="300658",
    stock_name="延江股份",
    start_date="2024-01-01",
    end_date="2024-06-01",
    benchmark_code="000300",
    adjust="qfq",
)

print("=== bundle ===")
print(f"  source_used = {bundle.source_used}")
print(f"  daily rows = {0 if bundle.daily is None else len(bundle.daily)}")
print(f"  index rows = {0 if bundle.index_daily is None else len(bundle.index_daily)}")
print(f"  fundamental rows = {0 if bundle.fundamental is None else len(bundle.fundamental)}")
print(f"  financial rows = {0 if bundle.financial is None else len(bundle.financial)}")
print(f"  money_flow rows = {0 if bundle.money_flow is None else len(bundle.money_flow)}")
print(f"  warnings = {bundle.warnings}")

if bundle.daily is None or bundle.daily.empty:
    print("FAIL: 主行情未获取，停止")
    sys.exit(1)

processed = preprocess(bundle, benchmark_name="沪深300")
print(f"\n=== processed ===")
print(f"  stock_df rows = {len(processed.stock_df)}")
print(f"  cols = {list(processed.stock_df.columns)}")

returns = processed.stock_df["simple_return"].dropna()
rf = 0.02

perf = analyze_performance(processed.stock_df, rf)
print(f"\n=== performance ===  success={perf.success}")
print(f"  data keys: {list(perf.data.keys())[:6]}")

risk = analyze_risk(processed.stock_df, rf)
print(f"\n=== risk ===  success={risk.success}")
print(f"  data keys: {list(risk.data.keys())[:6]}")

if processed.index_df is not None and not processed.index_df.empty:
    bench = analyze_benchmark(processed.stock_df, processed.index_df, rf)
    print(f"\n=== benchmark ===  success={bench.success}")
    print(f"  data keys: {list(bench.data.keys())[:6]}")

fund = analyze_fundamental(bundle.fundamental, bundle.financial)
print(f"\n=== fundamental ===  success={fund.success}")
print(f"  data keys: {list(fund.data.keys())[:8]}")
print(f"  interp: {fund.interpretation[:200]}")

tech = analyze_technical(processed.stock_df)
print(f"\n=== technical ===  success={tech.success}")
print(f"  data keys: {list(tech.data.keys())[:6]}")

print("\n✅ E2E AKShare 路径通过")
