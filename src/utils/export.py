"""Export utilities for CSV, Excel, JSON, Markdown, HTML."""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils.formatting import COLUMN_FORMAT


def export_csv(df: pd.DataFrame, path: Path, index: bool = False) -> Path:
    """Export DataFrame to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")
    return path


def export_excel(df: pd.DataFrame, path: Path, sheet_name: str = "筛选结果") -> Path:
    """Export DataFrame to Excel with formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]
        # Auto-fit column widths
        for i, col in enumerate(df.columns, 1):
            display = COLUMN_FORMAT.get(col, (col, None, 100))
            ws.column_dimensions[chr(64 + i) if i <= 26 else "A"].width = max(display[2] // 6, 10)
    return path


def export_json(data: dict, path: Path, indent: int = 2) -> Path:
    """Export dict to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    class _Encoder(json.JSONEncoder):
        def default(self, o):
            if hasattr(o, "isoformat"):
                return o.isoformat()
            if hasattr(o, "item"):
                return o.item()
            return super().default(o)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, cls=_Encoder)
    return path


def export_markdown(content: str, path: Path) -> Path:
    """Export markdown string to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def export_html(content: str, path: Path) -> Path:
    """Export HTML string to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def df_to_json_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts with NaN handling."""
    records = df.where(df.notna(), None).to_dict(orient="records")
    return records


__all__ = [
    "export_csv", "export_excel", "export_json",
    "export_markdown", "export_html", "df_to_json_records",
]
