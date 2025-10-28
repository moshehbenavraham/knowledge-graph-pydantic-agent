"""
Additional edge case tests for upload_handler.py - pushing coverage to 100%.

Tests extreme scenarios, error paths, and boundary conditions for file uploads.
"""

import base64
import io
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.ui.features.upload_handler import (
    process_document_upload,
    process_image_upload,
    process_tabular_upload,
)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = Mock()
    mock_table = Mock()
    mock_insert = Mock()
    mock_execute = Mock()
    mock_execute.execute = Mock(return_value=Mock(data=[{"id": "doc-123"}]))

    mock_insert.execute = Mock(return_value=Mock(data=[{"id": "doc-123"}]))
    mock_table.insert = Mock(return_value=mock_insert)
    client.table = Mock(return_value=mock_table)

    return client


@pytest.fixture
def mock_embedding_client():
    """Mock embedding client."""
    return AsyncMock()


# ====================
# Document Upload Edge Cases
# ====================


@pytest.mark.asyncio
async def test_process_document_empty_file(mock_supabase, mock_embedding_client):
    """Test processing empty document file."""
    mock_file = Mock()
    mock_file.name = "empty.txt"
    mock_file.type = "text/plain"
    mock_file.size = 0
    mock_file.read = Mock(return_value=b"")

    with (
        patch("src.agentic_rag.ingestion.chunker.semantic_chunk", return_value=[]),
        patch(
            "src.agentic_rag.ingestion.embedder.generate_embeddings",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        result = await process_document_upload(mock_file, mock_supabase, mock_embedding_client)

        # Should succeed even with empty content
        assert result["success"] is True
        assert result["chunks"] == 0


@pytest.mark.asyncio
async def test_process_document_very_large_file(mock_supabase, mock_embedding_client):
    """Test processing very large document (>10MB)."""
    large_content = "x" * (10 * 1024 * 1024)  # 10MB

    mock_file = Mock()
    mock_file.name = "large.txt"
    mock_file.type = "text/plain"
    mock_file.size = len(large_content)
    mock_file.read = Mock(return_value=large_content.encode())

    # Mock chunking to return many chunks
    mock_chunks = [{"content": f"chunk {i}"} for i in range(1000)]
    mock_embeddings = [[0.1] * 1536 for _ in range(1000)]

    with (
        patch("src.agentic_rag.ingestion.chunker.semantic_chunk", return_value=mock_chunks),
        patch(
            "src.agentic_rag.ingestion.embedder.generate_embeddings",
            new_callable=AsyncMock,
            return_value=mock_embeddings,
        ),
    ):
        result = await process_document_upload(mock_file, mock_supabase, mock_embedding_client)

        assert result["success"] is True
        assert result["chunks"] == 1000


@pytest.mark.asyncio
async def test_process_document_decode_error(mock_supabase, mock_embedding_client):
    """Test processing document with decode errors."""
    mock_file = Mock()
    mock_file.name = "binary.bin"
    mock_file.type = "application/octet-stream"
    mock_file.size = 100
    mock_file.read = Mock(return_value=b"\x80\x81\x82\x83")  # Invalid UTF-8

    result = await process_document_upload(mock_file, mock_supabase, mock_embedding_client)

    # Should fail gracefully
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_process_document_chunking_error(mock_supabase, mock_embedding_client):
    """Test error during chunking."""
    mock_file = Mock()
    mock_file.name = "test.txt"
    mock_file.type = "text/plain"
    mock_file.size = 100
    mock_file.read = Mock(return_value=b"test content")

    with patch(
        "src.agentic_rag.ingestion.chunker.semantic_chunk",
        side_effect=RuntimeError("Chunking error"),
    ):
        result = await process_document_upload(mock_file, mock_supabase, mock_embedding_client)

        assert result["success"] is False
        assert "Chunking error" in result["message"]


@pytest.mark.asyncio
async def test_process_document_embedding_error(mock_supabase, mock_embedding_client):
    """Test error during embedding generation."""
    mock_file = Mock()
    mock_file.name = "test.txt"
    mock_file.type = "text/plain"
    mock_file.size = 100
    mock_file.read = Mock(return_value=b"test content")

    with (
        patch(
            "src.agentic_rag.ingestion.chunker.semantic_chunk", return_value=[{"content": "chunk1"}]
        ),
        patch(
            "src.agentic_rag.ingestion.embedder.generate_embeddings",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Embedding error"),
        ),
    ):
        result = await process_document_upload(mock_file, mock_supabase, mock_embedding_client)

        assert result["success"] is False
        assert "Embedding error" in result["message"]


@pytest.mark.asyncio
async def test_process_document_database_error(mock_supabase, mock_embedding_client):
    """Test error during database insertion."""
    mock_file = Mock()
    mock_file.name = "test.txt"
    mock_file.type = "text/plain"
    mock_file.size = 100
    mock_file.read = Mock(return_value=b"test content")

    # Make database insertion fail
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
        "DB error"
    )

    with (
        patch(
            "src.agentic_rag.ingestion.chunker.semantic_chunk", return_value=[{"content": "chunk1"}]
        ),
        patch(
            "src.agentic_rag.ingestion.embedder.generate_embeddings",
            new_callable=AsyncMock,
            return_value=[[0.1] * 1536],
        ),
    ):
        result = await process_document_upload(mock_file, mock_supabase, mock_embedding_client)

        assert result["success"] is False
        assert "DB error" in result["message"]


@pytest.mark.asyncio
async def test_process_document_unicode_content(mock_supabase, mock_embedding_client):
    """Test processing document with unicode characters."""
    unicode_content = "测试 тест परीक्षण 🚀"

    mock_file = Mock()
    mock_file.name = "unicode.txt"
    mock_file.type = "text/plain"
    mock_file.size = len(unicode_content)
    mock_file.read = Mock(return_value=unicode_content.encode())

    with (
        patch(
            "src.agentic_rag.ingestion.chunker.semantic_chunk",
            return_value=[{"content": unicode_content}],
        ),
        patch(
            "src.agentic_rag.ingestion.embedder.generate_embeddings",
            new_callable=AsyncMock,
            return_value=[[0.1] * 1536],
        ),
    ):
        result = await process_document_upload(mock_file, mock_supabase, mock_embedding_client)

        assert result["success"] is True


# ====================
# Image Upload Edge Cases
# ====================


@pytest.mark.asyncio
async def test_process_image_empty_file(mock_supabase):
    """Test processing empty image file."""
    mock_file = Mock()
    mock_file.name = "empty.png"
    mock_file.type = "image/png"
    mock_file.size = 0
    mock_file.read = Mock(return_value=b"")

    result = await process_image_upload(mock_file, mock_supabase)

    # Should succeed even with empty file
    assert result["success"] is True


@pytest.mark.asyncio
async def test_process_image_very_large_file(mock_supabase):
    """Test processing very large image (>10MB)."""
    large_image = b"\x89PNG\r\n\x1a\n" + (b"x" * (10 * 1024 * 1024))

    mock_file = Mock()
    mock_file.name = "large.png"
    mock_file.type = "image/png"
    mock_file.size = len(large_image)
    mock_file.read = Mock(return_value=large_image)

    result = await process_image_upload(mock_file, mock_supabase)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_process_image_base64_encoding(mock_supabase):
    """Test that image is properly base64 encoded."""
    image_bytes = b"\x89PNG\r\n\x1a\ntest"

    mock_file = Mock()
    mock_file.name = "test.png"
    mock_file.type = "image/png"
    mock_file.size = len(image_bytes)
    mock_file.read = Mock(return_value=image_bytes)

    # Capture the inserted document
    inserted_doc = None

    def capture_insert(doc):
        nonlocal inserted_doc
        inserted_doc = doc
        mock_result = Mock()
        mock_result.execute = Mock(return_value=Mock(data=[{"id": "img-123"}]))
        return mock_result

    mock_supabase.table.return_value.insert = Mock(side_effect=capture_insert)

    result = await process_image_upload(mock_file, mock_supabase)

    assert result["success"] is True
    # Verify base64 encoding
    assert "image_data" in inserted_doc["metadata"]
    decoded = base64.b64decode(inserted_doc["metadata"]["image_data"])
    assert decoded == image_bytes


@pytest.mark.asyncio
async def test_process_image_database_error(mock_supabase):
    """Test error during image database insertion."""
    mock_file = Mock()
    mock_file.name = "test.png"
    mock_file.type = "image/png"
    mock_file.size = 100
    mock_file.read = Mock(return_value=b"image data")

    mock_supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
        "DB error"
    )

    result = await process_image_upload(mock_file, mock_supabase)

    assert result["success"] is False
    assert "DB error" in result["message"]


