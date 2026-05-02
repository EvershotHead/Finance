"""报告生成模块 - 生成 JSON/HTML/Markdown/CSV 报告"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from jinja2 import Template

from finweb_src.utils.logger import get_logger
from finweb_src.utils.export import save_json, save_html, save_markdown, save_csv

logger = get_logger("Report")


def _safe_get(obj, field, default=None):
    """安全获取对象属性或字典值（兼容 dataclass 和 dict）"""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


def _clean_for_json(data: Any) -> Any:
    """递归清理数据，移除不可序列化的对象"""
    if isinstance(data, dict):
        return {k: _clean_for_json(v) for k, v in data.items() if k not in ("figures", "_sr", "strategy_nv", "benchmark_nv")}
    elif isinstance(data, list):
        return [_clean_for_json(item) for item in data]
    elif isinstance(data, pd.Series):
        return data.to_list()
    elif isinstance(data, pd.DataFrame):
        return data.to_dict(orient="records")
    elif hasattr(data, "item"):  # numpy 类型
        return data.item()
    return data


def generate_json_report(meta: Dict, results: Dict, filepath: str) -> str:
    """生成 JSON 报告
    
    Args:
        meta: 元信息字典
        results: 所有分析结果
        filepath: 输出路径
        
    Returns:
        实际保存路径
    """
    report = {
        "meta": {
            **meta,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    for key, value in results.items():
        # 将 dataclass 对象转为 dict
        if hasattr(value, "__dataclass_fields__"):
            value = {k: getattr(value, k) for k in value.__dataclass_fields__}
        report[key] = _clean_for_json(value)
    
    return save_json(report, filepath)


def generate_csv_export(df: pd.DataFrame, filepath: str) -> str:
    """导出清洗后的 CSV 数据
    
    Args:
        df: 股票数据 DataFrame
        filepath: 输出路径
        
    Returns:
        实际保存路径
    """
    return save_csv(df, filepath)


def generate_markdown_report(meta: Dict, results: Dict, filepath: str) -> str:
    """生成 Markdown 报告
    
    Args:
        meta: 元信息字典
        results: 所有分析结果
        filepath: 输出路径
        
    Returns:
        实际保存路径
    """
    sn = meta.get("stock_name", "")
    sc = meta.get("stock_code", "")
    
    lines = [
        f"# {sn}({sc}) 量化分析报告",
        "",
        f"- **分析区间**: {meta.get('start_date', '')} ~ {meta.get('end_date', '')}",
        f"- **基准指数**: {meta.get('benchmark', '')}",
        f"- **数据源**: {meta.get('data_source', '')}",
        f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]
    
    # 各分析模块
    section_map = [
        ("performance", "行情表现"),
        ("return_distribution", "收益率分布"),
        ("risk_metrics", "风险指标"),
        ("benchmark_comparison", "基准比较"),
        ("ols_capm", "OLS/CAPM 回归"),
        ("time_series_tests", "时间序列检验"),
        ("garch", "GARCH 波动率模型"),
        ("technical_indicators", "技术指标"),
        ("fundamental", "基本面分析"),
        ("liquidity", "流动性分析"),
        ("backtesting", "策略回测"),
        ("score", "综合评分"),
    ]
    
    for key, title in section_map:
        r = results.get(key)
        if not r or not _safe_get(r, "success"):
            continue
            
        lines.append(f"## {title}")
        lines.append("")
        
        # 解读文本
        interp = _safe_get(r, "interpretation", "")
        if interp:
            lines.append(interp)
            lines.append("")
        
        # 数据表格
        data = _safe_get(r, "data", {})
        if data and isinstance(data, dict):
            lines.append("| 指标 | 值 |")
            lines.append("|------|-----|")
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    continue
                lines.append(f"| {k} | {v} |")
            lines.append("")
    
    # 结论
    conclusion = results.get("conclusion", {})
    if conclusion:
        lines.append("## 核心结论")
        lines.append("")
        for s in conclusion.get("summary", []):
            lines.append(f"- {s}")
        
        if conclusion.get("strengths"):
            lines.append("")
            lines.append("### 优点")
            for s in conclusion["strengths"]:
                lines.append(f"- {s}")
        
        if conclusion.get("risks"):
            lines.append("")
            lines.append("### 风险点")
            for s in conclusion["risks"]:
                lines.append(f"- {s}")
    
    # 免责声明
    lines.extend([
        "",
        "## 免责声明",
        "",
        "本报告基于历史数据自动生成，仅供学习和研究参考，不构成任何投资建议。",
        "投资者应独立判断并承担投资风险。历史表现不代表未来。",
        ""
    ])
    
    content = "\n".join(lines)
    return save_markdown(content, filepath)


def generate_html_report(meta: Dict, results: Dict, filepath: str) -> str:
    """生成 HTML 报告
    
    Args:
        meta: 元信息字典
        results: 所有分析结果
        filepath: 输出路径
        
    Returns:
        实际保存路径
    """
    template_path = Path(__file__).parent / "templates" / "report.html"
    
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            tmpl = Template(f.read())
        html = tmpl.render(
            meta=meta,
            results=results,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    else:
        # 如果模板不存在，生成简单 HTML
        html = _generate_simple_html(meta, results)
    
    return save_html(html, filepath)


def _generate_simple_html(meta: Dict, results: Dict) -> str:
    """生成简单 HTML 报告（无模板时使用）"""
    sn = meta.get("stock_name", "")
    sc = meta.get("stock_code", "")
    
    sections_html = ""
    section_map = [
        ("performance", "行情表现"),
        ("risk_metrics", "风险指标"),
        ("benchmark_comparison", "基准比较"),
        ("ols_capm", "OLS/CAPM"),
        ("technical_indicators", "技术指标"),
        ("score", "综合评分"),
    ]
    
    for key, title in section_map:
        r = results.get(key)
        if r and _safe_get(r, "success"):
            interp = _safe_get(r, "interpretation", "").replace("\n", "<br>")
            sections_html += f"<h2>{title}</h2><p style='background:#e8f4fd;padding:10px;border-left:3px solid #1f77b4;'>{interp}</p>\n"
            
            data = _safe_get(r, "data", {})
            if data:
                sections_html += "<table border='1' cellpadding='8' style='border-collapse:collapse;margin:10px 0;'>"
                sections_html += "<tr><th>指标</th><th>值</th></tr>"
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        continue
                    sections_html += f"<tr><td>{k}</td><td>{v}</td></tr>"
                sections_html += "</table>"
    
    conclusion = results.get("conclusion", {})
    conclusion_html = ""
    for s in conclusion.get("summary", []):
        conclusion_html += f"<li>{s}</li>\n"
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{sn}({sc}) 量化分析报告</title>
<style>
body {{ font-family: "Microsoft YaHei", sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; color: #333; }}
h1 {{ color: #1f77b4; border-bottom: 2px solid #1f77b4; padding-bottom: 10px; }}
h2 {{ color: #2c3e50; margin-top: 30px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f5f5f5; }}
.meta {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
.disclaimer {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 30px; }}
</style>
</head>
<body>
<h1>{sn}({sc}) 量化分析报告</h1>
<div class="meta">
<p><strong>分析区间</strong>: {meta.get('start_date', '')} ~ {meta.get('end_date', '')}</p>
<p><strong>基准指数</strong>: {meta.get('benchmark', '')}</p>
<p><strong>数据源</strong>: {meta.get('data_source', '')}</p>
</div>
{sections_html}
<h2>核心结论</h2>
<ul>{conclusion_html}</ul>
<div class="disclaimer">
<h2>免责声明</h2>
<p>本报告基于历史数据自动生成，仅供学习和研究参考，不构成任何投资建议。投资者应独立判断并承担投资风险。</p>
</div>
</body>
</html>"""