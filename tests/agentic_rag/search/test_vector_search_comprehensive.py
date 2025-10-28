"""
Comprehensive tests for VectorSearch - pgvector similarity search with caching.

Covers:
- Initialization and configuration
- Vector search with embeddings
- Search caching (TTL-based)
- Cache key generation
- Similar chunk search
- Chunk retrieval by IDs
- Metadata filtering
- Similarity thresholds
- Statistics tracking
- ChunkResult model
- SearchCache operations
"""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from src.agentic_rag.search.vector_search import (
    ChunkResult,
    SearchCache,
    VectorSearch,
)

# ===== Fixtures =====


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager."""
    cm = MagicMock()
    # Set up get_pg_connection to return an async context manager
    cm.get_pg_connection.return_value = AsyncMock()
    return cm


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = Mock()
    config.performance.enable_caching = True
    config.performance.embedding_cache_ttl = 3600
    return config


@pytest.fixture
def vector_search(mock_connection_manager, mock_config):
    """Create VectorSearch instance with mocks."""
    with patch("src.agentic_rag.search.vector_search.get_config", return_value=mock_config):
        vs = VectorSearch(mock_connection_manager)
        return vs


@pytest.fixture
def sample_embedding():
    """Sample embedding vector."""
    return [0.1] * 768  # 768-dimensional embedding


@pytest.fixture
def sample_chunk_result():
    """Sample chunk result."""
    return ChunkResult(
        chunk_id=uuid4(),
        content="Test content about OpenAI",
        similarity=0.9,
        document_id=uuid4(),
        document_title="Test Document",
        document_source="test.pdf",
        metadata={"page": 1},
        entities=["OpenAI"],
    )


# ===== Initialization Tests =====


class TestVectorSearchInit:
    """Test VectorSearch initialization."""

    def test_init_requires_connection_manager(self):
        """Test that initialization requires connection manager."""
        with pytest.raises(
            ValueError, match="VectorSearch requires an initialized ConnectionManager"
        ):
            VectorSearch(None)

    def test_init_with_connection_manager(self, mock_connection_manager, mock_config):
        """Test successful initialization."""
        with patch("src.agentic_rag.search.vector_search.get_config", return_value=mock_config):
            vs = VectorSearch(mock_connection_manager)

            assert vs.connection_manager == mock_connection_manager
            assert vs.pg_store is not None
            assert vs.embedder is not None

    def test_init_with_caching_enabled(self, mock_connection_manager, mock_config):
        """Test initialization with caching enabled."""
        mock_config.performance.enable_caching = True

        with patch("src.agentic_rag.search.vector_search.get_config", return_value=mock_config):
            vs = VectorSearch(mock_connection_manager)

            assert vs.cache is not None

    def test_init_with_caching_disabled(self, mock_connection_manager, mock_config):
        """Test initialization with caching disabled."""
        mock_config.performance.enable_caching = False

        with patch("src.agentic_rag.search.vector_search.get_config", return_value=mock_config):
            vs = VectorSearch(mock_connection_manager)

            assert vs.cache is None

    def test_init_creates_stats(self, vector_search):
        """Test that initialization creates stats tracking."""
        assert vector_search._stats["searches"] == 0
        assert vector_search._stats["cache_hits"] == 0


# ===== Search Tests =====


@pytest.mark.asyncio
class TestVectorSearch:
    """Test vector search functionality."""

    async def test_search_generates_embedding(self, vector_search, sample_embedding):
        """Test that search generates query embedding."""
        vector_search.embedder.embed = AsyncMock(return_value=sample_embedding)

        with patch.object(vector_search, "_search_vectors", new=AsyncMock(return_value=[])):
            await vector_search.search("test query", limit=10)

            vector_search.embedder.embed.assert_called_once_with("test query")

    async def test_search_checks_cache(self, vector_search, sample_embedding, sample_chunk_result):
        """Test that search checks cache first."""
        vector_search.embedder.embed = AsyncMock(return_value=sample_embedding)
        vector_search.cache.get = Mock(return_value=[sample_chunk_result])

        results = await vector_search.search("test query", limit=10)

        assert len(results) == 1
        assert vector_search._stats["cache_hits"] == 1

    async def test_search_performs_query_on_cache_miss(
        self, vector_search, sample_embedding, sample_chunk_result
    ):
        """Test that search performs query on cache miss."""
        vector_search.embedder.embed = AsyncMock(return_value=sample_embedding)
        vector_search.cache.get = Mock(return_value=None)

        with patch.object(
            vector_search, "_search_vectors", new=AsyncMock(return_value=[sample_chunk_result])
        ):
            results = await vector_search.search("test query", limit=10)

            assert len(results) == 1
            assert vector_search._stats["cache_misses"] == 1

    async def test_search_caches_results(
        self, vector_search, sample_embedding, sample_chunk_result
    ):
        """Test that search caches results."""
        vector_search.embedder.embed = AsyncMock(return_value=sample_embedding)
        vector_search.cache.get = Mock(return_value=None)
        vector_search.cache.set = Mock()

        with patch.object(
            vector_search, "_search_vectors", new=AsyncMock(return_value=[sample_chunk_result])
        ):
            await vector_search.search("test query", limit=10)

            vector_search.cache.set.assert_called_once()

    async def test_search_with_filters(self, vector_search, sample_embedding):
        """Test search with metadata filters."""
        vector_search.embedder.embed = AsyncMock(return_value=sample_embedding)
        filters = {"source": "test.pdf"}

        with patch.object(vector_search, "_search_vectors", new=AsyncMock(return_value=[])):
            await vector_search.search("test query", limit=10, filters=filters)

            call_args = vector_search._search_vectors.call_args
            assert call_args[0][2] == filters

    async def test_search_with_similarity_threshold(self, vector_search, sample_embedding):
        """Test search with similarity threshold."""
        vector_search.embedder.embed = AsyncMock(return_value=sample_embedding)

        with patch.object(vector_search, "_search_vectors", new=AsyncMock(return_value=[])):
            await vector_search.search("test query", limit=10, similarity_threshold=0.7)

            call_args = vector_search._search_vectors.call_args
            assert call_args[0][3] == 0.7

    async def test_search_updates_stats(self, vector_search, sample_embedding):
        """Test that search updates statistics."""
        vector_search.embedder.embed = AsyncMock(return_value=sample_embedding)

        with patch.object(vector_search, "_search_vectors", new=AsyncMock(return_value=[])):
            await vector_search.search("test query", limit=10)

            assert vector_search._stats["searches"] == 1
            assert vector_search._stats["total_latency"] > 0


# ===== Search Vectors Tests =====


@pytest.mark.asyncio
class TestSearchVectors:
    """Test internal vector search execution."""

    async def test_search_vectors_queries_database(self, vector_search, sample_embedding):
        """Test that _search_vectors queries the database."""
        mock_conn = AsyncMock()
        mock_row = {
            "chunk_id": uuid4(),
            "content": "Test content",
            "similarity": 0.9,
            "document_id": uuid4(),
            "document_title": "Test Doc",
            "document_source": "test.pdf",
            "metadata": json.dumps({}),
            "entity_refs": [],
        }
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        vector_search.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )
        vector_search.connection_manager.get_pg_connection.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        results = await vector_search._search_vectors(
            sample_embedding, limit=10, filters=None, similarity_threshold=0.0
        )

        assert len(results) == 1
        assert results[0].content == "Test content"

    async def test_search_vectors_with_1536_embedding(self, vector_search):
        """Test vector search with 1536-dimensional embedding."""
        embedding_1536 = [0.1] * 1536

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        vector_search.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )
        vector_search.connection_manager.get_pg_connection.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await vector_search._search_vectors(
            embedding_1536, limit=10, filters=None, similarity_threshold=0.0
        )

        # Verify embedding_1536 column was used
        call_args = mock_conn.fetch.call_args
        query = call_args[0][0]
        assert "embedding_1536" in query

    async def test_search_vectors_with_768_embedding(self, vector_search, sample_embedding):
        """Test vector search with 768-dimensional embedding."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        vector_search.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )
        vector_search.connection_manager.get_pg_connection.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await vector_search._search_vectors(
            sample_embedding, limit=10, filters=None, similarity_threshold=0.0
        )

        # Verify embedding_768 column was used
        call_args = mock_conn.fetch.call_args
        query = call_args[0][0]
        assert "embedding_768" in query

    async def test_search_vectors_applies_filters(self, vector_search, sample_embedding):
        """Test that metadata filters are applied."""
        filters = {"source": "test.pdf", "page": 1}

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        vector_search.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )
        vector_search.connection_manager.get_pg_connection.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await vector_search._search_vectors(
            sample_embedding, limit=10, filters=filters, similarity_threshold=0.0
        )

        call_args = mock_conn.fetch.call_args
        filter_param = call_args[0][3]
        assert filter_param == json.dumps(filters)


