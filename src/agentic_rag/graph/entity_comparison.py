"""
Cross-entity comparison engine for knowledge graph queries.

This module enables comparison queries that compare numeric facts across
2-5 entities, supporting questions like "Compare Microsoft vs Intel revenue"
and "How do Apple and NVIDIA profit margins differ?"

Key components:
- EntityMetrics, EntityComparisonResult: Dataclasses for comparison data
- ComparisonQuery: Pydantic model for query parameters
- ComparisonQueryBuilder: Builder pattern for Cypher query construction
- ComparisonResultParser: Parser for Neo4j comparison records
- Type compatibility validation using TypeHierarchy
- Growth rate calculation helpers (delta, percentage, QoQ, YoY)

Performance targets:
- 2-entity comparisons: < 500ms
- 5-entity comparisons: < 1.5 seconds
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
from src.agentic_rag.graph.type_hierarchy import get_type_hierarchy
from src.agentic_rag.resilience import ServiceType, get_circuit_breaker
from src.config import get_settings

if TYPE_CHECKING:
    from src.agentic_rag.storage.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


# =============================================================================
# Constants
# =============================================================================


# Default configuration values
DEFAULT_MIN_ENTITIES = 2
DEFAULT_MAX_ENTITIES = 5
DEFAULT_COMPARISON_LIMIT = 50


# =============================================================================
# Enums
# =============================================================================


class SortOrder(str, Enum):
    """Sort order for comparison results."""

    ASCENDING = "asc"
    DESCENDING = "desc"


class GrowthType(str, Enum):
    """Type of growth calculation."""

    ABSOLUTE = "absolute"  # Current - Baseline
    PERCENTAGE = "percentage"  # (Current - Baseline) / |Baseline| * 100
    QOQ = "qoq"  # Quarter-over-quarter
    YOY = "yoy"  # Year-over-year


# =============================================================================
# Dataclasses (T003-T005)
# =============================================================================


@dataclass
class EntityMetrics:
    """
    Metrics data for a single entity in a comparison.

    Attributes:
        entity_name: Name of the entity
        entity_type: Type of entity (e.g., "company", "organization")
        value: Numeric value for the metric (None if missing)
        unit: Unit of measurement (e.g., "USD", "percent")
        metric_type: Type of metric (e.g., "revenue", "profit")
        fiscal_quarter: Fiscal quarter if time-filtered (e.g., "Q3")
        fiscal_year: Fiscal year if time-filtered (e.g., 2024)
        fact_count: Number of facts aggregated
        source_documents: Document references for provenance
    """

    entity_name: str
    entity_type: str = ""
    value: float | None = None
    unit: str = ""
    metric_type: str = ""
    fiscal_quarter: str | None = None
    fiscal_year: int | None = None
    fact_count: int = 0
    source_documents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "value": self.value,
            "unit": self.unit,
            "metric_type": self.metric_type,
            "fiscal_quarter": self.fiscal_quarter,
            "fiscal_year": self.fiscal_year,
            "fact_count": self.fact_count,
            "source_documents": self.source_documents,
        }

    @property
    def has_value(self) -> bool:
        """Check if entity has a valid metric value."""
        return self.value is not None

    @property
    def period_label(self) -> str:
        """Get human-readable period label if time-filtered."""
        if self.fiscal_quarter and self.fiscal_year:
            return f"{self.fiscal_quarter} {self.fiscal_year}"
        if self.fiscal_year:
            return f"FY {self.fiscal_year}"
        return ""


@dataclass
class GrowthMetrics:
    """
    Growth calculation results for an entity.

    Attributes:
        entity_name: Name of the entity
        baseline_value: Value from baseline period
        current_value: Value from current period
        absolute_delta: Current - Baseline
        percent_change: ((Current - Baseline) / |Baseline|) * 100
        growth_type: Type of growth calculation performed
        baseline_period: Description of baseline period
        current_period: Description of current period
    """

    entity_name: str
    baseline_value: float | None = None
    current_value: float | None = None
    absolute_delta: float | None = None
    percent_change: float | None = None
    growth_type: GrowthType = GrowthType.ABSOLUTE
    baseline_period: str = ""
    current_period: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entity_name": self.entity_name,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "absolute_delta": self.absolute_delta,
            "percent_change": self.percent_change,
            "growth_type": self.growth_type.value,
            "baseline_period": self.baseline_period,
            "current_period": self.current_period,
        }

    def get_summary(self) -> str:
        """Get human-readable growth summary."""
        if self.absolute_delta is None:
            return f"{self.entity_name}: Insufficient data for comparison"

        delta_str = f"{self.absolute_delta:+.2f}"
        pct_str = f"{self.percent_change:+.1f}%" if self.percent_change is not None else "N/A"

        return (
            f"{self.entity_name}: {delta_str} ({pct_str}) "
            f"from {self.baseline_period} to {self.current_period}"
        )


@dataclass
class EntityComparisonResult:
    """
    Side-by-side comparison results for multiple entities.

    Attributes:
        entities: List of EntityMetrics for each compared entity
        metric: The metric being compared
        comparison_valid: Whether comparison was valid (same entity types)
        error_message: Error message if comparison invalid
        entities_compared: Number of entities in comparison
        entities_with_data: Number of entities with valid data
        ranking: Entities ranked by metric value (entity names in order)
        growth_metrics: Optional growth calculations if temporal comparison
        query_time_ms: Query execution time in milliseconds
    """

    entities: list[EntityMetrics] = field(default_factory=list)
    metric: str = ""
    comparison_valid: bool = True
    error_message: str = ""
    entities_compared: int = 0
    entities_with_data: int = 0
    ranking: list[str] = field(default_factory=list)
    growth_metrics: list[GrowthMetrics] = field(default_factory=list)
    query_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entities": [e.to_dict() for e in self.entities],
            "metric": self.metric,
            "comparison_valid": self.comparison_valid,
            "error_message": self.error_message,
            "entities_compared": self.entities_compared,
            "entities_with_data": self.entities_with_data,
            "ranking": self.ranking,
            "growth_metrics": [g.to_dict() for g in self.growth_metrics],
            "query_time_ms": self.query_time_ms,
        }

    def get_summary(self) -> str:
        """Get human-readable comparison summary."""
        if not self.comparison_valid:
            return f"Comparison invalid: {self.error_message}"

        if not self.entities:
            return "No data available for comparison"

        lines = [f"Comparing {self.metric} across {self.entities_compared} entities:"]
        for i, entity in enumerate(self.entities):
            rank = i + 1
            value_str = f"{entity.value:.2f}" if entity.value is not None else "N/A"
            unit = entity.unit or ""
            lines.append(f"  {rank}. {entity.entity_name}: {value_str} {unit}".strip())

        return "\n".join(lines)


# =============================================================================
# Pydantic Model (T003)
# =============================================================================


class ComparisonQuery(BaseModel):
    """
    Query parameters for cross-entity comparison.

    Attributes:
        entity_names: List of 2-5 entity names to compare
        metric: Metric to compare (e.g., "revenue", "profit", "margin")
        entity_type_filter: Optional entity type filter for disambiguation
        fiscal_quarter: Optional quarter filter (Q1-Q4)
        fiscal_year: Optional year filter
        sort_order: Sort entities by metric value (ascending/descending)
        include_growth: Whether to include growth rate calculations
        growth_type: Type of growth calculation if include_growth is True
        limit: Maximum records per entity
    """

    entity_names: list[str] = Field(
        ...,
        min_length=DEFAULT_MIN_ENTITIES,
        max_length=DEFAULT_MAX_ENTITIES,
        description="List of 2-5 entity names to compare",
    )
    metric: str = Field(
        ...,
        min_length=1,
        description="Metric to compare (e.g., 'revenue', 'profit')",
    )
    entity_type_filter: str | None = Field(
        default=None,
        description="Optional entity type filter for disambiguation",
    )
    fiscal_quarter: str | None = Field(
        default=None,
        pattern=r"^[Qq][1-4]$",
        description="Optional fiscal quarter filter (Q1-Q4)",
    )
    fiscal_year: int | None = Field(
        default=None,
        ge=2000,
        le=2100,
        description="Optional fiscal year filter",
    )
    sort_order: SortOrder = Field(
        default=SortOrder.DESCENDING,
        description="Sort order for ranking (descending = highest first)",
    )
    include_growth: bool = Field(
        default=False,
        description="Include growth rate calculations",
    )
    growth_type: GrowthType = Field(
        default=GrowthType.PERCENTAGE,
        description="Type of growth calculation",
    )
    limit: int = Field(
        default=DEFAULT_COMPARISON_LIMIT,
        ge=1,
        le=100,
        description="Maximum records per entity",
    )

    @field_validator("entity_names")
    @classmethod
    def validate_entity_names(cls, v: list[str]) -> list[str]:
        """Validate and deduplicate entity names."""
        # Remove empty strings and normalize
        cleaned = [name.strip() for name in v if name and name.strip()]
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique = []
        for name in cleaned:
            name_lower = name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                unique.append(name)

        if len(unique) < DEFAULT_MIN_ENTITIES:
            raise ValueError(
                f"At least {DEFAULT_MIN_ENTITIES} unique entity names required, "
                f"got {len(unique)}"
            )

        if len(unique) > DEFAULT_MAX_ENTITIES:
            raise ValueError(
                f"At most {DEFAULT_MAX_ENTITIES} entity names allowed, " f"got {len(unique)}"
            )

        return unique

    @field_validator("fiscal_quarter")
    @classmethod
    def normalize_quarter(cls, v: str | None) -> str | None:
        """Normalize quarter to uppercase."""
        if v is None:
            return None
        return v.upper()


# =============================================================================
# Type Compatibility Validation (T006)
# =============================================================================


class TypeCompatibilityError(Exception):
    """Raised when entities are not type-compatible for comparison."""

    pass


def validate_type_compatibility(
    entity_types: list[tuple[str, str]],
) -> tuple[bool, str]:
    """
    Validate that all entities are type-compatible for comparison.

    Entities are compatible if they share the same parent type in the
    type hierarchy. For example, "company" and "corporation" are both
    subtypes of "organization" and can be compared.

    Args:
        entity_types: List of (entity_name, entity_type) tuples

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_type_compatibility([("Intel", "company"), ("AMD", "company")])
        (True, "")
        >>> validate_type_compatibility([("Intel", "company"), ("Tim Cook", "person")])
        (False, "Cannot compare 'organization' (Intel) with 'person' (Tim Cook)")
    """
    if not entity_types:
        return True, ""

    if len(entity_types) < 2:
        return True, ""

    hierarchy = get_type_hierarchy()

    # Get parent types for all entities
    parent_types: list[tuple[str, str, str | None]] = []
    for entity_name, entity_type in entity_types:
        parent = hierarchy.get_parent_type(entity_type)
        parent_types.append((entity_name, entity_type, parent))

    # Check if all have the same parent type
    first_parent = parent_types[0][2]

    for entity_name, entity_type, parent in parent_types[1:]:
        if parent != first_parent:
            first_entity = parent_types[0][0]
            first_type = first_parent or parent_types[0][1]
            second_type = parent or entity_type

            return (
                False,
                f"Cannot compare '{first_type}' ({first_entity}) "
                f"with '{second_type}' ({entity_name})",
            )

    return True, ""


def get_entities_with_types(
    entity_metrics: list[EntityMetrics],
) -> list[tuple[str, str]]:
    """
    Extract entity name and type pairs from metrics.

    Args:
        entity_metrics: List of EntityMetrics objects

    Returns:
        List of (entity_name, entity_type) tuples
    """
    return [(em.entity_name, em.entity_type) for em in entity_metrics if em.entity_type]


# =============================================================================
# Growth Rate Helpers (T007-T008)
# =============================================================================


def calculate_absolute_delta(
    current: float | None,
    baseline: float | None,
) -> float | None:
    """
    Calculate absolute delta (current - baseline).

    Args:
        current: Current period value
        baseline: Baseline period value

    Returns:
        Absolute difference, or None if either value is None

    Example:
        >>> calculate_absolute_delta(100.0, 80.0)
        20.0
        >>> calculate_absolute_delta(50.0, 80.0)
        -30.0
    """
    if current is None or baseline is None:
        return None
    return current - baseline


def calculate_percent_change(
    current: float | None,
    baseline: float | None,
) -> float | None:
    """
    Calculate percentage change from baseline to current.

    Formula: ((current - baseline) / |baseline|) * 100

    Handles zero baseline specially:
    - If baseline is 0 and current is 0: returns 0.0
    - If baseline is 0 and current != 0: returns +/- 100.0

    Args:
        current: Current period value
        baseline: Baseline period value

    Returns:
        Percentage change, or None if either value is None

    Example:
        >>> calculate_percent_change(110.0, 100.0)
        10.0
        >>> calculate_percent_change(80.0, 100.0)
        -20.0
        >>> calculate_percent_change(50.0, 0.0)
        100.0
    """
    if current is None or baseline is None:
        return None

    if baseline == 0:
        if current == 0:
            return 0.0
        # Use 100% to indicate significant change from zero baseline
        return 100.0 if current > 0 else -100.0

    return ((current - baseline) / abs(baseline)) * 100


def calculate_qoq_growth(
    current_quarter: str,
    current_year: int,
    current_value: float | None,
    data_points: dict[tuple[str, int], float],
    entity_name: str,
) -> GrowthMetrics:
    """
    Calculate quarter-over-quarter growth.

    Args:
        current_quarter: Current quarter (Q1-Q4)
        current_year: Current year
        current_value: Current period value
        data_points: Dictionary mapping (quarter, year) to values
        entity_name: Name of entity for result

    Returns:
        GrowthMetrics with QoQ calculation

    Example:
        >>> data = {("Q2", 2024): 80.0, ("Q3", 2024): 100.0}
        >>> calculate_qoq_growth("Q3", 2024, 100.0, data, "Intel")
        GrowthMetrics(entity_name='Intel', ..., percent_change=25.0, ...)
    """
    # Get previous quarter
    quarter_num = int(current_quarter[1])
    if quarter_num == 1:
        prev_quarter = "Q4"
        prev_year = current_year - 1
    else:
        prev_quarter = f"Q{quarter_num - 1}"
        prev_year = current_year

    baseline_value = data_points.get((prev_quarter, prev_year))

    return GrowthMetrics(
        entity_name=entity_name,
        baseline_value=baseline_value,
        current_value=current_value,
        absolute_delta=calculate_absolute_delta(current_value, baseline_value),
        percent_change=calculate_percent_change(current_value, baseline_value),
        growth_type=GrowthType.QOQ,
        baseline_period=f"{prev_quarter} {prev_year}" if baseline_value is not None else "",
        current_period=f"{current_quarter} {current_year}",
    )


def calculate_yoy_growth(
    current_quarter: str,
    current_year: int,
    current_value: float | None,
    data_points: dict[tuple[str, int], float],
    entity_name: str,
) -> GrowthMetrics:
    """
    Calculate year-over-year growth.

    Args:
        current_quarter: Current quarter (Q1-Q4)
        current_year: Current year
        current_value: Current period value
        data_points: Dictionary mapping (quarter, year) to values
        entity_name: Name of entity for result

    Returns:
        GrowthMetrics with YoY calculation

    Example:
        >>> data = {("Q3", 2023): 80.0, ("Q3", 2024): 100.0}
        >>> calculate_yoy_growth("Q3", 2024, 100.0, data, "Intel")
        GrowthMetrics(entity_name='Intel', ..., percent_change=25.0, ...)
    """
    prev_year = current_year - 1
    baseline_value = data_points.get((current_quarter, prev_year))

    return GrowthMetrics(
        entity_name=entity_name,
        baseline_value=baseline_value,
        current_value=current_value,
        absolute_delta=calculate_absolute_delta(current_value, baseline_value),
        percent_change=calculate_percent_change(current_value, baseline_value),
        growth_type=GrowthType.YOY,
        baseline_period=f"{current_quarter} {prev_year}" if baseline_value is not None else "",
        current_period=f"{current_quarter} {current_year}",
    )


# =============================================================================
# Query Builder (T009-T010)
# =============================================================================


class ComparisonQueryBuilder:
    """
    Builder pattern for constructing cross-entity comparison Cypher queries.

    Builds parameterized Cypher queries with:
    - Multi-entity matching
    - Metric filtering
    - Optional time filtering (quarter/year)
    - Entity type filtering with hierarchy expansion
    """

    def __init__(self) -> None:
        """Initialize the query builder."""
        self._entity_names: list[str] = []
        self._metric: str = ""
        self._entity_type_filter: str | None = None
        self._fiscal_quarter: str | None = None
        self._fiscal_year: int | None = None
        self._limit: int = DEFAULT_COMPARISON_LIMIT
        self._type_hierarchy = get_type_hierarchy()

    def for_entities(self, entity_names: list[str]) -> ComparisonQueryBuilder:
        """Set the entities to compare."""
        self._entity_names = entity_names
        return self

    def with_metric(self, metric: str) -> ComparisonQueryBuilder:
        """Set the metric to compare."""
        self._metric = metric
        return self

    def with_entity_type_filter(self, entity_type: str | None) -> ComparisonQueryBuilder:
        """Set optional entity type filter."""
        self._entity_type_filter = entity_type
        return self

    def in_quarter(self, quarter: str | None) -> ComparisonQueryBuilder:
        """Set optional quarter filter."""
        self._fiscal_quarter = quarter.upper() if quarter else None
        return self

    def in_year(self, year: int | None) -> ComparisonQueryBuilder:
        """Set optional year filter."""
        self._fiscal_year = year
        return self

    def with_limit(self, limit: int) -> ComparisonQueryBuilder:
        """Set result limit per entity."""
        self._limit = max(1, min(100, limit))
        return self

    def from_query(self, query: ComparisonQuery) -> ComparisonQueryBuilder:
        """Configure builder from ComparisonQuery model."""
        self._entity_names = query.entity_names
        self._metric = query.metric
        self._entity_type_filter = query.entity_type_filter
        self._fiscal_quarter = query.fiscal_quarter
        self._fiscal_year = query.fiscal_year
        self._limit = query.limit
        return self

    def build(self) -> tuple[str, dict[str, Any]]:
        """
        Build the Cypher query and parameters.

        Returns:
            Tuple of (cypher_query_string, parameters_dict)

        Raises:
            ValueError: If required parameters are not set
        """
        if not self._entity_names:
            raise ValueError("At least 2 entity names are required")

        if len(self._entity_names) < DEFAULT_MIN_ENTITIES:
            raise ValueError(f"At least {DEFAULT_MIN_ENTITIES} entity names required")

        if not self._metric:
            raise ValueError("Metric is required")

        params: dict[str, Any] = {
            "entity_patterns": [name.lower() for name in self._entity_names],
            "metric_pattern": self._metric.lower(),
            "limit_per_entity": self._limit,
        }

        # Build WHERE clauses
        where_clauses = self._build_where_clauses(params)
        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Build the query for multi-entity comparison
        query = f"""
        UNWIND $entity_patterns AS entity_pattern
        MATCH (e:Entity)-[:HAS_EPISODE]->(ep:Episode)
        WHERE toLower(e.name) CONTAINS entity_pattern
          AND {where_str}
        UNWIND ep.numeric_facts AS fact
        WHERE toLower(coalesce(fact.fact_type, '')) CONTAINS $metric_pattern
           OR toLower(coalesce(fact.type, '')) CONTAINS $metric_pattern
           OR toLower(coalesce(fact.original_text, '')) CONTAINS $metric_pattern
        WITH e.name AS entity_name,
             e.type AS entity_type,
             ep.fiscal_quarter AS fiscal_quarter,
             ep.fiscal_year AS fiscal_year,
             fact,
             e.document_refs AS doc_refs
        WITH entity_name,
             entity_type,
             fiscal_quarter,
             fiscal_year,
             avg(toFloat(fact.value)) AS avg_value,
             collect(DISTINCT fact.unit)[0] AS unit,
             collect(DISTINCT coalesce(fact.fact_type, fact.type))[0] AS metric_type,
             count(fact) AS fact_count,
             doc_refs
        RETURN entity_name,
               entity_type,
               fiscal_quarter,
               fiscal_year,
               avg_value AS value,
               unit,
               metric_type,
               fact_count,
               [d IN coalesce(doc_refs, []) | d.filename] AS source_documents
        ORDER BY entity_name, fiscal_year DESC, fiscal_quarter DESC
        LIMIT $limit_per_entity * size($entity_patterns)
        """

        logger.debug(
            "ComparisonQueryBuilder.build",
            entity_count=len(self._entity_names),
            metric=self._metric,
            entity_type_filter=self._entity_type_filter,
            fiscal_quarter=self._fiscal_quarter,
            fiscal_year=self._fiscal_year,
        )

        return query.strip(), params

    def _build_where_clauses(self, params: dict[str, Any]) -> list[str]:
        """Build WHERE clauses for filtering."""
        clauses = []

        # Entity type filtering with hierarchy expansion
        if self._entity_type_filter:
            expanded_types = self._type_hierarchy.expand_type_filter(self._entity_type_filter)
            params["entity_types"] = [t.lower() for t in expanded_types]
            clauses.append("toLower(e.type) IN $entity_types")

        # Time filtering
        if self._fiscal_quarter:
            params["fiscal_quarter"] = self._fiscal_quarter
            clauses.append("ep.fiscal_quarter = $fiscal_quarter")

        if self._fiscal_year:
            params["fiscal_year"] = self._fiscal_year
            clauses.append("ep.fiscal_year = $fiscal_year")

        return clauses


# =============================================================================
# Result Parser (T011)
# =============================================================================


class ComparisonResultParser:
    """
    Parses Neo4j comparison records into EntityMetrics and results.

    Handles conversion from raw Cypher results to typed dataclasses
    with aggregation by entity and ranking calculation.
    """

    @staticmethod
    def parse_record(record: dict[str, Any]) -> EntityMetrics:
        """
        Parse a single Neo4j record into an EntityMetrics.

        Args:
            record: Dictionary from Neo4j query result

        Returns:
            EntityMetrics with parsed data
        """
        # Handle source_documents which may be a list or None
        source_docs = record.get("source_documents", []) or []
        if isinstance(source_docs, list):
            source_docs = [str(d) for d in source_docs if d is not None]
        else:
            source_docs = []

        return EntityMetrics(
            entity_name=record.get("entity_name", ""),
            entity_type=record.get("entity_type", "") or "",
            value=float(record["value"]) if record.get("value") is not None else None,
            unit=record.get("unit", "") or "",
            metric_type=record.get("metric_type", "") or "",
            fiscal_quarter=record.get("fiscal_quarter"),
            fiscal_year=record.get("fiscal_year"),
            fact_count=int(record.get("fact_count", 0)),
            source_documents=source_docs,
        )

    @staticmethod
    def parse_records(records: list[dict[str, Any]]) -> list[EntityMetrics]:
        """
        Parse multiple Neo4j records into EntityMetrics.

        Args:
            records: List of dictionaries from Neo4j query results

        Returns:
            List of EntityMetrics objects
        """
        return [ComparisonResultParser.parse_record(r) for r in records]

    @staticmethod
    def aggregate_by_entity(
        metrics: list[EntityMetrics],
        entity_names: list[str],
    ) -> list[EntityMetrics]:
        """
        Aggregate metrics by entity, ensuring all requested entities are represented.

        Takes the first (most recent) record per entity and fills in placeholders
        for entities without data.

        Args:
            metrics: List of EntityMetrics from query
            entity_names: Original list of requested entity names

        Returns:
            List of EntityMetrics, one per requested entity
        """
        # Group by entity (case-insensitive matching)
        entity_map: dict[str, EntityMetrics] = {}
        for metric in metrics:
            key = metric.entity_name.lower()
            if key not in entity_map:
                entity_map[key] = metric

        # Build result list preserving original order
        result: list[EntityMetrics] = []
        for name in entity_names:
            key = name.lower()
            if key in entity_map:
                result.append(entity_map[key])
            else:
                # Create placeholder for missing entity
                result.append(
                    EntityMetrics(
                        entity_name=name,
                        entity_type="",
                        value=None,
                    )
                )

        return result

    @staticmethod
    def rank_entities(
        metrics: list[EntityMetrics],
        sort_order: SortOrder = SortOrder.DESCENDING,
    ) -> list[str]:
        """
        Rank entities by their metric values.

        Entities without values are placed at the end.

        Args:
            metrics: List of EntityMetrics to rank
            sort_order: Ascending or descending order

        Returns:
            List of entity names in ranked order
        """
        # Separate entities with and without values
        with_values = [(m.entity_name, m.value) for m in metrics if m.value is not None]
        without_values = [m.entity_name for m in metrics if m.value is None]

        # Sort entities with values
        reverse = sort_order == SortOrder.DESCENDING
        with_values.sort(key=lambda x: x[1] or 0, reverse=reverse)

        # Combine: ranked entities first, then entities without values
        return [name for name, _ in with_values] + without_values


# =============================================================================
# Execute Function (T012)
# =============================================================================


async def execute_comparison(
    connection_manager: ConnectionManager,
    query: ComparisonQuery,
    use_cache: bool = True,
    timeout_seconds: float | None = None,
) -> EntityComparisonResult:
    """
    Execute a cross-entity comparison query against Neo4j.

    This is the main entry point for comparison queries. It validates
    type compatibility, builds the Cypher query, executes it, and
    parses the results with ranking. Results are cached for improved
    performance on repeated queries.

    Args:
        connection_manager: Initialized database connection manager
        query: ComparisonQuery parameters
        use_cache: Whether to use query result caching (default True)
        timeout_seconds: Query timeout (default from settings)

    Returns:
        EntityComparisonResult with side-by-side comparison data

    Raises:
        ValueError: If connection_manager is None

    Example:
        >>> query = ComparisonQuery(
        ...     entity_names=["Intel", "AMD"],
        ...     metric="revenue",
        ...     fiscal_quarter="Q3",
        ...     fiscal_year=2024,
        ... )
        >>> result = await execute_comparison(connection_manager, query)
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
        "execute_comparison called",
        entity_names=query.entity_names,
        metric=query.metric,
        entity_type_filter=query.entity_type_filter,
        fiscal_quarter=query.fiscal_quarter,
        fiscal_year=query.fiscal_year,
        use_cache=use_cache,
    )

    # Check cache first
    cache = get_query_cache()
    cache_key = generate_cache_key(
        query=",".join(sorted(query.entity_names)),
        params={
            "metric": query.metric,
            "entity_type_filter": query.entity_type_filter,
            "fiscal_quarter": query.fiscal_quarter,
            "fiscal_year": query.fiscal_year,
            "include_growth": query.include_growth,
            "growth_type": query.growth_type.value,
            "limit": query.limit,
        },
        prefix="comparison",
    )

    if use_cache:
        hit, cached_result = cache.get(CacheType.COMPARISON, cache_key)
        if hit:
            logger.info(
                "execute_comparison cache hit",
                entity_names=query.entity_names,
                cache_key=cache_key[:16],
            )
            return cached_result

    # Build query
    builder = ComparisonQueryBuilder().from_query(query)
    cypher, params = builder.build()

    logger.debug("execute_comparison cypher", cypher_preview=cypher[:200])

    # Get circuit breaker for Neo4j
    neo4j_breaker = get_circuit_breaker(ServiceType.NEO4J)

    # Check if circuit is open
    if not await neo4j_breaker.can_execute():
        logger.warning(
            "execute_comparison circuit open",
            entity_names=query.entity_names,
            circuit_state=neo4j_breaker.state.value,
        )
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        return EntityComparisonResult(
            comparison_valid=False,
            error_message="Knowledge graph temporarily unavailable. Please try again later.",
            entities_compared=len(query.entity_names),
            query_time_ms=query_time,
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
            "execute_comparison timeout",
            entity_names=query.entity_names,
            timeout_seconds=timeout_seconds,
        )
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        return EntityComparisonResult(
            comparison_valid=False,
            error_message=f"Query timed out after {timeout_seconds}s",
            entities_compared=len(query.entity_names),
            query_time_ms=query_time,
        )

    except Exception as e:
        await neo4j_breaker.record_failure(e)
        logger.exception(
            "execute_comparison failed",
            error=str(e),
            entity_names=query.entity_names,
        )
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        return EntityComparisonResult(
            comparison_valid=False,
            error_message="Unable to complete comparison. Please try again.",
            entities_compared=len(query.entity_names),
            query_time_ms=query_time,
        )

    # Parse results
    metrics = ComparisonResultParser.parse_records(records)
    aggregated = ComparisonResultParser.aggregate_by_entity(metrics, query.entity_names)

    # Validate type compatibility
    entity_types = get_entities_with_types(aggregated)
    is_compatible, error_msg = validate_type_compatibility(entity_types)

    if not is_compatible:
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        return EntityComparisonResult(
            entities=aggregated,
            metric=query.metric,
            comparison_valid=False,
            error_message=error_msg,
            entities_compared=len(query.entity_names),
            entities_with_data=sum(1 for m in aggregated if m.has_value),
            query_time_ms=query_time,
        )

    # Rank entities
    ranking = ComparisonResultParser.rank_entities(aggregated, query.sort_order)

    # Sort entities by ranking
    rank_order = {name: i for i, name in enumerate(ranking)}
    aggregated.sort(key=lambda m: rank_order.get(m.entity_name.lower(), len(ranking)))

    # Calculate growth metrics if requested
    growth_metrics: list[GrowthMetrics] = []
    if query.include_growth and query.fiscal_quarter and query.fiscal_year:
        growth_metrics = _calculate_growth_for_entities(
            aggregated,
            query.growth_type,
            query.fiscal_quarter,
            query.fiscal_year,
            metrics,  # Pass all metrics for lookups
        )

    query_time = (datetime.now() - start_time).total_seconds() * 1000

    # Build result
    comparison_result = EntityComparisonResult(
        entities=aggregated,
        metric=query.metric,
        comparison_valid=True,
        entities_compared=len(query.entity_names),
        entities_with_data=sum(1 for m in aggregated if m.has_value),
        ranking=ranking,
        growth_metrics=growth_metrics,
        query_time_ms=query_time,
    )

    # Cache results
    if use_cache:
        cache.set(CacheType.COMPARISON, cache_key, comparison_result)

    logger.info(
        "execute_comparison completed",
        entities_found=len(aggregated),
        entities_with_data=sum(1 for m in aggregated if m.has_value),
        query_time_ms=query_time,
        cached=use_cache,
    )

    return comparison_result


