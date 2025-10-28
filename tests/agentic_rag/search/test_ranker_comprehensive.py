"""
Comprehensive tests for agentic_rag/search/ranker.py - Result ranking system.

Tests cover:
- RankedResults dataclass
- ResultRanker initialization and weight normalization
- Multi-factor ranking (similarity, entity overlap, temporal, authority, diversity)
- Chunk ranking with various scenarios
- Diversity enforcement
- Feedback-based re-ranking
- Statistics tracking
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.agentic_rag.search.ranker import RankedResults, ResultRanker

# ====================
# Mock Data Classes
# ====================


@dataclass
class MockChunk:
    """Mock chunk for testing."""

    chunk_id: str
    content: str
    similarity: float
    entities: list[str] = None
    document_id: str = None
    document_source: str = None
    metadata: dict = None

    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MockFact:
    """Mock fact for testing."""

    description: str
    confidence: float
    created_at: datetime = None

    def to_dict(self):
        return {
            "description": self.description,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class MockRelationship:
    """Mock relationship for testing."""

    source: str
    target: str
    confidence: float

    def to_dict(self):
        return {"source": self.source, "target": self.target, "confidence": self.confidence}


# ====================
# RankedResults Tests
# ====================


class TestRankedResults:
    """Test RankedResults dataclass."""

    def test_ranked_results_initialization(self):
        """Test RankedResults initializes with defaults."""
        results = RankedResults()

        assert results.chunks == []
        assert results.facts == []
        assert results.relationships == []
        assert results.ranking_metadata == {}

    def test_ranked_results_with_data(self):
        """Test RankedResults with data."""
        chunks = [MockChunk("1", "test content", 0.9)]
        facts = [MockFact("test fact", 0.8)]
        relationships = [MockRelationship("A", "B", 0.7)]
        metadata = {"test": "value"}

        results = RankedResults(
            chunks=chunks, facts=facts, relationships=relationships, ranking_metadata=metadata
        )

        assert len(results.chunks) == 1
        assert len(results.facts) == 1
        assert len(results.relationships) == 1
        assert results.ranking_metadata["test"] == "value"

    def test_ranked_results_to_dict(self):
        """Test RankedResults conversion to dictionary."""
        chunks = [MockChunk("1", "test", 0.9)]
        facts = [MockFact("fact", 0.8)]
        relationships = [MockRelationship("A", "B", 0.7)]

        results = RankedResults(chunks=chunks, facts=facts, relationships=relationships)
        result_dict = results.to_dict()

        assert "chunks" in result_dict
        assert "facts" in result_dict
        assert "relationships" in result_dict
        assert "ranking_metadata" in result_dict


# ====================
# ResultRanker Initialization Tests
# ====================


class TestResultRankerInitialization:
    """Test ResultRanker initialization."""

    def test_ranker_default_initialization(self):
        """Test ranker initializes with default weights."""
        ranker = ResultRanker()

        assert ranker.weights is not None
        assert "similarity" in ranker.weights
        assert "entity_overlap" in ranker.weights
        assert "temporal_relevance" in ranker.weights
        assert "source_authority" in ranker.weights
        assert "diversity" in ranker.weights

        # Check weights sum to 1.0
        total = sum(ranker.weights.values())
        assert abs(total - 1.0) < 0.001

    def test_ranker_custom_weights(self):
        """Test ranker with custom weights."""
        custom_weights = {
            "similarity": 0.5,
            "entity_overlap": 0.3,
            "temporal_relevance": 0.1,
            "source_authority": 0.05,
            "diversity": 0.05,
        }

        ranker = ResultRanker(weights=custom_weights)

        # Check weights are normalized to sum to 1.0
        total = sum(ranker.weights.values())
        assert abs(total - 1.0) < 0.001

    def test_weight_normalization(self):
        """Test weight normalization."""
        unnormalized = {
            "similarity": 2.0,
            "entity_overlap": 1.0,
            "temporal_relevance": 1.0,
            "source_authority": 0.5,
            "diversity": 0.5,
        }

        ranker = ResultRanker(weights=unnormalized)

        total = sum(ranker.weights.values())
        assert abs(total - 1.0) < 0.001

    def test_stats_initialization(self):
        """Test statistics tracking initialization."""
        ranker = ResultRanker()

        stats = ranker.get_stats()
        assert stats["rankings_performed"] == 0
        assert stats["total_chunks_ranked"] == 0
        assert stats["diversity_adjustments"] == 0
        assert stats["temporal_boosts"] == 0


# ====================
# Ranking Tests
# ====================


class TestResultRanking:
    """Test result ranking functionality."""

    def test_rank_empty_results(self):
        """Test ranking with empty results."""
        ranker = ResultRanker()

        results = {"chunks": [], "facts": [], "relationships": []}

        ranked = ranker.rank(results)

        assert len(ranked.chunks) == 0
        assert len(ranked.facts) == 0
        assert len(ranked.relationships) == 0

    def test_rank_chunks_only(self):
        """Test ranking with chunks only."""
        ranker = ResultRanker()

        chunks = [
            MockChunk("1", "high similarity content", 0.9),
            MockChunk("2", "medium similarity content", 0.5),
            MockChunk("3", "low similarity content", 0.3),
        ]

        results = {"chunks": chunks, "facts": [], "relationships": []}

        ranked = ranker.rank(results, limit=2)

        assert len(ranked.chunks) == 2
        # Higher similarity chunks should be ranked first
        assert ranked.chunks[0].similarity >= ranked.chunks[1].similarity

    def test_rank_with_facts(self):
        """Test ranking with facts."""
        ranker = ResultRanker()

        facts = [
            MockFact("high confidence", 0.9),
            MockFact("medium confidence", 0.5),
            MockFact("low confidence", 0.3),
        ]

        results = {"chunks": [], "facts": facts, "relationships": []}

        ranked = ranker.rank(results, limit=2)

        assert len(ranked.facts) == 2
        # Higher confidence facts should be ranked first
        assert ranked.facts[0].confidence >= ranked.facts[1].confidence

    def test_rank_with_relationships(self):
        """Test ranking with relationships."""
        ranker = ResultRanker()

        relationships = [
            MockRelationship("A", "B", 0.9),
            MockRelationship("C", "D", 0.5),
            MockRelationship("E", "F", 0.3),
        ]

        results = {"chunks": [], "facts": [], "relationships": relationships}

        ranked = ranker.rank(results, limit=2)

        assert len(ranked.relationships) == 2
        # Higher confidence relationships should be ranked first
        assert ranked.relationships[0].confidence >= ranked.relationships[1].confidence

    def test_rank_with_query_entities(self):
        """Test ranking with query entities for entity overlap."""
        ranker = ResultRanker()

        chunks = [
            MockChunk("1", "content", 0.8, entities=["Python", "FastAPI"]),
            MockChunk("2", "content", 0.8, entities=["Java", "Spring"]),
            MockChunk("3", "content", 0.8, entities=["Python", "Django"]),
        ]

        query_entities = ["Python", "FastAPI"]

        results = {"chunks": chunks, "facts": [], "relationships": []}

        ranked = ranker.rank(results, limit=3, query_entities=query_entities)

        # Chunk 1 should rank highest due to entity overlap
        assert ranked.chunks[0].chunk_id == "1"

    def test_rank_with_temporal_context(self):
        """Test ranking with temporal context."""
        ranker = ResultRanker()

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        last_month = now - timedelta(days=30)

        chunks = [
            MockChunk("1", "recent content", 0.7, metadata={"created_at": now.isoformat()}),
            MockChunk(
                "2", "yesterday content", 0.7, metadata={"created_at": yesterday.isoformat()}
            ),
            MockChunk("3", "old content", 0.7, metadata={"created_at": last_month.isoformat()}),
        ]

        results = {"chunks": chunks, "facts": [], "relationships": []}

        ranked = ranker.rank(results, limit=3, temporal_context=now)

        # More recent content should rank higher (all else being equal)
        # Chunk 1 (now) should rank first
        assert ranked.chunks[0].chunk_id == "1"


# ====================
# Factor Scoring Tests
# ====================


class TestFactorScoring:
    """Test individual ranking factor scoring."""

    def test_similarity_score(self):
        """Test similarity scoring."""
        ranker = ResultRanker()

        chunk_high = MockChunk("1", "test", 0.9)
        chunk_low = MockChunk("2", "test", 0.3)
        chunk_no_sim = Mock(content="test")

        assert ranker._similarity_score(chunk_high) == 0.9
        assert ranker._similarity_score(chunk_low) == 0.3
        assert ranker._similarity_score(chunk_no_sim) == 0.5  # Default

    def test_entity_overlap_score_no_query_entities(self):
        """Test entity overlap scoring with no query entities."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "test", 0.8, entities=["Python"])

        score = ranker._entity_overlap_score(chunk, None)
        assert score == 0.5  # Neutral score

    def test_entity_overlap_score_with_match(self):
        """Test entity overlap scoring with matching entities."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "test", 0.8, entities=["Python", "FastAPI"])
        query_entities = ["Python", "FastAPI"]

        score = ranker._entity_overlap_score(chunk, query_entities)
        assert score > 0.5  # Should have high overlap

    def test_entity_overlap_score_no_match(self):
        """Test entity overlap scoring with no matching entities."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "test", 0.8, entities=["Java", "Spring"])
        query_entities = ["Python", "FastAPI"]

        score = ranker._entity_overlap_score(chunk, query_entities)
        assert score < 0.5  # Low overlap

    def test_temporal_relevance_score_no_context(self):
        """Test temporal relevance scoring with no context."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "test", 0.8)

        score = ranker._temporal_relevance_score(chunk, None)
        assert score == 0.5  # Neutral score

    def test_temporal_relevance_score_recent(self):
        """Test temporal relevance scoring for recent content."""
        ranker = ResultRanker()

        now = datetime.utcnow()
        chunk = MockChunk("1", "test", 0.8, metadata={"created_at": now.isoformat()})

        score = ranker._temporal_relevance_score(chunk, now)
        assert score == 1.0  # Same day

    def test_temporal_relevance_score_old(self):
        """Test temporal relevance scoring for old content."""
        ranker = ResultRanker()

        now = datetime.utcnow()
        old_date = now - timedelta(days=500)
        chunk = MockChunk("1", "test", 0.8, metadata={"created_at": old_date.isoformat()})

        score = ranker._temporal_relevance_score(chunk, now)
        assert score < 0.5  # Old content

    def test_authority_score_official_docs(self):
        """Test authority scoring for official docs."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "test", 0.8, document_source="official_documentation")

        score = ranker._authority_score(chunk)
        assert score == ResultRanker.AUTHORITY_SCORES["official_docs"]

    def test_authority_score_whitepaper(self):
        """Test authority scoring for whitepaper."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "test", 0.8, document_source="company_whitepaper")

        score = ranker._authority_score(chunk)
        assert score == ResultRanker.AUTHORITY_SCORES["whitepaper"]

    def test_authority_score_blog(self):
        """Test authority scoring for blog post."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "test", 0.8, document_source="blog_post")

        score = ranker._authority_score(chunk)
        assert score == ResultRanker.AUTHORITY_SCORES["blog_post"]

    def test_authority_score_unknown(self):
        """Test authority scoring for unknown source."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "test", 0.8, document_source="random_website")

        score = ranker._authority_score(chunk)
        assert score == ResultRanker.AUTHORITY_SCORES["unknown"]

    def test_diversity_score_novel_content(self):
        """Test diversity scoring for novel content."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "unique content that hasn't been seen", 0.8)
        seen_content = set()

        score = ranker._diversity_score(chunk, seen_content)
        assert score == 1.0

    def test_diversity_score_duplicate_content(self):
        """Test diversity scoring for duplicate content."""
        ranker = ResultRanker()

        content = "duplicate content"
        chunk = MockChunk("1", content, 0.8)
        seen_content = {content[:100].lower()}

        score = ranker._diversity_score(chunk, seen_content)
        assert score == 0.0


