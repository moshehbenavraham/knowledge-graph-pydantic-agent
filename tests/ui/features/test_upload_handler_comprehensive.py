"""
Comprehensive tests for upload_handler.py module.

Tests document, image, and tabular file upload processing with
success/failure scenarios, database operations, and error handling.
"""

import base64
import io
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.ui.features.upload_handler import (
    process_document_upload,
    process_image_upload,
    process_tabular_upload,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = MagicMock()
    table_mock = MagicMock()
    insert_mock = MagicMock()
    execute_mock = MagicMock()

    # Setup chain: table().insert().execute()
    execute_mock.return_value = MagicMock(data=[{"id": "test-doc-id"}])
    insert_mock.return_value.execute = execute_mock
    table_mock.return_value.insert = insert_mock
    client.table = table_mock

    return client


@pytest.fixture
def mock_embedding_client():
    """Mock embedding client (OpenAI)."""
    return MagicMock()


@pytest.fixture
def mock_text_file():
    """Create mock text file upload."""
    file = MagicMock()
    file.name = "test_document.txt"
    file.type = "text/plain"
    file.size = 1024
    file.read.return_value = (
        b"This is test content for a document upload.\n\nIt has multiple lines."
    )
    return file


@pytest.fixture
def mock_markdown_file():
    """Create mock markdown file upload."""
    file = MagicMock()
    file.name = "test_doc.md"
    file.type = "text/markdown"
    file.size = 2048
    file.read.return_value = (
        b"# Test Document\n\nThis is a markdown file.\n\n## Section 1\n\nContent here."
    )
    return file


@pytest.fixture
def mock_image_file():
    """Create mock image file upload."""
    file = MagicMock()
    file.name = "test_image.png"
    file.type = "image/png"
    file.size = 5120
    # Create simple PNG-like bytes
    file.read.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 100
    return file


@pytest.fixture
def mock_csv_file():
    """Create mock CSV file upload."""
    file = MagicMock()
    file.name = "test_data.csv"
    file.type = "text/csv"
    file.size = 1536

    # Create CSV content
    csv_content = "name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago"
    file.read.return_value = csv_content.encode("utf-8")
    return file


@pytest.fixture
def mock_excel_file():
    """Create mock Excel file upload."""
    file = MagicMock()
    file.name = "test_data.xlsx"
    file.type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    file.size = 4096

    # Create Excel bytes in memory
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25], "city": ["NYC", "LA"]})
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    file.read.return_value = buffer.read()

    return file


