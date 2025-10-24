"""
Comprehensive tests for BaseHandler and SimpleHandler.

Covers:
- BaseHandler initialization
- Client creation (LLM, Supabase)
- Setup hook mechanism
- Agent dependencies creation
- SimpleHandler execution (non-streaming)
- Error handling in initialization
- Error handling in execution
- Logging throughout
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

from src.agent import UnifiedAgentDeps
from src.ui.features.base_handler import BaseHandler, SimpleHandler

# ===== Test Subclass =====


class TestHandler(BaseHandler):
    """Concrete implementation of BaseHandler for testing."""

    async def run_agent(
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs,
    ):
        return {"response": "test response"}


# ===== Fixtures =====


@pytest.fixture
def mock_config():
    """Mock UI configuration."""
    return {"mode": "simple", "features": {}}


@pytest.fixture
def base_handler(mock_config):
    """Create BaseHandler test instance."""
    return TestHandler(mock_config)


@pytest.fixture
def simple_handler(mock_config):
    """Create SimpleHandler instance."""
    return SimpleHandler(mock_config)


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


# ===== BaseHandler Initialization Tests =====


@pytest.mark.asyncio
class TestBaseHandlerInit:
    """Test BaseHandler initialization."""

    def test_init(self, mock_config):
        """Test basic initialization."""
        handler = TestHandler(mock_config)

        assert handler.config == mock_config
        assert handler.embedding_client is None
        assert handler.supabase is None
        assert handler._initialized is False

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    def test_initialize_creates_clients(self, mock_get_supabase, mock_get_llm, base_handler):
        """Test that initialize() creates clients."""
        mock_llm_client = Mock()
        mock_supabase_client = Mock()
        mock_get_llm.return_value = mock_llm_client
        mock_get_supabase.return_value = mock_supabase_client

        base_handler.initialize()

        assert base_handler.embedding_client == mock_llm_client
        assert base_handler.supabase == mock_supabase_client
        assert base_handler._initialized is True

        mock_get_llm.assert_called_once()
        mock_get_supabase.assert_called_once()

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    def test_initialize_only_once(self, mock_get_supabase, mock_get_llm, base_handler):
        """Test that initialize() only runs once."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        base_handler.initialize()
        base_handler.initialize()  # Second call

        # Should only be called once
        mock_get_llm.assert_called_once()
        mock_get_supabase.assert_called_once()

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    def test_initialize_calls_setup_hook(self, mock_get_supabase, mock_get_llm, base_handler):
        """Test that initialize() calls _setup_hook()."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        with patch.object(base_handler, "_setup_hook") as mock_setup_hook:
            base_handler.initialize()

            mock_setup_hook.assert_called_once()

    @patch("src.ui.features.base_handler.get_llm_client")
    def test_initialize_llm_client_error(self, mock_get_llm, base_handler):
        """Test error handling when LLM client creation fails."""
        mock_get_llm.side_effect = ConnectionError("LLM connection failed")

        with pytest.raises(ConnectionError, match="LLM connection failed"):
            base_handler.initialize()

        assert base_handler._initialized is False

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    def test_initialize_supabase_client_error(self, mock_get_supabase, mock_get_llm, base_handler):
        """Test error handling when Supabase client creation fails."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.side_effect = RuntimeError("Supabase connection failed")

        with pytest.raises(RuntimeError, match="Supabase connection failed"):
            base_handler.initialize()

        assert base_handler._initialized is False

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    def test_initialize_setup_hook_error(self, mock_get_supabase, mock_get_llm, base_handler):
        """Test error handling when _setup_hook() fails."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        with patch.object(base_handler, "_setup_hook", side_effect=ValueError("Setup failed")):
            with pytest.raises(ValueError, match="Setup failed"):
                base_handler.initialize()

    @patch("src.ui.features.base_handler.logger")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    def test_initialize_logging(self, mock_get_supabase, mock_get_llm, mock_logger, base_handler):
        """Test that initialization produces proper logs."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        base_handler.initialize()

        # Verify logging calls
        assert mock_logger.info.called
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("initialize()" in str(call) for call in log_calls)
        assert any("COMPLETE" in str(call) for call in log_calls)


# ===== BaseHandler Dependencies Tests =====


