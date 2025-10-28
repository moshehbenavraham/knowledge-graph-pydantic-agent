"""
Comprehensive tests for SupabaseRestStore.

Tests REST API operations for document and chunk storage using Supabase client.
"""

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from src.agentic_rag.storage.supabase_rest_store import SupabaseRestStore


class MockSupabaseResponse:
    """Mock Supabase API response."""

    def __init__(self, data=None, error=None):
        """Initialize mock response."""
        self.data = data or []
        self.error = error

    def execute(self):
        """Mock execute method."""
        if self.error:
            raise Exception(self.error)
        return self


class MockSupabaseTable:
    """Mock Supabase table operations."""

    def __init__(self):
        """Initialize mock table."""
        self.insert_data = None
        self.update_data = None
        self.eq_field = None
        self.eq_value = None
        self.order_field = None
        self.select_fields = None
        self.response_data = []
        self._current_operation = None

    def insert(self, data):
        """Mock insert operation."""
        self.insert_data = data
        self._current_operation = "insert"
        return self

    def update(self, data):
        """Mock update operation."""
        self.update_data = data
        self._current_operation = "update"
        return self

    def delete(self):
        """Mock delete operation."""
        self._current_operation = "delete"
        return self

    def select(self, fields="*"):
        """Mock select operation."""
        self.select_fields = fields
        self._current_operation = "select"
        return self

    def eq(self, field, value):
        """Mock eq filter."""
        self.eq_field = field
        self.eq_value = value
        return self

    def order(self, field):
        """Mock order operation."""
        self.order_field = field
        return self

    def execute(self):
        """Mock execute."""
        # For update/delete operations that follow eq, create a new response
        if self._current_operation in ["update", "delete"] and self.eq_field:
            return MockSupabaseResponse(data=self.response_data)
        return MockSupabaseResponse(data=self.response_data)

    def set_response(self, data):
        """Set response data for execute."""
        self.response_data = data


class MockSupabaseClient:
    """Mock Supabase client."""

    def __init__(self):
        """Initialize mock client."""
        self._tables = {}
        self.rpc_responses = {}

    def table(self, table_name):
        """Get or create mock table."""
        if table_name not in self._tables:
            self._tables[table_name] = MockSupabaseTable()
        return self._tables[table_name]

    @property
    def tables(self):
        """Access to internal tables for test setup."""
        return self._tables

    def rpc(self, function_name, params):
        """Mock RPC call."""
        response_data = self.rpc_responses.get(function_name, [])
        return MockSupabaseResponse(data=response_data)

    def set_rpc_response(self, function_name, data):
        """Set RPC response data."""
        self.rpc_responses[function_name] = data


@pytest.fixture
def mock_supabase_client():
    """Provide mock Supabase client."""
    return MockSupabaseClient()


@pytest.fixture
def supabase_store(mock_supabase_client):
    """Provide SupabaseRestStore with mocked client."""
    with patch("src.agentic_rag.storage.supabase_rest_store.create_client") as mock_create:
        mock_create.return_value = mock_supabase_client
        store = SupabaseRestStore(supabase_url="https://test.supabase.co", supabase_key="test_key")
        store.client = mock_supabase_client
        # Pre-create tables so tests can access them
        mock_supabase_client.table("documents")
        mock_supabase_client.table("chunks")
        return store


