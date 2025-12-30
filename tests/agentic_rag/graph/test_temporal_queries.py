"""
Unit tests for temporal trend query engine.

Tests cover:
- T016: TemporalQuery Pydantic model validation
- T017: TemporalQueryBuilder Cypher generation
- T018: QoQ/YoY comparison functions with edge cases
"""

import pytest
from pydantic import ValidationError

from src.agentic_rag.graph.temporal_queries import (
    ComparisonResult,
    ComparisonType,
    DataPoint,
    TemporalQuery,
    TemporalQueryBuilder,
    TrendDirection,
    TrendResult,
    TrendResultParser,
    calculate_qoq_comparison,
    calculate_yoy_comparison,
    get_previous_quarter,
    get_same_quarter_previous_year,
    int_to_quarter,
    quarter_sort_key,
    quarter_to_int,
)

# =============================================================================
# Helper Function Tests (T011)
# =============================================================================


class TestQuarterHelpers:
    """Test quarter conversion and sorting helper functions."""

    def test_quarter_to_int_valid(self) -> None:
        """Test valid quarter string to int conversion."""
        assert quarter_to_int("Q1") == 1
        assert quarter_to_int("Q2") == 2
        assert quarter_to_int("Q3") == 3
        assert quarter_to_int("Q4") == 4

    def test_quarter_to_int_case_insensitive(self) -> None:
        """Test case insensitivity."""
        assert quarter_to_int("q1") == 1
        assert quarter_to_int("q4") == 4
        assert quarter_to_int("Q2") == 2

    def test_quarter_to_int_with_whitespace(self) -> None:
        """Test trimming whitespace."""
        assert quarter_to_int(" Q1 ") == 1
        assert quarter_to_int("Q4 ") == 4

    def test_quarter_to_int_invalid(self) -> None:
        """Test invalid quarter strings raise ValueError."""
        with pytest.raises(ValueError, match="Invalid quarter"):
            quarter_to_int("Q5")
        with pytest.raises(ValueError, match="Invalid quarter"):
            quarter_to_int("Q0")
        with pytest.raises(ValueError, match="Invalid quarter"):
            quarter_to_int("invalid")

    def test_int_to_quarter_valid(self) -> None:
        """Test valid int to quarter string conversion."""
        assert int_to_quarter(1) == "Q1"
        assert int_to_quarter(2) == "Q2"
        assert int_to_quarter(3) == "Q3"
        assert int_to_quarter(4) == "Q4"

    def test_int_to_quarter_invalid(self) -> None:
        """Test invalid quarter numbers raise ValueError."""
        with pytest.raises(ValueError, match="Invalid quarter number"):
            int_to_quarter(0)
        with pytest.raises(ValueError, match="Invalid quarter number"):
            int_to_quarter(5)

    def test_quarter_sort_key(self) -> None:
        """Test sort key generation for chronological ordering."""
        # Q4 2023 < Q1 2024
        assert quarter_sort_key(2023, "Q4") < quarter_sort_key(2024, "Q1")
        # Same year ordering
        assert quarter_sort_key(2024, "Q1") < quarter_sort_key(2024, "Q2")
        assert quarter_sort_key(2024, "Q2") < quarter_sort_key(2024, "Q3")
        assert quarter_sort_key(2024, "Q3") < quarter_sort_key(2024, "Q4")

    def test_get_previous_quarter_mid_year(self) -> None:
        """Test getting previous quarter within same year."""
        assert get_previous_quarter(2024, "Q2") == (2024, "Q1")
        assert get_previous_quarter(2024, "Q3") == (2024, "Q2")
        assert get_previous_quarter(2024, "Q4") == (2024, "Q3")

    def test_get_previous_quarter_year_boundary(self) -> None:
        """Test getting previous quarter across year boundary."""
        assert get_previous_quarter(2024, "Q1") == (2023, "Q4")
        assert get_previous_quarter(2025, "Q1") == (2024, "Q4")

    def test_get_same_quarter_previous_year(self) -> None:
        """Test getting same quarter from previous year."""
        assert get_same_quarter_previous_year(2024, "Q3") == (2023, "Q3")
        assert get_same_quarter_previous_year(2024, "Q1") == (2023, "Q1")
        assert get_same_quarter_previous_year(2025, "Q4") == (2024, "Q4")


