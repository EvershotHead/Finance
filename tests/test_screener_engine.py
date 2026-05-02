"""Tests for the screening engine."""

import pandas as pd
import numpy as np
import pytest

from src.screener.screening_engine import ScreeningEngine
from src.screener.presets import load_preset, available_presets
from src.screener.explanations import generate_reasons, generate_risks
from src.screener.scoring import compute_scores


class TestPresets:
    def test_load_preset(self):
        config = load_preset("balanced")
        assert config is not None
        assert "stages" in config
        assert "ranking" in config

    def test_all_presets_available(self):
        presets = available_presets()
        assert len(presets) >= 8
        assert "balanced" in presets
        assert "risk_averse" in presets

    def test_unknown_preset(self):
        config = load_preset("nonexistent")
        assert config is None


class TestExplanations:
    def test_generate_reasons(self):
        row = pd.Series({
            "ret_20d": 0.1,
            "ret_120d": 0.2,
            "volatility_120d": 0.25,
            "avg_amount_20d": 2e8,
            "pe_ttm": 15,
            "roe": 15,
            "is_ma_bullish": True,
            "total_score": 75,
        })
        reasons = generate_reasons(row)
        assert len(reasons) >= 3
        assert all(isinstance(r, str) for r in reasons)

    def test_generate_risks(self):
        row = pd.Series({
            "is_st": 1,
            "max_drawdown_120d": -0.3,
            "pe_ttm": -5,
            "data_quality_score": 50,
        })
        risks = generate_risks(row)
        assert len(risks) >= 1
        assert any("ST" in r for r in risks)

    def test_no_risks(self):
        row = pd.Series({
            "is_st": 0,
            "max_drawdown_120d": -0.05,
            "pe_ttm": 15,
            "volatility_120d": 0.2,
            "avg_amount_20d": 5e8,
            "listing_days": 1000,
            "beta_120d": 1.0,
            "data_quality_score": 90,
        })
        risks = generate_risks(row)
        assert len(risks) >= 1  # At least generic risk


class TestScoring:
    def test_compute_scores(self, sample_features_df):
        result = compute_scores(sample_features_df, "balanced")
        assert "total_score" in result.columns
        assert "return_score" in result.columns
        # Scores should be between 0 and 100 (or NaN)
        valid = result["total_score"].dropna()
        if len(valid) > 0:
            assert valid.between(0, 100).all()


class TestScreeningEngine:
    def test_empty_features(self, monkeypatch):
        engine = ScreeningEngine()
        # Mock feature store to return None
        monkeypatch.setattr("src.storage.feature_store.load_latest_features", lambda: None)
        assert engine.load_features() is False

    def test_run_custom(self, sample_features_df, sample_filter_config, monkeypatch):
        engine = ScreeningEngine()
        engine._features = sample_features_df

        result = engine.run_custom(sample_filter_config)
        assert result is not None
        assert result.total_before == 100
        assert len(result.candidates) <= 20

    def test_empty_result(self, sample_features_df):
        engine = ScreeningEngine()
        engine._features = sample_features_df

        # Very restrictive filter
        config = {
            "universe": {"exclude_st": True, "min_listing_days": 180, "min_data_quality_score": 60},
            "stages": [
                {"name": "impossible", "logic": "AND", "rules": [
                    {"field": "pe_ttm", "operator": ">", "value": 10000},
                ]},
            ],
            "ranking": {"score_model": "balanced", "sort_by": "total_score", "ascending": False, "top_n": 50},
        }
        result = engine.run_custom(config)
        assert result is not None
        assert len(result.candidates) == 0
