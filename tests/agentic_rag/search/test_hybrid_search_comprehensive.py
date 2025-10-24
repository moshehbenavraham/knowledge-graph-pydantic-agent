"""
Comprehensive tests for HybridSearch - intelligent vector + graph search orchestration.

Covers:
- Initialization and configuration
- Strategy selection logic
- Vector-only search
- Graph-only search
- Hybrid search (parallel vector + graph)
- Adaptive search
- Graph context boosting
- Similar content search
- Analytics logging
- Statistics tracking
- Intent-based routing
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from src.agentic_rag.search.hybrid_search import (
    HybridSearch,
    HybridSearchResult,
)
from src.agentic_rag.search.intent_analyzer import SearchIntent
from src.agentic_rag.search.vector_search import ChunkResult
from src.agentic_rag.search.graph_search import GraphSearchResult
from src.config import SearchStrategy


# ===== Fixtures =====


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager."""
    cm = Mock()
    return cm


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = Mock()
    config.performance.enable_graph = True
    config.performance.enable_parallel_search = True
    return config


@pytest.fixture
def hybrid_search(mock_connection_manager, mock_config):
    """Create HybridSearch instance with mocks."""
    with patch("src.agentic_rag.search.hybrid_search.get_config", return_value=mock_config):
        hs = HybridSearch(mock_connection_manager)
        return hs


@pytest.fixture
def sample_chunks():
    """Sample chunk results."""
    return [
        ChunkResult(
            chunk_id=uuid4(),
            content="OpenAI released GPT-4",
            similarity=0.9,
            metadata={"source": "doc1"},
            entities=["OpenAI", "GPT-4"],
        ),
        ChunkResult(
            chunk_id=uuid4(),
            content="GPT-4 is a large language model",
            similarity=0.8,
            metadata={"source": "doc2"},
            entities=["GPT-4"],
        ),
    ]


@pytest.fixture
def sample_graph_results():
    """Sample graph search results."""
    return GraphSearchResult(
        entities=[Mock(name="OpenAI"), Mock(name="GPT-4")],
        relationships=[Mock(type="CREATED")],
        facts=[Mock(content="OpenAI created GPT-4")],
        chunk_refs=["chunk_1", "chunk_2"],
    )


# ===== Initialization Tests =====


class TestHybridSearchInit:
    """Test HybridSearch initialization."""

    def test_init_requires_connection_manager(self):
        """Test that initialization requires connection manager."""
        with pytest.raises(ValueError, match="HybridSearch requires an initialized ConnectionManager"):
            HybridSearch(None)

    def test_init_with_connection_manager(self, mock_connection_manager, mock_config):
        """Test successful initialization."""
        with patch("src.agentic_rag.search.hybrid_search.get_config", return_value=mock_config):
            hs = HybridSearch(mock_connection_manager)

            assert hs.connection_manager == mock_connection_manager
            assert hs.vector_search is not None
            assert hs.graph_search is not None
            assert hs.intent_analyzer is not None
            assert hs.ranker is not None

    def test_init_creates_stats(self, hybrid_search):
        """Test that initialization creates stats tracking."""
        assert hybrid_search._stats["searches"] == 0
        assert "strategies" in hybrid_search._stats
        assert hybrid_search._stats["graph_boosts"] == 0


# ===== Strategy Selection Tests =====


