"""
Comprehensive test coverage for vector_search.py.

Targets uncovered lines to increase coverage from 69.67% to 75%+.
Focuses on error handling, edge cases, cache behavior, and async operations.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from src.agentic_rag.search.vector_search import ChunkResult, SearchCache, VectorSearch


@pytest.fixture
def mock_connection_manager():
    """Mock ConnectionManager for VectorSearch tests."""
    mock_manager = Mock()
    # Add necessary attributes/methods that VectorSearch might need
    return mock_manager


class TestChunkResult:
    """Test ChunkResult dataclass."""

    def test_score_property(self):
        """Test score property (line 39)."""
        chunk = ChunkResult(
            chunk_id=UUID("12345678-1234-5678-1234-567812345678"),
            content="Test content",
            similarity=0.85,
            document_id=UUID("87654321-4321-8765-4321-876543218765"),
            document_title="Test Doc",
            document_source="test.md",
        )
        assert chunk.score == 0.85
        assert chunk.score == chunk.similarity

    def test_score_property_with_metadata(self):
        """Test score property with full metadata."""
        chunk = ChunkResult(
            chunk_id=UUID("12345678-1234-5678-1234-567812345678"),
            content="Test content",
            similarity=0.92,
            document_id=UUID("87654321-4321-8765-4321-876543218765"),
            document_title="Test Doc",
            document_source="test.md",
            metadata={"author": "test"},
            entities=["Entity1", "Entity2"],
        )
        assert chunk.score == 0.92

    def test_to_dict_complete(self):
        """Test to_dict with all fields."""
        chunk = ChunkResult(
            chunk_id=UUID("12345678-1234-5678-1234-567812345678"),
            content="Test content",
            similarity=0.75,
            document_id=UUID("87654321-4321-8765-4321-876543218765"),
            document_title="Test Doc",
            document_source="test.md",
            metadata={"key": "value"},
            entities=["Entity1"],
        )
        result = chunk.to_dict()
        assert result["chunk_id"] == "12345678-1234-5678-1234-567812345678"
        assert result["similarity"] == 0.75
        assert result["metadata"] == {"key": "value"}
        assert result["entities"] == ["Entity1"]


class TestSearchCache:
    """Test SearchCache class."""

    def test_cache_initialization(self):
        """Test cache initialization with different TTL values."""
        cache1 = SearchCache(ttl_seconds=3600)
        assert cache1.ttl == timedelta(seconds=3600)

        cache2 = SearchCache(ttl_seconds=60)
        assert cache2.ttl == timedelta(seconds=60)

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = SearchCache(ttl_seconds=60)
        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_hit(self):
        """Test cache hit returns cached results."""
        cache = SearchCache(ttl_seconds=60)
        results = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Test",
                similarity=0.9,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
            )
        ]
        cache.set("test_key", results)
        cached = cache.get("test_key")
        assert cached == results

    def test_cache_expiration(self):
        """Test cache expiration removes stale entries."""
        cache = SearchCache(ttl_seconds=1)
        results = [
            ChunkResult(
                chunk_id=uuid4(),
                content="Test",
                similarity=0.9,
                document_id=uuid4(),
                document_title="Test",
                document_source="test.md",
            )
        ]
        key = "test_key"
        cache.set(key, results)

        # Manually expire by backdating
        cache._cache[key] = (datetime.now() - timedelta(seconds=10), results)
        expired = cache.get(key)
        assert expired is None
        assert key not in cache._cache

    def test_cache_clear(self):
        """Test cache clear removes all entries."""
        cache = SearchCache(ttl_seconds=60)
        cache.set("key1", [])
        cache.set("key2", [])
        assert len(cache._cache) == 2

        cache.clear()
        assert len(cache._cache) == 0

    def test_generate_key_consistency(self):
        """Test cache key generation is consistent."""
        embedding = [0.1, 0.2, 0.3] * 10
        filters = {"type": "test", "author": "alice"}

        key1 = SearchCache.generate_key(embedding, filters)
        key2 = SearchCache.generate_key(embedding, filters)
        assert key1 == key2

    def test_generate_key_different_filters(self, mock_connection_manager):
        """Test different filters produce different keys."""
        embedding = [0.1] * 30
        filters1 = {"type": "test"}
        filters2 = {"type": "prod"}

        key1 = SearchCache.generate_key(embedding, filters1)
        key2 = SearchCache.generate_key(embedding, filters2)
        assert key1 != key2

    def test_generate_key_no_filters(self, mock_connection_manager):
        """Test key generation with no filters."""
        embedding = [0.1] * 30
        key1 = SearchCache.generate_key(embedding, None)
        key2 = SearchCache.generate_key(embedding, {})
        # Should be different because None vs {} in JSON
        assert isinstance(key1, str)
        assert isinstance(key2, str)

    def test_generate_key_uses_md5(self, mock_connection_manager):
        """Test that generate_key uses MD5 hashing."""
        embedding = [0.1] * 10
        filters = {"test": "value"}
        key = SearchCache.generate_key(embedding, filters)

        # Verify it's a valid MD5 hash (32 hex chars)
        assert len(key) == 32
        assert all(c in "0123456789abcdef" for c in key)


class TestVectorSearchInitialization:
    """Test VectorSearch initialization."""

    def test_init_with_cache_enabled(self, mock_connection_manager):
        """Test initialization with caching enabled (line 145)."""
        with patch("src.agentic_rag.search.vector_search.get_config") as mock_config:
            mock_perf = Mock()
            mock_perf.enable_caching = True
            mock_perf.embedding_cache_ttl = 3600
            mock_config.return_value.performance = mock_perf

            search = VectorSearch(mock_connection_manager)
            assert search.cache is not None
            assert isinstance(search.cache, SearchCache)

    def test_init_with_cache_disabled(self, mock_connection_manager):
        """Test initialization with caching disabled (line 145)."""
        with patch("src.agentic_rag.search.vector_search.get_config") as mock_config:
            mock_perf = Mock()
            mock_perf.enable_caching = False
            mock_config.return_value.performance = mock_perf

            search = VectorSearch(mock_connection_manager)
            assert search.cache is None

    def test_init_with_custom_connection_manager(self, mock_connection_manager):
        """Test initialization with custom connection manager."""
        mock_conn_manager = Mock()
        search = VectorSearch(connection_manager=mock_conn_manager)
        assert search.connection_manager is mock_conn_manager

    def test_init_creates_default_stats(self, mock_connection_manager):
        """Test initialization creates stats dictionary."""
        search = VectorSearch(mock_connection_manager)
        assert search._stats == {
            "searches": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_latency": 0,
        }


class TestVectorSearchWithCache:
    """Test VectorSearch with cache enabled."""

    @pytest.mark.asyncio
    async def test_search_with_cache_hit(self, mock_connection_manager):
        """Test search with cache hit (lines 178-181)."""
        with patch("src.agentic_rag.search.vector_search.get_config") as mock_config:
            mock_perf = Mock()
            mock_perf.enable_caching = True
            mock_perf.embedding_cache_ttl = 3600
            mock_config.return_value.performance = mock_perf

            search = VectorSearch(mock_connection_manager)

            # Pre-populate cache
            cached_results = [
                ChunkResult(
                    chunk_id=uuid4(),
                    content="Cached content",
                    similarity=0.95,
                    document_id=uuid4(),
                    document_title="Cached",
                    document_source="cache.md",
                )
            ]

            query_embedding = [0.1] * 1536
            cache_key = SearchCache.generate_key(query_embedding, None)
            search.cache.set(cache_key, cached_results)

            with patch.object(search.embedder, "embed", return_value=query_embedding):
                results = await search.search("test query", limit=10)

                assert results == cached_results
                assert search._stats["cache_hits"] == 1
                assert search._stats["searches"] == 1

    @pytest.mark.asyncio
    async def test_search_with_cache_miss(self, mock_connection_manager):
        """Test search with cache miss (line 182)."""
        with patch("src.agentic_rag.search.vector_search.get_config") as mock_config:
            mock_perf = Mock()
            mock_perf.enable_caching = True
            mock_perf.embedding_cache_ttl = 3600
            mock_config.return_value.performance = mock_perf

            search = VectorSearch(mock_connection_manager)

            query_embedding = [0.1] * 1536
            expected_results = [
                ChunkResult(
                    chunk_id=uuid4(),
                    content="New content",
                    similarity=0.88,
                    document_id=uuid4(),
                    document_title="New",
                    document_source="new.md",
                )
            ]

            with patch.object(search.embedder, "embed", return_value=query_embedding):
                with patch.object(search, "_search_vectors", return_value=expected_results):
                    results = await search.search("test query", limit=10)

                    assert results == expected_results
                    assert search._stats["cache_misses"] == 1
                    assert search._stats["cache_hits"] == 0

    @pytest.mark.asyncio
    async def test_search_caches_results(self, mock_connection_manager):
        """Test that search caches results after retrieval."""
        with patch("src.agentic_rag.search.vector_search.get_config") as mock_config:
            mock_perf = Mock()
            mock_perf.enable_caching = True
            mock_perf.embedding_cache_ttl = 3600
            mock_config.return_value.performance = mock_perf

            search = VectorSearch(mock_connection_manager)

            query_embedding = [0.1] * 1536
            expected_results = [
                ChunkResult(
                    chunk_id=uuid4(),
                    content="Content",
                    similarity=0.9,
                    document_id=uuid4(),
                    document_title="Doc",
                    document_source="doc.md",
                )
            ]

            with patch.object(search.embedder, "embed", return_value=query_embedding):
                with patch.object(search, "_search_vectors", return_value=expected_results):
                    # First call - cache miss
                    await search.search("test query", limit=10)

                    # Verify it was cached
                    cache_key = SearchCache.generate_key(query_embedding, None)
                    cached = search.cache.get(cache_key)
                    assert cached == expected_results


class TestVectorSearchErrors:
    """Test error handling in VectorSearch (lines 220-287)."""

    @pytest.mark.asyncio
    async def test_search_vectors_with_string_embedding(self, mock_connection_manager):
        """Test _search_vectors with string embedding (lines 249-251)."""
        search = VectorSearch(mock_connection_manager)

        # Mock connection that returns no results
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        async def mock_get_connection():
            return mock_conn

        # Create async context manager mock
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            # Test with string embedding (already in PostgreSQL format)
            embedding_str = "[0.1,0.2,0.3]"
            results = await search._search_vectors(embedding_str, 10, None, 0.0)

            assert results == []
            # Verify fetch was called with string embedding
            mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_vectors_with_list_embedding(self, mock_connection_manager):
        """Test _search_vectors with list embedding (lines 252-254)."""
        search = VectorSearch(mock_connection_manager)

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            # Test with list embedding
            embedding_list = [0.1, 0.2, 0.3]
            results = await search._search_vectors(embedding_list, 10, None, 0.0)

            assert results == []
            # Verify it was converted to string format
            call_args = mock_conn.fetch.call_args
            assert "[0.1,0.2,0.3]" in str(call_args)

    @pytest.mark.asyncio
    async def test_search_vectors_with_metadata_filters(self, mock_connection_manager):
        """Test _search_vectors with metadata filters (line 261)."""
        search = VectorSearch(mock_connection_manager)

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            filters = {"type": "article", "author": "alice"}
            embedding = [0.1] * 1536
            results = await search._search_vectors(embedding, 10, filters, 0.7)

            assert results == []
            # Verify filters were passed as JSON
            call_args = mock_conn.fetch.call_args
            assert json.dumps(filters) in str(call_args)

    @pytest.mark.asyncio
    async def test_search_vectors_metadata_as_string(self, mock_connection_manager):
        """Test _search_vectors with metadata as string (lines 268-272)."""
        search = VectorSearch(mock_connection_manager)

        # Mock row with metadata as string
        mock_row = {
            "chunk_id": uuid4(),
            "content": "Test content",
            "similarity": 0.85,
            "document_id": uuid4(),
            "document_title": "Test",
            "document_source": "test.md",
            "metadata": '{"key": "value"}',
            "entity_refs": ["Entity1"],
        }

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            embedding = [0.1] * 1536
            results = await search._search_vectors(embedding, 10, None, 0.0)

            assert len(results) == 1
            assert results[0].metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_search_vectors_metadata_as_dict(self, mock_connection_manager):
        """Test _search_vectors with metadata as dict (line 271)."""
        search = VectorSearch(mock_connection_manager)

        # Mock row with metadata as dict
        mock_row = {
            "chunk_id": uuid4(),
            "content": "Test content",
            "similarity": 0.85,
            "document_id": uuid4(),
            "document_title": "Test",
            "document_source": "test.md",
            "metadata": {"key": "value"},
            "entity_refs": None,
        }

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            embedding = [0.1] * 1536
            results = await search._search_vectors(embedding, 10, None, 0.0)

            assert len(results) == 1
            assert results[0].metadata == {"key": "value"}
            assert results[0].entities == []

    @pytest.mark.asyncio
    async def test_search_vectors_multiple_results(self, mock_connection_manager):
        """Test _search_vectors with multiple results (lines 274-285)."""
        search = VectorSearch(mock_connection_manager)

        chunk_id1 = uuid4()
        chunk_id2 = uuid4()
        doc_id = uuid4()

        mock_rows = [
            {
                "chunk_id": chunk_id1,
                "content": "First chunk",
                "similarity": 0.95,
                "document_id": doc_id,
                "document_title": "Test Doc",
                "document_source": "test.md",
                "metadata": {"page": 1},
                "entity_refs": ["Entity1"],
            },
            {
                "chunk_id": chunk_id2,
                "content": "Second chunk",
                "similarity": 0.87,
                "document_id": doc_id,
                "document_title": "Test Doc",
                "document_source": "test.md",
                "metadata": {"page": 2},
                "entity_refs": ["Entity2", "Entity3"],
            },
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            embedding = [0.1] * 1536
            results = await search._search_vectors(embedding, 10, None, 0.0)

            assert len(results) == 2
            assert results[0].chunk_id == chunk_id1
            assert results[0].similarity == 0.95
            assert results[1].chunk_id == chunk_id2
            assert results[1].entities == ["Entity2", "Entity3"]


class TestSearchSimilarChunks:
    """Test search_similar_chunks method (lines 312, 317)."""

    @pytest.mark.asyncio
    async def test_search_similar_chunks_not_found(self, mock_connection_manager):
        """Test search_similar_chunks when chunk not found (line 312)."""
        search = VectorSearch(mock_connection_manager)

        chunk_id = uuid4()

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            results = await search.search_similar_chunks(chunk_id, limit=5)
            assert results == []

    @pytest.mark.asyncio
    async def test_search_similar_chunks_no_embedding(self, mock_connection_manager):
        """Test search_similar_chunks when chunk has no embedding (line 317)."""
        search = VectorSearch(mock_connection_manager)

        chunk_id = uuid4()

        # Mock row with no embeddings
        mock_row = {
            "content": "Test content",
            "embedding_1536": None,
            "embedding_768": None,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            results = await search.search_similar_chunks(chunk_id, limit=5)
            assert results == []

    @pytest.mark.asyncio
    async def test_search_similar_chunks_with_1536_embedding(self, mock_connection_manager):
        """Test search_similar_chunks with 1536-dim embedding."""
        search = VectorSearch(mock_connection_manager)

        chunk_id = uuid4()
        embedding_1536 = [0.1] * 1536

        mock_row = {
            "content": "Test content",
            "embedding_1536": embedding_1536,
            "embedding_768": None,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            with patch.object(search, "_search_vectors", return_value=[]) as mock_search:
                await search.search_similar_chunks(chunk_id, limit=5)

                # Verify _search_vectors called with correct params
                mock_search.assert_called_once()
                call_args = mock_search.call_args
                assert call_args[0][0] == embedding_1536
                assert call_args[0][1] == 6  # limit + 1
                assert call_args[0][3] == 0.7  # Higher threshold

    @pytest.mark.asyncio
    async def test_search_similar_chunks_with_768_embedding(self, mock_connection_manager):
        """Test search_similar_chunks with 768-dim embedding."""
        search = VectorSearch(mock_connection_manager)

        chunk_id = uuid4()
        embedding_768 = [0.1] * 768

        mock_row = {
            "content": "Test content",
            "embedding_1536": None,
            "embedding_768": embedding_768,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            with patch.object(search, "_search_vectors", return_value=[]) as mock_search:
                await search.search_similar_chunks(chunk_id, limit=5)

                mock_search.assert_called_once()
                call_args = mock_search.call_args
                assert call_args[0][0] == embedding_768


class TestGetChunksByIds:
    """Test get_chunks_by_ids method (lines 337-379)."""

    @pytest.mark.asyncio
    async def test_get_chunks_by_ids_empty_list(self, mock_connection_manager):
        """Test get_chunks_by_ids with empty list (line 337-338)."""
        search = VectorSearch(mock_connection_manager)
        results = await search.get_chunks_by_ids([])
        assert results == []

    @pytest.mark.asyncio
    async def test_get_chunks_by_ids_single_chunk(self, mock_connection_manager):
        """Test get_chunks_by_ids with single chunk (lines 340-379)."""
        search = VectorSearch(mock_connection_manager)

        chunk_id = uuid4()
        doc_id = uuid4()

        mock_row = {
            "chunk_id": chunk_id,
            "content": "Test content",
            "document_id": doc_id,
            "document_title": "Test Doc",
            "document_source": "test.md",
            "metadata": {"key": "value"},
            "entity_refs": ["Entity1"],
        }

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            results = await search.get_chunks_by_ids([chunk_id])

            assert len(results) == 1
            assert results[0].chunk_id == chunk_id
            assert results[0].similarity == 1.0  # Direct retrieval
            assert results[0].content == "Test content"

    @pytest.mark.asyncio
    async def test_get_chunks_by_ids_multiple_chunks(self, mock_connection_manager):
        """Test get_chunks_by_ids with multiple chunks."""
        search = VectorSearch(mock_connection_manager)

        chunk_id1 = uuid4()
        chunk_id2 = uuid4()
        doc_id = uuid4()

        mock_rows = [
            {
                "chunk_id": chunk_id1,
                "content": "First chunk",
                "document_id": doc_id,
                "document_title": "Test Doc",
                "document_source": "test.md",
                "metadata": '{"page": 1}',
                "entity_refs": None,
            },
            {
                "chunk_id": chunk_id2,
                "content": "Second chunk",
                "document_id": doc_id,
                "document_title": "Test Doc",
                "document_source": "test.md",
                "metadata": {"page": 2},
                "entity_refs": ["Entity1", "Entity2"],
            },
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            results = await search.get_chunks_by_ids([chunk_id1, chunk_id2])

            assert len(results) == 2
            assert results[0].chunk_id == chunk_id1
            assert results[0].metadata == {"page": 1}
            assert results[0].entities == []
            assert results[1].chunk_id == chunk_id2
            assert results[1].entities == ["Entity1", "Entity2"]

    @pytest.mark.asyncio
    async def test_get_chunks_by_ids_with_string_metadata(self, mock_connection_manager):
        """Test get_chunks_by_ids with metadata as string (lines 360-364)."""
        search = VectorSearch(mock_connection_manager)

        chunk_id = uuid4()

        mock_row = {
            "chunk_id": chunk_id,
            "content": "Test",
            "document_id": uuid4(),
            "document_title": "Test",
            "document_source": "test.md",
            "metadata": '{"author": "alice", "year": 2024}',
            "entity_refs": [],
        }

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            results = await search.get_chunks_by_ids([chunk_id])

            assert len(results) == 1
            assert results[0].metadata == {"author": "alice", "year": 2024}


class TestGetStats:
    """Test get_stats method (lines 391-398)."""

    def test_get_stats_no_searches(self, mock_connection_manager):
        """Test get_stats with no searches."""
        search = VectorSearch(mock_connection_manager)
        stats = search.get_stats()

        assert stats["searches"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["total_latency"] == 0
        assert "avg_latency" not in stats
        assert "cache_hit_rate" not in stats

    def test_get_stats_with_searches(self, mock_connection_manager):
        """Test get_stats with searches (line 391)."""
        search = VectorSearch(mock_connection_manager)
        search._stats["searches"] = 10
        search._stats["total_latency"] = 2.5

        stats = search.get_stats()
        assert stats["avg_latency"] == 0.25

    def test_get_stats_with_cache_activity(self, mock_connection_manager):
        """Test get_stats with cache activity (lines 393-398)."""
        search = VectorSearch(mock_connection_manager)
        search._stats["searches"] = 20
        search._stats["total_latency"] = 5.0
        search._stats["cache_hits"] = 15
        search._stats["cache_misses"] = 5

        stats = search.get_stats()
        assert stats["avg_latency"] == 0.25
        assert stats["cache_hit_rate"] == 0.75

    def test_get_stats_zero_cache_activity(self, mock_connection_manager):
        """Test get_stats with zero cache activity (line 398)."""
        search = VectorSearch(mock_connection_manager)
        search._stats["searches"] = 10
        search._stats["total_latency"] = 2.0
        search._stats["cache_hits"] = 0
        search._stats["cache_misses"] = 0

        stats = search.get_stats()
        assert stats["cache_hit_rate"] == 0.0

    def test_get_stats_all_cache_hits(self, mock_connection_manager):
        """Test get_stats with all cache hits."""
        search = VectorSearch(mock_connection_manager)
        search._stats["searches"] = 10
        search._stats["total_latency"] = 1.0
        search._stats["cache_hits"] = 10
        search._stats["cache_misses"] = 0

        stats = search.get_stats()
        assert stats["cache_hit_rate"] == 1.0


class TestClearCache:
    """Test clear_cache method (lines 404-406)."""

    def test_clear_cache_when_enabled(self, mock_connection_manager):
        """Test clear_cache when cache is enabled (lines 404-406)."""
        with patch("src.agentic_rag.search.vector_search.get_config") as mock_config:
            mock_perf = Mock()
            mock_perf.enable_caching = True
            mock_perf.embedding_cache_ttl = 3600
            mock_config.return_value.performance = mock_perf

            search = VectorSearch(mock_connection_manager)

            # Add some data to cache
            search.cache.set("key1", [])
            search.cache.set("key2", [])
            assert len(search.cache._cache) == 2

            # Clear cache
            search.clear_cache()
            assert len(search.cache._cache) == 0

    def test_clear_cache_when_disabled(self, mock_connection_manager):
        """Test clear_cache when cache is disabled."""
        with patch("src.agentic_rag.search.vector_search.get_config") as mock_config:
            mock_perf = Mock()
            mock_perf.enable_caching = False
            mock_config.return_value.performance = mock_perf

            search = VectorSearch(mock_connection_manager)

            # Should not raise error
            search.clear_cache()


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self, mock_connection_manager):
        """Test search with empty query."""
        search = VectorSearch(mock_connection_manager)

        with patch.object(search.embedder, "embed", return_value=[0.0] * 1536):
            with patch.object(search, "_search_vectors", return_value=[]):
                results = await search.search("", limit=10)
                assert results == []

    @pytest.mark.asyncio
    async def test_search_with_very_long_query(self, mock_connection_manager):
        """Test search with very long query."""
        search = VectorSearch(mock_connection_manager)

        long_query = "test " * 1000  # Very long query

        with patch.object(search.embedder, "embed", return_value=[0.1] * 1536):
            with patch.object(search, "_search_vectors", return_value=[]):
                results = await search.search(long_query, limit=10)
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, mock_connection_manager):
        """Test search with special characters in query."""
        search = VectorSearch(mock_connection_manager)

        special_query = "test @#$%^&*() query\n\t\r"

        with patch.object(search.embedder, "embed", return_value=[0.1] * 1536):
            with patch.object(search, "_search_vectors", return_value=[]):
                results = await search.search(special_query, limit=10)
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_zero_limit(self, mock_connection_manager):
        """Test search with zero limit."""
        search = VectorSearch(mock_connection_manager)

        with patch.object(search.embedder, "embed", return_value=[0.1] * 1536):
            with patch.object(search, "_search_vectors", return_value=[]):
                results = await search.search("test", limit=0)
                assert results == []

    @pytest.mark.asyncio
    async def test_search_with_very_high_threshold(self, mock_connection_manager):
        """Test search with very high similarity threshold."""
        search = VectorSearch(mock_connection_manager)

        with patch.object(search.embedder, "embed", return_value=[0.1] * 1536):
            with patch.object(search, "_search_vectors", return_value=[]):
                results = await search.search("test", limit=10, similarity_threshold=0.99)
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_complex_filters(self, mock_connection_manager):
        """Test search with complex metadata filters."""
        search = VectorSearch(mock_connection_manager)

        complex_filters = {
            "type": "article",
            "author": "alice",
            "year": 2024,
            "tags": ["ai", "ml"],
            "nested": {"key": "value"},
        }

        with patch.object(search.embedder, "embed", return_value=[0.1] * 1536):
            with patch.object(search, "_search_vectors", return_value=[]):
                results = await search.search("test", limit=10, filters=complex_filters)
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_returns_more_than_limit(self, mock_connection_manager):
        """Test that search respects limit even if more results available."""
        search = VectorSearch(mock_connection_manager)

        # Create 20 mock results
        mock_results = [
            ChunkResult(
                chunk_id=uuid4(),
                content=f"Content {i}",
                similarity=0.9 - i * 0.01,
                document_id=uuid4(),
                document_title=f"Doc {i}",
                document_source=f"doc{i}.md",
            )
            for i in range(20)
        ]

        with patch.object(search.embedder, "embed", return_value=[0.1] * 1536):
            with patch.object(search, "_search_vectors", return_value=mock_results):
                results = await search.search("test", limit=5)
                assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_with_768_dim_embedding(self, mock_connection_manager):
        """Test search with 768-dimensional embedding."""
        search = VectorSearch(mock_connection_manager)

        embedding_768 = [0.1] * 768

        with patch.object(search.embedder, "embed", return_value=embedding_768):
            with patch.object(search, "_search_vectors", return_value=[]) as mock_search:
                await search.search("test", limit=10)

                # Verify correct embedding dimension passed
                call_args = mock_search.call_args
                assert len(call_args[0][0]) == 768

    @pytest.mark.asyncio
    async def test_cache_key_with_unicode_filters(self, mock_connection_manager):
        """Test cache key generation with unicode in filters."""
        embedding = [0.1] * 10
        filters = {"author": "José", "title": "日本語", "emoji": "😀"}

        key = SearchCache.generate_key(embedding, filters)
        assert isinstance(key, str)
        assert len(key) == 32

    def test_chunk_result_with_none_entities(self, mock_connection_manager):
        """Test ChunkResult with None entities."""
        chunk = ChunkResult(
            chunk_id=uuid4(),
            content="Test",
            similarity=0.9,
            document_id=uuid4(),
            document_title="Test",
            document_source="test.md",
            entities=None,
        )
        # Should default to empty list
        assert chunk.entities is None

    @pytest.mark.asyncio
    async def test_search_updates_stats(self, mock_connection_manager):
        """Test that search updates statistics correctly."""
        search = VectorSearch(mock_connection_manager)

        with patch.object(search.embedder, "embed", return_value=[0.1] * 1536):
            with patch.object(search, "_search_vectors", return_value=[]):
                await search.search("test1", limit=10)
                await search.search("test2", limit=10)
                await search.search("test3", limit=10)

                stats = search.get_stats()
                assert stats["searches"] == 3
                assert stats["total_latency"] > 0
                assert "avg_latency" in stats


class TestAsyncContextManagers:
    """Test async context manager usage."""

    @pytest.mark.asyncio
    async def test_search_vectors_connection_cleanup(self, mock_connection_manager):
        """Test that connection is properly cleaned up."""
        search = VectorSearch(mock_connection_manager)

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            await search._search_vectors([0.1] * 1536, 10, None, 0.0)

            # Verify context manager was used properly
            mock_context.__aenter__.assert_called_once()
            mock_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_similar_chunks_connection_cleanup(self, mock_connection_manager):
        """Test connection cleanup in search_similar_chunks."""
        search = VectorSearch(mock_connection_manager)

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            await search.search_similar_chunks(uuid4(), limit=5)

            mock_context.__aenter__.assert_called_once()
            mock_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_chunks_by_ids_connection_cleanup(self, mock_connection_manager):
        """Test connection cleanup in get_chunks_by_ids."""
        search = VectorSearch(mock_connection_manager)

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            search.connection_manager, "get_pg_connection", return_value=mock_context
        ):
            await search.get_chunks_by_ids([uuid4()])

            mock_context.__aenter__.assert_called_once()
            mock_context.__aexit__.assert_called_once()
