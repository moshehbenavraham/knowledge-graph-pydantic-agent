"""
Temporal trend query engine for knowledge graph time-series analysis.

This module provides temporal aggregation and comparison queries using
fiscal_quarter and fiscal_year metadata on episodes. Enables time-series
questions like "How has Intel's revenue changed over time?" and
"Compare Apple Q3 2023 vs Q3 2024".

Key components:
- DataPoint, TrendResult, ComparisonResult: Dataclasses for temporal data
- TemporalQuery: Pydantic model for query parameters
- TemporalQueryBuilder: Builder pattern for Cypher query construction
- TrendResultParser: Parser for Neo4j temporal records

Performance targets:
- Single quarter queries: < 500ms
- Range queries (1 year): < 1 second
- Comparison queries: < 1 second
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field, field_validator

from src.agentic_rag.cache import CacheType, generate_cache_key, get_query_cache
from src.agentic_rag.resilience import ServiceType, get_circuit_breaker
from src.config import get_settings

if TYPE_CHECKING:
    from src.agentic_rag.storage.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums
# =============================================================================


class ComparisonType(str, Enum):
    """Type of temporal comparison."""

    QOQ = "qoq"  # Quarter-over-quarter
    YOY = "yoy"  # Year-over-year
    NONE = "none"  # No comparison, just trend data


class TrendDirection(str, Enum):
    """Direction of trend."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"
    INSUFFICIENT_DATA = "insufficient_data"


# =============================================================================
# Helper Functions (T011)
# =============================================================================


def quarter_to_int(quarter: str) -> int:
    """
    Convert quarter string to integer for sorting.

    Args:
        quarter: Quarter string like "Q1", "Q2", "Q3", "Q4"

    Returns:
        Integer 1-4 representing the quarter

    Raises:
        ValueError: If quarter string is invalid

    Example:
        >>> quarter_to_int("Q1")
        1
        >>> quarter_to_int("Q4")
        4
    """
    quarter_upper = quarter.upper().strip()
    mapping = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    if quarter_upper not in mapping:
        raise ValueError(f"Invalid quarter: {quarter}. Expected Q1, Q2, Q3, or Q4")
    return mapping[quarter_upper]


def int_to_quarter(quarter_num: int) -> str:
    """
    Convert integer to quarter string.

    Args:
        quarter_num: Integer 1-4

    Returns:
        Quarter string like "Q1", "Q2", "Q3", "Q4"

    Raises:
        ValueError: If quarter_num is not 1-4

    Example:
        >>> int_to_quarter(1)
        'Q1'
        >>> int_to_quarter(4)
        'Q4'
    """
    if quarter_num not in (1, 2, 3, 4):
        raise ValueError(f"Invalid quarter number: {quarter_num}. Expected 1, 2, 3, or 4")
    return f"Q{quarter_num}"


def quarter_sort_key(year: int, quarter: str) -> int:
    """
    Generate a sort key for chronological ordering of fiscal quarters.

    Args:
        year: Fiscal year (e.g., 2024)
        quarter: Quarter string like "Q1", "Q2", "Q3", "Q4"

    Returns:
        Integer sort key where higher values are more recent

    Example:
        >>> quarter_sort_key(2024, "Q1")
        20241
        >>> quarter_sort_key(2023, "Q4") < quarter_sort_key(2024, "Q1")
        True
    """
    return year * 10 + quarter_to_int(quarter)


def get_previous_quarter(year: int, quarter: str) -> tuple[int, str]:
    """
    Get the previous quarter given a year and quarter.

    Args:
        year: Current fiscal year
        quarter: Current quarter string

    Returns:
        Tuple of (previous_year, previous_quarter)

    Example:
        >>> get_previous_quarter(2024, "Q1")
        (2023, 'Q4')
        >>> get_previous_quarter(2024, "Q3")
        (2024, 'Q2')
    """
    q_num = quarter_to_int(quarter)
    if q_num == 1:
        return year - 1, "Q4"
    return year, int_to_quarter(q_num - 1)


def get_same_quarter_previous_year(year: int, quarter: str) -> tuple[int, str]:
    """
    Get the same quarter from the previous year.

    Args:
        year: Current fiscal year
        quarter: Current quarter string

    Returns:
        Tuple of (previous_year, same_quarter)

    Example:
        >>> get_same_quarter_previous_year(2024, "Q3")
        (2023, 'Q3')
    """
    return year - 1, quarter


