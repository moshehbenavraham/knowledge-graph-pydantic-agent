"""
Comprehensive tests for SupabaseRestStore - REST API alternative to PostgresStore.

Covers:
- Document storage and retrieval
- Chunk storage with embeddings
- Metadata updates
- Vector similarity search via RPC
- Document/chunk deletion
- Error handling
"""

import json
import pytest
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from src.agentic_rag.storage.supabase_rest_store import SupabaseRestStore


# ===== Fixtures =====


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    client = Mock()
    return client


@pytest.fixture
def supabase_store(mock_supabase_client):
    """Create SupabaseRestStore with mocked client."""
    with patch("src.agentic_rag.storage.supabase_rest_store.create_client", return_value=mock_supabase_client):
        store = SupabaseRestStore(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )
        return store


@pytest.fixture
def sample_document_id():
    """Sample document UUID."""
    return uuid4()


# ===== Initialization Tests =====


class TestSupabaseRestStoreInit:
    """Test SupabaseRestStore initialization."""

    def test_init_creates_client(self):
        """Test that initialization creates Supabase client."""
        with patch("src.agentic_rag.storage.supabase_rest_store.create_client") as mock_create:
            mock_client = Mock()
            mock_create.return_value = mock_client

            store = SupabaseRestStore("https://test.supabase.co", "test_key")

            assert store.client == mock_client
            mock_create.assert_called_once_with("https://test.supabase.co", "test_key")


# ===== Document Storage Tests =====


@pytest.mark.asyncio
class TestStoreDocument:
    """Test document storage."""

    async def test_store_document_success(self, supabase_store):
        """Test successful document storage."""
        doc_id = uuid4()
        mock_result = Mock()
        mock_result.data = [{"id": str(doc_id)}]

        supabase_store.client.table.return_value.insert.return_value.execute.return_value = mock_result

        result_id = await supabase_store.store_document(
            title="Test Doc",
            source="test.pdf",
            content="Test content",
            metadata={"page": 1}
        )

        assert result_id == doc_id
        supabase_store.client.table.assert_called_with("documents")

    async def test_store_document_with_default_metadata(self, supabase_store):
        """Test document storage with default empty metadata."""
        doc_id = uuid4()
        mock_result = Mock()
        mock_result.data = [{"id": str(doc_id)}]

        supabase_store.client.table.return_value.insert.return_value.execute.return_value = mock_result

        await supabase_store.store_document(
            title="Test Doc",
            source="test.pdf",
            content="Test content"
        )

        # Verify metadata defaults to empty dict
        call_args = supabase_store.client.table.return_value.insert.call_args
        doc_data = call_args[0][0]
        assert doc_data["metadata"] == {}

    async def test_store_document_no_id_returned(self, supabase_store):
        """Test error when no document ID is returned."""
        mock_result = Mock()
        mock_result.data = []

        supabase_store.client.table.return_value.insert.return_value.execute.return_value = mock_result

        with pytest.raises(ValueError, match="No document ID returned"):
            await supabase_store.store_document("Test", "test.pdf", "content")

    async def test_store_document_error_handling(self, supabase_store):
        """Test error handling during document storage."""
        supabase_store.client.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            await supabase_store.store_document("Test", "test.pdf", "content")


# ===== Chunk Storage Tests =====


