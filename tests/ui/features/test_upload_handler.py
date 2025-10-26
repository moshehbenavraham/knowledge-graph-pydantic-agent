"""Comprehensive tests for upload_handler.py module."""

import base64
import io
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.ui.features.upload_handler import (
    process_document_upload,
    process_image_upload,
    process_tabular_upload,
)


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = Mock()
    table_mock = Mock()
    insert_mock = Mock()
    execute_mock = Mock()

    # Chain the mocks: client.table().insert().execute()
    execute_mock.return_value = Mock(data=[{"id": "test_id"}])
    insert_mock.execute = execute_mock
    table_mock.insert.return_value = insert_mock
    client.table.return_value = table_mock

    return client


@pytest.fixture
def mock_embedding_client():
    """Create a mock embedding client."""
    return Mock()


@pytest.fixture
def mock_uploaded_file():
    """Create a mock Streamlit UploadedFile."""

    def _create_file(name, content, file_type="text/plain", size=1024):
        file = Mock()
        file.name = name
        file.type = file_type
        file.size = size
        file.read = Mock(
            return_value=content.encode("utf-8") if isinstance(content, str) else content
        )
        return file

    return _create_file


@pytest.fixture
def mock_image_file():
    """Create a mock image file."""
    file = Mock()
    file.name = "test_image.png"
    file.type = "image/png"
    file.size = 2048
    file.read = Mock(return_value=b"\x89PNG\r\n\x1a\n" + b"fake_image_data" * 100)
    return file


@pytest.fixture
def mock_csv_file():
    """Create a mock CSV file."""
    csv_content = "name,age,city\nJohn,30,NYC\nJane,25,LA\nBob,35,SF"
    file = Mock()
    file.name = "test_data.csv"
    file.type = "text/csv"
    file.size = len(csv_content)
    file.read = Mock(return_value=csv_content.encode("utf-8"))
    return file


@pytest.fixture
def mock_excel_file():
    """Create a mock Excel file."""
    # Create a real Excel file in memory
    df = pd.DataFrame({"name": ["John", "Jane"], "age": [30, 25], "city": ["NYC", "LA"]})
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_bytes = excel_buffer.getvalue()

    file = Mock()
    file.name = "test_data.xlsx"
    file.type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    file.size = len(excel_bytes)
    file.read = Mock(return_value=excel_bytes)
    return file


# ============================================================================
# process_document_upload Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_document_upload_success(
    mock_uploaded_file, mock_supabase_client, mock_embedding_client
):
    """Test successful document upload."""
    file = mock_uploaded_file("test.txt", "This is a test document. " * 100, "text/plain")

    with (
        patch("src.agentic_rag.ingestion.chunker.semantic_chunk") as mock_chunk,
        patch("src.agentic_rag.ingestion.embedder.generate_embeddings") as mock_embed,
    ):
        # Mock chunking to return 3 chunks
        mock_chunk.return_value = [
            {"content": "chunk 1"},
            {"content": "chunk 2"},
            {"content": "chunk 3"},
        ]

        # Mock embeddings (async function)
        mock_embed.return_value = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]

        result = await process_document_upload(file, mock_supabase_client, mock_embedding_client)

        assert result["success"] is True
        assert result["chunks"] == 3
        assert "test.txt" in result["message"]
        assert result["document_id"] == "test.txt"

        # Verify chunking was called
        mock_chunk.assert_called_once()

        # Verify embeddings were generated
        mock_embed.assert_called_once()

        # Verify database insertion
        mock_supabase_client.table.assert_called_with("documents")
        mock_supabase_client.table().insert.assert_called_once()


@pytest.mark.asyncio
async def test_process_document_upload_empty_content(
    mock_uploaded_file, mock_supabase_client, mock_embedding_client
):
    """Test document upload with empty content."""
    file = mock_uploaded_file("empty.txt", "", "text/plain")

    with (
        patch("src.agentic_rag.ingestion.chunker.semantic_chunk") as mock_chunk,
        patch("src.agentic_rag.ingestion.embedder.generate_embeddings") as mock_embed,
    ):
        mock_chunk.return_value = []
        mock_embed.return_value = []

        result = await process_document_upload(file, mock_supabase_client, mock_embedding_client)

        assert result["success"] is True
        assert result["chunks"] == 0