# ====================
# Chunk Ranking Tests
# ====================


class TestChunkRanking:
    """Test chunk-specific ranking."""

    def test_rank_chunks_empty(self):
        """Test ranking empty chunk list."""
        ranker = ResultRanker()

        ranked = ranker.rank_chunks([])
        assert ranked == []

    def test_rank_chunks_basic(self):
        """Test basic chunk ranking."""
        ranker = ResultRanker()

        chunks = [
            MockChunk("1", "content", 0.9),
            MockChunk("2", "content", 0.5),
            MockChunk("3", "content", 0.7),
        ]

        ranked = ranker.rank_chunks(chunks, limit=2)

        assert len(ranked) == 2
        # Should be ordered by score
        assert ranked[0].similarity >= ranked[1].similarity

    def test_rank_chunks_metadata_attached(self):
        """Test that ranking metadata is attached to chunks."""
        ranker = ResultRanker()

        chunks = [MockChunk("1", "content", 0.9)]

        ranked = ranker.rank_chunks(chunks, limit=1)

        assert "rank" in ranked[0].metadata
        assert "ranking_score" in ranked[0].metadata
        assert ranked[0].metadata["rank"] == 1


# ====================
# Diversity Enforcement Tests
# ====================


class TestDiversityEnforcement:
    """Test diversity enforcement in ranking."""

    def test_diversity_same_document_penalty(self):
        """Test penalty for multiple chunks from same document."""
        ranker = ResultRanker()

        chunks = [
            MockChunk("1", "content 1", 0.9, document_id="doc1"),
            MockChunk("2", "content 2", 0.9, document_id="doc1"),
            MockChunk("3", "content 3", 0.9, document_id="doc1"),
            MockChunk("4", "content 4", 0.9, document_id="doc1"),
            MockChunk("5", "content 5", 0.9, document_id="doc2"),
        ]

        scored = [{"chunk": c, "final_score": c.similarity, "factor_scores": {}} for c in chunks]

        diverse = ranker._ensure_diversity(scored, limit=5)

        # Should penalize chunks 4+ from doc1
        # Chunk from doc2 should be ranked higher
        doc_ids_in_top_3 = [diverse[i]["chunk"].document_id for i in range(3)]
        assert "doc2" in doc_ids_in_top_3

    def test_diversity_update_seen_content(self):
        """Test updating seen content."""
        ranker = ResultRanker()

        chunk = MockChunk("1", "test content for tracking", 0.9)
        seen_content = set()

        ranker._update_seen_content(chunk, seen_content)

        assert len(seen_content) == 1
        assert "test content for tracking"[:100].lower() in seen_content