def _calculate_growth_for_entities(
    aggregated: list[EntityMetrics],
    growth_type: GrowthType,
    fiscal_quarter: str,
    fiscal_year: int,
    all_metrics: list[EntityMetrics],
) -> list[GrowthMetrics]:
    """
    Calculate growth metrics for all entities.

    Args:
        aggregated: Aggregated metrics (one per entity)
        growth_type: Type of growth calculation
        fiscal_quarter: Current quarter
        fiscal_year: Current year
        all_metrics: All metrics from query for lookups

    Returns:
        List of GrowthMetrics for each entity
    """
    # Build lookup dict: (entity_name_lower, quarter, year) -> value
    data_lookup: dict[str, dict[tuple[str, int], float]] = {}
    for m in all_metrics:
        if m.value is not None and m.fiscal_quarter and m.fiscal_year:
            entity_key = m.entity_name.lower()
            if entity_key not in data_lookup:
                data_lookup[entity_key] = {}
            data_lookup[entity_key][(m.fiscal_quarter, m.fiscal_year)] = m.value

    results: list[GrowthMetrics] = []
    for entity in aggregated:
        entity_key = entity.entity_name.lower()
        entity_data = data_lookup.get(entity_key, {})

        if growth_type == GrowthType.QOQ:
            growth = calculate_qoq_growth(
                fiscal_quarter,
                fiscal_year,
                entity.value,
                entity_data,
                entity.entity_name,
            )
        elif growth_type == GrowthType.YOY:
            growth = calculate_yoy_growth(
                fiscal_quarter,
                fiscal_year,
                entity.value,
                entity_data,
                entity.entity_name,
            )
        else:
            # For ABSOLUTE and PERCENTAGE, we need baseline data
            # Default to current value only
            growth = GrowthMetrics(
                entity_name=entity.entity_name,
                current_value=entity.value,
                growth_type=growth_type,
                current_period=entity.period_label,
            )

        results.append(growth)

    return results


