import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock environment variables before importing modules that use them
with patch.dict(
    os.environ,
    {
        "SUPABASE_URL": "https://test-supabase-url.com",
        "SUPABASE_SERVICE_KEY": "test-supabase-key",
        "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
    },
):
    # Add src directory to path to import the module
    sys.path.append(str(Path(__file__).parent.parent.parent.resolve()))
    from src.rag_pipeline.common.db_handler import (
        delete_document_by_file_id,
        insert_document_chunks,
        insert_document_rows,
        insert_or_update_document_metadata,
    )


class TestDbHandler:
    @pytest.fixture(autouse=True)
    def mock_supabase_client(self):
        # This fixture will run before each test in this class
        # and patch the module-level supabase client directly
        with patch("src.rag_pipeline.common.db_handler.supabase") as mock_supabase_instance:
            yield mock_supabase_instance

    def test_delete_document_by_file_id(self, mock_supabase_client):
        file_id = "test_file_id"

        # Mock the table and delete methods
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_eq = MagicMock()
        mock_delete.eq.return_value = mock_eq
        mock_execute = MagicMock()
        mock_eq.execute.return_value = mock_execute

        # Set return values for execute
        mock_execute.data = [{"id": "doc1"}, {"id": "doc2"}]  # For documents table

        delete_document_by_file_id(file_id)

        # Assert calls for documents table only (cascades to chunks)
        mock_supabase_client.table.assert_called_once_with("documents")
        mock_table.delete.assert_called_once()
        mock_delete.eq.assert_called_once_with("metadata->>file_id", file_id)

    def test_insert_document_chunks(self, mock_supabase_client):
        chunks = ["chunk1", "chunk2"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        file_id = "file123"
        file_url = "http://example.com/file123"
        file_title = "Test Document"
        mime_type = "text/plain"
        file_content = b"some content"

        # Mock the table calls
        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_execute = MagicMock()
        mock_execute.data = [{"id": "doc-uuid-123"}]  # Document ID returned
        mock_insert.execute.return_value = mock_execute

        insert_document_chunks(
            chunks, embeddings, file_id, file_url, file_title, mime_type, file_content
        )

        # Verify documents table insert was called (first call)
        mock_supabase_client.table.assert_any_call("documents")

        # Verify chunks table insert was called (second call)
        mock_supabase_client.table.assert_any_call("chunks")

        # Verify insert was called twice (once for documents, once for chunks)
        assert mock_table.insert.call_count == 2

    def test_insert_or_update_document_metadata_insert(self, mock_supabase_client):
        """Test that insert_or_update_document_metadata is a no-op (metadata is now in documents table)."""
        file_id = "meta1"
        file_title = "Metadata Title"
        file_url = "http://example.com/meta1"
        schema = ["col1", "col2"]

        # Function is now a no-op - should not make any database calls
        insert_or_update_document_metadata(file_id, file_title, file_url, schema)

        # Verify no table operations were called (function is a no-op)
        mock_supabase_client.table.assert_not_called()

    def test_insert_or_update_document_metadata_update(self, mock_supabase_client):
        """Test that insert_or_update_document_metadata is a no-op for updates too."""
        file_id = "meta1"
        file_title = "Updated Metadata Title"
        file_url = "http://example.com/meta1/updated"

        # Function is now a no-op - should not make any database calls
        insert_or_update_document_metadata(file_id, file_title, file_url)

        # Verify no table operations were called (function is a no-op)
        mock_supabase_client.table.assert_not_called()

    def test_insert_document_rows(self, mock_supabase_client):
        file_id = "rows123"
        rows = [{"col1": "val1", "col2": 1}, {"col1": "val2", "col2": 2}]
        document_uuid = "doc-uuid-456"

        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table

        # Mock select to find document UUID
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq_select = MagicMock()
        mock_select.eq.return_value = mock_eq_select
        mock_execute_select = MagicMock()
        mock_execute_select.data = [{"id": document_uuid}]
        mock_eq_select.execute.return_value = mock_execute_select

        # Mock delete
        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_eq_delete = MagicMock()
        mock_delete.eq.return_value = mock_eq_delete
        mock_execute_delete = MagicMock()
        mock_eq_delete.execute.return_value = mock_execute_delete

        # Mock insert
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert_execute = MagicMock()
        mock_insert.execute.return_value = mock_insert_execute

        insert_document_rows(file_id, rows)

        # Verify document lookup was done
        mock_supabase_client.table.assert_any_call("documents")
        mock_select.eq.assert_called_once_with("metadata->>file_id", file_id)

        # Verify existing rows are deleted using document UUID (not file_id)
        mock_supabase_client.table.assert_any_call("document_rows")
        mock_delete.eq.assert_called_once_with("dataset_id", document_uuid)

        # Verify new rows are inserted with row_index
        mock_table.insert.assert_called_once()  # Batch insert call
