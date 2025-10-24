"""
Comprehensive tests for PostgresStore.

Tests all CRUD operations, search functionality, session management,
sync queue operations, and statistics gathering.
"""

import json
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.agentic_rag.storage.postgres_store import PostgresStore


class MockAsyncConnection:
    """Mock asyncpg connection for testing."""

    def __init__(self):
        """Initialize mock connection."""
        self.executed_queries = []
        self.fetchval_return = None
        self.fetchrow_return = None
        self.fetch_return = []

    async def execute(self, query: str, *args):
        """Mock execute method."""
        self.executed_queries.append((query, args))

    async def fetchval(self, query: str, *args):
        """Mock fetchval method."""
        self.executed_queries.append((query, args))
        return self.fetchval_return

    async def fetchrow(self, query: str, *args):
        """Mock fetchrow method."""
        self.executed_queries.append((query, args))
        return self.fetchrow_return

    async def fetch(self, query: str, *args):
        """Mock fetch method."""
        self.executed_queries.append((query, args))
        return self.fetch_return

    def set_fetchval(self, value):
        """Set return value for fetchval."""
        self.fetchval_return = value

    def set_fetchrow(self, value):
        """Set return value for fetchrow."""
        self.fetchrow_return = value

    def set_fetch(self, values):
        """Set return value for fetch."""
        self.fetch_return = values


@pytest.fixture
def mock_connection():
    """Provide mock database connection."""
    return MockAsyncConnection()


@pytest.fixture
def mock_connection_manager(mock_connection):
    """Provide mock connection manager."""
    manager = MagicMock()

    @asynccontextmanager
    async def get_pg_connection():
        yield mock_connection

    manager.get_pg_connection = get_pg_connection
    return manager


@pytest.fixture
def postgres_store(mock_connection_manager):
    """Provide PostgresStore instance with mocked connection."""
    return PostgresStore(mock_connection_manager)


class TestStoreDocument:
    """Tests for store_document method."""

    @pytest.mark.asyncio
    async def test_store_document_success(self, postgres_store, mock_connection):
        """Test successful document storage."""
        doc_id = uuid4()
        mock_connection.set_fetchval(doc_id)

        result = await postgres_store.store_document(
            title="Test Doc", source="test.pdf", content="Test content", metadata={"key": "value"}
        )

        assert result == doc_id
        assert len(mock_connection.executed_queries) == 1
        query, args = mock_connection.executed_queries[0]
        assert "INSERT INTO documents" in query
        assert args == ("Test Doc", "test.pdf", "Test content", '{"key": "value"}')

    @pytest.mark.asyncio
    async def test_store_document_no_metadata(self, postgres_store, mock_connection):
        """Test document storage without metadata."""
        doc_id = uuid4()
        mock_connection.set_fetchval(doc_id)

        result = await postgres_store.store_document(
            title="Test Doc", source="test.pdf", content="Test content"
        )

        assert result == doc_id
        query, args = mock_connection.executed_queries[0]
        assert args[3] == "{}"  # Empty metadata dict


class TestStoreChunks:
    """Tests for store_chunks method."""

    @pytest.mark.asyncio
    async def test_store_chunks_with_embeddings(self, postgres_store, mock_connection):
        """Test storing chunks with both embedding types."""
        doc_id = uuid4()
        chunk_id_1 = uuid4()
        chunk_id_2 = uuid4()

        # Mock fetchrow to return chunk IDs
        mock_connection.set_fetchrow({"id": chunk_id_1})

        chunks = [
            {
                "content": "Chunk 1",
                "embedding_1536": [0.1] * 1536,
                "embedding_768": [0.2] * 768,
                "metadata": {"type": "text"},
                "token_count": 100,
            },
            {
                "content": "Chunk 2",
                "embedding_1536": [0.3] * 1536,
                "embedding_768": [0.4] * 768,
                "metadata": {},
                "token_count": 150,
            },
        ]

        # Update mock to return different IDs for each call
        call_count = [0]

        async def fetchrow_with_counter(query, *args):
            """Mock fetchrow that returns different IDs."""
            mock_connection.executed_queries.append((query, args))
            call_count[0] += 1
            if call_count[0] == 1:
                return {"id": chunk_id_1}
            return {"id": chunk_id_2}

        mock_connection.fetchrow = fetchrow_with_counter

        result = await postgres_store.store_chunks(doc_id, chunks)

        assert len(result) == 2
        assert result[0] == chunk_id_1
        assert result[1] == chunk_id_2

    @pytest.mark.asyncio
    async def test_store_chunks_no_embeddings(self, postgres_store, mock_connection):
        """Test storing chunks without embeddings."""
        doc_id = uuid4()
        chunk_id = uuid4()

        mock_connection.set_fetchrow({"id": chunk_id})

        chunks = [
            {"content": "Chunk without embeddings", "metadata": {}, "token_count": 50}
        ]

        result = await postgres_store.store_chunks(doc_id, chunks)

        assert len(result) == 1
        query, args = mock_connection.executed_queries[0]
        assert args[2] is None  # embedding_1536 should be None
        assert args[3] is None  # embedding_768 should be None