# =============================================================================
# Dataclasses (T004-T006)
# =============================================================================


@dataclass
class DataPoint:
    """
    Single time-series data point with temporal and value information.

    Attributes:
        quarter: Fiscal quarter string (Q1, Q2, Q3, Q4)
        year: Fiscal year (e.g., 2024)
        value: Numeric value for this period
        unit: Unit of measurement (e.g., "USD millions", "percent")
        entity: Entity name this data point belongs to
        metric: Metric name (e.g., "revenue", "profit_margin")
        fact_count: Number of facts aggregated into this data point
        source_episodes: Episode IDs contributing to this value
    """

    quarter: str
    year: int
    value: float
    unit: str = ""
    entity: str = ""
    metric: str = ""
    fact_count: int = 1
    source_episodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "quarter": self.quarter,
            "year": self.year,
            "value": self.value,
            "unit": self.unit,
            "entity": self.entity,
            "metric": self.metric,
            "fact_count": self.fact_count,
            "source_episodes": self.source_episodes,
        }

    @property
    def sort_key(self) -> int:
        """Get sort key for chronological ordering."""
        return quarter_sort_key(self.year, self.quarter)

    @property
    def period_label(self) -> str:
        """Get human-readable period label."""
        return f"{self.quarter} {self.year}"


@dataclass
class TrendResult:
    """
    Collection of time-series data points with trend metadata.

    Attributes:
        data_points: List of DataPoint objects in chronological order
        entity: Entity name for this trend
        metric: Metric being tracked
        direction: Overall trend direction
        percent_change: Total percent change from first to last data point
        time_span: Human-readable time span description
        start_period: First period in the trend
        end_period: Last period in the trend
        missing_periods: List of periods with no data
    """

    data_points: list[DataPoint] = field(default_factory=list)
    entity: str = ""
    metric: str = ""
    direction: TrendDirection = TrendDirection.INSUFFICIENT_DATA
    percent_change: float | None = None
    time_span: str = ""
    start_period: str = ""
    end_period: str = ""
    missing_periods: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "data_points": [dp.to_dict() for dp in self.data_points],
            "entity": self.entity,
            "metric": self.metric,
            "direction": self.direction.value,
            "percent_change": self.percent_change,
            "time_span": self.time_span,
            "start_period": self.start_period,
            "end_period": self.end_period,
            "missing_periods": self.missing_periods,
        }

    def get_summary(self) -> str:
        """
        Get a human-readable summary of the trend.

        Returns:
            String summary like "Intel revenue: UP 15.2% (Q1 2023 - Q4 2024)"
        """
        if not self.data_points:
            return f"{self.entity} {self.metric}: No data available"

        pct_str = f"{self.percent_change:+.1f}%" if self.percent_change is not None else "N/A"
        return (
            f"{self.entity} {self.metric}: {self.direction.value.upper()} "
            f"{pct_str} ({self.time_span})"
        )


@dataclass
class ComparisonResult:
    """
    Quarter-over-quarter or year-over-year comparison result.

    Attributes:
        baseline: Baseline data point (earlier period)
        current: Current data point (later period)
        delta: Absolute change (current - baseline)
        percent_change: Percentage change from baseline
        comparison_type: Type of comparison (QOQ or YOY)
        baseline_missing: True if baseline period has no data
        current_missing: True if current period has no data
        entity: Entity name for this comparison
        metric: Metric being compared
    """

    baseline: DataPoint | None = None
    current: DataPoint | None = None
    delta: float | None = None
    percent_change: float | None = None
    comparison_type: ComparisonType = ComparisonType.NONE
    baseline_missing: bool = False
    current_missing: bool = False
    entity: str = ""
    metric: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "current": self.current.to_dict() if self.current else None,
            "delta": self.delta,
            "percent_change": self.percent_change,
            "comparison_type": self.comparison_type.value,
            "baseline_missing": self.baseline_missing,
            "current_missing": self.current_missing,
            "entity": self.entity,
            "metric": self.metric,
        }

    def get_summary(self) -> str:
        """
        Get a human-readable summary of the comparison.

        Returns:
            String summary like "Intel revenue Q3 2024 vs Q3 2023: +$5.2B (+15.2%)"
        """
        if self.baseline_missing and self.current_missing:
            return f"{self.entity} {self.metric}: No data for comparison"

        if self.baseline_missing:
            current_label = self.current.period_label if self.current else "current"
            return f"{self.entity} {self.metric} {current_label}: No baseline data"

        if self.current_missing:
            baseline_label = self.baseline.period_label if self.baseline else "baseline"
            return f"{self.entity} {self.metric}: No current data (baseline: {baseline_label})"

        if self.baseline is None or self.current is None:
            return f"{self.entity} {self.metric}: Incomplete data"

        delta_str = f"{self.delta:+.2f}" if self.delta is not None else "N/A"
        pct_str = f"{self.percent_change:+.1f}%" if self.percent_change is not None else "N/A"
        unit = self.current.unit or ""

        return (
            f"{self.entity} {self.metric} {self.current.period_label} vs "
            f"{self.baseline.period_label}: {delta_str} {unit} ({pct_str})"
        )


