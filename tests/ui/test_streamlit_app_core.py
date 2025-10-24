"""
Comprehensive tests for streamlit_app core functionality.

Tests JSON serialization, UI configuration, mode management, and message display.
Target: 70%+ coverage of streamlit_app.py
"""

import json
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from src.config import UIMode


class TestMakeJsonSafe:
    """Test make_json_safe utility function."""

    def test_primitives_unchanged(self):
        """Test primitive types remain unchanged."""
        from src.ui.streamlit_app import make_json_safe

        assert make_json_safe(None) is None
        assert make_json_safe(True) is True
        assert make_json_safe(False) is False
        assert make_json_safe(42) == 42
        assert make_json_safe(3.14) == 3.14
        assert make_json_safe("hello") == "hello"

    def test_list_conversion(self):
        """Test list conversion."""
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe([1, "two", 3.0, True, None])
        assert result == [1, "two", 3.0, True, None]
        assert isinstance(result, list)

    def test_tuple_conversion(self):
        """Test tuple conversion to list."""
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe((1, 2, 3))
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_dict_conversion(self):
        """Test dict conversion."""
        from src.ui.streamlit_app import make_json_safe

        result = make_json_safe({"a": 1, "b": "two", "c": 3.0})
        assert result == {"a": 1, "b": "two", "c": 3.0}
        assert isinstance(result, dict)

    def test_nested_structures(self):
        """Test nested data structures."""
        from src.ui.streamlit_app import make_json_safe

        nested = {
            "list": [1, 2, {"inner": "value"}],
            "dict": {"nested": [3, 4, 5]},
            "tuple": (6, 7, 8),
        }

        result = make_json_safe(nested)
        assert result["list"] == [1, 2, {"inner": "value"}]
        assert result["dict"] == {"nested": [3, 4, 5]}
        assert result["tuple"] == [6, 7, 8]

    def test_max_depth_limit(self):
        """Test max depth recursion limit."""
        from src.ui.streamlit_app import make_json_safe

        # Create deeply nested structure
        deep = {"level": 1}
        current = deep
        for i in range(15):
            current["nested"] = {"level": i + 2}
            current = current["nested"]

        result = make_json_safe(deep, max_depth=5)
        # Should stop at max_depth
        assert "<max depth reached>" in str(result)

    def test_non_serializable_object(self):
        """Test non-serializable object conversion."""
        from src.ui.streamlit_app import make_json_safe

        class CustomObject:
            def __init__(self):
                self.value = 42

        obj = CustomObject()
        result = make_json_safe(obj)
        # Should convert to string
        assert isinstance(result, str)

    def test_uuid_conversion(self):
        """Test UUID conversion."""
        from src.ui.streamlit_app import make_json_safe

        uid = uuid4()
        result = make_json_safe(uid)
        # UUIDs should be converted to string
        assert isinstance(result, str)
        assert str(uid) == result

    def test_complex_mixed_types(self):
        """Test complex mixed types."""
        from src.ui.streamlit_app import make_json_safe

        class NonSerializable:
            pass

        data = {
            "str": "hello",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "tuple": (4, 5, 6),
            "nested_dict": {"inner": "value"},
            "non_serializable": NonSerializable(),
        }

        result = make_json_safe(data)
        assert result["str"] == "hello"
        assert result["int"] == 42
        assert result["list"] == [1, 2, 3]
        assert result["tuple"] == [4, 5, 6]
        assert isinstance(result["non_serializable"], str)

    def test_json_serialization_after_conversion(self):
        """Test that result is actually JSON serializable."""
        from src.ui.streamlit_app import make_json_safe

        class Unserializable:
            def __init__(self):
                self.data = "test"

        data = {"obj": Unserializable(), "list": [1, 2, Unserializable()]}

        result = make_json_safe(data)
        # Should be able to serialize to JSON
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestUIConfig:
    """Test UIConfig class."""

    def test_simple_mode_features(self):
        """Test SIMPLE mode feature flags."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config.mode", UIMode.SIMPLE):
            config = UIConfig()
            assert config.mode == UIMode.SIMPLE
            assert config.features["streaming"] is False
            assert config.features["memory"] is False
            assert config.features["mcp"] is False
            assert config.features["tools_visibility"] is False
            assert config.features["metrics"] is False

    def test_standard_mode_features(self):
        """Test STANDARD mode feature flags."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config.mode", UIMode.STANDARD):
            config = UIConfig()
            assert config.mode == UIMode.STANDARD
            assert config.features["streaming"] is True
            assert config.features["memory"] is False
            assert config.features["mcp"] is False
            assert config.features["tools_visibility"] is True
            assert config.features["metrics"] is False

    def test_advanced_mode_features(self):
        """Test ADVANCED mode feature flags."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config.mode", UIMode.ADVANCED):
            config = UIConfig()
            assert config.mode == UIMode.ADVANCED
            assert config.features["streaming"] is True
            assert config.features["memory"] is True
            assert config.features["mcp"] is True
            assert config.features["tools_visibility"] is True
            assert config.features["metrics"] is True

    def test_get_handler_simple_mode(self):
        """Test get_handler returns SimpleHandler for SIMPLE mode."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config.mode", UIMode.SIMPLE):
            with patch("src.ui.streamlit_app.SimpleHandler") as mock_handler:
                config = UIConfig()
                handler = config.get_handler()

                mock_handler.assert_called_once()
                call_args = mock_handler.call_args[0][0]
                assert call_args["enable_memory"] is False
                assert call_args["enable_mcp"] is False

    def test_get_handler_standard_mode(self):
        """Test get_handler returns StreamingHandler for STANDARD mode."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config.mode", UIMode.STANDARD):
            with patch("src.ui.streamlit_app.StreamingHandler") as mock_handler:
                config = UIConfig()
                handler = config.get_handler()

                mock_handler.assert_called_once()
                call_args = mock_handler.call_args[0][0]
                assert call_args["enable_memory"] is False
                assert call_args["enable_mcp"] is False

    def test_get_handler_advanced_mode(self):
        """Test get_handler returns MCPHandler for ADVANCED mode."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config.mode", UIMode.ADVANCED):
            with patch("src.ui.streamlit_app.MCPHandler") as mock_handler:
                config = UIConfig()
                handler = config.get_handler()

                mock_handler.assert_called_once()
                call_args = mock_handler.call_args[0][0]
                assert call_args["enable_memory"] is True
                assert call_args["enable_mcp"] is True

    def test_handler_config_includes_user_id(self):
        """Test handler config includes user_id."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config.mode", UIMode.SIMPLE):
            with patch("src.ui.streamlit_app.SimpleHandler") as mock_handler:
                config = UIConfig()
                config.get_handler()

                call_args = mock_handler.call_args[0][0]
                assert call_args["user_id"] == "streamlit_user"

    def test_handler_config_includes_memory_limit(self):
        """Test handler config includes memory_limit."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.config.mode", UIMode.ADVANCED):
            with patch("src.ui.streamlit_app.MCPHandler") as mock_handler:
                config = UIConfig()
                config.get_handler()

                call_args = mock_handler.call_args[0][0]
                assert call_args["memory_limit"] == 3


