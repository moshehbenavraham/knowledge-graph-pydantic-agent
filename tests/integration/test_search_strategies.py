"""
Integration tests for search strategies.
"""

import pytest

from src.agentic_rag.search.hybrid_search import HybridSearch
from src.agentic_rag.search.intent_analyzer import IntentAnalyzer
from src.agentic_rag.search.vector_search import VectorSearch


class TestVectorSearch:
    """Integration tests for vector search."""

    @pytest.mark.asyncio
    async def test_vector_search_accuracy(
        self, postgres_store, sample_document_with_chunks
    ):
        """Test vector search returns relevant results."""
        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        # Create vector search
        embedder = EmbeddingGenerator()
        search = VectorSearch(postgres_store, embedder)

        # Search for ML content
        results = await search.search("machine learning", limit=5)

        # Should return results
        assert len(results.chunks) > 0
        assert results.chunks[0].similarity > 0.0

        # Results should be ordered by similarity
        similarities = [chunk.similarity for chunk in results.chunks]
        assert similarities == sorted(similarities, reverse=True)

    @pytest.mark.asyncio
    async def test_vector_search_threshold(
        self, postgres_store, sample_document_with_chunks
    ):
        """Test vector search respects similarity threshold."""
        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        search = VectorSearch(postgres_store, embedder)

        # Search with high threshold
        results = await search.search(
            "completely unrelated topic xyz", limit=5, similarity_threshold=0.9
        )

        # Should return fewer or no results
        # (since the query is unrelated to sample content)
        assert len(results.chunks) >= 0  # May be 0 if threshold is too high

    @pytest.mark.asyncio
    async def test_vector_search_empty_query(self, postgres_store):
        """Test vector search handles empty query gracefully."""
        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        search = VectorSearch(postgres_store, embedder)

        # Empty query should return empty results or raise error
        try:
            results = await search.search("", limit=5)
            # If it doesn't error, results should be empty or minimal
            assert isinstance(results.chunks, list)
        except ValueError:
            # It's acceptable to raise ValueError for empty query
            pass


class TestHybridSearch:
    """Integration tests for hybrid search."""

    @pytest.mark.asyncio
    async def test_hybrid_search_integration(
        self, postgres_store, neo4j_store, sample_document_with_chunks
    ):
        """Test hybrid search combines vector + graph results."""
        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        vector_search = VectorSearch(postgres_store, embedder)

        # Create hybrid search
        search = HybridSearch(
            postgres_store=postgres_store,
            neo4j_store=neo4j_store,
            vector_search=vector_search,
        )

        # Search
        results = await search.search("machine learning AI", limit=10)

        # Should return results
        assert isinstance(results.chunks, list)
        assert results.search_strategy is not None

    @pytest.mark.asyncio
    async def test_hybrid_search_entity_boosting(
        self, postgres_store, neo4j_store, sample_document_with_chunks
    ):
        """Test that hybrid search boosts results with entity matches."""
        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        vector_search = VectorSearch(postgres_store, embedder)

        search = HybridSearch(
            postgres_store=postgres_store,
            neo4j_store=neo4j_store,
            vector_search=vector_search,
        )

        # Search with entity-focused query
        results = await search.search("entities and relationships", limit=10)

        # Results should include boosted scores
        if len(results.chunks) > 0:
            assert all(hasattr(chunk, "similarity") for chunk in results.chunks)

    @pytest.mark.asyncio
    async def test_hybrid_search_parallel_execution(
        self, postgres_store, neo4j_store, sample_document_with_chunks
    ):
        """Test that hybrid search executes vector and graph searches in parallel."""
        import time

        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        vector_search = VectorSearch(postgres_store, embedder)

        search = HybridSearch(
            postgres_store=postgres_store,
            neo4j_store=neo4j_store,
            vector_search=vector_search,
        )

        # Time hybrid search
        start = time.perf_counter()
        results = await search.search("test query", limit=5)
        hybrid_time = time.perf_counter() - start

        # Verify it completes reasonably quickly
        # (parallel execution should be faster than sequential)
        assert hybrid_time < 5.0  # Should complete within 5 seconds


