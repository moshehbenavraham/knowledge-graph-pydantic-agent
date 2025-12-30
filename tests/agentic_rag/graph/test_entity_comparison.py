"""
Unit tests for cross-entity comparison engine.

Tests cover:
- Pydantic models and dataclasses (T016)
- Type compatibility validation (T017)
- Growth rate calculation helpers (T018)
- ComparisonQueryBuilder Cypher generation (T019)
- ComparisonResultParser and ranking (T019)
- Integration tests with mocked Neo4j (T020)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agentic_rag.graph.entity_comparison import (
    ComparisonQuery,
    ComparisonQueryBuilder,
    ComparisonResultParser,
    EntityComparisonResult,
    EntityMetrics,
    GrowthMetrics,
    GrowthType,
    SortOrder,
    calculate_absolute_delta,
    calculate_percent_change,
    calculate_qoq_growth,
    calculate_yoy_growth,
    compare_entities,
    execute_comparison,
    get_entities_with_types,
    validate_type_compatibility,
)

# =============================================================================
# T016: Unit tests for Pydantic models and dataclasses
# =============================================================================


class TestEntityMetrics:
    """Tests for EntityMetrics dataclass."""

    def test_create_entity_metrics_basic(self) -> None:
        """Test basic EntityMetrics creation."""
        metrics = EntityMetrics(entity_name="Intel")
        assert metrics.entity_name == "Intel"
        assert metrics.entity_type == ""
        assert metrics.value is None
        assert metrics.unit == ""
        assert metrics.metric_type == ""
        assert metrics.fiscal_quarter is None
        assert metrics.fiscal_year is None
        assert metrics.fact_count == 0
        assert metrics.source_documents == []

    def test_create_entity_metrics_with_data(self) -> None:
        """Test EntityMetrics creation with all fields."""
        metrics = EntityMetrics(
            entity_name="Intel",
            entity_type="company",
            value=15.4,
            unit="USD billions",
            metric_type="revenue",
            fiscal_quarter="Q3",
            fiscal_year=2024,
            fact_count=5,
            source_documents=["doc1.pdf", "doc2.pdf"],
        )
        assert metrics.entity_name == "Intel"
        assert metrics.entity_type == "company"
        assert metrics.value == 15.4
        assert metrics.unit == "USD billions"
        assert metrics.metric_type == "revenue"
        assert metrics.fiscal_quarter == "Q3"
        assert metrics.fiscal_year == 2024
        assert metrics.fact_count == 5
        assert len(metrics.source_documents) == 2

    def test_entity_metrics_has_value_true(self) -> None:
        """Test has_value property when value exists."""
        metrics = EntityMetrics(entity_name="Intel", value=15.4)
        assert metrics.has_value is True

    def test_entity_metrics_has_value_false(self) -> None:
        """Test has_value property when value is None."""
        metrics = EntityMetrics(entity_name="Intel")
        assert metrics.has_value is False

    def test_entity_metrics_period_label_full(self) -> None:
        """Test period_label with quarter and year."""
        metrics = EntityMetrics(entity_name="Intel", fiscal_quarter="Q3", fiscal_year=2024)
        assert metrics.period_label == "Q3 2024"

    def test_entity_metrics_period_label_year_only(self) -> None:
        """Test period_label with year only."""
        metrics = EntityMetrics(entity_name="Intel", fiscal_year=2024)
        assert metrics.period_label == "FY 2024"

    def test_entity_metrics_period_label_empty(self) -> None:
        """Test period_label with no time data."""
        metrics = EntityMetrics(entity_name="Intel")
        assert metrics.period_label == ""

    def test_entity_metrics_to_dict(self) -> None:
        """Test EntityMetrics serialization."""
        metrics = EntityMetrics(
            entity_name="Intel",
            entity_type="company",
            value=15.4,
            unit="USD billions",
        )
        data = metrics.to_dict()
        assert data["entity_name"] == "Intel"
        assert data["entity_type"] == "company"
        assert data["value"] == 15.4
        assert data["unit"] == "USD billions"


class TestGrowthMetrics:
    """Tests for GrowthMetrics dataclass."""

    def test_create_growth_metrics_basic(self) -> None:
        """Test basic GrowthMetrics creation."""
        growth = GrowthMetrics(entity_name="Intel")
        assert growth.entity_name == "Intel"
        assert growth.baseline_value is None
        assert growth.current_value is None
        assert growth.absolute_delta is None
        assert growth.percent_change is None
        assert growth.growth_type == GrowthType.ABSOLUTE

    def test_create_growth_metrics_with_data(self) -> None:
        """Test GrowthMetrics creation with calculated values."""
        growth = GrowthMetrics(
            entity_name="Intel",
            baseline_value=100.0,
            current_value=120.0,
            absolute_delta=20.0,
            percent_change=20.0,
            growth_type=GrowthType.YOY,
            baseline_period="Q3 2023",
            current_period="Q3 2024",
        )
        assert growth.baseline_value == 100.0
        assert growth.current_value == 120.0
        assert growth.absolute_delta == 20.0
        assert growth.percent_change == 20.0
        assert growth.growth_type == GrowthType.YOY

    def test_growth_metrics_get_summary_with_data(self) -> None:
        """Test get_summary with complete data."""
        growth = GrowthMetrics(
            entity_name="Intel",
            baseline_value=100.0,
            current_value=120.0,
            absolute_delta=20.0,
            percent_change=20.0,
            baseline_period="Q3 2023",
            current_period="Q3 2024",
        )
        summary = growth.get_summary()
        assert "Intel" in summary
        assert "+20.00" in summary
        assert "+20.0%" in summary

    def test_growth_metrics_get_summary_insufficient_data(self) -> None:
        """Test get_summary with insufficient data."""
        growth = GrowthMetrics(entity_name="Intel")
        summary = growth.get_summary()
        assert "Insufficient data" in summary

    def test_growth_metrics_to_dict(self) -> None:
        """Test GrowthMetrics serialization."""
        growth = GrowthMetrics(
            entity_name="Intel",
            absolute_delta=20.0,
            growth_type=GrowthType.QOQ,
        )
        data = growth.to_dict()
        assert data["entity_name"] == "Intel"
        assert data["absolute_delta"] == 20.0
        assert data["growth_type"] == "qoq"


class TestEntityComparisonResult:
    """Tests for EntityComparisonResult dataclass."""

    def test_create_empty_result(self) -> None:
        """Test empty EntityComparisonResult creation."""
        result = EntityComparisonResult()
        assert result.entities == []
        assert result.metric == ""
        assert result.comparison_valid is True
        assert result.error_message == ""
        assert result.entities_compared == 0
        assert result.entities_with_data == 0
        assert result.ranking == []
        assert result.growth_metrics == []
        assert result.query_time_ms == 0.0

    def test_create_result_with_data(self) -> None:
        """Test EntityComparisonResult with comparison data."""
        entities = [
            EntityMetrics(entity_name="Intel", value=15.4),
            EntityMetrics(entity_name="AMD", value=6.8),
        ]
        result = EntityComparisonResult(
            entities=entities,
            metric="revenue",
            comparison_valid=True,
            entities_compared=2,
            entities_with_data=2,
            ranking=["Intel", "AMD"],
            query_time_ms=250.5,
        )
        assert len(result.entities) == 2
        assert result.metric == "revenue"
        assert result.entities_compared == 2
        assert result.ranking == ["Intel", "AMD"]

    def test_result_get_summary_valid(self) -> None:
        """Test get_summary with valid comparison."""
        entities = [
            EntityMetrics(entity_name="Intel", value=15.4, unit="USD billions"),
            EntityMetrics(entity_name="AMD", value=6.8, unit="USD billions"),
        ]
        result = EntityComparisonResult(
            entities=entities,
            metric="revenue",
            comparison_valid=True,
            entities_compared=2,
        )
        summary = result.get_summary()
        assert "revenue" in summary
        assert "Intel" in summary
        assert "AMD" in summary
        assert "15.40" in summary
        assert "6.80" in summary

    def test_result_get_summary_invalid(self) -> None:
        """Test get_summary with invalid comparison."""
        result = EntityComparisonResult(
            comparison_valid=False,
            error_message="Type mismatch",
        )
        summary = result.get_summary()
        assert "invalid" in summary
        assert "Type mismatch" in summary

    def test_result_get_summary_no_data(self) -> None:
        """Test get_summary with no entities."""
        result = EntityComparisonResult()
        summary = result.get_summary()
        assert "No data available" in summary

    def test_result_to_dict(self) -> None:
        """Test EntityComparisonResult serialization."""
        entities = [EntityMetrics(entity_name="Intel", value=15.4)]
        result = EntityComparisonResult(
            entities=entities,
            metric="revenue",
            ranking=["Intel"],
            query_time_ms=100.0,
        )
        data = result.to_dict()
        assert len(data["entities"]) == 1
        assert data["metric"] == "revenue"
        assert data["ranking"] == ["Intel"]
        assert data["query_time_ms"] == 100.0


class TestComparisonQuery:
    """Tests for ComparisonQuery Pydantic model."""

    def test_create_basic_query(self) -> None:
        """Test basic query creation with minimum required fields."""
        query = ComparisonQuery(
            entity_names=["Intel", "AMD"],
            metric="revenue",
        )
        assert query.entity_names == ["Intel", "AMD"]
        assert query.metric == "revenue"
        assert query.entity_type_filter is None
        assert query.fiscal_quarter is None
        assert query.fiscal_year is None
        assert query.sort_order == SortOrder.DESCENDING
        assert query.include_growth is False
        assert query.growth_type == GrowthType.PERCENTAGE
        assert query.limit == 50

    def test_create_query_with_all_params(self) -> None:
        """Test query creation with all parameters."""
        query = ComparisonQuery(
            entity_names=["Intel", "AMD", "NVIDIA"],
            metric="revenue",
            entity_type_filter="organization",
            fiscal_quarter="Q3",
            fiscal_year=2024,
            sort_order=SortOrder.ASCENDING,
            include_growth=True,
            growth_type=GrowthType.YOY,
            limit=20,
        )
        assert len(query.entity_names) == 3
        assert query.entity_type_filter == "organization"
        assert query.fiscal_quarter == "Q3"
        assert query.fiscal_year == 2024
        assert query.sort_order == SortOrder.ASCENDING
        assert query.include_growth is True
        assert query.growth_type == GrowthType.YOY
        assert query.limit == 20

    def test_query_validates_minimum_entities(self) -> None:
        """Test that at least 2 entities are required."""
        with pytest.raises(ValueError):
            ComparisonQuery(entity_names=["Intel"], metric="revenue")

    def test_query_validates_maximum_entities(self) -> None:
        """Test that at most 5 entities are allowed."""
        with pytest.raises(ValueError):
            ComparisonQuery(
                entity_names=["A", "B", "C", "D", "E", "F"],
                metric="revenue",
            )

    def test_query_deduplicates_entities(self) -> None:
        """Test that duplicate entities are removed."""
        query = ComparisonQuery(
            entity_names=["Intel", "intel", "INTEL", "AMD"],
            metric="revenue",
        )
        # Should deduplicate case-insensitively, keeping first occurrence
        assert len(query.entity_names) == 2
        assert query.entity_names[0] == "Intel"
        assert query.entity_names[1] == "AMD"

    def test_query_removes_empty_entities(self) -> None:
        """Test that empty entity names are removed."""
        query = ComparisonQuery(
            entity_names=["Intel", "", "  ", "AMD"],
            metric="revenue",
        )
        assert len(query.entity_names) == 2

    def test_query_normalizes_quarter(self) -> None:
        """Test quarter normalization to uppercase."""
        query = ComparisonQuery(
            entity_names=["Intel", "AMD"],
            metric="revenue",
            fiscal_quarter="q3",
        )
        assert query.fiscal_quarter == "Q3"

    def test_query_validates_quarter_format(self) -> None:
        """Test quarter format validation."""
        with pytest.raises(ValueError):
            ComparisonQuery(
                entity_names=["Intel", "AMD"],
                metric="revenue",
                fiscal_quarter="Quarter3",
            )

    def test_query_validates_year_range(self) -> None:
        """Test year range validation."""
        with pytest.raises(ValueError):
            ComparisonQuery(
                entity_names=["Intel", "AMD"],
                metric="revenue",
                fiscal_year=1999,  # Below 2000
            )

    def test_query_validates_limit_range(self) -> None:
        """Test limit range validation."""
        with pytest.raises(ValueError):
            ComparisonQuery(
                entity_names=["Intel", "AMD"],
                metric="revenue",
                limit=200,  # Above 100
            )


# =============================================================================
# T017: Unit tests for type compatibility validation
# =============================================================================


class TestTypeCompatibilityValidation:
    """Tests for type compatibility validation functions."""

    def test_validate_empty_types(self) -> None:
        """Test validation with empty list."""
        is_valid, error = validate_type_compatibility([])
        assert is_valid is True
        assert error == ""

    def test_validate_single_entity(self) -> None:
        """Test validation with single entity."""
        is_valid, error = validate_type_compatibility([("Intel", "company")])
        assert is_valid is True
        assert error == ""

    def test_validate_same_types(self) -> None:
        """Test validation with same types."""
        entity_types = [
            ("Intel", "company"),
            ("AMD", "company"),
            ("NVIDIA", "company"),
        ]
        is_valid, error = validate_type_compatibility(entity_types)
        assert is_valid is True
        assert error == ""

    def test_validate_compatible_subtypes(self) -> None:
        """Test validation with compatible subtypes (same parent)."""
        entity_types = [
            ("Intel", "company"),
            ("AMD", "corporation"),
        ]
        is_valid, _error = validate_type_compatibility(entity_types)
        # Both should be subtypes of "organization"
        assert is_valid is True

    def test_validate_incompatible_types(self) -> None:
        """Test validation with incompatible types."""
        entity_types = [
            ("Intel", "company"),
            ("Tim Cook", "person"),
        ]
        is_valid, error = validate_type_compatibility(entity_types)
        assert is_valid is False
        assert error is not None
        assert "Cannot compare" in error
        assert "Intel" in error
        assert "Tim Cook" in error

    def test_get_entities_with_types(self) -> None:
        """Test extracting entity types from metrics."""
        metrics = [
            EntityMetrics(entity_name="Intel", entity_type="company"),
            EntityMetrics(entity_name="AMD", entity_type="company"),
            EntityMetrics(entity_name="Unknown", entity_type=""),  # No type
        ]
        result = get_entities_with_types(metrics)
        # Should only include entities with types
        assert len(result) == 2
        assert ("Intel", "company") in result
        assert ("AMD", "company") in result


# =============================================================================
# T018: Unit tests for growth rate calculation helpers
# =============================================================================


class TestGrowthRateHelpers:
    """Tests for growth rate calculation functions."""

    def test_calculate_absolute_delta_positive(self) -> None:
        """Test absolute delta with positive growth."""
        result = calculate_absolute_delta(120.0, 100.0)
        assert result == 20.0

    def test_calculate_absolute_delta_negative(self) -> None:
        """Test absolute delta with negative growth."""
        result = calculate_absolute_delta(80.0, 100.0)
        assert result == -20.0

    def test_calculate_absolute_delta_none_current(self) -> None:
        """Test absolute delta with None current."""
        result = calculate_absolute_delta(None, 100.0)
        assert result is None

    def test_calculate_absolute_delta_none_baseline(self) -> None:
        """Test absolute delta with None baseline."""
        result = calculate_absolute_delta(120.0, None)
        assert result is None

    def test_calculate_percent_change_positive(self) -> None:
        """Test percent change with positive growth."""
        result = calculate_percent_change(120.0, 100.0)
        assert result == 20.0

    def test_calculate_percent_change_negative(self) -> None:
        """Test percent change with negative growth."""
        result = calculate_percent_change(80.0, 100.0)
        assert result == -20.0

    def test_calculate_percent_change_zero_baseline_positive(self) -> None:
        """Test percent change with zero baseline (positive current)."""
        result = calculate_percent_change(50.0, 0.0)
        assert result == 100.0

    def test_calculate_percent_change_zero_baseline_negative(self) -> None:
        """Test percent change with zero baseline (negative current)."""
        result = calculate_percent_change(-50.0, 0.0)
        assert result == -100.0

    def test_calculate_percent_change_zero_both(self) -> None:
        """Test percent change with both zero."""
        result = calculate_percent_change(0.0, 0.0)
        assert result == 0.0

    def test_calculate_percent_change_none_values(self) -> None:
        """Test percent change with None values."""
        assert calculate_percent_change(None, 100.0) is None
        assert calculate_percent_change(100.0, None) is None

    def test_calculate_qoq_growth_q3_to_q2(self) -> None:
        """Test QoQ growth from Q2 to Q3."""
        data = {("Q2", 2024): 100.0, ("Q3", 2024): 120.0}
        result = calculate_qoq_growth("Q3", 2024, 120.0, data, "Intel")
        assert result.entity_name == "Intel"
        assert result.baseline_value == 100.0
        assert result.current_value == 120.0
        assert result.absolute_delta == 20.0
        assert result.percent_change == 20.0
        assert result.growth_type == GrowthType.QOQ
        assert result.baseline_period == "Q2 2024"
        assert result.current_period == "Q3 2024"

    def test_calculate_qoq_growth_q1_to_q4(self) -> None:
        """Test QoQ growth from Q4 previous year to Q1."""
        data = {("Q4", 2023): 100.0, ("Q1", 2024): 110.0}
        result = calculate_qoq_growth("Q1", 2024, 110.0, data, "Intel")
        assert result.baseline_value == 100.0
        assert result.baseline_period == "Q4 2023"
        assert result.current_period == "Q1 2024"

    def test_calculate_qoq_growth_missing_baseline(self) -> None:
        """Test QoQ growth with missing baseline data."""
        data: dict[tuple[str, int], float] = {}
        result = calculate_qoq_growth("Q3", 2024, 120.0, data, "Intel")
        assert result.baseline_value is None
        assert result.absolute_delta is None
        assert result.baseline_period == ""

    def test_calculate_yoy_growth_same_quarter(self) -> None:
        """Test YoY growth for same quarter."""
        data = {("Q3", 2023): 100.0, ("Q3", 2024): 130.0}
        result = calculate_yoy_growth("Q3", 2024, 130.0, data, "Intel")
        assert result.entity_name == "Intel"
        assert result.baseline_value == 100.0
        assert result.current_value == 130.0
        assert result.absolute_delta == 30.0
        assert result.percent_change == 30.0
        assert result.growth_type == GrowthType.YOY
        assert result.baseline_period == "Q3 2023"
        assert result.current_period == "Q3 2024"

    def test_calculate_yoy_growth_missing_baseline(self) -> None:
        """Test YoY growth with missing baseline data."""
        data: dict[tuple[str, int], float] = {}
        result = calculate_yoy_growth("Q3", 2024, 130.0, data, "Intel")
        assert result.baseline_value is None
        assert result.baseline_period == ""


# =============================================================================
# T019: Unit tests for ComparisonQueryBuilder and ComparisonResultParser
# =============================================================================


class TestComparisonQueryBuilder:
    """Tests for ComparisonQueryBuilder."""

    def test_builder_requires_entities(self) -> None:
        """Test that build() requires entity names."""
        builder = ComparisonQueryBuilder().with_metric("revenue")
        with pytest.raises(ValueError, match="At least 2 entity names are required"):
            builder.build()

    def test_builder_requires_metric(self) -> None:
        """Test that build() requires metric."""
        builder = ComparisonQueryBuilder().for_entities(["Intel", "AMD"])
        with pytest.raises(ValueError, match="Metric is required"):
            builder.build()

    def test_builder_basic_query(self) -> None:
        """Test basic query generation."""
        builder = ComparisonQueryBuilder().for_entities(["Intel", "AMD"]).with_metric("revenue")
        cypher, params = builder.build()

        assert "$entity_patterns" in cypher
        assert "$metric_pattern" in cypher
        assert params["entity_patterns"] == ["intel", "amd"]
        assert params["metric_pattern"] == "revenue"

    def test_builder_with_time_filters(self) -> None:
        """Test query with fiscal quarter and year filters."""
        builder = (
            ComparisonQueryBuilder()
            .for_entities(["Intel", "AMD"])
            .with_metric("revenue")
            .in_quarter("Q3")
            .in_year(2024)
        )
        cypher, params = builder.build()

        assert "$fiscal_quarter" in cypher
        assert "$fiscal_year" in cypher
        assert params["fiscal_quarter"] == "Q3"
        assert params["fiscal_year"] == 2024

    def test_builder_with_entity_type_filter(self) -> None:
        """Test query with entity type filter (expands hierarchy)."""
        builder = (
            ComparisonQueryBuilder()
            .for_entities(["Intel", "AMD"])
            .with_metric("revenue")
            .with_entity_type_filter("organization")
        )
        cypher, params = builder.build()

        assert "$entity_types" in cypher
        # Should include "organization" and subtypes like "company"
        assert "organization" in params["entity_types"]

    def test_builder_from_query_model(self) -> None:
        """Test builder configuration from ComparisonQuery model."""
        query = ComparisonQuery(
            entity_names=["Intel", "AMD", "NVIDIA"],
            metric="profit",
            fiscal_quarter="Q3",
            fiscal_year=2024,
            limit=20,
        )
        builder = ComparisonQueryBuilder().from_query(query)
        _cypher, params = builder.build()

        assert params["entity_patterns"] == ["intel", "amd", "nvidia"]
        assert params["metric_pattern"] == "profit"
        assert params["fiscal_quarter"] == "Q3"
        assert params["fiscal_year"] == 2024
        assert params["limit_per_entity"] == 20

    def test_builder_method_chaining(self) -> None:
        """Test fluent method chaining."""
        builder = (
            ComparisonQueryBuilder()
            .for_entities(["Intel", "AMD"])
            .with_metric("revenue")
            .with_entity_type_filter("company")
            .in_quarter("Q3")
            .in_year(2024)
            .with_limit(30)
        )
        _, params = builder.build()

        assert params["entity_patterns"] == ["intel", "amd"]
        assert params["metric_pattern"] == "revenue"
        assert params["fiscal_quarter"] == "Q3"
        assert params["fiscal_year"] == 2024
        assert params["limit_per_entity"] == 30


class TestComparisonResultParser:
    """Tests for ComparisonResultParser."""

    def test_parse_record_basic(self) -> None:
        """Test parsing a basic record."""
        record = {
            "entity_name": "Intel",
            "entity_type": "company",
            "value": 15.4,
            "unit": "USD billions",
            "metric_type": "revenue",
            "fiscal_quarter": "Q3",
            "fiscal_year": 2024,
            "fact_count": 3,
            "source_documents": ["doc1.pdf", "doc2.pdf"],
        }
        result = ComparisonResultParser.parse_record(record)

        assert result.entity_name == "Intel"
        assert result.entity_type == "company"
        assert result.value == 15.4
        assert result.unit == "USD billions"
        assert result.metric_type == "revenue"
        assert result.fiscal_quarter == "Q3"
        assert result.fiscal_year == 2024
        assert result.fact_count == 3
        assert len(result.source_documents) == 2

    def test_parse_record_with_null_values(self) -> None:
        """Test parsing record with null values."""
        record = {
            "entity_name": "Intel",
            "entity_type": None,
            "value": None,
            "unit": None,
            "metric_type": None,
            "fiscal_quarter": None,
            "fiscal_year": None,
            "fact_count": 0,
            "source_documents": None,
        }
        result = ComparisonResultParser.parse_record(record)

        assert result.entity_name == "Intel"
        assert result.entity_type == ""
        assert result.value is None
        assert result.unit == ""
        assert result.source_documents == []

    def test_parse_records_multiple(self) -> None:
        """Test parsing multiple records."""
        records = [
            {"entity_name": "Intel", "value": 15.4},
            {"entity_name": "AMD", "value": 6.8},
        ]
        results = ComparisonResultParser.parse_records(records)

        assert len(results) == 2
        assert results[0].entity_name == "Intel"
        assert results[1].entity_name == "AMD"

    def test_aggregate_by_entity_all_found(self) -> None:
        """Test aggregation when all entities have data."""
        metrics = [
            EntityMetrics(entity_name="Intel", value=15.4),
            EntityMetrics(entity_name="AMD", value=6.8),
        ]
        entity_names = ["Intel", "AMD"]
        result = ComparisonResultParser.aggregate_by_entity(metrics, entity_names)

        assert len(result) == 2
        assert result[0].entity_name == "Intel"
        assert result[1].entity_name == "AMD"

    def test_aggregate_by_entity_missing_entity(self) -> None:
        """Test aggregation with missing entity creates placeholder."""
        metrics = [
            EntityMetrics(entity_name="Intel", value=15.4),
        ]
        entity_names = ["Intel", "AMD"]
        result = ComparisonResultParser.aggregate_by_entity(metrics, entity_names)

        assert len(result) == 2
        assert result[0].entity_name == "Intel"
        assert result[0].value == 15.4
        assert result[1].entity_name == "AMD"
        assert result[1].value is None  # Placeholder

    def test_aggregate_by_entity_case_insensitive(self) -> None:
        """Test aggregation is case-insensitive."""
        metrics = [
            EntityMetrics(entity_name="INTEL", value=15.4),
        ]
        entity_names = ["Intel"]
        result = ComparisonResultParser.aggregate_by_entity(metrics, entity_names)

        assert len(result) == 1
        assert result[0].value == 15.4

    def test_aggregate_by_entity_preserves_order(self) -> None:
        """Test aggregation preserves requested entity order."""
        metrics = [
            EntityMetrics(entity_name="AMD", value=6.8),
            EntityMetrics(entity_name="Intel", value=15.4),
        ]
        entity_names = ["Intel", "AMD", "NVIDIA"]
        result = ComparisonResultParser.aggregate_by_entity(metrics, entity_names)

        assert result[0].entity_name == "Intel"
        assert result[1].entity_name == "AMD"
        assert result[2].entity_name == "NVIDIA"

    def test_rank_entities_descending(self) -> None:
        """Test ranking entities descending (highest first)."""
        metrics = [
            EntityMetrics(entity_name="Intel", value=15.4),
            EntityMetrics(entity_name="AMD", value=6.8),
            EntityMetrics(entity_name="NVIDIA", value=20.0),
        ]
        ranking = ComparisonResultParser.rank_entities(metrics, SortOrder.DESCENDING)

        assert ranking == ["NVIDIA", "Intel", "AMD"]

    def test_rank_entities_ascending(self) -> None:
        """Test ranking entities ascending (lowest first)."""
        metrics = [
            EntityMetrics(entity_name="Intel", value=15.4),
            EntityMetrics(entity_name="AMD", value=6.8),
            EntityMetrics(entity_name="NVIDIA", value=20.0),
        ]
        ranking = ComparisonResultParser.rank_entities(metrics, SortOrder.ASCENDING)

        assert ranking == ["AMD", "Intel", "NVIDIA"]

    def test_rank_entities_with_none_values(self) -> None:
        """Test ranking puts None values at end."""
        metrics = [
            EntityMetrics(entity_name="Intel", value=15.4),
            EntityMetrics(entity_name="Unknown", value=None),
            EntityMetrics(entity_name="AMD", value=6.8),
        ]
        ranking = ComparisonResultParser.rank_entities(metrics)

        assert ranking[-1] == "Unknown"
        assert ranking[0] == "Intel"
        assert ranking[1] == "AMD"


# =============================================================================
# T020: Integration tests with mocked Neo4j
# =============================================================================


class TestExecuteComparison:
    """Integration tests for execute_comparison with mocked Neo4j."""

    @pytest.fixture
    def mock_connection_manager(self) -> MagicMock:
        """Create mock connection manager."""
        manager = MagicMock()
        session = AsyncMock()
        manager.get_neo4j_session.return_value.__aenter__ = AsyncMock(return_value=session)
        manager.get_neo4j_session.return_value.__aexit__ = AsyncMock(return_value=None)
        return manager

    @pytest.mark.asyncio
    async def test_execute_requires_connection_manager(self) -> None:
        """Test that execute requires connection manager."""
        query = ComparisonQuery(entity_names=["Intel", "AMD"], metric="revenue")
        with pytest.raises(ValueError, match="connection_manager is required"):
            await execute_comparison(None, query)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_execute_returns_result_on_no_data(
        self, mock_connection_manager: MagicMock
    ) -> None:
        """Test that empty results are handled gracefully."""

        class MockAsyncIterator:
            def __init__(self, items: list[Any]) -> None:
                self.items = items
                self.index = 0

            def __aiter__(self) -> MockAsyncIterator:
                return self

            async def __anext__(self) -> Any:
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_result = MockAsyncIterator([])

        session = AsyncMock()
        session.run.return_value = mock_result

        mock_connection_manager.get_neo4j_session.return_value.__aenter__ = AsyncMock(
            return_value=session
        )

        query = ComparisonQuery(entity_names=["Intel", "AMD"], metric="revenue")
        result = await execute_comparison(mock_connection_manager, query)

        assert result.comparison_valid is True
        assert result.entities_compared == 2
        assert result.entities_with_data == 0

    @pytest.mark.asyncio
    async def test_execute_parses_results(self, mock_connection_manager: MagicMock) -> None:
        """Test that results are properly parsed."""
        mock_records = [
            {
                "entity_name": "Intel",
                "entity_type": "company",
                "value": 15.4,
                "unit": "USD billions",
                "metric_type": "revenue",
                "fiscal_quarter": "Q3",
                "fiscal_year": 2024,
                "fact_count": 3,
                "source_documents": ["doc1.pdf"],
            },
            {
                "entity_name": "AMD",
                "entity_type": "company",
                "value": 6.8,
                "unit": "USD billions",
                "metric_type": "revenue",
                "fiscal_quarter": "Q3",
                "fiscal_year": 2024,
                "fact_count": 2,
                "source_documents": ["doc2.pdf"],
            },
        ]

        class MockAsyncIterator:
            def __init__(self, items: list[Any]) -> None:
                self.items = items
                self.index = 0

            def __aiter__(self) -> MockAsyncIterator:
                return self

            async def __anext__(self) -> Any:
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_result = MockAsyncIterator(mock_records)

        session = AsyncMock()
        session.run.return_value = mock_result

        mock_connection_manager.get_neo4j_session.return_value.__aenter__ = AsyncMock(
            return_value=session
        )

        query = ComparisonQuery(entity_names=["Intel", "AMD"], metric="revenue")
        result = await execute_comparison(mock_connection_manager, query)

        assert result.comparison_valid is True
        assert result.entities_compared == 2
        assert result.entities_with_data == 2
        assert result.ranking == ["Intel", "AMD"]
        assert result.entities[0].entity_name == "Intel"
        assert result.entities[0].value == 15.4
        assert result.entities[1].entity_name == "AMD"
        assert result.entities[1].value == 6.8

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self, mock_connection_manager: MagicMock) -> None:
        """Test that exceptions are handled gracefully."""
        mock_connection_manager.get_neo4j_session.return_value.__aenter__.side_effect = Exception(
            "Connection failed"
        )

        query = ComparisonQuery(entity_names=["Intel", "AMD"], metric="revenue")
        result = await execute_comparison(mock_connection_manager, query)

        assert result.comparison_valid is False
        assert "Query execution failed" in result.error_message


class TestCompareEntitiesConvenience:
    """Tests for the compare_entities convenience function."""

    @pytest.mark.asyncio
    async def test_compare_entities_calls_execute(self) -> None:
        """Test that compare_entities creates query and calls execute."""
        with patch(
            "src.agentic_rag.graph.entity_comparison.execute_comparison",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = EntityComparisonResult(
                comparison_valid=True,
                entities_compared=2,
            )

            mock_manager = MagicMock()
            _result = await compare_entities(
                mock_manager,
                entity_names=["Intel", "AMD"],
                metric="revenue",
                fiscal_quarter="Q3",
                fiscal_year=2024,
            )

            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            query = call_args[0][1]
            assert query.entity_names == ["Intel", "AMD"]
            assert query.metric == "revenue"
            assert query.fiscal_quarter == "Q3"
            assert query.fiscal_year == 2024


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_entity_metrics_with_zero_value(self) -> None:
        """Test EntityMetrics with zero value."""
        metrics = EntityMetrics(entity_name="Intel", value=0.0)
        assert metrics.has_value is True
        assert metrics.value == 0.0

    def test_growth_metrics_with_negative_values(self) -> None:
        """Test GrowthMetrics with negative growth."""
        growth = GrowthMetrics(
            entity_name="Intel",
            baseline_value=100.0,
            current_value=50.0,
            absolute_delta=-50.0,
            percent_change=-50.0,
        )
        summary = growth.get_summary()
        assert "-50.00" in summary
        assert "-50.0%" in summary

    def test_query_with_special_characters(self) -> None:
        """Test query with special characters in entity names."""
        query = ComparisonQuery(
            entity_names=["Intel (Corporation)", "AMD Inc."],
            metric="revenue",
        )
        assert "Intel (Corporation)" in query.entity_names
        assert "AMD Inc." in query.entity_names

    def test_ranking_with_all_none_values(self) -> None:
        """Test ranking when all values are None."""
        metrics = [
            EntityMetrics(entity_name="A", value=None),
            EntityMetrics(entity_name="B", value=None),
        ]
        ranking = ComparisonResultParser.rank_entities(metrics)
        # Both should be at end (order preserved since both None)
        assert set(ranking) == {"A", "B"}

    def test_ranking_with_equal_values(self) -> None:
        """Test ranking with equal values."""
        metrics = [
            EntityMetrics(entity_name="A", value=100.0),
            EntityMetrics(entity_name="B", value=100.0),
        ]
        ranking = ComparisonResultParser.rank_entities(metrics)
        # Both should be included
        assert len(ranking) == 2

    def test_aggregate_with_duplicate_entity_names(self) -> None:
        """Test aggregation takes first occurrence."""
        metrics = [
            EntityMetrics(entity_name="Intel", value=15.4),
            EntityMetrics(entity_name="Intel", value=16.0),  # Duplicate
        ]
        entity_names = ["Intel"]
        result = ComparisonResultParser.aggregate_by_entity(metrics, entity_names)

        assert len(result) == 1
        assert result[0].value == 15.4  # First occurrence

    def test_percent_change_with_negative_baseline(self) -> None:
        """Test percent change calculation with negative baseline."""
        result = calculate_percent_change(50.0, -100.0)
        # (50 - (-100)) / |-100| * 100 = 150%
        assert result == 150.0


# =============================================================================
# Performance / Boundary Tests
# =============================================================================


class TestPerformanceBoundaries:
    """Tests for performance-related boundaries."""

    def test_query_limit_respects_maximum(self) -> None:
        """Test that query limit is capped at 100."""
        query = ComparisonQuery(
            entity_names=["Intel", "AMD"],
            metric="revenue",
            limit=100,
        )
        assert query.limit == 100

    def test_entity_count_minimum(self) -> None:
        """Test minimum entity count (2)."""
        query = ComparisonQuery(
            entity_names=["Intel", "AMD"],
            metric="revenue",
        )
        assert len(query.entity_names) == 2

    def test_entity_count_maximum(self) -> None:
        """Test maximum entity count (5)."""
        query = ComparisonQuery(
            entity_names=["A", "B", "C", "D", "E"],
            metric="revenue",
        )
        assert len(query.entity_names) == 5

    def test_builder_limit_capping(self) -> None:
        """Test builder caps limit at 100."""
        builder = (
            ComparisonQueryBuilder()
            .for_entities(["Intel", "AMD"])
            .with_metric("revenue")
            .with_limit(500)
        )
        _, params = builder.build()
        assert params["limit_per_entity"] == 100

    def test_parse_many_records(self) -> None:
        """Test parsing many records."""
        records = []
        for i in range(60):
            records.append(
                {
                    "entity_name": f"Entity{i}",
                    "value": float(i),
                }
            )

        results = ComparisonResultParser.parse_records(records)
        assert len(results) == 60