@pytest.mark.asyncio
async def test_process_document_upload_chunking_error(
    mock_uploaded_file, mock_supabase_client, mock_embedding_client
):
    """Test document upload when chunking fails."""
    file = mock_uploaded_file("test.txt", "Test content", "text/plain")

    with patch(
        "src.agentic_rag.ingestion.chunker.semantic_chunk", side_effect=Exception("Chunking failed")
    ):
        result = await process_document_upload(file, mock_supabase_client, mock_embedding_client)

        assert result["success"] is False
        assert "failed" in result["message"].lower()
        assert "error" in result


@pytest.mark.asyncio
async def test_process_document_upload_embedding_error(
    mock_uploaded_file, mock_supabase_client, mock_embedding_client
):
    """Test document upload when embedding generation fails."""
    file = mock_uploaded_file("test.txt", "Test content", "text/plain")

    with (
        patch("src.agentic_rag.ingestion.chunker.semantic_chunk") as mock_chunk,
        patch(
            "src.agentic_rag.ingestion.embedder.generate_embeddings",
            side_effect=Exception("Embedding failed"),
        ),
    ):
        mock_chunk.return_value = [{"content": "chunk 1"}]

        result = await process_document_upload(file, mock_supabase_client, mock_embedding_client)

        assert result["success"] is False
        assert "error" in result


@pytest.mark.asyncio
async def test_process_document_upload_database_error(
    mock_uploaded_file, mock_supabase_client, mock_embedding_client
):
    """Test document upload when database insertion fails."""
    file = mock_uploaded_file("test.txt", "Test content", "text/plain")

    with (
        patch("src.agentic_rag.ingestion.chunker.semantic_chunk") as mock_chunk,
        patch("src.agentic_rag.ingestion.embedder.generate_embeddings") as mock_embed,
    ):
        mock_chunk.return_value = [{"content": "chunk 1"}]
        mock_embed.return_value = [[0.1] * 1536]

        # Make database insertion fail
        mock_supabase_client.table().insert().execute.side_effect = Exception("DB Error")

        result = await process_document_upload(file, mock_supabase_client, mock_embedding_client)

        assert result["success"] is False
        assert "error" in result


@pytest.mark.asyncio
async def test_process_document_upload_decode_error(mock_supabase_client, mock_embedding_client):
    """Test document upload when file cannot be decoded."""
    file = Mock()
    file.name = "binary.bin"
    file.type = "application/octet-stream"
    file.size = 1024
    file.read = Mock(return_value=b"\x80\x81\x82")  # Invalid UTF-8

    result = await process_document_upload(file, mock_supabase_client, mock_embedding_client)

    assert result["success"] is False
    assert "error" in result


# ============================================================================
# process_image_upload Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_image_upload_success(mock_image_file, mock_supabase_client):
    """Test successful image upload."""
    result = await process_image_upload(mock_image_file, mock_supabase_client)

    assert result["success"] is True
    assert "test_image.png" in result["message"]
    assert result["document_id"] == "test_image.png"

    # Verify database insertion
    mock_supabase_client.table.assert_called_with("documents")
    insert_call = mock_supabase_client.table().insert.call_args[0][0]

    assert insert_call["title"] == "test_image.png"
    assert insert_call["source"] == "test_image.png"
    assert "[Image:" in insert_call["content"]
    assert "image_data" in insert_call["metadata"]
    assert insert_call["metadata"]["is_image"] is True


@pytest.mark.asyncio
async def test_process_image_upload_base64_encoding(mock_image_file, mock_supabase_client):
    """Test that image is properly base64 encoded."""
    result = await process_image_upload(mock_image_file, mock_supabase_client)

    assert result["success"] is True

    # Verify the image was base64 encoded
    insert_call = mock_supabase_client.table().insert.call_args[0][0]
    image_data = insert_call["metadata"]["image_data"]

    # Verify it's valid base64
    try:
        decoded = base64.b64decode(image_data)
        assert len(decoded) > 0
    except Exception as e:
        pytest.fail(f"Image data is not valid base64: {e}")


