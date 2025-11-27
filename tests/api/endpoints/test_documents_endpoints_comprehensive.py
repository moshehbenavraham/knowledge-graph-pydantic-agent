"""
Comprehensive tests for api/endpoints/documents.py - Document management endpoints.

Tests cover:
- Document ingestion (success and failure)
- Document listing with pagination and filtering
- Document retrieval (with and without chunks)
- Document deletion
- Document metadata updates
- Document reindexing
- Document statistics
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_graphiti_client, get_postgres_store
from src.api.endpoints.documents import router


@pytest.fixture
def mock_postgres_store():
    """Mock PostgresStore."""
    store = Mock()
    store.list_documents = AsyncMock(return_value=[])
    store.count_documents = AsyncMock(return_value=0)
    store.get_document = AsyncMock(return_value=None)
    store.get_document_chunks = AsyncMock(return_value=[])
    store.delete_document = AsyncMock(return_value=True)
    store.update_document = AsyncMock(return_value=True)
    store.count_chunks = AsyncMock(return_value=0)
    return store


@pytest.fixture
def mock_graphiti_client():
    """Mock Graphiti client."""
    return Mock()


@pytest.fixture
def mock_ingestion_pipeline():
    """Mock DocumentIngestionPipeline."""
    with patch("src.api.endpoints.documents.IngestionPipeline") as mock_pipeline:
        instance = Mock()
        instance.ingest_document = AsyncMock()
        mock_pipeline.return_value = instance
        yield instance


@pytest.fixture
def app(mock_postgres_store, mock_graphiti_client):
    """Create FastAPI test app with dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    # Override dependencies using FastAPI's dependency_overrides
    async def get_mock_postgres_store():
        return mock_postgres_store

    async def get_mock_graphiti_client():
        return mock_graphiti_client

    app.dependency_overrides[get_postgres_store] = get_mock_postgres_store
    app.dependency_overrides[get_graphiti_client] = get_mock_graphiti_client

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# ====================
# Document Ingestion Tests
# ====================


