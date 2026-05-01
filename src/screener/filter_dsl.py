"""Filter DSL — parser and executor for stock screening rules."""

from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd
import numpy as np

from src.utils.logger import logger
from src.utils.exceptions import FilterParseError


# ============================================================
# Operators
# ============================================================

def apply_operator(series: pd.Series, operator: str, value: Any) -> pd.Series:
    """Apply a filter operator to a pandas Series.

    Returns boolean Series (True = passes filter).
    """
    if operator == "=":
        return series == value
    elif operator == "!=":
        return series != value
    elif operator == ">":
        return series > value
    elif operator == ">=":
        return series >= value
    elif operator == "<":
        return series < value
    elif operator == "<=":
        return series <= value
    elif operator == "between":
        lo, hi = value if isinstance(value, (list, tuple)) else (value, value)
        return (series >= lo) & (series <= hi)
    elif operator == "in":
        return series.isin(value if isinstance(value, list) else [value])
    elif operator == "not in":
        return ~series.isin(value if isinstance(value, list) else [value])
    elif operator == "is_null":
        return series.isna()
    elif operator == "not_null":
        return series.notna()
    elif operator == "top_n":
        n = int(value)
        return series.rank(ascending=False, method="min") <= n
    elif operator == "bottom_n":
        n = int(value)
        return series.rank(ascending=True, method="min") <= n
    elif operator == "top_pct":
        pct = value / 100.0 if value > 1 else value
        return series.rank(pct=True) >= (1 - pct)
    elif operator == "bottom_pct":
        pct = value / 100.0 if value > 1 else value
        return series.rank(pct=True) <= pct
    elif operator == "percentile_gte":
        threshold = series.quantile(value / 100.0 if value > 1 else value)
        return series >= threshold
    elif operator == "percentile_lte":
        threshold = series.quantile(value / 100.0 if value > 1 else value)
        return series <= threshold
    elif operator == "industry_percentile_gte":
        # This requires industry info — handled at engine level
        return pd.Series(True, index=series.index)
    elif operator == "industry_percentile_lte":
        return pd.Series(True, index=series.index)
    else:
        raise FilterParseError(f"Unknown operator: {operator}")


SUPPORTED_OPERATORS = [
    "=", "!=", ">", ">=", "<", "<=",
    "between", "in", "not in", "is_null", "not_null",
    "top_n", "bottom_n", "top_pct", "bottom_pct",
    "percentile_gte", "percentile_lte",
    "industry_percentile_gte", "industry_percentile_lte",
]


# ============================================================
# Data Classes
# ============================================================

@dataclass
class FilterRule:
    """A single filter rule."""
    field: str
    operator: str
    value: Any

    def validate(self):
        if self.operator not in SUPPORTED_OPERATORS:
            raise FilterParseError(f"Unsupported operator: {self.operator}")
        if self.operator == "between":
            if not isinstance(self.value, (list, tuple)) or len(self.value) != 2:
                raise FilterParseError("'between' requires [min, max]")


@dataclass
class FilterStage:
    """A stage containing multiple rules with AND/OR logic."""
    name: str
    logic: str = "AND"
    rules: list[FilterRule] = field(default_factory=list)


@dataclass
class UniverseConfig:
    """Universe filter configuration."""
    market: str = "A股"
    boards: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    exclude_st: bool = True
    exclude_suspended: bool = True
    min_listing_days: int = 0
    min_data_quality_score: float = 0


@dataclass
class RankingConfig:
    """Ranking configuration."""
    score_model: str = "balanced"
    sort_by: str = "total_score"
    ascending: bool = False
    top_n: int = 50


@dataclass
class FilterDSL:
    """Complete filter configuration."""
    universe: UniverseConfig = field(default_factory=UniverseConfig)
    stages: list[FilterStage] = field(default_factory=list)
    ranking: RankingConfig = field(default_factory=RankingConfig)


@dataclass
class StageResult:
    """Result of a single filter stage."""
    name: str
    count_before: int
    count_after: int
    removed: int


@dataclass
class FilterResult:
    """Complete filter result."""
    candidates: pd.DataFrame
    stage_results: list[StageResult]
    total_before: int
    total_after: int
    ranking_applied: bool = False


# ============================================================
# Parser
# ============================================================

def parse_filter_config(config: dict) -> FilterDSL:
    """Parse a dict configuration into FilterDSL."""
    # Universe
    uni = config.get("universe", {})
    universe = UniverseConfig(
        market=uni.get("market", "A股"),
        boards=uni.get("boards", []),
        industries=uni.get("industries", []),
        exclude_st=uni.get("exclude_st", True),
        exclude_suspended=uni.get("exclude_suspended", True),
        min_listing_days=uni.get("min_listing_days", 0),
        min_data_quality_score=uni.get("min_data_quality_score", 0),
    )

    # Stages
    stages = []
    for stage_cfg in config.get("stages", []):
        rules = []
        for rule_cfg in stage_cfg.get("rules", []):
            rule = FilterRule(
                field=rule_cfg["field"],
                operator=rule_cfg["operator"],
                value=rule_cfg["value"],
            )
            rule.validate()
            rules.append(rule)
        stages.append(FilterStage(
            name=stage_cfg.get("name", "Unnamed"),
            logic=stage_cfg.get("logic", "AND"),
            rules=rules,
        ))

    # Ranking
    rank = config.get("ranking", {})
    ranking = RankingConfig(
        score_model=rank.get("score_model", "balanced"),
        sort_by=rank.get("sort_by", "total_score"),
        ascending=rank.get("ascending", False),
        top_n=rank.get("top_n", 50),
    )

    return FilterDSL(universe=universe, stages=stages, ranking=ranking)


