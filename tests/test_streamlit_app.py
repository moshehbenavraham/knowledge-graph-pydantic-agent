import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

# Mock Streamlit functions before importing the app
sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit.runtime.scriptrunner.script_run_context"] = MagicMock()
sys.modules["streamlit.runtime.caching"] = MagicMock()
sys.modules["streamlit.session_state"] = MagicMock()
sys.modules["streamlit.elements.empty"] = MagicMock()
sys.modules["streamlit.elements.markdown"] = MagicMock()
sys.modules["streamlit.elements.chat"] = MagicMock()

# Add src directory to path to import the module
sys.path.append(str(Path(__file__).parent.parent.resolve() / "src"))

# Import after mocking and path setup
from ui.features.base_handler import SimpleHandler
from ui.features.mcp_handler import MCPHandler
from ui.features.streaming_handler import StreamingHandler
from ui.streamlit_app import (
    UIConfig,
    UIMode,
    display_message_part,
    export_conversation,
    handle_user_input,
    initialize_session_state,
    render_sidebar,
)
from ui.streamlit_app import main as streamlit_main


class TestUIConfig:
    def test_ui_modes(self):
        config = UIConfig()
        assert config.mode == UIMode.STANDARD  # Default mode

    def test_features_for_simple_mode(self):
        features = UIConfig._get_features_for_mode(UIMode.SIMPLE)
        assert features["streaming"] is False
        assert features["memory"] is False
        assert features["mcp"] is False
        assert features["tools_visibility"] is False
        assert features["metrics"] is False

    def test_features_for_standard_mode(self):
        features = UIConfig._get_features_for_mode(UIMode.STANDARD)
        assert features["streaming"] is True
        assert features["memory"] is False
        assert features["mcp"] is False
        assert features["tools_visibility"] is True
        assert features["metrics"] is False

    def test_features_for_advanced_mode(self):
        features = UIConfig._get_features_for_mode(UIMode.ADVANCED)
        assert features["streaming"] is True
        assert features["memory"] is True
        assert features["mcp"] is True
        assert features["tools_visibility"] is True
        assert features["metrics"] is True

    def test_get_handler_simple(self):
        config = UIConfig()
        config.mode = UIMode.SIMPLE
        handler = config.get_handler()
        assert isinstance(handler, SimpleHandler)

    def test_get_handler_standard(self):
        config = UIConfig()
        config.mode = UIMode.STANDARD
        handler = config.get_handler()
        assert isinstance(handler, StreamingHandler)

    def test_get_handler_advanced(self):
        config = UIConfig()
        config.mode = UIMode.ADVANCED
        handler = config.get_handler()
        assert isinstance(handler, MCPHandler)


