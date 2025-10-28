"""
Comprehensive tests for MCPHandler - MCP-enabled streaming with memory.

Covers:
- MCP context management (open/close)
- MCP enabled/disabled modes
- Delegation to MemoryHandler
- Streaming with MCP context
- Error handling in MCP context
- Chunk counting and logging
- Integration with super_agent
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

from src.ui.features.mcp_handler import MCPHandler

# ===== Fixtures =====


@pytest.fixture
def mock_config():
    """Mock UI configuration."""
    return {
        "mode": "advanced",
        "features": {
            "streaming": True,
            "memory": True,
            "mcp": True,
        },
        "enable_mcp": True,
        "enable_memory": True,
    }


@pytest.fixture
def mock_config_mcp_disabled():
    """Mock UI configuration with MCP disabled."""
    return {
        "mode": "advanced",
        "features": {
            "streaming": True,
            "memory": True,
            "mcp": False,
        },
        "enable_mcp": False,
        "enable_memory": True,
    }


@pytest.fixture
def mcp_handler(mock_config):
    """Create MCPHandler instance."""
    return MCPHandler(mock_config)


@pytest.fixture
def mcp_handler_disabled(mock_config_mcp_disabled):
    """Create MCPHandler instance with MCP disabled."""
    return MCPHandler(mock_config_mcp_disabled)


@pytest.fixture
def mock_http_client():
    """Mock AsyncClient."""
    return AsyncMock(spec=AsyncClient)


@pytest.fixture
def sample_message_history():
    """Sample message history."""
    return [
        ModelRequest(parts=["Hello"]),
        ModelResponse(parts=["Hi there!"]),
    ]


# ===== Initialization Tests =====


class TestMCPHandlerInit:
    """Test MCPHandler initialization."""

    def test_init_with_mcp_enabled(self, mock_config):
        """Test initialization with MCP enabled."""
        handler = MCPHandler(mock_config)

        assert handler.enable_mcp is True
        assert hasattr(handler, "memory_client")  # Inherited from MemoryHandler
        assert hasattr(handler, "user_id")  # Inherited from MemoryHandler

    def test_init_with_mcp_disabled(self, mock_config_mcp_disabled):
        """Test initialization with MCP disabled."""
        handler = MCPHandler(mock_config_mcp_disabled)

        assert handler.enable_mcp is False

    def test_init_defaults_mcp_enabled(self):
        """Test that MCP defaults to enabled if not specified."""
        config = {"mode": "advanced"}
        handler = MCPHandler(config)

        # Should default to True
        assert handler.enable_mcp is True

    def test_init_inherits_from_memory_handler(self, mock_config):
        """Test that MCPHandler inherits from MemoryHandler."""
        handler = MCPHandler(mock_config)

        # Should have MemoryHandler attributes
        assert hasattr(handler, "run_agent")
        assert hasattr(handler, "memory_client")
        assert hasattr(handler, "user_id")

        # Check inheritance chain
        from src.ui.features.memory_handler import MemoryHandler

        assert isinstance(handler, MemoryHandler)


# ===== MCP Enabled Tests =====


@pytest.mark.asyncio
class TestMCPHandlerEnabled:
    """Test MCPHandler with MCP enabled."""

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_with_mcp_context(
        self, mock_super_agent, mcp_handler, mock_http_client, sample_message_history
    ):
        """Test that MCP context is opened when MCP is enabled."""
        # Mock the context manager
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        # Mock parent's run_agent to return some chunks
        async def mock_parent_run_agent(*args, **kwargs):
            yield {"type": "text_start"}
            yield {"type": "text_delta", "content": "Hello"}
            yield {"type": "complete"}

        with patch.object(
            MCPHandler.__bases__[0],  # MemoryHandler
            "run_agent",
            new=mock_parent_run_agent,
        ):
            chunks = []
            async for chunk in mcp_handler.run_agent(
                "test input", sample_message_history, mock_http_client
            ):
                chunks.append(chunk)

            # Verify chunks were yielded
            assert len(chunks) == 3
            assert chunks[0]["type"] == "text_start"
            assert chunks[1]["content"] == "Hello"

            # Verify MCP context was entered and exited
            mock_super_agent.__aenter__.assert_called_once()
            mock_super_agent.__aexit__.assert_called_once()

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_mcp_chunk_counting(
        self, mock_super_agent, mcp_handler, mock_http_client, sample_message_history
    ):
        """Test that chunks are counted in MCP mode."""
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        async def mock_parent_run_agent(*args, **kwargs):
            for i in range(10):
                yield {"type": "text_delta", "content": f"chunk_{i}"}

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            chunks = []
            async for chunk in mcp_handler.run_agent(
                "test input", sample_message_history, mock_http_client
            ):
                chunks.append(chunk)

            assert len(chunks) == 10

    @patch("src.ui.features.mcp_handler.super_agent")
    @patch("src.ui.features.mcp_handler.logger")
    async def test_run_agent_mcp_logging(
        self,
        mock_logger,
        mock_super_agent,
        mcp_handler,
        mock_http_client,
        sample_message_history,
    ):
        """Test that MCP-specific logging occurs."""
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        async def mock_parent_run_agent(*args, **kwargs):
            yield {"type": "complete"}

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            async for _ in mcp_handler.run_agent(
                "test input", sample_message_history, mock_http_client
            ):
                pass

            # Verify MCP-specific logging
            assert mock_logger.info.called
            # Check for MCP-specific log messages
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("MCP enabled" in str(call) for call in log_calls)

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_mcp_with_kwargs(
        self, mock_super_agent, mcp_handler, mock_http_client, sample_message_history
    ):
        """Test that kwargs are passed through in MCP mode."""
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        received_kwargs = {}

        async def mock_parent_run_agent(*args, **kwargs):
            received_kwargs.update(kwargs)
            yield {"type": "complete"}

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            async for _ in mcp_handler.run_agent(
                "test input",
                sample_message_history,
                mock_http_client,
                extra_param="test_value",
            ):
                pass

            assert received_kwargs.get("extra_param") == "test_value"


# ===== MCP Disabled Tests =====


@pytest.mark.asyncio
class TestMCPHandlerDisabled:
    """Test MCPHandler with MCP disabled."""

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_mcp_disabled_no_context(
        self,
        mock_super_agent,
        mcp_handler_disabled,
        mock_http_client,
        sample_message_history,
    ):
        """Test that MCP context is NOT opened when MCP is disabled."""

        async def mock_parent_run_agent(*args, **kwargs):
            yield {"type": "text_start"}
            yield {"type": "complete"}

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            chunks = []
            async for chunk in mcp_handler_disabled.run_agent(
                "test input", sample_message_history, mock_http_client
            ):
                chunks.append(chunk)

            # Verify chunks were yielded
            assert len(chunks) == 2

            # Verify MCP context was NOT used
            mock_super_agent.__aenter__.assert_not_called()
            mock_super_agent.__aexit__.assert_not_called()

    @patch("src.ui.features.mcp_handler.logger")
    async def test_run_agent_mcp_disabled_logging(
        self,
        mock_logger,
        mcp_handler_disabled,
        mock_http_client,
        sample_message_history,
    ):
        """Test logging when MCP is disabled."""

        async def mock_parent_run_agent(*args, **kwargs):
            yield {"type": "complete"}

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            async for _ in mcp_handler_disabled.run_agent(
                "test input", sample_message_history, mock_http_client
            ):
                pass

            # Verify disabled logging
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("MCP disabled" in str(call) for call in log_calls)

    async def test_run_agent_mcp_disabled_delegates_to_parent(
        self, mcp_handler_disabled, mock_http_client, sample_message_history
    ):
        """Test that run_agent delegates to parent when MCP is disabled."""
        expected_chunks = [
            {"type": "text_start"},
            {"type": "text_delta", "content": "Test"},
            {"type": "complete"},
        ]

        async def mock_parent_run_agent(*args, **kwargs):
            for chunk in expected_chunks:
                yield chunk

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            chunks = []
            async for chunk in mcp_handler_disabled.run_agent(
                "test input", sample_message_history, mock_http_client
            ):
                chunks.append(chunk)

            assert chunks == expected_chunks


# ===== Error Handling Tests =====


@pytest.mark.asyncio
class TestMCPHandlerErrors:
    """Test MCPHandler error handling."""

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_mcp_context_error(
        self, mock_super_agent, mcp_handler, mock_http_client, sample_message_history
    ):
        """Test error handling when MCP context fails."""
        # Make MCP context raise an error
        mock_super_agent.__aenter__ = AsyncMock(side_effect=RuntimeError("MCP context failed"))
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(RuntimeError, match="MCP context failed"):
            async for _ in mcp_handler.run_agent(
                "test input", sample_message_history, mock_http_client
            ):
                pass

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_parent_error_in_mcp_context(
        self, mock_super_agent, mcp_handler, mock_http_client, sample_message_history
    ):
        """Test error handling when parent raises error inside MCP context."""
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        async def mock_parent_run_agent(*args, **kwargs):
            yield {"type": "text_start"}
            raise ValueError("Parent error")

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            with pytest.raises(ValueError, match="Parent error"):
                async for _ in mcp_handler.run_agent(
                    "test input", sample_message_history, mock_http_client
                ):
                    pass

    @patch("src.ui.features.mcp_handler.super_agent")
    @patch("src.ui.features.mcp_handler.logger")
    async def test_run_agent_error_logging(
        self,
        mock_logger,
        mock_super_agent,
        mcp_handler,
        mock_http_client,
        sample_message_history,
    ):
        """Test that errors are logged with exception details."""
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        async def mock_parent_run_agent(*args, **kwargs):
            # Make this an async generator that raises an error
            if False:
                yield
            raise ConnectionError("Network failure")

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            with pytest.raises(ConnectionError):
                async for _ in mcp_handler.run_agent(
                    "test input", sample_message_history, mock_http_client
                ):
                    pass

            # Verify exception logging
            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args
            assert "FAILED" in str(call_args)


# ===== Integration Tests =====


@pytest.mark.asyncio
class TestMCPHandlerIntegration:
    """Test MCPHandler integration scenarios."""

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_empty_message_history(
        self, mock_super_agent, mcp_handler, mock_http_client
    ):
        """Test with empty message history."""
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        async def mock_parent_run_agent(*args, **kwargs):
            yield {"type": "complete"}

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            chunks = []
            async for chunk in mcp_handler.run_agent("test input", [], mock_http_client):
                chunks.append(chunk)

            assert len(chunks) == 1

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_long_input(
        self, mock_super_agent, mcp_handler, mock_http_client, sample_message_history
    ):
        """Test with very long user input."""
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        long_input = "x" * 10000

        async def mock_parent_run_agent(*args, **kwargs):
            yield {"type": "complete"}

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            chunks = []
            async for chunk in mcp_handler.run_agent(
                long_input, sample_message_history, mock_http_client
            ):
                chunks.append(chunk)

            assert len(chunks) == 1

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_many_chunks(
        self, mock_super_agent, mcp_handler, mock_http_client, sample_message_history
    ):
        """Test streaming many chunks through MCP context."""
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        async def mock_parent_run_agent(*args, **kwargs):
            for i in range(100):
                yield {"type": "text_delta", "content": f"chunk_{i}"}

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            chunks = []
            async for chunk in mcp_handler.run_agent(
                "test input", sample_message_history, mock_http_client
            ):
                chunks.append(chunk)

            assert len(chunks) == 100
            assert all(isinstance(chunk, dict) for chunk in chunks)

    @patch("src.ui.features.mcp_handler.super_agent")
    async def test_run_agent_context_cleanup_on_error(
        self, mock_super_agent, mcp_handler, mock_http_client, sample_message_history
    ):
        """Test that MCP context is properly cleaned up on error."""
        mock_context = AsyncMock()
        mock_super_agent.__aenter__ = AsyncMock(return_value=mock_context)
        mock_super_agent.__aexit__ = AsyncMock(return_value=None)

        async def mock_parent_run_agent(*args, **kwargs):
            yield {"type": "text_start"}
            raise RuntimeError("Streaming error")

        with patch.object(
            MCPHandler.__bases__[0],
            "run_agent",
            new=mock_parent_run_agent,
        ):
            with pytest.raises(RuntimeError):
                async for _ in mcp_handler.run_agent(
                    "test input", sample_message_history, mock_http_client
                ):
                    pass

            # Verify context exit was called despite error
            mock_super_agent.__aexit__.assert_called_once()