# =============================================================================
# DataPoint Tests (T004)
# =============================================================================


class TestDataPoint:
    """Test DataPoint dataclass."""

    def test_datapoint_creation(self) -> None:
        """Test basic DataPoint creation."""
        dp = DataPoint(
            quarter="Q1",
            year=2024,
            value=100.5,
            unit="USD millions",
            entity="Intel",
            metric="revenue",
        )
        assert dp.quarter == "Q1"
        assert dp.year == 2024
        assert dp.value == 100.5
        assert dp.unit == "USD millions"
        assert dp.entity == "Intel"
        assert dp.metric == "revenue"

    def test_datapoint_sort_key(self) -> None:
        """Test DataPoint sort_key property."""
        dp = DataPoint(quarter="Q3", year=2024, value=100.0)
        assert dp.sort_key == 20243

    def test_datapoint_period_label(self) -> None:
        """Test DataPoint period_label property."""
        dp = DataPoint(quarter="Q3", year=2024, value=100.0)
        assert dp.period_label == "Q3 2024"

    def test_datapoint_to_dict(self) -> None:
        """Test DataPoint serialization."""
        dp = DataPoint(
            quarter="Q1",
            year=2024,
            value=100.0,
            entity="Intel",
        )
        result = dp.to_dict()
        assert result["quarter"] == "Q1"
        assert result["year"] == 2024
        assert result["value"] == 100.0
        assert result["entity"] == "Intel"

    def test_datapoint_default_values(self) -> None:
        """Test DataPoint default values."""
        dp = DataPoint(quarter="Q1", year=2024, value=50.0)
        assert dp.unit == ""
        assert dp.entity == ""
        assert dp.metric == ""
        assert dp.fact_count == 1
        assert dp.source_episodes == []


# =============================================================================
# TrendResult Tests (T005)
# =============================================================================


class TestTrendResult:
    """Test TrendResult dataclass."""

    def test_trend_result_empty(self) -> None:
        """Test empty TrendResult."""
        result = TrendResult()
        assert result.data_points == []
        assert result.direction == TrendDirection.INSUFFICIENT_DATA
        assert result.percent_change is None

    def test_trend_result_summary_no_data(self) -> None:
        """Test summary with no data points."""
        result = TrendResult(entity="Intel", metric="revenue")
        summary = result.get_summary()
        assert "No data available" in summary

    def test_trend_result_summary_with_data(self) -> None:
        """Test summary with data points."""
        dp1 = DataPoint(quarter="Q1", year=2023, value=100.0, entity="Intel")
        dp2 = DataPoint(quarter="Q2", year=2023, value=110.0, entity="Intel")
        result = TrendResult(
            data_points=[dp1, dp2],
            entity="Intel",
            metric="revenue",
            direction=TrendDirection.UP,
            percent_change=10.0,
            time_span="Q1 2023 - Q2 2023",
        )
        summary = result.get_summary()
        assert "Intel" in summary
        assert "revenue" in summary
        assert "UP" in summary
        assert "+10.0%" in summary

    def test_trend_result_to_dict(self) -> None:
        """Test TrendResult serialization."""
        dp = DataPoint(quarter="Q1", year=2024, value=100.0)
        result = TrendResult(
            data_points=[dp],
            entity="Intel",
            metric="revenue",
            direction=TrendDirection.UP,
        )
        result_dict = result.to_dict()
        assert result_dict["entity"] == "Intel"
        assert result_dict["direction"] == "up"
        assert len(result_dict["data_points"]) == 1


# =============================================================================
# ComparisonResult Tests (T006)
# =============================================================================


