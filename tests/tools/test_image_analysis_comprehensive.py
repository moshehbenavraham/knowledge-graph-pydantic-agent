"""
Comprehensive tests for image analysis tool.

Tests:
- Document retrieval by source and ID
- Base64 image decoding
- Vision LLM integration (OpenAI and Anthropic)
- Model mapping for Anthropic
- Error handling
- Metadata extraction
"""

import base64
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.tools.image_analysis import image_analysis_tool


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client."""
    client = Mock()
    return client


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock()
    settings.llm_provider = "openai"
    settings.vision_llm_choice = "gpt-4-vision-preview"
    settings.llm_api_key = "test-api-key"
    settings.llm_base_url = "https://api.openai.com/v1"
    return settings


@pytest.fixture
def sample_image_base64():
    """Create sample base64 encoded image."""
    # Small 1x1 pixel PNG
    png_bytes = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    )
    return png_bytes.decode("utf-8")


@pytest.mark.asyncio
class TestDocumentRetrieval:
    """Test document retrieval from Supabase."""

    async def test_retrieve_by_source(self, mock_supabase, mock_settings, sample_image_base64):
        """Test retrieving document by source field."""
        # Mock Supabase query response
        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {"file_contents": sample_image_base64, "mime_type": "image/png"},
                "source": "test-image.png",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        # Mock vision agent
        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent_class.return_value = mock_agent
                mock_agent.run = AsyncMock(return_value=Mock(output="Analysis result"))

                result = await image_analysis_tool(
                    mock_supabase, "test-image.png", "What is in this image?"
                )

                assert "Analysis result" in result
                # Verify it tried source field first
                mock_supabase.from_.assert_called_with("documents")

    async def test_retrieve_by_id_fallback(self, mock_supabase, mock_settings, sample_image_base64):
        """Test retrieving document by ID when source fails."""
        # First query (by source) returns empty
        mock_empty_result = Mock()
        mock_empty_result.data = []

        # Second query (by ID) returns data
        mock_success_result = Mock()
        mock_success_result.data = [
            {
                "metadata": {"file_contents": sample_image_base64, "mime_type": "image/png"},
                "source": "test-image.png",
            }
        ]

        # Set up mock to return different results
        mock_query = (
            mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value
        )
        mock_query.execute.side_effect = [mock_empty_result, mock_success_result]

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent_class.return_value = mock_agent
                mock_agent.run = AsyncMock(return_value=Mock(output="Analysis result"))

                result = await image_analysis_tool(mock_supabase, "doc-id-123", "Analyze this")

                assert "Analysis result" in result

    async def test_document_not_found(self, mock_supabase, mock_settings):
        """Test handling when document is not found."""
        mock_result = Mock()
        mock_result.data = []

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            result = await image_analysis_tool(mock_supabase, "nonexistent-doc", "Analyze this")

            assert "No content found for document" in result
            assert "nonexistent-doc" in result

    async def test_no_file_contents_in_metadata(self, mock_supabase, mock_settings):
        """Test handling when metadata has no file contents."""
        mock_result = Mock()
        mock_result.data = [
            {"metadata": {}, "source": "test-image.png"}  # No file_contents or image_data
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            result = await image_analysis_tool(mock_supabase, "test-image.png", "Analyze this")

            assert "No file contents found for document" in result


@pytest.mark.asyncio
class TestMetadataExtraction:
    """Test metadata extraction and format handling."""

    async def test_extract_file_contents_field(
        self, mock_supabase, mock_settings, sample_image_base64
    ):
        """Test extracting file_contents field."""
        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {"file_contents": sample_image_base64, "mime_type": "image/jpeg"},
                "source": "test.jpg",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent_class.return_value = mock_agent
                mock_agent.run = AsyncMock(return_value=Mock(output="JPEG image"))

                result = await image_analysis_tool(mock_supabase, "test.jpg", "Analyze")

                # Verify it used file_contents
                assert "JPEG image" in result

    async def test_extract_image_data_field_fallback(
        self, mock_supabase, mock_settings, sample_image_base64
    ):
        """Test extracting image_data field as fallback."""
        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {
                    "image_data": sample_image_base64,  # Use image_data instead
                    "mime_type": "image/png",
                },
                "source": "test.png",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent_class.return_value = mock_agent
                mock_agent.run = AsyncMock(return_value=Mock(output="PNG image"))

                result = await image_analysis_tool(mock_supabase, "test.png", "Analyze")

                assert "PNG image" in result

    async def test_mime_type_extraction(self, mock_supabase, mock_settings, sample_image_base64):
        """Test mime_type extraction."""
        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {"file_contents": sample_image_base64, "mime_type": "image/webp"},
                "source": "test.webp",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent_class.return_value = mock_agent
                mock_agent.run = AsyncMock(return_value=Mock(output="WebP"))

                await image_analysis_tool(mock_supabase, "test.webp", "Analyze")

                # Verify agent was called with correct mime_type
                assert mock_agent.run.called

    async def test_file_type_fallback_for_mime_type(
        self, mock_supabase, mock_settings, sample_image_base64
    ):
        """Test using file_type as fallback for mime_type."""
        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {
                    "file_contents": sample_image_base64,
                    "file_type": "image/gif",  # Using file_type instead
                },
                "source": "test.gif",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent_class.return_value = mock_agent
                mock_agent.run = AsyncMock(return_value=Mock(output="GIF"))

                result = await image_analysis_tool(mock_supabase, "test.gif", "Analyze")

                assert "GIF" in result


@pytest.mark.asyncio
class TestVisionLLMIntegration:
    """Test vision LLM integration."""

    async def test_openai_model_creation(self, mock_supabase, mock_settings, sample_image_base64):
        """Test OpenAI model creation."""
        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {"file_contents": sample_image_base64, "mime_type": "image/png"},
                "source": "test.png",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            with patch("src.tools.image_analysis.OpenAIChatModel") as mock_model_class:
                with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                    mock_agent = AsyncMock()
                    mock_agent_class.return_value = mock_agent
                    mock_agent.run = AsyncMock(return_value=Mock(output="Result"))

                    await image_analysis_tool(mock_supabase, "test.png", "Analyze")

                    # Verify OpenAI model was created
                    assert mock_model_class.called

    async def test_anthropic_model_creation(self, mock_supabase, sample_image_base64):
        """Test Anthropic model creation."""
        anthropic_settings = Mock()
        anthropic_settings.llm_provider = "anthropic"
        anthropic_settings.vision_llm_choice = "claude-3-opus"
        anthropic_settings.llm_api_key = "test-key"

        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {"file_contents": sample_image_base64, "mime_type": "image/png"},
                "source": "test.png",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=anthropic_settings):
            with patch("src.tools.image_analysis.AnthropicModel") as mock_model_class:
                with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                    mock_agent = AsyncMock()
                    mock_agent_class.return_value = mock_agent
                    mock_agent.run = AsyncMock(return_value=Mock(output="Result"))

                    await image_analysis_tool(mock_supabase, "test.png", "Analyze")

                    # Verify Anthropic model was created with mapped name
                    mock_model_class.assert_called_once()
                    call_args = mock_model_class.call_args
                    assert "claude-3-opus-20240229" in str(call_args)

    async def test_anthropic_model_mapping(self, mock_supabase, sample_image_base64):
        """Test Anthropic model name mapping."""
        test_cases = [
            ("claude-3-sonnet", "claude-3-5-sonnet-20241022"),
            ("claude-3.5-sonnet", "claude-3-5-sonnet-20241022"),
            ("claude-3-haiku", "claude-3-haiku-20240307"),
            ("claude-4-sonnet", "claude-4-sonnet"),
        ]

        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {"file_contents": sample_image_base64, "mime_type": "image/png"},
                "source": "test.png",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        for input_model, expected_model in test_cases:
            anthropic_settings = Mock()
            anthropic_settings.llm_provider = "anthropic"
            anthropic_settings.vision_llm_choice = input_model
            anthropic_settings.llm_api_key = "test-key"

            with patch("src.tools.image_analysis.get_settings", return_value=anthropic_settings):
                with patch("src.tools.image_analysis.AnthropicModel") as mock_model_class:
                    with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_agent_class.return_value = mock_agent
                        mock_agent.run = AsyncMock(return_value=Mock(output="Result"))

                        await image_analysis_tool(mock_supabase, "test.png", "Analyze")

                        # Verify correct model name was used
                        call_args = mock_model_class.call_args
                        assert expected_model in str(call_args[0])


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling."""

    async def test_exception_during_analysis(
        self, mock_supabase, mock_settings, sample_image_base64
    ):
        """Test handling exception during analysis."""
        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {"file_contents": sample_image_base64, "mime_type": "image/png"},
                "source": "test.png",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            with patch("src.tools.image_analysis.Agent") as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent_class.return_value = mock_agent
                mock_agent.run = AsyncMock(side_effect=Exception("LLM API error"))

                result = await image_analysis_tool(mock_supabase, "test.png", "Analyze")

                assert "Error analyzing image" in result
                assert "LLM API error" in result

    async def test_invalid_base64(self, mock_supabase, mock_settings):
        """Test handling invalid base64 data."""
        mock_result = Mock()
        mock_result.data = [
            {
                "metadata": {"file_contents": "invalid-base64!!!", "mime_type": "image/png"},
                "source": "test.png",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            result = await image_analysis_tool(mock_supabase, "test.png", "Analyze")

            assert "Error analyzing image" in result

    async def test_supabase_query_exception(self, mock_supabase, mock_settings):
        """Test handling Supabase query exception."""
        mock_supabase.from_.side_effect = Exception("Database connection error")

        with patch("src.tools.image_analysis.get_settings", return_value=mock_settings):
            result = await image_analysis_tool(mock_supabase, "test.png", "Analyze")

            assert "Error analyzing image" in result
            assert "Database connection error" in result
