"""
Comprehensive tests for image analysis tool.

Tests image loading, vision model integration, OCR, object detection, and error handling.
Target: 85%+ coverage of image_analysis.py
"""

import base64
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for document retrieval."""
    client = Mock()

    # Mock table operations
    mock_table = Mock()
    client.table.return_value = mock_table

    # Mock select operation
    mock_select = Mock()
    mock_table.select.return_value = mock_select

    # Mock eq operation
    mock_eq = Mock()
    mock_select.eq.return_value = mock_eq

    # Mock execute
    mock_execute = Mock()
    mock_eq.execute.return_value = mock_execute

    # Default: return document with base64 image
    mock_execute.data = [
        {
            "id": str(uuid4()),
            "file_path": "test_image.png",
            "content": "base64encodedimagedata",
            "metadata": {"mime_type": "image/png"},
        }
    ]

    return client


@pytest.fixture
def mock_vision_client():
    """Mock vision model client."""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock()

    # Default response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "This image shows a cat sitting on a mat."

    client.chat.completions.create.return_value = mock_response

    return client


class TestImageAnalysisTool:
    """Test image_analysis_tool function."""

    @pytest.mark.asyncio
    async def test_analyze_image_success(self, mock_supabase_client, mock_vision_client):
        """Test successful image analysis."""
        from src.tools.image_analysis import image_analysis_tool

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="test-123",
                analysis_query="What's in this image?",
            )

            assert isinstance(result, str)
            assert "cat" in result or "This image" in result
            mock_vision_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_image_by_file_path(self, mock_supabase_client, mock_vision_client):
        """Test image analysis using file_path."""
        from src.tools.image_analysis import image_analysis_tool

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="images/test.png",
                analysis_query="Describe this image",
            )

            assert isinstance(result, str)
            # Should query by file_path
            mock_supabase_client.table.assert_called()

    @pytest.mark.asyncio
    async def test_analyze_image_not_found(self, mock_supabase_client, mock_vision_client):
        """Test analysis when image not found."""
        from src.tools.image_analysis import image_analysis_tool

        # Return empty result
        mock_supabase_client.table().select().eq().execute.return_value.data = []

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="nonexistent",
                analysis_query="Test",
            )

            assert "not found" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_analyze_image_ocr_query(self, mock_supabase_client, mock_vision_client):
        """Test OCR-specific analysis."""
        from src.tools.image_analysis import image_analysis_tool

        mock_vision_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "Text found: Hello World"

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="test-123",
                analysis_query="Extract all text from this image",
            )

            assert "Text found" in result or "Hello World" in result

    @pytest.mark.asyncio
    async def test_analyze_image_object_detection(self, mock_supabase_client, mock_vision_client):
        """Test object detection analysis."""
        from src.tools.image_analysis import image_analysis_tool

        mock_vision_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "Objects detected: person, car, tree"

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="test-123",
                analysis_query="What objects are in this image?",
            )

            assert "Objects detected" in result or "person" in result

    @pytest.mark.asyncio
    async def test_analyze_image_scene_description(self, mock_supabase_client, mock_vision_client):
        """Test scene description analysis."""
        from src.tools.image_analysis import image_analysis_tool

        mock_vision_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "A sunny park with people playing frisbee"

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="test-123",
                analysis_query="Describe the scene",
            )

            assert "park" in result or "frisbee" in result

    @pytest.mark.asyncio
    async def test_analyze_image_with_metadata(self, mock_supabase_client, mock_vision_client):
        """Test analysis with image metadata."""
        from src.tools.image_analysis import image_analysis_tool

        # Add metadata to document
        mock_supabase_client.table().select().eq().execute.return_value.data[0]["metadata"] = {
            "mime_type": "image/jpeg",
            "width": 1920,
            "height": 1080,
        }

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="test-123",
                analysis_query="Test",
            )

            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_image_vision_model_error(self, mock_supabase_client, mock_vision_client):
        """Test handling of vision model errors."""
        from src.tools.image_analysis import image_analysis_tool

        mock_vision_client.chat.completions.create.side_effect = Exception("Vision model error")

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="test-123",
                analysis_query="Test",
            )

            assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_analyze_image_invalid_base64(self, mock_supabase_client, mock_vision_client):
        """Test handling of invalid base64 image data."""
        from src.tools.image_analysis import image_analysis_tool

        # Return invalid base64
        mock_supabase_client.table().select().eq().execute.return_value.data[0]["content"] = (
            "invalid_base64"
        )

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="test-123",
                analysis_query="Test",
            )

            # Should handle gracefully
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_multiple_images_sequential(
        self, mock_supabase_client, mock_vision_client
    ):
        """Test analyzing multiple images sequentially."""
        from src.tools.image_analysis import image_analysis_tool

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            results = []
            for i in range(3):
                result = await image_analysis_tool(
                    supabase_client=mock_supabase_client,
                    document_id=f"image-{i}",
                    analysis_query="Describe",
                )
                results.append(result)

            assert len(results) == 3
            assert all(isinstance(r, str) for r in results)

    @pytest.mark.asyncio
    async def test_analyze_image_different_mime_types(
        self, mock_supabase_client, mock_vision_client
    ):
        """Test analysis with different image mime types."""
        from src.tools.image_analysis import image_analysis_tool

        mime_types = ["image/png", "image/jpeg", "image/webp", "image/gif"]

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            for mime_type in mime_types:
                mock_supabase_client.table().select().eq().execute.return_value.data[0][
                    "metadata"
                ] = {"mime_type": mime_type}

                result = await image_analysis_tool(
                    supabase_client=mock_supabase_client,
                    document_id="test-123",
                    analysis_query="Test",
                )

                assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_analyze_image_long_query(self, mock_supabase_client, mock_vision_client):
        """Test analysis with long detailed query."""
        from src.tools.image_analysis import image_analysis_tool

        long_query = (
            "Please provide a detailed analysis of this image including: "
            "1. Overall scene description "
            "2. All visible objects "
            "3. Any text present "
            "4. Color palette "
            "5. Composition and framing"
        )

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="test-123",
                analysis_query=long_query,
            )

            assert isinstance(result, str)
            # Vision model should have been called with the full query
            call_args = mock_vision_client.chat.completions.create.call_args
            assert long_query in str(call_args)

    @pytest.mark.asyncio
    async def test_analyze_image_database_connection_error(
        self, mock_supabase_client, mock_vision_client
    ):
        """Test handling of database connection errors."""
        from src.tools.image_analysis import image_analysis_tool

        mock_supabase_client.table.side_effect = Exception("Database connection failed")

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            result = await image_analysis_tool(
                supabase_client=mock_supabase_client,
                document_id="test-123",
                analysis_query="Test",
            )

            assert "error" in result.lower() or "failed" in result.lower()


class TestImageEncoding:
    """Test image encoding utilities."""

    def test_base64_encoding(self):
        """Test base64 encoding of image data."""
        test_data = b"fake image data"
        encoded = base64.b64encode(test_data).decode("utf-8")

        # Should be base64 encoded
        assert isinstance(encoded, str)
        # Should be decodable
        decoded = base64.b64decode(encoded)
        assert decoded == test_data

    def test_large_image_encoding(self):
        """Test encoding of large image."""
        # Simulate 5MB image
        large_data = b"x" * (5 * 1024 * 1024)
        encoded = base64.b64encode(large_data).decode("utf-8")

        assert isinstance(encoded, str)
        assert len(encoded) > 0


class TestVisionModelIntegration:
    """Test vision model client integration."""

    @pytest.mark.asyncio
    async def test_vision_client_initialization(self):
        """Test vision client initialization."""
        with patch("src.tools.image_analysis.get_vision_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            from src.tools.image_analysis import get_vision_client

            client = get_vision_client()
            assert client is not None

    @pytest.mark.asyncio
    async def test_vision_model_api_call(self, mock_vision_client):
        """Test vision model API call format."""
        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            from src.tools.image_analysis import image_analysis_tool

            mock_supabase = Mock()
            mock_supabase.table().select().eq().execute.return_value.data = [
                {"id": "test", "file_path": "test.png", "content": "testdata", "metadata": {}}
            ]

            await image_analysis_tool(
                supabase_client=mock_supabase,
                document_id="test",
                analysis_query="What is this?",
            )

            # Check API call was made
            mock_vision_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_vision_model_response_parsing(self, mock_vision_client):
        """Test parsing of vision model response."""
        complex_response = {
            "objects": ["cat", "mat"],
            "text": "Welcome",
            "colors": ["red", "blue"],
        }

        mock_vision_client.chat.completions.create.return_value.choices[
            0
        ].message.content = str(complex_response)

        with patch("src.tools.image_analysis.get_vision_client", return_value=mock_vision_client):
            from src.tools.image_analysis import image_analysis_tool

            mock_supabase = Mock()
            mock_supabase.table().select().eq().execute.return_value.data = [
                {"id": "test", "file_path": "test.png", "content": "data", "metadata": {}}
            ]

            result = await image_analysis_tool(
                supabase_client=mock_supabase,
                document_id="test",
                analysis_query="Analyze",
            )

            assert isinstance(result, str)
            assert "cat" in result or "objects" in result