# =============================================================================
# Pydantic Model (T007)
# =============================================================================


class TemporalQuery(BaseModel):
    """
    Query parameters for temporal trend analysis.

    Attributes:
        entity: Entity name to query (e.g., "Intel", "Apple")
        metric: Optional metric filter (e.g., "revenue", "profit")
        start_year: Start of time range (inclusive)
        end_year: End of time range (inclusive)
        start_quarter: Optional start quarter filter (Q1-Q4)
        end_quarter: Optional end quarter filter (Q1-Q4)
        comparison_type: Type of comparison to perform
        limit: Maximum data points to return
    """

    entity: str = Field(
        ...,
        min_length=1,
        description="Entity name to query for temporal data",
    )
    metric: str | None = Field(
        default=None,
        description="Optional metric filter (e.g., 'revenue', 'profit')",
    )
    start_year: int = Field(
        default=2020,
        ge=2000,
        le=2100,
        description="Start of time range (inclusive)",
    )
    end_year: int = Field(
        default=2025,
        ge=2000,
        le=2100,
        description="End of time range (inclusive)",
    )
    start_quarter: str | None = Field(
        default=None,
        pattern=r"^[Qq][1-4]$",
        description="Optional start quarter (Q1-Q4)",
    )
    end_quarter: str | None = Field(
        default=None,
        pattern=r"^[Qq][1-4]$",
        description="Optional end quarter (Q1-Q4)",
    )
    comparison_type: ComparisonType = Field(
        default=ComparisonType.NONE,
        description="Type of comparison to perform",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum data points to return",
    )

    @field_validator("end_year")
    @classmethod
    def validate_end_year(cls, v: int, info: Any) -> int:
        """Ensure end_year >= start_year."""
        start_year = info.data.get("start_year", 2020)
        if v < start_year:
            raise ValueError(f"end_year ({v}) must be >= start_year ({start_year})")
        return v

    @field_validator("start_quarter", "end_quarter")
    @classmethod
    def normalize_quarter(cls, v: str | None) -> str | None:
        """Normalize quarter to uppercase."""
        if v is None:
            return None
        return v.upper()


# =============================================================================
# Query Builder (T008-T009)
# =============================================================================


