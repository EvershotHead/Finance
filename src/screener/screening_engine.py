"""Screening engine — orchestrates filtering, scoring, and explanations."""

from pathlib import Path
from typing import Optional

import pandas as pd

from src.screener.filter_dsl import (
    FilterDSL, FilterResult, parse_filter_config, execute_filter,
)
from src.screener.scoring import compute_scores
from src.screener.explanations import generate_reasons, generate_risks
from src.screener.presets import load_preset, available_presets
from src.storage import feature_store
from src.utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class ScreeningEngine:
    """Main screening engine that orchestrates the full pipeline."""

    def __init__(self):
        self._features: Optional[pd.DataFrame] = None

    def load_features(self) -> bool:
        """Load features from feature store."""
        df = feature_store.load_latest_features()
        if df is None or len(df) == 0:
            logger.warning("No features available in feature store")
            return False
        self._features = df
        logger.info(f"Loaded {len(df)} stocks from feature store")
        return True

    @property
    def features(self) -> Optional[pd.DataFrame]:
        return self._features

    def run_preset(
        self,
        preset_name: str,
        top_n: Optional[int] = None,
        overrides: Optional[dict] = None,
    ) -> Optional[FilterResult]:
        """Run a preset screening template.

        Args:
            preset_name: Name of preset from configs/screener_presets.yaml
            top_n: Override top N
            overrides: Dict of overrides to merge into preset config

        Returns:
            FilterResult or None if features not loaded
        """
        if self._features is None:
            if not self.load_features():
                return None

        config_dict = load_preset(preset_name)
        if config_dict is None:
            logger.error(f"Preset '{preset_name}' not found")
            return None

        # Apply overrides
        if overrides:
            config_dict = _merge_overrides(config_dict, overrides)
        if top_n is not None:
            config_dict.setdefault("ranking", {})["top_n"] = top_n

        return self._execute(config_dict)

    def run_custom(self, config_dict: dict) -> Optional[FilterResult]:
        """Run a custom screening configuration."""
        if self._features is None:
            if not self.load_features():
                return None
        return self._execute(config_dict)

    def _execute(self, config_dict: dict) -> Optional[FilterResult]:
        """Execute screening pipeline."""
        config = parse_filter_config(config_dict)

        # Score features
        score_model = config.ranking.score_model
        scored = compute_scores(self._features, weights_profile=score_model)

        # Execute filter
        result = execute_filter(scored, config)

        # Generate explanations
        if len(result.candidates) > 0:
            result.candidates = _add_explanations(result.candidates, config_dict)

        logger.info(f"Screening complete: {result.total_before} → {result.total_after} stocks")
        return result

    def get_available_fields(self) -> list[str]:
        """Return list of fields available for filtering."""
        if self._features is None:
            return []
        return sorted(self._features.columns.tolist())


def _add_explanations(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Add reasons and risks columns to results."""
    df = df.copy()
    reasons_list = []
    risks_list = []

    for _, row in df.iterrows():
        reasons = generate_reasons(row, config)
        risks = generate_risks(row)
        reasons_list.append(reasons)
        risks_list.append(risks)

    df["reasons"] = reasons_list
    df["risks"] = risks_list
    return df


def _merge_overrides(base: dict, overrides: dict) -> dict:
    """Deep merge overrides into base config."""
    import copy
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key].update(value)
        else:
            result[key] = value
    return result


__all__ = ["ScreeningEngine"]
