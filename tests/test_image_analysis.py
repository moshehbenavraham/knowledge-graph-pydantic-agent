import base64
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock environment variables before importing modules that use them
with patch.dict(
    os.environ,
    {
        "LLM_PROVIDER": "openai",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_API_KEY": "test-api-key",
        "LLM_CHOICE": "gpt-4o-mini",
        "VISION_LLM_CHOICE": "gpt-4o-mini",
        "SUPABASE_URL": "https://test-supabase-url.com",
        "SUPABASE_SERVICE_KEY": "test-supabase-key",
    },
):
    # Add src directory to path to import the tools module
    sys.path.append(str(Path(__file__).parent.parent.resolve() / "src"))

    from tools.image_analysis import image_analysis_tool


class TestImageAnalysisTool:
    @pytest.mark.asyncio
    @patch("tools.image_analysis.OpenAIModel")
    @patch("tools.image_analysis.OpenAIProvider")
    @patch("tools.image_analysis.Agent")
    @patch("tools.image_analysis.os.getenv")
    async def test_image_analysis_tool_success(
        self, mock_getenv, mock_agent_class, mock_provider_class, mock_model_class
    ):
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            "VISION_LLM_CHOICE": "gpt-4o-mini",
            "LLM_BASE_URL": "https://api.openai.com/v1",
            "LLM_API_KEY": "test-api-key",
        }.get(key, default)

        # Mock OpenAI provider, model and agent
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider

        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Create a mock agent with a proper async mock for run
        mock_agent = MagicMock()
        # We need to track if run was called and with what arguments
        run_called = False
        run_args = None

        async def mock_run(*args, **kwargs):
            nonlocal run_called, run_args
            run_called = True
            run_args = args
            mock_result = MagicMock()
            mock_result.data = "Image analysis result"
            return mock_result

        mock_agent.run = mock_run
        mock_agent_class.return_value = mock_agent

        # Mock Supabase client and response
        mock_supabase = MagicMock()
        mock_from = MagicMock()
        mock_supabase.from_.return_value = mock_from
        mock_select = MagicMock()
        mock_from.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_limit = MagicMock()
        mock_eq.limit.return_value = mock_limit
        mock_execute = MagicMock()
        mock_limit.execute.return_value = mock_execute

        # Setup mock document data with base64 image
        test_binary = base64.b64encode(b"test image data").decode("utf-8")
        mock_execute.data = [
            {
                "metadata": {
                    "file_id": "img1",
                    "file_contents": test_binary,
                    "mime_type": "image/jpeg",
                }
            }
        ]

        # Test the function
        result = await image_analysis_tool(mock_supabase, "img1", "Describe this image")

        # Verify Supabase query was called correctly
        mock_supabase.from_.assert_called_once_with("documents")
        mock_from.select.assert_called_once_with("metadata")
        mock_select.eq.assert_called_once_with("metadata->>file_id", "img1")
        mock_eq.limit.assert_called_once_with(1)

        # Verify agent setup and run
        mock_provider_class.assert_called_once_with(
            base_url="https://api.openai.com/v1", api_key="test-api-key"
        )
        mock_model_class.assert_called_once_with("gpt-4o-mini", provider=mock_provider)
        mock_agent_class.assert_called_once()

        # Verify the agent run method was called
        assert run_called, "Agent run method was not called"
        # Verify the arguments were correct
        assert run_args is not None, "Agent run was called without arguments"
        assert (
            run_args[0][0] == "Describe this image"
        ), f"Expected 'Describe this image', got {run_args[0][0]}"
        # Check that the second argument is a BinaryContent object
        assert hasattr(run_args[0][1], "data"), "Second argument is missing 'data' attribute"
        assert hasattr(
            run_args[0][1], "media_type"
        ), "Second argument is missing 'media_type' attribute"

        # Verify the result
        assert result == "Image analysis result"

    @pytest.mark.asyncio
    async def test_image_analysis_tool_no_document(self):
        # Mock Supabase client with no results
        mock_supabase = MagicMock()
        mock_from = MagicMock()
        mock_supabase.from_.return_value = mock_from
        mock_select = MagicMock()
        mock_from.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_limit = MagicMock()
        mock_eq.limit.return_value = mock_limit
        mock_execute = MagicMock()
        mock_limit.execute.return_value = mock_execute
        mock_execute.data = []

        # Test the function
        result = await image_analysis_tool(mock_supabase, "img1", "Describe this image")

        # Verify the result for no document
        assert result == "No content found for document: img1"

    @pytest.mark.asyncio
    async def test_image_analysis_tool_no_file_contents(self):
        # Mock Supabase client with document but no file contents
        mock_supabase = MagicMock()
        mock_from = MagicMock()
        mock_supabase.from_.return_value = mock_from
        mock_select = MagicMock()
        mock_from.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_limit = MagicMock()
        mock_eq.limit.return_value = mock_limit
        mock_execute = MagicMock()
        mock_limit.execute.return_value = mock_execute

        # Document with empty file contents
        mock_execute.data = [
            {"metadata": {"file_id": "img1", "file_contents": "", "mime_type": "image/jpeg"}}
        ]

        # Test the function
        result = await image_analysis_tool(mock_supabase, "img1", "Describe this image")

        # Verify the result for no file contents
        assert result == "No file contents found for document: img1"

    @pytest.mark.asyncio
    async def test_image_analysis_tool_exception(self):
        # Mock Supabase client that raises an exception
        mock_supabase = MagicMock()
        mock_supabase.from_.side_effect = Exception("Test exception")

        # Test the function
        with patch("builtins.print") as mock_print:
            result = await image_analysis_tool(mock_supabase, "img1", "Describe this image")

        # Verify the exception was handled
        mock_print.assert_called_once_with("Error analyzing image: Test exception")
        assert "Error analyzing image: Test exception" in result