@pytest.mark.asyncio
async def test_process_image_upload_database_error(mock_image_file, mock_supabase_client):
    """Test image upload when database insertion fails."""
    mock_supabase_client.table().insert().execute.side_effect = Exception("DB Error")

    result = await process_image_upload(mock_image_file, mock_supabase_client)

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_process_image_upload_read_error(mock_supabase_client):
    """Test image upload when file read fails."""
    file = Mock()
    file.name = "bad_image.png"
    file.type = "image/png"
    file.size = 1024
    file.read = Mock(side_effect=Exception("Read failed"))

    result = await process_image_upload(file, mock_supabase_client)

    assert result["success"] is False
    assert "error" in result


# ============================================================================
# process_tabular_upload Tests (CSV)
# ============================================================================


@pytest.mark.asyncio
async def test_process_tabular_upload_csv_success(mock_csv_file, mock_supabase_client):
    """Test successful CSV upload."""
    result = await process_tabular_upload(mock_csv_file, mock_supabase_client)

    assert result["success"] is True
    assert result["rows"] == 3
    assert result["columns"] == 3
    assert "test_data.csv" in result["message"]
    assert result["dataset_id"] == "test_id"

    # Verify metadata was inserted
    mock_supabase_client.table.assert_any_call("documents")
    metadata_call = mock_supabase_client.table().insert.call_args_list[0][0][0]

    assert metadata_call["title"] == "test_data.csv"
    assert metadata_call["metadata"]["is_tabular"] is True
    assert metadata_call["metadata"]["columns"] == ["name", "age", "city"]
    assert metadata_call["metadata"]["row_count"] == 3

    # Verify rows were inserted
    mock_supabase_client.table.assert_any_call("document_rows")


@pytest.mark.asyncio
async def test_process_tabular_upload_excel_success(mock_excel_file, mock_supabase_client):
    """Test successful Excel upload."""
    result = await process_tabular_upload(mock_excel_file, mock_supabase_client)

    assert result["success"] is True
    assert result["rows"] == 2
    assert result["columns"] == 3
    assert "test_data.xlsx" in result["message"]


@pytest.mark.asyncio
async def test_process_tabular_upload_unsupported_type(mock_supabase_client):
    """Test tabular upload with unsupported file type."""
    file = Mock()
    file.name = "test.txt"
    file.type = "text/plain"
    file.size = 1024

    result = await process_tabular_upload(file, mock_supabase_client)

    assert result["success"] is False
    assert "Unsupported file type" in result["message"]


@pytest.mark.asyncio
async def test_process_tabular_upload_empty_csv(mock_supabase_client):
    """Test upload of empty CSV."""
    csv_content = "name,age,city"  # Header only, no data
    file = Mock()
    file.name = "empty.csv"
    file.type = "text/csv"
    file.size = len(csv_content)
    file.read = Mock(return_value=csv_content.encode("utf-8"))

    result = await process_tabular_upload(file, mock_supabase_client)

    assert result["success"] is True
    assert result["rows"] == 0


@pytest.mark.asyncio
async def test_process_tabular_upload_csv_parse_error(mock_supabase_client):
    """Test CSV upload when parsing fails."""
    file = Mock()
    file.name = "bad.csv"
    file.type = "text/csv"
    file.size = 1024
    file.read = Mock(return_value=b"invalid\xffcsv\xffdata")

    result = await process_tabular_upload(file, mock_supabase_client)

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_process_tabular_upload_database_error(mock_csv_file, mock_supabase_client):
    """Test tabular upload when database insertion fails."""
    mock_supabase_client.table().insert().execute.side_effect = Exception("DB Error")

    result = await process_tabular_upload(mock_csv_file, mock_supabase_client)

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_process_tabular_upload_row_storage(mock_csv_file, mock_supabase_client):
    """Test that individual rows are properly stored."""
    result = await process_tabular_upload(mock_csv_file, mock_supabase_client)

    assert result["success"] is True

    # Get the document_rows insert call
    calls = mock_supabase_client.table.call_args_list
    rows_insert_call = None
    for call in calls:
        if call and len(call) > 0 and len(call[0]) > 0 and call[0][0] == "document_rows":
            # Get the insert call after this table() call
            rows_insert_call = mock_supabase_client.table().insert.call_args

    assert rows_insert_call is not None
    rows_data = rows_insert_call[0][0]

    # Verify we have 3 rows
    assert len(rows_data) == 3

    # Verify row structure
    for i, row_doc in enumerate(rows_data):
        assert "dataset_id" in row_doc
        assert "row_data" in row_doc
        assert "row_index" in row_doc
        assert row_doc["row_index"] == i


