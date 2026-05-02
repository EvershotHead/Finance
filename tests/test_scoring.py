"""Tests for scoring module."""

import pandas as pd
import numpy as np
import pytest

from src.screener.scoring import (
    winsorize, percentile_rank, compute_scores, load_weights,
    compute_sub_score, _pe_special_score, _moderate_score, _rsi_score,
)


class TestWinsorize:
    def test_basic(self):
        s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 100])
        result = winsorize(s, 0.1, 0.9)
        assert result.max() <= 100
        assert result.min() >= 1

    def test_with_nan(self):
        s = pd.Series([1, 2, np.nan, 4, 5])
        result = winsorize(s)
        assert pd.isna(result.iloc[2])


class TestPercentileRank:
    def test_higher_better(self):
        s = pd.Series([10, 20, 30, 40, 50])
        result = percentile_rank(s, higher_better=True)
        assert result.iloc[0] < result.iloc[-1]

    def test_lower_better(self):
        s = pd.Series([10, 20, 30, 40, 50])
        result = percentile_rank(s, higher_better=False)
        assert result.iloc[0] > result.iloc[-1]

    def test_with_nan(self):
        s = pd.Series([10, np.nan, 30, 40, 50])
        result = percentile_rank(s)
        assert pd.isna(result.iloc[1])


class TestPESpecialScore:
    def test_negative_pe(self):
        pe = pd.Series([-5, 10, 20, -10])
        scores = _pe_special_score(pe)
        assert scores.iloc[0] < scores.iloc[1]  # negative < positive
        assert scores.iloc[3] < scores.iloc[1]

    def test_extreme_pe(self):
        pe = pd.Series([10, 300, 20, np.nan])
        scores = _pe_special_score(pe)
        assert scores.iloc[1] < scores.iloc[0]  # extreme < normal
        assert pd.isna(scores.iloc[3]) is False  # NaN gets low score, not NaN

    def test_reasonable_pe(self):
        pe = pd.Series([5, 10, 15, 20, 25])
        scores = _pe_special_score(pe)
        assert scores.iloc[0] > scores.iloc[-1]  # lower PE = higher score


class TestComputeScores:
    def test_basic(self, sample_features_df):
        result = compute_scores(sample_features_df, "balanced")
        assert "total_score" in result.columns
        assert "return_score" in result.columns
        assert "risk_score" in result.columns
        assert result["total_score"].between(0, 100).all() or result["total_score"].isna().all()

    def test_different_profiles(self, sample_features_df):
        balanced = compute_scores(sample_features_df, "balanced")
        risk_averse = compute_scores(sample_features_df, "risk_averse")
        # Both should produce valid scores (0-100 range or NaN)
        for df in [balanced, risk_averse]:
            valid = df["total_score"].dropna()
            if len(valid) > 0:
                assert valid.between(0, 100).all()


class TestLoadWeights:
    def test_balanced(self):
        weights = load_weights("balanced")
        assert "return_score" in weights
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_unknown_profile(self):
        weights = load_weights("nonexistent_profile")
        assert "return_score" in weights  # falls back to balanced