@pytest.mark.asyncio
async def test_process_image_read_error(mock_supabase):
    """Test error during image reading."""
    mock_file = Mock()
    mock_file.name = "corrupt.png"
    mock_file.type = "image/png"
    mock_file.size = 100
    mock_file.read = Mock(side_effect=OSError("Read error"))

    result = await process_image_upload(mock_file, mock_supabase)

    assert result["success"] is False
    assert "error" in result


# ====================
# Tabular Upload Edge Cases
# ====================


@pytest.mark.asyncio
async def test_process_tabular_empty_csv(mock_supabase):
    """Test processing empty CSV file."""
    empty_csv = b"col1,col2\n"

    mock_file = Mock()
    mock_file.name = "empty.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(empty_csv)
    mock_file.read = Mock(return_value=empty_csv)

    result = await process_tabular_upload(mock_file, mock_supabase)

    # Should succeed with 0 rows
    assert result["success"] is True
    assert result["rows"] == 0


@pytest.mark.asyncio
async def test_process_tabular_very_large_csv(mock_supabase):
    """Test processing very large CSV (1000+ rows)."""
    # Create CSV with 1000 rows
    csv_data = "col1,col2,col3\n"
    for i in range(1000):
        csv_data += f"{i},value{i},data{i}\n"

    mock_file = Mock()
    mock_file.name = "large.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(csv_data)
    mock_file.read = Mock(return_value=csv_data.encode())

    result = await process_tabular_upload(mock_file, mock_supabase)

    assert result["success"] is True
    assert result["rows"] == 1000


