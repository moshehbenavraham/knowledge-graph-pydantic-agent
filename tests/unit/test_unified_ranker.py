"""
Unit tests for UnifiedRanker.

Tests the unified ranking function that combines multiple ranking signals.
"""

import pytest

from src.agentic_rag.search.result_merger import ResultType, SearchResultItem
from src.agentic_rag.search.unified_ranker import (
    RankingSignals,
    RankingWeights,
    UnifiedRanker,
)


@pytest.fixture
def ranker() -> UnifiedRanker:
    """Create UnifiedRanker instance."""
    return UnifiedRanker()


@pytest.fixture
def custom_weights_ranker() -> UnifiedRanker:
    """Create UnifiedRanker with custom weights."""
    weights = RankingWeights(
        relevance=2.0,
        relationship=1.0,
        temporal=1.5,
        entity_match=0.0,
        source_authority=0.0,
    )
    return UnifiedRanker(weights=weights)


class TestRankingSignals:
    """Tests for RankingSignals dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        signals = RankingSignals()
        assert signals.relevance_score == 0.0
        assert signals.relationship_strength is None
        assert signals.temporal_recency is None
        assert signals.entity_match_score is None
        assert signals.source_authority is None

    def test_with_values(self) -> None:
        """Test creation with values."""
        signals = RankingSignals(
            relevance_score=0.9,
            relationship_strength=0.8,
            temporal_recency=0.7,
        )
        assert signals.relevance_score == 0.9
        assert signals.relationship_strength == 0.8
        assert signals.temporal_recency == 0.7

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        signals = RankingSignals(
            relevance_score=0.9,
            relationship_strength=0.8,
        )
        result = signals.to_dict()
        assert result["relevance_score"] == 0.9
        assert result["relationship_strength"] == 0.8
        assert result["temporal_recency"] is None

    def test_from_search_result_item(self) -> None:
        """Test creation from SearchResultItem."""
        item = SearchResultItem(
            result_type=ResultType.GRAPH_PATH,
            title="Test",
            content="Content",
            relevance_score=0.85,
            relationship_strength=0.75,
            temporal_recency=0.6,
        )
        signals = RankingSignals.from_search_result_item(item)
        assert signals.relevance_score == 0.85
        assert signals.relationship_strength == 0.75
        assert signals.temporal_recency == 0.6


class TestRankingWeights:
    """Tests for RankingWeights dataclass."""

    def test_default_weights(self) -> None:
        """Test default weight values."""
        weights = RankingWeights()
        assert weights.relevance == 1.0
        assert weights.relationship == 0.8
        assert weights.temporal == 0.6
        assert weights.entity_match == 0.5
        assert weights.source_authority == 0.3

    def test_custom_weights(self) -> None:
        """Test custom weight values."""
        weights = RankingWeights(
            relevance=2.0,
            relationship=1.5,
            temporal=1.0,
        )
        assert weights.relevance == 2.0
        assert weights.relationship == 1.5
        assert weights.temporal == 1.0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        weights = RankingWeights()
        result = weights.to_dict()
        assert "relevance" in result
        assert "relationship" in result
        assert "temporal" in result


class TestUnifiedRanker:
    """Tests for UnifiedRanker class."""

    def test_initialization_default_weights(self, ranker: UnifiedRanker) -> None:
        """Test initialization with default weights."""
        assert ranker.weights is not None
        assert ranker.weights.relevance == 1.0

    def test_initialization_custom_weights(self, custom_weights_ranker: UnifiedRanker) -> None:
        """Test initialization with custom weights."""
        assert custom_weights_ranker.weights.relevance == 2.0
        assert custom_weights_ranker.weights.relationship == 1.0

    def test_rank_empty_list(self, ranker: UnifiedRanker) -> None:
        """Test ranking empty list."""
        result = ranker.rank([])
        assert result == []

    def test_rank_single_item(self, ranker: UnifiedRanker) -> None:
        """Test ranking single item."""
        item = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Test",
            content="Content",
            relevance_score=0.9,
        )
        result = ranker.rank([item])
        assert len(result) == 1
        assert result[0] == item
        assert "final_score" in result[0].metadata

    def test_rank_multiple_items(self, ranker: UnifiedRanker) -> None:
        """Test ranking multiple items."""
        item1 = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="High Score",
            content="Content",
            relevance_score=0.95,
        )
        item2 = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Low Score",
            content="Content",
            relevance_score=0.5,
        )
        item3 = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Medium Score",
            content="Content",
            relevance_score=0.75,
        )

        result = ranker.rank([item2, item3, item1])  # Pass in random order
        assert result[0].title == "High Score"
        assert result[1].title == "Medium Score"
        assert result[2].title == "Low Score"

    def test_rank_with_limit(self, ranker: UnifiedRanker) -> None:
        """Test ranking with limit."""
        items = [
            SearchResultItem(
                result_type=ResultType.VECTOR_CHUNK,
                title=f"Item {i}",
                content="Content",
                relevance_score=i / 10,
            )
            for i in range(10)
        ]
        result = ranker.rank(items, limit=3)
        assert len(result) == 3
        assert result[0].relevance_score >= result[1].relevance_score

    def test_calculate_score_relevance_only(self, ranker: UnifiedRanker) -> None:
        """Test score calculation with only relevance."""
        item = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Test",
            content="Content",
            relevance_score=0.8,
        )
        score = ranker.calculate_score(item)
        assert score == 0.8

    def test_calculate_score_with_relationship(self, ranker: UnifiedRanker) -> None:
        """Test score calculation with relationship strength."""
        item = SearchResultItem(
            result_type=ResultType.GRAPH_PATH,
            title="Test",
            content="Content",
            relevance_score=0.8,
            relationship_strength=0.6,
        )
        score = ranker.calculate_score(item)
        # Weighted average: (0.8*1.0 + 0.6*0.8) / (1.0 + 0.8)
        expected = (0.8 * 1.0 + 0.6 * 0.8) / 1.8
        assert abs(score - expected) < 0.01

    def test_calculate_score_with_temporal(self, ranker: UnifiedRanker) -> None:
        """Test score calculation with temporal recency."""
        item = SearchResultItem(
            result_type=ResultType.TEMPORAL_TREND,
            title="Test",
            content="Content",
            relevance_score=0.8,
            temporal_recency=0.9,
        )
        score = ranker.calculate_score(item)
        # Weighted average: (0.8*1.0 + 0.9*0.6) / (1.0 + 0.6)
        expected = (0.8 * 1.0 + 0.9 * 0.6) / 1.6
        assert abs(score - expected) < 0.01

    def test_calculate_score_all_signals(self, ranker: UnifiedRanker) -> None:
        """Test score calculation with all signals."""
        item = SearchResultItem(
            result_type=ResultType.GRAPH_PATH,
            title="Test",
            content="Content",
            relevance_score=0.9,
            relationship_strength=0.8,
            temporal_recency=0.7,
        )
        score = ranker.calculate_score(item)
        # All signals contribute
        assert score > 0
        assert score <= 1.0

    def test_calculate_score_from_signals(self, ranker: UnifiedRanker) -> None:
        """Test score calculation from RankingSignals."""
        signals = RankingSignals(
            relevance_score=0.9,
            relationship_strength=0.8,
            temporal_recency=0.7,
        )
        score = ranker.calculate_score_from_signals(signals)
        assert score > 0
        assert score <= 1.0

    def test_rerank_with_boost(self, ranker: UnifiedRanker) -> None:
        """Test reranking with entity boost."""
        item1 = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Item 1",
            content="Content",
            relevance_score=0.7,
            entities=["Intel"],
        )
        item2 = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Item 2",
            content="Content",
            relevance_score=0.8,
            entities=["AMD"],
        )

        # Without boost, item2 should be first
        result_no_boost = ranker.rank([item1, item2])
        assert result_no_boost[0].title == "Item 2"

        # With boost for Intel, item1 should be boosted
        result_boosted = ranker.rerank_with_boost(
            [item1, item2], boost_entities=["Intel"], boost_factor=1.3
        )
        assert result_boosted[0].title == "Item 1"

    def test_rerank_with_boost_capped_at_1(self, ranker: UnifiedRanker) -> None:
        """Test that boosted scores are capped at 1.0."""
        item = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Test",
            content="Content",
            relevance_score=0.95,
            entities=["Intel"],
        )
        result = ranker.rerank_with_boost([item], boost_entities=["Intel"], boost_factor=1.5)
        assert result[0].metadata["final_score"] <= 1.0

    def test_stats_tracking(self, ranker: UnifiedRanker) -> None:
        """Test statistics tracking."""
        items = [
            SearchResultItem(
                result_type=ResultType.VECTOR_CHUNK,
                title="Test",
                content="Content",
                relevance_score=0.8,
            )
        ]
        ranker.rank(items)
        stats = ranker.get_stats()
        assert stats["rankings"] == 1
        assert stats["items_ranked"] == 1
        assert stats["avg_score"] > 0

    def test_custom_weights_affect_ranking(self, custom_weights_ranker: UnifiedRanker) -> None:
        """Test that custom weights affect ranking order."""
        # Item with high relevance, low relationship
        item1 = SearchResultItem(
            result_type=ResultType.GRAPH_PATH,
            title="High Relevance",
            content="Content",
            relevance_score=0.9,
            relationship_strength=0.3,
        )
        # Item with medium relevance, high relationship
        item2 = SearchResultItem(
            result_type=ResultType.GRAPH_PATH,
            title="High Relationship",
            content="Content",
            relevance_score=0.5,
            relationship_strength=0.9,
        )

        # With custom weights (relevance=2.0, relationship=1.0),
        # item1 should rank higher because relevance is weighted more
        result = custom_weights_ranker.rank([item1, item2])
        assert result[0].title == "High Relevance"
