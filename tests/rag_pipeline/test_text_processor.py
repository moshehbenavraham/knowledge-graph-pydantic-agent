import pytest
import os
import sys
import json
import io
import csv
from unittest.mock import patch, MagicMock, AsyncMock, call

# Mock environment variables before importing modules that use them
with patch.dict(os.environ, {
    'EMBEDDING_API_KEY': 'test-embedding-key',
    'EMBEDDING_BASE_URL': 'https://test-openai.com/v1',
    'EMBEDDING_MODEL_CHOICE': 'text-embedding-3-small',
}):
    # Add src directory to path to import the module
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))
    from rag_pipeline.common.text_processor import (
        chunk_text,
        extract_text_from_pdf,
        extract_text_from_file,
        create_embeddings,
        is_tabular_file,
        extract_schema_from_csv,
        extract_rows_from_csv,
        openai_client # Import the initialized openai_client
    )
    import pypdf


class TestTextProcessor:
    @pytest.fixture(autouse=True)
    def mock_openai_client(self):
        # This fixture will run before each test in this class
        # and ensure the global openai_client is mocked
        with patch('rag_pipeline.common.text_processor.OpenAI') as mock_openai:
            mock_openai_instance = MagicMock()
            mock_openai.return_value = mock_openai_instance
            yield mock_openai_instance

    def test_chunk_text(self):
        text = "This is a long text that needs to be chunked for processing."
        
        # Test basic chunking
        chunks = chunk_text(text, chunk_size=10, overlap=0)
        assert chunks == ["This is a ", "long text ", "that needs", " to be ch", "unked for ", "processin", "g."]
        
        # Test with overlap
        chunks_overlap = chunk_text(text, chunk_size=10, overlap=3)
        assert chunks_overlap == ["This is a ", "s a long t", "ong text ", "ext that n", "hat needs ", "needs to b", "s to be ch", "be chunked", "unked for ", "d for proc", "r process", "ocessing.", "ssing."]
        
        # Test empty text
        assert chunk_text("") == []
        
        # Test text shorter than chunk size
        assert chunk_text("short", chunk_size=10) == ["short"]

    @patch('rag_pipeline.common.text_processor.tempfile.NamedTemporaryFile')
    @patch('rag_pipeline.common.text_processor.os.remove')
    @patch('rag_pipeline.common.text_processor.pypdf.PdfReader')
    def test_extract_text_from_pdf(self, mock_pdf_reader, mock_os_remove, mock_tempfile):
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/test.pdf"
        mock_temp_file.__enter__.return_value = mock_temp_file
        mock_temp_file.write.return_value = None
        mock_temp_file.__exit__.return_value = None
        mock_tempfile.return_value = mock_temp_file
        
        mock_reader_instance = MagicMock()
        mock_pdf_reader.return_value = mock_reader_instance
        
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content."
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content."
        mock_reader_instance.pages = [mock_page1, mock_page2]
        
        file_content = b"pdf_binary_data"
        result = extract_text_from_pdf(file_content)
        
        mock_temp_file.write.assert_called_once_with(file_content)
        mock_pdf_reader.assert_called_once_with(ANY) # Check that it's called with a file-like object
        assert "Page 1 content." in result
        assert "Page 2 content." in result
        mock_os_remove.assert_called_once_with("/tmp/test.pdf")

    def test_extract_text_from_file_pdf(self):
        file_content = b"pdf_binary_data"
        mime_type = "application/pdf"
        config = {"supported_mime_types": ["application/pdf"]}
        
        with patch('rag_pipeline.common.text_processor.extract_text_from_pdf') as mock_extract_pdf:
            mock_extract_pdf.return_value = "Extracted PDF text"
            result = extract_text_from_file(file_content, mime_type, "test.pdf", config)
            mock_extract_pdf.assert_called_once_with(file_content)
            assert result == "Extracted PDF text"

    def test_extract_text_from_file_image(self):
        file_content = b"image_binary_data"
        mime_type = "image/jpeg"
        file_name = "my_image.jpg"
        config = {"supported_mime_types": ["image/jpeg"]}
        
        result = extract_text_from_file(file_content, mime_type, file_name, config)
        assert result == file_name # For images, it returns the file name

    def test_extract_text_from_file_text(self):
        file_content = b"plain text content"
        mime_type = "text/plain"
        config = {"supported_mime_types": ["text/plain"]}
        
        result = extract_text_from_file(file_content, mime_type, "test.txt", config)
        assert result == "plain text content"

    def test_extract_text_from_file_unsupported(self):
        file_content = b"unsupported binary data"
        mime_type = "application/octet-stream"
        config = {"supported_mime_types": []}
        
        result = extract_text_from_file(file_content, mime_type, "test.bin", config)
        assert result == "unsupported binary data" # Decodes as utf-8 with errors replaced

    def test_create_embeddings(self, mock_openai_client):
        texts = ["text1", "text2"]
        
        mock_embeddings_response = MagicMock()
        mock_embeddings_response.data = [
            MagicMock(embedding=[0.1, 0.2]),
            MagicMock(embedding=[0.3, 0.4])
        ]
        mock_openai_client.embeddings.create.return_value = mock_embeddings_response
        
        result = create_embeddings(texts)
        
        mock_openai_client.embeddings.create.assert_called_once_with(
            model='text-embedding-3-small', # From mocked env var
            input=texts
        )
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_create_embeddings_empty_texts(self):
        assert create_embeddings([]) == []

    def test_is_tabular_file(self):
        config = {"tabular_mime_types": ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]}
        
        assert is_tabular_file("text/csv", config) is True
        assert is_tabular_file("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", config) is True
        assert is_tabular_file("application/pdf", config) is False
        assert is_tabular_file("image/jpeg", config) is False
        
        # Test with default config
        assert is_tabular_file("text/csv") is True
        assert is_tabular_file("application/pdf") is False

    def test_extract_schema_from_csv(self):
        csv_content = b"header1,header2,header3\nval1,val2,val3"
        result = extract_schema_from_csv(csv_content)
        assert result == ["header1", "header2", "header3"]

    def test_extract_schema_from_csv_empty(self):
        csv_content = b""
        result = extract_schema_from_csv(csv_content)
        assert result == []

    def test_extract_rows_from_csv(self):
        csv_content = b"col1,col2\nvalA,1\nvalB,2"
        result = extract_rows_from_csv(csv_content)
        assert result == [{'col1': 'valA', 'col2': '1'}, {'col1': 'valB', 'col2': '2'}]

    def test_extract_rows_from_csv_empty(self):
        csv_content = b""
        result = extract_rows_from_csv(csv_content)
        assert result == []
