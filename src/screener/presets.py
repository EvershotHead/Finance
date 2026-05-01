"""Preset screening templates — loads from YAML config."""

from pathlib import Path
from typing import Optional

import yaml

from src.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PRESETS_PATH = PROJECT_ROOT / "configs" / "screener_presets.yaml"


def load_preset(name: str) -> Optional[dict]:
    """Load a preset screening configuration by name."""
    try:
        with open(PRESETS_PATH, "r", encoding="utf-8") as f:
            presets = yaml.safe_load(f)
        if name in presets:
            return presets[name]
        logger.warning(f"Preset '{name}' not found. Available: {list(presets.keys())}")
        return None
    except Exception as e:
        logger.error(f"Failed to load presets: {e}")
        return None


def available_presets() -> dict[str, dict]:
    """Return all available presets with their names and descriptions."""
    try:
        with open(PRESETS_PATH, "r", encoding="utf-8") as f:
            presets = yaml.safe_load(f)
        return {
            k: {"name": v.get("name", k), "description": v.get("description", ""),
                 "risk_warning": v.get("risk_warning", "")}
            for k, v in presets.items()
        }
    except Exception as e:
        logger.error(f"Failed to load presets: {e}")
        return {}


def get_preset_names() -> list[str]:
    """Return list of preset names."""
    return list(available_presets().keys())


def get_preset_display() -> dict[str, str]:
    """Return mapping of preset_key → display_name."""
    return {k: v["name"] for k, v in available_presets().items()}


__all__ = ["load_preset", "available_presets", "get_preset_names", "get_preset_display"]