class TemporalQueryBuilder:
    """
    Builder pattern for constructing temporal aggregation Cypher queries.

    Builds parameterized Cypher queries with:
    - Entity filtering
    - Time range constraints (year, quarter)
    - Metric filtering
    - Chronological ordering
    """

    def __init__(self) -> None:
        """Initialize the query builder."""
        self._entity: str | None = None
        self._metric: str | None = None
        self._start_year: int = 2020
        self._end_year: int = 2025
        self._start_quarter: str | None = None
        self._end_quarter: str | None = None
        self._limit: int = 50

    def for_entity(self, entity: str) -> TemporalQueryBuilder:
        """Set the entity to query."""
        self._entity = entity
        return self

    def with_metric(self, metric: str | None) -> TemporalQueryBuilder:
        """Set optional metric filter."""
        self._metric = metric
        return self

    def in_year_range(self, start_year: int, end_year: int) -> TemporalQueryBuilder:
        """Set the year range."""
        self._start_year = start_year
        self._end_year = end_year
        return self

    def in_quarter_range(
        self, start_quarter: str | None, end_quarter: str | None
    ) -> TemporalQueryBuilder:
        """Set optional quarter range."""
        self._start_quarter = start_quarter.upper() if start_quarter else None
        self._end_quarter = end_quarter.upper() if end_quarter else None
        return self

    def with_limit(self, limit: int) -> TemporalQueryBuilder:
        """Set result limit."""
        self._limit = max(1, min(200, limit))
        return self

    def from_query(self, query: TemporalQuery) -> TemporalQueryBuilder:
        """Configure builder from TemporalQuery model."""
        self._entity = query.entity
        self._metric = query.metric
        self._start_year = query.start_year
        self._end_year = query.end_year
        self._start_quarter = query.start_quarter
        self._end_quarter = query.end_quarter
        self._limit = query.limit
        return self

    def build(self) -> tuple[str, dict[str, Any]]:
        """
        Build the Cypher query and parameters.

        Returns:
            Tuple of (cypher_query_string, parameters_dict)

        Raises:
            ValueError: If entity is not set
        """
        if not self._entity:
            raise ValueError("entity is required")

        params: dict[str, Any] = {
            "entity_pattern": self._entity.lower(),
            "start_year": self._start_year,
            "end_year": self._end_year,
            "limit": self._limit,
        }

        # Build WHERE clauses
        where_clauses = self._build_where_clauses(params)
        where_str = " AND ".join(where_clauses)

        # Build query with aggregation by quarter/year
        query = f"""
        MATCH (e:Entity)-[:HAS_EPISODE]->(ep:Episode)
        WHERE toLower(e.name) CONTAINS $entity_pattern
          AND {where_str}
        WITH ep, e,
             ep.fiscal_quarter as quarter,
             ep.fiscal_year as year
        WHERE quarter IS NOT NULL AND year IS NOT NULL
        UNWIND ep.numeric_facts as fact
        WITH e.name as entity_name,
             quarter,
             year,
             fact,
             ep.id as episode_id
        {self._build_metric_filter(params)}
        WITH entity_name,
             quarter,
             year,
             avg(toFloat(fact.value)) as avg_value,
             collect(DISTINCT fact.unit)[0] as unit,
             collect(DISTINCT fact.type)[0] as metric_type,
             count(fact) as fact_count,
             collect(DISTINCT episode_id) as episode_ids
        RETURN entity_name,
               quarter,
               year,
               avg_value as value,
               unit,
               metric_type as metric,
               fact_count,
               episode_ids
        ORDER BY year ASC,
                 CASE quarter
                   WHEN 'Q1' THEN 1
                   WHEN 'Q2' THEN 2
                   WHEN 'Q3' THEN 3
                   WHEN 'Q4' THEN 4
                   ELSE 5
                 END ASC
        LIMIT $limit
        """

        logger.debug(
            "TemporalQueryBuilder.build",
            entity=self._entity,
            metric=self._metric,
            year_range=f"{self._start_year}-{self._end_year}",
            quarter_range=f"{self._start_quarter}-{self._end_quarter}",
        )

        return query.strip(), params

    def _build_where_clauses(self, params: dict[str, Any]) -> list[str]:
        """Build WHERE clauses for time range filtering."""
        clauses = [
            "ep.fiscal_year >= $start_year",
            "ep.fiscal_year <= $end_year",
        ]

        # Quarter range filtering
        if self._start_quarter and self._end_quarter:
            params["start_q_num"] = quarter_to_int(self._start_quarter)
            params["end_q_num"] = quarter_to_int(self._end_quarter)

            # Handle same-year quarter ranges
            clauses.append(
                """
            (
                (ep.fiscal_year > $start_year AND ep.fiscal_year < $end_year)
                OR (ep.fiscal_year = $start_year AND CASE ep.fiscal_quarter
                    WHEN 'Q1' THEN 1 WHEN 'Q2' THEN 2
                    WHEN 'Q3' THEN 3 WHEN 'Q4' THEN 4 ELSE 0 END >= $start_q_num)
                OR (ep.fiscal_year = $end_year AND CASE ep.fiscal_quarter
                    WHEN 'Q1' THEN 1 WHEN 'Q2' THEN 2
                    WHEN 'Q3' THEN 3 WHEN 'Q4' THEN 4 ELSE 0 END <= $end_q_num)
            )
            """.strip()
            )
        elif self._start_quarter:
            params["start_q_num"] = quarter_to_int(self._start_quarter)
            clauses.append(
                """
            (ep.fiscal_year > $start_year OR
             (ep.fiscal_year = $start_year AND CASE ep.fiscal_quarter
                WHEN 'Q1' THEN 1 WHEN 'Q2' THEN 2
                WHEN 'Q3' THEN 3 WHEN 'Q4' THEN 4 ELSE 0 END >= $start_q_num))
            """.strip()
            )
        elif self._end_quarter:
            params["end_q_num"] = quarter_to_int(self._end_quarter)
            clauses.append(
                """
            (ep.fiscal_year < $end_year OR
             (ep.fiscal_year = $end_year AND CASE ep.fiscal_quarter
                WHEN 'Q1' THEN 1 WHEN 'Q2' THEN 2
                WHEN 'Q3' THEN 3 WHEN 'Q4' THEN 4 ELSE 0 END <= $end_q_num))
            """.strip()
            )

        return clauses

    def _build_metric_filter(self, params: dict[str, Any]) -> str:
        """Build metric filter clause."""
        if self._metric:
            params["metric_pattern"] = self._metric.lower()
            return "WHERE toLower(fact.type) CONTAINS $metric_pattern"
        return ""


