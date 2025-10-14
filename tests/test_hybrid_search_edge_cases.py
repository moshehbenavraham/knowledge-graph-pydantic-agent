"""
Targeted edge case tests for hybrid_search.py to achieve 95%+ coverage.

Specifically covers missing lines: 129, 132, 178, 182, 195-197, 226, 385-396
"""

from unittest.mock import Mock, patch
from uuid import UUID, uuid4

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


class TestStrategyExecutionPaths:
    """Tests to cover specific strategy execution paths (lines 129, 132)."""

    @pytest.mark.asyncio
    async def test_search_with_graph_only_strategy_forced(self):
        """
        Test line 129: Force GRAPH_ONLY strategy to execute graph-only search path.
        """
        search = HybridSearch()

        with patch.object(search.graph_search, "search") as mock_graph:
            mock_graph.return_value = GraphSearchResult(
                facts=[GraphFact("Test fact", None, 0.8, "chunk-1")],
                entities=[GraphEntity("e1", "Entity1", "company", ["chunk-1"])],
                chunk_refs=[],
            )

            with patch.object(search.vector_search, "get_chunks_by_ids") as mock_get_chunks:
                mock_get_chunks.return_value = []

                # Force GRAPH_ONLY strategy - this should execute line 129
                result = await search.search(
                    "test query", limit=10, strategy=SearchStrategy.GRAPH_ONLY
                )

                # Verify graph search was called
                mock_graph.assert_called_once()
                assert isinstance(result, HybridSearchResult)
                assert len(result.facts) > 0
                assert result.search_strategy == SearchStrategy.GRAPH_ONLY

    @pytest.mark.asyncio
    async def test_search_with_hybrid_strategy_forced(self):
        """
        Test line 132: Force HYBRID strategy to execute hybrid search path.
        """
        search = HybridSearch()

        with patch.object(search.config.performance, "enable_parallel_search", False):
            with patch.object(search.vector_search, "search") as mock_vector:
                mock_vector.return_value = [
                    ChunkResult(
                        chunk_id=uuid4(),
                        content="Test content",
                        similarity=0.8,
                        document_id=uuid4(),
                        document_title="Test Doc",
                        document_source="test.md",
                    )
                ]

                with patch.object(search.graph_search, "search") as mock_graph:
                    mock_graph.return_value = GraphSearchResult()

                    # Force HYBRID strategy - this should execute line 132
                    result = await search.search(
                        "test query", limit=10, strategy=SearchStrategy.HYBRID
                    )

                    # Verify both searches were called
                    mock_vector.assert_called_once()
                    mock_graph.assert_called_once()
                    assert isinstance(result, HybridSearchResult)
                    assert result.search_strategy == SearchStrategy.HYBRID


class TestStrategySelectionFallbacks:
    """Tests to cover strategy selection fallback paths (lines 178, 182)."""

    @pytest.mark.asyncio
    async def test_temporal_intent_without_graph_enabled(self):
        """
        Test line 178: TEMPORAL intent should fallback to VECTOR_ONLY when graph disabled.
        """
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.TEMPORAL,
            entities_mentioned=["OpenAI"],
            temporal_markers=["when", "2023"],
            relationship_indicators=[],
        )

        # Disable graph to trigger fallback
        with patch.object(search.config.performance, "enable_graph", False):
            strategy = search._select_strategy(mock_intent)
            assert strategy == SearchStrategy.VECTOR_ONLY

    @pytest.mark.asyncio
    async def test_entity_focused_intent_without_graph_enabled(self):
        """
        Test line 178: ENTITY_FOCUSED intent should fallback to VECTOR_ONLY when graph disabled.
        """
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.ENTITY_FOCUSED,
            entities_mentioned=["Microsoft", "OpenAI"],
            temporal_markers=[],
            relationship_indicators=[],
        )

        # Disable graph to trigger fallback
        with patch.object(search.config.performance, "enable_graph", False):
            strategy = search._select_strategy(mock_intent)
            assert strategy == SearchStrategy.VECTOR_ONLY

    @pytest.mark.asyncio
    async def test_default_intent_without_graph_enabled(self):
        """
        Test line 182: Default/HYBRID intent should fallback to VECTOR_ONLY when graph disabled.
        """
        search = HybridSearch()

        mock_intent = Mock(
            primary_intent=SearchIntent.HYBRID,
            entities_mentioned=[],
            temporal_markers=[],
            relationship_indicators=[],
        )

        # Disable graph to trigger fallback
        with patch.object(search.config.performance, "enable_graph", False):
            strategy = search._select_strategy(mock_intent)
            assert strategy == SearchStrategy.VECTOR_ONLY

    @pytest.mark.asyncio
    async def test_semantic_intent_without_graph_enabled(self):
        """
        Test line 182: Any non-specific intent should fallback to VECTOR_ONLY when graph disabled.
        """
        search = HybridSearch()

        # Test with a different intent that doesn't match specific conditions
        mock_intent = Mock(
            primary_intent=SearchIntent.VECTOR_HEAVY,
            entities_mentioned=[],
            temporal_markers=[],
            relationship_indicators=[],
        )

        with patch.object(search.config.performance, "enable_graph", False):
            # This should already return VECTOR_ONLY, but we're testing the fallback path
            strategy = search._select_strategy(mock_intent)
            assert strategy == SearchStrategy.VECTOR_ONLY