class TestComparisonResult:
    """Test ComparisonResult dataclass."""

    def test_comparison_result_complete(self) -> None:
        """Test complete comparison with both values."""
        baseline = DataPoint(quarter="Q2", year=2024, value=100.0, entity="Intel")
        current = DataPoint(quarter="Q3", year=2024, value=115.0, entity="Intel")
        result = ComparisonResult(
            baseline=baseline,
            current=current,
            delta=15.0,
            percent_change=15.0,
            comparison_type=ComparisonType.QOQ,
            entity="Intel",
            metric="revenue",
        )
        assert result.delta == 15.0
        assert result.percent_change == 15.0
        assert not result.baseline_missing
        assert not result.current_missing

    def test_comparison_result_missing_baseline(self) -> None:
        """Test comparison with missing baseline."""
        current = DataPoint(quarter="Q3", year=2024, value=115.0, entity="Intel")
        result = ComparisonResult(
            baseline=None,
            current=current,
            baseline_missing=True,
            entity="Intel",
            metric="revenue",
        )
        summary = result.get_summary()
        assert "No baseline data" in summary

    def test_comparison_result_missing_current(self) -> None:
        """Test comparison with missing current value."""
        baseline = DataPoint(quarter="Q2", year=2024, value=100.0, entity="Intel")
        result = ComparisonResult(
            baseline=baseline,
            current=None,
            current_missing=True,
            entity="Intel",
            metric="revenue",
        )
        summary = result.get_summary()
        assert "No current data" in summary

    def test_comparison_result_both_missing(self) -> None:
        """Test comparison with both values missing."""
        result = ComparisonResult(
            baseline_missing=True,
            current_missing=True,
            entity="Intel",
            metric="revenue",
        )
        summary = result.get_summary()
        assert "No data for comparison" in summary


# =============================================================================
# TemporalQuery Model Tests (T016)
# =============================================================================


class TestTemporalQuery:
    """Test TemporalQuery Pydantic model validation."""

    def test_valid_basic_query(self) -> None:
        """Test basic valid query."""
        query = TemporalQuery(entity="Intel")
        assert query.entity == "Intel"
        assert query.start_year == 2020
        assert query.end_year == 2025
        assert query.comparison_type == ComparisonType.NONE

    def test_valid_full_query(self) -> None:
        """Test fully specified query."""
        query = TemporalQuery(
            entity="Apple",
            metric="revenue",
            start_year=2022,
            end_year=2024,
            start_quarter="Q1",
            end_quarter="Q4",
            comparison_type=ComparisonType.YOY,
            limit=100,
        )
        assert query.entity == "Apple"
        assert query.metric == "revenue"
        assert query.start_year == 2022
        assert query.end_year == 2024
        assert query.start_quarter == "Q1"
        assert query.end_quarter == "Q4"
        assert query.comparison_type == ComparisonType.YOY
        assert query.limit == 100

    def test_invalid_empty_entity(self) -> None:
        """Test empty entity raises ValidationError."""
        with pytest.raises(ValidationError):
            TemporalQuery(entity="")

    def test_invalid_year_range(self) -> None:
        """Test end_year < start_year raises ValidationError."""
        with pytest.raises(ValidationError):
            TemporalQuery(entity="Intel", start_year=2024, end_year=2022)

    def test_invalid_quarter_format(self) -> None:
        """Test invalid quarter format raises ValidationError."""
        with pytest.raises(ValidationError):
            TemporalQuery(entity="Intel", start_quarter="Q5")
        with pytest.raises(ValidationError):
            TemporalQuery(entity="Intel", start_quarter="invalid")

    def test_quarter_normalization(self) -> None:
        """Test quarter strings are normalized to uppercase."""
        query = TemporalQuery(entity="Intel", start_quarter="q1", end_quarter="q4")
        assert query.start_quarter == "Q1"
        assert query.end_quarter == "Q4"

    def test_limit_bounds(self) -> None:
        """Test limit validation bounds."""
        with pytest.raises(ValidationError):
            TemporalQuery(entity="Intel", limit=0)
        with pytest.raises(ValidationError):
            TemporalQuery(entity="Intel", limit=201)

    def test_year_bounds(self) -> None:
        """Test year validation bounds."""
        with pytest.raises(ValidationError):
            TemporalQuery(entity="Intel", start_year=1999)
        with pytest.raises(ValidationError):
            TemporalQuery(entity="Intel", end_year=2101)