# ===== Similar Chunks Search Tests =====


@pytest.mark.asyncio
class TestSearchSimilarChunks:
    """Test similar chunk search."""

    async def test_search_similar_chunks(self, vector_search):
        """Test finding similar chunks."""
        chunk_id = uuid4()
        mock_embedding = [0.1] * 1536

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            return_value={
                "content": "Test content",
                "embedding_1536": mock_embedding,
                "embedding_768": None,
            }
        )

        vector_search.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )
        vector_search.connection_manager.get_pg_connection.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        with patch.object(vector_search, "_search_vectors", new=AsyncMock(return_value=[])):
            await vector_search.search_similar_chunks(chunk_id, limit=5)

            # Should call _search_vectors with limit+1 and higher threshold
            call_args = vector_search._search_vectors.call_args
            assert call_args[0][1] == 6  # limit + 1
            assert call_args[0][3] == 0.7  # Higher threshold

    async def test_search_similar_chunks_not_found(self, vector_search):
        """Test similar chunk search when chunk not found."""
        chunk_id = uuid4()

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        vector_search.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )
        vector_search.connection_manager.get_pg_connection.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        results = await vector_search.search_similar_chunks(chunk_id, limit=5)

        assert results == []

    async def test_search_similar_chunks_no_embedding(self, vector_search):
        """Test similar chunk search when chunk has no embedding."""
        chunk_id = uuid4()

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            return_value={
                "content": "Test content",
                "embedding_1536": None,
                "embedding_768": None,
            }
        )

        vector_search.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )
        vector_search.connection_manager.get_pg_connection.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        results = await vector_search.search_similar_chunks(chunk_id, limit=5)

        assert results == []