class TestStreamlitApp:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # Reset Streamlit mocks before each test
        sys.modules["streamlit"].reset_mock()
        sys.modules["streamlit.session_state"].reset_mock()
        sys.modules["streamlit.session_state"].messages = []
        sys.modules["streamlit.session_state"].config = UIConfig()
        sys.modules["streamlit.session_state"].handler = None
        sys.modules["streamlit.session_state"].theme = "light"

        # Mock external dependencies
        with (
            patch("ui.streamlit_app.get_llm_client") as mock_get_llm_client,
            patch("ui.streamlit_app.get_supabase_client") as mock_get_supabase_client,
            patch("ui.features.base_handler.get_llm_client") as mock_handler_llm_client,
            patch("ui.features.base_handler.get_supabase_client") as mock_handler_supabase_client,
            patch("ui.features.memory_handler.get_mem0_client") as mock_get_mem0_client,
            patch("ui.streamlit_app.AsyncClient") as mock_async_client,
            patch("ui.streamlit_app.super_agent") as mock_super_agent,
            patch("ui.features.base_handler.super_agent") as mock_handler_super_agent,
        ):
            # Configure mocks
            mock_llm_client = MagicMock()
            mock_supabase_client = MagicMock()
            mock_get_llm_client.return_value = mock_llm_client
            mock_get_supabase_client.return_value = mock_supabase_client
            mock_handler_llm_client.return_value = mock_llm_client
            mock_handler_supabase_client.return_value = mock_supabase_client

            # Configure mem0 client mock
            mock_mem0_client = MagicMock()
            mock_mem0_client.search.return_value = {"results": []}
            mock_mem0_client.add.return_value = None
            mock_get_mem0_client.return_value = mock_mem0_client

            # Configure AsyncClient mock
            mock_http_client = AsyncMock()
            mock_async_client.return_value.__aenter__.return_value = mock_http_client
            mock_async_client.return_value.__aexit__.return_value = None

            # Configure super_agent mock
            mock_result = MagicMock()
            mock_result.output = "Test response"
            mock_result.new_messages.return_value = []
            mock_super_agent.run.return_value = mock_result
            mock_handler_super_agent.run.return_value = mock_result

            self.mock_get_llm_client = mock_get_llm_client
            self.mock_get_supabase_client = mock_get_supabase_client
            self.mock_get_mem0_client = mock_get_mem0_client
            self.mock_async_client = mock_async_client
            self.mock_super_agent = mock_super_agent
            self.mock_http_client = mock_http_client
            self.mock_mem0_client = mock_mem0_client

            yield

    def test_display_message_part_user_prompt(self):
        mock_st = sys.modules["streamlit"]
        part = UserPromptPart(content="Hello user")
        display_message_part(part)
        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with("Hello user")

    def test_display_message_part_text(self):
        mock_st = sys.modules["streamlit"]
        part = TextPart(content="Hello assistant")
        display_message_part(part)
        mock_st.chat_message.assert_called_once_with("assistant")
        mock_st.markdown.assert_called_once_with("Hello assistant")

    def test_initialize_session_state(self):
        mock_st = sys.modules["streamlit"]
        mock_st.session_state = MagicMock()
        mock_st.session_state.__contains__ = lambda self, key: False
        mock_st.session_state.messages = None
        mock_st.session_state.config = None
        mock_st.session_state.handler = None
        mock_st.session_state.theme = None

        initialize_session_state()

        assert mock_st.session_state.messages == []
        assert isinstance(mock_st.session_state.config, UIConfig)
        assert mock_st.session_state.handler is not None
        assert mock_st.session_state.theme == "light"

    def test_export_conversation(self):
        mock_st = sys.modules["streamlit"]
        mock_st.session_state.config = UIConfig()
        mock_st.session_state.messages = [
            ModelRequest(parts=[UserPromptPart(content="Test question")]),
            ModelResponse(parts=[TextPart(content="Test answer")]),
        ]

        export_conversation()

        # Check that download_button was called
        mock_st.download_button.assert_called_once()
        call_args = mock_st.download_button.call_args
        assert call_args[1]["label"] == "Download JSON"
        assert "conversation_" in call_args[1]["file_name"]
        assert call_args[1]["mime"] == "application/json"

    @pytest.mark.asyncio
    async def test_handle_user_input_simple_mode(self):
        mock_st = sys.modules["streamlit"]
        mock_st.session_state.config = UIConfig()
        mock_st.session_state.config.mode = UIMode.SIMPLE
        mock_st.session_state.config.features = UIConfig._get_features_for_mode(UIMode.SIMPLE)
        mock_st.session_state.handler = mock_st.session_state.config.get_handler()
        mock_st.session_state.handler.initialize = MagicMock()
        mock_st.session_state.handler.initialize()
        mock_st.session_state.messages = []
        mock_st.spinner.return_value.__enter__ = MagicMock()
        mock_st.spinner.return_value.__exit__ = MagicMock()

        # Mock the handler's run_agent method
        mock_result = {"response": "Simple response", "new_messages": [], "streaming": False}
        mock_st.session_state.handler.run_agent = AsyncMock(return_value=mock_result)

        await handle_user_input("Test input")

        # Verify user message was displayed
        assert mock_st.chat_message.call_count >= 2  # User and assistant
        mock_st.markdown.assert_any_call("Test input")
        mock_st.markdown.assert_any_call("Simple response")

    @pytest.mark.asyncio
    async def test_handle_user_input_streaming_mode(self):
        mock_st = sys.modules["streamlit"]
        mock_st.session_state.config = UIConfig()
        mock_st.session_state.config.mode = UIMode.STANDARD
        mock_st.session_state.config.features = UIConfig._get_features_for_mode(UIMode.STANDARD)
        mock_st.session_state.handler = mock_st.session_state.config.get_handler()
        mock_st.session_state.handler.initialize = MagicMock()
        mock_st.session_state.handler.initialize()
        mock_st.session_state.messages = []

        mock_placeholder = MagicMock()
        mock_st.empty.return_value = mock_placeholder

        # Mock the handler's run_agent method to yield streaming chunks
        async def mock_streaming():
            yield {"type": "start", "content": "Hello"}
            yield {"type": "delta", "content": " world"}
            yield {"type": "complete", "new_messages": []}

        mock_st.session_state.handler.run_agent = mock_streaming

        await handle_user_input("Test input")

        # Verify streaming updates
        assert mock_st.chat_message.call_count >= 2
        mock_placeholder.markdown.assert_any_call("Hello▌")
        mock_placeholder.markdown.assert_any_call("Hello world▌")
        mock_placeholder.markdown.assert_any_call("Hello world")

    @pytest.mark.asyncio
    async def test_main_function_configuration(self):
        mock_st = sys.modules["streamlit"]
        mock_st.set_page_config = MagicMock()
        mock_st.title = MagicMock()
        mock_st.caption = MagicMock()
        mock_st.chat_input = MagicMock(return_value=None)
        mock_st.session_state = MagicMock()
        mock_st.session_state.__contains__ = lambda self, key: True
        mock_st.session_state.messages = []
        mock_st.session_state.config = UIConfig()
        mock_st.session_state.handler = None
        mock_st.session_state.theme = "light"

        with patch("ui.streamlit_app.initialize_session_state") as mock_init:
            with patch("ui.streamlit_app.render_sidebar"):
                await streamlit_main()

                # Verify page configuration
                mock_st.set_page_config.assert_called_once()
                config_args = mock_st.set_page_config.call_args
                assert config_args[1]["page_title"] == "Pydantic AI Agent"
                assert config_args[1]["page_icon"] == "🤖"
                assert config_args[1]["layout"] == "wide"

                # Verify initialization
                mock_init.assert_called_once()

                # Verify title
                mock_st.title.assert_called_once_with("🤖 Pydantic AI Agent")

                # Verify mode indicator
                mock_st.caption.assert_called()

    def test_render_sidebar(self):
        mock_st = sys.modules["streamlit"]
        mock_st.session_state.config = UIConfig()
        mock_st.session_state.handler = mock_st.session_state.config.get_handler()
        mock_st.sidebar = MagicMock()
        mock_st.sidebar.__enter__ = MagicMock()
        mock_st.sidebar.__exit__ = MagicMock()

        # Mock the various sidebar elements
        mock_st.sidebar.title = MagicMock()
        mock_st.sidebar.subheader = MagicMock()
        mock_st.sidebar.radio = MagicMock(return_value=UIMode.STANDARD)
        mock_st.sidebar.divider = MagicMock()
        mock_st.sidebar.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
        mock_st.sidebar.button = MagicMock(return_value=False)
        mock_st.sidebar.caption = MagicMock()

        with mock_st.sidebar:
            render_sidebar()

        # Verify sidebar was populated
        mock_st.sidebar.title.assert_called_with("⚙️ Settings")
        mock_st.sidebar.subheader.assert_any_call("UI Mode")
        mock_st.sidebar.radio.assert_called_once()
