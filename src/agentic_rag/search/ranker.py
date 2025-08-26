"""
Result ranking and re-ranking algorithms.

Multi-factor ranking system for optimizing search result relevance.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


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
            return chunk.similarity
        if hasattr(chunk, "score"):
            return chunk.score
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
        if not query_entities:
            return 0.5  # Neutral score if no query entities

        # Get chunk entities
        chunk_entities = set()
        if hasattr(chunk, "entities"):
            chunk_entities = set(e.lower() for e in chunk.entities)
        elif hasattr(chunk, "metadata") and "entity_refs" in chunk.metadata:
            chunk_entities = set(e.lower() for e in chunk.metadata["entity_refs"])

        if not chunk_entities:
            return 0.0

        # Calculate overlap
        query_entities_lower = set(e.lower() for e in query_entities)
        overlap = chunk_entities & query_entities_lower

        if not query_entities_lower:
            return 0.0

        # Jaccard similarity
        union = chunk_entities | query_entities_lower
        if union:
            return len(overlap) / len(union)
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
            return self.AUTHORITY_SCORES["unknown"]

        source_lower = source.lower()

        # Check against known patterns
        if "official" in source_lower or "documentation" in source_lower:
            return self.AUTHORITY_SCORES["official_docs"]
        if "whitepaper" in source_lower:
            return self.AUTHORITY_SCORES["whitepaper"]
        if "research" in source_lower or "paper" in source_lower:
            return self.AUTHORITY_SCORES["research_paper"]
        if "news" in source_lower or "article" in source_lower:
            return self.AUTHORITY_SCORES["news_article"]
        if "blog" in source_lower:
            return self.AUTHORITY_SCORES["blog_post"]
        if "twitter" in source_lower or "social" in source_lower:
            return self.AUTHORITY_SCORES["social_media"]
        return self.AUTHORITY_SCORES["unknown"]

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
            return 1.0

        # Simple content hash (first 100 chars)
        content_sig = content[:100].lower()

        # Check similarity to seen content
        if content_sig in seen_content:
            return 0.0  # Duplicate content

        # Check for partial overlap
        for seen in seen_content:
            # Simple overlap check
            overlap = len(set(content_sig.split()) & set(seen.split()))
            total = len(set(content_sig.split()) | set(seen.split()))

            if total > 0 and overlap / total > 0.7:
                return 0.3  # High overlap

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
        if len(scored_chunks) <= limit:
            return scored_chunks

        diverse_results = []
        seen_documents = defaultdict(int)
        seen_topics = defaultdict(int)

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
        for chunk in chunks:
            chunk_id = str(getattr(chunk, "chunk_id", ""))

            # Boost positive examples
            if chunk_id in positive_examples:
                if hasattr(chunk, "similarity"):
                    chunk.similarity = min(1.0, chunk.similarity * 1.5)

            # Penalize negative examples
            if chunk_id in negative_examples:
                if hasattr(chunk, "similarity"):
                    chunk.similarity = chunk.similarity * 0.5

        # Re-rank with updated scores
        return self.rank_chunks(chunks, len(chunks))

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
