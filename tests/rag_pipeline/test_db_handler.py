import base64
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

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
        mock_execute_rows = MagicMock()
        mock_execute_rows.data = [{"row_id": "row1"}]  # For document_rows table
        mock_eq.execute.side_effect = [
            mock_execute,
            mock_execute_rows,
            MagicMock(data=[{"id": "metadata1"}]),
        ]  # Added mock for document_metadata

        delete_document_by_file_id(file_id)

        # Assert calls for documents table
        mock_supabase_client.table.assert_any_call("documents")
        mock_table.delete.assert_any_call()
        mock_delete.eq.assert_any_call("metadata->>file_id", file_id)

        # Assert calls for document_rows table
        mock_supabase_client.table.assert_any_call("document_rows")
        mock_table.delete.assert_any_call()
        mock_delete.eq.assert_any_call("dataset_id", file_id)

        # Assert calls for document_metadata table
        mock_supabase_client.table.assert_any_call("document_metadata")
        mock_table.delete.assert_any_call()
        mock_delete.eq.assert_any_call("id", file_id)

    def test_insert_document_chunks(self, mock_supabase_client):
        chunks = ["chunk1", "chunk2"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        file_id = "file123"
        file_url = "http://example.com/file123"
        file_title = "Test Document"
        mime_type = "text/plain"
        file_content = b"some content"

        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_execute = MagicMock()
        mock_insert.execute.return_value = mock_execute

        insert_document_chunks(
            chunks, embeddings, file_id, file_url, file_title, mime_type, file_content
        )

        expected_calls = [
            call(
                {
                    "content": "chunk1",
                    "metadata": {
                        "file_id": file_id,
                        "file_url": file_url,
                        "file_title": file_title,
                        "mime_type": mime_type,
                        "chunk_index": 0,
                        "file_contents": base64.b64encode(file_content).decode("utf-8"),
                    },
                    "embedding": [0.1, 0.2],
                }
            ),
            call(
                {
                    "content": "chunk2",
                    "metadata": {
                        "file_id": file_id,
                        "file_url": file_url,
                        "file_title": file_title,
                        "mime_type": mime_type,
                        "chunk_index": 1,
                        "file_contents": base64.b64encode(file_content).decode("utf-8"),
                    },
                    "embedding": [0.3, 0.4],
                }
            ),
        ]
        mock_table.insert.assert_has_calls(expected_calls, any_order=True)
        assert mock_insert.execute.call_count == len(chunks)

    def test_insert_or_update_document_metadata_insert(self, mock_supabase_client):
        file_id = "meta1"
        file_title = "Metadata Title"
        file_url = "http://example.com/meta1"
        schema = ["col1", "col2"]

        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_execute = MagicMock()
        mock_eq.execute.return_value = mock_execute

        # Simulate no existing data for insert
        mock_execute.data = []

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert_execute = MagicMock()
        mock_insert.execute.return_value = mock_insert_execute

        insert_or_update_document_metadata(file_id, file_title, file_url, schema)

        expected_data = {
            "id": file_id,
            "title": file_title,
            "url": file_url,
            "schema": json.dumps(schema),
        }
        mock_table.insert.assert_called_once_with(expected_data)
        mock_insert.execute.assert_called_once()
        mock_table.update.assert_not_called()

    def test_insert_or_update_document_metadata_update(self, mock_supabase_client):
        file_id = "meta1"
        file_title = "Updated Metadata Title"
        file_url = "http://example.com/meta1/updated"

        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_execute = MagicMock()
        mock_eq.execute.return_value = mock_execute

        # Simulate existing data for update
        mock_execute.data = [{"id": file_id, "title": "Old Title"}]

        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_execute = MagicMock()
        mock_update.execute.return_value = mock_update_execute

        insert_or_update_document_metadata(file_id, file_title, file_url)

        expected_data = {"id": file_id, "title": file_title, "url": file_url}
        mock_table.update.assert_called_once_with(expected_data)
        mock_update.eq.assert_called_once_with("id", file_id)
        # Since update().eq() returns a mock, check that execute was called on that return value
        mock_update.eq.return_value.execute.assert_called_once()
        mock_table.insert.assert_not_called()

    def test_insert_document_rows(self, mock_supabase_client):
        file_id = "rows123"
        rows = [{"col1": "val1", "col2": 1}, {"col1": "val2", "col2": 2}]

        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_eq_delete = MagicMock()
        mock_delete.eq.return_value = mock_eq_delete
        mock_execute_delete = MagicMock()
        mock_eq_delete.execute.return_value = mock_execute_delete

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert_execute = MagicMock()
        mock_insert.execute.return_value = mock_insert_execute

        insert_document_rows(file_id, rows)

        # Verify existing rows are deleted
        mock_table.delete.assert_called_once()
        mock_delete.eq.assert_called_once_with("dataset_id", file_id)

        # Verify new rows are inserted
        expected_calls = [
            call({"dataset_id": file_id, "row_data": {"col1": "val1", "col2": 1}}),
            call({"dataset_id": file_id, "row_data": {"col1": "val2", "col2": 2}}),
        ]
        mock_table.insert.assert_has_calls(expected_calls, any_order=True)
        assert mock_insert.execute.call_count == len(rows)