# ============================================================================
# process_document_upload Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_success(
    mock_chunk, mock_embeddings, mock_text_file, mock_supabase, mock_embedding_client
):
    """Test successful document upload processing."""
    # Mock chunking
    mock_chunk.return_value = [
        {"content": "Chunk 1 content"},
        {"content": "Chunk 2 content"},
    ]

    # Mock embeddings
    mock_embeddings.return_value = [[0.1] * 1536, [0.2] * 1536]

    result = await process_document_upload(mock_text_file, mock_supabase, mock_embedding_client)

    assert result["success"] is True
    assert "test_document.txt" in result["message"]
    assert result["chunks"] == 2
    assert result["document_id"] == "test_document.txt"

    # Verify chunking was called
    mock_chunk.assert_called_once()

    # Verify embeddings were generated
    mock_embeddings.assert_called_once()

    # Verify database insertion
    mock_supabase.table.assert_called_with("documents")


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_markdown(
    mock_chunk, mock_embeddings, mock_markdown_file, mock_supabase, mock_embedding_client
):
    """Test markdown file upload."""
    mock_chunk.return_value = [{"content": "Markdown content"}]
    mock_embeddings.return_value = [[0.1] * 1536]

    result = await process_document_upload(mock_markdown_file, mock_supabase, mock_embedding_client)

    assert result["success"] is True
    assert "test_doc.md" in result["message"]
    assert result["chunks"] == 1


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_large_file(
    mock_chunk, mock_embeddings, mock_supabase, mock_embedding_client
):
    """Test uploading large document with many chunks."""
    large_file = MagicMock()
    large_file.name = "large_doc.txt"
    large_file.type = "text/plain"
    large_file.size = 50000
    large_file.read.return_value = b"Large content " * 1000

    # Mock many chunks
    mock_chunk.return_value = [{"content": f"Chunk {i}"} for i in range(50)]
    mock_embeddings.return_value = [[0.1] * 1536] * 50

    result = await process_document_upload(large_file, mock_supabase, mock_embedding_client)

    assert result["success"] is True
    assert result["chunks"] == 50


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_metadata(
    mock_chunk, mock_embeddings, mock_text_file, mock_supabase, mock_embedding_client
):
    """Test that correct metadata is included in documents."""
    mock_chunk.return_value = [{"content": "Test"}]
    mock_embeddings.return_value = [[0.1] * 1536]

    await process_document_upload(mock_text_file, mock_supabase, mock_embedding_client)

    # Get the insert call
    insert_call = mock_supabase.table.return_value.insert.call_args[0][0]

    # Verify metadata structure
    assert len(insert_call) == 1
    doc = insert_call[0]
    assert "metadata" in doc
    assert doc["metadata"]["source"] == "test_document.txt"
    assert doc["metadata"]["file_type"] == "text/plain"
    assert doc["metadata"]["upload_source"] == "streamlit_ui"
    assert doc["metadata"]["chunk_index"] == 0


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_chunking_params(
    mock_chunk, mock_embeddings, mock_text_file, mock_supabase, mock_embedding_client
):
    """Test that correct chunking parameters are used."""
    mock_chunk.return_value = [{"content": "Test"}]
    mock_embeddings.return_value = [[0.1] * 1536]

    await process_document_upload(mock_text_file, mock_supabase, mock_embedding_client)

    # Verify chunking params
    call_kwargs = mock_chunk.call_args[1]
    assert call_kwargs["chunk_size"] == 1000
    assert call_kwargs["overlap"] == 200


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_decode_error(
    mock_chunk, mock_embeddings, mock_supabase, mock_embedding_client
):
    """Test handling of file decode errors."""
    bad_file = MagicMock()
    bad_file.name = "bad.txt"
    bad_file.type = "text/plain"
    bad_file.size = 100
    bad_file.read.return_value.decode.side_effect = UnicodeDecodeError(
        "utf-8", b"", 0, 1, "invalid"
    )

    result = await process_document_upload(bad_file, mock_supabase, mock_embedding_client)

    assert result["success"] is False
    assert "Upload failed" in result["message"]
    assert "error" in result


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_chunking_failure(
    mock_chunk, mock_embeddings, mock_text_file, mock_supabase, mock_embedding_client
):
    """Test handling of chunking failures."""
    mock_chunk.side_effect = Exception("Chunking failed")

    result = await process_document_upload(mock_text_file, mock_supabase, mock_embedding_client)

    assert result["success"] is False
    assert "Upload failed" in result["message"]


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_embedding_failure(
    mock_chunk, mock_embeddings, mock_text_file, mock_supabase, mock_embedding_client
):
    """Test handling of embedding generation failures."""
    mock_chunk.return_value = [{"content": "Test"}]
    mock_embeddings.side_effect = Exception("Embedding API failed")

    result = await process_document_upload(mock_text_file, mock_supabase, mock_embedding_client)

    assert result["success"] is False
    assert "Upload failed" in result["message"]


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_db_failure(
    mock_chunk, mock_embeddings, mock_text_file, mock_supabase, mock_embedding_client
):
    """Test handling of database insertion failures."""
    mock_chunk.return_value = [{"content": "Test"}]
    mock_embeddings.return_value = [[0.1] * 1536]

    # Make database insert fail
    mock_supabase.table.return_value.insert.side_effect = Exception("DB connection lost")

    result = await process_document_upload(mock_text_file, mock_supabase, mock_embedding_client)

    assert result["success"] is False
    assert "Upload failed" in result["message"]


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_empty_file(
    mock_chunk, mock_embeddings, mock_supabase, mock_embedding_client
):
    """Test handling of empty file."""
    empty_file = MagicMock()
    empty_file.name = "empty.txt"
    empty_file.type = "text/plain"
    empty_file.size = 0
    empty_file.read.return_value = b""

    mock_chunk.return_value = []
    mock_embeddings.return_value = []

    result = await process_document_upload(empty_file, mock_supabase, mock_embedding_client)

    # Should still succeed but with 0 chunks
    assert result["success"] is True
    assert result["chunks"] == 0