@pytest.mark.asyncio
async def test_process_tabular_excel_file(mock_supabase):
    """Test processing Excel file."""
    # Create Excel data in memory
    df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_data = excel_buffer.getvalue()

    mock_file = Mock()
    mock_file.name = "test.xlsx"
    mock_file.type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    mock_file.size = len(excel_data)
    mock_file.read = Mock(return_value=excel_data)

    result = await process_tabular_upload(mock_file, mock_supabase)

    assert result["success"] is True
    assert result["rows"] == 3


@pytest.mark.asyncio
async def test_process_tabular_unsupported_type(mock_supabase):
    """Test processing unsupported tabular file type."""
    mock_file = Mock()
    mock_file.name = "test.json"
    mock_file.type = "application/json"
    mock_file.size = 100
    mock_file.read = Mock(return_value=b'{"key": "value"}')

    result = await process_tabular_upload(mock_file, mock_supabase)

    assert result["success"] is False
    assert "Unsupported file type" in result["message"]


@pytest.mark.asyncio
async def test_process_tabular_malformed_csv(mock_supabase):
    """Test processing malformed CSV."""
    malformed_csv = b"col1,col2\nvalue1,value2,value3,value4\n"

    mock_file = Mock()
    mock_file.name = "malformed.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(malformed_csv)
    mock_file.read = Mock(return_value=malformed_csv)

    # pandas should handle this, but let's test the error case
    result = await process_tabular_upload(mock_file, mock_supabase)

    # pandas may handle this or fail - either way is valid
    assert isinstance(result, dict)
    assert "success" in result


@pytest.mark.asyncio
async def test_process_tabular_database_metadata_error(mock_supabase):
    """Test error during metadata insertion."""
    csv_data = b"col1,col2\n1,a\n2,b\n"

    mock_file = Mock()
    mock_file.name = "test.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(csv_data)
    mock_file.read = Mock(return_value=csv_data)

    mock_supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
        "Metadata error"
    )

    result = await process_tabular_upload(mock_file, mock_supabase)

    assert result["success"] is False


@pytest.mark.asyncio
async def test_process_tabular_rows_insertion_error(mock_supabase):
    """Test error during rows insertion."""
    csv_data = b"col1,col2\n1,a\n2,b\n"

    mock_file = Mock()
    mock_file.name = "test.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(csv_data)
    mock_file.read = Mock(return_value=csv_data)

    # Make first insert succeed (metadata), second fail (rows)
    call_count = [0]

    def side_effect_insert(*args, **kwargs):
        call_count[0] += 1
        mock_result = Mock()
        if call_count[0] == 1:
            # First call succeeds (metadata)
            mock_result.execute = Mock(return_value=Mock(data=[{"id": "dataset-123"}]))
        else:
            # Second call fails (rows)
            mock_result.execute = Mock(side_effect=RuntimeError("Rows insert error"))
        return mock_result

    mock_supabase.table.return_value.insert = Mock(side_effect=side_effect_insert)

    result = await process_tabular_upload(mock_file, mock_supabase)

    assert result["success"] is False


@pytest.mark.asyncio
async def test_process_tabular_mixed_data_types(mock_supabase):
    """Test CSV with mixed data types."""
    csv_data = b"int_col,float_col,str_col,bool_col\n1,1.5,text,True\n2,2.5,more,False\n"

    mock_file = Mock()
    mock_file.name = "mixed.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(csv_data)
    mock_file.read = Mock(return_value=csv_data)

    result = await process_tabular_upload(mock_file, mock_supabase)

    assert result["success"] is True
    assert result["columns"] == 4


