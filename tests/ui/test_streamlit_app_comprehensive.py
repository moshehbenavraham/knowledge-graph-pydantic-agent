"""
Comprehensive tests for src/ui/streamlit_app.py

Covers:
- make_json_safe() utility function with depth limits, circular refs
- UIConfig class, mode features, handler creation
- display_message_part() with all message types
- initialize_session_state() first init + subsequent calls
- render_sidebar() navigation, mode switching, feature toggles
- render_dashboard() and _render_dashboard_content()
- export_conversation() with various message types
- handle_user_input() streaming and non-streaming modes
- main() app initialization and routing
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, PropertyMock, patch

import pandas as pd
import pytest
from httpx import AsyncClient
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from src.config import UIMode


@pytest.fixture
def mock_streamlit():
    """Mock streamlit for testing."""
    with patch("src.ui.streamlit_app.st") as mock_st:
        # Mock session_state as a dictionary
        mock_st.session_state = {}

        # Mock common streamlit functions
        mock_st.empty = Mock(return_value=Mock(container=Mock(__enter__=Mock(), __exit__=Mock())))
        mock_st.markdown = Mock()
        mock_st.chat_message = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))
        mock_st.expander = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))
        mock_st.spinner = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))
        mock_st.status = Mock()
        mock_st.chat_input = Mock(return_value=None)
        mock_st.sidebar = Mock()
        mock_st.title = Mock()
        mock_st.caption = Mock()
        mock_st.divider = Mock()
        mock_st.subheader = Mock()
        mock_st.radio = Mock()
        mock_st.checkbox = Mock()
        mock_st.button = Mock(return_value=False)
        mock_st.download_button = Mock()
        mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock(), Mock()])
        mock_st.container = Mock()
        mock_st.metric = Mock()
        mock_st.progress = Mock(return_value=Mock())
        mock_st.error = Mock()
        mock_st.warning = Mock()
        mock_st.info = Mock()
        mock_st.success = Mock()
        mock_st.rerun = Mock()
        mock_st.set_page_config = Mock()
        mock_st.dataframe = Mock()
        mock_st.plotly_chart = Mock()
        mock_st.selectbox = Mock()
        mock_st.slider = Mock()
        mock_st.write = Mock()
        mock_st.code = Mock()
        mock_st.json = Mock()
        mock_st.column_config = Mock()
        mock_st.column_config.TextColumn = Mock()
        mock_st.column_config.NumberColumn = Mock()

        # Mock components
        with patch("src.ui.streamlit_app.components") as mock_components:
            mock_components.html = Mock()
            yield mock_st


class TestMakeJsonSafe:
    """Test make_json_safe() utility function."""

    def test_primitives(self):
        """Test JSON-safe primitives pass through."""
        from src.ui.streamlit_app import make_json_safe

        assert make_json_safe(None) is None
        assert make_json_safe(True) is True
        assert make_json_safe(False) is False
        assert make_json_safe(42) == 42
        assert make_json_safe(3.14) == 3.14
        assert make_json_safe("hello") == "hello"

    def test_list_recursion(self):
        """Test list conversion."""
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe([1, "two", 3.0, None, True])
        assert result == [1, "two", 3.0, None, True]

    def test_tuple_recursion(self):
        """Test tuple conversion to list."""
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe((1, 2, 3))
        assert result == [1, 2, 3]

    def test_dict_recursion(self):
        """Test dict conversion."""
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe({"a": 1, "b": "two", "c": [3, 4]})
        assert result == {"a": 1, "b": "two", "c": [3, 4]}

    def test_nested_structures(self):
        """Test deeply nested structures."""
        from src.ui.streamlit_app import make_json_safe

        data = {
            "users": [
                {"name": "Alice", "scores": [1, 2, 3]},
                {"name": "Bob", "scores": [4, 5, 6]},
            ]
        }
        result = make_json_safe(data)
        assert result == data

    def test_max_depth_limit(self):
        """Test max_depth prevents infinite recursion."""
        from src.ui.streamlit_app import make_json_safe

        # Create nested structure beyond max depth
        deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": {"j": "too deep"}}}}}}}}}}
        result = make_json_safe(deep, max_depth=5)
        # Should have "<max depth reached>" somewhere
        assert "<max depth reached>" in str(result)

    def test_non_serializable_object(self):
        """Test non-serializable objects get converted to strings."""
        from src.ui.streamlit_app import make_json_safe

        class CustomObj:
            def __repr__(self):
                return "CustomObj()"

        obj = CustomObj()
        result = make_json_safe(obj)
        assert result == "CustomObj()"

    def test_non_string_dict_keys(self):
        """Test dict keys get converted to strings."""
        from src.ui.streamlit_app import make_json_safe

        data = {1: "one", 2: "two"}
        result = make_json_safe(data)
        assert result == {"1": "one", "2": "two"}

    def test_exception_in_str_conversion(self):
        """Test fallback when str() fails."""
        from src.ui.streamlit_app import make_json_safe

        class BrokenObj:
            def __str__(self):
                raise ValueError("Cannot convert to string")

        obj = BrokenObj()
        result = make_json_safe(obj)
        assert "BrokenObj object" in result


class TestUIConfig:
    """Test UIConfig class."""

    def test_simple_mode_features(self):
        """Test simple mode has all features disabled."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.config.ui.ui_config") as mock_config:
            mock_config.mode = UIMode.SIMPLE
            config = UIConfig()

            assert config.mode == UIMode.SIMPLE
            assert config.features["streaming"] is False
            assert config.features["memory"] is False
            assert config.features["mcp"] is False
            assert config.features["tools_visibility"] is False
            assert config.features["metrics"] is False

    def test_standard_mode_features(self):
        """Test standard mode has streaming and tools."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.config.ui.ui_config") as mock_config:
            mock_config.mode = UIMode.STANDARD
            config = UIConfig()

            assert config.mode == UIMode.STANDARD
            assert config.features["streaming"] is True
            assert config.features["memory"] is False
            assert config.features["mcp"] is False
            assert config.features["tools_visibility"] is True
            assert config.features["metrics"] is False

    def test_advanced_mode_features(self):
        """Test advanced mode has all features enabled."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.config.ui.ui_config") as mock_config:
            mock_config.mode = UIMode.ADVANCED
            config = UIConfig()

            assert config.mode == UIMode.ADVANCED
            assert config.features["streaming"] is True
            assert config.features["memory"] is True
            assert config.features["mcp"] is True
            assert config.features["tools_visibility"] is True
            assert config.features["metrics"] is True

    def test_get_handler_simple(self):
        """Test get_handler returns SimpleHandler for simple mode."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.config.ui.ui_config") as mock_config:
            with patch("src.ui.streamlit_app.SimpleHandler") as mock_handler:
                mock_config.mode = UIMode.SIMPLE
                config = UIConfig()
                handler = config.get_handler()

                mock_handler.assert_called_once()
                call_args = mock_handler.call_args[0][0]
                assert call_args["enable_memory"] is False
                assert call_args["enable_mcp"] is False

    def test_get_handler_standard(self):
        """Test get_handler returns StreamingHandler for standard mode."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.config.ui.ui_config") as mock_config:
            with patch("src.ui.streamlit_app.StreamingHandler") as mock_handler:
                mock_config.mode = UIMode.STANDARD
                config = UIConfig()
                handler = config.get_handler()

                mock_handler.assert_called_once()

    def test_get_handler_advanced(self):
        """Test get_handler returns MCPHandler for advanced mode."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.config.ui.ui_config") as mock_config:
            with patch("src.ui.streamlit_app.MCPHandler") as mock_handler:
                mock_config.mode = UIMode.ADVANCED
                config = UIConfig()
                handler = config.get_handler()

                mock_handler.assert_called_once()


class TestDisplayMessagePart:
    """Test display_message_part() function."""

    def test_user_prompt_display(self, mock_streamlit):
        """Test user-prompt message display."""
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_streamlit.session_state.config = mock_config

        part = Mock(part_kind="user-prompt", content="Hello!")
        display_message_part(part)

        mock_streamlit.chat_message.assert_called_with("user")
        mock_streamlit.markdown.assert_called()

    def test_text_display(self, mock_streamlit):
        """Test text message display."""
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_streamlit.session_state.config = mock_config

        part = Mock(part_kind="text", content="Response text")
        display_message_part(part)

        mock_streamlit.chat_message.assert_called_with("assistant")

    def test_tool_call_with_dict_args(self, mock_streamlit):
        """Test tool-call display with dict args."""
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_streamlit.session_state.config = mock_config

        part = Mock(
            part_kind="tool-call",
            tool_name="test_tool",
            args={"param": "value"}
        )
        display_message_part(part)

        mock_streamlit.expander.assert_called()

    def test_tool_call_with_json_string_args(self, mock_streamlit):
        """Test tool-call display with JSON string args."""
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_streamlit.session_state.config = mock_config

        part = Mock(
            part_kind="tool-call",
            tool_name="test_tool",
            args='{"param": "value"}'
        )
        display_message_part(part)

        mock_streamlit.expander.assert_called()

    def test_tool_call_with_empty_args(self, mock_streamlit):
        """Test tool-call display with empty args."""
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_streamlit.session_state.config = mock_config

        part = Mock(
            part_kind="tool-call",
            tool_name="test_tool",
            args=""
        )
        display_message_part(part)

    def test_tool_call_with_invalid_json(self, mock_streamlit):
        """Test tool-call display with invalid JSON string."""
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_streamlit.session_state.config = mock_config

        part = Mock(
            part_kind="tool-call",
            tool_name="test_tool",
            args="not valid json"
        )
        display_message_part(part)

        # Should fall back to code display
        mock_streamlit.code.assert_called()

    def test_tool_return_display(self, mock_streamlit):
        """Test tool-return display."""
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_streamlit.session_state.config = mock_config

        part = Mock(
            part_kind="tool-return",
            tool_name="test_tool",
            content="result data"
        )
        display_message_part(part)

        mock_streamlit.expander.assert_called()

    def test_tool_return_long_content_truncated(self, mock_streamlit):
        """Test tool-return with long content gets truncated."""
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": True}
        mock_streamlit.session_state.config = mock_config

        long_content = "x" * 3000
        part = Mock(
            part_kind="tool-return",
            tool_name="test_tool",
            content=long_content
        )
        display_message_part(part)

        # Should show truncation message
        mock_streamlit.caption.assert_called()

    def test_tools_not_visible(self, mock_streamlit):
        """Test tool messages not displayed when tools_visibility is False."""
        from src.ui.streamlit_app import display_message_part

        mock_config = Mock()
        mock_config.features = {"tools_visibility": False}
        mock_streamlit.session_state.config = mock_config

        part = Mock(part_kind="tool-call", tool_name="test_tool", args={})
        display_message_part(part)

        # Should not call expander
        mock_streamlit.expander.assert_not_called()


class TestInitializeSessionState:
    """Test initialize_session_state() function."""

    def test_first_initialization(self, mock_streamlit):
        """Test first session state initialization with loading screen."""
        from src.ui.streamlit_app import initialize_session_state

        with patch("src.ui.streamlit_app.UIConfig") as mock_ui_config_class:
            with patch("time.sleep"):  # Speed up test
                mock_config = Mock()
                mock_config.mode = Mock(value="advanced")
                mock_config.features = {"streaming": True, "memory": True}
                mock_ui_config_class.return_value = mock_config

                mock_handler = Mock()
                mock_handler.initialize = Mock()
                mock_config.get_handler = Mock(return_value=mock_handler)

                # Empty session state (first init)
                mock_streamlit.session_state = {}

                initialize_session_state()

                # Should create all session state items
                assert "messages" in mock_streamlit.session_state
                assert "config" in mock_streamlit.session_state
                assert "handler" in mock_streamlit.session_state
                assert "theme" in mock_streamlit.session_state
                assert "current_page" in mock_streamlit.session_state

                # Should initialize handler
                mock_handler.initialize.assert_called_once()

    def test_subsequent_initialization(self, mock_streamlit):
        """Test subsequent session state initialization (fast path)."""
        from src.ui.streamlit_app import initialize_session_state

        # Pre-populate session state
        mock_handler = Mock()
        mock_config = Mock()
        mock_config.mode = Mock(value="simple")

        mock_streamlit.session_state = {
            "handler": mock_handler,
            "config": mock_config,
            "messages": [],
            "theme": "light",
            "current_page": "Chat",
        }

        initialize_session_state()

        # Should not re-initialize (handler should be same object)
        assert mock_streamlit.session_state["handler"] is mock_handler

    def test_partial_session_state(self, mock_streamlit):
        """Test initialization with partial session state."""
        from src.ui.streamlit_app import initialize_session_state

        with patch("src.ui.streamlit_app.UIConfig") as mock_ui_config_class:
            mock_config = Mock()
            mock_config.mode = Mock(value="standard")
            mock_config.features = {}
            mock_ui_config_class.return_value = mock_config

            # Some state exists but not all
            mock_streamlit.session_state = {
                "messages": [{"role": "user", "content": "hi"}],
            }

            initialize_session_state()

            # Should fill in missing state
            assert "config" in mock_streamlit.session_state
            assert "theme" in mock_streamlit.session_state


class TestExportConversation:
    """Test export_conversation() function."""

    def test_export_empty_conversation(self, mock_streamlit):
        """Test exporting empty conversation."""
        from src.ui.streamlit_app import export_conversation

        mock_config = Mock()
        mock_config.mode = Mock(value="simple")
        mock_streamlit.session_state = {
            "messages": [],
            "config": mock_config,
        }

        export_conversation()

        # Should create download button
        mock_streamlit.download_button.assert_called_once()
        call_kwargs = mock_streamlit.download_button.call_args[1]
        exported_data = json.loads(call_kwargs["data"])

        assert exported_data["mode"] == "simple"
        assert exported_data["messages"] == []

    def test_export_conversation_with_messages(self, mock_streamlit):
        """Test exporting conversation with user/assistant messages."""
        from src.ui.streamlit_app import export_conversation

        mock_config = Mock()
        mock_config.mode = Mock(value="advanced")

        # Create mock messages
        user_part = UserPromptPart(content="Hello")
        assistant_part = TextPart(content="Hi there!")

        msg1 = ModelRequest(parts=[user_part])
        msg2 = ModelResponse(parts=[assistant_part])

        mock_streamlit.session_state = {
            "messages": [msg1, msg2],
            "config": mock_config,
        }

        export_conversation()

        call_kwargs = mock_streamlit.download_button.call_args[1]
        exported_data = json.loads(call_kwargs["data"])

        assert len(exported_data["messages"]) == 2
        assert exported_data["messages"][0]["role"] == "user"
        assert exported_data["messages"][0]["content"] == "Hello"
        assert exported_data["messages"][1]["role"] == "assistant"
        assert exported_data["messages"][1]["content"] == "Hi there!"

    def test_export_filters_tool_messages(self, mock_streamlit):
        """Test export only includes user-prompt and text parts."""
        from src.ui.streamlit_app import export_conversation

        mock_config = Mock()
        mock_config.mode = Mock(value="standard")

        # Create messages with tool calls (should be filtered)
        user_part = UserPromptPart(content="Search for X")
        tool_call_part = ToolCallPart(
            tool_name="search",
            args={"query": "X"},
            tool_call_id="123"
        )
        tool_return_part = ToolReturnPart(
            tool_name="search",
            content="Results",
            tool_call_id="123"
        )
        text_part = TextPart(content="Here are the results")

        msg = ModelResponse(parts=[user_part, tool_call_part, tool_return_part, text_part])

        mock_streamlit.session_state = {
            "messages": [msg],
            "config": mock_config,
        }

        export_conversation()

        call_kwargs = mock_streamlit.download_button.call_args[1]
        exported_data = json.loads(call_kwargs["data"])

        # Should only export user-prompt and text parts
        assert len(exported_data["messages"]) == 2


@pytest.mark.asyncio
class TestHandleUserInput:
    """Test handle_user_input() function."""

    async def test_non_streaming_mode(self, mock_streamlit):
        """Test non-streaming mode execution."""
        from src.ui.streamlit_app import handle_user_input

        mock_handler = AsyncMock()
        mock_handler.run_agent = AsyncMock(return_value={
            "response": "Test response",
            "new_messages": []
        })

        mock_config = Mock()
        mock_config.mode = Mock(value="simple")
        mock_config.features = {"streaming": False}

        mock_streamlit.session_state = {
            "handler": mock_handler,
            "config": mock_config,
            "messages": [],
        }

        await handle_user_input("Test input")

        # Should call handler
        mock_handler.run_agent.assert_called_once()

        # Should display response
        mock_streamlit.markdown.assert_called()

    async def test_streaming_mode_text_only(self, mock_streamlit):
        """Test streaming mode with text chunks."""
        from src.ui.streamlit_app import handle_user_input

        async def mock_stream():
            yield {"type": "start", "content": "Hello"}
            yield {"type": "delta", "content": " world"}
            yield {"type": "delta", "content": "!"}
            yield {"type": "complete", "new_messages": []}

        mock_handler = Mock()
        mock_handler.run_agent = Mock(return_value=mock_stream())

        mock_config = Mock()
        mock_config.features = {"streaming": True, "tools_visibility": False}

        mock_streamlit.session_state = {
            "handler": mock_handler,
            "config": mock_config,
            "messages": [],
        }

        await handle_user_input("Test")

        # Should process all chunks
        assert len(mock_streamlit.session_state["messages"]) == 0  # complete added empty list

    async def test_streaming_mode_with_tool_calls(self, mock_streamlit):
        """Test streaming mode with tool calls and returns."""
        from src.ui.streamlit_app import handle_user_input

        async def mock_stream():
            yield {"type": "start", "content": "Searching"}
            yield {
                "type": "tool-call",
                "tool_name": "search",
                "args": {"query": "test"}
            }
            yield {
                "type": "tool-return",
                "tool_name": "search",
                "content": "Results"
            }
            yield {"type": "delta", "content": "..."}
            yield {"type": "complete", "new_messages": []}

        mock_handler = Mock()
        mock_handler.run_agent = Mock(return_value=mock_stream())

        mock_config = Mock()
        mock_config.features = {"streaming": True, "tools_visibility": True}

        mock_streamlit.session_state = {
            "handler": mock_handler,
            "config": mock_config,
            "messages": [],
        }

        await handle_user_input("Search for test")

        # Should show tool UI
        mock_streamlit.expander.assert_called()

    async def test_streaming_mode_complete_with_tool_returns(self, mock_streamlit):
        """Test streaming complete event extracts tool returns from messages."""
        from src.ui.streamlit_app import handle_user_input

        tool_return_part = ToolReturnPart(
            tool_name="search",
            content="Final results",
            tool_call_id="123"
        )
        msg = ModelResponse(parts=[tool_return_part])

        async def mock_stream():
            yield {"type": "start", "content": "Done"}
            yield {"type": "complete", "new_messages": [msg]}

        mock_handler = Mock()
        mock_handler.run_agent = Mock(return_value=mock_stream())

        mock_config = Mock()
        mock_config.features = {"streaming": True, "tools_visibility": True}

        mock_streamlit.session_state = {
            "handler": mock_handler,
            "config": mock_config,
            "messages": [],
        }

        await handle_user_input("Test")

        # Should add messages to session state
        assert len(mock_streamlit.session_state["messages"]) == 1


@pytest.mark.asyncio
class TestRenderDashboard:
    """Test render_dashboard() and _render_dashboard_content() functions."""

    async def test_render_dashboard_initialization(self, mock_streamlit):
        """Test dashboard initialization with loading screen."""
        from src.ui.streamlit_app import render_dashboard

        with patch("src.ui.streamlit_app.get_connection_manager") as mock_get_conn:
            with patch("src.ui.streamlit_app.DashboardHandler") as mock_handler_class:
                with patch("src.ui.streamlit_app._render_dashboard_content") as mock_render:
                    mock_conn = AsyncMock()
                    mock_get_conn.return_value = mock_conn

                    mock_handler = Mock()
                    mock_handler_class.return_value = mock_handler

                    await render_dashboard()

                    # Should initialize connection manager and handler
                    mock_get_conn.assert_called_once()
                    mock_handler_class.assert_called_once_with(mock_conn)

                    # Should render dashboard content
                    mock_render.assert_called_once_with(mock_handler)

    async def test_render_dashboard_error_handling(self, mock_streamlit):
        """Test dashboard error handling."""
        from src.ui.streamlit_app import render_dashboard

        with patch("src.ui.streamlit_app.get_connection_manager") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")

            await render_dashboard()

            # Should show error
            mock_streamlit.error.assert_called()
            mock_streamlit.info.assert_called()

    async def test_render_dashboard_content_search_analytics(self, mock_streamlit):
        """Test dashboard content renders search analytics."""
        from src.ui.streamlit_app import _render_dashboard_content

        mock_handler = AsyncMock()
        mock_handler.get_search_metrics = AsyncMock(return_value={
            "total_searches": 100,
            "avg_latency_ms": 150.5,
            "most_used_strategy": "HYBRID",
            "boost_rate": 0.25,
            "strategy_distribution": {"HYBRID": 50, "VECTOR_HEAVY": 30, "GRAPH_HEAVY": 20}
        })
        mock_handler.get_time_series_data = AsyncMock(return_value=[])
        mock_handler.get_intent_distribution = AsyncMock(return_value={})
        mock_handler.get_graph_data = AsyncMock(return_value={"entities": [], "relationships": []})
        mock_handler.get_top_entities = AsyncMock(return_value=[])
        mock_handler.get_performance_metrics = AsyncMock(return_value={})
        mock_handler.get_tool_usage_metrics = AsyncMock(return_value={"total_calls": 0})
        mock_handler.get_agent_interaction_metrics = AsyncMock(return_value={"total_interactions": 0})
        mock_handler.refresh_materialized_views = AsyncMock(return_value=True)
        mock_handler.clear_cache = Mock()

        await _render_dashboard_content(mock_handler)

        # Should render metrics
        mock_streamlit.metric.assert_called()
        mock_handler.get_search_metrics.assert_called_once()

    async def test_render_dashboard_content_refresh_button(self, mock_streamlit):
        """Test dashboard refresh button."""
        from src.ui.streamlit_app import _render_dashboard_content

        mock_handler = AsyncMock()
        mock_handler.get_search_metrics = AsyncMock(return_value={})
        mock_handler.get_time_series_data = AsyncMock(return_value=[])
        mock_handler.get_intent_distribution = AsyncMock(return_value={})
        mock_handler.get_graph_data = AsyncMock(return_value={"entities": [], "relationships": []})
        mock_handler.get_top_entities = AsyncMock(return_value=[])
        mock_handler.get_performance_metrics = AsyncMock(return_value={})
        mock_handler.get_tool_usage_metrics = AsyncMock(return_value={"total_calls": 0})
        mock_handler.get_agent_interaction_metrics = AsyncMock(return_value={"total_interactions": 0})
        mock_handler.clear_cache = Mock()

        # Simulate refresh button click
        mock_streamlit.button = Mock(side_effect=[True, False])  # First button (refresh) clicked

        await _render_dashboard_content(mock_handler)

        # Should clear cache and rerun
        mock_handler.clear_cache.assert_called_once()
        mock_streamlit.rerun.assert_called()

    async def test_render_dashboard_content_graph_visualization(self, mock_streamlit):
        """Test knowledge graph visualization."""
        from src.ui.streamlit_app import _render_dashboard_content

        mock_handler = AsyncMock()
        mock_handler.get_search_metrics = AsyncMock(return_value={})
        mock_handler.get_time_series_data = AsyncMock(return_value=[])
        mock_handler.get_intent_distribution = AsyncMock(return_value={})
        mock_handler.get_graph_data = AsyncMock(return_value={
            "entities": [
                {"id": "1", "name": "Entity1", "type": "person"},
                {"id": "2", "name": "Entity2", "type": "company"}
            ],
            "relationships": [
                {"source": "1", "target": "2", "type": "works_at"}
            ]
        })
        mock_handler.get_top_entities = AsyncMock(return_value=[])
        mock_handler.get_performance_metrics = AsyncMock(return_value={})
        mock_handler.get_tool_usage_metrics = AsyncMock(return_value={"total_calls": 0})
        mock_handler.get_agent_interaction_metrics = AsyncMock(return_value={"total_interactions": 0})

        mock_streamlit.slider = Mock(return_value=100)
        mock_streamlit.selectbox = Mock(return_value="force_directed")

        with patch("src.ui.streamlit_app.create_pyvis_graph") as mock_create_graph:
            mock_net = Mock()
            mock_net.save_graph = Mock()
            mock_create_graph.return_value = mock_net

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".html") as tmp:
                tmp.write("<html>test</html>")
                tmp_path = tmp.name

            with patch("builtins.open", mock.mock_open(read_data="<html>test</html>")):
                with patch("pathlib.Path.unlink"):
                    await _render_dashboard_content(mock_handler)

            # Should create graph
            mock_create_graph.assert_called_once()

    async def test_render_dashboard_content_entity_timeline(self, mock_streamlit):
        """Test entity timeline display."""
        from src.ui.streamlit_app import _render_dashboard_content

        mock_handler = AsyncMock()
        mock_handler.get_search_metrics = AsyncMock(return_value={})
        mock_handler.get_time_series_data = AsyncMock(return_value=[])
        mock_handler.get_intent_distribution = AsyncMock(return_value={})
        mock_handler.get_graph_data = AsyncMock(return_value={"entities": [], "relationships": []})
        mock_handler.get_top_entities = AsyncMock(return_value=[
            {"id": "1", "name": "Entity1", "type": "person", "relationship_count": 5, "chunk_count": 10}
        ])
        mock_handler.get_entity_timeline = AsyncMock(return_value=[
            {"description": "Event 1", "valid_from": "2024-01-01"}
        ])
        mock_handler.get_performance_metrics = AsyncMock(return_value={})
        mock_handler.get_tool_usage_metrics = AsyncMock(return_value={"total_calls": 0})
        mock_handler.get_agent_interaction_metrics = AsyncMock(return_value={"total_interactions": 0})

        # Simulate entity selection
        mock_streamlit.selectbox = Mock(side_effect=["force_directed", "Entity1"])

        await _render_dashboard_content(mock_handler)

        # Should fetch timeline
        mock_handler.get_entity_timeline.assert_called_once_with("1")


@pytest.mark.asyncio
class TestMain:
    """Test main() function."""

    async def test_main_chat_page(self, mock_streamlit):
        """Test main() renders chat page."""
        from src.ui.streamlit_app import main

        mock_config = Mock()
        mock_config.mode = UIMode.ADVANCED
        mock_config.features = {}

        mock_handler = Mock()

        mock_streamlit.session_state = {
            "config": mock_config,
            "handler": mock_handler,
            "messages": [],
            "current_page": "Chat",
        }

        # No user input
        mock_streamlit.chat_input = Mock(return_value=None)

        with patch("src.ui.streamlit_app.initialize_session_state"):
            with patch("src.ui.streamlit_app.render_sidebar"):
                await main()

        # Should set page config
        mock_streamlit.set_page_config.assert_called_once()

        # Should show title
        mock_streamlit.title.assert_called()

    async def test_main_dashboard_page(self, mock_streamlit):
        """Test main() renders dashboard page."""
        from src.ui.streamlit_app import main

        mock_config = Mock()
        mock_config.mode = UIMode.ADVANCED

        mock_streamlit.session_state = {
            "config": mock_config,
            "current_page": "Dashboard",
        }

        with patch("src.ui.streamlit_app.initialize_session_state"):
            with patch("src.ui.streamlit_app.render_sidebar"):
                with patch("src.ui.streamlit_app.render_dashboard") as mock_render_dash:
                    await main()

        # Should render dashboard
        mock_render_dash.assert_called_once()

    async def test_main_dashboard_in_simple_mode(self, mock_streamlit):
        """Test dashboard warning in simple mode."""
        from src.ui.streamlit_app import main

        mock_config = Mock()
        mock_config.mode = UIMode.SIMPLE

        mock_streamlit.session_state = {
            "config": mock_config,
            "current_page": "Dashboard",
        }

        with patch("src.ui.streamlit_app.initialize_session_state"):
            await main()

        # Should show warning
        mock_streamlit.warning.assert_called()
        mock_streamlit.info.assert_called()

    async def test_main_with_user_input(self, mock_streamlit):
        """Test main() handles user input."""
        from src.ui.streamlit_app import main

        mock_config = Mock()
        mock_config.mode = UIMode.SIMPLE
        mock_config.features = {"streaming": False}

        mock_handler = AsyncMock()
        mock_handler.run_agent = AsyncMock(return_value={
            "response": "Response",
            "new_messages": []
        })

        mock_streamlit.session_state = {
            "config": mock_config,
            "handler": mock_handler,
            "messages": [],
            "current_page": "Chat",
        }

        # Simulate user input
        mock_streamlit.chat_input = Mock(return_value="Test input")

        with patch("src.ui.streamlit_app.initialize_session_state"):
            with patch("src.ui.streamlit_app.handle_user_input") as mock_handle:
                await main()

        # Should handle input
        mock_handle.assert_called_once_with("Test input")


class TestRenderSidebar:
    """Test render_sidebar() function."""

    def test_render_sidebar_navigation(self, mock_streamlit):
        """Test sidebar navigation between Chat and Dashboard."""
        from src.ui.streamlit_app import render_sidebar

        mock_config = Mock()
        mock_config.mode = UIMode.STANDARD
        mock_config.features = {"metrics": False}

        mock_handler = Mock()
        mock_handler.deps = Mock()
        mock_handler.deps.supabase = Mock()
        mock_handler.deps.embedding_client = Mock()

        mock_streamlit.session_state = {
            "config": mock_config,
            "handler": mock_handler,
            "current_page": "Chat",
            "messages": [],
        }

        # Simulate radio button selection
        mock_streamlit.radio = Mock(side_effect=["💬 Chat", UIMode.STANDARD])
        mock_streamlit.button = Mock(return_value=False)

        with patch("src.ui.streamlit_app.render_upload_section"):
            with mock_streamlit.sidebar:
                render_sidebar()

        # Should not rerun (same page)
        mock_streamlit.rerun.assert_not_called()

    def test_render_sidebar_mode_change(self, mock_streamlit):
        """Test sidebar mode change triggers rerun."""
        from src.ui.streamlit_app import render_sidebar

        mock_config = Mock()
        mock_config.mode = UIMode.SIMPLE
        mock_config.features = {}

        mock_handler = Mock()

        mock_streamlit.session_state = {
            "config": mock_config,
            "handler": mock_handler,
            "current_page": "Chat",
            "messages": [],
        }

        # Simulate mode change
        mock_streamlit.radio = Mock(return_value=UIMode.STANDARD)
        mock_streamlit.button = Mock(return_value=False)

        with patch("src.ui.streamlit_app.UIConfig") as mock_ui_config:
            mock_new_config = Mock()
            mock_new_config.features = {"streaming": True}
            mock_ui_config._get_features_for_mode = Mock(return_value={"streaming": True})

            mock_new_handler = Mock()
            mock_new_handler.initialize = Mock()
            mock_config.get_handler = Mock(return_value=mock_new_handler)

            with patch("src.ui.streamlit_app.render_upload_section"):
                with mock_streamlit.sidebar:
                    render_sidebar()

        # Should trigger rerun
        mock_streamlit.rerun.assert_called()

    def test_render_sidebar_clear_chat(self, mock_streamlit):
        """Test sidebar clear chat button."""
        from src.ui.streamlit_app import render_sidebar

        mock_config = Mock()
        mock_config.mode = UIMode.ADVANCED
        mock_config.features = {"metrics": False}

        mock_handler = Mock()
        mock_handler.deps = Mock()
        mock_handler.deps.supabase = Mock()
        mock_handler.deps.embedding_client = Mock()

        mock_streamlit.session_state = {
            "config": mock_config,
            "handler": mock_handler,
            "current_page": "Chat",
            "messages": [{"role": "user", "content": "test"}],
        }

        # Simulate clear button click
        def button_side_effect(label, *args, **kwargs):
            if "Clear Chat" in label:
                return True
            return False

        mock_streamlit.button = Mock(side_effect=button_side_effect)
        mock_streamlit.radio = Mock(side_effect=[UIMode.ADVANCED])

        with patch("src.ui.streamlit_app.render_upload_section"):
            with mock_streamlit.sidebar:
                render_sidebar()

        # Should clear messages
        assert mock_streamlit.session_state["messages"] == []
        mock_streamlit.rerun.assert_called()

    def test_render_sidebar_metrics(self, mock_streamlit):
        """Test sidebar metrics display."""
        from src.ui.streamlit_app import render_sidebar

        user_part = UserPromptPart(content="Hello")
        text_part = TextPart(content="Hi")
        msg1 = ModelRequest(parts=[user_part])
        msg2 = ModelResponse(parts=[text_part])

        mock_config = Mock()
        mock_config.mode = UIMode.ADVANCED
        mock_config.features = {"metrics": True}

        mock_handler = Mock()
        mock_handler.deps = Mock()
        mock_handler.deps.supabase = Mock()
        mock_handler.deps.embedding_client = Mock()
        mock_handler.memory_client = Mock()  # Memory active

        mock_streamlit.session_state = {
            "config": mock_config,
            "handler": mock_handler,
            "current_page": "Chat",
            "messages": [msg1, msg2],
        }

        mock_streamlit.radio = Mock(return_value=UIMode.ADVANCED)
        mock_streamlit.button = Mock(return_value=False)
        mock_streamlit.container = Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock()))

        with patch("src.ui.streamlit_app.render_upload_section"):
            with mock_streamlit.sidebar:
                render_sidebar()

        # Should display metrics
        mock_streamlit.metric.assert_called()