# ============================================================
# Executor
# ============================================================

def apply_universe_filter(df: pd.DataFrame, config: UniverseConfig) -> pd.DataFrame:
    """Apply universe-level filters."""
    result = df.copy()

    # Board filter
    if config.boards:
        if "board" in result.columns:
            result = result[result["board"].isin(config.boards)]

    # Industry filter
    if config.industries:
        if "industry" in result.columns:
            result = result[result["industry"].isin(config.industries)]

    # Exclude ST
    if config.exclude_st and "is_st" in result.columns:
        result = result[result["is_st"] == 0]

    # Min listing days
    if config.min_listing_days > 0 and "listing_days" in result.columns:
        result = result[result["listing_days"] >= config.min_listing_days]

    # Min data quality
    if config.min_data_quality_score > 0 and "data_quality_score" in result.columns:
        result = result[result["data_quality_score"] >= config.min_data_quality_score]

    return result


def apply_stage(df: pd.DataFrame, stage: FilterStage) -> tuple[pd.DataFrame, StageResult]:
    """Apply a single filter stage. Returns filtered df and stage result."""
    count_before = len(df)

    if not stage.rules:
        return df, StageResult(stage.name, count_before, count_before, 0)

    masks = []
    for rule in stage.rules:
        if rule.field not in df.columns:
            logger.warning(f"Field '{rule.field}' not found, skipping rule")
            masks.append(pd.Series(True, index=df.index))
            continue

        try:
            mask = apply_operator(df[rule.field], rule.operator, rule.value)
            masks.append(mask)
        except Exception as e:
            logger.warning(f"Rule {rule.field} {rule.operator} {rule.value} failed: {e}")
            masks.append(pd.Series(True, index=df.index))

    if not masks:
        return df, StageResult(stage.name, count_before, count_before, 0)

    # Combine masks
    if stage.logic == "AND":
        combined = masks[0]
        for m in masks[1:]:
            combined = combined & m
    elif stage.logic == "OR":
        combined = masks[0]
        for m in masks[1:]:
            combined = combined | m
    else:
        combined = masks[0]

    result = df[combined.fillna(False)]
    count_after = len(result)

    return result, StageResult(stage.name, count_before, count_after, count_before - count_after)


def apply_industry_percentile_filter(
    df: pd.DataFrame,
    field: str,
    operator: str,
    value: float,
) -> pd.Series:
    """Apply industry-level percentile filter."""
    if "industry" not in df.columns or field not in df.columns:
        return pd.Series(True, index=df.index)

    mask = pd.Series(False, index=df.index)

    for industry, group in df.groupby("industry"):
        if len(group) < 5:
            mask[group.index] = True  # Too few stocks, keep all
            continue

        series = group[field]
        if "gte" in operator:
            threshold = series.quantile(value / 100.0 if value > 1 else value)
            mask[group.index] = series >= threshold
        else:
            threshold = series.quantile(value / 100.0 if value > 1 else value)
            mask[group.index] = series <= threshold

    return mask


def execute_filter(df: pd.DataFrame, config: FilterDSL) -> FilterResult:
    """Execute the complete filter pipeline."""
    total_before = len(df)

    # Apply universe filter
    filtered = apply_universe_filter(df, config.universe)
    stage_results = [
        StageResult("股票池筛选", total_before, len(filtered), total_before - len(filtered))
    ]

    # Apply each stage
    for stage in config.stages:
        filtered, result = apply_stage(filtered, stage)
        stage_results.append(result)
        logger.info(f"Stage '{stage.name}': {result.count_before} → {result.count_after} (-{result.removed})")

    # Apply ranking
    ranking_applied = False
    sort_col = config.ranking.sort_by
    if sort_col in filtered.columns:
        filtered = filtered.sort_values(sort_col, ascending=config.ranking.ascending, na_position="last")
        ranking_applied = True

    if config.ranking.top_n > 0:
        filtered = filtered.head(config.ranking.top_n)

    return FilterResult(
        candidates=filtered.reset_index(drop=True),
        stage_results=stage_results,
        total_before=total_before,
        total_after=len(filtered),
        ranking_applied=ranking_applied,
    )


__all__ = [
    "FilterRule", "FilterStage", "UniverseConfig", "RankingConfig",
    "FilterDSL", "FilterResult", "StageResult",
    "parse_filter_config", "execute_filter", "apply_operator",
    "apply_universe_filter", "apply_stage", "apply_industry_percentile_filter",
    "SUPPORTED_OPERATORS",
]