# ====================
# Feedback Re-ranking Tests
# ====================


class TestFeedbackReranking:
    """Test feedback-based re-ranking."""

    def test_rerank_with_positive_feedback(self):
        """Test re-ranking with positive feedback."""
        ranker = ResultRanker()

        chunks = [
            MockChunk("1", "content", 0.5),
            MockChunk("2", "content", 0.7),
        ]

        positive = ["1"]
        negative = []

        reranked = ranker.rerank_with_feedback(chunks, positive, negative)

        # Chunk 1 should be boosted and rank higher
        assert reranked[0].chunk_id == "1"

    def test_rerank_with_negative_feedback(self):
        """Test re-ranking with negative feedback."""
        ranker = ResultRanker()

        chunks = [
            MockChunk("1", "content", 0.9),
            MockChunk("2", "content", 0.5),
        ]

        positive = []
        negative = ["1"]

        reranked = ranker.rerank_with_feedback(chunks, positive, negative)

        # Chunk 1 should be penalized and rank lower
        assert reranked[0].chunk_id == "2"

    def test_rerank_with_mixed_feedback(self):
        """Test re-ranking with both positive and negative feedback."""
        ranker = ResultRanker()

        chunks = [
            MockChunk("1", "content", 0.7),
            MockChunk("2", "content", 0.6),
            MockChunk("3", "content", 0.8),
        ]

        positive = ["2"]
        negative = ["3"]

        reranked = ranker.rerank_with_feedback(chunks, positive, negative)

        # Chunk 2 should be boosted to top, chunk 3 penalized
        assert reranked[0].chunk_id == "2"