# =============================================================================
# Convenience Functions
# =============================================================================


async def compare_entities(
    connection_manager: ConnectionManager,
    entity_names: list[str],
    metric: str,
    fiscal_quarter: str | None = None,
    fiscal_year: int | None = None,
    entity_type_filter: str | None = None,
    include_growth: bool = False,
    growth_type: GrowthType = GrowthType.PERCENTAGE,
) -> EntityComparisonResult:
    """
    Compare multiple entities on a specific metric.

    Convenience wrapper for common comparison use cases.

    Args:
        connection_manager: Database connection manager
        entity_names: List of 2-5 entity names to compare
        metric: Metric to compare (e.g., "revenue", "profit")
        fiscal_quarter: Optional quarter filter (Q1-Q4)
        fiscal_year: Optional year filter
        entity_type_filter: Optional entity type filter
        include_growth: Whether to include growth calculations
        growth_type: Type of growth calculation

    Returns:
        EntityComparisonResult with side-by-side data

    Example:
        >>> result = await compare_entities(
        ...     connection_manager,
        ...     ["Intel", "AMD", "NVIDIA"],
        ...     "revenue",
        ...     fiscal_quarter="Q3",
        ...     fiscal_year=2024,
        ... )
        >>> print(result.get_summary())
    """
    query = ComparisonQuery(
        entity_names=entity_names,
        metric=metric,
        entity_type_filter=entity_type_filter,
        fiscal_quarter=fiscal_quarter,
        fiscal_year=fiscal_year,
        include_growth=include_growth,
        growth_type=growth_type,
    )
    return await execute_comparison(connection_manager, query)
