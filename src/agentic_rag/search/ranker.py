"""
Result ranking and re-ranking algorithms.

Multi-factor ranking system for optimizing search result relevance.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

logger = logging.getLogger(__name__)
structlog_logger = structlog.get_logger(__name__)


@dataclass
class RankedResults:
    """Container for ranked search results."""

    chunks: list[Any] = field(default_factory=list)
    facts: list[Any] = field(default_factory=list)
    relationships: list[Any] = field(default_factory=list)
    ranking_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunks": [c.to_dict() if hasattr(c, "to_dict") else c for c in self.chunks],
            "facts": [f.to_dict() if hasattr(f, "to_dict") else f for f in self.facts],
            "relationships": [
                r.to_dict() if hasattr(r, "to_dict") else r for r in self.relationships
            ],
            "ranking_metadata": self.ranking_metadata,
        }


class ResultRanker:
    """
    Multi-factor result ranking system.

    Ranking factors:
    1. Semantic similarity (40%)
    2. Entity overlap (20%)
    3. Temporal relevance (20%)
    4. Source authority (10%)
    5. Result diversity (10%)
    """

    # Ranking weight configuration
    DEFAULT_WEIGHTS = {
        "similarity": 0.4,
        "entity_overlap": 0.2,
        "temporal_relevance": 0.2,
        "source_authority": 0.1,
        "diversity": 0.1,
    }

    # Known authoritative sources (example)
    AUTHORITY_SCORES = {
        "official_docs": 1.0,
        "whitepaper": 0.9,
        "research_paper": 0.85,
        "news_article": 0.7,
        "blog_post": 0.6,
        "social_media": 0.4,
        "unknown": 0.5,
    }

    def __init__(self, weights: dict[str, float] | None = None):
        """
        Initialize result ranker.

        Args:
            weights: Custom ranking weights
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._normalize_weights()

        self._stats = {
            "rankings_performed": 0,
            "total_chunks_ranked": 0,
            "diversity_adjustments": 0,
            "temporal_boosts": 0,
        }

    def _normalize_weights(self):
        """Normalize weights to sum to 1.0."""
        total = sum(self.weights.values())
        if total > 0:
            for key in self.weights:
                self.weights[key] /= total

    def rank(
        self,
        results: dict[str, Any],
        limit: int = 10,
        query_entities: list[str] | None = None,
        temporal_context: datetime | None = None,
    ) -> RankedResults:
        """
        Rank mixed search results.

        Args:
            results: Dictionary with chunks, facts, relationships
            limit: Maximum number of results
            query_entities: Entities mentioned in query
            temporal_context: Temporal context for ranking

        Returns:
            Ranked results
        """
        structlog_logger.info(
            "Ranking search results",
            limit=limit,
            has_query_entities=bool(query_entities),
            has_temporal_context=bool(temporal_context),
        )
        self._stats["rankings_performed"] += 1

        # Extract components
        chunks = results.get("chunks", [])
        facts = results.get("facts", [])
        relationships = results.get("relationships", [])

        # Rank chunks
        ranked_chunks = self.rank_chunks(chunks, limit, query_entities, temporal_context)

        # Rank facts by confidence and relevance
        ranked_facts = sorted(facts, key=lambda f: getattr(f, "confidence", 0.5), reverse=True)[
            :limit
        ]

        # Rank relationships by confidence
        ranked_relationships = sorted(
            relationships, key=lambda r: getattr(r, "confidence", 0.5), reverse=True
        )[:limit]

        structlog_logger.info(
            "Ranking complete",
            chunks_ranked=len(ranked_chunks),
            facts_ranked=len(ranked_facts),
            relationships_ranked=len(ranked_relationships),
        )
        return RankedResults(
            chunks=ranked_chunks,
            facts=ranked_facts,
            relationships=ranked_relationships,
            ranking_metadata={
                "weights_used": self.weights,
                "chunks_processed": len(chunks),
                "facts_processed": len(facts),
                "relationships_processed": len(relationships),
            },
        )

    def rank_chunks(
        self,
        chunks: list[Any],
        limit: int = 10,
        query_entities: list[str] | None = None,
        temporal_context: datetime | None = None,
    ) -> list[Any]:
        """
        Rank document chunks using multi-factor scoring.

        Args:
            chunks: List of chunk results
            limit: Maximum number of results
            query_entities: Entities from query
            temporal_context: Temporal context

        Returns:
            Ranked list of chunks
        """
        structlog_logger.info(
            "Ranking chunks",
            num_chunks=len(chunks),
            limit=limit,
            has_query_entities=bool(query_entities),
        )
        if not chunks:
            return []

        self._stats["total_chunks_ranked"] += len(chunks)

        # Calculate scores for each chunk
        scored_chunks = []
        seen_content = set()  # For diversity tracking

        for chunk in chunks:
            # Calculate individual factor scores
            scores = {
                "similarity": self._similarity_score(chunk),
                "entity_overlap": self._entity_overlap_score(chunk, query_entities),
                "temporal_relevance": self._temporal_relevance_score(chunk, temporal_context),
                "source_authority": self._authority_score(chunk),
                "diversity": self._diversity_score(chunk, seen_content),
            }

            # Calculate weighted final score
            final_score = sum(scores[factor] * self.weights[factor] for factor in self.weights)

            scored_chunks.append(
                {"chunk": chunk, "final_score": final_score, "factor_scores": scores}
            )

            # Update seen content for diversity
            self._update_seen_content(chunk, seen_content)

        # Sort by final score
        scored_chunks.sort(key=lambda x: x["final_score"], reverse=True)

        # Apply diversity post-processing
        diverse_chunks = self._ensure_diversity(scored_chunks, limit)

        # Extract chunks
        ranked = [item["chunk"] for item in diverse_chunks[:limit]]

        # Attach ranking metadata
        for i, chunk in enumerate(ranked):
            if hasattr(chunk, "metadata"):
                chunk.metadata["rank"] = i + 1
                chunk.metadata["ranking_score"] = diverse_chunks[i]["final_score"]

        structlog_logger.info("Chunk ranking complete", chunks_returned=len(ranked))
        return ranked

    def _similarity_score(self, chunk) -> float:
        """
        Get semantic similarity score.

        Args:
            chunk: Chunk result

        Returns:
            Similarity score (0-1)
        """
        # Use existing similarity if available
        if hasattr(chunk, "similarity"):
            score = chunk.similarity
            structlog_logger.debug("_similarity_score", score=score, source="chunk.similarity")
            return score
        if hasattr(chunk, "score"):
            score = chunk.score
            structlog_logger.debug("_similarity_score", score=score, source="chunk.score")
            return score
        structlog_logger.debug("_similarity_score", score=0.5, source="default")
        return 0.5  # Default middle score

    def _entity_overlap_score(self, chunk, query_entities: list[str] | None) -> float:
        """
        Calculate entity overlap score.

        Args:
            chunk: Chunk result
            query_entities: Entities from query

        Returns:
            Overlap score (0-1)
        """
        structlog_logger.debug(
            "_entity_overlap_score called", has_query_entities=bool(query_entities)
        )

        if not query_entities:
            return 0.5  # Neutral score if no query entities

        # Get chunk entities
        chunk_entities = set()
        if hasattr(chunk, "entities"):
            chunk_entities = {e.lower() for e in chunk.entities}
        elif hasattr(chunk, "metadata") and "entity_refs" in chunk.metadata:
            chunk_entities = {e.lower() for e in chunk.metadata["entity_refs"]}

        if not chunk_entities:
            structlog_logger.debug("_entity_overlap_score - no chunk entities", score=0.0)
            return 0.0

        # Calculate overlap
        query_entities_lower = {e.lower() for e in query_entities}
        overlap = chunk_entities & query_entities_lower

        if not query_entities_lower:
            return 0.0

        # Jaccard similarity
        union = chunk_entities | query_entities_lower
        if union:
            score = len(overlap) / len(union)
            structlog_logger.debug(
                "_entity_overlap_score completed",
                score=score,
                overlap_count=len(overlap),
                union_count=len(union),
            )
            return score
        return 0.0

    def _temporal_relevance_score(self, chunk, temporal_context: datetime | None) -> float:
        """
        Calculate temporal relevance score.

        Args:
            chunk: Chunk result
            temporal_context: Temporal context

        Returns:
            Temporal score (0-1)
        """
        structlog_logger.debug(
            "_temporal_relevance_score called", has_temporal_context=bool(temporal_context)
        )

        if not temporal_context:
            return 0.5  # Neutral score if no temporal context

        # Check for temporal metadata
        chunk_time = None

        if hasattr(chunk, "metadata"):
            # Look for various temporal fields
            for field in ["created_at", "timestamp", "date", "published_at"]:
                if field in chunk.metadata:
                    try:
                        if isinstance(chunk.metadata[field], str):
                            chunk_time = datetime.fromisoformat(chunk.metadata[field])
                        elif isinstance(chunk.metadata[field], datetime):
                            chunk_time = chunk.metadata[field]
                    except (KeyError, ValueError, TypeError):
                        continue

        if not chunk_time:
            return 0.5  # Neutral if no temporal info

        # Calculate recency score (exponential decay)
        time_diff = abs((temporal_context - chunk_time).days)

        if time_diff == 0:
            score = 1.0
        elif time_diff < 7:
            score = 0.9
        elif time_diff < 30:
            score = 0.8
        elif time_diff < 90:
            score = 0.6
        elif time_diff < 365:
            score = 0.4
        else:
            score = 0.2

        if score > 0.5:
            self._stats["temporal_boosts"] += 1

        structlog_logger.debug(
            "_temporal_relevance_score completed",
            score=score,
            time_diff_days=time_diff,
            temporal_boost=score > 0.5,
        )
        return score

    def _authority_score(self, chunk) -> float:
        """
        Calculate source authority score.

        Args:
            chunk: Chunk result

        Returns:
            Authority score (0-1)
        """
        # Check document source
        source = None
        if hasattr(chunk, "document_source"):
            source = chunk.document_source
        elif hasattr(chunk, "metadata") and "source" in chunk.metadata:
            source = chunk.metadata["source"]

        if not source:
            structlog_logger.debug(
                "_authority_score - no source", score=self.AUTHORITY_SCORES["unknown"]
            )
            return self.AUTHORITY_SCORES["unknown"]

        source_lower = source.lower()

        # Check against known patterns
        if "official" in source_lower or "documentation" in source_lower:
            score = self.AUTHORITY_SCORES["official_docs"]
            source_type = "official_docs"
        elif "whitepaper" in source_lower:
            score = self.AUTHORITY_SCORES["whitepaper"]
            source_type = "whitepaper"
        elif "research" in source_lower or "paper" in source_lower:
            score = self.AUTHORITY_SCORES["research_paper"]
            source_type = "research_paper"
        elif "news" in source_lower or "article" in source_lower:
            score = self.AUTHORITY_SCORES["news_article"]
            source_type = "news_article"
        elif "blog" in source_lower:
            score = self.AUTHORITY_SCORES["blog_post"]
            source_type = "blog_post"
        elif "twitter" in source_lower or "social" in source_lower:
            score = self.AUTHORITY_SCORES["social_media"]
            source_type = "social_media"
        else:
            score = self.AUTHORITY_SCORES["unknown"]
            source_type = "unknown"

        structlog_logger.debug("_authority_score completed", score=score, source_type=source_type)
        return score

    def _diversity_score(self, chunk, seen_content: set[str]) -> float:
        """
        Calculate diversity score to avoid redundancy.

        Args:
            chunk: Chunk result
            seen_content: Set of seen content hashes

        Returns:
            Diversity score (0-1)
        """
        # Create content signature
        content = getattr(chunk, "content", "")
        if not content:
            structlog_logger.debug("_diversity_score - no content", score=1.0)
            return 1.0

        # Simple content hash (first 100 chars)
        content_sig = content[:100].lower()

        # Check similarity to seen content
        if content_sig in seen_content:
            structlog_logger.debug("_diversity_score - duplicate content", score=0.0)
            return 0.0  # Duplicate content

        # Check for partial overlap
        for seen in seen_content:
            # Simple overlap check
            overlap = len(set(content_sig.split()) & set(seen.split()))
            total = len(set(content_sig.split()) | set(seen.split()))

            if total > 0 and overlap / total > 0.7:
                structlog_logger.debug(
                    "_diversity_score - high overlap", score=0.3, overlap_ratio=overlap / total
                )
                return 0.3  # High overlap

        structlog_logger.debug("_diversity_score - novel content", score=1.0)
        return 1.0  # Novel content

    def _update_seen_content(self, chunk, seen_content: set[str]):
        """
        Update seen content set.

        Args:
            chunk: Chunk result
            seen_content: Set to update
        """
        content = getattr(chunk, "content", "")
        if content:
            # Add content signature
            seen_content.add(content[:100].lower())

    def _ensure_diversity(self, scored_chunks: list[dict], limit: int) -> list[dict]:
        """
        Ensure result diversity by penalizing similar content.

        Args:
            scored_chunks: Scored chunk list
            limit: Result limit

        Returns:
            Diverse chunk list
        """
        structlog_logger.debug(
            "_ensure_diversity called", num_chunks=len(scored_chunks), limit=limit
        )

        if len(scored_chunks) <= limit:
            return scored_chunks

        diverse_results = []
        seen_documents = defaultdict(int)
        seen_topics = defaultdict(int)
        initial_adjustments = self._stats["diversity_adjustments"]

        for item in scored_chunks:
            chunk = item["chunk"]

            # Check document diversity
            doc_id = getattr(chunk, "document_id", None)
            if doc_id:
                # Penalize if too many from same document
                if seen_documents[doc_id] >= 3:
                    item["final_score"] *= 0.5
                    self._stats["diversity_adjustments"] += 1
                seen_documents[doc_id] += 1

            # Check topic diversity (based on entities)
            if hasattr(chunk, "entities") and chunk.entities:
                main_entity = chunk.entities[0] if chunk.entities else None
                if main_entity:
                    if seen_topics[main_entity] >= 2:
                        item["final_score"] *= 0.7
                        self._stats["diversity_adjustments"] += 1
                    seen_topics[main_entity] += 1

            diverse_results.append(item)

        # Re-sort after diversity adjustments
        diverse_results.sort(key=lambda x: x["final_score"], reverse=True)

        adjustments_made = self._stats["diversity_adjustments"] - initial_adjustments
        structlog_logger.debug(
            "_ensure_diversity completed",
            adjustments_made=adjustments_made,
            unique_documents=len(seen_documents),
            unique_topics=len(seen_topics),
        )

        return diverse_results

    def rerank_with_feedback(
        self, chunks: list[Any], positive_examples: list[str], negative_examples: list[str]
    ) -> list[Any]:
        """
        Re-rank results based on user feedback.

        Args:
            chunks: Current results
            positive_examples: Positive feedback chunk IDs
            negative_examples: Negative feedback chunk IDs

        Returns:
            Re-ranked results
        """
        structlog_logger.info(
            "rerank_with_feedback called",
            num_chunks=len(chunks),
            num_positive=len(positive_examples),
            num_negative=len(negative_examples),
        )

        positive_count = 0
        negative_count = 0

        for chunk in chunks:
            chunk_id = str(getattr(chunk, "chunk_id", ""))

            # Boost positive examples
            if chunk_id in positive_examples and hasattr(chunk, "similarity"):
                chunk.similarity = min(1.0, chunk.similarity * 1.5)
                positive_count += 1

            # Penalize negative examples
            if chunk_id in negative_examples and hasattr(chunk, "similarity"):
                chunk.similarity = chunk.similarity * 0.5
                negative_count += 1

        # Re-rank with updated scores
        result = self.rank_chunks(chunks, len(chunks))

        structlog_logger.info(
            "rerank_with_feedback completed",
            positive_applied=positive_count,
            negative_applied=negative_count,
            result_count=len(result),
        )
        return result

    def get_stats(self) -> dict[str, Any]:
        """
        Get ranking statistics.

        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()

        if stats["rankings_performed"] > 0:
            stats["avg_chunks_per_ranking"] = (
                stats["total_chunks_ranked"] / stats["rankings_performed"]
            )
            stats["avg_diversity_adjustments"] = (
                stats["diversity_adjustments"] / stats["rankings_performed"]
            )

        stats["current_weights"] = self.weights

        return stats