# =============================================================================
# TemporalQueryBuilder Tests (T017)
# =============================================================================


class TestTemporalQueryBuilder:
    """Test TemporalQueryBuilder Cypher generation."""

    def test_build_requires_entity(self) -> None:
        """Test that build() raises ValueError without entity."""
        builder = TemporalQueryBuilder()
        with pytest.raises(ValueError, match="entity is required"):
            builder.build()

    def test_basic_query_generation(self) -> None:
        """Test basic query generation."""
        builder = TemporalQueryBuilder()
        builder.for_entity("Intel").in_year_range(2023, 2024)
        cypher, params = builder.build()

        assert "MATCH (e:Entity)" in cypher
        assert "fiscal_quarter" in cypher
        assert "fiscal_year" in cypher
        assert params["entity_pattern"] == "intel"
        assert params["start_year"] == 2023
        assert params["end_year"] == 2024

    def test_query_with_metric_filter(self) -> None:
        """Test query with metric filter."""
        builder = TemporalQueryBuilder()
        builder.for_entity("Intel").with_metric("revenue")
        cypher, params = builder.build()

        assert "metric_pattern" in params
        assert params["metric_pattern"] == "revenue"
        assert "toLower(fact.type) CONTAINS $metric_pattern" in cypher

    def test_query_with_quarter_range(self) -> None:
        """Test query with quarter range."""
        builder = TemporalQueryBuilder()
        builder.for_entity("Intel").in_quarter_range("Q1", "Q4")
        _, params = builder.build()

        assert "start_q_num" in params
        assert "end_q_num" in params
        assert params["start_q_num"] == 1
        assert params["end_q_num"] == 4

    def test_from_query(self) -> None:
        """Test building from TemporalQuery model."""
        query = TemporalQuery(
            entity="Apple",
            metric="profit",
            start_year=2022,
            end_year=2024,
            limit=25,
        )
        builder = TemporalQueryBuilder().from_query(query)
        _, params = builder.build()

        assert params["entity_pattern"] == "apple"
        assert params["start_year"] == 2022
        assert params["end_year"] == 2024
        assert params["limit"] == 25

    def test_query_ordering(self) -> None:
        """Test that results are ordered chronologically."""
        builder = TemporalQueryBuilder().for_entity("Intel")
        cypher, _ = builder.build()

        assert "ORDER BY year ASC" in cypher
        assert "CASE quarter" in cypher

    def test_fluent_interface(self) -> None:
        """Test fluent builder interface returns self."""
        builder = TemporalQueryBuilder()
        result = (
            builder.for_entity("Intel")
            .with_metric("revenue")
            .in_year_range(2020, 2024)
            .in_quarter_range("Q1", "Q4")
            .with_limit(50)
        )
        assert result is builder


# =============================================================================
# TrendResultParser Tests (T010)
# =============================================================================