class TestStrategySelection:
    """Test search strategy selection logic."""

    def test_select_strategy_vector_heavy(self, hybrid_search):
        """Test VECTOR_HEAVY intent maps to VECTOR_ONLY strategy."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.VECTOR_HEAVY

        strategy = hybrid_search._select_strategy(intent_result)

        assert strategy == SearchStrategy.VECTOR_ONLY

    def test_select_strategy_graph_heavy_with_graph_enabled(self, hybrid_search):
        """Test GRAPH_HEAVY intent maps to GRAPH_ONLY when graph is enabled."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.GRAPH_HEAVY
        hybrid_search.config.performance.enable_graph = True

        strategy = hybrid_search._select_strategy(intent_result)

        assert strategy == SearchStrategy.GRAPH_ONLY

    def test_select_strategy_graph_heavy_with_graph_disabled(self, hybrid_search):
        """Test GRAPH_HEAVY falls back to VECTOR_ONLY when graph is disabled."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.GRAPH_HEAVY
        hybrid_search.config.performance.enable_graph = False

        strategy = hybrid_search._select_strategy(intent_result)

        assert strategy == SearchStrategy.VECTOR_ONLY

    def test_select_strategy_temporal(self, hybrid_search):
        """Test TEMPORAL intent maps to HYBRID strategy."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.TEMPORAL
        hybrid_search.config.performance.enable_graph = True

        strategy = hybrid_search._select_strategy(intent_result)

        assert strategy == SearchStrategy.HYBRID

    def test_select_strategy_entity_focused(self, hybrid_search):
        """Test ENTITY_FOCUSED intent maps to HYBRID strategy."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.ENTITY_FOCUSED
        hybrid_search.config.performance.enable_graph = True

        strategy = hybrid_search._select_strategy(intent_result)

        assert strategy == SearchStrategy.HYBRID

    def test_select_strategy_default_adaptive(self, hybrid_search):
        """Test default strategy is ADAPTIVE when graph is enabled."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.HYBRID
        hybrid_search.config.performance.enable_graph = True

        strategy = hybrid_search._select_strategy(intent_result)

        assert strategy == SearchStrategy.ADAPTIVE


# ===== Vector-Only Search Tests =====


@pytest.mark.asyncio
class TestVectorOnlySearch:
    """Test vector-only search strategy."""

    async def test_vector_only_search(self, hybrid_search, sample_chunks):
        """Test vector-only search execution."""
        hybrid_search.vector_search.search = AsyncMock(return_value=sample_chunks)

        result = await hybrid_search._vector_only_search("test query", limit=10)

        assert len(result.chunks) == 2
        assert result.metadata["search_type"] == "vector_only"
        hybrid_search.vector_search.search.assert_called_once_with("test query", 10)

    async def test_vector_only_empty_results(self, hybrid_search):
        """Test vector-only search with no results."""
        hybrid_search.vector_search.search = AsyncMock(return_value=[])

        result = await hybrid_search._vector_only_search("test query", limit=10)

        assert len(result.chunks) == 0


# ===== Graph-Only Search Tests =====


@pytest.mark.asyncio
class TestGraphOnlySearch:
    """Test graph-only search strategy."""

    async def test_graph_only_search(self, hybrid_search, sample_graph_results):
        """Test graph-only search execution."""
        intent_result = Mock()
        hybrid_search.graph_search.search = AsyncMock(return_value=sample_graph_results)
        hybrid_search.vector_search.get_chunks_by_ids = AsyncMock(return_value=[])

        result = await hybrid_search._graph_only_search("test query", limit=10, intent_result=intent_result)

        assert len(result.entities) == 2
        assert len(result.facts) == 1
        assert result.metadata["search_type"] == "graph_only"

    async def test_graph_only_fetches_chunk_content(self, hybrid_search, sample_graph_results, sample_chunks):
        """Test that graph-only search fetches chunk content."""
        intent_result = Mock()
        sample_graph_results.chunk_refs = [str(uuid4()), str(uuid4())]

        hybrid_search.graph_search.search = AsyncMock(return_value=sample_graph_results)
        hybrid_search.vector_search.get_chunks_by_ids = AsyncMock(return_value=sample_chunks)

        result = await hybrid_search._graph_only_search("test query", limit=10, intent_result=intent_result)

        assert len(result.chunks) == 2
        hybrid_search.vector_search.get_chunks_by_ids.assert_called_once()

    async def test_graph_only_handles_invalid_chunk_refs(self, hybrid_search, sample_graph_results):
        """Test graph-only search with invalid chunk refs."""
        intent_result = Mock()
        sample_graph_results.chunk_refs = ["invalid-uuid", "also-invalid"]

        hybrid_search.graph_search.search = AsyncMock(return_value=sample_graph_results)
        hybrid_search.vector_search.get_chunks_by_ids = AsyncMock(return_value=[])

        result = await hybrid_search._graph_only_search("test query", limit=10, intent_result=intent_result)

        # Should not crash, just skip invalid UUIDs
        assert len(result.chunks) == 0


