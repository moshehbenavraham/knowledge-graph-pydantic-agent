"""
Relationship scoring functions for dynamic strength calculation.

This module provides evidence-based scoring for knowledge graph relationships,
computing strength values based on:
- Chunk count (more mentions = stronger evidence)
- Relationship type priority (e.g., ACQUIRED > MENTIONED_IN)
- Entity importance scores (relationships between important entities score higher)
"""

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# Relationship type priorities (0.0 to 1.0)
# Higher values indicate stronger/more significant relationship types
TYPE_PRIORITIES: dict[str, float] = {
    # Ownership/Control relationships (highest priority)
    "acquired": 1.0,
    "owns": 1.0,
    "merged_with": 0.95,
    "subsidiary_of": 0.9,
    # Founding/Creation relationships
    "founded": 0.85,
    "created": 0.8,
    # Financial relationships
    "invested_in": 0.75,
    "funded": 0.7,
    "financed": 0.7,
    # Employment/Affiliation relationships
    "works_at": 0.6,
    "employed_by": 0.6,
    "leads": 0.65,
    "manages": 0.6,
    # Partnership/Collaboration relationships
    "partners_with": 0.55,
    "collaborates_with": 0.55,
    "allied_with": 0.5,
    # Competition relationships
    "competes_with": 0.5,
    "rivals": 0.5,
    # Location relationships
    "located_in": 0.4,
    "headquartered_in": 0.45,
    # Generic/Weak relationships (lowest priority)
    "related_to": 0.3,
    "mentioned_in": 0.25,
    "associated_with": 0.35,
}

# Default priority for unknown relationship types
DEFAULT_TYPE_PRIORITY: float = 0.5

# Maximum chunks for normalization (relationships with >= MAX_CHUNKS get full chunk_factor)
DEFAULT_MAX_CHUNKS: int = 10

# Default importance score when entity lacks explicit importance_score
DEFAULT_IMPORTANCE_SCORE: float = 0.5


@dataclass
class ScoringConfig:
    """Configuration for relationship scoring weights and thresholds.

    Attributes:
        w1: Weight for chunk count factor (0.0-1.0)
        w2: Weight for relationship type factor (0.0-1.0)
        w3: Weight for entity importance factor (0.0-1.0)
        max_chunks: Maximum chunks for normalization
        default_importance: Default importance score for entities without explicit scores
    """

    w1: float = 0.4  # Chunk count weight
    w2: float = 0.3  # Type priority weight
    w3: float = 0.3  # Importance weight
    max_chunks: int = DEFAULT_MAX_CHUNKS
    default_importance: float = DEFAULT_IMPORTANCE_SCORE

    def __post_init__(self) -> None:
        """Validate weights sum to 1.0."""
        total = self.w1 + self.w2 + self.w3
        if abs(total - 1.0) > 0.001:
            logger.warning(
                "Scoring weights do not sum to 1.0, results may be unexpected",
                w1=self.w1,
                w2=self.w2,
                w3=self.w3,
                total=total,
            )


def _normalize_chunk_factor(chunk_count: int, max_chunks: int = DEFAULT_MAX_CHUNKS) -> float:
    """
    Normalize chunk count to a factor between 0.0 and 1.0.

    More chunks indicate stronger evidence for the relationship.

    Args:
        chunk_count: Number of source chunks referencing this relationship
        max_chunks: Maximum chunks for full score (default: 10)

    Returns:
        Normalized factor between 0.0 and 1.0
    """
    if chunk_count <= 0:
        return 0.0
    if max_chunks <= 0:
        return 1.0
    return min(1.0, chunk_count / max_chunks)


def _get_type_priority(relationship_type: str | None) -> float:
    """
    Get priority score for a relationship type.

    Args:
        relationship_type: The relationship type string (e.g., 'acquired', 'works_at')

    Returns:
        Priority score between 0.0 and 1.0
    """
    if not relationship_type:
        return DEFAULT_TYPE_PRIORITY

    # Normalize type to lowercase for lookup
    normalized_type = relationship_type.lower().strip()

    return TYPE_PRIORITIES.get(normalized_type, DEFAULT_TYPE_PRIORITY)


