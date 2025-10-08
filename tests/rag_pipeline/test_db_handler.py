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
    sys.path.append(str(Path(__file__).parent.parent.parent.resolve() / "src"))
    from rag_pipeline.common.db_handler import (
        delete_document_by_file_id,
        insert_document_chunks,
        insert_document_rows,
        insert_or_update_document_metadata,
        process_file_for_rag,  # Import the initialized supabase client
    )


class TestDbHandler:
    @pytest.fixture(autouse=True)
    def mock_supabase_client(self):
        # This fixture will run before each test in this class
        # and ensure the global supabase client is mocked
        with patch("rag_pipeline.common.db_handler.create_client") as mock_create_client:
            mock_supabase_instance = MagicMock()
            mock_create_client.return_value = mock_supabase_instance
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
        mock_insert_execute.assert_called_once()
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
        mock_update_execute.assert_called_once()
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
        assert mock_insert_execute.call_count == len(rows)

    @patch("rag_pipeline.common.db_handler.delete_document_by_file_id")
    @patch("rag_pipeline.common.db_handler.insert_or_update_document_metadata")
    @patch("rag_pipeline.common.db_handler.insert_document_rows")
    @patch("rag_pipeline.common.db_handler.insert_document_chunks")
    @patch("rag_pipeline.common.text_processor.is_tabular_file")
    @patch("rag_pipeline.common.text_processor.extract_schema_from_csv")
    @patch("rag_pipeline.common.text_processor.extract_rows_from_csv")
    @patch("rag_pipeline.common.text_processor.chunk_text")
    @patch("rag_pipeline.common.text_processor.create_embeddings")
    def test_process_file_for_rag_text_file(
        self,
        mock_create_embeddings,
        mock_chunk_text,
        mock_extract_rows_from_csv,
        mock_extract_schema_from_csv,
        mock_is_tabular_file,
        mock_insert_document_chunks,
        mock_insert_document_rows,
        mock_insert_or_update_document_metadata,
        mock_delete_document_by_file_id,
    ):
        file_content = b"This is some text content."
        text = "This is some text content."
        file_id = "text_file_id"
        file_url = "http://example.com/text.txt"
        file_title = "Text Document"
        mime_type = "text/plain"
        config = {"text_processing": {"default_chunk_size": 10, "default_chunk_overlap": 0}}

        mock_is_tabular_file.return_value = False
        mock_chunk_text.return_value = ["chunk1", "chunk2"]
        mock_create_embeddings.return_value = [[0.1], [0.2]]

        result = process_file_for_rag(
            file_content, text, file_id, file_url, file_title, mime_type, config
        )

        mock_delete_document_by_file_id.assert_called_once_with(file_id)
        mock_is_tabular_file.assert_called_once_with(mime_type, config)
        mock_insert_or_update_document_metadata.assert_called_once_with(
            file_id, file_title, file_url, None
        )
        mock_insert_document_rows.assert_not_called()
        mock_chunk_text.assert_called_once_with(text, chunk_size=10, overlap=0)
        mock_create_embeddings.assert_called_once_with(["chunk1", "chunk2"])
        mock_insert_document_chunks.assert_called_once_with(
            ["chunk1", "chunk2"], [[0.1], [0.2]], file_id, file_url, file_title, mime_type
        )
        assert result is True

    @patch("rag_pipeline.common.db_handler.delete_document_by_file_id")
    @patch("rag_pipeline.common.db_handler.insert_or_update_document_metadata")
    @patch("rag_pipeline.common.db_handler.insert_document_rows")
    @patch("rag_pipeline.common.db_handler.insert_document_chunks")
    @patch("rag_pipeline.common.text_processor.is_tabular_file")
    @patch("rag_pipeline.common.text_processor.extract_schema_from_csv")
    @patch("rag_pipeline.common.text_processor.extract_rows_from_csv")
    @patch("rag_pipeline.common.text_processor.chunk_text")
    @patch("rag_pipeline.common.text_processor.create_embeddings")
    def test_process_file_for_rag_tabular_file(
        self,
        mock_create_embeddings,
        mock_chunk_text,
        mock_extract_rows_from_csv,
        mock_extract_schema_from_csv,
        mock_is_tabular_file,
        mock_insert_document_chunks,
        mock_insert_document_rows,
        mock_insert_or_update_document_metadata,
        mock_delete_document_by_file_id,
    ):
        file_content = b"col1,col2\nval1,val2"
        text = "col1,col2\nval1,val2"
        file_id = "tabular_file_id"
        file_url = "http://example.com/data.csv"
        file_title = "Data Sheet"
        mime_type = "text/csv"
        config = {
            "tabular_mime_types": ["text/csv"],
            "text_processing": {"default_chunk_size": 10, "default_chunk_overlap": 0},
        }

        mock_is_tabular_file.return_value = True
        mock_extract_schema_from_csv.return_value = ["col1", "col2"]
        mock_extract_rows_from_csv.return_value = [{"col1": "val1", "col2": "val2"}]
        mock_chunk_text.return_value = ["chunk1"]
        mock_create_embeddings.return_value = [[0.1]]

        result = process_file_for_rag(
            file_content, text, file_id, file_url, file_title, mime_type, config
        )

        mock_delete_document_by_file_id.assert_called_once_with(file_id)
        mock_is_tabular_file.assert_called_once_with(mime_type, config)
        mock_extract_schema_from_csv.assert_called_once_with(file_content)
        mock_insert_or_update_document_metadata.assert_called_once_with(
            file_id, file_title, file_url, ["col1", "col2"]
        )
        mock_extract_rows_from_csv.assert_called_once_with(file_content)
        mock_insert_document_rows.assert_called_once_with(
            file_id, [{"col1": "val1", "col2": "val2"}]
        )
        mock_chunk_text.assert_called_once_with(text, chunk_size=10, overlap=0)
        mock_create_embeddings.assert_called_once_with(["chunk1"])
        mock_insert_document_chunks.assert_called_once_with(
            ["chunk1"], [[0.1]], file_id, file_url, file_title, mime_type
        )
        assert result is True

    @patch("rag_pipeline.common.db_handler.delete_document_by_file_id")
    @patch("rag_pipeline.common.db_handler.insert_or_update_document_metadata")
    @patch("rag_pipeline.common.db_handler.insert_document_rows")
    @patch("rag_pipeline.common.db_handler.insert_document_chunks")
    @patch("rag_pipeline.common.text_processor.is_tabular_file")
    @patch("rag_pipeline.common.text_processor.extract_schema_from_csv")
    @patch("rag_pipeline.common.text_processor.extract_rows_from_csv")
    @patch("rag_pipeline.common.text_processor.chunk_text")
    @patch("rag_pipeline.common.text_processor.create_embeddings")
    def test_process_file_for_rag_image_file(
        self,
        mock_create_embeddings,
        mock_chunk_text,
        mock_extract_rows_from_csv,
        mock_extract_schema_from_csv,
        mock_is_tabular_file,
        mock_insert_document_chunks,
        mock_insert_document_rows,
        mock_insert_or_update_document_metadata,
        mock_delete_document_by_file_id,
    ):
        file_content = b"image_binary_data"
        text = "Image description"
        file_id = "image_file_id"
        file_url = "http://example.com/image.jpg"
        file_title = "Image Document"
        mime_type = "image/jpeg"
        config = {"text_processing": {"default_chunk_size": 10, "default_chunk_overlap": 0}}

        mock_is_tabular_file.return_value = False
        mock_chunk_text.return_value = ["Image description"]
        mock_create_embeddings.return_value = [[0.5]]

        result = process_file_for_rag(
            file_content, text, file_id, file_url, file_title, mime_type, config
        )

        mock_delete_document_by_file_id.assert_called_once_with(file_id)
        mock_is_tabular_file.assert_called_once_with(mime_type, config)
        mock_insert_or_update_document_metadata.assert_called_once_with(
            file_id, file_title, file_url, None
        )
        mock_insert_document_rows.assert_not_called()
        mock_chunk_text.assert_called_once_with(text, chunk_size=10, overlap=0)
        mock_create_embeddings.assert_called_once_with(["Image description"])
        mock_insert_document_chunks.assert_called_once_with(
            ["Image description"], [[0.5]], file_id, file_url, file_title, mime_type, file_content
        )
        assert result is True

    @patch("rag_pipeline.common.db_handler.delete_document_by_file_id")
    @patch("rag_pipeline.common.db_handler.insert_or_update_document_metadata")
    @patch("rag_pipeline.common.db_handler.insert_document_rows")
    @patch("rag_pipeline.common.db_handler.insert_document_chunks")
    @patch("rag_pipeline.common.text_processor.is_tabular_file")
    @patch("rag_pipeline.common.text_processor.extract_schema_from_csv")
    @patch("rag_pipeline.common.text_processor.extract_rows_from_csv")
    @patch("rag_pipeline.common.text_processor.chunk_text")
    @patch("rag_pipeline.common.text_processor.create_embeddings")
    def test_process_file_for_rag_no_chunks(
        self,
        mock_create_embeddings,
        mock_chunk_text,
        mock_extract_rows_from_csv,
        mock_extract_schema_from_csv,
        mock_is_tabular_file,
        mock_insert_document_chunks,
        mock_insert_document_rows,
        mock_insert_or_update_document_metadata,
        mock_delete_document_by_file_id,
    ):
        file_content = b"short text"
        text = "short text"
        file_id = "short_file_id"
        file_url = "http://example.com/short.txt"
        file_title = "Short Document"
        mime_type = "text/plain"
        config = {"text_processing": {"default_chunk_size": 100, "default_chunk_overlap": 0}}

        mock_is_tabular_file.return_value = False
        mock_chunk_text.return_value = []  # Simulate no chunks created

        result = process_file_for_rag(
            file_content, text, file_id, file_url, file_title, mime_type, config
        )

        mock_delete_document_by_file_id.assert_called_once_with(file_id)
        mock_insert_or_update_document_metadata.assert_called_once_with(
            file_id, file_title, file_url, None
        )
        mock_insert_document_chunks.assert_not_called()  # Should not be called if no chunks
        assert result is False  # Should return False on failure