class TestDisplayMessagePart:
    """Test display_message_part function."""

    @pytest.fixture
    def mock_streamlit(self):
        """Mock streamlit components."""
        with patch("src.ui.streamlit_app.st") as mock_st:
            # Setup mock session state
            mock_st.session_state = Mock()
            mock_st.session_state.config = Mock()
            mock_st.session_state.config.features = {"tools_visibility": True}

            # Setup mock chat_message context manager
            mock_chat = MagicMock()
            mock_st.chat_message.return_value.__enter__ = Mock(return_value=mock_chat)
            mock_st.chat_message.return_value.__exit__ = Mock(return_value=None)

            # Setup mock expander
            mock_expander = MagicMock()
            mock_st.expander.return_value.__enter__ = Mock(return_value=mock_expander)
            mock_st.expander.return_value.__exit__ = Mock(return_value=None)

            yield mock_st

    def test_display_user_prompt(self, mock_streamlit):
        """Test displaying user prompt."""
        from src.ui.streamlit_app import display_message_part

        part = Mock()
        part.part_kind = "user-prompt"
        part.content = "Hello, agent!"

        display_message_part(part)

        mock_streamlit.chat_message.assert_called_with("user")
        mock_streamlit.markdown.assert_called_with("Hello, agent!")

    def test_display_text_response(self, mock_streamlit):
        """Test displaying text response."""
        from src.ui.streamlit_app import display_message_part

        part = Mock()
        part.part_kind = "text"
        part.content = "Hello, user!"

        display_message_part(part)

        mock_streamlit.chat_message.assert_called_with("assistant")
        mock_streamlit.markdown.assert_called_with("Hello, user!")

    def test_display_tool_call_with_visibility(self, mock_streamlit):
        """Test displaying tool call when tools_visibility is True."""
        from src.ui.streamlit_app import display_message_part

        part = Mock()
        part.part_kind = "tool-call"
        part.tool_name = "search_web"
        part.args = Mock()
        part.args.model_dump.return_value = {"query": "test"}

        display_message_part(part)

        mock_streamlit.expander.assert_called_with("🔧 Tool: search_web")

    def test_display_tool_call_without_visibility(self, mock_streamlit):
        """Test tool call not displayed when tools_visibility is False."""
        from src.ui.streamlit_app import display_message_part

        mock_streamlit.session_state.config.features = {"tools_visibility": False}

        part = Mock()
        part.part_kind = "tool-call"
        part.tool_name = "search_web"

        display_message_part(part)

        # Expander should not be called
        mock_streamlit.expander.assert_not_called()

    def test_display_empty_content_skipped(self, mock_streamlit):
        """Test messages with empty content are skipped."""
        from src.ui.streamlit_app import display_message_part

        part = Mock()
        part.part_kind = "user-prompt"
        part.content = ""

        display_message_part(part)

        # Should not create chat message
        mock_streamlit.chat_message.assert_not_called()

    def test_display_tool_call_with_args(self, mock_streamlit):
        """Test tool call displays arguments."""
        from src.ui.streamlit_app import display_message_part

        part = Mock()
        part.part_kind = "tool-call"
        part.tool_name = "retrieve_documents"
        part.args = Mock()
        part.args.model_dump.return_value = {"query": "test query", "limit": 10}

        display_message_part(part)

        mock_streamlit.expander.assert_called_once()
        assert "retrieve_documents" in mock_streamlit.expander.call_args[0][0]


