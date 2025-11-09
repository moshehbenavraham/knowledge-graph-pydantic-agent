"""
Unit tests for the Agentic RAG adapter.

Tests the integration layer between legacy RAG watchers
(Google Drive, Local Files) and the Agentic RAG pipeline.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.agentic_rag.ingestion.pipeline import IngestionResult
from src.rag_pipeline.adapters.agentic_rag_adapter import (
    process_file_with_agentic_rag,
    process_file_with_agentic_rag_sync,
)


class TestAgenticRAGAdapter:
    """Tests for the Agentic RAG adapter functions."""

    @pytest.fixture
    def sample_text(self):
        """Sample document text for testing."""
        return "This is a test document with some content for RAG processing."

    @pytest.fixture
    def sample_file_id(self):
        """Sample file ID."""
        return "/path/to/test_file.txt"

    @pytest.fixture
    def sample_file_title(self):
        """Sample file title."""
        return "test_file"

    @pytest.fixture
    def sample_file_url(self):
        """Sample file URL."""
        return "file:///path/to/test_file.txt"

    @pytest.fixture
    def successful_ingestion_result(self):
        """Mock successful ingestion result."""
        return IngestionResult(
            document_id=UUID("12345678-1234-5678-1234-567812345678"),
            title="test_file",
            source="file:///path/to/test_file.txt",
            chunks_created=5,
            entities_extracted=3,
            relationships_extracted=2,
            facts_extracted=4,
            processing_time=1.5,
            errors=[],
            metadata={"chunk_ids": ["chunk1", "chunk2", "chunk3", "chunk4", "chunk5"]},
        )

    @pytest.fixture
    def failed_ingestion_result(self):
        """Mock failed ingestion result."""
        return IngestionResult(
            document_id=UUID("00000000-0000-0000-0000-000000000000"),
            title="test_file",
            source="file:///path/to/test_file.txt",
            chunks_created=0,
            entities_extracted=0,
            relationships_extracted=0,
            facts_extracted=0,
            processing_time=0.5,
            errors=["Failed to chunk document", "Database connection error"],
        )

    @pytest.mark.asyncio
    async def test_adapter_basic_processing_success(
        self,
        sample_text,
        sample_file_id,
        sample_file_title,
        sample_file_url,
        successful_ingestion_result,
    ):
        """Test basic successful document processing through adapter."""
        # Mock the DocumentIngestionPipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document = AsyncMock(return_value=successful_ingestion_result)
        mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
        mock_pipeline.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.rag_pipeline.adapters.agentic_rag_adapter.DocumentIngestionPipeline",
            return_value=mock_pipeline,
        ):
            result = await process_file_with_agentic_rag(
                text=sample_text,
                file_id=sample_file_id,
                file_title=sample_file_title,
                file_url=sample_file_url,
                mime_type="text/plain",
                use_rest_api=False,
            )

        # Verify result
        assert result is True

        # Verify pipeline was called correctly
        mock_pipeline.ingest_document.assert_called_once()
        call_args = mock_pipeline.ingest_document.call_args
        assert call_args.kwargs["content"] == sample_text
        assert call_args.kwargs["title"] == sample_file_title
        assert call_args.kwargs["source"] == sample_file_url
        assert call_args.kwargs["metadata"]["file_id"] == sample_file_id
        assert call_args.kwargs["metadata"]["mime_type"] == "text/plain"
        assert call_args.kwargs["metadata"]["source_type"] == "local_file"

    @pytest.mark.asyncio
    async def test_adapter_google_drive_source_detection(
        self, sample_text, successful_ingestion_result
    ):
        """Test that Google Drive files are correctly identified."""
        # Mock the DocumentIngestionPipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document = AsyncMock(return_value=successful_ingestion_result)
        mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
        mock_pipeline.__aexit__ = AsyncMock(return_value=False)

        google_drive_url = "https://drive.google.com/file/d/abc123/view"

        with patch(
            "src.rag_pipeline.adapters.agentic_rag_adapter.DocumentIngestionPipeline",
            return_value=mock_pipeline,
        ):
            result = await process_file_with_agentic_rag(
                text=sample_text,
                file_id="abc123",
                file_title="gdrive_file",
                file_url=google_drive_url,
            )

        # Verify result
        assert result is True

        # Verify source_type is google_drive
        call_args = mock_pipeline.ingest_document.call_args
        assert call_args.kwargs["metadata"]["source_type"] == "google_drive"

    @pytest.mark.asyncio
    async def test_adapter_with_rest_api_mode(
        self,
        sample_text,
        sample_file_id,
        sample_file_title,
        sample_file_url,
        successful_ingestion_result,
    ):
        """Test adapter with REST API mode enabled."""
        # Mock the DocumentIngestionPipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document = AsyncMock(return_value=successful_ingestion_result)
        mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
        mock_pipeline.__aexit__ = AsyncMock(return_value=False)

        mock_pipeline_class = MagicMock(return_value=mock_pipeline)

        with patch(
            "src.rag_pipeline.adapters.agentic_rag_adapter.DocumentIngestionPipeline",
            mock_pipeline_class,
        ):
            result = await process_file_with_agentic_rag(
                text=sample_text,
                file_id=sample_file_id,
                file_title=sample_file_title,
                file_url=sample_file_url,
                use_rest_api=True,
            )

        # Verify result
        assert result is True

        # Verify pipeline was initialized with use_rest_api=True
        mock_pipeline_class.assert_called_once_with(use_rest_api=True)

    @pytest.mark.asyncio
    async def test_adapter_processing_failure(
        self,
        sample_text,
        sample_file_id,
        sample_file_title,
        sample_file_url,
        failed_ingestion_result,
    ):
        """Test handling of processing failures."""
        # Mock the DocumentIngestionPipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document = AsyncMock(return_value=failed_ingestion_result)
        mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
        mock_pipeline.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.rag_pipeline.adapters.agentic_rag_adapter.DocumentIngestionPipeline",
            return_value=mock_pipeline,
        ):
            result = await process_file_with_agentic_rag(
                text=sample_text,
                file_id=sample_file_id,
                file_title=sample_file_title,
                file_url=sample_file_url,
            )

        # Verify result is False for failed ingestion
        assert result is False

    @pytest.mark.asyncio
    async def test_adapter_exception_handling(
        self, sample_text, sample_file_id, sample_file_title, sample_file_url
    ):
        """Test exception handling in the adapter."""
        # Mock the DocumentIngestionPipeline to raise an exception
        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
        mock_pipeline.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.rag_pipeline.adapters.agentic_rag_adapter.DocumentIngestionPipeline",
            return_value=mock_pipeline,
        ):
            result = await process_file_with_agentic_rag(
                text=sample_text,
                file_id=sample_file_id,
                file_title=sample_file_title,
                file_url=sample_file_url,
            )

        # Verify result is False on exception
        assert result is False

    @pytest.mark.asyncio
    async def test_adapter_without_mime_type(
        self,
        sample_text,
        sample_file_id,
        sample_file_title,
        sample_file_url,
        successful_ingestion_result,
    ):
        """Test adapter without providing mime_type."""
        # Mock the DocumentIngestionPipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document = AsyncMock(return_value=successful_ingestion_result)
        mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
        mock_pipeline.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.rag_pipeline.adapters.agentic_rag_adapter.DocumentIngestionPipeline",
            return_value=mock_pipeline,
        ):
            result = await process_file_with_agentic_rag(
                text=sample_text,
                file_id=sample_file_id,
                file_title=sample_file_title,
                file_url=sample_file_url,
                # No mime_type provided
            )

        # Verify result
        assert result is True

        # Verify metadata does not include mime_type if not provided
        call_args = mock_pipeline.ingest_document.call_args
        metadata = call_args.kwargs["metadata"]
        assert "mime_type" not in metadata
        assert "file_id" in metadata
        assert "source_type" in metadata

    def test_sync_wrapper(
        self,
        sample_text,
        sample_file_id,
        sample_file_title,
        sample_file_url,
        successful_ingestion_result,
    ):
        """Test the synchronous wrapper function."""
        # Mock the async function
        with patch(
            "src.rag_pipeline.adapters.agentic_rag_adapter.process_file_with_agentic_rag",
            new_callable=AsyncMock,
        ) as mock_async_func:
            mock_async_func.return_value = True

            result = process_file_with_agentic_rag_sync(
                text=sample_text,
                file_id=sample_file_id,
                file_title=sample_file_title,
                file_url=sample_file_url,
                mime_type="text/plain",
                use_rest_api=False,
            )

            # Verify result
            assert result is True

            # Verify async function was called with correct arguments
            mock_async_func.assert_called_once_with(
                text=sample_text,
                file_id=sample_file_id,
                file_title=sample_file_title,
                file_url=sample_file_url,
                mime_type="text/plain",
                use_rest_api=False,
            )

    @pytest.mark.asyncio
    async def test_adapter_context_manager_cleanup(
        self,
        sample_text,
        sample_file_id,
        sample_file_title,
        sample_file_url,
        successful_ingestion_result,
    ):
        """Test that context manager properly cleans up resources."""
        # Mock the DocumentIngestionPipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document = AsyncMock(return_value=successful_ingestion_result)
        mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
        mock_pipeline.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.rag_pipeline.adapters.agentic_rag_adapter.DocumentIngestionPipeline",
            return_value=mock_pipeline,
        ):
            await process_file_with_agentic_rag(
                text=sample_text,
                file_id=sample_file_id,
                file_title=sample_file_title,
                file_url=sample_file_url,
            )

        # Verify context manager was used properly
        mock_pipeline.__aenter__.assert_called_once()
        mock_pipeline.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_adapter_large_document(self, sample_file_id, sample_file_title, sample_file_url):
        """Test adapter with a large document."""
        # Create a large document (10KB)
        large_text = "Large document content. " * 500  # ~12KB

        successful_result = IngestionResult(
            document_id=UUID("12345678-1234-5678-1234-567812345678"),
            title=sample_file_title,
            source=sample_file_url,
            chunks_created=10,  # More chunks for larger doc
            entities_extracted=15,
            relationships_extracted=8,
            facts_extracted=20,
            processing_time=3.5,
            errors=[],
        )

        # Mock the DocumentIngestionPipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.ingest_document = AsyncMock(return_value=successful_result)
        mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
        mock_pipeline.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.rag_pipeline.adapters.agentic_rag_adapter.DocumentIngestionPipeline",
            return_value=mock_pipeline,
        ):
            result = await process_file_with_agentic_rag(
                text=large_text,
                file_id=sample_file_id,
                file_title=sample_file_title,
                file_url=sample_file_url,
            )

        # Verify result
        assert result is True

        # Verify large text was passed
        call_args = mock_pipeline.ingest_document.call_args
        assert len(call_args.kwargs["content"]) > 10000