# ====================
# Statistics Tests
# ====================


class TestStatistics:
    """Test statistics tracking."""

    def test_stats_initial_state(self):
        """Test initial statistics state."""
        ranker = ResultRanker()

        stats = ranker.get_stats()

        assert stats["rankings_performed"] == 0
        assert stats["total_chunks_ranked"] == 0

    def test_stats_after_ranking(self):
        """Test statistics after performing rankings."""
        ranker = ResultRanker()

        chunks = [MockChunk("1", "test", 0.8), MockChunk("2", "test", 0.7)]

        results = {"chunks": chunks, "facts": [], "relationships": []}

        ranker.rank(results)

        stats = ranker.get_stats()

        assert stats["rankings_performed"] == 1
        assert stats["total_chunks_ranked"] == 2

    def test_stats_averages(self):
        """Test statistics averages calculation."""
        ranker = ResultRanker()

        # Perform multiple rankings
        for _ in range(3):
            chunks = [MockChunk(str(i), "test", 0.8) for i in range(5)]
            results = {"chunks": chunks, "facts": [], "relationships": []}
            ranker.rank(results)

        stats = ranker.get_stats()

        assert stats["rankings_performed"] == 3
        assert stats["total_chunks_ranked"] == 15
        assert stats["avg_chunks_per_ranking"] == 5.0

    def test_stats_includes_weights(self):
        """Test that statistics include current weights."""
        custom_weights = {"similarity": 0.8, "entity_overlap": 0.2}
        ranker = ResultRanker(weights=custom_weights)

        stats = ranker.get_stats()

        assert "current_weights" in stats
        assert "similarity" in stats["current_weights"]