# =============================================================================
# Result Parser (T010)
# =============================================================================


class TrendResultParser:
    """
    Parses Neo4j temporal records into DataPoint and TrendResult objects.

    Handles conversion from raw Cypher results to typed dataclasses
    with chronological ordering and trend calculation.
    """

    @staticmethod
    def parse_record(record: dict[str, Any]) -> DataPoint:
        """
        Parse a single Neo4j record into a DataPoint.

        Args:
            record: Dictionary from Neo4j query result

        Returns:
            DataPoint with parsed temporal data
        """
        return DataPoint(
            quarter=record.get("quarter", ""),
            year=int(record.get("year", 0)),
            value=float(record.get("value", 0.0)),
            unit=record.get("unit", "") or "",
            entity=record.get("entity_name", ""),
            metric=record.get("metric", "") or "",
            fact_count=int(record.get("fact_count", 1)),
            source_episodes=record.get("episode_ids", []) or [],
        )

    @staticmethod
    def parse_records(records: list[dict[str, Any]]) -> list[DataPoint]:
        """
        Parse multiple Neo4j records into DataPoints.

        Args:
            records: List of dictionaries from Neo4j query results

        Returns:
            List of DataPoints sorted chronologically (oldest first)
        """
        data_points = [TrendResultParser.parse_record(r) for r in records]
        # Sort chronologically (oldest first)
        data_points.sort(key=lambda dp: dp.sort_key)
        return data_points

    @staticmethod
    def build_trend_result(
        data_points: list[DataPoint],
        entity: str,
        metric: str = "",
    ) -> TrendResult:
        """
        Build a TrendResult from a list of DataPoints.

        Args:
            data_points: Chronologically sorted DataPoints
            entity: Entity name
            metric: Metric name

        Returns:
            TrendResult with calculated direction and percent_change
        """
        if not data_points:
            return TrendResult(
                entity=entity,
                metric=metric,
                direction=TrendDirection.INSUFFICIENT_DATA,
            )

        # Ensure chronological order
        sorted_points = sorted(data_points, key=lambda dp: dp.sort_key)

        first = sorted_points[0]
        last = sorted_points[-1]

        # Calculate percent change
        percent_change: float | None = None
        direction = TrendDirection.INSUFFICIENT_DATA

        if len(sorted_points) >= 2:
            if first.value != 0:
                percent_change = ((last.value - first.value) / abs(first.value)) * 100
                if percent_change > 1.0:
                    direction = TrendDirection.UP
                elif percent_change < -1.0:
                    direction = TrendDirection.DOWN
                else:
                    direction = TrendDirection.FLAT
            elif last.value != 0:
                # First value is 0, any change is significant
                direction = TrendDirection.UP if last.value > 0 else TrendDirection.DOWN
            else:
                direction = TrendDirection.FLAT

        # Build time span description
        time_span = f"{first.period_label} - {last.period_label}"

        return TrendResult(
            data_points=sorted_points,
            entity=entity,
            metric=metric,
            direction=direction,
            percent_change=percent_change,
            time_span=time_span,
            start_period=first.period_label,
            end_period=last.period_label,
        )