class TestUpdateChunkMetadata:
    """Tests for update_chunk_metadata method."""

    @pytest.mark.asyncio
    async def test_update_chunk_metadata_basic(self, postgres_store, mock_connection):
        """Test basic metadata update."""
        chunk_id = uuid4()
        mock_connection.set_fetchval('{"existing": "data"}')

        await postgres_store.update_chunk_metadata(chunk_id, {"new_field": "new_value"})

        assert len(mock_connection.executed_queries) == 2
        # First query: SELECT metadata
        # Second query: UPDATE chunk
        update_query = mock_connection.executed_queries[1][0]
        assert "UPDATE chunks" in update_query

    @pytest.mark.asyncio
    async def test_update_chunk_metadata_with_entity_refs(
        self, postgres_store, mock_connection
    ):
        """Test metadata update with entity references."""
        chunk_id = uuid4()
        mock_connection.set_fetchval('{"existing": "data"}')

        await postgres_store.update_chunk_metadata(
            chunk_id, {"entity_refs": ["entity1", "entity2"], "other": "data"}
        )

        # Should use UPDATE query with entity_refs field
        update_query = mock_connection.executed_queries[1][0]
        assert "entity_refs" in update_query

    @pytest.mark.asyncio
    async def test_update_chunk_metadata_no_existing(self, postgres_store, mock_connection):
        """Test metadata update when no existing metadata."""
        chunk_id = uuid4()
        mock_connection.set_fetchval(None)

        await postgres_store.update_chunk_metadata(chunk_id, {"new_field": "value"})

        # Should create new metadata dict
        assert len(mock_connection.executed_queries) == 2


class TestSearchSimilar:
    """Tests for search_similar method."""

    @pytest.mark.asyncio
    async def test_search_similar_1536_embedding(self, postgres_store, mock_connection):
        """Test vector search with 1536-dimensional embedding."""
        chunk_id = uuid4()
        doc_id = uuid4()

        mock_connection.set_fetch(
            [
                {
                    "id": chunk_id,
                    "document_id": doc_id,
                    "content": "Similar content",
                    "metadata": {},
                    "chunk_index": 0,
                    "title": "Test Doc",
                    "source": "test.pdf",
                    "similarity": 0.95,
                }
            ]
        )

        embedding = [0.1] * 1536
        results = await postgres_store.search_similar(embedding, limit=5, similarity_threshold=0.7)

        assert len(results) == 1
        assert results[0]["id"] == chunk_id
        assert results[0]["similarity"] == 0.95

        query = mock_connection.executed_queries[0][0]
        assert "embedding_1536" in query

    @pytest.mark.asyncio
    async def test_search_similar_768_embedding(self, postgres_store, mock_connection):
        """Test vector search with 768-dimensional embedding."""
        mock_connection.set_fetch([])

        embedding = [0.1] * 768
        results = await postgres_store.search_similar(embedding, limit=10)

        query = mock_connection.executed_queries[0][0]
        assert "embedding_768" in query

    @pytest.mark.asyncio
    async def test_search_similar_no_results(self, postgres_store, mock_connection):
        """Test vector search with no matching results."""
        mock_connection.set_fetch([])

        embedding = [0.1] * 1536
        results = await postgres_store.search_similar(embedding)

        assert len(results) == 0