def _calculate_importance_factor(
    entity1_importance: float | None,
    entity2_importance: float | None,
    default_importance: float = DEFAULT_IMPORTANCE_SCORE,
) -> float:
    """
    Calculate importance factor from two entity importance scores.

    Uses the average of both entity importance scores.

    Args:
        entity1_importance: Importance score of first entity (0.0-1.0)
        entity2_importance: Importance score of second entity (0.0-1.0)
        default_importance: Default score for missing values

    Returns:
        Average importance factor between 0.0 and 1.0
    """
    # Handle None values with default
    score1 = entity1_importance if entity1_importance is not None else default_importance
    score2 = entity2_importance if entity2_importance is not None else default_importance

    # Clamp to valid range
    score1 = max(0.0, min(1.0, score1))
    score2 = max(0.0, min(1.0, score2))

    return (score1 + score2) / 2.0


def calculate_relationship_strength(
    chunk_count: int = 1,
    relationship_type: str | None = None,
    entity1_importance: float | None = None,
    entity2_importance: float | None = None,
    config: ScoringConfig | None = None,
) -> float:
    """
    Calculate dynamic relationship strength based on evidence factors.

    The strength score is a weighted combination of three factors:
    - Chunk factor: More mentions across chunks = stronger evidence
    - Type factor: Relationship type priority (e.g., ACQUIRED > MENTIONED_IN)
    - Importance factor: Relationships between important entities score higher

    Formula: strength = (w1 * chunk_factor) + (w2 * type_factor) + (w3 * importance_factor)

    Args:
        chunk_count: Number of source chunks referencing this relationship
        relationship_type: The relationship type string (e.g., 'acquired', 'works_at')
        entity1_importance: Importance score of first entity (0.0-1.0)
        entity2_importance: Importance score of second entity (0.0-1.0)
        config: Optional scoring configuration (uses defaults if None)

    Returns:
        Relationship strength between 0.0 and 1.0

    Example:
        >>> strength = calculate_relationship_strength(
        ...     chunk_count=5,
        ...     relationship_type='acquired',
        ...     entity1_importance=0.8,
        ...     entity2_importance=0.6
        ... )
        >>> print(f"Strength: {strength:.3f}")
        Strength: 0.710
    """
    if config is None:
        config = ScoringConfig()

    # Calculate individual factors
    chunk_factor = _normalize_chunk_factor(chunk_count, config.max_chunks)
    type_factor = _get_type_priority(relationship_type)
    importance_factor = _calculate_importance_factor(
        entity1_importance, entity2_importance, config.default_importance
    )

    # Weighted combination
    strength = (
        (config.w1 * chunk_factor) + (config.w2 * type_factor) + (config.w3 * importance_factor)
    )

    # Ensure result is in valid range [0.0, 1.0]
    strength = max(0.0, min(1.0, strength))

    logger.debug(
        "calculate_relationship_strength",
        chunk_count=chunk_count,
        chunk_factor=chunk_factor,
        relationship_type=relationship_type,
        type_factor=type_factor,
        importance_factor=importance_factor,
        final_strength=strength,
    )

    return strength


def calculate_relationship_strength_from_dict(
    relationship: dict[str, Any],
    entity1: dict[str, Any] | None = None,
    entity2: dict[str, Any] | None = None,
    config: ScoringConfig | None = None,
) -> float:
    """
    Calculate relationship strength from Neo4j relationship and entity dictionaries.

    Convenience function for use with Neo4j query results.

    Args:
        relationship: Relationship dictionary with 'type' and 'source_chunks' keys
        entity1: First entity dictionary with optional 'importance_score' key
        entity2: Second entity dictionary with optional 'importance_score' key
        config: Optional scoring configuration

    Returns:
        Relationship strength between 0.0 and 1.0
    """
    # Extract chunk count from source_chunks list
    # Default to 1 if source_chunks is missing or empty (minimum evidence)
    source_chunks = relationship.get("source_chunks")
    if isinstance(source_chunks, list) and len(source_chunks) > 0:
        chunk_count = len(source_chunks)
    else:
        chunk_count = 1  # Default to 1 for minimum evidence

    # Extract relationship type
    rel_type = relationship.get("type")

    # Extract entity importance scores
    entity1_importance = None
    entity2_importance = None

    if entity1:
        entity1_importance = entity1.get("importance_score")
    if entity2:
        entity2_importance = entity2.get("importance_score")

    return calculate_relationship_strength(
        chunk_count=chunk_count,
        relationship_type=rel_type,
        entity1_importance=entity1_importance,
        entity2_importance=entity2_importance,
        config=config,
    )
