"""Entity resolution package for deduplication and canonical name management.

This package provides multi-pass entity deduplication for the Neo4j knowledge graph,
including exact matching, fuzzy matching, and context-based disambiguation.

Public API:
    - normalize_entity_name: Normalize entity names (strip suffixes, standardize)
    - get_canonical_name: Get canonical name from ticker or alias
    - EntityResolver: Main facade for entity deduplication
    - find_duplicates: Find duplicate entities in the graph
    - MergeOperation: Pydantic model for merge operations
    - MergeHistory: Logging and retrieval of merge operations
"""

from src.agentic_rag.entity_resolution.canonical_names import (
    COMPANY_SUFFIXES,
    TICKER_TO_CANONICAL,
    get_canonical_name,
    normalize_entity_name,
)
from src.agentic_rag.entity_resolution.deduplication import (
    EntityResolver,
    find_duplicates,
)
from src.agentic_rag.entity_resolution.merge_history import (
    MergeHistory,
    MergeOperation,
)

__all__ = [
    "COMPANY_SUFFIXES",
    "TICKER_TO_CANONICAL",
    "EntityResolver",
    "MergeHistory",
    "MergeOperation",
    "find_duplicates",
    "get_canonical_name",
    "normalize_entity_name",
]