# ===== Get Chunks by IDs Tests =====


@pytest.mark.asyncio
class TestGetChunksByIds:
    """Test chunk retrieval by IDs."""

    async def test_get_chunks_by_ids(self, vector_search):
        """Test retrieving chunks by IDs."""
        chunk_ids = [uuid4(), uuid4()]

        mock_rows = [
            {
                "chunk_id": chunk_ids[0],
                "content": "Content 1",
                "document_id": uuid4(),
                "document_title": "Doc 1",
                "document_source": "doc1.pdf",
                "metadata": json.dumps({}),
                "entity_refs": [],
            },
            {
                "chunk_id": chunk_ids[1],
                "content": "Content 2",
                "document_id": uuid4(),
                "document_title": "Doc 2",
                "document_source": "doc2.pdf",
                "metadata": json.dumps({}),
                "entity_refs": [],
            },
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)

        vector_search.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )
        vector_search.connection_manager.get_pg_connection.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        results = await vector_search.get_chunks_by_ids(chunk_ids)

        assert len(results) == 2
        assert results[0].content == "Content 1"
        assert results[1].content == "Content 2"

    async def test_get_chunks_by_ids_empty_list(self, vector_search):
        """Test with empty chunk ID list."""
        results = await vector_search.get_chunks_by_ids([])

        assert results == []

    async def test_get_chunks_by_ids_sets_max_similarity(self, vector_search):
        """Test that direct retrieval sets similarity to 1.0."""
        chunk_ids = [uuid4()]

        mock_row = {
            "chunk_id": chunk_ids[0],
            "content": "Content",
            "document_id": uuid4(),
            "document_title": "Doc",
            "document_source": "doc.pdf",
            "metadata": json.dumps({}),
            "entity_refs": [],
        }

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        vector_search.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )
        vector_search.connection_manager.get_pg_connection.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        results = await vector_search.get_chunks_by_ids(chunk_ids)

        assert results[0].similarity == 1.0


# ===== Cache Tests =====