class TestVectorOnlySearchPath:
    """Tests to cover _vector_only_search method (lines 195-197)."""

    @pytest.mark.asyncio
    async def test_vector_only_search_basic(self):
        """
        Test lines 195-197: Execute _vector_only_search method directly.
        """
        search = HybridSearch()

        mock_chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Test content 1",
                similarity=0.9,
                document_id=uuid4(),
                document_title="Doc 1",
                document_source="doc1.md",
            ),
            ChunkResult(
                chunk_id=uuid4(),
                content="Test content 2",
                similarity=0.85,
                document_id=uuid4(),
                document_title="Doc 2",
                document_source="doc2.md",
            ),
        ]

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = mock_chunks

            # Call the method directly to execute lines 195-197
            result = await search._vector_only_search("test query", 10)

            mock_vector.assert_called_once_with("test query", 10)
            assert isinstance(result, HybridSearchResult)
            assert len(result.chunks) == 2
            assert result.metadata["search_type"] == "vector_only"

    @pytest.mark.asyncio
    async def test_vector_only_search_with_empty_results(self):
        """
        Test lines 195-197: _vector_only_search with empty results.
        """
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = []

            result = await search._vector_only_search("query with no results", 10)

            mock_vector.assert_called_once()
            assert isinstance(result, HybridSearchResult)
            assert len(result.chunks) == 0
            assert result.metadata["search_type"] == "vector_only"

    @pytest.mark.asyncio
    async def test_vector_only_search_via_strategy(self):
        """
        Test lines 195-197: Trigger _vector_only_search through strategy selection.
        """
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = [
                ChunkResult(
                    chunk_id=uuid4(),
                    content="Strategy-triggered content",
                    similarity=0.88,
                    document_id=uuid4(),
                    document_title="Strategy Doc",
                    document_source="strategy.md",
                )
            ]

            # Force VECTOR_ONLY strategy
            result = await search.search("test query", limit=5, strategy=SearchStrategy.VECTOR_ONLY)

            mock_vector.assert_called_once()
            assert len(result.chunks) == 1
            assert result.search_strategy == SearchStrategy.VECTOR_ONLY

    @pytest.mark.asyncio
    async def test_vector_only_search_with_large_limit(self):
        """
        Test lines 195-197: _vector_only_search with large limit parameter.
        """
        search = HybridSearch()

        large_result_set = [
            ChunkResult(
                chunk_id=uuid4(),
                content=f"Content {i}",
                similarity=0.9 - i * 0.01,
                document_id=uuid4(),
                document_title=f"Doc {i}",
                document_source=f"doc{i}.md",
            )
            for i in range(100)
        ]

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = large_result_set

            result = await search._vector_only_search("comprehensive query", 100)

            mock_vector.assert_called_once_with("comprehensive query", 100)
            assert len(result.chunks) == 100


