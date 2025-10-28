"""Ultra comprehensive tests for streamlit_app.py (target: 60%+ coverage)."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse

from src.config import UIMode


class TestMakeJsonSafe:
    """Test make_json_safe() function."""

    def test_make_json_safe_none(self):
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe(None)
        assert result is None

    def test_make_json_safe_primitives(self):
        from src.ui.streamlit_app import make_json_safe

        assert make_json_safe(True) is True
        assert make_json_safe(False) is False
        assert make_json_safe(42) == 42
        assert make_json_safe(3.14) == 3.14
        assert make_json_safe("hello") == "hello"

    def test_make_json_safe_list(self):
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe([1, 2, "three"])
        assert result == [1, 2, "three"]

    def test_make_json_safe_tuple(self):
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe((1, 2, "three"))
        assert result == [1, 2, "three"]

    def test_make_json_safe_dict(self):
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_make_json_safe_nested(self):
        from src.ui.streamlit_app import make_json_safe

        data = {
            "list": [1, 2, 3],
            "dict": {"nested": True},
            "tuple": (4, 5, 6),
        }
        result = make_json_safe(data)
        assert result["list"] == [1, 2, 3]
        assert result["dict"] == {"nested": True}
        assert result["tuple"] == [4, 5, 6]

    def test_make_json_safe_max_depth(self):
        from src.ui.streamlit_app import make_json_safe

        # Create deeply nested structure
        deep = {"level": 1}
        current = deep
        for i in range(15):
            current["nested"] = {"level": i + 2}
            current = current["nested"]

        result = make_json_safe(deep, max_depth=5)
        # Should stop at max depth
        assert "<max depth reached>" in str(result)

    def test_make_json_safe_non_serializable_object(self):
        from src.ui.streamlit_app import make_json_safe

        class CustomObject:
            def __str__(self):
                return "custom"

        obj = CustomObject()
        result = make_json_safe(obj)
        assert result == "custom"

    def test_make_json_safe_unprintable_object(self):
        from src.ui.streamlit_app import make_json_safe

        class BadObject:
            def __str__(self):
                raise Exception("Cannot convert to string")

        obj = BadObject()
        result = make_json_safe(obj)
        assert "BadObject object" in result


class TestUIConfig:
    """Test UIConfig class."""

    def test_uiconfig_init_simple(self):
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config") as mock_config:
            mock_config.mode = UIMode.SIMPLE
            ui_config = UIConfig()

            assert ui_config.mode == UIMode.SIMPLE
            assert ui_config.features["streaming"] is False
            assert ui_config.features["memory"] is False
            assert ui_config.features["mcp"] is False
            assert ui_config.features["tools_visibility"] is False
            assert ui_config.features["metrics"] is False

    def test_uiconfig_init_standard(self):
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config") as mock_config:
            mock_config.mode = UIMode.STANDARD
            ui_config = UIConfig()

            assert ui_config.mode == UIMode.STANDARD
            assert ui_config.features["streaming"] is True
            assert ui_config.features["memory"] is False
            assert ui_config.features["mcp"] is False
            assert ui_config.features["tools_visibility"] is True
            assert ui_config.features["metrics"] is False

    def test_uiconfig_init_advanced(self):
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config") as mock_config:
            mock_config.mode = UIMode.ADVANCED
            ui_config = UIConfig()

            assert ui_config.mode == UIMode.ADVANCED
            assert ui_config.features["streaming"] is True
            assert ui_config.features["memory"] is True
            assert ui_config.features["mcp"] is True
            assert ui_config.features["tools_visibility"] is True
            assert ui_config.features["metrics"] is True

    def test_uiconfig_get_handler_simple(self):
        from src.ui.features.base_handler import SimpleHandler
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config") as mock_config:
            mock_config.mode = UIMode.SIMPLE
            ui_config = UIConfig()
            handler = ui_config.get_handler()

            assert isinstance(handler, SimpleHandler)

    def test_uiconfig_get_handler_standard(self):
        from src.ui.features import StreamingHandler
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config") as mock_config:
            mock_config.mode = UIMode.STANDARD
            ui_config = UIConfig()
            handler = ui_config.get_handler()

            assert isinstance(handler, StreamingHandler)

    def test_uiconfig_get_handler_advanced(self):
        from src.ui.features import MCPHandler
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config") as mock_config:
            mock_config.mode = UIMode.ADVANCED
            ui_config = UIConfig()
            handler = ui_config.get_handler()

            assert isinstance(handler, MCPHandler)

    def test_get_features_for_mode_simple(self):
        from src.ui.streamlit_app import UIConfig

        features = UIConfig._get_features_for_mode(UIMode.SIMPLE)
        assert features["streaming"] is False
        assert features["memory"] is False

    def test_get_features_for_mode_standard(self):
        from src.ui.streamlit_app import UIConfig

        features = UIConfig._get_features_for_mode(UIMode.STANDARD)
        assert features["streaming"] is True
        assert features["memory"] is False
        assert features["tools_visibility"] is True

    def test_get_features_for_mode_advanced(self):
        from src.ui.streamlit_app import UIConfig

        features = UIConfig._get_features_for_mode(UIMode.ADVANCED)
        assert features["streaming"] is True
        assert features["memory"] is True
        assert features["mcp"] is True
        assert features["tools_visibility"] is True
        assert features["metrics"] is True


class TestDisplayMessagePart:
    """Test display_message_part() function."""

    @patch("streamlit.chat_message")
    @patch("streamlit.markdown")
    def test_display_user_prompt(self, mock_markdown, mock_chat_message):
        from src.ui.streamlit_app import display_message_part

        mock_context = MagicMock()
        mock_chat_message.return_value.__enter__.return_value = mock_context

        part = Mock()
        part.part_kind = "user-prompt"
        part.content = "Hello"

        display_message_part(part)

        mock_chat_message.assert_called_once_with("user")
        mock_markdown.assert_called_once_with("Hello")

    @patch("streamlit.chat_message")
    @patch("streamlit.markdown")
    def test_display_assistant_text(self, mock_markdown, mock_chat_message):
        from src.ui.streamlit_app import display_message_part

        mock_context = MagicMock()
        mock_chat_message.return_value.__enter__.return_value = mock_context

        part = Mock()
        part.part_kind = "text"
        part.content = "Response"

        display_message_part(part)

        mock_chat_message.assert_called_once_with("assistant")
        mock_markdown.assert_called_once_with("Response")

    @patch("streamlit.expander")
    @patch("streamlit.session_state")
    def test_display_tool_call_with_visibility(self, mock_session_state, mock_expander):
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_session_state.config = mock_config

        part = Mock()
        part.part_kind = "tool-call"
        part.tool_name = "test_tool"
        part.args = {"key": "value"}

        with patch("streamlit.json") as mock_json:
            display_message_part(part)
            mock_expander.assert_called_once()
            mock_json.assert_called_once()

    @patch("streamlit.session_state")
    def test_display_tool_call_no_visibility(self, mock_session_state):
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": False}
        mock_session_state.config = mock_config

        part = Mock()
        part.part_kind = "tool-call"
        part.tool_name = "test_tool"

        with patch("streamlit.expander") as mock_expander:
            display_message_part(part)
            mock_expander.assert_not_called()

    @patch("streamlit.expander")
    @patch("streamlit.code")
    @patch("streamlit.session_state")
    def test_display_tool_call_empty_args(self, mock_session_state, mock_code, mock_expander):
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_session_state.config = mock_config

        mock_expander_context = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_context

        part = Mock()
        part.part_kind = "tool-call"
        part.tool_name = "test_tool"
        part.args = ""

        with patch("streamlit.info") as mock_info:
            display_message_part(part)
            mock_info.assert_called_once_with("No arguments")

    @patch("streamlit.expander")
    @patch("streamlit.code")
    @patch("streamlit.session_state")
    def test_display_tool_call_invalid_json(self, mock_session_state, mock_code, mock_expander):
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_session_state.config = mock_config

        mock_expander_context = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_context

        part = Mock()
        part.part_kind = "tool-call"
        part.tool_name = "test_tool"
        part.args = "invalid json"

        display_message_part(part)
        mock_code.assert_called_once()

    @patch("streamlit.expander")
    @patch("streamlit.code")
    @patch("streamlit.session_state")
    def test_display_tool_return(self, mock_session_state, mock_code, mock_expander):
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_session_state.config = mock_config

        mock_expander_context = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_context

        part = Mock()
        part.part_kind = "tool-return"
        part.tool_name = "test_tool"
        part.content = "result"

        display_message_part(part)
        mock_code.assert_called_once()

    @patch("streamlit.expander")
    @patch("streamlit.code")
    @patch("streamlit.caption")
    @patch("streamlit.session_state")
    def test_display_tool_return_long_content(
        self, mock_session_state, mock_caption, mock_code, mock_expander
    ):
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_session_state.config = mock_config

        mock_expander_context = MagicMock()
        mock_expander.return_value.__enter__.return_value = mock_expander_context

        part = Mock()
        part.part_kind = "tool-return"
        part.tool_name = "test_tool"
        part.content = "x" * 3000

        display_message_part(part)
        mock_caption.assert_called_once()
        mock_code.assert_called_once()


class TestExportConversation:
    """Test export_conversation() function."""

    @patch("streamlit.download_button")
    @patch("streamlit.session_state")
    def test_export_conversation_empty(self, mock_session_state, mock_download_button):
        from src.ui.streamlit_app import export_conversation

        mock_config = Mock()
        mock_config.mode = UIMode.SIMPLE
        mock_session_state.config = mock_config
        mock_session_state.messages = []

        export_conversation()

        mock_download_button.assert_called_once()
        call_args = mock_download_button.call_args
        data = call_args[1]["data"]
        export_data = json.loads(data)

        assert export_data["mode"] == "simple"
        assert len(export_data["messages"]) == 0

    @patch("streamlit.download_button")
    @patch("streamlit.session_state")
    def test_export_conversation_with_messages(self, mock_session_state, mock_download_button):
        from src.ui.streamlit_app import export_conversation

        mock_config = Mock()
        mock_config.mode = UIMode.STANDARD
        mock_session_state.config = mock_config

        # Create mock messages
        user_part = Mock()
        user_part.part_kind = "user-prompt"
        user_part.content = "Hello"

        assistant_part = Mock()
        assistant_part.part_kind = "text"
        assistant_part.content = "Hi there"

        mock_request = Mock(spec=ModelRequest)
        mock_request.parts = [user_part]

        mock_response = Mock(spec=ModelResponse)
        mock_response.parts = [assistant_part]

        mock_session_state.messages = [mock_request, mock_response]

        export_conversation()

        mock_download_button.assert_called_once()
        call_args = mock_download_button.call_args
        data = call_args[1]["data"]
        export_data = json.loads(data)

        assert len(export_data["messages"]) == 2
        assert export_data["messages"][0]["role"] == "user"
        assert export_data["messages"][0]["content"] == "Hello"
        assert export_data["messages"][1]["role"] == "assistant"
        assert export_data["messages"][1]["content"] == "Hi there"


class TestInitializeSessionState:
    """Test initialize_session_state() function."""

    @patch("streamlit.progress")
    @patch("streamlit.empty")
    @patch("streamlit.markdown")
    @patch("time.sleep")
    def test_initialize_session_state_first_time(
        self, mock_sleep, mock_markdown, mock_empty, mock_progress
    ):
        from src.ui.streamlit_app import initialize_session_state

        # Create a dict-like object that also supports attribute access (like Streamlit's SessionState)
        class SessionStateDict(dict):
            def __getattr__(self, key):
                try:
                    return self[key]
                except KeyError:
                    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

            def __setattr__(self, key, value):
                self[key] = value

        mock_session_state = SessionStateDict()

        # Create proper container mock with nested context managers
        mock_container = MagicMock()
        mock_loading_placeholder = MagicMock()
        mock_loading_placeholder.container.return_value.__enter__.return_value = mock_container
        mock_loading_placeholder.empty = MagicMock()
        mock_empty.return_value = mock_loading_placeholder

        mock_progress_bar = MagicMock()
        mock_progress.return_value = mock_progress_bar

        with patch("streamlit.session_state", mock_session_state):
            with patch("src.ui.streamlit_app.config") as mock_ui_config:
                mock_ui_config.mode = UIMode.SIMPLE

                with patch("src.ui.streamlit_app.ConnectionManager"):
                    with patch(
                        "src.ui.streamlit_app.initialize_analytics_logger"
                    ) as mock_init_analytics:
                        mock_init_analytics.return_value = Mock()

                        initialize_session_state()

                        # Check that session state was initialized
                        assert "messages" in mock_session_state
                        assert "config" in mock_session_state
                        assert "handler" in mock_session_state


@pytest.mark.asyncio
class TestHandleUserInput:
    """Test handle_user_input() function."""

    @patch("streamlit.session_state")
    @patch("streamlit.chat_message")
    @patch("streamlit.markdown")
    @patch("streamlit.spinner")
    async def test_handle_user_input_simple_mode(
        self, mock_spinner, mock_markdown, mock_chat_message, mock_session_state
    ):
        from src.ui.streamlit_app import handle_user_input

        mock_config = Mock()
        mock_config.mode = UIMode.SIMPLE
        mock_config.features = {"streaming": False}

        mock_handler = Mock()
        mock_handler.run_agent = AsyncMock(
            return_value={"response": "Test response", "new_messages": []}
        )

        mock_session_state.config = mock_config
        mock_session_state.handler = mock_handler
        mock_session_state.messages = []
        mock_session_state.get = Mock(return_value=False)

        mock_chat_context = MagicMock()
        mock_chat_message.return_value.__enter__.return_value = mock_chat_context

        mock_spinner_context = MagicMock()
        mock_spinner.return_value.__enter__.return_value = mock_spinner_context

        # Mock AsyncClient as a proper async context manager
        mock_http_client = MagicMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            await handle_user_input("Hello")

            mock_handler.run_agent.assert_called_once()
            mock_markdown.assert_called()

    @patch("streamlit.session_state")
    @patch("streamlit.chat_message")
    @patch("streamlit.markdown")
    @patch("streamlit.empty")
    async def test_handle_user_input_streaming_mode(
        self, mock_empty, mock_markdown, mock_chat_message, mock_session_state
    ):
        from src.ui.streamlit_app import handle_user_input

        mock_config = Mock()
        mock_config.mode = UIMode.STANDARD
        mock_config.features = {"streaming": True, "tools_visibility": False}

        mock_handler = Mock()

        async def mock_stream(user_input, messages, http_client):
            yield {"type": "start", "content": "Test"}
            yield {"type": "delta", "content": " response"}
            yield {"type": "complete", "new_messages": []}

        mock_handler.run_agent = mock_stream

        mock_session_state.config = mock_config
        mock_session_state.handler = mock_handler
        mock_session_state.messages = []
        mock_session_state.get = Mock(return_value=False)

        mock_chat_context = MagicMock()
        mock_chat_message.return_value.__enter__.return_value = mock_chat_context

        mock_placeholder = MagicMock()
        mock_status_placeholder = MagicMock()

        # Mock empty() to return different placeholders for each call
        mock_empty.side_effect = [mock_placeholder, mock_status_placeholder]

        # Mock AsyncClient as a proper async context manager
        mock_http_client = MagicMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            await handle_user_input("Hello")

            assert mock_placeholder.markdown.called


@pytest.mark.asyncio
class TestRenderDashboard:
    """Test render_dashboard() function."""

    @patch("streamlit.title")
    @patch("streamlit.caption")
    @patch("streamlit.empty")
    @patch("streamlit.markdown")
    @patch("streamlit.progress")
    @patch("src.agentic_rag.storage.connection_manager.get_connection_manager")
    @patch("src.ui.streamlit_app.DashboardHandler")
    async def test_render_dashboard_success(
        self,
        mock_dashboard_handler_class,
        mock_get_connection_manager,
        mock_progress,
        mock_markdown,
        mock_empty,
        mock_caption,
        mock_title,
    ):
        from src.ui.streamlit_app import render_dashboard

        mock_conn_mgr = Mock()
        mock_get_connection_manager.return_value = mock_conn_mgr

        mock_handler = Mock()
        mock_dashboard_handler_class.return_value = mock_handler

        # Create proper container mock
        mock_container = MagicMock()
        mock_loading_placeholder = MagicMock()
        mock_loading_placeholder.container.return_value.__enter__.return_value = mock_container
        mock_loading_placeholder.empty = MagicMock()
        mock_empty.return_value = mock_loading_placeholder

        mock_progress_bar = MagicMock()
        mock_progress.return_value = mock_progress_bar

        mock_status_text = MagicMock()
        mock_container.empty = Mock(return_value=mock_status_text)

        with patch("src.ui.streamlit_app._render_dashboard_content") as mock_render:
            mock_render.return_value = None

            await render_dashboard()

            mock_get_connection_manager.assert_called_once()
            mock_dashboard_handler_class.assert_called_once_with(mock_conn_mgr)
            mock_render.assert_called_once_with(mock_handler)

    @patch("streamlit.title")
    @patch("streamlit.caption")
    @patch("streamlit.empty")
    @patch("streamlit.markdown")
    @patch("streamlit.progress")
    @patch("streamlit.error")
    @patch("streamlit.info")
    @patch("src.agentic_rag.storage.connection_manager.get_connection_manager")
    async def test_render_dashboard_error(
        self,
        mock_get_connection_manager,
        mock_info,
        mock_error,
        mock_progress,
        mock_markdown,
        mock_empty,
        mock_caption,
        mock_title,
    ):
        from src.ui.streamlit_app import render_dashboard

        mock_get_connection_manager.side_effect = Exception("Connection failed")

        # Create proper container mock
        mock_container = MagicMock()
        mock_loading_placeholder = MagicMock()
        mock_loading_placeholder.container.return_value.__enter__.return_value = mock_container
        mock_loading_placeholder.empty = MagicMock()
        mock_empty.return_value = mock_loading_placeholder

        mock_progress_bar = MagicMock()
        mock_progress.return_value = mock_progress_bar

        mock_status_text = MagicMock()
        mock_container.empty = Mock(return_value=mock_status_text)

        await render_dashboard()

        mock_error.assert_called_once()
        mock_info.assert_called_once()


class TestMain:
    """Test main() function."""

    @patch("streamlit.set_page_config")
    @patch("streamlit.query_params")
    @patch("src.ui.streamlit_app.require_authentication")
    @patch("src.ui.streamlit_app.initialize_session_state")
    @patch("src.ui.streamlit_app.render_sidebar")
    @patch("streamlit.session_state")
    @patch("streamlit.title")
    @patch("streamlit.caption")
    @patch("streamlit.chat_input")
    def test_main_chat_page_no_input(
        self,
        mock_chat_input,
        mock_caption,
        mock_title,
        mock_session_state,
        mock_render_sidebar,
        mock_initialize,
        mock_require_auth,
        mock_query_params,
        mock_set_page_config,
    ):
        from src.ui.streamlit_app import main

        mock_query_params.get.return_value = None
        mock_require_auth.return_value = ("Test User", Mock())

        mock_config = Mock()
        mock_config.mode = UIMode.STANDARD
        mock_session_state.config = mock_config
        mock_session_state.messages = []

        # Mock get() to return proper values - first call for config, second for current_page
        def mock_get(key, default=None):
            if key == "config":
                return mock_config
            if key == "current_page":
                return "Chat"
            return default

        mock_session_state.get = Mock(side_effect=mock_get)

        mock_chat_input.return_value = None

        # Run main
        asyncio.run(main())

        mock_set_page_config.assert_called_once()
        mock_require_auth.assert_called_once()
        mock_initialize.assert_called_once()


class TestLLMClient:
    """Test LLM client functions."""

    def test_get_llm_client_anthropic(self):
        from src.clients.llm import get_llm_client

        with patch("src.clients.llm.clients_config") as mock_config:
            mock_config.llm_provider.value = "anthropic"

            result = get_llm_client()
            assert result is None

    def test_get_llm_client_openai(self):
        from src.clients.llm import get_llm_client

        with patch("src.clients.llm.clients_config") as mock_config:
            mock_config.llm_provider.value = "openai"
            mock_config.llm_base_url = "https://api.openai.com/v1"
            mock_config.llm_api_key = "test-key"

            with patch("src.clients.llm.AsyncOpenAI") as MockAsyncOpenAI:
                get_llm_client()
                MockAsyncOpenAI.assert_called_once()

    def test_get_model_anthropic(self):
        from src.clients.llm import get_model

        with patch("src.clients.llm.clients_config") as mock_config:
            mock_config.llm_provider.value = "anthropic"
            mock_config.llm_model = "claude-3-sonnet"
            mock_config.llm_api_key = "test-key"

            with patch("src.clients.llm.AnthropicModel") as MockAnthropicModel:
                get_model()
                MockAnthropicModel.assert_called_once()

    def test_get_model_openai(self):
        from src.clients.llm import get_model

        with patch("src.clients.llm.clients_config") as mock_config:
            mock_config.llm_provider.value = "openai"
            mock_config.llm_model = "gpt-4"
            mock_config.llm_api_key = "test-key"
            mock_config.llm_base_url = "https://api.openai.com/v1"

            with patch("src.clients.llm.OpenAIChatModel") as MockOpenAIChatModel:
                with patch("src.clients.llm.OpenAIProvider"):
                    get_model()
                    MockOpenAIChatModel.assert_called_once()

    def test_get_model_ollama(self):
        from src.clients.llm import get_model

        with patch("src.clients.llm.clients_config") as mock_config:
            mock_config.llm_provider.value = "ollama"
            mock_config.llm_model = "llama2"
            mock_config.llm_api_key = "ollama"
            mock_config.llm_base_url = "http://localhost:11434/v1"

            with patch("src.clients.llm.OpenAIChatModel") as MockOpenAIChatModel:
                with patch("src.clients.llm.OpenAIProvider"):
                    get_model()
                    MockOpenAIChatModel.assert_called_once()

    def test_get_model_anthropic_name_mapping(self):
        from src.clients.llm import get_model

        with patch("src.clients.llm.clients_config") as mock_config:
            mock_config.llm_provider.value = "anthropic"
            mock_config.llm_api_key = "test-key"

            with patch("src.clients.llm.AnthropicModel") as MockAnthropicModel:
                # Test model name mappings
                mock_config.llm_model = "claude-3-opus"
                get_model()
                assert "claude-3-opus-20240229" in str(MockAnthropicModel.call_args)

                mock_config.llm_model = "claude-3.5-sonnet"
                get_model()
                assert "claude-3-5-sonnet-20241022" in str(MockAnthropicModel.call_args)
