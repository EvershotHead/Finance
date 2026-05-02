"""Tests for filter DSL."""

import pandas as pd
import numpy as np
import pytest

from src.screener.filter_dsl import (
    apply_operator, FilterRule, FilterStage, UniverseConfig,
    FilterDSL, parse_filter_config, execute_filter, apply_universe_filter, apply_stage,
)


class TestApplyOperator:
    def test_eq(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = apply_operator(s, "=", 3)
        assert result.tolist() == [False, False, True, False, False]

    def test_neq(self):
        s = pd.Series([1, 2, 3])
        result = apply_operator(s, "!=", 2)
        assert result.tolist() == [True, False, True]

    def test_gt(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = apply_operator(s, ">", 3)
        assert result.tolist() == [False, False, False, True, True]

    def test_gte(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = apply_operator(s, ">=", 3)
        assert result.tolist() == [False, False, True, True, True]

    def test_lt(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = apply_operator(s, "<", 3)
        assert result.tolist() == [True, True, False, False, False]

    def test_lte(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = apply_operator(s, "<=", 3)
        assert result.tolist() == [True, True, True, False, False]

    def test_between(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = apply_operator(s, "between", [2, 4])
        assert result.tolist() == [False, True, True, True, False]

    def test_in(self):
        s = pd.Series(["a", "b", "c", "d"])
        result = apply_operator(s, "in", ["a", "c"])
        assert result.tolist() == [True, False, True, False]

    def test_not_in(self):
        s = pd.Series(["a", "b", "c", "d"])
        result = apply_operator(s, "not in", ["a", "c"])
        assert result.tolist() == [False, True, False, True]

    def test_is_null(self):
        s = pd.Series([1.0, np.nan, 3.0, np.nan])
        result = apply_operator(s, "is_null", None)
        assert result.tolist() == [False, True, False, True]

    def test_not_null(self):
        s = pd.Series([1.0, np.nan, 3.0, np.nan])
        result = apply_operator(s, "not_null", None)
        assert result.tolist() == [True, False, True, False]

    def test_top_pct(self):
        s = pd.Series([10, 20, 30, 40, 50])
        result = apply_operator(s, "top_pct", 40)
        # Top 40% should include the highest values
        assert result.sum() >= 2
        assert result.iloc[-1] is True or result.iloc[-1] == True  # highest value included

    def test_bottom_pct(self):
        s = pd.Series([10, 20, 30, 40, 50])
        result = apply_operator(s, "bottom_pct", 40)
        assert result.sum() == 2


class TestFilterStage:
    def test_and_logic(self):
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [5, 4, 3, 2, 1]})
        stage = FilterStage(name="test", logic="AND", rules=[
            FilterRule(field="a", operator=">=", value=3),
            FilterRule(field="b", operator=">=", value=2),
        ])
        result_df, stage_result = apply_stage(df, stage)
        assert len(result_df) == 2  # a=3,b=3 and a=4,b=2

    def test_or_logic(self):
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
        stage = FilterStage(name="test", logic="OR", rules=[
            FilterRule(field="a", operator="<=", value=2),
            FilterRule(field="a", operator=">=", value=4),
        ])
        result_df, stage_result = apply_stage(df, stage)
        assert len(result_df) == 4  # 1, 2, 4, 5

    def test_empty_stage(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        stage = FilterStage(name="empty")
        result_df, stage_result = apply_stage(df, stage)
        assert len(result_df) == 3

    def test_missing_field(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        stage = FilterStage(name="test", rules=[
            FilterRule(field="nonexistent", operator=">", value=0),
        ])
        result_df, _ = apply_stage(df, stage)
        assert len(result_df) == 3  # field not found, rule skipped


class TestParseFilterConfig:
    def test_parse_basic(self, sample_filter_config):
        config = parse_filter_config(sample_filter_config)
        assert config.universe.exclude_st is True
        assert config.universe.min_listing_days == 180
        assert len(config.stages) == 2
        assert config.ranking.top_n == 20

    def test_parse_stages(self, sample_filter_config):
        config = parse_filter_config(sample_filter_config)
        assert config.stages[0].name == "流动性筛选"
        assert config.stages[0].rules[0].field == "avg_amount_20d"


class TestExecuteFilter:
    def test_full_pipeline(self, sample_features_df, sample_filter_config):
        config = parse_filter_config(sample_filter_config)
        result = execute_filter(sample_features_df, config)
        assert result.total_before == 100
        assert len(result.candidates) <= 20  # top_n=20
        assert len(result.stage_results) >= 1

    def test_universe_filter_st(self):
        df = pd.DataFrame({
            "stock_code": ["A", "B", "C"],
            "is_st": [0, 1, 0],
            "listing_days": [500, 500, 500],
            "data_quality_score": [80, 80, 80],
        })
        config = UniverseConfig(exclude_st=True)
        result = apply_universe_filter(df, config)
        assert len(result) == 2
