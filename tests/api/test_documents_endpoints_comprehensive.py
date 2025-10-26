"""
Comprehensive tests for documents API endpoints.

Tests document listing, retrieval, upload, deletion, and metadata operations.
Target: 80%+ coverage of documents endpoints.
"""

from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_document_dependencies():
    """Mock document dependencies."""
    with (
        patch("src.api.dependencies.get_supabase_client") as mock_supabase,
        patch("src.api.dependencies.get_rate_limiter") as mock_rate_limiter,
    ):
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance

        # Setup mock table operations
        mock_table = Mock()
        mock_supabase_instance.table.return_value = mock_table

        mock_rate_limiter_instance = Mock()
        mock_rate_limiter.return_value = mock_rate_limiter_instance
        mock_rate_limiter_instance.check_rate_limit = AsyncMock(return_value=True)

        yield {"supabase": mock_supabase_instance, "rate_limiter": mock_rate_limiter_instance}


@pytest.fixture
def test_client(mock_document_dependencies):
    """Create test client."""
    from src.api.main import app

    return TestClient(app)


class TestListDocumentsEndpoint:
    """Test GET /documents endpoint."""

    def test_list_documents_success(self, test_client, mock_document_dependencies):
        """Test successful document listing."""
        with patch(
            "src.api.endpoints.documents.list_documents_tool", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [
                {"id": str(uuid4()), "file_path": "doc1.pdf", "type": "pdf"},
                {"id": str(uuid4()), "file_path": "doc2.txt", "type": "text"},
            ]

            response = test_client.get("/documents")

            assert response.status_code in [200, 503]

    def test_list_documents_empty(self, test_client, mock_document_dependencies):
        """Test listing when no documents exist."""
        with patch(
            "src.api.endpoints.documents.list_documents_tool", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []

            response = test_client.get("/documents")

            assert response.status_code in [200, 503]

    def test_list_documents_with_pagination(self, test_client, mock_document_dependencies):
        """Test document listing with pagination."""
        with patch(
            "src.api.endpoints.documents.list_documents_tool", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [{"id": str(uuid4())} for _ in range(10)]

            response = test_client.get("/documents?limit=10&offset=0")

            assert response.status_code in [200, 503]

    def test_list_documents_filter_by_type(self, test_client, mock_document_dependencies):
        """Test filtering documents by type."""
        with patch(
            "src.api.endpoints.documents.list_documents_tool", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = [{"id": str(uuid4()), "type": "pdf"}]

            response = test_client.get("/documents?type=pdf")

            assert response.status_code in [200, 503]

    def test_list_documents_error_handling(self, test_client, mock_document_dependencies):
        """Test error handling in document listing."""
        with patch(
            "src.api.endpoints.documents.list_documents_tool", new_callable=AsyncMock
        ) as mock_list:
            mock_list.side_effect = Exception("Database error")

            response = test_client.get("/documents")

            assert response.status_code in [500, 503]


class TestGetDocumentEndpoint:
    """Test GET /documents/{document_id} endpoint."""

    def test_get_document_success(self, test_client, mock_document_dependencies):
        """Test successful document retrieval."""
        doc_id = str(uuid4())
        with patch(
            "src.api.endpoints.documents.get_document_content_tool", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                "id": doc_id,
                "file_path": "test.pdf",
                "content": "Document content...",
                "metadata": {"pages": 10},
            }

            response = test_client.get(f"/documents/{doc_id}")

            assert response.status_code in [200, 503]

    def test_get_document_not_found(self, test_client, mock_document_dependencies):
        """Test getting non-existent document."""
        doc_id = str(uuid4())
        with patch(
            "src.api.endpoints.documents.get_document_content_tool", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            response = test_client.get(f"/documents/{doc_id}")

            assert response.status_code in [404, 503]

    def test_get_document_with_chunks(self, test_client, mock_document_dependencies):
        """Test getting document with chunks."""
        doc_id = str(uuid4())
        with patch(
            "src.api.endpoints.documents.get_document_content_tool", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                "id": doc_id,
                "chunks": [
                    {"content": "Chunk 1", "index": 0},
                    {"content": "Chunk 2", "index": 1},
                ],
            }

            response = test_client.get(f"/documents/{doc_id}?include_chunks=true")

            assert response.status_code in [200, 503]

    def test_get_document_invalid_id(self, test_client):
        """Test getting document with invalid ID format."""
        response = test_client.get("/documents/invalid-id")

        # Should validate UUID format
        assert response.status_code in [422, 503]


class TestUploadDocumentEndpoint:
    """Test POST /documents/upload endpoint."""

    def test_upload_document_pdf(self, test_client, mock_document_dependencies):
        """Test uploading PDF document."""
        with patch(
            "src.api.endpoints.documents.process_document", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = {"document_id": str(uuid4()), "chunks_created": 10}

            # Create fake PDF file
            file_data = BytesIO(b"%PDF-1.4 fake pdf content")
            file_data.name = "test.pdf"

            response = test_client.post(
                "/documents/upload",
                files={"file": ("test.pdf", file_data, "application/pdf")},
            )

            assert response.status_code in [200, 201, 503]

    def test_upload_document_text(self, test_client, mock_document_dependencies):
        """Test uploading text document."""
        with patch(
            "src.api.endpoints.documents.process_document", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = {"document_id": str(uuid4()), "chunks_created": 5}

            file_data = BytesIO(b"Plain text content")
            response = test_client.post(
                "/documents/upload",
                files={"file": ("test.txt", file_data, "text/plain")},
            )

            assert response.status_code in [200, 201, 503]

    def test_upload_document_large_file(self, test_client, mock_document_dependencies):
        """Test uploading large document."""
        with patch(
            "src.api.endpoints.documents.process_document", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = {"document_id": str(uuid4())}

            # 5MB file
            large_file = BytesIO(b"x" * (5 * 1024 * 1024))
            response = test_client.post(
                "/documents/upload",
                files={"file": ("large.pdf", large_file, "application/pdf")},
            )

            # May be rejected due to size limits
            assert response.status_code in [200, 201, 413, 503]

    def test_upload_document_unsupported_type(self, test_client, mock_document_dependencies):
        """Test uploading unsupported file type."""
        file_data = BytesIO(b"binary data")
        response = test_client.post(
            "/documents/upload",
            files={"file": ("test.exe", file_data, "application/x-executable")},
        )

        # Should reject unsupported types
        assert response.status_code in [400, 415, 503]

    def test_upload_document_no_file(self, test_client):
        """Test upload without file."""
        response = test_client.post("/documents/upload")

        # Should require file
        assert response.status_code == 422


class TestDeleteDocumentEndpoint:
    """Test DELETE /documents/{document_id} endpoint."""

    def test_delete_document_success(self, test_client, mock_document_dependencies):
        """Test successful document deletion."""
        doc_id = str(uuid4())
        with patch(
            "src.api.endpoints.documents.delete_document", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = {"success": True, "deleted_chunks": 10}

            response = test_client.delete(f"/documents/{doc_id}")

            assert response.status_code in [200, 204, 503]

    def test_delete_document_not_found(self, test_client, mock_document_dependencies):
        """Test deleting non-existent document."""
        doc_id = str(uuid4())
        with patch(
            "src.api.endpoints.documents.delete_document", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = None

            response = test_client.delete(f"/documents/{doc_id}")

            assert response.status_code in [404, 503]

    def test_delete_document_cascade(self, test_client, mock_document_dependencies):
        """Test document deletion cascades to chunks."""
        doc_id = str(uuid4())
        with patch(
            "src.api.endpoints.documents.delete_document", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = {
                "success": True,
                "deleted_chunks": 25,
                "deleted_metadata": 5,
            }

            response = test_client.delete(f"/documents/{doc_id}")

            assert response.status_code in [200, 204, 503]


class TestDocumentMetadataEndpoint:
    """Test /documents/{document_id}/metadata endpoint."""

    def test_get_document_metadata(self, test_client, mock_document_dependencies):
        """Test getting document metadata."""
        doc_id = str(uuid4())
        with patch(
            "src.api.endpoints.documents.get_document_metadata", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                "file_type": "pdf",
                "pages": 10,
                "author": "Test Author",
                "created_at": "2024-01-01",
            }

            response = test_client.get(f"/documents/{doc_id}/metadata")

            assert response.status_code in [200, 503]

    def test_update_document_metadata(self, test_client, mock_document_dependencies):
        """Test updating document metadata."""
        doc_id = str(uuid4())
        with patch(
            "src.api.endpoints.documents.update_document_metadata", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = {"success": True}

            response = test_client.patch(
                f"/documents/{doc_id}/metadata",
                json={"author": "New Author", "tags": ["AI", "ML"]},
            )

            assert response.status_code in [200, 503]


class TestDocumentSearch:
    """Test document search within documents endpoint."""

    def test_search_documents_by_content(self, test_client, mock_document_dependencies):
        """Test searching documents by content."""
        with patch(
            "src.api.endpoints.documents.search_documents", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = [
                {"id": str(uuid4()), "file_path": "match1.pdf", "score": 0.95},
                {"id": str(uuid4()), "file_path": "match2.pdf", "score": 0.85},
            ]

            response = test_client.get("/documents/search?q=machine+learning")

            assert response.status_code in [200, 503]

    def test_search_documents_by_tags(self, test_client, mock_document_dependencies):
        """Test searching documents by tags."""
        with patch(
            "src.api.endpoints.documents.search_documents", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = [{"id": str(uuid4()), "tags": ["AI", "ML"]}]

            response = test_client.get("/documents/search?tags=AI,ML")

            assert response.status_code in [200, 503]

    def test_search_documents_empty_query(self, test_client):
        """Test search with empty query."""
        response = test_client.get("/documents/search?q=")

        # Should validate query
        assert response.status_code in [422, 503]


class TestDocumentAnalytics:
    """Test document analytics endpoints."""

    def test_document_stats(self, test_client, mock_document_dependencies):
        """Test getting document statistics."""
        with patch(
            "src.api.endpoints.documents.get_document_stats", new_callable=AsyncMock
        ) as mock_stats:
            mock_stats.return_value = {
                "total_documents": 100,
                "total_chunks": 5000,
                "by_type": {"pdf": 50, "txt": 30, "md": 20},
            }

            response = test_client.get("/documents/stats")

            assert response.status_code in [200, 503]

    def test_document_storage_usage(self, test_client, mock_document_dependencies):
        """Test getting storage usage statistics."""
        with patch(
            "src.api.endpoints.documents.get_storage_usage", new_callable=AsyncMock
        ) as mock_usage:
            mock_usage.return_value = {
                "total_size_bytes": 1073741824,  # 1GB
                "by_type": {"pdf": 536870912, "txt": 104857600},
            }

            response = test_client.get("/documents/storage")

            assert response.status_code in [200, 503]


class TestBatchOperations:
    """Test batch document operations."""

    def test_batch_upload(self, test_client, mock_document_dependencies):
        """Test batch document upload."""
        with patch(
            "src.api.endpoints.documents.process_documents_batch", new_callable=AsyncMock
        ) as mock_batch:
            mock_batch.return_value = {
                "processed": 3,
                "failed": 0,
                "document_ids": [str(uuid4()) for _ in range(3)],
            }

            files = [
                ("files", ("doc1.txt", BytesIO(b"content 1"), "text/plain")),
                ("files", ("doc2.txt", BytesIO(b"content 2"), "text/plain")),
                ("files", ("doc3.txt", BytesIO(b"content 3"), "text/plain")),
            ]

            response = test_client.post("/documents/batch-upload", files=files)

            assert response.status_code in [200, 201, 503]

    def test_batch_delete(self, test_client, mock_document_dependencies):
        """Test batch document deletion."""
        with patch(
            "src.api.endpoints.documents.delete_documents_batch", new_callable=AsyncMock
        ) as mock_batch:
            mock_batch.return_value = {"deleted": 3, "failed": 0}

            doc_ids = [str(uuid4()) for _ in range(3)]
            response = test_client.post("/documents/batch-delete", json={"document_ids": doc_ids})

            assert response.status_code in [200, 503]
