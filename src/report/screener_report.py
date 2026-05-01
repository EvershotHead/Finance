"""Screener report generation using Jinja2."""

from pathlib import Path
from datetime import datetime

import pandas as pd

from src.utils.logger import logger

try:
    from jinja2 import Environment, FileSystemLoader
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

TEMPLATE_DIR = Path(__file__).parent / "templates"


def generate_html_report(candidates: pd.DataFrame, result, config: dict = None) -> str:
    """Generate HTML report from screening results."""
    if not HAS_JINJA2:
        return _fallback_html(candidates, result)

    try:
        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        template = env.get_template("screener_report.html")
        return template.render(
            candidates=candidates,
            result=result,
            config=config or {},
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_before=result.total_before,
            total_after=result.total_after,
        )
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        return _fallback_html(candidates, result)


def generate_markdown_report(candidates: pd.DataFrame, result, config: dict = None) -> str:
    """Generate Markdown report."""
    if not HAS_JINJA2:
        return _fallback_markdown(candidates, result)

    try:
        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        template = env.get_template("screener_report.md")
        return template.render(
            candidates=candidates,
            result=result,
            config=config or {},
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        return _fallback_markdown(candidates, result)


def _fallback_html(df: pd.DataFrame, result) -> str:
    """Fallback HTML report without Jinja2."""
    rows = ""
    for i, (_, row) in enumerate(df.head(50).iterrows(), 1):
        rows += f"<tr><td>{i}</td><td>{row.get('stock_code','')}</td><td>{row.get('stock_name','')}</td>"
        rows += f"<td>{row.get('industry','')}</td><td>{row.get('total_score',0):.1f}</td></tr>\n"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>A股智能选股报告</title></head>
<body>
<h1>A股智能选股筛选报告</h1>
<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p>筛选前: {result.total_before} 只 | 筛选后: {result.total_after} 只</p>
<table border="1"><tr><th>排名</th><th>代码</th><th>名称</th><th>行业</th><th>评分</th></tr>
{rows}</table>
<p><b>免责声明</b>: 本报告仅供学习和辅助分析，不构成投资建议。</p>
</body></html>"""


def _fallback_markdown(df: pd.DataFrame, result) -> str:
    """Fallback Markdown report without Jinja2."""
    lines = [
        "# A股智能选股筛选报告\n\n",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        f"筛选前: {result.total_before} 只 | 筛选后: {result.total_after} 只\n\n",
        "| 排名 | 代码 | 名称 | 行业 | 评分 |\n",
        "|------|------|------|------|------|\n",
    ]
    for i, (_, row) in enumerate(df.head(50).iterrows(), 1):
        lines.append(f"| {i} | {row.get('stock_code','')} | {row.get('stock_name','')} | {row.get('industry','')} | {row.get('total_score',0):.1f} |\n")
    lines.append("\n---\n**免责声明**: 本报告仅供学习和辅助分析，不构成投资建议。\n")
    return "".join(lines)


__all__ = ["generate_html_report", "generate_markdown_report"]