# ====================
# Integration Tests
# ====================


class TestRankingIntegration:
    """Integration tests for full ranking workflow."""

    def test_full_ranking_workflow(self):
        """Test complete ranking workflow with all features."""
        ranker = ResultRanker()

        now = datetime.utcnow()

        chunks = [
            MockChunk(
                "1",
                "Python web framework",
                0.8,
                entities=["Python", "Web"],
                document_id="doc1",
                document_source="official_documentation",
                metadata={"created_at": now.isoformat()},
            ),
            MockChunk(
                "2",
                "Java enterprise framework",
                0.7,
                entities=["Java", "Enterprise"],
                document_id="doc2",
                document_source="blog_post",
                metadata={"created_at": (now - timedelta(days=30)).isoformat()},
            ),
        ]

        facts = [MockFact("Python is popular", 0.9)]
        relationships = [MockRelationship("Python", "FastAPI", 0.8)]

        results = {"chunks": chunks, "facts": facts, "relationships": relationships}

        ranked = ranker.rank(
            results, limit=2, query_entities=["Python", "Web"], temporal_context=now
        )

        # Verify all components are ranked
        assert len(ranked.chunks) > 0
        assert len(ranked.facts) > 0
        assert len(ranked.relationships) > 0

        # Verify metadata is present
        assert "weights_used" in ranked.ranking_metadata

    def test_ranking_with_large_result_set(self):
        """Test ranking with large number of results."""
        ranker = ResultRanker()

        # Create 100 chunks
        chunks = [MockChunk(str(i), f"content {i}", 0.5 + (i % 5) / 10) for i in range(100)]

        results = {"chunks": chunks, "facts": [], "relationships": []}

        ranked = ranker.rank(results, limit=10)

        # Should return exactly 10 chunks
        assert len(ranked.chunks) == 10

        # Should be sorted by score
        for i in range(len(ranked.chunks) - 1):
            assert ranked.chunks[i].similarity >= ranked.chunks[i + 1].similarity