class TestStoreDocument:
    """Tests for store_document method."""

    @pytest.mark.asyncio
    async def test_store_document_success(self, supabase_store, mock_supabase_client):
        """Test successful document storage."""
        doc_id = uuid4()
        mock_supabase_client.tables["documents"].set_response([{"id": str(doc_id)}])

        result = await supabase_store.store_document(
            title="Test Doc", source="test.pdf", content="Test content", metadata={"key": "value"}
        )

        assert result == doc_id
        table = mock_supabase_client.tables["documents"]
        assert table.insert_data["title"] == "Test Doc"
        assert table.insert_data["source"] == "test.pdf"
        assert table.insert_data["metadata"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_store_document_no_metadata(self, supabase_store, mock_supabase_client):
        """Test document storage without metadata."""
        doc_id = uuid4()
        mock_supabase_client.tables["documents"].set_response([{"id": str(doc_id)}])

        result = await supabase_store.store_document(
            title="Test Doc", source="test.pdf", content="Test content"
        )

        assert result == doc_id
        table = mock_supabase_client.tables["documents"]
        assert table.insert_data["metadata"] == {}

    @pytest.mark.asyncio
    async def test_store_document_no_id_returned(self, supabase_store, mock_supabase_client):
        """Test document storage when no ID is returned."""
        mock_supabase_client.tables["documents"].set_response([])

        with pytest.raises(ValueError, match="No document ID returned"):
            await supabase_store.store_document(title="Test", source="test.pdf", content="Content")

    @pytest.mark.asyncio
    async def test_store_document_exception(self, supabase_store, mock_supabase_client):
        """Test document storage with exception."""
        mock_table = mock_supabase_client.tables["documents"]

        def mock_execute_with_error():
            raise Exception("Database connection failed")

        mock_table.execute = mock_execute_with_error

        with pytest.raises(Exception, match="Database connection failed"):
            await supabase_store.store_document(title="Test", source="test.pdf", content="Content")


class TestStoreChunks:
    """Tests for store_chunks method."""

    @pytest.mark.asyncio
    async def test_store_chunks_success(self, supabase_store, mock_supabase_client):
        """Test successful chunk storage."""
        doc_id = uuid4()
        chunk_id_1 = uuid4()
        chunk_id_2 = uuid4()

        mock_supabase_client.tables["chunks"].set_response(
            [{"id": str(chunk_id_1)}, {"id": str(chunk_id_2)}]
        )

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
                "metadata": {},
                "token_count": 150,
            },
        ]

        result = await supabase_store.store_chunks(doc_id, chunks)

        assert len(result) == 2
        assert result[0] == chunk_id_1
        assert result[1] == chunk_id_2

        table = mock_supabase_client.tables["chunks"]
        assert table.insert_data is not None
        assert len(table.insert_data) == 2

    @pytest.mark.asyncio
    async def test_store_chunks_with_defaults(self, supabase_store, mock_supabase_client):
        """Test chunk storage with default values."""
        doc_id = uuid4()
        chunk_id = uuid4()

        mock_supabase_client.tables["chunks"].set_response([{"id": str(chunk_id)}])

        chunks = [{"content": "Simple chunk"}]

        result = await supabase_store.store_chunks(doc_id, chunks)

        assert len(result) == 1
        table = mock_supabase_client.tables["chunks"]
        chunk_record = table.insert_data[0]
        assert chunk_record["chunk_index"] == 0
        assert chunk_record["start_char"] == 0
        assert chunk_record["end_char"] == 1000

    @pytest.mark.asyncio
    async def test_store_chunks_no_ids_returned(self, supabase_store, mock_supabase_client):
        """Test chunk storage when no IDs returned."""
        doc_id = uuid4()
        mock_supabase_client.tables["chunks"].set_response([])

        chunks = [{"content": "Test chunk"}]

        with pytest.raises(ValueError, match="No chunk IDs returned"):
            await supabase_store.store_chunks(doc_id, chunks)

    @pytest.mark.asyncio
    async def test_store_chunks_exception(self, supabase_store, mock_supabase_client):
        """Test chunk storage with exception."""
        doc_id = uuid4()
        mock_table = mock_supabase_client.tables["chunks"]

        def mock_execute_with_error():
            raise Exception("Insert failed")

        mock_table.execute = mock_execute_with_error

        chunks = [{"content": "Test"}]

        with pytest.raises(Exception, match="Insert failed"):
            await supabase_store.store_chunks(doc_id, chunks)


class TestUpdateChunkMetadata:
    """Tests for update_chunk_metadata method."""

    @pytest.mark.asyncio
    async def test_update_chunk_metadata_success(self, supabase_store, mock_supabase_client):
        """Test successful metadata update."""
        chunk_id = uuid4()

        # Mock select to return existing metadata
        mock_supabase_client.tables["chunks"].set_response([{"metadata": {"existing": "data"}}])

        await supabase_store.update_chunk_metadata(chunk_id, {"new_field": "new_value"})

        table = mock_supabase_client.tables["chunks"]
        # Should have called select and update
        assert table.eq_field == "id"
        assert table.eq_value == str(chunk_id)

    @pytest.mark.asyncio
    async def test_update_chunk_metadata_with_entity_refs(
        self, supabase_store, mock_supabase_client
    ):
        """Test metadata update with entity references."""
        chunk_id = uuid4()

        mock_supabase_client.tables["chunks"].set_response([{"metadata": {}}])

        await supabase_store.update_chunk_metadata(
            chunk_id, {"entity_refs": ["entity1", "entity2"], "other": "data"}
        )

        table = mock_supabase_client.tables["chunks"]
        assert table.update_data["entity_refs"] == ["entity1", "entity2"]

    @pytest.mark.asyncio
    async def test_update_chunk_metadata_not_found(self, supabase_store, mock_supabase_client):
        """Test metadata update when chunk not found."""
        chunk_id = uuid4()

        mock_supabase_client.tables["chunks"].set_response([])

        # Should log warning but not raise exception
        await supabase_store.update_chunk_metadata(chunk_id, {"field": "value"})

    @pytest.mark.asyncio
    async def test_update_chunk_metadata_json_string(self, supabase_store, mock_supabase_client):
        """Test metadata update when existing metadata is JSON string."""
        chunk_id = uuid4()

        # Return JSON string instead of dict
        mock_supabase_client.tables["chunks"].set_response(
            [{"metadata": '{"existing": "json_string"}'}]
        )

        await supabase_store.update_chunk_metadata(chunk_id, {"new": "value"})

        # Should parse JSON and merge
        table = mock_supabase_client.tables["chunks"]
        assert table.update_data is not None


