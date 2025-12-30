"""
Unified ranker for combining multiple ranking signals.

This module provides a unified ranking function that combines:
- Relevance scores (from vector similarity)
- Relationship strength (from graph traversal)
- Temporal recency (from temporal queries)

Key components:
- RankingSignals: Input signals for ranking calculation
- UnifiedRanker: Combines signals into final ranking
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# Default weights for ranking signals
DEFAULT_RELEVANCE_WEIGHT = 1.0
DEFAULT_RELATIONSHIP_WEIGHT = 0.8
DEFAULT_TEMPORAL_WEIGHT = 0.6


@dataclass
class RankingSignals:
    """
    Input signals for unified ranking calculation.

    These signals are collected from various search result types
    and normalized to 0.0-1.0 range before ranking.

    Attributes:
        relevance_score: Semantic similarity or relevance (0.0-1.0)
        relationship_strength: Cumulative relationship strength (0.0-1.0)
        temporal_recency: How recent the data is (0.0-1.0)
        entity_match_score: How well entities match query (0.0-1.0)
        source_authority: Authority of source documents (0.0-1.0)
    """

    relevance_score: float = 0.0
    relationship_strength: float | None = None
    temporal_recency: float | None = None
    entity_match_score: float | None = None
    source_authority: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "relevance_score": self.relevance_score,
            "relationship_strength": self.relationship_strength,
            "temporal_recency": self.temporal_recency,
            "entity_match_score": self.entity_match_score,
            "source_authority": self.source_authority,
        }

    @classmethod
    def from_search_result_item(cls, item: Any) -> RankingSignals:
        """
        Create RankingSignals from a SearchResultItem.

        Args:
            item: SearchResultItem object

        Returns:
            RankingSignals with extracted values
        """
        return cls(
            relevance_score=getattr(item, "relevance_score", 0.0),
            relationship_strength=getattr(item, "relationship_strength", None),
            temporal_recency=getattr(item, "temporal_recency", None),
        )


@dataclass
class RankingWeights:
    """
    Configurable weights for ranking signals.

    Attributes:
        relevance: Weight for relevance/similarity score
        relationship: Weight for relationship strength
        temporal: Weight for temporal recency
        entity_match: Weight for entity matching
        source_authority: Weight for source authority
    """

    relevance: float = DEFAULT_RELEVANCE_WEIGHT
    relationship: float = DEFAULT_RELATIONSHIP_WEIGHT
    temporal: float = DEFAULT_TEMPORAL_WEIGHT
    entity_match: float = 0.5
    source_authority: float = 0.3

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary representation."""
        return {
            "relevance": self.relevance,
            "relationship": self.relationship,
            "temporal": self.temporal,
            "entity_match": self.entity_match,
            "source_authority": self.source_authority,
        }