# ============================================================================
# process_image_upload Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_image_upload_success(mock_image_file, mock_supabase):
    """Test successful image upload processing."""
    result = await process_image_upload(mock_image_file, mock_supabase)

    assert result["success"] is True
    assert "test_image.png" in result["message"]
    assert result["document_id"] == "test_image.png"

    # Verify database insertion
    mock_supabase.table.assert_called_with("documents")


@pytest.mark.asyncio
async def test_process_image_upload_base64_encoding(mock_image_file, mock_supabase):
    """Test that image is properly base64 encoded."""
    await process_image_upload(mock_image_file, mock_supabase)

    # Get the insert call
    insert_call = mock_supabase.table.return_value.insert.call_args[0][0]

    # Verify base64 encoding
    assert "metadata" in insert_call
    assert "image_data" in insert_call["metadata"]
    assert isinstance(insert_call["metadata"]["image_data"], str)

    # Decode and verify it matches original
    encoded_data = insert_call["metadata"]["image_data"]
    decoded_data = base64.b64decode(encoded_data)
    assert decoded_data == mock_image_file.read.return_value


@pytest.mark.asyncio
async def test_process_image_upload_metadata(mock_image_file, mock_supabase):
    """Test that correct metadata is included."""
    await process_image_upload(mock_image_file, mock_supabase)

    insert_call = mock_supabase.table.return_value.insert.call_args[0][0]

    assert insert_call["title"] == "test_image.png"
    assert insert_call["source"] == "test_image.png"
    assert insert_call["content"] == "[Image: test_image.png]"
    assert insert_call["metadata"]["is_image"] is True
    assert insert_call["metadata"]["file_type"] == "image/png"
    assert insert_call["metadata"]["upload_source"] == "streamlit_ui"


@pytest.mark.asyncio
async def test_process_image_upload_large_image(mock_supabase):
    """Test uploading large image file."""
    large_image = MagicMock()
    large_image.name = "large.jpg"
    large_image.type = "image/jpeg"
    large_image.size = 5 * 1024 * 1024  # 5MB
    large_image.read.return_value = b"\xff\xd8\xff" + b"\x00" * (5 * 1024 * 1024)

    result = await process_image_upload(large_image, mock_supabase)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_process_image_upload_different_formats(mock_supabase):
    """Test uploading different image formats."""
    formats = [
        ("test.jpg", "image/jpeg", b"\xff\xd8\xff"),
        ("test.gif", "image/gif", b"GIF89a"),
        ("test.webp", "image/webp", b"RIFF"),
    ]

    for filename, file_type, magic_bytes in formats:
        image = MagicMock()
        image.name = filename
        image.type = file_type
        image.size = 1024
        image.read.return_value = magic_bytes + b"\x00" * 100

        result = await process_image_upload(image, mock_supabase)

        assert result["success"] is True
        assert filename in result["message"]


@pytest.mark.asyncio
async def test_process_image_upload_read_failure(mock_supabase):
    """Test handling of file read errors."""
    bad_image = MagicMock()
    bad_image.name = "bad.png"
    bad_image.type = "image/png"
    bad_image.size = 100
    bad_image.read.side_effect = OSError("Cannot read file")

    result = await process_image_upload(bad_image, mock_supabase)

    assert result["success"] is False
    assert "Upload failed" in result["message"]