class TestHybridSearch:
    """Tests for hybrid_search method."""

    @pytest.mark.asyncio
    async def test_hybrid_search_with_entities(self, postgres_store, mock_connection):
        """Test hybrid search with entity boosting."""
        mock_connection.set_fetch(
            [
                {
                    "chunk_id": uuid4(),
                    "content": "Hybrid result",
                    "combined_score": 0.92,
                    "vector_score": 0.85,
                    "entity_boost": 1.2,
                }
            ]
        )

        embedding = [0.1] * 1536
        results = await postgres_store.hybrid_search(
            query_embedding=embedding,
            query_text="test query",
            entity_ids=["entity1", "entity2"],
            limit=10,
        )

        assert len(results) == 1
        query = mock_connection.executed_queries[0][0]
        assert "hybrid_search_enhanced" in query

    @pytest.mark.asyncio
    async def test_hybrid_search_no_entities(self, postgres_store, mock_connection):
        """Test hybrid search without entity boosting."""
        mock_connection.set_fetch([])

        embedding = [0.1] * 768
        results = await postgres_store.hybrid_search(
            query_embedding=embedding, query_text="test", entity_ids=None, limit=5
        )

        assert len(results) == 0


class TestGetDocument:
    """Tests for get_document method."""

    @pytest.mark.asyncio
    async def test_get_document_found(self, postgres_store, mock_connection):
        """Test retrieving existing document."""
        doc_id = uuid4()
        mock_connection.set_fetchrow(
            {
                "id": doc_id,
                "title": "Test Doc",
                "content": "Content",
                "metadata": {"key": "value"},
                "is_deleted": False,
            }
        )

        result = await postgres_store.get_document(doc_id)

        assert result is not None
        assert result["id"] == doc_id
        assert result["title"] == "Test Doc"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, postgres_store, mock_connection):
        """Test retrieving non-existent document."""
        mock_connection.set_fetchrow(None)

        doc_id = uuid4()
        result = await postgres_store.get_document(doc_id)

        assert result is None


class TestDeleteDocument:
    """Tests for delete_document method."""

    @pytest.mark.asyncio
    async def test_soft_delete_document(self, postgres_store, mock_connection):
        """Test soft deletion of document."""
        doc_id = uuid4()

        await postgres_store.delete_document(doc_id, hard_delete=False)

        assert len(mock_connection.executed_queries) == 1
        query = mock_connection.executed_queries[0][0]
        assert "UPDATE documents" in query
        assert "is_deleted = TRUE" in query

    @pytest.mark.asyncio
    async def test_hard_delete_document(self, postgres_store, mock_connection):
        """Test hard deletion of document."""
        doc_id = uuid4()

        await postgres_store.delete_document(doc_id, hard_delete=True)

        # Should insert into sync queue and then delete
        assert len(mock_connection.executed_queries) == 2
        assert "INSERT INTO graph_sync_queue" in mock_connection.executed_queries[0][0]
        assert "DELETE FROM documents" in mock_connection.executed_queries[1][0]


class TestSessionManagement:
    """Tests for session and message management."""

    @pytest.mark.asyncio
    async def test_create_session(self, postgres_store, mock_connection):
        """Test session creation."""
        session_id = uuid4()
        mock_connection.set_fetchval(session_id)

        result = await postgres_store.create_session(
            user_id="user123", metadata={"ip": "127.0.0.1"}
        )

        assert result == session_id
        query, args = mock_connection.executed_queries[0]
        assert "INSERT INTO sessions" in query

    @pytest.mark.asyncio
    async def test_add_message(self, postgres_store, mock_connection):
        """Test adding message to session."""
        session_id = uuid4()

        await postgres_store.add_message(
            session_id, role="user", content="Hello", metadata={"timestamp": "123"}
        )

        query, args = mock_connection.executed_queries[0]
        assert "INSERT INTO messages" in query
        assert args[0] == session_id
        assert args[1] == "user"
        assert args[2] == "Hello"

    @pytest.mark.asyncio
    async def test_get_session_messages(self, postgres_store, mock_connection):
        """Test retrieving session messages."""
        session_id = uuid4()
        msg_1 = {"role": "user", "content": "Hello"}
        msg_2 = {"role": "assistant", "content": "Hi there"}

        # Messages are returned in DESC order, then reversed
        mock_connection.set_fetch([msg_2, msg_1])

        results = await postgres_store.get_session_messages(session_id, limit=50)

        # Results are returned DESC then reversed, so newest should be last
        assert len(results) == 2
        # After reversal: msg_2 (assistant) is first, msg_1 (user) is second
        assert results[0]["role"] == "user"
        assert results[1]["role"] == "assistant"