class TestGraphOnlyChunkRetrieval:
    """Tests to cover chunk retrieval in graph-only search (line 226)."""

    @pytest.mark.asyncio
    async def test_graph_only_search_with_valid_chunk_refs(self):
        """
        Test line 226: Graph-only search with valid chunk references that need retrieval.
        """
        search = HybridSearch()

        chunk_id_1 = uuid4()
        chunk_id_2 = uuid4()

        mock_graph_result = GraphSearchResult(
            facts=[GraphFact("Fact about entities", None, 0.9, str(chunk_id_1))],
            entities=[
                GraphEntity("e1", "Company A", "company", [str(chunk_id_1)]),
                GraphEntity("e2", "Person B", "person", [str(chunk_id_2)]),
            ],
            chunk_refs=[str(chunk_id_1), str(chunk_id_2)],
        )

        mock_chunks = [
            ChunkResult(
                chunk_id=chunk_id_1,
                content="Content from chunk 1",
                similarity=0.95,
                document_id=uuid4(),
                document_title="Doc 1",
                document_source="doc1.md",
            ),
            ChunkResult(
                chunk_id=chunk_id_2,
                content="Content from chunk 2",
                similarity=0.92,
                document_id=uuid4(),
                document_title="Doc 2",
                document_source="doc2.md",
            ),
        ]

        mock_intent = Mock(
            primary_intent=SearchIntent.GRAPH_HEAVY,
            entities_mentioned=["Company A"],
            temporal_markers=[],
            relationship_indicators=["related"],
        )

        with patch.object(search.graph_search, "search") as mock_graph:
            mock_graph.return_value = mock_graph_result

            with patch.object(search.vector_search, "get_chunks_by_ids") as mock_get_chunks:
                mock_get_chunks.return_value = mock_chunks

                # This should execute line 226
                result = await search._graph_only_search("test query", 10, mock_intent)

                # Verify get_chunks_by_ids was called with UUID objects
                mock_get_chunks.assert_called_once()
                called_uuids = mock_get_chunks.call_args[0][0]
                assert all(isinstance(uid, UUID) for uid in called_uuids)
                assert len(called_uuids) == 2

                assert len(result.chunks) == 2
                assert len(result.entities) == 2

    @pytest.mark.asyncio
    async def test_graph_only_search_chunk_refs_exceeds_limit(self):
        """
        Test line 226: Graph-only search with more chunk refs than the limit.
        """
        search = HybridSearch()

        # Create 20 chunk references but limit to 5
        chunk_ids = [uuid4() for _ in range(20)]
        chunk_refs = [str(cid) for cid in chunk_ids]

        mock_graph_result = GraphSearchResult(
            facts=[GraphFact(f"Fact {i}", None, 0.8, str(chunk_ids[i])) for i in range(5)],
            entities=[
                GraphEntity(f"e{i}", f"Entity {i}", "company", [str(chunk_ids[i])])
                for i in range(5)
            ],
            chunk_refs=chunk_refs,  # 20 refs
        )

        mock_chunks = [
            ChunkResult(
                chunk_id=chunk_ids[i],
                content=f"Content {i}",
                similarity=0.9,
                document_id=uuid4(),
                document_title=f"Doc {i}",
                document_source=f"doc{i}.md",
            )
            for i in range(5)  # Only return first 5
        ]

        mock_intent = Mock(
            primary_intent=SearchIntent.GRAPH_HEAVY,
            entities_mentioned=["Entity 1"],
            temporal_markers=[],
            relationship_indicators=[],
        )

        with patch.object(search.graph_search, "search") as mock_graph:
            mock_graph.return_value = mock_graph_result

            with patch.object(search.vector_search, "get_chunks_by_ids") as mock_get_chunks:
                mock_get_chunks.return_value = mock_chunks

                # Limit is 5, but we have 20 chunk refs
                await search._graph_only_search("test query", 5, mock_intent)

                # Should only request first 5 chunk refs
                mock_get_chunks.assert_called_once()
                called_uuids = mock_get_chunks.call_args[0][0]
                assert len(called_uuids) <= 5

    @pytest.mark.asyncio
    async def test_graph_only_search_mixed_valid_invalid_chunk_refs(self):
        """
        Test line 226: Graph-only search with mix of valid and invalid UUID strings.
        """
        search = HybridSearch()

        valid_chunk_id = uuid4()

        # Mix valid and invalid chunk references
        mock_graph_result = GraphSearchResult(
            facts=[GraphFact("Test fact", None, 0.85, str(valid_chunk_id))],
            entities=[GraphEntity("e1", "Valid Entity", "company", [str(valid_chunk_id)])],
            chunk_refs=[str(valid_chunk_id), "invalid-uuid-string", "also-not-a-uuid", "12345"],
        )

        mock_chunks = [
            ChunkResult(
                chunk_id=valid_chunk_id,
                content="Valid chunk content",
                similarity=0.93,
                document_id=uuid4(),
                document_title="Valid Doc",
                document_source="valid.md",
            )
        ]

        mock_intent = Mock(
            primary_intent=SearchIntent.GRAPH_HEAVY,
            entities_mentioned=["Valid Entity"],
            temporal_markers=[],
            relationship_indicators=[],
        )

        with patch.object(search.graph_search, "search") as mock_graph:
            mock_graph.return_value = mock_graph_result

            with patch.object(search.vector_search, "get_chunks_by_ids") as mock_get_chunks:
                mock_get_chunks.return_value = mock_chunks

                result = await search._graph_only_search("test query", 10, mock_intent)

                # Should only pass valid UUIDs to get_chunks_by_ids
                mock_get_chunks.assert_called_once()
                called_uuids = mock_get_chunks.call_args[0][0]
                assert len(called_uuids) == 1  # Only the valid one
                assert all(isinstance(uid, UUID) for uid in called_uuids)

                assert len(result.chunks) == 1