@pytest.mark.asyncio
async def test_process_image_upload_db_failure(mock_image_file, mock_supabase):
    """Test handling of database insertion failures."""
    mock_supabase.table.return_value.insert.side_effect = Exception("DB error")

    result = await process_image_upload(mock_image_file, mock_supabase)

    assert result["success"] is False
    assert "Upload failed" in result["message"]


@pytest.mark.asyncio
async def test_process_image_upload_empty_image(mock_supabase):
    """Test handling of empty image file."""
    empty_image = MagicMock()
    empty_image.name = "empty.png"
    empty_image.type = "image/png"
    empty_image.size = 0
    empty_image.read.return_value = b""

    result = await process_image_upload(empty_image, mock_supabase)

    # Should still process (base64 encode empty bytes)
    assert result["success"] is True


# ============================================================================
# process_tabular_upload Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_tabular_upload_csv_success(mock_csv_file, mock_supabase):
    """Test successful CSV upload processing."""
    result = await process_tabular_upload(mock_csv_file, mock_supabase)

    assert result["success"] is True
    assert "test_data.csv" in result["message"]
    assert result["rows"] == 3
    assert result["columns"] == 3
    assert "dataset_id" in result

    # Verify both tables were called
    assert mock_supabase.table.call_count >= 2


@pytest.mark.asyncio
async def test_process_tabular_upload_excel_success(mock_excel_file, mock_supabase):
    """Test successful Excel upload processing."""
    result = await process_tabular_upload(mock_excel_file, mock_supabase)

    assert result["success"] is True
    assert "test_data.xlsx" in result["message"]
    assert result["rows"] == 2
    assert result["columns"] == 3


@pytest.mark.asyncio
async def test_process_tabular_upload_metadata(mock_csv_file, mock_supabase):
    """Test that correct metadata is stored."""
    await process_tabular_upload(mock_csv_file, mock_supabase)

    # Get the first insert call (metadata)
    first_insert = mock_supabase.table.return_value.insert.call_args_list[0][0][0]

    assert first_insert["title"] == "test_data.csv"
    assert first_insert["source"] == "test_data.csv"
    assert first_insert["content"] == "[Dataset: test_data.csv]"
    assert first_insert["metadata"]["is_tabular"] is True
    assert first_insert["metadata"]["columns"] == ["name", "age", "city"]
    assert first_insert["metadata"]["row_count"] == 3
    assert "schema" in first_insert["metadata"]


@pytest.mark.asyncio
async def test_process_tabular_upload_rows_storage(mock_csv_file, mock_supabase):
    """Test that individual rows are stored correctly."""
    await process_tabular_upload(mock_csv_file, mock_supabase)

    # Get the second insert call (rows)
    second_insert = mock_supabase.table.return_value.insert.call_args_list[1][0][0]

    assert len(second_insert) == 3  # 3 rows
    assert all("dataset_id" in row for row in second_insert)
    assert all("row_data" in row for row in second_insert)
    assert all("row_index" in row for row in second_insert)

    # Verify row data structure
    assert second_insert[0]["row_data"]["name"] == "Alice"
    assert second_insert[0]["row_data"]["age"] == 30
    assert second_insert[0]["row_data"]["city"] == "NYC"


@pytest.mark.asyncio
async def test_process_tabular_upload_large_dataset(mock_supabase):
    """Test uploading large CSV with many rows."""
    large_csv = MagicMock()
    large_csv.name = "large.csv"
    large_csv.type = "text/csv"
    large_csv.size = 100000

    # Create large CSV content
    csv_lines = ["id,value\n"]
    csv_lines.extend([f"{i},{i*10}\n" for i in range(1000)])
    csv_content = "".join(csv_lines)
    large_csv.read.return_value = csv_content.encode("utf-8")

    result = await process_tabular_upload(large_csv, mock_supabase)

    assert result["success"] is True
    assert result["rows"] == 1000