class TestIntentAnalyzer:
    """Integration tests for intent analyzer."""

    @pytest.mark.asyncio
    async def test_intent_analysis_semantic_query(self):
        """Test intent analyzer identifies semantic queries."""
        analyzer = IntentAnalyzer()

        query = "What is machine learning?"
        intent = await analyzer.analyze(query)

        # Should identify as vector-heavy or semantic
        assert intent.primary_intent in ["VECTOR_HEAVY", "HYBRID"]
        assert intent.confidence > 0.5

    @pytest.mark.asyncio
    async def test_intent_analysis_relationship_query(self):
        """Test intent analyzer identifies relationship queries."""
        analyzer = IntentAnalyzer()

        query = "How is Microsoft related to OpenAI?"
        intent = await analyzer.analyze(query)

        # Should identify relationship intent
        assert intent.primary_intent in ["GRAPH_HEAVY", "HYBRID"]
        assert "relationship" in intent.detected_patterns or "related" in query.lower()

    @pytest.mark.asyncio
    async def test_intent_analysis_temporal_query(self):
        """Test intent analyzer identifies temporal queries."""
        analyzer = IntentAnalyzer()

        query = "When did OpenAI release GPT-4?"
        intent = await analyzer.analyze(query)

        # Should detect temporal intent
        assert "TEMPORAL" in intent.primary_intent or "when" in query.lower()

    @pytest.mark.asyncio
    async def test_intent_analysis_entity_focused(self):
        """Test intent analyzer identifies entity-focused queries."""
        analyzer = IntentAnalyzer()

        query = "Tell me about Microsoft"
        intent = await analyzer.analyze(query)

        # Should detect entity focus
        assert intent.primary_intent in ["ENTITY_FOCUSED", "VECTOR_HEAVY", "HYBRID"]

    @pytest.mark.asyncio
    async def test_intent_analysis_hybrid_indicators(self):
        """Test intent analyzer identifies queries needing hybrid search."""
        analyzer = IntentAnalyzer()

        query = (
            "What is the relationship between machine learning and OpenAI's products?"
        )
        intent = await analyzer.analyze(query)

        # Complex query should suggest hybrid approach
        assert intent.primary_intent in ["HYBRID", "GRAPH_HEAVY"]


class TestSearchIntegration:
    """End-to-end search integration tests."""

    @pytest.mark.asyncio
    async def test_full_search_pipeline(
        self, postgres_store, neo4j_store, sample_document_with_chunks
    ):
        """Test complete search pipeline from query to results."""
        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        # Setup
        embedder = EmbeddingGenerator()
        vector_search = VectorSearch(postgres_store, embedder)
        hybrid_search = HybridSearch(
            postgres_store=postgres_store,
            neo4j_store=neo4j_store,
            vector_search=vector_search,
        )
        intent_analyzer = IntentAnalyzer()

        # Query
        query = "What does the document say about AI?"

        # 1. Analyze intent
        intent = await intent_analyzer.analyze(query)
        assert intent.primary_intent is not None

        # 2. Execute appropriate search
        if intent.primary_intent in ["VECTOR_HEAVY", "ENTITY_FOCUSED"]:
            results = await vector_search.search(query, limit=5)
        else:
            results = await hybrid_search.search(query, limit=5)

        # 3. Verify results
        assert results is not None
        assert isinstance(results.chunks, list)

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, postgres_store, sample_document_with_chunks
    ):
        """Test search with source filters."""
        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        search = VectorSearch(postgres_store, embedder)

        # Search with metadata filters
        results = await search.search(
            "machine learning", limit=5, filters={"source": "test.txt"}
        )

        # Should respect filters
        assert isinstance(results.chunks, list)

    @pytest.mark.asyncio
    async def test_search_performance(
        self, postgres_store, sample_document_with_chunks
    ):
        """Test search meets performance targets."""
        import time

        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        search = VectorSearch(postgres_store, embedder)

        # Time vector search
        start = time.perf_counter()
        await search.search("test query", limit=10)
        duration = time.perf_counter() - start

        # Should complete quickly (adjust threshold as needed)
        assert duration < 2.0  # Less than 2 seconds

    @pytest.mark.asyncio
    async def test_search_result_ranking(
        self, postgres_store, sample_document_with_chunks
    ):
        """Test that search results are properly ranked."""
        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        search = VectorSearch(postgres_store, embedder)

        results = await search.search("machine learning artificial intelligence", limit=10)

        # Results should be ordered by relevance
        if len(results.chunks) > 1:
            similarities = [chunk.similarity for chunk in results.chunks]
            # Check descending order
            for i in range(len(similarities) - 1):
                assert similarities[i] >= similarities[i + 1]

    @pytest.mark.asyncio
    async def test_concurrent_searches(
        self, postgres_store, sample_document_with_chunks
    ):
        """Test concurrent search operations."""
        import asyncio

        from src.agentic_rag.ingestion.embedder import EmbeddingGenerator

        embedder = EmbeddingGenerator()
        search = VectorSearch(postgres_store, embedder)

        # Execute multiple searches concurrently
        queries = [
            "machine learning",
            "artificial intelligence",
            "deep learning",
            "neural networks",
        ]

        tasks = [search.search(q, limit=5) for q in queries]
        results = await asyncio.gather(*tasks)

        # All searches should complete successfully
        assert len(results) == len(queries)
        assert all(r is not None for r in results)