class TestSearchSimilarWithGraphContext:
    """Tests to cover search_similar graph context path (lines 385-396)."""

    @pytest.mark.asyncio
    async def test_search_similar_with_graph_enabled_and_entities(self):
        """
        Test lines 385-396: search_similar with graph enabled and reference chunk has entities.
        """
        search = HybridSearch()

        reference_chunk_id = uuid4()

        # Similar chunks where first one has entities
        similar_chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Similar content with entities",
                similarity=0.88,
                document_id=uuid4(),
                document_title="Similar Doc 1",
                document_source="similar1.md",
                entities=["Entity A", "Entity B", "Entity C"],
            ),
            ChunkResult(
                chunk_id=uuid4(),
                content="Another similar content",
                similarity=0.82,
                document_id=uuid4(),
                document_title="Similar Doc 2",
                document_source="similar2.md",
                entities=["Entity D"],
            ),
        ]

        graph_results = GraphSearchResult(
            facts=[GraphFact("Related fact", None, 0.9, "chunk-1")],
            entities=[
                GraphEntity("e1", "Entity A", "company", ["chunk-1"]),
                GraphEntity("e2", "Entity B", "person", ["chunk-2"]),
            ],
            relationships=[],
        )

        with patch.object(search.config.performance, "enable_graph", True):
            with patch.object(search.vector_search, "search_similar_chunks") as mock_similar:
                mock_similar.return_value = similar_chunks

                with patch.object(search.graph_search, "search") as mock_graph:
                    mock_graph.return_value = graph_results

                    # This should execute lines 385-396
                    result = await search.search_similar(reference_chunk_id, limit=5)

                    # Verify graph search was called with entity query
                    mock_graph.assert_called_once()
                    # First 3 entities: "Entity A Entity B Entity C"
                    call_args = mock_graph.call_args[0][0]
                    assert "Entity A" in call_args

                    # Result should include graph data
                    assert isinstance(result, HybridSearchResult)
                    assert len(result.facts) > 0
                    assert len(result.entities) > 0
                    assert result.search_strategy == SearchStrategy.HYBRID
                    assert result.metadata["reference_chunk"] == str(reference_chunk_id)

    @pytest.mark.asyncio
    async def test_search_similar_with_single_entity(self):
        """
        Test lines 385-396: search_similar when reference chunk has only one entity.
        """
        search = HybridSearch()

        reference_chunk_id = uuid4()

        similar_chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Content with single entity",
                similarity=0.91,
                document_id=uuid4(),
                document_title="Single Entity Doc",
                document_source="single.md",
                entities=["SingleEntity"],
            )
        ]

        graph_results = GraphSearchResult(
            facts=[GraphFact("Single entity fact", None, 0.87, "chunk-1")],
            entities=[GraphEntity("e1", "SingleEntity", "organization", ["chunk-1"])],
        )

        with patch.object(search.config.performance, "enable_graph", True):
            with patch.object(search.vector_search, "search_similar_chunks") as mock_similar:
                mock_similar.return_value = similar_chunks

                with patch.object(search.graph_search, "search") as mock_graph:
                    mock_graph.return_value = graph_results

                    result = await search.search_similar(reference_chunk_id, limit=3)

                    mock_graph.assert_called_once()
                    assert result.search_strategy == SearchStrategy.HYBRID
                    assert len(result.facts) > 0

    @pytest.mark.asyncio
    async def test_search_similar_with_many_entities_uses_first_three(self):
        """
        Test lines 385-396: search_similar uses only first 3 entities for graph query.
        """
        search = HybridSearch()

        reference_chunk_id = uuid4()

        # Reference chunk with many entities
        similar_chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Content with many entities",
                similarity=0.94,
                document_id=uuid4(),
                document_title="Many Entities Doc",
                document_source="many.md",
                entities=["Entity1", "Entity2", "Entity3", "Entity4", "Entity5", "Entity6"],
            )
        ]

        graph_results = GraphSearchResult(
            facts=[GraphFact("Multi-entity fact", None, 0.92, "chunk-1")],
            entities=[GraphEntity(f"e{i}", f"Entity{i}", "type", []) for i in range(1, 4)],
        )

        with patch.object(search.config.performance, "enable_graph", True):
            with patch.object(search.vector_search, "search_similar_chunks") as mock_similar:
                mock_similar.return_value = similar_chunks

                with patch.object(search.graph_search, "search") as mock_graph:
                    mock_graph.return_value = graph_results

                    await search.search_similar(reference_chunk_id, limit=10)

                    # Should only use first 3 entities
                    mock_graph.assert_called_once()
                    call_args = mock_graph.call_args[0][0]
                    # Query should be "Entity1 Entity2 Entity3"
                    assert "Entity1" in call_args
                    assert "Entity2" in call_args
                    assert "Entity3" in call_args
                    # Entity4, Entity5, Entity6 should not be in query
                    assert "Entity4" not in call_args

    @pytest.mark.asyncio
    async def test_search_similar_graph_enabled_no_entities_in_reference(self):
        """
        Test lines 385-396: search_similar with graph enabled but no entities in reference chunk.
        """
        search = HybridSearch()

        reference_chunk_id = uuid4()

        # Reference chunk with NO entities
        similar_chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Content without entities",
                similarity=0.86,
                document_id=uuid4(),
                document_title="No Entity Doc",
                document_source="noentity.md",
                entities=[],  # Empty entities list
            )
        ]

        with patch.object(search.config.performance, "enable_graph", True):
            with patch.object(search.vector_search, "search_similar_chunks") as mock_similar:
                mock_similar.return_value = similar_chunks

                with patch.object(search.graph_search, "search") as mock_graph:
                    result = await search.search_similar(reference_chunk_id, limit=5)

                    # Graph search should NOT be called when no entities
                    mock_graph.assert_not_called()

                    # Should fallback to vector-only result
                    assert result.search_strategy == SearchStrategy.VECTOR_ONLY
                    assert len(result.facts) == 0

    @pytest.mark.asyncio
    async def test_search_similar_graph_disabled(self):
        """
        Test that search_similar doesn't execute lines 385-396 when graph is disabled.
        """
        search = HybridSearch()

        reference_chunk_id = uuid4()

        similar_chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Content with entities but graph disabled",
                similarity=0.89,
                document_id=uuid4(),
                document_title="Graph Disabled Doc",
                document_source="disabled.md",
                entities=["Entity X"],
            )
        ]

        with patch.object(search.config.performance, "enable_graph", False):
            with patch.object(search.vector_search, "search_similar_chunks") as mock_similar:
                mock_similar.return_value = similar_chunks

                with patch.object(search.graph_search, "search") as mock_graph:
                    result = await search.search_similar(reference_chunk_id, limit=5)

                    # Graph search should NOT be called when disabled
                    mock_graph.assert_not_called()

                    # Should return vector-only result
                    assert result.search_strategy == SearchStrategy.VECTOR_ONLY
                    assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_search_similar_empty_results(self):
        """
        Test search_similar when no similar chunks are found.
        """
        search = HybridSearch()

        reference_chunk_id = uuid4()

        with patch.object(search.config.performance, "enable_graph", True):
            with patch.object(search.vector_search, "search_similar_chunks") as mock_similar:
                mock_similar.return_value = []  # No similar chunks found

                with patch.object(search.graph_search, "search") as mock_graph:
                    result = await search.search_similar(reference_chunk_id, limit=5)

                    # Graph search should NOT be called when no results
                    mock_graph.assert_not_called()

                    # Should return empty vector-only result
                    assert result.search_strategy == SearchStrategy.VECTOR_ONLY
                    assert len(result.chunks) == 0