class TestModeSwitching:
    """Test UI mode switching functionality."""

    @pytest.fixture
    def mock_session_state(self):
        """Mock streamlit session state."""
        state = Mock()
        state.config = Mock()
        state.config.mode = UIMode.SIMPLE
        state.config.features = {
            "streaming": False,
            "memory": False,
            "mcp": False,
            "tools_visibility": False,
            "metrics": False,
        }
        state.handler = Mock()
        return state

    def test_mode_feature_mapping_consistency(self):
        """Test that mode feature mapping is consistent."""
        from src.ui.streamlit_app import UIConfig

        # Test all modes
        for mode in [UIMode.SIMPLE, UIMode.STANDARD, UIMode.ADVANCED]:
            with patch("src.ui.streamlit_app.config.mode", mode):
                config1 = UIConfig()
                config2 = UIConfig()

                # Features should be identical for same mode
                assert config1.features == config2.features

    def test_handler_type_matches_mode(self):
        """Test correct handler is returned for each mode."""
        from src.ui.streamlit_app import UIConfig

        with patch("src.ui.streamlit_app.SimpleHandler") as mock_simple:
            with patch("src.ui.streamlit_app.config.mode", UIMode.SIMPLE):
                UIConfig().get_handler()
                assert mock_simple.called

        with patch("src.ui.streamlit_app.StreamingHandler") as mock_streaming:
            with patch("src.ui.streamlit_app.config.mode", UIMode.STANDARD):
                UIConfig().get_handler()
                assert mock_streaming.called

        with patch("src.ui.streamlit_app.MCPHandler") as mock_mcp:
            with patch("src.ui.streamlit_app.config.mode", UIMode.ADVANCED):
                UIConfig().get_handler()
                assert mock_mcp.called
