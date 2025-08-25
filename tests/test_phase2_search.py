"""
Tests for Phase 2 search functionality.

Tests vector search, graph search, hybrid search, intent analysis,
and result ranking.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from src.agentic_rag.search import (
    ChunkResult,
    GraphSearch,
    GraphSearchResult,
    HybridSearch,
    HybridSearchResult,
    IntentAnalyzer,
    ResultRanker,
    SearchIntent,
    SearchStrategy,
    VectorSearch,
)
from src.agentic_rag.search.graph_search import GraphEntity, GraphFact, GraphRelationship
from src.agentic_rag.search.vector_search import SearchCache


class TestVectorSearch:
    """Test vector search functionality."""

    @pytest.mark.asyncio
    async def test_vector_search_basic(self):
        """Test basic vector search."""
        search = VectorSearch()

        # Mock components
        with patch.object(search.embedder, "embed") as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch.object(search, "_search_vectors") as mock_search:
                mock_search.return_value = [
                    ChunkResult(
                        chunk_id=UUID("12345678-1234-5678-1234-567812345678"),
                        content="Test content",
                        similarity=0.9,
                        document_id=UUID("87654321-4321-8765-4321-876543218765"),
                        document_title="Test Doc",
                        document_source="test.md",
                    )
                ]

                results = await search.search("test query", limit=10)

                assert len(results) == 1
                assert results[0].similarity == 0.9
                assert results[0].content == "Test content"

    @pytest.mark.asyncio
    async def test_search_cache_functionality(self):
        """Test search result caching."""
        cache = SearchCache(ttl_seconds=60)

        # Create test results
        results = [
            ChunkResult(
                chunk_id=UUID("12345678-1234-5678-1234-567812345678"),
                content="Test",
                similarity=0.9,
                document_id=UUID("87654321-4321-8765-4321-876543218765"),
                document_title="Test",
                document_source="test.md",
            )
        ]

        # Test cache operations
        key = cache.generate_key([0.1] * 10, {"test": "filter"})

        assert cache.get(key) is None
        cache.set(key, results)
        assert cache.get(key) == results

        # Test TTL
        cache._cache[key] = (datetime.now() - timedelta(seconds=120), results)
        assert cache.get(key) is None  # Should be expired

    @pytest.mark.asyncio
    async def test_similarity_search(self):
        """Test finding similar chunks."""
        search = VectorSearch()

        chunk_id = UUID("12345678-1234-5678-1234-567812345678")

        with patch.object(search.connection_manager, "get_pg_connection") as mock_conn:
            # Mock context manager
            mock_conn.return_value.__aenter__ = AsyncMock()
            mock_conn.return_value.__aexit__ = AsyncMock()

            # Mock fetchrow
            mock_conn.return_value.__aenter__.return_value.fetchrow = AsyncMock(
                return_value={
                    "content": "Test content",
                    "embedding_1536": [0.1] * 1536,
                    "embedding_768": None,
                }
            )

            with patch.object(search, "_search_vectors") as mock_search:
                mock_search.return_value = []

                results = await search.search_similar_chunks(chunk_id, limit=5)

                assert isinstance(results, list)


class TestGraphSearch:
    """Test graph search functionality."""

    @pytest.mark.asyncio
    async def test_graph_search_facts(self):
        """Test searching for facts."""
        search = GraphSearch()

        with patch.object(search.graphiti_client, "search") as mock_search:
            mock_search.return_value = [
                {
                    "fact": "Microsoft invested $10B in OpenAI",
                    "timestamp": datetime.now(),
                    "confidence": 0.9,
                    "source_chunk": "chunk-123",
                    "entities": ["Microsoft", "OpenAI"],
                }
            ]

            with patch.object(search, "_search_entities") as mock_entities:
                mock_entities.return_value = []

                with patch.object(search, "_search_relationships") as mock_rels:
                    mock_rels.return_value = []

                    result = await search.search("Microsoft OpenAI investment")

                    assert len(result.facts) == 1
                    assert result.facts[0].fact == "Microsoft invested $10B in OpenAI"
                    assert result.facts[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_entity_timeline(self):
        """Test entity timeline retrieval."""
        search = GraphSearch()

        with patch.object(search.neo4j_store, "execute_query") as mock_query:
            mock_query.return_value = [{"entity_id": "entity-123"}]

            with patch.object(search.graphiti_client, "get_entity_timeline") as mock_timeline:
                mock_timeline.return_value = [
                    {
                        "fact": "Founded in 2015",
                        "timestamp": datetime(2015, 1, 1),
                        "confidence": 0.95,
                        "source_chunk": "chunk-1",
                    },
                    {
                        "fact": "Raised $1B in 2019",
                        "timestamp": datetime(2019, 1, 1),
                        "confidence": 0.9,
                        "source_chunk": "chunk-2",
                    },
                ]

                timeline = await search.find_entity_timeline("OpenAI", limit=10)

                assert len(timeline) == 2
                assert timeline[0].fact == "Founded in 2015"
                assert timeline[1].fact == "Raised $1B in 2019"

    def test_chunk_ref_extraction(self):
        """Test extraction of chunk references."""
        search = GraphSearch()

        facts = [
            GraphFact(fact="Test fact", timestamp=None, confidence=0.8, source_chunk="chunk-1")
        ]

        entities = [
            GraphEntity(
                id="entity-1", name="Test Entity", type="company", chunk_refs=["chunk-2", "chunk-3"]
            )
        ]

        relationships = [
            GraphRelationship(
                source="Entity1",
                target="Entity2",
                type="related",
                confidence=0.7,
                properties={"source_chunk": "chunk-4"},
            )
        ]

        refs = search._extract_chunk_refs(facts, entities, relationships)

        assert "chunk-1" in refs
        assert "chunk-2" in refs
        assert "chunk-3" in refs
        assert "chunk-4" in refs


class TestIntentAnalysis:
    """Test query intent analysis."""

    def test_relationship_intent(self):
        """Test detection of relationship-focused queries."""
        analyzer = IntentAnalyzer()

        queries = [
            "How is Microsoft related to OpenAI?",
            "Who founded Anthropic?",
            "What companies has Google acquired?",
            "Show me partnerships between tech companies",
        ]

        for query in queries:
            result = analyzer.analyze(query)
            assert len(result.relationship_indicators) > 0
            assert result.primary_intent in [
                SearchIntent.GRAPH_HEAVY,
                SearchIntent.HYBRID,
                SearchIntent.ENTITY_FOCUSED,
            ]

    def test_temporal_intent(self):
        """Test detection of temporal queries."""
        analyzer = IntentAnalyzer()

        queries = [
            "Show me the timeline of OpenAI's development",
            "What happened in 2023?",
            "History of AI investments",
            "When did Microsoft invest in OpenAI?",
        ]

        for query in queries:
            result = analyzer.analyze(query)
            assert len(result.temporal_markers) > 0

    def test_entity_extraction(self):
        """Test entity extraction from queries."""
        analyzer = IntentAnalyzer()

        query = "Tell me about OpenAI, Microsoft, and Google's AI strategies"
        result = analyzer.analyze(query)

        assert "OpenAI" in result.entities_mentioned
        assert "Microsoft" in result.entities_mentioned
        assert "Google" in result.entities_mentioned

    def test_vector_intent(self):
        """Test detection of content-focused queries."""
        analyzer = IntentAnalyzer()

        queries = [
            "Explain how transformers work",
            "Describe the architecture of GPT",
            "Summary of recent AI developments",
        ]

        for query in queries:
            result = analyzer.analyze(query)
            # Should lean toward vector search for content
            assert result.primary_intent in [SearchIntent.VECTOR_HEAVY, SearchIntent.HYBRID]


class TestHybridSearch:
    """Test hybrid search orchestration."""

    @pytest.mark.asyncio
    async def test_strategy_selection(self):
        """Test search strategy selection based on intent."""
        search = HybridSearch()

        with patch.object(search.intent_analyzer, "analyze") as mock_analyze:
            # Test vector-heavy intent
            mock_analyze.return_value = Mock(
                primary_intent=SearchIntent.VECTOR_HEAVY,
                entities_mentioned=[],
                temporal_markers=[],
                relationship_indicators=[],
            )

            with patch.object(search, "_vector_only_search") as mock_vector:
                mock_vector.return_value = HybridSearchResult()

                result = await search.search("explain transformers", limit=10)

                assert result.search_strategy == SearchStrategy.VECTOR_ONLY
                mock_vector.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_search_execution(self):
        """Test parallel execution of vector and graph search."""
        search = HybridSearch()

        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = []

            with patch.object(search.graph_search, "search") as mock_graph:
                mock_graph.return_value = GraphSearchResult()

                with patch.object(search.intent_analyzer, "analyze") as mock_analyze:
                    mock_analyze.return_value = Mock(
                        primary_intent=SearchIntent.HYBRID,
                        entities_mentioned=["TestEntity"],
                        temporal_markers=[],
                        relationship_indicators=[],
                    )

                    await search.search("test query", strategy=SearchStrategy.HYBRID)

                    # Both searches should be called
                    mock_vector.assert_called()
                    mock_graph.assert_called()

    @pytest.mark.asyncio
    async def test_result_boosting(self):
        """Test boosting of results based on graph context."""
        search = HybridSearch()

        # Create test chunks
        chunks = [
            ChunkResult(
                chunk_id=UUID("12345678-1234-5678-1234-567812345678"),
                content="Content about Entity1",
                similarity=0.7,
                document_id=UUID("87654321-4321-8765-4321-876543218765"),
                document_title="Doc1",
                document_source="doc1.md",
                entities=["Entity1"],
            ),
            ChunkResult(
                chunk_id=UUID("22345678-1234-5678-1234-567812345678"),
                content="Content about Entity2",
                similarity=0.6,
                document_id=UUID("87654321-4321-8765-4321-876543218765"),
                document_title="Doc2",
                document_source="doc2.md",
                entities=["Entity2"],
            ),
        ]

        # Create graph results with Entity1
        graph_results = GraphSearchResult(
            entities=[
                GraphEntity(
                    id="e1",
                    name="Entity1",
                    type="company",
                    chunk_refs=["12345678-1234-5678-1234-567812345678"],
                )
            ],
            chunk_refs=["12345678-1234-5678-1234-567812345678"],
        )

        # Apply boosting
        boosted = await search._boost_with_graph_context(chunks, graph_results, None)

        # First chunk should be boosted
        assert boosted[0].similarity > 0.7  # Should be boosted
        assert boosted[0].chunk_id == UUID("12345678-1234-5678-1234-567812345678")


class TestResultRanking:
    """Test result ranking functionality."""

    def test_multi_factor_ranking(self):
        """Test multi-factor result ranking."""
        ranker = ResultRanker()

        # Create test chunks with varying scores
        chunks = [
            Mock(
                chunk_id="1",
                content="High similarity content",
                similarity=0.9,
                entities=["Entity1"],
                document_source="official_docs",
                metadata={},
            ),
            Mock(
                chunk_id="2",
                content="Medium similarity with entities",
                similarity=0.7,
                entities=["Entity1", "Entity2"],
                document_source="research_paper",
                metadata={},
            ),
            Mock(
                chunk_id="3",
                content="Low similarity recent content",
                similarity=0.5,
                entities=[],
                document_source="news_article",
                metadata={"created_at": datetime.now().isoformat()},
            ),
        ]

        # Rank with entity overlap
        ranked = ranker.rank_chunks(chunks, limit=3, query_entities=["Entity1", "Entity2"])

        assert len(ranked) == 3
        # First result should have good combined score
        assert ranked[0].chunk_id in ["1", "2"]

    def test_diversity_enforcement(self):
        """Test result diversity enforcement."""
        ranker = ResultRanker()

        # Create chunks from same document
        chunks = [
            Mock(
                chunk_id=f"chunk-{i}",
                content=f"Content part {i}",
                similarity=0.9 - i * 0.05,
                document_id="doc-1",
                entities=[],
                document_source="test.md",
                metadata={},
            )
            for i in range(5)
        ]

        # Add chunks from different document
        chunks.extend(
            [
                Mock(
                    chunk_id="chunk-other",
                    content="Different content",
                    similarity=0.7,
                    document_id="doc-2",
                    entities=[],
                    document_source="other.md",
                    metadata={},
                )
            ]
        )

        ranked = ranker.rank_chunks(chunks, limit=4)

        # Should include chunk from different document for diversity
        doc_ids = [getattr(c, "document_id", None) for c in ranked]
        assert "doc-2" in doc_ids

    def test_temporal_relevance_scoring(self):
        """Test temporal relevance in ranking."""
        ranker = ResultRanker()

        now = datetime.now()

        chunks = [
            Mock(
                chunk_id="old",
                content="Old content",
                similarity=0.8,
                entities=[],
                document_source="test.md",
                metadata={"created_at": (now - timedelta(days=365)).isoformat()},
            ),
            Mock(
                chunk_id="recent",
                content="Recent content",
                similarity=0.75,
                entities=[],
                document_source="test.md",
                metadata={"created_at": now.isoformat()},
            ),
        ]

        # Rank with temporal context
        ranker.rank_chunks(chunks, limit=2, temporal_context=now)

        # Recent content might rank higher despite lower similarity
        stats = ranker.get_stats()
        assert stats["temporal_boosts"] > 0

    def test_reranking_with_feedback(self):
        """Test re-ranking based on user feedback."""
        ranker = ResultRanker()

        chunks = [
            Mock(chunk_id="1", similarity=0.7),
            Mock(chunk_id="2", similarity=0.8),
            Mock(chunk_id="3", similarity=0.6),
        ]

        # Apply feedback
        reranked = ranker.rerank_with_feedback(
            chunks,
            positive_examples=["3"],  # Boost chunk 3
            negative_examples=["2"],  # Penalize chunk 2
        )

        # Chunk 3 should be boosted
        chunk3 = next(c for c in reranked if c.chunk_id == "3")
        assert chunk3.similarity > 0.6


class TestIntegration:
    """Integration tests for search components."""

    @pytest.mark.asyncio
    async def test_end_to_end_search_flow(self):
        """Test complete search flow from query to ranked results."""
        # Initialize hybrid search
        search = HybridSearch()

        # Mock all external dependencies
        with patch.object(search.vector_search, "search") as mock_vector:
            mock_vector.return_value = [
                ChunkResult(
                    chunk_id=UUID("12345678-1234-5678-1234-567812345678"),
                    content="Microsoft invested heavily in OpenAI",
                    similarity=0.85,
                    document_id=UUID("87654321-4321-8765-4321-876543218765"),
                    document_title="AI Investments",
                    document_source="investments.md",
                    entities=["Microsoft", "OpenAI"],
                )
            ]

            with patch.object(search.graph_search, "search") as mock_graph:
                mock_graph.return_value = GraphSearchResult(
                    facts=[
                        GraphFact(
                            fact="Microsoft invested $10B in OpenAI in 2023",
                            timestamp=datetime(2023, 1, 1),
                            confidence=0.95,
                            source_chunk="12345678-1234-5678-1234-567812345678",
                        )
                    ],
                    entities=[
                        GraphEntity(
                            id="e1",
                            name="Microsoft",
                            type="company",
                            chunk_refs=["12345678-1234-5678-1234-567812345678"],
                        )
                    ],
                )

                # Execute search
                result = await search.search("How much did Microsoft invest in OpenAI?", limit=10)

                # Verify results
                assert len(result.chunks) > 0
                assert len(result.facts) > 0
                assert result.search_strategy in [
                    SearchStrategy.HYBRID,
                    SearchStrategy.ADAPTIVE,
                    SearchStrategy.GRAPH_ONLY,
                ]

                # Check that relevant content was found
                if result.chunks:
                    assert "Microsoft" in result.chunks[0].content
                if result.facts:
                    assert "$10B" in result.facts[0].fact or "Microsoft" in result.facts[0].fact


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