class TestEdgeCaseCombinations:
    """Additional edge cases to ensure comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_vector_only_search_preserves_chunk_order(self):
        """
        Test that _vector_only_search preserves the order of results from vector search.
        """
        search = HybridSearch()

        ordered_chunks = [
            ChunkResult(
                chunk_id=uuid4(),
                content=f"Ordered content {i}",
                similarity=1.0 - i * 0.05,  # Descending order
                document_id=uuid4(),
                document_title=f"Order Doc {i}",
                document_source=f"order{i}.md",
            )
            for i in range(10)
        ]

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = ordered_chunks

            result = await search._vector_only_search("ordered query", 10)

            # Verify order is preserved
            for i in range(len(result.chunks) - 1):
                assert result.chunks[i].similarity >= result.chunks[i + 1].similarity

    @pytest.mark.asyncio
    async def test_graph_only_search_no_chunk_refs(self):
        """
        Test graph-only search when graph results have no chunk references.
        """
        search = HybridSearch()

        mock_graph_result = GraphSearchResult(
            facts=[GraphFact("Fact without chunks", None, 0.88, None)],
            entities=[GraphEntity("e1", "Standalone Entity", "concept", [])],
            chunk_refs=[],  # No chunk refs
        )

        mock_intent = Mock(
            primary_intent=SearchIntent.GRAPH_HEAVY,
            entities_mentioned=["Standalone Entity"],
            temporal_markers=[],
            relationship_indicators=[],
        )

        with patch.object(search.graph_search, "search") as mock_graph:
            mock_graph.return_value = mock_graph_result

            with patch.object(search.vector_search, "get_chunks_by_ids") as mock_get_chunks:
                result = await search._graph_only_search("test query", 10, mock_intent)

                # get_chunks_by_ids should NOT be called when no chunk refs
                mock_get_chunks.assert_not_called()

                # Should still return graph data without chunks
                assert len(result.chunks) == 0
                assert len(result.facts) > 0
                assert len(result.entities) > 0

    @pytest.mark.asyncio
    async def test_all_strategy_paths_update_statistics(self):
        """
        Test that all strategy execution paths update statistics correctly.
        """
        search = HybridSearch()

        strategies_to_test = [
            SearchStrategy.VECTOR_ONLY,
            SearchStrategy.GRAPH_ONLY,
            SearchStrategy.HYBRID,
            SearchStrategy.ADAPTIVE,
        ]

        for strategy in strategies_to_test:
            initial_count = search._stats["strategies"][strategy.value]

            with patch.object(search.vector_search, "search") as mock_vector:
                mock_vector.return_value = []

                with patch.object(search.graph_search, "search") as mock_graph:
                    mock_graph.return_value = GraphSearchResult()

                    with patch.object(search.vector_search, "get_chunks_by_ids") as mock_get:
                        mock_get.return_value = []

                        await search.search("test", limit=5, strategy=strategy)

                        # Verify strategy count was incremented
                        assert search._stats["strategies"][strategy.value] == initial_count + 1

    @pytest.mark.asyncio
    async def test_search_similar_with_boosting_applied(self):
        """
        Test that search_similar applies boosting when graph context is available.
        """
        search = HybridSearch()

        reference_chunk_id = uuid4()
        chunk_id = uuid4()

        similar_chunks = [
            ChunkResult(
                chunk_id=chunk_id,
                content="Boostable content",
                similarity=0.7,  # Will be boosted
                document_id=uuid4(),
                document_title="Boost Doc",
                document_source="boost.md",
                entities=["BoostEntity"],
            )
        ]

        graph_results = GraphSearchResult(
            facts=[],
            entities=[GraphEntity("e1", "BoostEntity", "company", [str(chunk_id)])],
            chunk_refs=[str(chunk_id)],
        )

        initial_boost_count = search._stats["entity_boosts"]

        with patch.object(search.config.performance, "enable_graph", True):
            with patch.object(search.vector_search, "search_similar_chunks") as mock_similar:
                mock_similar.return_value = similar_chunks.copy()

                with patch.object(search.graph_search, "search") as mock_graph:
                    mock_graph.return_value = graph_results

                    result = await search.search_similar(reference_chunk_id, limit=5)

                    # Verify boosting was applied
                    assert result.chunks[0].similarity > 0.7
                    # Entity boost should have been applied
                    assert search._stats["entity_boosts"] > initial_boost_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
