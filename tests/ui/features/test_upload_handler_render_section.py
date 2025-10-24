"""
Additional tests for upload_handler.py render_upload_section function.

Tests Streamlit UI rendering, event loop handling, and integration scenarios.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = MagicMock()
    table_mock = MagicMock()
    insert_mock = MagicMock()
    execute_mock = MagicMock()

    execute_mock.return_value = MagicMock(data=[{"id": "test-doc-id"}])
    insert_mock.return_value.execute = execute_mock
    table_mock.return_value.insert = insert_mock
    client.table = table_mock

    return client


@pytest.fixture
def mock_embedding_client():
    """Mock embedding client."""
    return MagicMock()


# ============================================================================
# render_upload_section Tests
# ============================================================================


@patch("src.ui.features.upload_handler.st")
def test_render_upload_section_basic(mock_st, mock_supabase, mock_embedding_client):
    """Test basic rendering of upload section."""
    from src.ui.features.upload_handler import render_upload_section

    # Mock streamlit components
    mock_st.selectbox.return_value = "Documents (PDF, TXT, MD)"
    mock_st.file_uploader.return_value = None

    render_upload_section(mock_supabase, mock_embedding_client)

    # Verify Streamlit components were called
    mock_st.subheader.assert_called_once_with("📤 Upload Files")
    mock_st.selectbox.assert_called_once()
    mock_st.file_uploader.assert_called_once()


@patch("src.ui.features.upload_handler.st")
def test_render_upload_section_document_type(mock_st, mock_supabase, mock_embedding_client):
    """Test render with Documents file type selected."""
    from src.ui.features.upload_handler import render_upload_section

    mock_st.selectbox.return_value = "Documents (PDF, TXT, MD)"
    mock_st.file_uploader.return_value = None

    render_upload_section(mock_supabase, mock_embedding_client)

    # Verify correct file types
    call_kwargs = mock_st.file_uploader.call_args[1]
    assert "txt" in call_kwargs["type"]
    assert "md" in call_kwargs["type"]
    assert "pdf" in call_kwargs["type"]


@patch("src.ui.features.upload_handler.st")
def test_render_upload_section_image_type(mock_st, mock_supabase, mock_embedding_client):
    """Test render with Images file type selected."""
    from src.ui.features.upload_handler import render_upload_section

    mock_st.selectbox.return_value = "Images (PNG, JPG)"
    mock_st.file_uploader.return_value = None

    render_upload_section(mock_supabase, mock_embedding_client)

    # Verify correct file types
    call_kwargs = mock_st.file_uploader.call_args[1]
    assert "png" in call_kwargs["type"]
    assert "jpg" in call_kwargs["type"]


@patch("src.ui.features.upload_handler.st")
def test_render_upload_section_data_type(mock_st, mock_supabase, mock_embedding_client):
    """Test render with Data file type selected."""
    from src.ui.features.upload_handler import render_upload_section

    mock_st.selectbox.return_value = "Data (CSV, Excel)"
    mock_st.file_uploader.return_value = None

    render_upload_section(mock_supabase, mock_embedding_client)

    # Verify correct file types
    call_kwargs = mock_st.file_uploader.call_args[1]
    assert "csv" in call_kwargs["type"]
    assert "xlsx" in call_kwargs["type"]


@patch("src.ui.features.upload_handler.st")
@patch("src.ui.features.upload_handler.asyncio.run")
@patch("src.ui.features.upload_handler.process_document_upload")
@patch("src.ui.features.upload_handler.nest_asyncio")
def test_render_upload_section_document_upload_success(
    mock_nest_asyncio,
    mock_process_doc,
    mock_asyncio_run,
    mock_st,
    mock_supabase,
    mock_embedding_client,
):
    """Test successful document upload through UI."""
    from src.ui.features.upload_handler import render_upload_section

    # Mock file upload
    mock_file = MagicMock()
    mock_file.name = "test.txt"
    mock_file.type = "text/plain"
    mock_file.size = 1024

    mock_st.selectbox.return_value = "Documents (PDF, TXT, MD)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = True  # Upload button clicked

    # Mock successful upload
    mock_asyncio_run.return_value = {
        "success": True,
        "message": "Upload successful",
        "chunks": 5,
    }

    # Mock columns
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = [mock_col1, mock_col2]

    # Mock spinner context
    mock_spinner = MagicMock()
    mock_spinner.__enter__ = MagicMock()
    mock_spinner.__exit__ = MagicMock()
    mock_st.spinner.return_value = mock_spinner

    render_upload_section(mock_supabase, mock_embedding_client)

    # Verify upload button was created
    mock_st.button.assert_called_once()


@patch("src.ui.features.upload_handler.st")
@patch("src.ui.features.upload_handler.asyncio.run")
@patch("src.ui.features.upload_handler.process_image_upload")
@patch("src.ui.features.upload_handler.nest_asyncio")
def test_render_upload_section_image_upload_success(
    mock_nest_asyncio,
    mock_process_image,
    mock_asyncio_run,
    mock_st,
    mock_supabase,
    mock_embedding_client,
):
    """Test successful image upload through UI."""
    from src.ui.features.upload_handler import render_upload_section

    mock_file = MagicMock()
    mock_file.name = "test.png"
    mock_file.type = "image/png"
    mock_file.size = 5120

    mock_st.selectbox.return_value = "Images (PNG, JPG)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = True

    mock_asyncio_run.return_value = {
        "success": True,
        "message": "Image uploaded",
    }

    mock_col1, mock_col2 = MagicMock(), MagicMock()
    mock_st.columns.return_value = [mock_col1, mock_col2]

    mock_spinner = MagicMock()
    mock_spinner.__enter__ = MagicMock()
    mock_spinner.__exit__ = MagicMock()
    mock_st.spinner.return_value = mock_spinner

    render_upload_section(mock_supabase, mock_embedding_client)

    mock_st.button.assert_called_once()


@patch("src.ui.features.upload_handler.st")
@patch("src.ui.features.upload_handler.asyncio.run")
@patch("src.ui.features.upload_handler.process_tabular_upload")
@patch("src.ui.features.upload_handler.nest_asyncio")
def test_render_upload_section_tabular_upload_success(
    mock_nest_asyncio,
    mock_process_tabular,
    mock_asyncio_run,
    mock_st,
    mock_supabase,
    mock_embedding_client,
):
    """Test successful tabular upload through UI."""
    from src.ui.features.upload_handler import render_upload_section

    mock_file = MagicMock()
    mock_file.name = "test.csv"
    mock_file.type = "text/csv"
    mock_file.size = 2048

    mock_st.selectbox.return_value = "Data (CSV, Excel)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = True

    mock_asyncio_run.return_value = {
        "success": True,
        "message": "Data uploaded",
        "rows": 100,
    }

    mock_col1, mock_col2 = MagicMock(), MagicMock()
    mock_st.columns.return_value = [mock_col1, mock_col2]

    mock_spinner = MagicMock()
    mock_spinner.__enter__ = MagicMock()
    mock_spinner.__exit__ = MagicMock()
    mock_st.spinner.return_value = mock_spinner

    render_upload_section(mock_supabase, mock_embedding_client)

    mock_st.button.assert_called_once()


@patch("src.ui.features.upload_handler.st")
@patch("src.ui.features.upload_handler.asyncio.run")
@patch("src.ui.features.upload_handler.nest_asyncio")
def test_render_upload_section_upload_failure(
    mock_nest_asyncio, mock_asyncio_run, mock_st, mock_supabase, mock_embedding_client
):
    """Test handling of upload failure."""
    from src.ui.features.upload_handler import render_upload_section

    mock_file = MagicMock()
    mock_file.name = "test.txt"
    mock_file.type = "text/plain"
    mock_file.size = 1024

    mock_st.selectbox.return_value = "Documents (PDF, TXT, MD)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = True

    # Mock failed upload
    mock_asyncio_run.return_value = {
        "success": False,
        "message": "Upload failed: Database error",
    }

    mock_col1, mock_col2 = MagicMock(), MagicMock()
    mock_st.columns.return_value = [mock_col1, mock_col2]

    mock_spinner = MagicMock()
    mock_spinner.__enter__ = MagicMock()
    mock_spinner.__exit__ = MagicMock()
    mock_st.spinner.return_value = mock_spinner

    render_upload_section(mock_supabase, mock_embedding_client)

    # Error should be displayed
    mock_st.error.assert_called_once()


@patch("src.ui.features.upload_handler.st")
@patch("src.ui.features.upload_handler.asyncio.get_event_loop")
@patch("src.ui.features.upload_handler.process_document_upload")
@patch("src.ui.features.upload_handler.nest_asyncio")
def test_render_upload_section_runtime_error_fallback(
    mock_nest_asyncio,
    mock_process_doc,
    mock_get_loop,
    mock_st,
    mock_supabase,
    mock_embedding_client,
):
    """Test fallback to event loop when asyncio.run raises RuntimeError."""
    from src.ui.features.upload_handler import render_upload_section

    mock_file = MagicMock()
    mock_file.name = "test.txt"
    mock_file.type = "text/plain"
    mock_file.size = 1024

    mock_st.selectbox.return_value = "Documents (PDF, TXT, MD)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = True

    # Mock RuntimeError from asyncio.run
    with patch(
        "src.ui.features.upload_handler.asyncio.run", side_effect=RuntimeError("Event loop")
    ):
        # Mock event loop
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = {
            "success": True,
            "message": "Upload successful",
        }
        mock_get_loop.return_value = mock_loop

        mock_col1, mock_col2 = MagicMock(), MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]

        mock_spinner = MagicMock()
        mock_spinner.__enter__ = MagicMock()
        mock_spinner.__exit__ = MagicMock()
        mock_st.spinner.return_value = mock_spinner

        render_upload_section(mock_supabase, mock_embedding_client)

        # Verify fallback was used
        mock_loop.run_until_complete.assert_called_once()


@patch("src.ui.features.upload_handler.st")
@patch("src.ui.features.upload_handler.asyncio.get_event_loop")
@patch("src.ui.features.upload_handler.process_image_upload")
@patch("src.ui.features.upload_handler.nest_asyncio")
def test_render_upload_section_image_runtime_error_fallback(
    mock_nest_asyncio,
    mock_process_image,
    mock_get_loop,
    mock_st,
    mock_supabase,
    mock_embedding_client,
):
    """Test fallback for image upload when RuntimeError occurs."""
    from src.ui.features.upload_handler import render_upload_section

    mock_file = MagicMock()
    mock_file.name = "test.png"
    mock_file.type = "image/png"
    mock_file.size = 5120

    mock_st.selectbox.return_value = "Images (PNG, JPG)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = True

    with patch(
        "src.ui.features.upload_handler.asyncio.run", side_effect=RuntimeError("Event loop")
    ):
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = {
            "success": True,
            "message": "Image uploaded",
        }
        mock_get_loop.return_value = mock_loop

        mock_col1, mock_col2 = MagicMock(), MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]

        mock_spinner = MagicMock()
        mock_spinner.__enter__ = MagicMock()
        mock_spinner.__exit__ = MagicMock()
        mock_st.spinner.return_value = mock_spinner

        render_upload_section(mock_supabase, mock_embedding_client)

        mock_loop.run_until_complete.assert_called_once()


@patch("src.ui.features.upload_handler.st")
@patch("src.ui.features.upload_handler.asyncio.get_event_loop")
@patch("src.ui.features.upload_handler.process_tabular_upload")
@patch("src.ui.features.upload_handler.nest_asyncio")
def test_render_upload_section_tabular_runtime_error_fallback(
    mock_nest_asyncio,
    mock_process_tabular,
    mock_get_loop,
    mock_st,
    mock_supabase,
    mock_embedding_client,
):
    """Test fallback for tabular upload when RuntimeError occurs."""
    from src.ui.features.upload_handler import render_upload_section

    mock_file = MagicMock()
    mock_file.name = "test.csv"
    mock_file.type = "text/csv"
    mock_file.size = 2048

    mock_st.selectbox.return_value = "Data (CSV, Excel)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = True

    with patch(
        "src.ui.features.upload_handler.asyncio.run", side_effect=RuntimeError("Event loop")
    ):
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = {
            "success": True,
            "message": "Data uploaded",
        }
        mock_get_loop.return_value = mock_loop

        mock_col1, mock_col2 = MagicMock(), MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]

        mock_spinner = MagicMock()
        mock_spinner.__enter__ = MagicMock()
        mock_spinner.__exit__ = MagicMock()
        mock_st.spinner.return_value = mock_spinner

        render_upload_section(mock_supabase, mock_embedding_client)

        mock_loop.run_until_complete.assert_called_once()


@patch("src.ui.features.upload_handler.st")
def test_render_upload_section_no_file_selected(mock_st, mock_supabase, mock_embedding_client):
    """Test render when no file is selected."""
    from src.ui.features.upload_handler import render_upload_section

    mock_st.selectbox.return_value = "Documents (PDF, TXT, MD)"
    mock_st.file_uploader.return_value = None  # No file

    render_upload_section(mock_supabase, mock_embedding_client)

    # Button should not be created when no file
    mock_st.button.assert_not_called()


@patch("src.ui.features.upload_handler.st")
@patch("src.ui.features.upload_handler.asyncio.run")
@patch("src.ui.features.upload_handler.nest_asyncio")
def test_render_upload_section_button_not_clicked(
    mock_nest_asyncio, mock_asyncio_run, mock_st, mock_supabase, mock_embedding_client
):
    """Test render when file is selected but button not clicked."""
    from src.ui.features.upload_handler import render_upload_section

    mock_file = MagicMock()
    mock_file.name = "test.txt"
    mock_file.type = "text/plain"
    mock_file.size = 1024

    mock_st.selectbox.return_value = "Documents (PDF, TXT, MD)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = False  # Not clicked

    mock_col1, mock_col2 = MagicMock(), MagicMock()
    mock_st.columns.return_value = [mock_col1, mock_col2]

    render_upload_section(mock_supabase, mock_embedding_client)

    # Upload should not be triggered
    mock_asyncio_run.assert_not_called()


@patch("src.ui.features.upload_handler.st")
@patch("src.ui.features.upload_handler.asyncio.run")
@patch("src.ui.features.upload_handler.nest_asyncio")
def test_render_upload_section_nest_asyncio_exception(
    mock_nest_asyncio, mock_asyncio_run, mock_st, mock_supabase, mock_embedding_client
):
    """Test handling of nest_asyncio.apply() exception."""
    from src.ui.features.upload_handler import render_upload_section

    mock_file = MagicMock()
    mock_file.name = "test.txt"
    mock_file.type = "text/plain"
    mock_file.size = 1024

    mock_st.selectbox.return_value = "Documents (PDF, TXT, MD)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = True

    # Mock nest_asyncio raising exception (should be suppressed)
    mock_nest_asyncio.apply.side_effect = Exception("Nest asyncio error")

    mock_asyncio_run.return_value = {
        "success": True,
        "message": "Upload successful",
    }

    mock_col1, mock_col2 = MagicMock(), MagicMock()
    mock_st.columns.return_value = [mock_col1, mock_col2]

    mock_spinner = MagicMock()
    mock_spinner.__enter__ = MagicMock()
    mock_spinner.__exit__ = MagicMock()
    mock_st.spinner.return_value = mock_spinner

    # Should not raise exception
    render_upload_section(mock_supabase, mock_embedding_client)

    # Upload should still proceed
    mock_asyncio_run.assert_called_once()


@patch("src.ui.features.upload_handler.st")
def test_render_upload_section_file_size_display(mock_st, mock_supabase, mock_embedding_client):
    """Test file size is displayed correctly."""
    from src.ui.features.upload_handler import render_upload_section

    mock_file = MagicMock()
    mock_file.name = "large_file.txt"
    mock_file.type = "text/plain"
    mock_file.size = 10240  # 10KB

    mock_st.selectbox.return_value = "Documents (PDF, TXT, MD)"
    mock_st.file_uploader.return_value = mock_file
    mock_st.button.return_value = False

    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = [mock_col1, mock_col2]

    render_upload_section(mock_supabase, mock_embedding_client)

    # Verify file info is displayed
    mock_col1.caption.assert_called_once()
    caption_text = mock_col1.caption.call_args[0][0]
    assert "large_file.txt" in caption_text
    assert "KB" in caption_text


# ============================================================================
# Additional Edge Cases
# ============================================================================


@pytest.mark.asyncio
@patch("src.ui.features.upload_handler.generate_embeddings")
@patch("src.ui.features.upload_handler.semantic_chunk")
async def test_process_document_upload_with_non_utf8(
    mock_chunk, mock_embeddings, mock_supabase, mock_embedding_client
):
    """Test document upload with non-UTF-8 encoding."""
    from src.ui.features.upload_handler import process_document_upload

    file = MagicMock()
    file.name = "latin1.txt"
    file.type = "text/plain"
    file.size = 100

    # Create bytes that will fail UTF-8 decoding
    "Café résumé".encode("latin-1")
    mock_read_result = MagicMock()
    mock_read_result.decode.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "error")
    file.read.return_value = mock_read_result

    result = await process_document_upload(file, mock_supabase, mock_embedding_client)

    assert result["success"] is False


@pytest.mark.asyncio
async def test_process_tabular_upload_xls_file(mock_supabase):
    """Test uploading .xls file (older Excel format)."""
    import io

    import pandas as pd

    from src.ui.features.upload_handler import process_tabular_upload

    file = MagicMock()
    file.name = "data.xls"
    file.type = "application/vnd.ms-excel"
    file.size = 2048

    # Create XLS content
    df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    file.read.return_value = buffer.read()

    result = await process_tabular_upload(file, mock_supabase)

    assert result["success"] is True
    assert result["rows"] == 2


@pytest.mark.asyncio
async def test_process_image_upload_webp(mock_supabase):
    """Test uploading WebP image."""
    from src.ui.features.upload_handler import process_image_upload

    file = MagicMock()
    file.name = "image.webp"
    file.type = "image/webp"
    file.size = 3072
    file.read.return_value = b"RIFF" + b"\x00" * 100

    result = await process_image_upload(file, mock_supabase)

    assert result["success"] is True
    assert "image.webp" in result["message"]