class TestSearchSimilar:
    """Tests for search_similar method."""

    @pytest.mark.asyncio
    async def test_search_similar_success(self, supabase_store, mock_supabase_client):
        """Test successful vector search."""
        chunk_id = uuid4()
        mock_supabase_client.set_rpc_response(
            "match_chunks",
            [
                {
                    "id": str(chunk_id),
                    "content": "Similar content",
                    "similarity": 0.95,
                }
            ],
        )

        embedding = [0.1] * 1536
        results = await supabase_store.search_similar(embedding, limit=5, threshold=0.7)

        assert len(results) == 1
        assert UUID(results[0]["id"]) == chunk_id

    @pytest.mark.asyncio
    async def test_search_similar_no_results(self, supabase_store, mock_supabase_client):
        """Test vector search with no results."""
        mock_supabase_client.set_rpc_response("match_chunks", [])

        embedding = [0.1] * 1536
        results = await supabase_store.search_similar(embedding)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_similar_exception(self, supabase_store, mock_supabase_client):
        """Test vector search with exception (RPC not implemented)."""

        def mock_rpc_with_error(*args, **kwargs):
            raise Exception("RPC function not found")

        mock_supabase_client.rpc = mock_rpc_with_error

        embedding = [0.1] * 768
        results = await supabase_store.search_similar(embedding, embedding_column="embedding_768")

        # Should return empty list on exception
        assert len(results) == 0


