"""
Enhanced tests for document management endpoints.

Target coverage: 20% → 75%+
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from src.api.endpoints.documents import (
    delete_document,
    get_document,
    get_document_stats,
    ingest_document,
    list_documents,
    reindex_document,
    update_document,
)
from src.api.models import IngestRequest


class TestIngestDocument:
    """Test document ingestion endpoint."""

    @pytest.mark.asyncio
    async def test_ingest_document_success(self):
        """Test successful document ingestion."""
        request = IngestRequest(
            content="Test document content",
            title="Test Document",
            source="test_source",
            metadata={"author": "Test Author"},
        )

        mock_store = AsyncMock()
        mock_graphiti = AsyncMock()

        mock_result = MagicMock()
        mock_result.document_id = "doc-123"
        mock_result.chunks_created = 5
        mock_result.entities_extracted = 10
        mock_result.get = lambda k, default: 3 if k == "relationships_extracted" else default

        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document.return_value = mock_result

        with patch("src.api.endpoints.documents.IngestionPipeline", return_value=mock_pipeline):
            with patch("src.api.endpoints.documents.ingest_requests_total"):
                with patch("src.api.endpoints.documents.ingest_duration"):
                    response = await ingest_document(
                        request=request,
                        postgres_store=mock_store,
                        graphiti_client=mock_graphiti,
                    )

        assert response.document_id == "doc-123"
        assert response.chunks_created == 5
        assert response.entities_extracted == 10
        assert response.status == "completed"
        assert response.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_ingest_document_error(self):
        """Test document ingestion with error."""
        request = IngestRequest(
            content="Test content",
            title="Test",
            source="test",
        )

        mock_store = AsyncMock()
        mock_graphiti = AsyncMock()

        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document.side_effect = Exception("Ingestion failed")

        with patch("src.api.endpoints.documents.IngestionPipeline", return_value=mock_pipeline):
            with patch("src.api.endpoints.documents.ingest_requests_total"):
                with pytest.raises(HTTPException) as exc_info:
                    await ingest_document(
                        request=request,
                        postgres_store=mock_store,
                        graphiti_client=mock_graphiti,
                    )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Document ingestion failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_ingest_document_metrics_recorded(self):
        """Test that ingestion metrics are recorded."""
        request = IngestRequest(content="Test", title="Test", source="test")

        mock_result = MagicMock()
        mock_result.document_id = "doc-123"
        mock_result.chunks_created = 3
        mock_result.entities_extracted = 5
        mock_result.get = lambda k, default: default

        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document.return_value = mock_result

        with patch("src.api.endpoints.documents.IngestionPipeline", return_value=mock_pipeline):
            with patch("src.api.endpoints.documents.ingest_requests_total") as mock_counter:
                with patch("src.api.endpoints.documents.ingest_duration") as mock_histogram:
                    await ingest_document(
                        request=request,
                        postgres_store=AsyncMock(),
                        graphiti_client=AsyncMock(),
                    )

                    mock_counter.labels.assert_called_with(status="success")
                    mock_histogram.observe.assert_called_once()


class TestListDocuments:
    """Test document listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_documents_default_pagination(self):
        """Test listing documents with default pagination."""
        mock_store = AsyncMock()
        mock_store.list_documents.return_value = [
            {
                "id": "doc-1",
                "title": "Document 1",
                "source": "test",
                "created_at": "2024-01-01T00:00:00Z",
                "chunk_count": 5,
            },
            {
                "id": "doc-2",
                "title": "Document 2",
                "source": "test",
                "created_at": "2024-01-02T00:00:00Z",
                "chunk_count": 3,
            },
        ]
        mock_store.count_documents.return_value = 2

        response = await list_documents(page=1, page_size=20, postgres_store=mock_store)

        assert len(response.documents) == 2
        assert response.total == 2
        assert response.page == 1
        assert response.page_size == 20
        assert response.has_more is False

    @pytest.mark.asyncio
    async def test_list_documents_with_pagination(self):
        """Test listing documents with custom pagination."""
        mock_store = AsyncMock()
        mock_store.list_documents.return_value = [
            {"id": f"doc-{i}", "title": f"Doc {i}", "source": "test", "created_at": "2024-01-01"}
            for i in range(10)
        ]
        mock_store.count_documents.return_value = 50

        response = await list_documents(page=2, page_size=10, postgres_store=mock_store)

        assert len(response.documents) == 10
        assert response.total == 50
        assert response.page == 2
        assert response.has_more is True
        # Verify offset calculation (page 2 with size 10 = offset 10)
        mock_store.list_documents.assert_called_once()
        call_kwargs = mock_store.list_documents.call_args[1]
        assert call_kwargs["offset"] == 10

    @pytest.mark.asyncio
    async def test_list_documents_with_source_filter(self):
        """Test listing documents with source filter."""
        mock_store = AsyncMock()
        mock_store.list_documents.return_value = [
            {"id": "doc-1", "title": "Doc 1", "source": "github", "created_at": "2024-01-01"}
        ]
        mock_store.count_documents.return_value = 1

        response = await list_documents(
            page=1, page_size=20, source_filter="github", postgres_store=mock_store
        )

        assert len(response.documents) == 1
        mock_store.count_documents.assert_called_with(source_filter="github")

    @pytest.mark.asyncio
    async def test_list_documents_empty(self):
        """Test listing documents with no results."""
        mock_store = AsyncMock()
        mock_store.list_documents.return_value = []
        mock_store.count_documents.return_value = 0

        response = await list_documents(page=1, page_size=20, postgres_store=mock_store)

        assert len(response.documents) == 0
        assert response.total == 0
        assert response.has_more is False

    @pytest.mark.asyncio
    async def test_list_documents_error(self):
        """Test listing documents with error."""
        mock_store = AsyncMock()
        mock_store.list_documents.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await list_documents(page=1, page_size=20, postgres_store=mock_store)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetDocument:
    """Test get document endpoint."""

    @pytest.mark.asyncio
    async def test_get_document_without_chunks(self):
        """Test getting document without chunk breakdown."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {
            "id": "doc-123",
            "title": "Test Document",
            "source": "test",
            "content": "Full document content",
            "created_at": "2024-01-01T00:00:00Z",
            "chunk_count": 5,
        }

        response = await get_document(
            document_id="doc-123", include_chunks=False, postgres_store=mock_store
        )

        assert response.metadata.id == "doc-123"
        assert response.content == "Full document content"
        assert response.chunks is None

    @pytest.mark.asyncio
    async def test_get_document_with_chunks(self):
        """Test getting document with chunk breakdown."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {
            "id": "doc-123",
            "title": "Test",
            "source": "test",
            "content": "Full content",
            "created_at": "2024-01-01",
            "chunk_count": 2,
        }
        mock_store.get_document_chunks.return_value = [
            {"id": "chunk-1", "content": "Chunk 1 content", "chunk_index": 0, "token_count": 50},
            {"id": "chunk-2", "content": "Chunk 2 content", "chunk_index": 1, "token_count": 45},
        ]

        response = await get_document(
            document_id="doc-123", include_chunks=True, postgres_store=mock_store
        )

        assert response.metadata.id == "doc-123"
        assert response.chunks is not None
        assert len(response.chunks) == 2
        assert response.chunks[0]["content"] == "Chunk 1 content"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self):
        """Test getting nonexistent document."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_document(document_id="nonexistent", postgres_store=mock_store)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Document not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_document_error(self):
        """Test getting document with error."""
        mock_store = AsyncMock()
        mock_store.get_document.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await get_document(document_id="doc-123", postgres_store=mock_store)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestDeleteDocument:
    """Test delete document endpoint."""

    @pytest.mark.asyncio
    async def test_delete_document_success(self):
        """Test successful document deletion."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {"id": "doc-123", "title": "Test"}
        mock_store.delete_document.return_value = True

        mock_graphiti = AsyncMock()

        response = await delete_document(
            document_id="doc-123", postgres_store=mock_store, graphiti_client=mock_graphiti
        )

        assert response["status"] == "deleted"
        assert response["document_id"] == "doc-123"
        mock_store.delete_document.assert_called_once_with("doc-123")

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self):
        """Test deleting nonexistent document."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await delete_document(
                document_id="nonexistent",
                postgres_store=mock_store,
                graphiti_client=AsyncMock(),
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_document_error(self):
        """Test document deletion with error."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {"id": "doc-123"}
        mock_store.delete_document.side_effect = Exception("Delete failed")

        with pytest.raises(HTTPException) as exc_info:
            await delete_document(
                document_id="doc-123",
                postgres_store=mock_store,
                graphiti_client=AsyncMock(),
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestUpdateDocument:
    """Test update document endpoint."""

    @pytest.mark.asyncio
    async def test_update_document_title(self):
        """Test updating document title."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {"id": "doc-123", "title": "Old Title"}
        mock_store.update_document.return_value = True

        response = await update_document(
            document_id="doc-123", title="New Title", postgres_store=mock_store
        )

        assert response["status"] == "updated"
        assert response["updates"]["title"] == "New Title"
        mock_store.update_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_document_metadata(self):
        """Test updating document metadata."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {"id": "doc-123"}
        mock_store.update_document.return_value = True

        new_metadata = {"author": "New Author", "tags": ["test"]}
        response = await update_document(
            document_id="doc-123", metadata=new_metadata, postgres_store=mock_store
        )

        assert response["status"] == "updated"
        assert response["updates"]["metadata"] == new_metadata

    @pytest.mark.asyncio
    async def test_update_document_both_fields(self):
        """Test updating both title and metadata."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {"id": "doc-123"}
        mock_store.update_document.return_value = True

        response = await update_document(
            document_id="doc-123",
            title="New Title",
            metadata={"key": "value"},
            postgres_store=mock_store,
        )

        assert len(response["updates"]) == 2

    @pytest.mark.asyncio
    async def test_update_document_no_updates(self):
        """Test update with no fields provided."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {"id": "doc-123"}

        with pytest.raises(HTTPException) as exc_info:
            await update_document(document_id="doc-123", postgres_store=mock_store)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "No updates provided" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_document_not_found(self):
        """Test updating nonexistent document."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await update_document(
                document_id="nonexistent", title="New Title", postgres_store=mock_store
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_document_update_failed(self):
        """Test update when database operation fails."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {"id": "doc-123"}
        mock_store.update_document.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await update_document(
                document_id="doc-123", title="New Title", postgres_store=mock_store
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestReindexDocument:
    """Test reindex document endpoint."""

    @pytest.mark.asyncio
    async def test_reindex_document_success(self):
        """Test successful document reindexing."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {"id": "doc-123", "title": "Test"}

        response = await reindex_document(
            document_id="doc-123", postgres_store=mock_store, graphiti_client=AsyncMock()
        )

        assert response["status"] == "reindexed"
        assert response["document_id"] == "doc-123"

    @pytest.mark.asyncio
    async def test_reindex_document_not_found(self):
        """Test reindexing nonexistent document."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await reindex_document(
                document_id="nonexistent",
                postgres_store=mock_store,
                graphiti_client=AsyncMock(),
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_reindex_document_error(self):
        """Test reindexing with error."""
        mock_store = AsyncMock()
        mock_store.get_document.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await reindex_document(
                document_id="doc-123",
                postgres_store=mock_store,
                graphiti_client=AsyncMock(),
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetDocumentStats:
    """Test get document stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_document_stats_success(self):
        """Test getting document statistics."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = {
            "id": "doc-123",
            "title": "Test",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_store.count_chunks.return_value = 10

        response = await get_document_stats(
            document_id="doc-123", postgres_store=mock_store, graphiti_client=AsyncMock()
        )

        assert response["document_id"] == "doc-123"
        assert response["chunk_count"] == 10
        assert response["entity_count"] == 0  # Not implemented yet
        assert response["relationship_count"] == 0  # Not implemented yet

    @pytest.mark.asyncio
    async def test_get_document_stats_not_found(self):
        """Test getting stats for nonexistent document."""
        mock_store = AsyncMock()
        mock_store.get_document.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_document_stats(
                document_id="nonexistent",
                postgres_store=mock_store,
                graphiti_client=AsyncMock(),
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_document_stats_error(self):
        """Test getting stats with error."""
        mock_store = AsyncMock()
        mock_store.get_document.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await get_document_stats(
                document_id="doc-123",
                postgres_store=mock_store,
                graphiti_client=AsyncMock(),
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestPrometheusMetrics:
    """Test Prometheus metrics for document endpoints."""

    def test_ingest_metrics_exist(self):
        """Test that ingestion metrics are defined."""
        from src.api.endpoints.documents import ingest_duration, ingest_requests_total

        assert ingest_requests_total is not None
        assert ingest_duration is not None

    def test_ingest_metrics_labels(self):
        """Test ingestion metrics accept correct labels."""
        from src.api.endpoints.documents import ingest_requests_total

        ingest_requests_total.labels(status="success")
        ingest_requests_total.labels(status="error")