# =============================================================================
# Comparison Functions (T012-T013)
# =============================================================================


def calculate_qoq_comparison(
    data_points: list[DataPoint],
    target_year: int,
    target_quarter: str,
    entity: str = "",
    metric: str = "",
) -> ComparisonResult:
    """
    Calculate quarter-over-quarter comparison.

    Compares the target quarter with the previous quarter.

    Args:
        data_points: List of DataPoints to search
        target_year: Year of the target quarter
        target_quarter: Target quarter (Q1-Q4)
        entity: Entity name for result
        metric: Metric name for result

    Returns:
        ComparisonResult with delta and percent_change

    Example:
        >>> result = calculate_qoq_comparison(data_points, 2024, "Q3")
        >>> print(result.get_summary())
        "Intel revenue Q3 2024 vs Q2 2024: +1.5B USD (+5.2%)"
    """
    target_quarter = target_quarter.upper()
    prev_year, prev_quarter = get_previous_quarter(target_year, target_quarter)

    # Find data points
    current_dp: DataPoint | None = None
    baseline_dp: DataPoint | None = None

    for dp in data_points:
        if dp.year == target_year and dp.quarter.upper() == target_quarter:
            current_dp = dp
        if dp.year == prev_year and dp.quarter.upper() == prev_quarter:
            baseline_dp = dp

    return _build_comparison_result(
        baseline_dp,
        current_dp,
        ComparisonType.QOQ,
        entity,
        metric,
    )


def calculate_yoy_comparison(
    data_points: list[DataPoint],
    target_year: int,
    target_quarter: str,
    entity: str = "",
    metric: str = "",
) -> ComparisonResult:
    """
    Calculate year-over-year comparison.

    Compares the target quarter with the same quarter from the previous year.

    Args:
        data_points: List of DataPoints to search
        target_year: Year of the target quarter
        target_quarter: Target quarter (Q1-Q4)
        entity: Entity name for result
        metric: Metric name for result

    Returns:
        ComparisonResult with delta and percent_change

    Example:
        >>> result = calculate_yoy_comparison(data_points, 2024, "Q3")
        >>> print(result.get_summary())
        "Intel revenue Q3 2024 vs Q3 2023: +2.1B USD (+8.5%)"
    """
    target_quarter = target_quarter.upper()
    prev_year, same_quarter = get_same_quarter_previous_year(target_year, target_quarter)

    # Find data points
    current_dp: DataPoint | None = None
    baseline_dp: DataPoint | None = None

    for dp in data_points:
        if dp.year == target_year and dp.quarter.upper() == target_quarter:
            current_dp = dp
        if dp.year == prev_year and dp.quarter.upper() == same_quarter:
            baseline_dp = dp

    return _build_comparison_result(
        baseline_dp,
        current_dp,
        ComparisonType.YOY,
        entity,
        metric,
    )


def _build_comparison_result(
    baseline: DataPoint | None,
    current: DataPoint | None,
    comparison_type: ComparisonType,
    entity: str,
    metric: str,
) -> ComparisonResult:
    """
    Build a ComparisonResult from baseline and current data points.

    Handles null values and calculates delta/percent_change.
    """
    baseline_missing = baseline is None
    current_missing = current is None

    delta: float | None = None
    percent_change: float | None = None

    if baseline is not None and current is not None:
        delta = current.value - baseline.value
        if baseline.value != 0:
            percent_change = (delta / abs(baseline.value)) * 100
        elif delta != 0:
            # Baseline is 0, any change is infinite percent
            # Use a large number to indicate significant change
            percent_change = 100.0 if delta > 0 else -100.0

    return ComparisonResult(
        baseline=baseline,
        current=current,
        delta=delta,
        percent_change=percent_change,
        comparison_type=comparison_type,
        baseline_missing=baseline_missing,
        current_missing=current_missing,
        entity=entity or (current.entity if current else (baseline.entity if baseline else "")),
        metric=metric or (current.metric if current else (baseline.metric if baseline else "")),
    )


# =============================================================================
# Execute Function (T014)
# =============================================================================