class TestTrendResultParser:
    """Test TrendResultParser."""

    def test_parse_single_record(self) -> None:
        """Test parsing a single Neo4j record."""
        record = {
            "entity_name": "Intel",
            "quarter": "Q3",
            "year": 2024,
            "value": 15.5,
            "unit": "USD billions",
            "metric": "revenue",
            "fact_count": 3,
            "episode_ids": ["ep1", "ep2"],
        }
        dp = TrendResultParser.parse_record(record)

        assert dp.entity == "Intel"
        assert dp.quarter == "Q3"
        assert dp.year == 2024
        assert dp.value == 15.5
        assert dp.unit == "USD billions"
        assert dp.metric == "revenue"
        assert dp.fact_count == 3

    def test_parse_multiple_records_sorted(self) -> None:
        """Test that multiple records are sorted chronologically."""
        records = [
            {"entity_name": "Intel", "quarter": "Q3", "year": 2024, "value": 15.0},
            {"entity_name": "Intel", "quarter": "Q1", "year": 2024, "value": 13.0},
            {"entity_name": "Intel", "quarter": "Q4", "year": 2023, "value": 12.0},
        ]
        data_points = TrendResultParser.parse_records(records)

        assert len(data_points) == 3
        # Should be sorted: Q4 2023, Q1 2024, Q3 2024
        assert data_points[0].quarter == "Q4"
        assert data_points[0].year == 2023
        assert data_points[1].quarter == "Q1"
        assert data_points[1].year == 2024
        assert data_points[2].quarter == "Q3"
        assert data_points[2].year == 2024

    def test_build_trend_result_up(self) -> None:
        """Test building TrendResult with upward trend."""
        data_points = [
            DataPoint(quarter="Q1", year=2024, value=100.0, entity="Intel"),
            DataPoint(quarter="Q2", year=2024, value=120.0, entity="Intel"),
        ]
        result = TrendResultParser.build_trend_result(data_points, "Intel", "revenue")

        assert result.direction == TrendDirection.UP
        assert result.percent_change == pytest.approx(20.0)
        assert result.time_span == "Q1 2024 - Q2 2024"

    def test_build_trend_result_down(self) -> None:
        """Test building TrendResult with downward trend."""
        data_points = [
            DataPoint(quarter="Q1", year=2024, value=100.0, entity="Intel"),
            DataPoint(quarter="Q2", year=2024, value=80.0, entity="Intel"),
        ]
        result = TrendResultParser.build_trend_result(data_points, "Intel", "revenue")

        assert result.direction == TrendDirection.DOWN
        assert result.percent_change == pytest.approx(-20.0)

    def test_build_trend_result_flat(self) -> None:
        """Test building TrendResult with flat trend (< 1% change)."""
        data_points = [
            DataPoint(quarter="Q1", year=2024, value=100.0, entity="Intel"),
            DataPoint(quarter="Q2", year=2024, value=100.5, entity="Intel"),
        ]
        result = TrendResultParser.build_trend_result(data_points, "Intel", "revenue")

        assert result.direction == TrendDirection.FLAT

    def test_build_trend_result_empty(self) -> None:
        """Test building TrendResult with no data."""
        result = TrendResultParser.build_trend_result([], "Intel", "revenue")
        assert result.direction == TrendDirection.INSUFFICIENT_DATA

    def test_build_trend_result_single_point(self) -> None:
        """Test building TrendResult with single data point."""
        data_points = [
            DataPoint(quarter="Q1", year=2024, value=100.0, entity="Intel"),
        ]
        result = TrendResultParser.build_trend_result(data_points, "Intel", "revenue")

        assert result.direction == TrendDirection.INSUFFICIENT_DATA
        assert result.percent_change is None


# =============================================================================
# Comparison Function Tests (T018)
# =============================================================================


