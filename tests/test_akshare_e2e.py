"""端到端测试：通过 AKShareFetcher 直接调用 4 类接口，确认更新后可用。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.akshare_fetcher import AKShareFetcher

f = AKShareFetcher()
STOCK = "300658"
INDEX = "000300"
START = "2024-01-01"
END = "2024-06-01"


def show(label, r):
    print(f"\n=== {label} ===")
    print(f"  success={r.success}  source={r.source}  type={r.data_type}")
    if r.error:
        print(f"  error={r.error}")
    if r.warnings:
        print(f"  warnings={r.warnings}")
    if r.success and r.data is not None:
        print(f"  rows={len(r.data)}  cols={list(r.data.columns)[:14]}")
        try:
            print(r.data.head(2).to_string())
        except Exception:
            pass


show("fetch_daily qfq", f.fetch_daily(STOCK, START, END, "qfq"))
show("fetch_daily hfq", f.fetch_daily(STOCK, START, END, "hfq"))
show("fetch_index_daily 000300", f.fetch_index_daily(INDEX, START, END))
show("fetch_index_daily 399001 (深证成指)", f.fetch_index_daily("399001", START, END))
show("fetch_fundamental", f.fetch_fundamental(STOCK, START, END))
show("fetch_financial", f.fetch_financial(STOCK))
show("fetch_money_flow", f.fetch_money_flow(STOCK, START, END))
