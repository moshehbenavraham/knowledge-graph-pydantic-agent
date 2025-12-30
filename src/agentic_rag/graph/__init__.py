"""
Graph utilities for Agentic RAG knowledge graph operations.

This module provides utilities for working with the Neo4j knowledge graph:
- temporal_parser: Extract temporal metadata from document filenames
- numeric_parser: Extract numeric facts (currency, percentages) from episode text
- relationship_scoring: Calculate dynamic relationship strength scores
- type_hierarchy: Semantic entity type grouping for hierarchical queries
- multi_hop: Multi-hop query engine for relationship traversal
"""

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
from .type_hierarchy import (
    TYPE_HIERARCHY,
    TypeHierarchy,
    get_type_hierarchy,
)

__all__ = [
    "CURRENCY_SYMBOL_MAP",
    "DEFAULT_IMPORTANCE_SCORE",
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_TYPE_PRIORITY",
    "FILENAME_PATTERN",
    "MAGNITUDE_MAP",
    "TYPE_HIERARCHY",
    "TYPE_PRIORITIES",
    # Multi-hop query engine
    "MultiHopQuery",
    "MultiHopQueryBuilder",
    "NumericFact",
    "PathNode",
    "PathResult",
    "PathResultParser",
    "PathStep",
    "ScoringConfig",
    "TemporalMetadata",
    "TypeHierarchy",
    "calculate_relationship_strength",
    "calculate_relationship_strength_from_dict",
    "execute_multi_hop",
    "explore_entity_neighborhood",
    "extract_numeric_facts_json",
    "extract_temporal_properties",
    "find_paths_between",
    "get_company_name",
    "get_type_hierarchy",
    "parse_filename",
    "parse_numeric_facts",
]