class TestQoQComparison:
    """Test quarter-over-quarter comparison function."""

    def test_qoq_positive_delta(self) -> None:
        """Test QoQ with positive change."""
        data_points = [
            DataPoint(quarter="Q2", year=2024, value=100.0, entity="Intel"),
            DataPoint(quarter="Q3", year=2024, value=115.0, entity="Intel"),
        ]
        result = calculate_qoq_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.comparison_type == ComparisonType.QOQ
        assert result.delta == pytest.approx(15.0)
        assert result.percent_change == pytest.approx(15.0)
        assert not result.baseline_missing
        assert not result.current_missing

    def test_qoq_negative_delta(self) -> None:
        """Test QoQ with negative change."""
        data_points = [
            DataPoint(quarter="Q2", year=2024, value=100.0, entity="Intel"),
            DataPoint(quarter="Q3", year=2024, value=85.0, entity="Intel"),
        ]
        result = calculate_qoq_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.delta == pytest.approx(-15.0)
        assert result.percent_change == pytest.approx(-15.0)

    def test_qoq_year_boundary(self) -> None:
        """Test QoQ across year boundary (Q1 vs Q4 previous year)."""
        data_points = [
            DataPoint(quarter="Q4", year=2023, value=100.0, entity="Intel"),
            DataPoint(quarter="Q1", year=2024, value=110.0, entity="Intel"),
        ]
        result = calculate_qoq_comparison(data_points, 2024, "Q1", "Intel", "revenue")

        assert result.delta == pytest.approx(10.0)
        assert result.baseline is not None
        assert result.baseline.year == 2023
        assert result.baseline.quarter == "Q4"

    def test_qoq_missing_baseline(self) -> None:
        """Test QoQ with missing baseline quarter."""
        data_points = [
            DataPoint(quarter="Q3", year=2024, value=115.0, entity="Intel"),
        ]
        result = calculate_qoq_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.baseline_missing
        assert result.baseline is None
        assert result.delta is None

    def test_qoq_missing_current(self) -> None:
        """Test QoQ with missing current quarter."""
        data_points = [
            DataPoint(quarter="Q2", year=2024, value=100.0, entity="Intel"),
        ]
        result = calculate_qoq_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.current_missing
        assert result.current is None

    def test_qoq_zero_baseline(self) -> None:
        """Test QoQ with zero baseline (avoid division by zero)."""
        data_points = [
            DataPoint(quarter="Q2", year=2024, value=0.0, entity="Intel"),
            DataPoint(quarter="Q3", year=2024, value=100.0, entity="Intel"),
        ]
        result = calculate_qoq_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.delta == pytest.approx(100.0)
        # Zero baseline should give 100% (significant change indicator)
        assert result.percent_change == pytest.approx(100.0)


class TestYoYComparison:
    """Test year-over-year comparison function."""

    def test_yoy_positive_delta(self) -> None:
        """Test YoY with positive change."""
        data_points = [
            DataPoint(quarter="Q3", year=2023, value=100.0, entity="Intel"),
            DataPoint(quarter="Q3", year=2024, value=120.0, entity="Intel"),
        ]
        result = calculate_yoy_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.comparison_type == ComparisonType.YOY
        assert result.delta == pytest.approx(20.0)
        assert result.percent_change == pytest.approx(20.0)

    def test_yoy_negative_delta(self) -> None:
        """Test YoY with negative change."""
        data_points = [
            DataPoint(quarter="Q3", year=2023, value=100.0, entity="Intel"),
            DataPoint(quarter="Q3", year=2024, value=70.0, entity="Intel"),
        ]
        result = calculate_yoy_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.delta == pytest.approx(-30.0)
        assert result.percent_change == pytest.approx(-30.0)

    def test_yoy_missing_previous_year(self) -> None:
        """Test YoY with missing previous year data."""
        data_points = [
            DataPoint(quarter="Q3", year=2024, value=100.0, entity="Intel"),
        ]
        result = calculate_yoy_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.baseline_missing
        assert result.baseline is None

    def test_yoy_zero_baseline(self) -> None:
        """Test YoY with zero baseline value."""
        data_points = [
            DataPoint(quarter="Q3", year=2023, value=0.0, entity="Intel"),
            DataPoint(quarter="Q3", year=2024, value=50.0, entity="Intel"),
        ]
        result = calculate_yoy_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.delta == pytest.approx(50.0)
        # Zero baseline should indicate significant change
        assert result.percent_change == pytest.approx(100.0)

    def test_yoy_both_zero(self) -> None:
        """Test YoY with both values zero."""
        data_points = [
            DataPoint(quarter="Q3", year=2023, value=0.0, entity="Intel"),
            DataPoint(quarter="Q3", year=2024, value=0.0, entity="Intel"),
        ]
        result = calculate_yoy_comparison(data_points, 2024, "Q3", "Intel", "revenue")

        assert result.delta == pytest.approx(0.0)
        # No change from 0 to 0
        assert result.percent_change is None