class TestGetDocument:
    """Tests for get_document method."""

    @pytest.mark.asyncio
    async def test_get_document_found(self, supabase_store, mock_supabase_client):
        """Test retrieving existing document."""
        doc_id = uuid4()
        doc_data = {
            "id": str(doc_id),
            "title": "Test Doc",
            "content": "Content",
            "metadata": {"key": "value"},
        }

        mock_supabase_client.tables["documents"].set_response([doc_data])

        result = await supabase_store.get_document(doc_id)

        assert result is not None
        assert result["title"] == "Test Doc"
        assert UUID(result["id"]) == doc_id

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, supabase_store, mock_supabase_client):
        """Test retrieving non-existent document."""
        doc_id = uuid4()
        mock_supabase_client.tables["documents"].set_response([])

        result = await supabase_store.get_document(doc_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_document_exception(self, supabase_store, mock_supabase_client):
        """Test get_document with exception."""
        doc_id = uuid4()
        mock_table = mock_supabase_client.tables["documents"]

        def mock_execute_with_error():
            raise Exception("Connection failed")

        mock_table.execute = mock_execute_with_error

        result = await supabase_store.get_document(doc_id)

        # Should return None on exception
        assert result is None


class TestGetChunks:
    """Tests for get_chunks method."""

    @pytest.mark.asyncio
    async def test_get_chunks_success(self, supabase_store, mock_supabase_client):
        """Test retrieving chunks for a document."""
        doc_id = uuid4()
        chunks_data = [
            {"id": str(uuid4()), "content": "Chunk 1", "chunk_index": 0},
            {"id": str(uuid4()), "content": "Chunk 2", "chunk_index": 1},
        ]

        mock_supabase_client.tables["chunks"].set_response(chunks_data)

        results = await supabase_store.get_chunks(doc_id)

        assert len(results) == 2
        assert results[0]["content"] == "Chunk 1"
        assert results[1]["content"] == "Chunk 2"

    @pytest.mark.asyncio
    async def test_get_chunks_empty(self, supabase_store, mock_supabase_client):
        """Test retrieving chunks when none exist."""
        doc_id = uuid4()
        mock_supabase_client.tables["chunks"].set_response([])

        results = await supabase_store.get_chunks(doc_id)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_chunks_exception(self, supabase_store, mock_supabase_client):
        """Test get_chunks with exception."""
        doc_id = uuid4()
        mock_table = mock_supabase_client.tables["chunks"]

        def mock_execute_with_error():
            raise Exception("Query failed")

        mock_table.execute = mock_execute_with_error

        results = await supabase_store.get_chunks(doc_id)

        # Should return empty list on exception
        assert len(results) == 0


class TestDeleteDocument:
    """Tests for delete_document method."""

    @pytest.mark.asyncio
    async def test_delete_document_success(self, supabase_store, mock_supabase_client):
        """Test successful document deletion."""
        doc_id = uuid4()

        # Mock successful deletion
        mock_supabase_client.tables["chunks"].set_response([])
        mock_supabase_client.tables["documents"].set_response([])

        result = await supabase_store.delete_document(doc_id)

        assert result is True

        # Should have called delete on both tables
        chunks_table = mock_supabase_client.tables["chunks"]
        docs_table = mock_supabase_client.tables["documents"]

        assert chunks_table.eq_value == str(doc_id)
        assert docs_table.eq_value == str(doc_id)

    @pytest.mark.asyncio
    async def test_delete_document_exception(self, supabase_store, mock_supabase_client):
        """Test document deletion with exception."""
        doc_id = uuid4()
        mock_table = mock_supabase_client.tables["chunks"]

        def mock_execute_with_error():
            raise Exception("Delete failed")

        mock_table.execute = mock_execute_with_error

        result = await supabase_store.delete_document(doc_id)

        # Should return False on exception
        assert result is False


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_store_empty_chunks(self, supabase_store, mock_supabase_client):
        """Test storing empty chunk list."""
        doc_id = uuid4()
        mock_supabase_client.tables["chunks"].set_response([])

        with pytest.raises(ValueError):
            await supabase_store.store_chunks(doc_id, [])

    @pytest.mark.asyncio
    async def test_search_with_custom_embedding_column(self, supabase_store, mock_supabase_client):
        """Test search with custom embedding column parameter."""
        mock_supabase_client.set_rpc_response("match_chunks", [])

        embedding = [0.1] * 768
        results = await supabase_store.search_similar(embedding, embedding_column="embedding_768")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_initialization_logging(self, mock_supabase_client):
        """Test that initialization logs correctly."""
        with patch("src.agentic_rag.storage.supabase_rest_store.create_client") as mock_create:
            mock_create.return_value = mock_supabase_client

            store = SupabaseRestStore(
                supabase_url="https://test.supabase.co", supabase_key="test_key"
            )

            # Should have created client
            assert store.client is not None


class TestComplexScenarios:
    """Tests for complex multi-step scenarios."""

    @pytest.mark.asyncio
    async def test_document_lifecycle(self, supabase_store, mock_supabase_client):
        """Test complete document lifecycle: create, update metadata, retrieve, delete."""
        doc_id = uuid4()

        # 1. Create document
        mock_supabase_client.tables["documents"].set_response([{"id": str(doc_id)}])
        created_id = await supabase_store.store_document(
            title="Test", source="test.pdf", content="Content"
        )
        assert created_id == doc_id

        # 2. Store chunks
        chunk_id = uuid4()
        mock_supabase_client.tables["chunks"].set_response([{"id": str(chunk_id)}])
        chunks = [{"content": "Chunk 1", "token_count": 50}]
        chunk_ids = await supabase_store.store_chunks(doc_id, chunks)
        assert len(chunk_ids) == 1

        # 3. Update chunk metadata
        mock_supabase_client.tables["chunks"].set_response([{"metadata": {}}])
        await supabase_store.update_chunk_metadata(chunk_id, {"processed": True})

        # 4. Retrieve document
        mock_supabase_client.tables["documents"].set_response([{"id": str(doc_id)}])
        doc = await supabase_store.get_document(doc_id)
        assert doc is not None

        # 5. Delete document
        mock_supabase_client.tables["chunks"].set_response([])
        mock_supabase_client.tables["documents"].set_response([])
        deleted = await supabase_store.delete_document(doc_id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_batch_chunk_operations(self, supabase_store, mock_supabase_client):
        """Test storing and retrieving multiple chunks."""
        doc_id = uuid4()
        chunk_ids = [uuid4() for _ in range(10)]

        # Store 10 chunks
        mock_response = [{"id": str(cid)} for cid in chunk_ids]
        mock_supabase_client.tables["chunks"].set_response(mock_response)

        chunks = [{"content": f"Chunk {i}", "token_count": 100 + i * 10} for i in range(10)]

        result = await supabase_store.store_chunks(doc_id, chunks)

        assert len(result) == 10
        for i, chunk_id in enumerate(chunk_ids):
            assert result[i] == chunk_id