@pytest.mark.asyncio
class TestBaseHandlerDeps:
    """Test BaseHandler agent dependencies creation."""

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    @patch("src.ui.features.base_handler.get_settings")
    def test_get_agent_deps_basic(
        self,
        mock_get_settings,
        mock_get_supabase,
        mock_get_llm,
        base_handler,
        mock_http_client,
    ):
        """Test basic agent dependencies creation."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_settings = Mock()
        mock_settings.brave_api_key = "brave_key"
        mock_settings.jina_api_key = "jina_key"
        mock_settings.searxng_base_url = "http://searxng"
        mock_settings.web_search_provider = "brave"
        mock_get_settings.return_value = mock_settings

        base_handler.initialize()
        deps = base_handler.get_agent_deps(mock_http_client)

        assert isinstance(deps, UnifiedAgentDeps)
        assert deps.http_client == mock_http_client
        assert deps.brave_api_key == "brave_key"
        assert deps.jina_api_key == "jina_key"
        assert deps.searxng_base_url == "http://searxng"
        assert deps.web_search_provider == "brave"

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    @patch("src.ui.features.base_handler.get_settings")
    def test_get_agent_deps_with_memories(
        self,
        mock_get_settings,
        mock_get_supabase,
        mock_get_llm,
        base_handler,
        mock_http_client,
    ):
        """Test agent dependencies with memory context."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_settings = Mock()
        mock_settings.brave_api_key = None
        mock_settings.jina_api_key = None
        mock_settings.searxng_base_url = None
        mock_settings.web_search_provider = None
        mock_get_settings.return_value = mock_settings

        base_handler.initialize()
        memories = "User likes Python. User works at OpenAI."
        deps = base_handler.get_agent_deps(mock_http_client, memories_str=memories)

        assert deps.memories == memories

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    @patch("src.ui.features.base_handler.get_settings")
    def test_get_agent_deps_empty_settings(
        self,
        mock_get_settings,
        mock_get_supabase,
        mock_get_llm,
        base_handler,
        mock_http_client,
    ):
        """Test agent dependencies with no optional settings."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_settings = Mock()
        mock_settings.brave_api_key = None
        mock_settings.jina_api_key = None
        mock_settings.searxng_base_url = None
        mock_settings.web_search_provider = None
        mock_get_settings.return_value = mock_settings

        base_handler.initialize()
        deps = base_handler.get_agent_deps(mock_http_client)

        # Should use empty strings for None values
        assert deps.brave_api_key == ""
        assert deps.jina_api_key == ""
        assert deps.searxng_base_url == ""
        assert deps.web_search_provider == ""

    @patch("src.ui.features.base_handler.logger")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    @patch("src.ui.features.base_handler.get_settings")
    def test_get_agent_deps_logging(
        self,
        mock_get_settings,
        mock_get_supabase,
        mock_get_llm,
        mock_logger,
        base_handler,
        mock_http_client,
    ):
        """Test that get_agent_deps produces proper logs."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_settings = Mock()
        mock_settings.brave_api_key = "key"
        mock_settings.jina_api_key = None
        mock_settings.searxng_base_url = None
        mock_settings.web_search_provider = "brave"
        mock_get_settings.return_value = mock_settings

        base_handler.initialize()
        base_handler.get_agent_deps(mock_http_client, memories_str="some memories")

        # Verify logging
        assert mock_logger.debug.called
        assert mock_logger.info.called


# ===== SimpleHandler Tests =====


