"""
Graph utilities for Agentic RAG knowledge graph operations.

This module provides utilities for working with the Neo4j knowledge graph:
- temporal_parser: Extract temporal metadata from document filenames
- numeric_parser: Extract numeric facts (currency, percentages) from episode text
- relationship_scoring: Calculate dynamic relationship strength scores
- type_hierarchy: Semantic entity type grouping for hierarchical queries
- multi_hop: Multi-hop query engine for relationship traversal
- temporal_queries: Temporal trend analysis and time-series comparisons
"""

from .entity_comparison import (
    ComparisonQuery,
    ComparisonQueryBuilder,
    ComparisonResultParser,
    EntityComparisonResult,
    EntityMetrics,
    GrowthMetrics,
    GrowthType,
    SortOrder,
    TypeCompatibilityError,
    calculate_absolute_delta,
    calculate_percent_change,
    calculate_qoq_growth,
    calculate_yoy_growth,
    compare_entities,
    execute_comparison,
    validate_type_compatibility,
)
from .multi_hop import (
    MultiHopQuery,
    MultiHopQueryBuilder,
    PathNode,
    PathResult,
    PathResultParser,
    PathStep,
    execute_multi_hop,
    explore_entity_neighborhood,
    find_paths_between,
)
from .numeric_parser import (
    CURRENCY_SYMBOL_MAP,
    MAGNITUDE_MAP,
    NumericFact,
    extract_numeric_facts_json,
    parse_numeric_facts,
)
from .relationship_scoring import (
    DEFAULT_IMPORTANCE_SCORE,
    DEFAULT_MAX_CHUNKS,
    DEFAULT_TYPE_PRIORITY,
    TYPE_PRIORITIES,
    ScoringConfig,
    calculate_relationship_strength,
    calculate_relationship_strength_from_dict,
)
from .temporal_parser import (
    FILENAME_PATTERN,
    TemporalMetadata,
    extract_temporal_properties,
    get_company_name,
    parse_filename,
)
from .temporal_queries import (
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
    compare_quarters,
    compare_years,
    execute_temporal_query,
    get_entity_trend,
    int_to_quarter,
    quarter_sort_key,
    quarter_to_int,
)
from .type_hierarchy import (
    TYPE_HIERARCHY,
    TypeHierarchy,
    get_type_hierarchy,
)

__all__ = [
    # Constants
    "CURRENCY_SYMBOL_MAP",
    "DEFAULT_IMPORTANCE_SCORE",
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_TYPE_PRIORITY",
    "FILENAME_PATTERN",
    "MAGNITUDE_MAP",
    "TYPE_HIERARCHY",
    "TYPE_PRIORITIES",
    # Models and Classes
    "ComparisonQuery",
    "ComparisonQueryBuilder",
    "ComparisonResult",
    "ComparisonResultParser",
    # Enums
    "ComparisonType",
    "DataPoint",
    "EntityComparisonResult",
    "EntityMetrics",
    "GrowthMetrics",
    "GrowthType",
    "MultiHopQuery",
    "MultiHopQueryBuilder",
    "NumericFact",
    "PathNode",
    "PathResult",
    "PathResultParser",
    "PathStep",
    "ScoringConfig",
    "SortOrder",
    "TemporalMetadata",
    "TemporalQuery",
    "TemporalQueryBuilder",
    "TrendDirection",
    "TrendResult",
    "TrendResultParser",
    "TypeCompatibilityError",
    "TypeHierarchy",
    # Functions - Comparison
    "calculate_absolute_delta",
    "calculate_percent_change",
    # Functions - Temporal
    "calculate_qoq_comparison",
    "calculate_qoq_growth",
    "calculate_relationship_strength",
    "calculate_relationship_strength_from_dict",
    "calculate_yoy_comparison",
    "calculate_yoy_growth",
    "compare_entities",
    "compare_quarters",
    "compare_years",
    "execute_comparison",
    # Functions - Multi-hop
    "execute_multi_hop",
    "execute_temporal_query",
    "explore_entity_neighborhood",
    # Functions - Parsing
    "extract_numeric_facts_json",
    "extract_temporal_properties",
    "find_paths_between",
    "get_company_name",
    "get_entity_trend",
    "get_type_hierarchy",
    "int_to_quarter",
    "parse_filename",
    "parse_numeric_facts",
    "quarter_sort_key",
    "quarter_to_int",
    "validate_type_compatibility",
]