class TestSyncQueue:
    """Tests for graph sync queue operations."""

    @pytest.mark.asyncio
    async def test_add_to_sync_queue(self, postgres_store, mock_connection):
        """Test adding item to sync queue."""
        doc_id = uuid4()
        chunk_id = uuid4()

        await postgres_store.add_to_sync_queue(
            document_id=doc_id,
            chunk_id=chunk_id,
            operation="update",
            payload={"field": "value"},
        )

        query, args = mock_connection.executed_queries[0]
        assert "INSERT INTO graph_sync_queue" in query
        assert args[0] == doc_id
        assert args[1] == chunk_id

    @pytest.mark.asyncio
    async def test_get_pending_sync_items(self, postgres_store, mock_connection):
        """Test retrieving pending sync items."""
        sync_id = uuid4()
        mock_connection.set_fetch(
            [
                {
                    "id": sync_id,
                    "document_id": uuid4(),
                    "status": "pending",
                    "operation": "create",
                }
            ]
        )

        results = await postgres_store.get_pending_sync_items(limit=100)

        assert len(results) == 1
        assert results[0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_update_sync_item_status_success(self, postgres_store, mock_connection):
        """Test updating sync item to completed status."""
        sync_id = uuid4()

        await postgres_store.update_sync_item_status(sync_id, "completed")

        query = mock_connection.executed_queries[0][0]
        assert "UPDATE graph_sync_queue" in query
        assert "status = $1" in query

    @pytest.mark.asyncio
    async def test_update_sync_item_status_failed(self, postgres_store, mock_connection):
        """Test updating sync item to failed status with error."""
        sync_id = uuid4()

        await postgres_store.update_sync_item_status(
            sync_id, "failed", error_message="Connection timeout"
        )

        query = mock_connection.executed_queries[0][0]
        assert "UPDATE graph_sync_queue" in query
        assert "retry_count = retry_count + 1" in query


class TestCacheOperations:
    """Tests for cache management."""

    @pytest.mark.asyncio
    async def test_clean_expired_cache(self, postgres_store, mock_connection):
        """Test cleaning expired cache entries."""
        mock_connection.set_fetchval(42)  # 42 entries deleted

        await postgres_store.clean_expired_cache()

        query = mock_connection.executed_queries[0][0]
        assert "DELETE FROM search_cache" in query
        assert "expires_at < NOW()" in query

    @pytest.mark.asyncio
    async def test_clean_expired_cache_none_expired(self, postgres_store, mock_connection):
        """Test cleaning cache when nothing is expired."""
        mock_connection.set_fetchval(0)

        await postgres_store.clean_expired_cache()

        # Should still execute query
        assert len(mock_connection.executed_queries) == 1


class TestListDocuments:
    """Tests for list_documents method."""

    @pytest.mark.asyncio
    async def test_list_documents_basic(self, postgres_store, mock_connection):
        """Test basic document listing."""
        doc_1 = {
            "id": uuid4(),
            "title": "Doc 1",
            "source": "test1.pdf",
            "chunk_count": 5,
        }
        mock_connection.set_fetch([doc_1])

        results = await postgres_store.list_documents(limit=20, offset=0)

        assert len(results) == 1
        assert results[0]["title"] == "Doc 1"

    @pytest.mark.asyncio
    async def test_list_documents_with_filter(self, postgres_store, mock_connection):
        """Test document listing with source filter."""
        mock_connection.set_fetch([])

        results = await postgres_store.list_documents(
            limit=10, offset=0, source_filter="%.pdf"
        )

        query = mock_connection.executed_queries[0][0]
        assert "d.source LIKE $3" in query

    @pytest.mark.asyncio
    async def test_list_documents_sorting(self, postgres_store, mock_connection):
        """Test document listing with custom sorting."""
        mock_connection.set_fetch([])

        await postgres_store.list_documents(
            limit=10, offset=0, sort_by="title", sort_order="asc"
        )

        query = mock_connection.executed_queries[0][0]
        assert "ORDER BY d.title ASC" in query

    @pytest.mark.asyncio
    async def test_list_documents_invalid_sort_field(self, postgres_store, mock_connection):
        """Test document listing with invalid sort field defaults to created_at."""
        mock_connection.set_fetch([])

        await postgres_store.list_documents(
            limit=10, offset=0, sort_by="invalid_field", sort_order="desc"
        )

        query = mock_connection.executed_queries[0][0]
        # Should default to created_at
        assert "ORDER BY d.created_at DESC" in query


class TestCountDocuments:
    """Tests for count_documents method."""

    @pytest.mark.asyncio
    async def test_count_documents_all(self, postgres_store, mock_connection):
        """Test counting all documents."""
        mock_connection.set_fetchrow({"total": 150})

        result = await postgres_store.count_documents()

        assert result == 150

    @pytest.mark.asyncio
    async def test_count_documents_with_filter(self, postgres_store, mock_connection):
        """Test counting documents with filter."""
        mock_connection.set_fetchrow({"total": 25})

        result = await postgres_store.count_documents(source_filter="%.md")

        assert result == 25


class TestGetDocumentChunks:
    """Tests for get_document_chunks method."""

    @pytest.mark.asyncio
    async def test_get_document_chunks_without_embeddings(
        self, postgres_store, mock_connection
    ):
        """Test getting chunks without embeddings."""
        doc_id = uuid4()
        mock_connection.set_fetch(
            [
                {"id": uuid4(), "content": "Chunk 1", "chunk_index": 0},
                {"id": uuid4(), "content": "Chunk 2", "chunk_index": 1},
            ]
        )

        results = await postgres_store.get_document_chunks(doc_id, include_embeddings=False)

        assert len(results) == 2
        query = mock_connection.executed_queries[0][0]
        assert "embedding_1536" not in query

    @pytest.mark.asyncio
    async def test_get_document_chunks_with_embeddings(
        self, postgres_store, mock_connection
    ):
        """Test getting chunks with embeddings."""
        doc_id = uuid4()
        mock_connection.set_fetch([])

        results = await postgres_store.get_document_chunks(doc_id, include_embeddings=True)

        query = mock_connection.executed_queries[0][0]
        assert "embedding_1536" in query
        assert "embedding_768" in query


class TestUpdateDocument:
    """Tests for update_document method."""

    @pytest.mark.asyncio
    async def test_update_document_title(self, postgres_store, mock_connection):
        """Test updating document title."""
        doc_id = uuid4()
        mock_connection.set_fetchrow({"id": doc_id})

        result = await postgres_store.update_document(doc_id, {"title": "New Title"})

        assert result is True
        query = mock_connection.executed_queries[0][0]
        assert "UPDATE documents" in query
        assert "title = $2" in query

    @pytest.mark.asyncio
    async def test_update_document_metadata(self, postgres_store, mock_connection):
        """Test updating document metadata."""
        doc_id = uuid4()
        mock_connection.set_fetchrow({"id": doc_id})

        result = await postgres_store.update_document(
            doc_id, {"metadata": {"new": "data", "version": 2}}
        )

        assert result is True
        query = mock_connection.executed_queries[0][0]
        assert "metadata = $2::jsonb" in query

    @pytest.mark.asyncio
    async def test_update_document_not_found(self, postgres_store, mock_connection):
        """Test updating non-existent document."""
        doc_id = uuid4()
        mock_connection.set_fetchrow(None)

        result = await postgres_store.update_document(doc_id, {"title": "New Title"})

        assert result is False

    @pytest.mark.asyncio
    async def test_update_document_no_valid_fields(self, postgres_store, mock_connection):
        """Test update with no valid fields."""
        doc_id = uuid4()

        result = await postgres_store.update_document(doc_id, {"invalid_field": "value"})

        assert result is False
        # Should not execute any queries
        assert len(mock_connection.executed_queries) == 0


class TestCountChunks:
    """Tests for count_chunks method."""

    @pytest.mark.asyncio
    async def test_count_chunks(self, postgres_store, mock_connection):
        """Test counting chunks for a document."""
        doc_id = uuid4()
        mock_connection.set_fetchrow({"total": 42})

        result = await postgres_store.count_chunks(doc_id)

        assert result == 42


class TestGetStatistics:
    """Tests for get_statistics method."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, postgres_store, mock_connection):
        """Test getting comprehensive database statistics."""
        # Mock multiple fetchval/fetchrow calls
        call_count = [0]

        async def fetchval_mock(query, *args):
            """Mock fetchval with different returns."""
            call_count[0] += 1
            if call_count[0] == 1:
                return 100  # total_documents
            return 0

        async def fetchrow_mock(query, *args):
            """Mock fetchrow with different returns."""
            if "chunks" in query.lower():
                return {
                    "total_chunks": 500,
                    "documents_with_chunks": 95,
                    "chunks_with_1536_embeddings": 450,
                    "chunks_with_768_embeddings": 400,
                    "avg_token_count": 250.5,
                }
            elif "sessions" in query.lower():
                return {"total_sessions": 50, "total_messages": 300}
            elif "graph_sync_queue" in query.lower():
                return {"pending_syncs": 10, "failed_syncs": 2, "completed_syncs": 200}
            elif "search_cache" in query.lower():
                return {
                    "cached_searches": 1000,
                    "avg_cache_hits": 5.2,
                    "max_cache_hits": 50,
                }
            return {}

        mock_connection.fetchval = fetchval_mock
        mock_connection.fetchrow = fetchrow_mock

        stats = await postgres_store.get_statistics()

        assert stats["total_documents"] == 100
        assert stats["total_chunks"] == 500
        assert stats["total_sessions"] == 50
        assert stats["pending_syncs"] == 10


class TestGetChunksByIds:
    """Tests for get_chunks_by_ids method."""

    @pytest.mark.asyncio
    async def test_get_chunks_by_ids(self, postgres_store, mock_connection):
        """Test retrieving multiple chunks by their IDs."""
        chunk_id_1 = uuid4()
        chunk_id_2 = uuid4()

        mock_connection.set_fetch(
            [
                {
                    "id": chunk_id_1,
                    "content": "Chunk 1",
                    "document_title": "Doc 1",
                    "chunk_index": 0,
                },
                {
                    "id": chunk_id_2,
                    "content": "Chunk 2",
                    "document_title": "Doc 1",
                    "chunk_index": 1,
                },
            ]
        )

        results = await postgres_store.get_chunks_by_ids([chunk_id_1, chunk_id_2])

        assert len(results) == 2
        assert results[0]["id"] == chunk_id_1
        assert results[1]["id"] == chunk_id_2

    @pytest.mark.asyncio
    async def test_get_chunks_by_ids_empty(self, postgres_store, mock_connection):
        """Test retrieving chunks with empty ID list."""
        mock_connection.set_fetch([])

        results = await postgres_store.get_chunks_by_ids([])

        assert len(results) == 0


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_store_chunks_empty_list(self, postgres_store, mock_connection):
        """Test storing empty chunk list."""
        doc_id = uuid4()

        result = await postgres_store.store_chunks(doc_id, [])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_session_messages_empty(self, postgres_store, mock_connection):
        """Test getting messages from empty session."""
        session_id = uuid4()
        mock_connection.set_fetch([])

        results = await postgres_store.get_session_messages(session_id)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_count_documents_none_returned(self, postgres_store, mock_connection):
        """Test count_documents when fetchrow returns None."""
        mock_connection.set_fetchrow(None)

        result = await postgres_store.count_documents()

        assert result == 0

    @pytest.mark.asyncio
    async def test_count_chunks_none_returned(self, postgres_store, mock_connection):
        """Test count_chunks when fetchrow returns None."""
        doc_id = uuid4()
        mock_connection.set_fetchrow(None)

        result = await postgres_store.count_chunks(doc_id)

        assert result == 0