@pytest.mark.asyncio
class TestSimpleHandler:
    """Test SimpleHandler execution."""

    @patch("src.ui.features.base_handler.super_agent")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    async def test_run_agent_basic(
        self,
        mock_get_supabase,
        mock_get_llm,
        mock_super_agent,
        simple_handler,
        mock_http_client,
        sample_message_history,
    ):
        """Test basic agent execution."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        # Mock agent result
        mock_result = Mock()
        mock_result.output = "Test response"
        mock_result.new_messages.return_value = [ModelResponse(parts=["Test response"])]
        mock_super_agent.run = AsyncMock(return_value=mock_result)

        simple_handler.initialize()
        result = await simple_handler.run_agent(
            "test input", sample_message_history, mock_http_client
        )

        assert result["response"] == "Test response"
        assert result["streaming"] is False
        assert len(result["new_messages"]) == 1

    @patch("src.ui.features.base_handler.super_agent")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    async def test_run_agent_long_output(
        self,
        mock_get_supabase,
        mock_get_llm,
        mock_super_agent,
        simple_handler,
        mock_http_client,
        sample_message_history,
    ):
        """Test agent with very long output."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        long_output = "x" * 10000
        mock_result = Mock()
        mock_result.output = long_output
        mock_result.new_messages.return_value = [ModelResponse(parts=[long_output])]
        mock_super_agent.run = AsyncMock(return_value=mock_result)

        simple_handler.initialize()
        result = await simple_handler.run_agent(
            "test input", sample_message_history, mock_http_client
        )

        assert result["response"] == long_output
        assert len(result["response"]) == 10000

    @patch("src.ui.features.base_handler.super_agent")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    async def test_run_agent_empty_output(
        self,
        mock_get_supabase,
        mock_get_llm,
        mock_super_agent,
        simple_handler,
        mock_http_client,
        sample_message_history,
    ):
        """Test agent with empty output."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_result = Mock()
        mock_result.output = ""
        mock_result.new_messages.return_value = []
        mock_super_agent.run = AsyncMock(return_value=mock_result)

        simple_handler.initialize()
        result = await simple_handler.run_agent(
            "test input", sample_message_history, mock_http_client
        )

        assert result["response"] == ""
        assert len(result["new_messages"]) == 0

    @patch("src.ui.features.base_handler.super_agent")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    async def test_run_agent_none_output(
        self,
        mock_get_supabase,
        mock_get_llm,
        mock_super_agent,
        simple_handler,
        mock_http_client,
        sample_message_history,
    ):
        """Test agent with None output."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_result = Mock()
        mock_result.output = None
        mock_result.new_messages.return_value = []
        mock_super_agent.run = AsyncMock(return_value=mock_result)

        simple_handler.initialize()
        result = await simple_handler.run_agent(
            "test input", sample_message_history, mock_http_client
        )

        assert result["response"] is None
        assert result["streaming"] is False

    @patch("src.ui.features.base_handler.super_agent")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    async def test_run_agent_empty_history(
        self,
        mock_get_supabase,
        mock_get_llm,
        mock_super_agent,
        simple_handler,
        mock_http_client,
    ):
        """Test agent with empty message history."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_result = Mock()
        mock_result.output = "Response"
        mock_result.new_messages.return_value = [ModelResponse(parts=["Response"])]
        mock_super_agent.run = AsyncMock(return_value=mock_result)

        simple_handler.initialize()
        result = await simple_handler.run_agent("test input", [], mock_http_client)

        assert result["response"] == "Response"
        mock_super_agent.run.assert_called_once()

    @patch("src.ui.features.base_handler.super_agent")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    async def test_run_agent_error_handling(
        self,
        mock_get_supabase,
        mock_get_llm,
        mock_super_agent,
        simple_handler,
        mock_http_client,
        sample_message_history,
    ):
        """Test error handling in agent execution."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_super_agent.run = AsyncMock(side_effect=RuntimeError("Agent execution failed"))

        simple_handler.initialize()
        with pytest.raises(RuntimeError, match="Agent execution failed"):
            await simple_handler.run_agent("test input", sample_message_history, mock_http_client)

    @patch("src.ui.features.base_handler.logger")
    @patch("src.ui.features.base_handler.super_agent")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    async def test_run_agent_logging(
        self,
        mock_get_supabase,
        mock_get_llm,
        mock_super_agent,
        mock_logger,
        simple_handler,
        mock_http_client,
        sample_message_history,
    ):
        """Test that run_agent produces proper logs."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_result = Mock()
        mock_result.output = "Test response"
        mock_result.new_messages.return_value = [ModelResponse(parts=["Test response"])]
        mock_super_agent.run = AsyncMock(return_value=mock_result)

        simple_handler.initialize()
        await simple_handler.run_agent("test input", sample_message_history, mock_http_client)

        # Verify logging
        assert mock_logger.info.called
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("NON-STREAMING" in str(call) for call in log_calls)
        assert any("COMPLETE" in str(call) for call in log_calls)

    @patch("src.ui.features.base_handler.logger")
    @patch("src.ui.features.base_handler.super_agent")
    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    async def test_run_agent_error_logging(
        self,
        mock_get_supabase,
        mock_get_llm,
        mock_super_agent,
        mock_logger,
        simple_handler,
        mock_http_client,
        sample_message_history,
    ):
        """Test error logging in agent execution."""
        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        mock_super_agent.run = AsyncMock(side_effect=ValueError("Test error"))

        simple_handler.initialize()
        with pytest.raises(ValueError):
            await simple_handler.run_agent("test input", sample_message_history, mock_http_client)

        # Verify exception logging
        mock_logger.exception.assert_called_once()
        call_args = mock_logger.exception.call_args
        assert "FAILED" in str(call_args)


# ===== Setup Hook Tests =====


@pytest.mark.asyncio
class TestSetupHook:
    """Test _setup_hook mechanism."""

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    def test_setup_hook_called(self, mock_get_supabase, mock_get_llm):
        """Test that _setup_hook is called during initialization."""

        class HookedHandler(BaseHandler):
            def __init__(self, config):
                super().__init__(config)
                self.hook_called = False

            def _setup_hook(self):
                self.hook_called = True

            async def run_agent(self, *args, **kwargs):
                pass

        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        handler = HookedHandler({})
        handler.initialize()

        assert handler.hook_called is True

    @patch("src.ui.features.base_handler.get_llm_client")
    @patch("src.ui.features.base_handler.get_supabase_client")
    def test_setup_hook_can_modify_state(self, mock_get_supabase, mock_get_llm):
        """Test that _setup_hook can modify handler state."""

        class StatefulHandler(BaseHandler):
            def __init__(self, config):
                super().__init__(config)
                self.custom_state = None

            def _setup_hook(self):
                self.custom_state = "initialized"

            async def run_agent(self, *args, **kwargs):
                pass

        mock_get_llm.return_value = Mock()
        mock_get_supabase.return_value = Mock()

        handler = StatefulHandler({})
        handler.initialize()

        assert handler.custom_state == "initialized"