async def execute_temporal_query(
    connection_manager: ConnectionManager,
    query: TemporalQuery,
    use_cache: bool = True,
    timeout_seconds: float | None = None,
) -> TrendResult:
    """
    Execute a temporal query against Neo4j and return trend results.

    This is the main entry point for temporal queries. It builds the
    Cypher query, executes it against Neo4j, and parses the results.
    Results are cached for improved performance on repeated queries.

    Args:
        connection_manager: Initialized database connection manager
        query: TemporalQuery parameters
        use_cache: Whether to use query result caching (default True)
        timeout_seconds: Query timeout (default from settings)

    Returns:
        TrendResult with data points and trend analysis

    Raises:
        ValueError: If connection_manager is None

    Example:
        >>> query = TemporalQuery(
        ...     entity="Intel",
        ...     metric="revenue",
        ...     start_year=2023,
        ...     end_year=2024,
        ... )
        >>> result = await execute_temporal_query(connection_manager, query)
        >>> print(result.get_summary())
    """
    if connection_manager is None:
        raise ValueError("connection_manager is required")

    # Get timeout from settings if not specified
    if timeout_seconds is None:
        settings = get_settings()
        timeout_seconds = settings.query_timeout_seconds

    start_time = datetime.now()

    logger.info(
        "execute_temporal_query called",
        entity=query.entity,
        metric=query.metric,
        year_range=f"{query.start_year}-{query.end_year}",
        comparison_type=query.comparison_type.value,
        use_cache=use_cache,
    )

    # Check cache first
    cache = get_query_cache()
    cache_key = generate_cache_key(
        query=query.entity,
        params={
            "metric": query.metric,
            "start_year": query.start_year,
            "end_year": query.end_year,
            "start_quarter": query.start_quarter,
            "end_quarter": query.end_quarter,
            "comparison_type": query.comparison_type.value,
            "limit": query.limit,
        },
        prefix="temporal_trend",
    )

    if use_cache:
        hit, cached_result = cache.get(CacheType.TEMPORAL_TREND, cache_key)
        if hit:
            logger.info(
                "execute_temporal_query cache hit",
                entity=query.entity,
                cache_key=cache_key[:16],
            )
            return cached_result  # type: ignore[no-any-return]

    # Build query
    builder = TemporalQueryBuilder().from_query(query)
    cypher, params = builder.build()

    logger.debug("execute_temporal_query cypher", cypher_preview=cypher[:200])

    # Get circuit breaker for Neo4j
    neo4j_breaker = get_circuit_breaker(ServiceType.NEO4J)

    # Check if circuit is open
    if not await neo4j_breaker.can_execute():
        logger.warning(
            "execute_temporal_query circuit open",
            entity=query.entity,
            circuit_state=neo4j_breaker.state.value,
        )
        return TrendResult(
            entity=query.entity,
            metric=query.metric or "",
            direction=TrendDirection.INSUFFICIENT_DATA,
        )

    # Execute query with timeout
    try:
        async with asyncio.timeout(timeout_seconds):
            async with connection_manager.get_neo4j_session() as session:
                result = await session.run(cypher, params)

                records = []
                async for record in result:
                    records.append(dict(record))

        # Record success in circuit breaker
        await neo4j_breaker.record_success()

    except TimeoutError:
        await neo4j_breaker.record_failure()
        logger.warning(
            "execute_temporal_query timeout",
            entity=query.entity,
            timeout_seconds=timeout_seconds,
        )
        return TrendResult(
            entity=query.entity,
            metric=query.metric or "",
            direction=TrendDirection.INSUFFICIENT_DATA,
        )

    except Exception as e:
        await neo4j_breaker.record_failure(e)
        logger.exception(
            "execute_temporal_query failed",
            error=str(e),
            entity=query.entity,
        )
        return TrendResult(
            entity=query.entity,
            metric=query.metric or "",
            direction=TrendDirection.INSUFFICIENT_DATA,
        )

    # Parse results
    data_points = TrendResultParser.parse_records(records)
    trend_result = TrendResultParser.build_trend_result(
        data_points,
        entity=query.entity,
        metric=query.metric or "",
    )

    # Cache results
    if use_cache:
        cache.set(CacheType.TEMPORAL_TREND, cache_key, trend_result)

    query_time = (datetime.now() - start_time).total_seconds()

    logger.info(
        "execute_temporal_query completed",
        data_points_found=len(data_points),
        direction=trend_result.direction.value,
        query_time_ms=query_time * 1000,
        entity=query.entity,
        cached=use_cache,
    )

    return trend_result