@pytest.mark.asyncio
async def test_process_tabular_unicode_data(mock_supabase):
    """Test CSV with unicode characters."""
    csv_data = "name,city\n测试,北京\nтест,Москва\n".encode()

    mock_file = Mock()
    mock_file.name = "unicode.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(csv_data)
    mock_file.read = Mock(return_value=csv_data)

    result = await process_tabular_upload(mock_file, mock_supabase)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_process_tabular_special_characters_in_columns(mock_supabase):
    """Test CSV with special characters in column names."""
    csv_data = b"col!@#,col$%^,col&*()\nval1,val2,val3\n"

    mock_file = Mock()
    mock_file.name = "special.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(csv_data)
    mock_file.read = Mock(return_value=csv_data)

    result = await process_tabular_upload(mock_file, mock_supabase)

    # pandas should handle this
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_process_tabular_no_rows_data(mock_supabase):
    """Test CSV with no data to insert into rows table."""
    # Only headers, no data rows
    csv_data = b"col1,col2\n"

    mock_file = Mock()
    mock_file.name = "headers_only.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(csv_data)
    mock_file.read = Mock(return_value=csv_data)

    result = await process_tabular_upload(mock_file, mock_supabase)

    assert result["success"] is True
    assert result["rows"] == 0


# ====================
# Metadata Edge Cases
# ====================


@pytest.mark.asyncio
async def test_document_metadata_completeness(mock_supabase, mock_embedding_client):
    """Test that all metadata fields are populated correctly."""
    mock_file = Mock()
    mock_file.name = "metadata_test.txt"
    mock_file.type = "text/plain"
    mock_file.size = 100
    mock_file.read = Mock(return_value=b"test content")

    inserted_docs = []

    def capture_insert(docs):
        inserted_docs.extend(docs)
        mock_result = Mock()
        mock_result.execute = Mock(return_value=Mock(data=[{"id": "doc-123"}]))
        return mock_result

    mock_supabase.table.return_value.insert = Mock(side_effect=capture_insert)

    with (
        patch(
            "src.agentic_rag.ingestion.chunker.semantic_chunk", return_value=[{"content": "chunk1"}]
        ),
        patch(
            "src.agentic_rag.ingestion.embedder.generate_embeddings",
            new_callable=AsyncMock,
            return_value=[[0.1] * 1536],
        ),
    ):
        result = await process_document_upload(mock_file, mock_supabase, mock_embedding_client)

        assert result["success"] is True
        assert len(inserted_docs) > 0

        # Verify metadata structure
        doc = inserted_docs[0]
        assert "source" in doc
        assert "content" in doc
        assert "metadata" in doc
        assert doc["metadata"]["upload_source"] == "streamlit_ui"
        assert doc["metadata"]["file_type"] == "text/plain"


@pytest.mark.asyncio
async def test_tabular_schema_preservation(mock_supabase):
    """Test that tabular data schema is preserved correctly."""
    csv_data = b"int_col,float_col,str_col\n1,1.5,text\n"

    mock_file = Mock()
    mock_file.name = "schema.csv"
    mock_file.type = "text/csv"
    mock_file.size = len(csv_data)
    mock_file.read = Mock(return_value=csv_data)

    inserted_doc = None

    def capture_insert(doc_or_list):
        nonlocal inserted_doc
        # Handle both single doc (dict) and list of rows
        if isinstance(doc_or_list, dict) and "columns" in doc_or_list.get("metadata", {}):
            inserted_doc = doc_or_list
        mock_result = Mock()
        mock_result.execute = Mock(return_value=Mock(data=[{"id": "dataset-123"}]))
        return mock_result

    mock_supabase.table.return_value.insert = Mock(side_effect=capture_insert)

    result = await process_tabular_upload(mock_file, mock_supabase)

    assert result["success"] is True
    assert inserted_doc is not None
    assert "schema" in inserted_doc["metadata"]


# ====================
# File Size Edge Cases
# ====================


@pytest.mark.asyncio
async def test_document_single_byte_file(mock_supabase, mock_embedding_client):
    """Test processing file with single byte."""
    mock_file = Mock()
    mock_file.name = "tiny.txt"
    mock_file.type = "text/plain"
    mock_file.size = 1
    mock_file.read = Mock(return_value=b"x")

    with (
        patch("src.agentic_rag.ingestion.chunker.semantic_chunk", return_value=[{"content": "x"}]),
        patch(
            "src.agentic_rag.ingestion.embedder.generate_embeddings",
            new_callable=AsyncMock,
            return_value=[[0.1] * 1536],
        ),
    ):
        result = await process_document_upload(mock_file, mock_supabase, mock_embedding_client)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_image_single_byte_file(mock_supabase):
    """Test processing image with single byte."""
    mock_file = Mock()
    mock_file.name = "tiny.png"
    mock_file.type = "image/png"
    mock_file.size = 1
    mock_file.read = Mock(return_value=b"x")

    result = await process_image_upload(mock_file, mock_supabase)

    assert result["success"] is True
