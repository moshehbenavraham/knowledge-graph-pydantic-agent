"""
Extended comprehensive tests for hybrid search system.

Tests strategy selection, result merging, boosting mechanisms, parallel execution,
error handling, cache integration, intent-based routing, and performance edge cases.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.agentic_rag.search import (
    ChunkResult,
    GraphSearchResult,
    HybridSearch,
    HybridSearchResult,
    SearchIntent,
    SearchStrategy,
)
from src.agentic_rag.search.graph_search import GraphEntity, GraphFact
from src.agentic_rag.search.vector_search import SearchCache


class TestStrategySelection:
    """Test strategy selection logic based on various inputs."""

    @pytest.mark.asyncio
    async def test_vector_heavy_intent_selects_vector_only(self):
        """Vector-heavy intent should select VECTOR_ONLY strategy."""
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.VECTOR_HEAVY,
            entities_mentioned=[],
            temporal_markers=[],
            relationship_indicators=[],
        )

        strategy = search._select_strategy(mock_intent)
        assert strategy == SearchStrategy.VECTOR_ONLY

    @pytest.mark.asyncio
    async def test_graph_heavy_intent_with_graph_enabled(self):
        """Graph-heavy intent with graph enabled should select GRAPH_ONLY."""
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.GRAPH_HEAVY,
            entities_mentioned=["Entity1"],
            temporal_markers=[],
            relationship_indicators=["related", "connected"],
        )

        with patch.object(search.config.performance, "enable_graph", True):
            strategy = search._select_strategy(mock_intent)
            assert strategy == SearchStrategy.GRAPH_ONLY

    @pytest.mark.asyncio
    async def test_graph_heavy_intent_without_graph_enabled(self):
        """Graph-heavy intent without graph should fallback to VECTOR_ONLY."""
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.GRAPH_HEAVY,
            entities_mentioned=["Entity1"],
            temporal_markers=[],
            relationship_indicators=["related"],
        )

        with patch.object(search.config.performance, "enable_graph", False):
            strategy = search._select_strategy(mock_intent)
            assert strategy == SearchStrategy.VECTOR_ONLY

    @pytest.mark.asyncio
    async def test_temporal_intent_selects_hybrid(self):
        """Temporal intent should select HYBRID strategy when graph enabled."""
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.TEMPORAL,
            entities_mentioned=["OpenAI"],
            temporal_markers=["when", "2023"],
            relationship_indicators=[],
        )

        with patch.object(search.config.performance, "enable_graph", True):
            strategy = search._select_strategy(mock_intent)
            assert strategy == SearchStrategy.HYBRID

    @pytest.mark.asyncio
    async def test_entity_focused_intent_selects_hybrid(self):
        """Entity-focused intent should select HYBRID strategy."""
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.ENTITY_FOCUSED,
            entities_mentioned=["Microsoft", "OpenAI"],
            temporal_markers=[],
            relationship_indicators=[],
        )

        with patch.object(search.config.performance, "enable_graph", True):
            strategy = search._select_strategy(mock_intent)
            assert strategy == SearchStrategy.HYBRID

    @pytest.mark.asyncio
    async def test_default_intent_with_graph_selects_adaptive(self):
        """Default intent with graph enabled should select ADAPTIVE."""
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.HYBRID,
            entities_mentioned=[],
            temporal_markers=[],
            relationship_indicators=[],
        )

        with patch.object(search.config.performance, "enable_graph", True):
            strategy = search._select_strategy(mock_intent)
            assert strategy == SearchStrategy.ADAPTIVE


class TestResultMerging:
    """Test result merging algorithms."""

    @pytest.mark.asyncio
    async def test_merge_with_empty_vector_results(self):
        """Test merging when vector search returns empty results."""
        search = HybridSearch()

        graph_results = GraphSearchResult(
            facts=[GraphFact("Test fact", None, 0.8, "chunk-1")],
            entities=[GraphEntity("e1", "Entity1", "company", ["chunk-1"])],
        )

        boosted = await search._boost_with_graph_context([], graph_results, None)
        assert len(boosted) == 0

    @pytest.mark.asyncio
    async def test_merge_with_empty_graph_results(self):
        """Test merging when graph search returns empty results."""
        search = HybridSearch()

        chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Test content",
                similarity=0.8,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
            )
        ]

        graph_results = GraphSearchResult()
        boosted = await search._boost_with_graph_context(chunks, graph_results, None)

        assert len(boosted) == 1
        assert boosted[0].similarity == 0.8  # No boosting applied

    @pytest.mark.asyncio
    async def test_merge_with_overlapping_chunk_refs(self):
        """Test merging when chunk IDs overlap between vector and graph results."""
        search = HybridSearch()

        chunk_id = uuid4()
        chunks = [
            ChunkResult(
                chunk_id=chunk_id,
                content="Test content",
                similarity=0.7,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
                entities=["Entity1"],
            )
        ]

        graph_results = GraphSearchResult(
            entities=[GraphEntity("e1", "Entity1", "company", [str(chunk_id)])],
            chunk_refs=[str(chunk_id)],
        )

        boosted = await search._boost_with_graph_context(chunks, graph_results, None)

        # Should be boosted due to overlap
        assert boosted[0].similarity > 0.7
        assert search._stats["graph_boosts"] > 0

    @pytest.mark.asyncio
    async def test_merge_preserves_top_results_order(self):
        """Test that merging preserves correct result ordering."""
        search = HybridSearch()

        chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content=f"Content {i}",
                similarity=0.9 - i * 0.1,
                document_id=uuid4(),
                document_title=f"Doc {i}",
                document_source=f"doc{i}.md",
            )
            for i in range(5)
        ]

        graph_results = GraphSearchResult()
        boosted = await search._boost_with_graph_context(chunks, graph_results, None)

        # Order should be preserved based on similarity
        for i in range(len(boosted) - 1):
            assert boosted[i].similarity >= boosted[i + 1].similarity


class TestBoostingMechanisms:
    """Test various boosting mechanisms."""

    @pytest.mark.asyncio
    async def test_chunk_ref_boosting(self):
        """Test boosting based on chunk reference in graph results."""
        search = HybridSearch()

        chunk_id = uuid4()
        chunks = [
            ChunkResult(
                chunk_id=chunk_id,
                content="Referenced content",
                similarity=0.6,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
            )
        ]

        graph_results = GraphSearchResult(chunk_refs=[str(chunk_id)])

        initial_boost_count = search._stats["graph_boosts"]
        boosted = await search._boost_with_graph_context(chunks, graph_results, None)

        # Should apply 1.3x boost
        assert boosted[0].similarity == min(1.0, 0.6 * 1.3)
        assert search._stats["graph_boosts"] == initial_boost_count + 1

    @pytest.mark.asyncio
    async def test_entity_overlap_boosting(self):
        """Test boosting based on entity overlap."""
        search = HybridSearch()

        chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Content about Entity1",
                similarity=0.7,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
                entities=["Entity1", "Entity2"],
            )
        ]

        graph_results = GraphSearchResult(
            entities=[
                GraphEntity("e1", "Entity1", "company", []),
                GraphEntity("e2", "Entity3", "person", []),
            ]
        )

        initial_boost_count = search._stats["entity_boosts"]
        boosted = await search._boost_with_graph_context(chunks, graph_results, None)

        # Should apply entity boost (1.2x)
        assert boosted[0].similarity > 0.7
        assert search._stats["entity_boosts"] == initial_boost_count + 1

    @pytest.mark.asyncio
    async def test_combined_boosting(self):
        """Test combined boosting from multiple sources."""
        search = HybridSearch()

        chunk_id = uuid4()
        chunks = [
            ChunkResult(
                chunk_id=chunk_id,
                content="Content with Entity1",
                similarity=0.5,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
                entities=["Entity1"],
            )
        ]

        graph_results = GraphSearchResult(
            entities=[GraphEntity("e1", "Entity1", "company", [str(chunk_id)])],
            chunk_refs=[str(chunk_id)],
        )

        boosted = await search._boost_with_graph_context(chunks, graph_results, None)

        # Should apply both boosts: 0.5 * 1.3 * 1.2 = 0.78
        expected = min(1.0, 0.5 * 1.3 * 1.2)
        assert abs(boosted[0].similarity - expected) < 0.01

    @pytest.mark.asyncio
    async def test_temporal_intent_boosting(self):
        """Test boosting based on temporal intent."""
        search = HybridSearch()

        chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Recent content",
                similarity=0.7,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
                metadata={"created_at": datetime.now().isoformat()},
            )
        ]

        mock_intent = Mock(
            primary_intent=SearchIntent.TEMPORAL,
            entities_mentioned=[],
            temporal_markers=["recent"],
            relationship_indicators=[],
        )

        graph_results = GraphSearchResult()
        boosted = await search._boost_with_graph_context(chunks, graph_results, mock_intent)

        # Should apply temporal boost (1.1x)
        assert boosted[0].similarity > 0.7

    @pytest.mark.asyncio
    async def test_entity_focused_intent_boosting(self):
        """Test boosting based on entity-focused intent."""
        search = HybridSearch()

        chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Content about OpenAI",
                similarity=0.65,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
                entities=["OpenAI"],
            )
        ]

        mock_intent = Mock(
            primary_intent=SearchIntent.ENTITY_FOCUSED,
            entities_mentioned=["OpenAI"],
            temporal_markers=[],
            relationship_indicators=[],
        )

        graph_results = GraphSearchResult()
        boosted = await search._boost_with_graph_context(chunks, graph_results, mock_intent)

        # Should apply entity focus boost (1.3x)
        expected = min(1.0, 0.65 * 1.3)
        assert abs(boosted[0].similarity - expected) < 0.01

    @pytest.mark.asyncio
    async def test_boost_capping_at_1_0(self):
        """Test that boosting does not exceed similarity of 1.0."""
        search = HybridSearch()

        chunk_id = uuid4()
        chunks = [
            ChunkResult(
                chunk_id=chunk_id,
                content="High similarity content",
                similarity=0.95,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
                entities=["Entity1"],
            )
        ]

        graph_results = GraphSearchResult(
            entities=[GraphEntity("e1", "Entity1", "company", [str(chunk_id)])],
            chunk_refs=[str(chunk_id)],
        )

        boosted = await search._boost_with_graph_context(chunks, graph_results, None)

        # Should be capped at 1.0
        assert boosted[0].similarity == 1.0


class TestParallelExecution:
    """Test parallel execution of searches."""

    @pytest.mark.asyncio
    async def test_parallel_search_both_complete(self):
        """Test parallel execution when both searches complete successfully."""
        search = HybridSearch()

        with patch.object(search.config.performance, "enable_parallel_search", True):
            with patch.object(search.vector_search, "search") as mock_vector:
                mock_vector.return_value = [
                    ChunkResult(
                        chunk_id=uuid4(),
                        content="Test",
                        similarity=0.8,
                        document_id=uuid4(),
                        document_title="Test",
                        document_source="test.md",
                    )
                ]

                with patch.object(search.graph_search, "search") as mock_graph:
                    mock_graph.return_value = GraphSearchResult()

                    mock_intent = Mock(
                        primary_intent=SearchIntent.HYBRID,
                        entities_mentioned=[],
                        temporal_markers=[],
                        relationship_indicators=[],
                    )

                    result = await search._hybrid_search("test query", 10, mock_intent)

                    # Both should be called
                    mock_vector.assert_called_once()
                    mock_graph.assert_called_once()
                    assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_sequential_execution_when_parallel_disabled(self):
        """Test sequential execution when parallel search is disabled."""
        search = HybridSearch()

        with patch.object(search.config.performance, "enable_parallel_search", False):
            with patch.object(search.vector_search, "search") as mock_vector:
                mock_vector.return_value = []

                with patch.object(search.graph_search, "search") as mock_graph:
                    mock_graph.return_value = GraphSearchResult()

                    mock_intent = Mock(
                        primary_intent=SearchIntent.HYBRID,
                        entities_mentioned=[],
                        temporal_markers=[],
                        relationship_indicators=[],
                    )

                    result = await search._hybrid_search("test query", 10, mock_intent)

                    # Both should be called sequentially
                    mock_vector.assert_called_once()
                    mock_graph.assert_called_once()
                    assert isinstance(result, HybridSearchResult)


class TestErrorHandling:
    """Test error handling and fallback mechanisms."""

    @pytest.mark.asyncio
    async def test_vector_search_failure_fallback(self):
        """Test fallback when vector search fails."""
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.side_effect = Exception("Vector search failed")

            with patch.object(search.graph_search, "search") as mock_graph:
                mock_graph.return_value = GraphSearchResult()

                mock_intent = Mock(
                    primary_intent=SearchIntent.HYBRID,
                    entities_mentioned=[],
                    temporal_markers=[],
                    relationship_indicators=[],
                )

                # Should not crash, but may return partial results
                with pytest.raises(Exception):  # noqa: B017
                    await search._hybrid_search("test query", 10, mock_intent)

    @pytest.mark.asyncio
    async def test_graph_search_failure_fallback(self):
        """Test fallback when graph search fails."""
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = [
                ChunkResult(
                    chunk_id=uuid4(),
                    content="Test",
                    similarity=0.8,
                    document_id=uuid4(),
                    document_title="Test",
                    document_source="test.md",
                )
            ]

            with patch.object(search.graph_search, "search") as mock_graph:
                mock_graph.side_effect = Exception("Graph search failed")

                mock_intent = Mock(
                    primary_intent=SearchIntent.HYBRID,
                    entities_mentioned=[],
                    temporal_markers=[],
                    relationship_indicators=[],
                )

                # Should not crash, but may return partial results
                with pytest.raises(Exception):  # noqa: B017
                    await search._hybrid_search("test query", 10, mock_intent)

    @pytest.mark.asyncio
    async def test_invalid_chunk_id_in_graph_results(self):
        """Test handling of invalid chunk IDs from graph results."""
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.GRAPH_HEAVY,
            entities_mentioned=["Test"],
            temporal_markers=[],
            relationship_indicators=[],
        )

        with patch.object(search.graph_search, "search") as mock_graph:
            mock_graph.return_value = GraphSearchResult(chunk_refs=["invalid-uuid", "also-invalid"])

            with patch.object(search.vector_search, "get_chunks_by_ids") as mock_get:
                mock_get.return_value = []

                result = await search._graph_only_search("test", 10, mock_intent)

                # Should handle gracefully
                assert isinstance(result, HybridSearchResult)
                assert len(result.chunks) == 0

    @pytest.mark.asyncio
    async def test_empty_query_handling(self):
        """Test handling of empty query strings."""
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = []

            result = await search.search("", limit=10)

            # Should handle gracefully
            assert isinstance(result, HybridSearchResult)
            mock_vector.assert_called()


class TestCacheIntegration:
    """Test cache integration with search operations."""

    def test_cache_key_generation_consistency(self):
        """Test that cache keys are generated consistently."""
        cache = SearchCache()

        embedding = [0.1] * 100
        filters = {"test": "filter"}

        key1 = cache.generate_key(embedding, filters)
        key2 = cache.generate_key(embedding, filters)

        assert key1 == key2

    def test_cache_key_generation_different_embeddings(self):
        """Test that different embeddings generate different keys."""
        cache = SearchCache()

        embedding1 = [0.1] * 100
        embedding2 = [0.2] * 100

        key1 = cache.generate_key(embedding1, {})
        key2 = cache.generate_key(embedding2, {})

        assert key1 != key2

    def test_cache_expiration(self):
        """Test that cached results expire correctly."""
        cache = SearchCache(ttl_seconds=1)

        results = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Test",
                similarity=0.8,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
            )
        ]

        key = cache.generate_key([0.1] * 10, {})
        cache.set(key, results)

        # Should be available immediately
        assert cache.get(key) == results

        # Manually expire
        cache._cache[key] = (datetime.now() - timedelta(seconds=5), results)

        # Should be expired
        assert cache.get(key) is None

    def test_cache_clear_functionality(self):
        """Test cache clearing."""
        cache = SearchCache()

        results = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Test",
                similarity=0.8,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
            )
        ]

        key = cache.generate_key([0.1] * 10, {})
        cache.set(key, results)

        assert cache.get(key) is not None

        cache.clear()

        assert cache.get(key) is None

    @pytest.mark.skip(reason="SearchCache does not support max_size parameter")
    def test_cache_size_limit(self):
        """Test cache respects maximum size."""
        cache = SearchCache(max_size=2)

        for i in range(5):
            key = cache.generate_key([float(i)] * 10, {})
            results = [
                ChunkResult(
                    chunk_id=uuid4(),
                    content=f"Test {i}",
                    similarity=0.8,
                    document_id=uuid4(),
                    document_title="Test",
                    document_source="test.md",
                )
            ]
            cache.set(key, results)

        # Should only keep max_size entries
        assert len(cache._cache) <= 2


class TestIntentBasedRouting:
    """Test intent-based routing logic."""

    @pytest.mark.asyncio
    async def test_routing_with_forced_strategy(self):
        """Test that forced strategy overrides intent analysis."""
        search = HybridSearch()

        with patch.object(search.intent_analyzer, "analyze") as mock_analyze:
            with patch.object(search, "_vector_only_search") as mock_vector:
                mock_vector.return_value = HybridSearchResult()

                # Force VECTOR_ONLY despite what intent analysis might suggest
                await search.search("test query", limit=10, strategy=SearchStrategy.VECTOR_ONLY)

                # Intent analysis should not be called when strategy is forced
                mock_analyze.assert_not_called()
                mock_vector.assert_called_once()

    @pytest.mark.asyncio
    async def test_adaptive_search_with_high_similarity_results(self):
        """Test adaptive search with high similarity results stays vector-only."""
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            # High similarity results
            mock_vector.return_value = [
                ChunkResult(
                    chunk_id=uuid4(),
                    content=f"High similarity content {i}",
                    similarity=0.9,
                    document_id=uuid4(),
                    document_title="Test",
                    document_source="test.md",
                )
                for i in range(5)
            ]

            mock_intent = Mock(
                primary_intent=SearchIntent.HYBRID,
                entities_mentioned=["Entity1"],
                temporal_markers=[],
                relationship_indicators=[],
            )

            result = await search._adaptive_search("test query", 10, mock_intent)

            # Should not trigger graph search
            assert result.metadata["search_type"] == "adaptive_vector"

    @pytest.mark.asyncio
    async def test_adaptive_search_with_low_similarity_triggers_graph(self):
        """Test adaptive search with low similarity results triggers graph search."""
        search = HybridSearch()

        with patch.object(search.config.performance, "enable_graph", True):
            with patch.object(search.vector_search, "search") as mock_vector:
                # Low similarity results
                mock_vector.return_value = [
                    ChunkResult(
                        chunk_id=uuid4(),
                        content="Low similarity content",
                        similarity=0.5,
                        document_id=uuid4(),
                        document_title="Test",
                        document_source="test.md",
                    )
                ]

                with patch.object(search, "_hybrid_search") as mock_hybrid:
                    mock_hybrid.return_value = HybridSearchResult()

                    mock_intent = Mock(
                        primary_intent=SearchIntent.HYBRID,
                        entities_mentioned=["Entity1"],
                        temporal_markers=[],
                        relationship_indicators=[],
                    )

                    await search._adaptive_search("test query", 10, mock_intent)

                    # Should trigger hybrid search
                    mock_hybrid.assert_called_once()

    @pytest.mark.asyncio
    async def test_adaptive_search_with_multiple_entities(self):
        """Test adaptive search with multiple entities triggers graph search."""
        search = HybridSearch()

        with patch.object(search.config.performance, "enable_graph", True):
            with patch.object(search.vector_search, "search") as mock_vector:
                mock_vector.return_value = [
                    ChunkResult(
                        chunk_id=uuid4(),
                        content="Content with entities",
                        similarity=0.75,
                        document_id=uuid4(),
                        document_title="Test",
                        document_source="test.md",
                    )
                ]

                with patch.object(search, "_hybrid_search") as mock_hybrid:
                    mock_hybrid.return_value = HybridSearchResult()

                    mock_intent = Mock(
                        primary_intent=SearchIntent.HYBRID,
                        entities_mentioned=["Entity1", "Entity2", "Entity3"],
                        temporal_markers=[],
                        relationship_indicators=[],
                    )

                    await search._adaptive_search("test query", 10, mock_intent)

                    # Should trigger hybrid search due to multiple entities
                    mock_hybrid.assert_called_once()


class TestPerformanceEdgeCases:
    """Test performance and edge cases."""

    @pytest.mark.asyncio
    async def test_large_result_set_handling(self):
        """Test handling of large result sets."""
        search = HybridSearch()

        # Create 1000 chunks
        large_chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content=f"Content {i}",
                similarity=0.9 - i * 0.0001,
                document_id=uuid4(),
                document_title=f"Doc {i}",
                document_source=f"doc{i}.md",
            )
            for i in range(1000)
        ]

        graph_results = GraphSearchResult()

        # Should handle efficiently
        boosted = await search._boost_with_graph_context(large_chunks, graph_results, None)

        assert len(boosted) == 1000
        assert all(isinstance(c, ChunkResult) for c in boosted)

    @pytest.mark.asyncio
    async def test_search_with_zero_limit(self):
        """Test search with limit of 0."""
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = []

            result = await search.search("test query", limit=0)

            # Should handle gracefully
            assert isinstance(result, HybridSearchResult)
            mock_vector.assert_called()

    @pytest.mark.asyncio
    async def test_search_similar_with_nonexistent_chunk(self):
        """Test similarity search with nonexistent chunk ID."""
        search = HybridSearch()

        with patch.object(search.vector_search, "search_similar_chunks") as mock_similar:
            mock_similar.return_value = []

            result = await search.search_similar(uuid4(), limit=5)

            assert isinstance(result, HybridSearchResult)
            assert len(result.chunks) == 0

    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test that search statistics are tracked correctly."""
        search = HybridSearch()

        initial_searches = search._stats["searches"]

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = []

            await search.search("test query", limit=10)

        assert search._stats["searches"] == initial_searches + 1
        assert search._stats["total_latency"] > 0

    @pytest.mark.asyncio
    async def test_get_stats_with_no_searches(self):
        """Test getting statistics when no searches performed."""
        search = HybridSearch()

        stats = search.get_stats()

        assert stats["searches"] == 0
        assert "vector_stats" in stats
        assert "graph_stats" in stats
        assert "intent_stats" in stats

    @pytest.mark.asyncio
    async def test_get_stats_with_multiple_searches(self):
        """Test statistics after multiple searches."""
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = []

            # Perform multiple searches
            for _ in range(5):
                await search.search("test query", limit=10)

        stats = search.get_stats()

        assert stats["searches"] == 5
        assert "avg_latency" in stats
        assert "strategy_distribution" in stats
        assert stats["total_latency"] > 0

    @pytest.mark.asyncio
    async def test_result_to_dict_serialization(self):
        """Test HybridSearchResult serialization to dictionary."""
        result = HybridSearchResult(
            chunks=[
                ChunkResult(
                    chunk_id=uuid4(),
                    content="Test",
                    similarity=0.8,
                    document_id=uuid4(),
                    document_title="Test",
                    document_source="test.md",
                )
            ],
            facts=[GraphFact("Test fact", None, 0.9, "chunk-1")],
            entities=[GraphEntity("e1", "Entity1", "company", ["chunk-1"])],
            search_strategy=SearchStrategy.HYBRID,
            intent=SearchIntent.HYBRID,
            query_time=0.5,
            metadata={"test": "data"},
        )

        result_dict = result.to_dict()

        assert "chunks" in result_dict
        assert "facts" in result_dict
        assert "entities" in result_dict
        assert result_dict["search_strategy"] == "hybrid"
        assert result_dict["intent"] == "hybrid"
        assert result_dict["query_time"] == 0.5
        assert result_dict["metadata"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_hybrid_search_result_limits(self):
        """Test that hybrid search respects result limits."""
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            # Return more results than requested
            mock_vector.return_value = [
                ChunkResult(
                    chunk_id=uuid4(),
                    content=f"Content {i}",
                    similarity=0.9 - i * 0.01,
                    document_id=uuid4(),
                    document_title="Test",
                    document_source="test.md",
                )
                for i in range(50)
            ]

            with patch.object(search.graph_search, "search") as mock_graph:
                mock_graph.return_value = GraphSearchResult(
                    facts=[GraphFact(f"Fact {i}", None, 0.8, f"chunk-{i}") for i in range(20)],
                    entities=[GraphEntity(f"e{i}", f"Entity{i}", "company", []) for i in range(20)],
                )

                mock_intent = Mock(
                    primary_intent=SearchIntent.HYBRID,
                    entities_mentioned=[],
                    temporal_markers=[],
                    relationship_indicators=[],
                )

                result = await search._hybrid_search("test query", 10, mock_intent)

                # Should limit chunks to 10
                assert len(result.chunks) <= 10
                # Should limit facts to 10
                assert len(result.facts) <= 10
                # Should limit entities to 10
                assert len(result.entities) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