class TestSearchCache:
    """Test SearchCache functionality."""

    def test_cache_init(self):
        """Test cache initialization."""
        cache = SearchCache(ttl_seconds=1800)

        assert cache.ttl == timedelta(seconds=1800)
        assert cache._cache == {}

    def test_cache_get_miss(self):
        """Test cache miss."""
        cache = SearchCache()

        result = cache.get("nonexistent_key")

        assert result is None

    def test_cache_set_and_get(self, sample_chunk_result):
        """Test caching and retrieving results."""
        cache = SearchCache()
        results = [sample_chunk_result]

        cache.set("test_key", results)
        cached = cache.get("test_key")

        assert cached == results

    def test_cache_expiration(self, sample_chunk_result):
        """Test that cache entries expire."""
        cache = SearchCache(ttl_seconds=0)  # Instant expiration
        results = [sample_chunk_result]

        cache.set("test_key", results)

        # Give it a moment to expire
        import time

        time.sleep(0.1)

        cached = cache.get("test_key")

        assert cached is None

    def test_cache_clear(self, sample_chunk_result):
        """Test clearing cache."""
        cache = SearchCache()
        cache.set("key1", [sample_chunk_result])
        cache.set("key2", [sample_chunk_result])

        cache.clear()

        assert cache._cache == {}

    def test_generate_cache_key(self):
        """Test cache key generation."""
        embedding = [0.1] * 10
        filters = {"source": "test.pdf"}

        key = SearchCache.generate_key(embedding, filters)

        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hex digest length

    def test_generate_cache_key_consistent(self):
        """Test that same inputs generate same key."""
        embedding = [0.1] * 10
        filters = {"source": "test.pdf"}

        key1 = SearchCache.generate_key(embedding, filters)
        key2 = SearchCache.generate_key(embedding, filters)

        assert key1 == key2

    def test_generate_cache_key_different_filters(self):
        """Test that different filters generate different keys."""
        embedding = [0.1] * 10

        key1 = SearchCache.generate_key(embedding, {"source": "test.pdf"})
        key2 = SearchCache.generate_key(embedding, {"source": "other.pdf"})

        assert key1 != key2


# ===== Statistics Tests =====


class TestStatistics:
    """Test statistics tracking and retrieval."""

    def test_get_stats_empty(self, vector_search):
        """Test getting stats before any searches."""
        stats = vector_search.get_stats()

        assert stats["searches"] == 0
        assert stats["cache_hits"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_searches(self, vector_search, sample_embedding):
        """Test stats after performing searches."""
        vector_search.embedder.embed = AsyncMock(return_value=sample_embedding)

        with patch.object(vector_search, "_search_vectors", new=AsyncMock(return_value=[])):
            await vector_search.search("query 1", limit=10)
            await vector_search.search("query 2", limit=10)

        stats = vector_search.get_stats()

        assert stats["searches"] == 2
        assert "avg_latency" in stats

    @pytest.mark.asyncio
    async def test_get_stats_cache_hit_rate(
        self, vector_search, sample_embedding, sample_chunk_result
    ):
        """Test cache hit rate calculation."""
        vector_search.embedder.embed = AsyncMock(return_value=sample_embedding)
        vector_search.cache.get = Mock(side_effect=[None, [sample_chunk_result]])

        with patch.object(
            vector_search, "_search_vectors", new=AsyncMock(return_value=[sample_chunk_result])
        ):
            await vector_search.search("query 1", limit=10)  # Cache miss
            await vector_search.search("query 2", limit=10)  # Cache hit

        stats = vector_search.get_stats()

        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["cache_hit_rate"] == 0.5

    def test_clear_cache(self, vector_search):
        """Test clearing the search cache."""
        vector_search.cache.clear = Mock()

        vector_search.clear_cache()

        vector_search.cache.clear.assert_called_once()


# ===== ChunkResult Model Tests =====


class TestChunkResult:
    """Test ChunkResult dataclass."""

    def test_chunk_result_creation(self):
        """Test creating ChunkResult."""
        chunk_id = uuid4()
        document_id = uuid4()

        result = ChunkResult(
            chunk_id=chunk_id,
            content="Test content",
            similarity=0.9,
            document_id=document_id,
            document_title="Test Doc",
            document_source="test.pdf",
            metadata={"page": 1},
            entities=["Entity1"],
        )

        assert result.chunk_id == chunk_id
        assert result.content == "Test content"
        assert result.similarity == 0.9

    def test_chunk_result_score_property(self, sample_chunk_result):
        """Test score property (alias for similarity)."""
        assert sample_chunk_result.score == sample_chunk_result.similarity

    def test_chunk_result_to_dict(self, sample_chunk_result):
        """Test converting ChunkResult to dictionary."""
        result_dict = sample_chunk_result.to_dict()

        assert "chunk_id" in result_dict
        assert result_dict["content"] == sample_chunk_result.content
        assert result_dict["similarity"] == sample_chunk_result.similarity
        assert result_dict["entities"] == ["OpenAI"]

    def test_chunk_result_defaults(self):
        """Test ChunkResult default values."""
        result = ChunkResult(
            chunk_id=uuid4(),
            content="Test",
            similarity=0.8,
            document_id=uuid4(),
            document_title="Doc",
            document_source="source",
        )

        assert result.metadata == {}
        assert result.entities == []