# ============================================================================
# Edge Cases & Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_document_upload_large_file(
    mock_uploaded_file, mock_supabase_client, mock_embedding_client
):
    """Test document upload with large file."""
    # Create a large document (>10KB)
    large_content = "This is a test sentence. " * 500
    file = mock_uploaded_file("large.txt", large_content, "text/plain", size=len(large_content))

    with (
        patch("src.agentic_rag.ingestion.chunker.semantic_chunk") as mock_chunk,
        patch("src.agentic_rag.ingestion.embedder.generate_embeddings") as mock_embed,
    ):
        # Simulate chunking into 10 chunks
        mock_chunk.return_value = [{"content": f"chunk {i}"} for i in range(10)]
        mock_embed.return_value = [[0.1] * 1536] * 10

        result = await process_document_upload(file, mock_supabase_client, mock_embedding_client)

        assert result["success"] is True
        assert result["chunks"] == 10


@pytest.mark.asyncio
async def test_process_document_upload_special_characters(
    mock_uploaded_file, mock_supabase_client, mock_embedding_client
):
    """Test document upload with special characters."""
    content = "Test with émojis 🔥 and speçial characters: ñ, ü, é"
    file = mock_uploaded_file("special.txt", content, "text/plain")

    with (
        patch("src.agentic_rag.ingestion.chunker.semantic_chunk") as mock_chunk,
        patch("src.agentic_rag.ingestion.embedder.generate_embeddings") as mock_embed,
    ):
        mock_chunk.return_value = [{"content": content}]
        mock_embed.return_value = [[0.1] * 1536]

        result = await process_document_upload(file, mock_supabase_client, mock_embedding_client)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_process_tabular_upload_large_dataset(mock_supabase_client):
    """Test tabular upload with large dataset."""
    # Create a CSV with 100 rows
    rows = ["name,age,city"]
    rows.extend([f"Person{i},3{i % 10},City{i % 5}" for i in range(100)])
    csv_content = "\n".join(rows)

    file = Mock()
    file.name = "large_data.csv"
    file.type = "text/csv"
    file.size = len(csv_content)
    file.read = Mock(return_value=csv_content.encode("utf-8"))

    result = await process_tabular_upload(file, mock_supabase_client)

    assert result["success"] is True
    assert result["rows"] == 100


@pytest.mark.asyncio
async def test_process_tabular_upload_mixed_dtypes(mock_supabase_client):
    """Test tabular upload with mixed data types."""
    csv_content = "name,age,salary,is_active\nJohn,30,50000.50,true\nJane,25,60000.75,false"
    file = Mock()
    file.name = "mixed_types.csv"
    file.type = "text/csv"
    file.size = len(csv_content)
    file.read = Mock(return_value=csv_content.encode("utf-8"))

    result = await process_tabular_upload(file, mock_supabase_client)

    assert result["success"] is True
    assert result["rows"] == 2
    assert result["columns"] == 4


@pytest.mark.asyncio
async def test_process_image_upload_different_formats(mock_supabase_client):
    """Test image upload with different image formats."""
    formats = [
        ("test.png", "image/png", b"\x89PNG\r\n\x1a\n"),
        ("test.jpg", "image/jpeg", b"\xff\xd8\xff"),
        ("test.gif", "image/gif", b"GIF89a"),
    ]

    for name, mime_type, magic_bytes in formats:
        file = Mock()
        file.name = name
        file.type = mime_type
        file.size = 1024
        file.read = Mock(return_value=magic_bytes + b"fake_data" * 100)

        result = await process_image_upload(file, mock_supabase_client)

        assert result["success"] is True
        assert name in result["message"]