@pytest.mark.asyncio
class TestStoreChunks:
    """Test chunk storage."""

    async def test_store_chunks_basic(self, supabase_store, sample_document_id):
        """Test storing basic chunks."""
        chunks = [
            {"content": "Chunk 1"},
            {"content": "Chunk 2"},
        ]

        chunk_ids = [uuid4(), uuid4()]
        mock_result = Mock()
        mock_result.data = [{"id": str(chunk_id)} for chunk_id in chunk_ids]

        supabase_store.client.table.return_value.insert.return_value.execute.return_value = mock_result

        result_ids = await supabase_store.store_chunks(sample_document_id, chunks)

        assert len(result_ids) == 2
        assert result_ids == chunk_ids

    async def test_store_chunks_with_embeddings(self, supabase_store, sample_document_id):
        """Test storing chunks with embeddings."""
        chunks = [
            {
                "content": "Chunk 1",
                "embedding_1536": [0.1] * 1536,
                "embedding_768": [0.2] * 768,
            }
        ]

        chunk_id = uuid4()
        mock_result = Mock()
        mock_result.data = [{"id": str(chunk_id)}]

        supabase_store.client.table.return_value.insert.return_value.execute.return_value = mock_result

        await supabase_store.store_chunks(sample_document_id, chunks)

        # Verify embeddings were included
        call_args = supabase_store.client.table.return_value.insert.call_args
        chunk_records = call_args[0][0]
        assert "embedding_1536" in chunk_records[0]
        assert "embedding_768" in chunk_records[0]

    async def test_store_chunks_with_metadata(self, supabase_store, sample_document_id):
        """Test storing chunks with metadata."""
        chunks = [
            {
                "content": "Chunk 1",
                "metadata": {"section": "intro"},
                "start_char": 0,
                "end_char": 100,
                "token_count": 20,
            }
        ]

        chunk_id = uuid4()
        mock_result = Mock()
        mock_result.data = [{"id": str(chunk_id)}]

        supabase_store.client.table.return_value.insert.return_value.execute.return_value = mock_result

        await supabase_store.store_chunks(sample_document_id, chunks)

        # Verify metadata was included
        call_args = supabase_store.client.table.return_value.insert.call_args
        chunk_records = call_args[0][0]
        assert chunk_records[0]["metadata"] == {"section": "intro"}
        assert chunk_records[0]["token_count"] == 20

    async def test_store_chunks_no_ids_returned(self, supabase_store, sample_document_id):
        """Test error when no chunk IDs are returned."""
        chunks = [{"content": "Chunk 1"}]
        mock_result = Mock()
        mock_result.data = None

        supabase_store.client.table.return_value.insert.return_value.execute.return_value = mock_result

        with pytest.raises(ValueError, match="No chunk IDs returned"):
            await supabase_store.store_chunks(sample_document_id, chunks)


# ===== Metadata Update Tests =====


@pytest.mark.asyncio
class TestUpdateChunkMetadata:
    """Test chunk metadata updates."""

    async def test_update_metadata_success(self, supabase_store):
        """Test successful metadata update."""
        chunk_id = uuid4()

        # Mock existing chunk
        mock_select_result = Mock()
        mock_select_result.data = [{"metadata": {"existing": "value"}}]

        supabase_store.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_select_result

        # Mock update
        mock_update_result = Mock()
        supabase_store.client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_result

        await supabase_store.update_chunk_metadata(
            chunk_id,
            {"new_field": "new_value"}
        )

        # Verify update was called
        assert supabase_store.client.table.return_value.update.called

    async def test_update_metadata_merges_existing(self, supabase_store):
        """Test that metadata is merged with existing data."""
        chunk_id = uuid4()

        mock_select_result = Mock()
        mock_select_result.data = [{"metadata": {"existing": "value"}}]

        supabase_store.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_select_result

        await supabase_store.update_chunk_metadata(
            chunk_id,
            {"new_field": "new_value"}
        )

        # Verify merged metadata
        call_args = supabase_store.client.table.return_value.update.call_args
        update_data = call_args[0][0]
        assert update_data["metadata"]["existing"] == "value"
        assert update_data["metadata"]["new_field"] == "new_value"

    async def test_update_metadata_handles_json_string(self, supabase_store):
        """Test handling of JSON string metadata."""
        chunk_id = uuid4()

        mock_select_result = Mock()
        mock_select_result.data = [{"metadata": json.dumps({"existing": "value"})}]

        supabase_store.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_select_result

        await supabase_store.update_chunk_metadata(chunk_id, {"new": "value"})

        # Should parse JSON and merge
        call_args = supabase_store.client.table.return_value.update.call_args
        update_data = call_args[0][0]
        assert "existing" in update_data["metadata"]

    async def test_update_metadata_chunk_not_found(self, supabase_store):
        """Test handling of non-existent chunk."""
        chunk_id = uuid4()

        mock_select_result = Mock()
        mock_select_result.data = []

        supabase_store.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_select_result

        # Should not raise, just log warning
        await supabase_store.update_chunk_metadata(chunk_id, {"field": "value"})