class TestComparisonEdgeCases:
    """Test edge cases for comparison functions."""

    def test_negative_values(self) -> None:
        """Test comparison with negative values (losses)."""
        data_points = [
            DataPoint(quarter="Q2", year=2024, value=-50.0, entity="Intel"),
            DataPoint(quarter="Q3", year=2024, value=-30.0, entity="Intel"),
        ]
        result = calculate_qoq_comparison(data_points, 2024, "Q3", "Intel", "loss")

        # Loss decreased from -50 to -30, delta is +20 (improvement)
        assert result.delta == pytest.approx(20.0)
        # Relative to |-50|, this is +40% change (20/50 = 0.4)
        assert result.percent_change == pytest.approx(40.0)

    def test_case_insensitive_quarter(self) -> None:
        """Test quarter matching is case insensitive."""
        data_points = [
            DataPoint(quarter="q2", year=2024, value=100.0, entity="Intel"),
            DataPoint(quarter="Q3", year=2024, value=115.0, entity="Intel"),
        ]
        result = calculate_qoq_comparison(data_points, 2024, "q3", "Intel", "revenue")

        assert not result.baseline_missing
        assert not result.current_missing
        assert result.delta == pytest.approx(15.0)

    def test_empty_data_points(self) -> None:
        """Test comparison with empty data points list."""
        result = calculate_qoq_comparison([], 2024, "Q3", "Intel", "revenue")

        assert result.baseline_missing
        assert result.current_missing
        assert result.delta is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestTemporalQueryIntegration:
    """Integration tests combining multiple components."""

    def test_full_query_flow(self) -> None:
        """Test complete query construction and parameter generation."""
        query = TemporalQuery(
            entity="Intel Corporation",
            metric="revenue",
            start_year=2023,
            end_year=2024,
            start_quarter="Q1",
            end_quarter="Q4",
        )

        builder = TemporalQueryBuilder().from_query(query)
        cypher, params = builder.build()

        # Verify query structure
        assert "MATCH (e:Entity)" in cypher
        assert "fiscal_quarter" in cypher
        assert "fiscal_year" in cypher
        assert "ORDER BY" in cypher

        # Verify parameters
        assert params["entity_pattern"] == "intel corporation"
        assert params["start_year"] == 2023
        assert params["end_year"] == 2024
        assert params["metric_pattern"] == "revenue"

    def test_trend_analysis_workflow(self) -> None:
        """Test complete trend analysis workflow."""
        # Simulate Neo4j records
        records = [
            {"entity_name": "Intel", "quarter": "Q1", "year": 2024, "value": 10.0},
            {"entity_name": "Intel", "quarter": "Q2", "year": 2024, "value": 11.5},
            {"entity_name": "Intel", "quarter": "Q3", "year": 2024, "value": 12.0},
            {"entity_name": "Intel", "quarter": "Q4", "year": 2024, "value": 13.0},
        ]

        # Parse records
        data_points = TrendResultParser.parse_records(records)
        assert len(data_points) == 4

        # Build trend result
        result = TrendResultParser.build_trend_result(data_points, "Intel", "revenue")

        assert result.direction == TrendDirection.UP
        assert result.percent_change == pytest.approx(30.0)
        assert result.start_period == "Q1 2024"
        assert result.end_period == "Q4 2024"

    def test_comparison_workflow(self) -> None:
        """Test complete comparison workflow."""
        records = [
            {"entity_name": "Intel", "quarter": "Q3", "year": 2023, "value": 10.0},
            {"entity_name": "Intel", "quarter": "Q3", "year": 2024, "value": 12.5},
        ]

        data_points = TrendResultParser.parse_records(records)

        # YoY comparison
        yoy = calculate_yoy_comparison(data_points, 2024, "Q3", "Intel", "revenue")
        assert yoy.delta == pytest.approx(2.5)
        assert yoy.percent_change == pytest.approx(25.0)

        # Summary should be readable
        summary = yoy.get_summary()
        assert "Q3 2024" in summary
        assert "Q3 2023" in summary