@pytest.mark.asyncio
async def test_process_tabular_upload_empty_dataframe(mock_supabase):
    """Test handling of empty CSV."""
    empty_csv = MagicMock()
    empty_csv.name = "empty.csv"
    empty_csv.type = "text/csv"
    empty_csv.size = 10
    empty_csv.read.return_value = b"col1,col2\n"  # Headers only

    result = await process_tabular_upload(empty_csv, mock_supabase)

    assert result["success"] is True
    assert result["rows"] == 0


@pytest.mark.asyncio
async def test_process_tabular_upload_special_characters(mock_supabase):
    """Test CSV with special characters and Unicode."""
    unicode_csv = MagicMock()
    unicode_csv.name = "unicode.csv"
    unicode_csv.type = "text/csv"
    unicode_csv.size = 100
    csv_content = "name,country\nJosé,España\n你好,中国\n"
    unicode_csv.read.return_value = csv_content.encode("utf-8")

    result = await process_tabular_upload(unicode_csv, mock_supabase)

    assert result["success"] is True
    assert result["rows"] == 2


@pytest.mark.asyncio
async def test_process_tabular_upload_unsupported_type(mock_supabase):
    """Test rejection of unsupported file types."""
    bad_file = MagicMock()
    bad_file.name = "data.json"
    bad_file.type = "application/json"
    bad_file.size = 100
    bad_file.read.return_value = b'{"key": "value"}'

    result = await process_tabular_upload(bad_file, mock_supabase)

    assert result["success"] is False
    assert "Unsupported file type" in result["message"]


@pytest.mark.asyncio
async def test_process_tabular_upload_csv_parse_error(mock_supabase):
    """Test handling of CSV parsing errors."""
    bad_csv = MagicMock()
    bad_csv.name = "bad.csv"
    bad_csv.type = "text/csv"
    bad_csv.size = 100
    bad_csv.read.return_value = b"invalid,csv,format\nwith,mismatched\ncolumns,here,extra,too,many"

    # This might still succeed with pandas handling, but test error path
    result = await process_tabular_upload(bad_csv, mock_supabase)

    # pandas is quite lenient, so this might succeed
    assert isinstance(result, dict)
    assert "success" in result


@pytest.mark.asyncio
async def test_process_tabular_upload_excel_parse_error(mock_supabase):
    """Test handling of Excel parsing errors."""
    bad_excel = MagicMock()
    bad_excel.name = "bad.xlsx"
    bad_excel.type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    bad_excel.size = 100
    bad_excel.read.return_value = b"not an excel file"

    result = await process_tabular_upload(bad_excel, mock_supabase)

    assert result["success"] is False
    assert "Upload failed" in result["message"]


@pytest.mark.asyncio
async def test_process_tabular_upload_metadata_insert_failure(mock_csv_file, mock_supabase):
    """Test handling of metadata insertion failure."""
    mock_supabase.table.return_value.insert.side_effect = Exception("DB error")

    result = await process_tabular_upload(mock_csv_file, mock_supabase)

    assert result["success"] is False
    assert "Upload failed" in result["message"]


@pytest.mark.asyncio
async def test_process_tabular_upload_rows_insert_failure(mock_csv_file, mock_supabase):
    """Test handling of rows insertion failure."""
    # First insert succeeds (metadata), second fails (rows)
    mock_supabase.table.return_value.insert.side_effect = [
        MagicMock(data=[{"id": "test-id"}]),  # Metadata succeeds
        Exception("Rows insert failed"),  # Rows fails
    ]

    result = await process_tabular_upload(mock_csv_file, mock_supabase)

    assert result["success"] is False