# ===== Search Tests =====


@pytest.mark.asyncio
class TestSearchSimilar:
    """Test vector similarity search."""

    async def test_search_similar_success(self, supabase_store):
        """Test successful similarity search."""
        query_embedding = [0.1] * 1536

        mock_result = Mock()
        mock_result.data = [
            {"id": str(uuid4()), "content": "Similar chunk 1", "similarity": 0.9},
            {"id": str(uuid4()), "content": "Similar chunk 2", "similarity": 0.85},
        ]

        supabase_store.client.rpc.return_value.execute.return_value = mock_result

        results = await supabase_store.search_similar(query_embedding, limit=10, threshold=0.7)

        assert len(results) == 2
        supabase_store.client.rpc.assert_called_once_with(
            "match_chunks",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.7,
                "match_count": 10,
            }
        )

    async def test_search_similar_no_results(self, supabase_store):
        """Test search with no results."""
        query_embedding = [0.1] * 1536

        mock_result = Mock()
        mock_result.data = []

        supabase_store.client.rpc.return_value.execute.return_value = mock_result

        results = await supabase_store.search_similar(query_embedding)

        assert results == []

    async def test_search_similar_rpc_not_implemented(self, supabase_store):
        """Test graceful fallback when RPC not implemented."""
        query_embedding = [0.1] * 1536

        supabase_store.client.rpc.return_value.execute.side_effect = Exception("RPC not found")

        # Should return empty, not raise
        results = await supabase_store.search_similar(query_embedding)

        assert results == []


# ===== Document Retrieval Tests =====


@pytest.mark.asyncio
class TestGetDocument:
    """Test document retrieval."""

    async def test_get_document_success(self, supabase_store, sample_document_id):
        """Test retrieving existing document."""
        mock_result = Mock()
        mock_result.data = [{
            "id": str(sample_document_id),
            "title": "Test Doc",
            "content": "Test content",
        }]

        supabase_store.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        doc = await supabase_store.get_document(sample_document_id)

        assert doc is not None
        assert doc["title"] == "Test Doc"

    async def test_get_document_not_found(self, supabase_store, sample_document_id):
        """Test retrieving non-existent document."""
        mock_result = Mock()
        mock_result.data = []

        supabase_store.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        doc = await supabase_store.get_document(sample_document_id)

        assert doc is None


# ===== Chunk Retrieval Tests =====


@pytest.mark.asyncio
class TestGetChunks:
    """Test chunk retrieval."""

    async def test_get_chunks_success(self, supabase_store, sample_document_id):
        """Test retrieving chunks for a document."""
        mock_result = Mock()
        mock_result.data = [
            {"id": str(uuid4()), "content": "Chunk 1", "chunk_index": 0},
            {"id": str(uuid4()), "content": "Chunk 2", "chunk_index": 1},
        ]

        supabase_store.client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        chunks = await supabase_store.get_chunks(sample_document_id)

        assert len(chunks) == 2
        assert chunks[0]["chunk_index"] == 0

    async def test_get_chunks_none(self, supabase_store, sample_document_id):
        """Test retrieving chunks when none exist."""
        mock_result = Mock()
        mock_result.data = []

        supabase_store.client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result

        chunks = await supabase_store.get_chunks(sample_document_id)

        assert chunks == []


# ===== Document Deletion Tests =====


@pytest.mark.asyncio
class TestDeleteDocument:
    """Test document deletion."""

    async def test_delete_document_success(self, supabase_store, sample_document_id):
        """Test successful document deletion."""
        mock_result = Mock()
        supabase_store.client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result

        result = await supabase_store.delete_document(sample_document_id)

        assert result is True
        # Should delete chunks first, then document
        assert supabase_store.client.table.call_count >= 2

    async def test_delete_document_error(self, supabase_store, sample_document_id):
        """Test error handling during deletion."""
        supabase_store.client.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception("Delete failed")

        result = await supabase_store.delete_document(sample_document_id)

        assert result is False