class TestDocumentIngestion:
    """Test document ingestion endpoint."""

    def test_ingest_document_success(
        self, client, mock_postgres_store, mock_graphiti_client, mock_ingestion_pipeline
    ):
        """Test successful document ingestion."""
        # Mock ingestion result
        mock_result = Mock()
        mock_result.document_id = "doc123"
        mock_result.chunks_created = 5
        mock_result.entities_extracted = 3
        mock_result.relationships_extracted = 2
        mock_ingestion_pipeline.ingest_document.return_value = mock_result

        response = client.post(
            "/api/v1/documents",
            json={
                "title": "Test Document",
                "content": "This is test content.",
                "source": "test_source",
                "metadata": {"author": "tester"},
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["document_id"] == "doc123"
        assert data["chunks_created"] == 5
        assert data["entities_extracted"] == 3
        assert data["status"] == "completed"
        assert "processing_time_ms" in data

    def test_ingest_document_failure(
        self, client, mock_postgres_store, mock_graphiti_client, mock_ingestion_pipeline
    ):
        """Test document ingestion failure."""
        mock_ingestion_pipeline.ingest_document.side_effect = RuntimeError("Ingestion failed")

        response = client.post(
            "/api/v1/documents",
            json={
                "title": "Test Document",
                "content": "This is test content.",
                "source": "test_source",
            },
        )

        assert response.status_code == 500
        assert "ingestion failed" in response.json()["detail"].lower()


# ====================
# Document Listing Tests
# ====================


class TestDocumentListing:
    """Test document listing endpoint."""

    def test_list_documents_empty(self, client, mock_postgres_store, mock_graphiti_client):
        """Test listing when no documents exist."""
        mock_postgres_store.list_documents.return_value = []
        mock_postgres_store.count_documents.return_value = 0

        response = client.get("/api/v1/documents")

        assert response.status_code == 200
        data = response.json()

        assert data["documents"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["has_more"] is False

    def test_list_documents_with_data(self, client, mock_postgres_store):
        """Test listing with documents."""
        now = datetime.now(UTC).isoformat()

        mock_documents = [
            {
                "id": "doc1",
                "title": "Document 1",
                "source": "source1",
                "created_at": now,
                "updated_at": now,
                "chunk_count": 5,
                "metadata": {"author": "user1"},
            },
            {
                "id": "doc2",
                "title": "Document 2",
                "source": "source2",
                "created_at": now,
                "chunk_count": 3,
            },
        ]

        mock_postgres_store.list_documents.return_value = mock_documents
        mock_postgres_store.count_documents.return_value = 2

        response = client.get("/api/v1/documents")

        assert response.status_code == 200
        data = response.json()

        assert len(data["documents"]) == 2
        assert data["total"] == 2
        assert data["documents"][0]["id"] == "doc1"
        assert data["documents"][1]["id"] == "doc2"

    def test_list_documents_pagination(self, client, mock_postgres_store):
        """Test document listing with pagination."""
        now = datetime.now(UTC).isoformat()

        mock_documents = [
            {
                "id": f"doc{i}",
                "title": f"Document {i}",
                "source": "source",
                "created_at": now,
                "chunk_count": 1,
            }
            for i in range(10)
        ]

        mock_postgres_store.list_documents.return_value = mock_documents
        mock_postgres_store.count_documents.return_value = 50

        response = client.get("/api/v1/documents?page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total"] == 50
        assert data["has_more"] is True

    def test_list_documents_with_source_filter(self, client, mock_postgres_store):
        """Test document listing with source filter."""
        now = datetime.now(UTC).isoformat()

        mock_documents = [
            {
                "id": "doc1",
                "title": "Document 1",
                "source": "pdf",
                "created_at": now,
                "chunk_count": 1,
            }
        ]

        mock_postgres_store.list_documents.return_value = mock_documents
        mock_postgres_store.count_documents.return_value = 1

        response = client.get("/api/v1/documents?source_filter=pdf")

        assert response.status_code == 200
        data = response.json()

        assert len(data["documents"]) == 1
        assert data["documents"][0]["source"] == "pdf"

        # Verify filter was passed
        mock_postgres_store.list_documents.assert_called_once()
        call_args = mock_postgres_store.list_documents.call_args
        assert call_args[1]["source_filter"] == "pdf"

    def test_list_documents_failure(self, client, mock_postgres_store):
        """Test document listing failure."""
        mock_postgres_store.list_documents.side_effect = RuntimeError("Database error")

        response = client.get("/api/v1/documents")

        assert response.status_code == 500
        assert "failed to list documents" in response.json()["detail"].lower()


# ====================
# Get Document Tests
# ====================


class TestGetDocument:
    """Test document retrieval endpoint."""

    def test_get_document_success(self, client, mock_postgres_store):
        """Test successful document retrieval."""
        now = datetime.now(UTC).isoformat()

        mock_document = {
            "id": "doc1",
            "title": "Test Document",
            "source": "test",
            "content": "Full document content here",
            "created_at": now,
            "updated_at": now,
            "chunk_count": 3,
            "metadata": {"author": "tester"},
        }

        mock_postgres_store.get_document.return_value = mock_document

        response = client.get("/api/v1/documents/doc1")

        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["id"] == "doc1"
        assert data["metadata"]["title"] == "Test Document"
        assert data["content"] == "Full document content here"
        assert data["chunks"] is None

    def test_get_document_with_chunks(self, client, mock_postgres_store):
        """Test document retrieval with chunks."""
        now = datetime.now(UTC).isoformat()

        mock_document = {
            "id": "doc1",
            "title": "Test Document",
            "source": "test",
            "content": "Full content",
            "created_at": now,
            "chunk_count": 2,
        }

        # Mock chunks from database (get_document_chunks returns dicts)
        mock_chunks = [
            {"id": "chunk1", "content": "Chunk 1 content", "chunk_index": 0, "token_count": 50},
            {"id": "chunk2", "content": "Chunk 2 content", "chunk_index": 1, "token_count": 45},
        ]

        mock_postgres_store.get_document.return_value = mock_document
        mock_postgres_store.get_document_chunks.return_value = mock_chunks

        response = client.get("/api/v1/documents/doc1?include_chunks=true")

        assert response.status_code == 200
        data = response.json()

        assert data["chunks"] is not None
        assert len(data["chunks"]) == 2
        assert data["chunks"][0] == "Chunk 1 content"

    def test_get_document_not_found(self, client, mock_postgres_store):
        """Test get non-existent document."""
        mock_postgres_store.get_document.return_value = None

        response = client.get("/api/v1/documents/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_document_failure(self, client, mock_postgres_store):
        """Test document retrieval failure."""
        mock_postgres_store.get_document.side_effect = RuntimeError("Database error")

        response = client.get("/api/v1/documents/doc1")

        assert response.status_code == 500
        assert "failed to retrieve document" in response.json()["detail"].lower()


# ====================
# Delete Document Tests
# ====================


class TestDeleteDocument:
    """Test document deletion endpoint."""

    def test_delete_document_success(self, client, mock_postgres_store, mock_graphiti_client):
        """Test successful document deletion."""
        now = datetime.now(UTC).isoformat()

        mock_document = {
            "id": "doc1",
            "title": "Test Document",
            "source": "test",
            "created_at": now,
        }

        mock_postgres_store.get_document.return_value = mock_document
        mock_postgres_store.delete_document.return_value = True

        response = client.delete("/api/v1/documents/doc1")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "deleted"
        assert data["document_id"] == "doc1"

        # Verify deletion was called
        mock_postgres_store.delete_document.assert_called_once_with("doc1")

    def test_delete_document_not_found(self, client, mock_postgres_store, mock_graphiti_client):
        """Test deleting non-existent document."""
        mock_postgres_store.get_document.return_value = None

        response = client.delete("/api/v1/documents/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_document_failure(self, client, mock_postgres_store, mock_graphiti_client):
        """Test document deletion failure."""
        now = datetime.now(UTC).isoformat()

        mock_document = {"id": "doc1", "created_at": now}
        mock_postgres_store.get_document.return_value = mock_document
        mock_postgres_store.delete_document.side_effect = RuntimeError("Deletion failed")

        response = client.delete("/api/v1/documents/doc1")

        assert response.status_code == 500
        assert "failed to delete document" in response.json()["detail"].lower()


# ====================
# Update Document Tests
# ====================


class TestUpdateDocument:
    """Test document update endpoint."""

    def test_update_document_title(self, client, mock_postgres_store):
        """Test updating document title."""
        now = datetime.now(UTC).isoformat()

        mock_document = {
            "id": "doc1",
            "title": "Old Title",
            "source": "test",
            "created_at": now,
        }

        mock_postgres_store.get_document.return_value = mock_document
        mock_postgres_store.update_document.return_value = True

        response = client.patch("/api/v1/documents/doc1?title=New Title")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "updated"
        assert data["updates"]["title"] == "New Title"

    def test_update_document_not_found(self, client, mock_postgres_store):
        """Test updating non-existent document."""
        mock_postgres_store.get_document.return_value = None

        response = client.patch("/api/v1/documents/nonexistent?title=New Title")

        assert response.status_code == 404

    def test_update_document_no_updates(self, client, mock_postgres_store):
        """Test update with no fields provided."""
        now = datetime.now(UTC).isoformat()

        mock_document = {"id": "doc1", "created_at": now}
        mock_postgres_store.get_document.return_value = mock_document

        response = client.patch("/api/v1/documents/doc1")

        assert response.status_code == 400
        assert "no updates provided" in response.json()["detail"].lower()


# ====================
# Reindex Document Tests
# ====================


class TestReindexDocument:
    """Test document reindexing endpoint."""

    def test_reindex_document_success(self, client, mock_postgres_store, mock_graphiti_client):
        """Test successful document reindexing."""
        now = datetime.now(UTC).isoformat()

        mock_document = {"id": "doc1", "created_at": now}
        mock_postgres_store.get_document.return_value = mock_document

        response = client.post("/api/v1/documents/doc1/reindex")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "reindexed"
        assert data["document_id"] == "doc1"

    def test_reindex_document_not_found(self, client, mock_postgres_store, mock_graphiti_client):
        """Test reindexing non-existent document."""
        mock_postgres_store.get_document.return_value = None

        response = client.post("/api/v1/documents/nonexistent/reindex")

        assert response.status_code == 404


# ====================
# Document Stats Tests
# ====================


class TestDocumentStats:
    """Test document statistics endpoint."""

    def test_get_document_stats_success(self, client, mock_postgres_store, mock_graphiti_client):
        """Test successful document stats retrieval."""
        now = datetime.now(UTC).isoformat()

        mock_document = {"id": "doc1", "created_at": now}
        mock_postgres_store.get_document.return_value = mock_document
        mock_postgres_store.count_chunks.return_value = 5

        response = client.get("/api/v1/documents/doc1/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["document_id"] == "doc1"
        assert data["chunk_count"] == 5
        assert "entity_count" in data
        assert "relationship_count" in data

    def test_get_document_stats_not_found(self, client, mock_postgres_store, mock_graphiti_client):
        """Test stats for non-existent document."""
        mock_postgres_store.get_document.return_value = None

        response = client.get("/api/v1/documents/nonexistent/stats")

        assert response.status_code == 404