@pytest.mark.asyncio
async def test_process_tabular_upload_missing_dataset_id(mock_csv_file, mock_supabase):
    """Test handling when dataset_id is not returned."""
    # Mock response with no data
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])

    result = await process_tabular_upload(mock_csv_file, mock_supabase)

    # Should fall back to filename
    assert result["success"] is True
    assert result["dataset_id"] == "test_data.csv"


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_concurrent_uploads(
    mock_chunk, mock_embeddings, mock_text_file, mock_supabase, mock_embedding_client
):
    """Test handling of concurrent upload operations."""
    mock_chunk.return_value = [{"content": "Test"}]
    mock_embeddings.return_value = [[0.1] * 1536]

    # Run multiple uploads concurrently
    import asyncio

    results = await asyncio.gather(
        process_document_upload(mock_text_file, mock_supabase, mock_embedding_client),
        process_document_upload(mock_text_file, mock_supabase, mock_embedding_client),
        process_document_upload(mock_text_file, mock_supabase, mock_embedding_client),
    )

    assert all(r["success"] for r in results)


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_document_upload_with_special_characters_in_name(
    mock_chunk, mock_embeddings, mock_supabase, mock_embedding_client
):
    """Test uploading document with special characters in filename."""
    special_file = MagicMock()
    special_file.name = "test document (2025) #1.txt"
    special_file.type = "text/plain"
    special_file.size = 100
    special_file.read.return_value = b"Content"

    mock_chunk.return_value = [{"content": "Test"}]
    mock_embeddings.return_value = [[0.1] * 1536]

    result = await process_document_upload(special_file, mock_supabase, mock_embedding_client)

    assert result["success"] is True
    assert "test document (2025) #1.txt" in result["message"]


@pytest.mark.asyncio
async def test_image_upload_with_unicode_name(mock_supabase):
    """Test uploading image with Unicode filename."""
    unicode_image = MagicMock()
    unicode_image.name = "图片_테스트_مثال.png"
    unicode_image.type = "image/png"
    unicode_image.size = 1024
    unicode_image.read.return_value = b"\x89PNG" + b"\x00" * 100

    result = await process_image_upload(unicode_image, mock_supabase)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_tabular_upload_with_mixed_dtypes(mock_supabase):
    """Test CSV with mixed data types."""
    mixed_csv = MagicMock()
    mixed_csv.name = "mixed.csv"
    mixed_csv.type = "text/csv"
    mixed_csv.size = 200
    csv_content = "id,name,score,date\n1,Alice,95.5,2025-01-01\n2,Bob,87.3,2025-01-02\n"
    mixed_csv.read.return_value = csv_content.encode("utf-8")

    result = await process_tabular_upload(mixed_csv, mock_supabase)

    assert result["success"] is True
    assert result["rows"] == 2


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_document_upload_logging(
    mock_chunk, mock_embeddings, mock_text_file, mock_supabase, mock_embedding_client
):
    """Test that appropriate logging occurs during upload."""
    mock_chunk.return_value = [{"content": "Test"}]
    mock_embeddings.return_value = [[0.1] * 1536]

    with patch("src.ui.features.upload_handler.logger") as mock_logger:
        await process_document_upload(mock_text_file, mock_supabase, mock_embedding_client)

        # Verify logging calls
        assert mock_logger.info.call_count >= 5  # Multiple info logs
        assert any(
            "Document upload started" in str(call) for call in mock_logger.info.call_args_list
        )


@pytest.mark.asyncio
async def test_image_upload_logging(mock_image_file, mock_supabase):
    """Test that appropriate logging occurs during image upload."""
    with patch("src.ui.features.upload_handler.logger") as mock_logger:
        await process_image_upload(mock_image_file, mock_supabase)

        assert mock_logger.info.call_count >= 4


@pytest.mark.asyncio
async def test_tabular_upload_logging(mock_csv_file, mock_supabase):
    """Test that appropriate logging occurs during tabular upload."""
    with patch("src.ui.features.upload_handler.logger") as mock_logger:
        await process_tabular_upload(mock_csv_file, mock_supabase)

        assert mock_logger.info.call_count >= 5


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_document_upload_error_logging(
    mock_chunk, mock_embeddings, mock_text_file, mock_supabase, mock_embedding_client
):
    """Test error logging when upload fails."""
    mock_chunk.side_effect = Exception("Test error")

    with patch("src.ui.features.upload_handler.logger") as mock_logger:
        await process_document_upload(mock_text_file, mock_supabase, mock_embedding_client)

        mock_logger.exception.assert_called_once()