# ===== Hybrid Search Tests =====


@pytest.mark.asyncio
class TestHybridSearch:
    """Test hybrid (combined) search strategy."""

    async def test_hybrid_search_parallel(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test hybrid search with parallel execution."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.HYBRID
        intent_result.entities_mentioned = []

        hybrid_search.config.performance.enable_parallel_search = True
        hybrid_search.vector_search.search = AsyncMock(return_value=sample_chunks)
        hybrid_search.graph_search.search = AsyncMock(return_value=sample_graph_results)
        hybrid_search.ranker.rank_chunks = Mock(side_effect=lambda chunks, limit: chunks[:limit])

        result = await hybrid_search._hybrid_search("test query", limit=10, intent_result=intent_result)

        assert result.metadata["search_type"] == "hybrid"
        assert len(result.chunks) > 0
        assert len(result.facts) > 0

    async def test_hybrid_search_sequential(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test hybrid search with sequential execution."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.HYBRID
        intent_result.entities_mentioned = []

        hybrid_search.config.performance.enable_parallel_search = False
        hybrid_search.vector_search.search = AsyncMock(return_value=sample_chunks)
        hybrid_search.graph_search.search = AsyncMock(return_value=sample_graph_results)
        hybrid_search.ranker.rank_chunks = Mock(side_effect=lambda chunks, limit: chunks[:limit])

        result = await hybrid_search._hybrid_search("test query", limit=10, intent_result=intent_result)

        assert result.metadata["search_type"] == "hybrid"

    async def test_hybrid_search_applies_boosts(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test that hybrid search applies graph context boosts."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.HYBRID
        intent_result.entities_mentioned = []

        hybrid_search.vector_search.search = AsyncMock(return_value=sample_chunks)
        hybrid_search.graph_search.search = AsyncMock(return_value=sample_graph_results)
        hybrid_search.ranker.rank_chunks = Mock(side_effect=lambda chunks, limit: chunks[:limit])

        with patch.object(hybrid_search, "_boost_with_graph_context", new=AsyncMock(return_value=sample_chunks)):
            result = await hybrid_search._hybrid_search("test query", limit=10, intent_result=intent_result)

            hybrid_search._boost_with_graph_context.assert_called_once()


# ===== Adaptive Search Tests =====


@pytest.mark.asyncio
class TestAdaptiveSearch:
    """Test adaptive search strategy."""

    async def test_adaptive_search_stays_vector_only(self, hybrid_search, sample_chunks):
        """Test adaptive search stays vector-only when results are good."""
        intent_result = Mock()
        intent_result.entities_mentioned = []

        # High similarity scores
        good_chunks = [
            ChunkResult(chunk_id=uuid4(), content="test", similarity=0.9, metadata={}, entities=[]),
            ChunkResult(chunk_id=uuid4(), content="test", similarity=0.85, metadata={}, entities=[]),
        ]

        hybrid_search.vector_search.search = AsyncMock(side_effect=[good_chunks, sample_chunks])

        result = await hybrid_search._adaptive_search("test query", limit=10, intent_result=intent_result)

        assert result.metadata["search_type"] == "adaptive_vector"

    async def test_adaptive_search_triggers_hybrid(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test adaptive search triggers hybrid when similarity is low."""
        intent_result = Mock()
        intent_result.entities_mentioned = []

        # Low similarity scores
        poor_chunks = [
            ChunkResult(chunk_id=uuid4(), content="test", similarity=0.5, metadata={}, entities=[]),
        ]

        hybrid_search.vector_search.search = AsyncMock(return_value=poor_chunks)
        hybrid_search.graph_search.search = AsyncMock(return_value=sample_graph_results)
        hybrid_search.ranker.rank_chunks = Mock(side_effect=lambda chunks, limit: chunks[:limit])

        with patch.object(hybrid_search, "_hybrid_search", new=AsyncMock(return_value=HybridSearchResult(metadata={"search_type": "hybrid"}))):
            result = await hybrid_search._adaptive_search("test query", limit=10, intent_result=intent_result)

            hybrid_search._hybrid_search.assert_called_once()

    async def test_adaptive_search_triggers_hybrid_with_multiple_entities(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test adaptive search triggers hybrid when multiple entities are mentioned."""
        intent_result = Mock()
        intent_result.entities_mentioned = ["OpenAI", "GPT-4", "Microsoft"]

        good_chunks = [
            ChunkResult(chunk_id=uuid4(), content="test", similarity=0.9, metadata={}, entities=[]),
        ]

        hybrid_search.vector_search.search = AsyncMock(return_value=good_chunks)
        hybrid_search.graph_search.search = AsyncMock(return_value=sample_graph_results)
        hybrid_search.ranker.rank_chunks = Mock(side_effect=lambda chunks, limit: chunks[:limit])

        with patch.object(hybrid_search, "_hybrid_search", new=AsyncMock(return_value=HybridSearchResult(metadata={"search_type": "hybrid"}))):
            result = await hybrid_search._adaptive_search("test query", limit=10, intent_result=intent_result)

            # Should trigger hybrid due to multiple entities
            hybrid_search._hybrid_search.assert_called_once()


# ===== Graph Context Boosting Tests =====


@pytest.mark.asyncio
class TestGraphContextBoosting:
    """Test graph context boosting logic."""

    async def test_boost_with_chunk_refs(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test boosting chunks referenced in graph results."""
        intent_result = None

        # Set chunk ID to match graph ref
        sample_chunks[0].chunk_id = UUID("00000000-0000-0000-0000-000000000001")
        sample_graph_results.chunk_refs = ["00000000-0000-0000-0000-000000000001"]

        original_similarity = sample_chunks[0].similarity

        result = await hybrid_search._boost_with_graph_context(
            sample_chunks, sample_graph_results, intent_result
        )

        # Should be boosted
        assert result[0].similarity > original_similarity
        assert hybrid_search._stats["graph_boosts"] > 0

    async def test_boost_with_entity_matches(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test boosting chunks with matching entities."""
        intent_result = None

        # Set matching entity names
        sample_chunks[0].entities = ["OpenAI", "GPT-4"]
        sample_graph_results.entities = [Mock(name="OpenAI"), Mock(name="GPT-4")]
        sample_graph_results.chunk_refs = []

        original_similarity = sample_chunks[0].similarity

        result = await hybrid_search._boost_with_graph_context(
            sample_chunks, sample_graph_results, intent_result
        )

        # Should be boosted
        assert result[0].similarity > original_similarity
        assert hybrid_search._stats["entity_boosts"] > 0

    async def test_boost_with_temporal_intent(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test boosting for temporal queries."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.TEMPORAL
        intent_result.entities_mentioned = []

        sample_chunks[0].metadata = {"created_at": datetime.now()}
        sample_graph_results.chunk_refs = []
        sample_graph_results.entities = []

        result = await hybrid_search._boost_with_graph_context(
            sample_chunks, sample_graph_results, intent_result
        )

        # Should apply temporal boost
        assert result is not None

    async def test_boost_with_entity_focused_intent(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test boosting for entity-focused queries."""
        intent_result = Mock()
        intent_result.primary_intent = SearchIntent.ENTITY_FOCUSED
        intent_result.entities_mentioned = ["OpenAI"]

        sample_chunks[0].entities = ["OpenAI"]
        sample_graph_results.chunk_refs = []
        sample_graph_results.entities = []

        original_similarity = sample_chunks[0].similarity

        result = await hybrid_search._boost_with_graph_context(
            sample_chunks, sample_graph_results, intent_result
        )

        # Should be boosted
        assert result[0].similarity > original_similarity


# ===== Main Search Tests =====


@pytest.mark.asyncio
class TestMainSearch:
    """Test main search method."""

    async def test_search_with_auto_strategy(self, hybrid_search, sample_chunks):
        """Test search with automatic strategy selection."""
        hybrid_search.intent_analyzer.analyze = Mock(return_value=Mock(primary_intent=SearchIntent.VECTOR_HEAVY))

        with patch.object(hybrid_search, "_vector_only_search", new=AsyncMock(return_value=HybridSearchResult(chunks=sample_chunks))):
            result = await hybrid_search.search("test query", limit=10)

            assert result.search_strategy == SearchStrategy.VECTOR_ONLY
            assert result.query_time > 0
            assert hybrid_search._stats["searches"] == 1

    async def test_search_with_forced_strategy(self, hybrid_search, sample_chunks):
        """Test search with forced strategy."""
        with patch.object(hybrid_search, "_vector_only_search", new=AsyncMock(return_value=HybridSearchResult(chunks=sample_chunks))):
            result = await hybrid_search.search("test query", limit=10, strategy=SearchStrategy.VECTOR_ONLY)

            assert result.search_strategy == SearchStrategy.VECTOR_ONLY
            # Should not analyze intent when strategy is forced
            assert result.intent is None

    async def test_search_logs_analytics(self, hybrid_search, sample_chunks):
        """Test that search logs analytics events."""
        hybrid_search.intent_analyzer.analyze = Mock(return_value=Mock(primary_intent=SearchIntent.VECTOR_HEAVY))

        with patch.object(hybrid_search, "_vector_only_search", new=AsyncMock(return_value=HybridSearchResult(chunks=sample_chunks))), \
             patch.object(hybrid_search, "_log_search_analytics", new=AsyncMock()) as mock_log:
            await hybrid_search.search("test query", limit=10)

            mock_log.assert_called_once()


# ===== Similar Content Search Tests =====


@pytest.mark.asyncio
class TestSearchSimilar:
    """Test similar content search."""

    async def test_search_similar_vector_only(self, hybrid_search, sample_chunks):
        """Test similar search with vector only."""
        chunk_id = uuid4()

        hybrid_search.config.performance.enable_graph = False
        hybrid_search.vector_search.search_similar_chunks = AsyncMock(return_value=sample_chunks)

        result = await hybrid_search.search_similar(chunk_id, limit=5)

        assert result.search_strategy == SearchStrategy.VECTOR_ONLY
        assert len(result.chunks) == 2

    async def test_search_similar_with_graph_enhancement(self, hybrid_search, sample_chunks, sample_graph_results):
        """Test similar search enhanced with graph context."""
        chunk_id = uuid4()

        sample_chunks[0].entities = ["OpenAI"]

        hybrid_search.config.performance.enable_graph = True
        hybrid_search.vector_search.search_similar_chunks = AsyncMock(return_value=sample_chunks)
        hybrid_search.graph_search.search = AsyncMock(return_value=sample_graph_results)

        with patch.object(hybrid_search, "_boost_with_graph_context", new=AsyncMock(return_value=sample_chunks)):
            result = await hybrid_search.search_similar(chunk_id, limit=5)

            assert result.search_strategy == SearchStrategy.HYBRID
            hybrid_search._boost_with_graph_context.assert_called_once()


# ===== Statistics Tests =====


class TestStatistics:
    """Test statistics tracking and retrieval."""

    def test_get_stats_empty(self, hybrid_search):
        """Test getting stats before any searches."""
        stats = hybrid_search.get_stats()

        assert stats["searches"] == 0
        assert "vector_stats" in stats
        assert "graph_stats" in stats
        assert "intent_stats" in stats

    @pytest.mark.asyncio
    async def test_get_stats_with_searches(self, hybrid_search, sample_chunks):
        """Test stats after performing searches."""
        hybrid_search.intent_analyzer.analyze = Mock(return_value=Mock(primary_intent=SearchIntent.VECTOR_HEAVY))

        with patch.object(hybrid_search, "_vector_only_search", new=AsyncMock(return_value=HybridSearchResult(chunks=sample_chunks))), \
             patch.object(hybrid_search, "_log_search_analytics", new=AsyncMock()):
            await hybrid_search.search("query 1", limit=10)
            await hybrid_search.search("query 2", limit=10)
            await hybrid_search.search("query 3", limit=10)

        stats = hybrid_search.get_stats()

        assert stats["searches"] == 3
        assert "avg_latency" in stats
        assert "strategy_distribution" in stats

    def test_stats_tracks_strategies(self, hybrid_search):
        """Test that stats track strategy usage."""
        hybrid_search._stats["searches"] = 10
        hybrid_search._stats["strategies"][SearchStrategy.VECTOR_ONLY.value] = 6
        hybrid_search._stats["strategies"][SearchStrategy.HYBRID.value] = 4

        stats = hybrid_search.get_stats()

        assert stats["strategy_distribution"][SearchStrategy.VECTOR_ONLY.value] == 0.6
        assert stats["strategy_distribution"][SearchStrategy.HYBRID.value] == 0.4


# ===== Analytics Logging Tests =====


@pytest.mark.asyncio
class TestAnalyticsLogging:
    """Test analytics event logging."""

    async def test_log_search_analytics_success(self, hybrid_search):
        """Test successful analytics logging."""
        with patch("src.agentic_rag.search.hybrid_search.get_analytics_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_logger.log_search = AsyncMock()
            mock_get_logger.return_value = mock_logger

            result = HybridSearchResult(
                chunks=[],
                entities=[],
                facts=[],
                metadata={"search_type": "vector_only"},
            )

            await hybrid_search._log_search_analytics(
                "test query",
                SearchStrategy.VECTOR_ONLY,
                SearchIntent.VECTOR_HEAVY,
                result,
                datetime.now(),
                datetime.now(),
            )

            mock_logger.log_search.assert_called_once()

    async def test_log_search_analytics_handles_errors(self, hybrid_search):
        """Test that analytics errors don't break search."""
        with patch("src.agentic_rag.search.hybrid_search.get_analytics_logger", side_effect=Exception("Analytics error")):
            result = HybridSearchResult()

            # Should not raise
            await hybrid_search._log_search_analytics(
                "test query",
                SearchStrategy.VECTOR_ONLY,
                SearchIntent.VECTOR_HEAVY,
                result,
                datetime.now(),
                datetime.now(),
            )


# ===== HybridSearchResult Tests =====


class TestHybridSearchResult:
    """Test HybridSearchResult dataclass."""

    def test_result_to_dict(self, sample_chunks):
        """Test converting result to dictionary."""
        result = HybridSearchResult(
            chunks=sample_chunks,
            facts=[],
            entities=[],
            relationships=[],
            search_strategy=SearchStrategy.HYBRID,
            intent=SearchIntent.HYBRID,
            query_time=0.5,
            metadata={"test": "value"},
        )

        result_dict = result.to_dict()

        assert result_dict["search_strategy"] == "HYBRID"
        assert result_dict["intent"] == "HYBRID"
        assert result_dict["query_time"] == 0.5
        assert len(result_dict["chunks"]) == 2
        assert result_dict["metadata"]["test"] == "value"

    def test_result_to_dict_with_none_intent(self, sample_chunks):
        """Test converting result with None intent."""
        result = HybridSearchResult(
            chunks=sample_chunks,
            intent=None,
        )

        result_dict = result.to_dict()

        assert result_dict["intent"] is None

    def test_result_defaults(self):
        """Test result default values."""
        result = HybridSearchResult()

        assert result.chunks == []
        assert result.facts == []
        assert result.entities == []
        assert result.relationships == []
        assert result.search_strategy == SearchStrategy.HYBRID
        assert result.query_time == 0.0
        assert result.metadata == {}