class UnifiedRanker:
    """
    Combine multiple ranking signals into a unified score.

    The UnifiedRanker implements a weighted combination of signals
    from different search result types, producing a single ranking
    score for sorting and presentation.

    Default weights:
    - Relevance (vector similarity): 1.0
    - Relationship strength: 0.8
    - Temporal recency: 0.6

    Example:
        >>> ranker = UnifiedRanker()
        >>> ranked = ranker.rank(search_result_items)
        >>> for item in ranked[:10]:
        ...     print(f"{item.title}: {item.final_score:.3f}")
    """

    def __init__(self, weights: RankingWeights | None = None) -> None:
        """
        Initialize the unified ranker.

        Args:
            weights: Custom ranking weights (uses defaults if None)
        """
        self.weights = weights or RankingWeights()
        self._stats: dict[str, int | float] = {
            "rankings": 0,
            "items_ranked": 0,
            "avg_score": 0.0,
        }
        logger.info("UnifiedRanker initialized", weights=self.weights.to_dict())

    def rank(
        self,
        items: list[Any],
        limit: int | None = None,
    ) -> list[Any]:
        """
        Rank search result items by combined score.

        Calculates a unified score for each item based on available
        signals and returns items sorted by score (highest first).

        Args:
            items: List of SearchResultItem objects
            limit: Maximum items to return (None = all)

        Returns:
            Sorted list of items with final_score attribute set
        """
        if not items:
            return []

        self._stats["rankings"] += 1

        # Calculate scores for all items
        scored_items: list[tuple[float, Any]] = []
        for item in items:
            score = self.calculate_score(item)
            # Store score on item for later access
            item.metadata["final_score"] = score
            scored_items.append((score, item))

        # Sort by score (highest first)
        scored_items.sort(key=lambda x: x[0], reverse=True)

        # Update stats
        scores = [s for s, _ in scored_items]
        self._stats["items_ranked"] += len(items)
        if scores:
            self._stats["avg_score"] = sum(scores) / len(scores)

        # Extract sorted items
        ranked = [item for _, item in scored_items]

        if limit is not None:
            ranked = ranked[:limit]

        logger.info(
            "UnifiedRanker.rank completed",
            items_ranked=len(items),
            limit=limit,
            top_score=scores[0] if scores else 0.0,
        )

        return ranked

    def calculate_score(self, item: Any) -> float:
        """
        Calculate unified score for a single item.

        Uses weighted combination of available signals.
        Missing signals (None) are excluded from calculation.

        Args:
            item: SearchResultItem or similar object

        Returns:
            Combined ranking score (0.0-1.0)
        """
        signals = RankingSignals.from_search_result_item(item)
        return self.calculate_score_from_signals(signals)

    def calculate_score_from_signals(self, signals: RankingSignals) -> float:
        """
        Calculate unified score from ranking signals.

        Implements weighted average of available signals:
        score = sum(signal * weight) / sum(weight) for available signals

        Args:
            signals: RankingSignals with input values

        Returns:
            Combined ranking score (0.0-1.0)
        """
        weighted_sum = 0.0
        total_weight = 0.0

        # Relevance is always available
        weighted_sum += signals.relevance_score * self.weights.relevance
        total_weight += self.weights.relevance

        # Add relationship strength if available
        if signals.relationship_strength is not None:
            weighted_sum += signals.relationship_strength * self.weights.relationship
            total_weight += self.weights.relationship

        # Add temporal recency if available
        if signals.temporal_recency is not None:
            weighted_sum += signals.temporal_recency * self.weights.temporal
            total_weight += self.weights.temporal

        # Add entity match if available
        if signals.entity_match_score is not None:
            weighted_sum += signals.entity_match_score * self.weights.entity_match
            total_weight += self.weights.entity_match

        # Add source authority if available
        if signals.source_authority is not None:
            weighted_sum += signals.source_authority * self.weights.source_authority
            total_weight += self.weights.source_authority

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def rerank_with_boost(
        self,
        items: list[Any],
        boost_entities: list[str] | None = None,
        boost_factor: float = 1.2,
        limit: int | None = None,
    ) -> list[Any]:
        """
        Rank items with optional entity-based boosting.

        Items containing specified entities receive a score boost.

        Args:
            items: List of SearchResultItem objects
            boost_entities: Entity names to boost
            boost_factor: Multiplier for matching items (default 1.2)
            limit: Maximum items to return

        Returns:
            Sorted list of items
        """
        if not items:
            return []

        boost_set = {e.lower() for e in (boost_entities or [])}

        scored_items: list[tuple[float, Any]] = []
        for item in items:
            score = self.calculate_score(item)

            # Apply boost if item contains target entities
            if boost_set:
                item_entities = {e.lower() for e in getattr(item, "entities", [])}
                if item_entities & boost_set:
                    score *= boost_factor
                    score = min(1.0, score)  # Cap at 1.0

            item.metadata["final_score"] = score
            scored_items.append((score, item))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        ranked = [item for _, item in scored_items]

        if limit is not None:
            ranked = ranked[:limit]

        logger.debug(
            "UnifiedRanker.rerank_with_boost completed",
            items=len(items),
            boost_entities=len(boost_entities) if boost_entities else 0,
        )

        return ranked

    def get_stats(self) -> dict[str, Any]:
        """Get ranker statistics."""
        return dict(self._stats)
