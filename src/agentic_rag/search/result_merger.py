"""
Result merger for normalizing heterogeneous search results.

This module provides a unified interface for merging results from different
query engines (multi-hop, temporal, comparison) into a common format for
ranking and presentation.

Key components:
- SearchResultItem: Normalized dataclass for any search result type
- ResultMerger: Merges and normalizes heterogeneous results
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ResultType(str, Enum):
    """Type of search result."""

    VECTOR_CHUNK = "vector_chunk"
    GRAPH_PATH = "graph_path"
    TEMPORAL_TREND = "temporal_trend"
    ENTITY_COMPARISON = "entity_comparison"
    ENTITY = "entity"
    FACT = "fact"


@dataclass
class SearchResultItem:
    """
    Normalized search result item from any query engine.

    This dataclass provides a common structure for all result types,
    enabling unified ranking and presentation.

    Attributes:
        result_type: Type of the original result
        title: Human-readable title or summary
        content: Main content or description
        relevance_score: Normalized relevance score (0.0-1.0)
        relationship_strength: For path/relationship results (0.0-1.0)
        temporal_recency: Recency score for temporal results (0.0-1.0)
        entities: List of entity names involved
        source_documents: Document references for provenance
        metadata: Additional type-specific metadata
        created_at: When this result was generated
        original_result: Reference to the original result object
    """

    result_type: ResultType
    title: str
    content: str
    relevance_score: float = 0.0
    relationship_strength: float | None = None
    temporal_recency: float | None = None
    entities: list[str] = field(default_factory=list)
    source_documents: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    original_result: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "result_type": self.result_type.value,
            "title": self.title,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "relationship_strength": self.relationship_strength,
            "temporal_recency": self.temporal_recency,
            "entities": self.entities,
            "source_documents": self.source_documents,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def combined_score(self) -> float:
        """
        Calculate combined score from all available signals.

        Uses weighted average of available scores.
        """
        scores = [self.relevance_score]
        weights = [1.0]

        if self.relationship_strength is not None:
            scores.append(self.relationship_strength)
            weights.append(0.8)

        if self.temporal_recency is not None:
            scores.append(self.temporal_recency)
            weights.append(0.6)

        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        return sum(s * w for s, w in zip(scores, weights, strict=False)) / total_weight


class ResultMerger:
    """
    Merge heterogeneous search results into a unified format.

    The ResultMerger normalizes results from different query engines
    (vector search, multi-hop traversal, temporal trends, entity comparisons)
    into SearchResultItem objects that can be uniformly ranked.

    Example:
        >>> merger = ResultMerger()
        >>> items = merger.merge_all(
        ...     chunks=vector_results,
        ...     paths=path_results,
        ...     trends=[trend_result],
        ...     comparisons=[comparison_result],
        ... )
        >>> for item in items:
        ...     print(f"{item.title}: {item.combined_score:.2f}")
    """

    def __init__(self) -> None:
        """Initialize the result merger."""
        self._stats: dict[str, int] = {
            "merges": 0,
            "chunks_merged": 0,
            "paths_merged": 0,
            "trends_merged": 0,
            "comparisons_merged": 0,
        }
        logger.info("ResultMerger initialized")

    def merge_all(
        self,
        chunks: list[Any] | None = None,
        paths: list[Any] | None = None,
        trends: list[Any] | None = None,
        comparisons: list[Any] | None = None,
        deduplicate: bool = True,
    ) -> list[SearchResultItem]:
        """
        Merge all result types into unified SearchResultItems.

        Args:
            chunks: Vector search ChunkResult objects
            paths: Multi-hop PathResult objects
            trends: Temporal TrendResult objects
            comparisons: Entity comparison EntityComparisonResult objects
            deduplicate: Whether to deduplicate by content

        Returns:
            List of normalized SearchResultItem objects
        """
        self._stats["merges"] += 1
        items: list[SearchResultItem] = []

        if chunks:
            items.extend(self.normalize_chunks(chunks))

        if paths:
            items.extend(self.normalize_paths(paths))

        if trends:
            items.extend(self.normalize_trends(trends))

        if comparisons:
            items.extend(self.normalize_comparisons(comparisons))

        if deduplicate:
            items = self._deduplicate(items)

        logger.info(
            "ResultMerger.merge_all completed",
            total_items=len(items),
            chunks=len(chunks) if chunks else 0,
            paths=len(paths) if paths else 0,
            trends=len(trends) if trends else 0,
            comparisons=len(comparisons) if comparisons else 0,
        )

        return items

    def normalize_chunks(self, chunks: list[Any]) -> list[SearchResultItem]:
        """
        Normalize vector search ChunkResult objects.

        Args:
            chunks: List of ChunkResult objects

        Returns:
            List of SearchResultItem objects
        """
        items: list[SearchResultItem] = []

        for chunk in chunks:
            try:
                # Extract chunk attributes
                title = getattr(chunk, "document_title", "Untitled")
                content = getattr(chunk, "content", "")
                similarity = getattr(chunk, "similarity", 0.0)
                entities = getattr(chunk, "entities", [])
                source = getattr(chunk, "document_source", "")

                item = SearchResultItem(
                    result_type=ResultType.VECTOR_CHUNK,
                    title=title,
                    content=content[:500] if content else "",
                    relevance_score=float(similarity),
                    entities=list(entities) if entities else [],
                    source_documents=[source] if source else [],
                    metadata={
                        "chunk_id": str(getattr(chunk, "chunk_id", "")),
                        "document_id": str(getattr(chunk, "document_id", "")),
                    },
                    original_result=chunk,
                )
                items.append(item)
                self._stats["chunks_merged"] += 1

            except Exception as e:
                logger.warning("Failed to normalize chunk", error=str(e))

        return items

    def normalize_paths(self, paths: list[Any]) -> list[SearchResultItem]:
        """
        Normalize multi-hop PathResult objects.

        Args:
            paths: List of PathResult objects

        Returns:
            List of SearchResultItem objects
        """
        items: list[SearchResultItem] = []

        for path in paths:
            try:
                # Extract path attributes
                nodes = getattr(path, "nodes", [])
                summary = path.get_path_summary() if hasattr(path, "get_path_summary") else ""
                strength = getattr(path, "cumulative_strength", 0.0)
                hop_count = getattr(path, "hop_count", 0)
                source_docs = getattr(path, "source_documents", [])

                # Extract entity names from nodes
                entities = [n.name for n in nodes if hasattr(n, "name")]

                # Build title from first and last entity
                if len(entities) >= 2:
                    title = f"{entities[0]} -> {entities[-1]}"
                elif entities:
                    title = entities[0]
                else:
                    title = "Path result"

                item = SearchResultItem(
                    result_type=ResultType.GRAPH_PATH,
                    title=title,
                    content=summary,
                    relevance_score=float(strength),
                    relationship_strength=float(strength),
                    entities=entities,
                    source_documents=list(source_docs) if source_docs else [],
                    metadata={
                        "hop_count": hop_count,
                        "node_count": len(nodes),
                    },
                    original_result=path,
                )
                items.append(item)
                self._stats["paths_merged"] += 1

            except Exception as e:
                logger.warning("Failed to normalize path", error=str(e))

        return items

    def normalize_trends(self, trends: list[Any]) -> list[SearchResultItem]:
        """
        Normalize temporal TrendResult objects.

        Args:
            trends: List of TrendResult objects

        Returns:
            List of SearchResultItem objects
        """
        items: list[SearchResultItem] = []

        for trend in trends:
            try:
                # Extract trend attributes
                entity = getattr(trend, "entity", "")
                metric = getattr(trend, "metric", "")
                direction = getattr(trend, "direction", None)
                percent_change = getattr(trend, "percent_change", None)
                time_span = getattr(trend, "time_span", "")
                data_points = getattr(trend, "data_points", [])
                summary = trend.get_summary() if hasattr(trend, "get_summary") else ""

                # Calculate temporal recency based on most recent data point
                recency = 0.0
                if data_points:
                    # More recent data = higher score
                    latest = data_points[-1] if data_points else None
                    if latest:
                        year = getattr(latest, "year", 2020)
                        # Normalize to 0-1 based on year (2020-2025 range)
                        recency = min(1.0, max(0.0, (year - 2020) / 5))

                title = f"{entity} {metric} trend" if entity and metric else "Trend result"

                item = SearchResultItem(
                    result_type=ResultType.TEMPORAL_TREND,
                    title=title,
                    content=summary,
                    relevance_score=0.7,  # Base relevance for trend results
                    temporal_recency=recency,
                    entities=[entity] if entity else [],
                    metadata={
                        "direction": direction.value if direction else None,
                        "percent_change": percent_change,
                        "time_span": time_span,
                        "data_point_count": len(data_points),
                    },
                    original_result=trend,
                )
                items.append(item)
                self._stats["trends_merged"] += 1

            except Exception as e:
                logger.warning("Failed to normalize trend", error=str(e))

        return items

    def normalize_comparisons(self, comparisons: list[Any]) -> list[SearchResultItem]:
        """
        Normalize entity comparison EntityComparisonResult objects.

        Args:
            comparisons: List of EntityComparisonResult objects

        Returns:
            List of SearchResultItem objects
        """
        items: list[SearchResultItem] = []

        for comparison in comparisons:
            try:
                # Extract comparison attributes
                entities_data = getattr(comparison, "entities", [])
                metric = getattr(comparison, "metric", "")
                comparison_valid = getattr(comparison, "comparison_valid", False)
                ranking = getattr(comparison, "ranking", [])
                summary = comparison.get_summary() if hasattr(comparison, "get_summary") else ""

                # Extract entity names
                entities = [e.entity_name for e in entities_data if hasattr(e, "entity_name")]

                title = f"Comparison: {', '.join(entities[:3])}"
                if len(entities) > 3:
                    title += f" (+{len(entities) - 3} more)"

                item = SearchResultItem(
                    result_type=ResultType.ENTITY_COMPARISON,
                    title=title,
                    content=summary,
                    relevance_score=0.8 if comparison_valid else 0.3,
                    entities=entities,
                    metadata={
                        "metric": metric,
                        "comparison_valid": comparison_valid,
                        "entities_compared": len(entities),
                        "ranking": ranking,
                    },
                    original_result=comparison,
                )
                items.append(item)
                self._stats["comparisons_merged"] += 1

            except Exception as e:
                logger.warning("Failed to normalize comparison", error=str(e))

        return items

    def _deduplicate(self, items: list[SearchResultItem]) -> list[SearchResultItem]:
        """
        Remove duplicate results based on content similarity.

        Uses title + entity combination as a simple deduplication key.

        Args:
            items: List of SearchResultItems

        Returns:
            Deduplicated list
        """
        seen: set[str] = set()
        unique: list[SearchResultItem] = []

        for item in items:
            # Create deduplication key
            entities_str = ",".join(sorted(item.entities[:3]))
            key = f"{item.title}|{entities_str}"

            if key not in seen:
                seen.add(key)
                unique.append(item)

        if len(items) != len(unique):
            logger.debug(
                "Deduplicated results",
                original=len(items),
                unique=len(unique),
                removed=len(items) - len(unique),
            )

        return unique

    def get_stats(self) -> dict[str, int]:
        """Get merger statistics."""
        return dict(self._stats)