# =============================================================================
# Convenience Functions (T015)
# =============================================================================


async def get_entity_trend(
    connection_manager: ConnectionManager,
    entity: str,
    metric: str | None = None,
    start_year: int = 2020,
    end_year: int = 2025,
    limit: int = 50,
) -> TrendResult:
    """
    Get the trend data for an entity over a time range.

    Convenience wrapper for common use case of retrieving all
    temporal data for an entity.

    Args:
        connection_manager: Database connection manager
        entity: Entity name to query
        metric: Optional metric filter
        start_year: Start of time range
        end_year: End of time range
        limit: Maximum data points

    Returns:
        TrendResult with chronological data points
    """
    query = TemporalQuery(
        entity=entity,
        metric=metric,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
    )
    return await execute_temporal_query(connection_manager, query)


async def compare_quarters(
    connection_manager: ConnectionManager,
    entity: str,
    target_year: int,
    target_quarter: str,
    comparison_type: ComparisonType = ComparisonType.QOQ,
    metric: str | None = None,
) -> ComparisonResult:
    """
    Compare a specific quarter with its baseline (previous quarter or same quarter last year).

    Args:
        connection_manager: Database connection manager
        entity: Entity name
        target_year: Year of the target quarter
        target_quarter: Target quarter (Q1-Q4)
        comparison_type: QOQ or YOY comparison
        metric: Optional metric filter

    Returns:
        ComparisonResult with delta and percent_change
    """
    # Determine year range needed for comparison
    if comparison_type == ComparisonType.YOY:
        start_year = target_year - 1
    else:
        start_year = target_year - 1 if target_quarter.upper() == "Q1" else target_year

    query = TemporalQuery(
        entity=entity,
        metric=metric,
        start_year=start_year,
        end_year=target_year,
    )

    result = await execute_temporal_query(connection_manager, query)

    if comparison_type == ComparisonType.QOQ:
        return calculate_qoq_comparison(
            result.data_points,
            target_year,
            target_quarter,
            entity,
            metric or "",
        )
    return calculate_yoy_comparison(
        result.data_points,
        target_year,
        target_quarter,
        entity,
        metric or "",
    )


async def compare_years(
    connection_manager: ConnectionManager,
    entity: str,
    year1: int,
    year2: int,
    metric: str | None = None,
) -> ComparisonResult:
    """
    Compare full-year aggregates between two years.

    Aggregates all quarters for each year and compares the totals.

    Args:
        connection_manager: Database connection manager
        entity: Entity name
        year1: First year (baseline)
        year2: Second year (current)
        metric: Optional metric filter

    Returns:
        ComparisonResult with year-over-year comparison
    """
    query = TemporalQuery(
        entity=entity,
        metric=metric,
        start_year=min(year1, year2),
        end_year=max(year1, year2),
    )

    result = await execute_temporal_query(connection_manager, query)

    # Aggregate by year
    year_totals: dict[int, tuple[float, int, str]] = {}
    for dp in result.data_points:
        if dp.year not in year_totals:
            year_totals[dp.year] = (0.0, 0, dp.unit)
        current_total, current_count, unit = year_totals[dp.year]
        year_totals[dp.year] = (current_total + dp.value, current_count + 1, unit)

    # Create DataPoints for comparison
    baseline_dp: DataPoint | None = None
    current_dp: DataPoint | None = None

    if year1 in year_totals:
        total, count, unit = year_totals[year1]
        baseline_dp = DataPoint(
            quarter="FY",
            year=year1,
            value=total,
            unit=unit,
            entity=entity,
            metric=metric or "",
            fact_count=count,
        )

    if year2 in year_totals:
        total, count, unit = year_totals[year2]
        current_dp = DataPoint(
            quarter="FY",
            year=year2,
            value=total,
            unit=unit,
            entity=entity,
            metric=metric or "",
            fact_count=count,
        )

    return _build_comparison_result(
        baseline_dp,
        current_dp,
        ComparisonType.YOY,
        entity,
        metric or "",
    )
