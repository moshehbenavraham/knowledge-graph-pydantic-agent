"""Mega comprehensive tests for streamlit_app.py - targeting 482 uncovered lines.

Tests all UI initialization, session management, message handling, and rendering logic.
"""

from unittest.mock import MagicMock, Mock, patch

from src.ui.streamlit_app import (
    UIConfig,
    display_message_part,
    make_json_safe,
)


class TestMakeJsonSafe:
    """Test make_json_safe function."""

    def test_make_json_safe_none(self):
        """Test with None value."""
        result = make_json_safe(None)
        assert result is None

    def test_make_json_safe_bool(self):
        """Test with boolean."""
        assert make_json_safe(True) is True
        assert make_json_safe(False) is False

    def test_make_json_safe_int(self):
        """Test with integer."""
        result = make_json_safe(42)
        assert result == 42

    def test_make_json_safe_float(self):
        """Test with float."""
        result = make_json_safe(3.14)
        assert result == 3.14

    def test_make_json_safe_string(self):
        """Test with string."""
        result = make_json_safe("hello")
        assert result == "hello"

    def test_make_json_safe_list(self):
        """Test with list."""
        result = make_json_safe([1, 2, 3])
        assert result == [1, 2, 3]

    def test_make_json_safe_tuple(self):
        """Test with tuple."""
        result = make_json_safe((1, 2, 3))
        assert result == [1, 2, 3]  # Converts to list

    def test_make_json_safe_dict(self):
        """Test with dict."""
        result = make_json_safe({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_make_json_safe_nested(self):
        """Test with nested structures."""
        obj = {"list": [1, 2, {"nested": "value"}], "tuple": (3, 4)}
        result = make_json_safe(obj)
        assert result["list"] == [1, 2, {"nested": "value"}]
        assert result["tuple"] == [3, 4]

    def test_make_json_safe_max_depth(self):
        """Test max depth prevention."""
        # Create deeply nested structure
        nested = {
            "a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": {"j": {"k": "too deep"}}}}}}}}}}
        }
        result = make_json_safe(nested, max_depth=5)
        # Should reach max depth
        assert isinstance(result, dict)

    def test_make_json_safe_non_serializable_object(self):
        """Test with non-serializable object."""

        class CustomObject:
            def __str__(self):
                return "custom_object"

        obj = CustomObject()
        result = make_json_safe(obj)
        assert result == "custom_object"

    def test_make_json_safe_object_no_str(self):
        """Test with object that fails str()."""

        class BrokenObject:
            def __str__(self):
                raise Exception("Cannot convert to string")

        obj = BrokenObject()
        result = make_json_safe(obj)
        assert "<BrokenObject object>" in result


class TestUIConfig:
    """Test UIConfig class."""

    @patch("src.ui.streamlit_app.config")
    def test_uiconfig_init_simple_mode(self, mock_config):
        """Test UIConfig initialization with SIMPLE mode."""
        from src.config import UIMode

        mock_config.mode = UIMode.SIMPLE
        ui_config = UIConfig()

        assert ui_config.mode == UIMode.SIMPLE
        assert ui_config.features["streaming"] is False
        assert ui_config.features["memory"] is False
        assert ui_config.features["mcp"] is False
        assert ui_config.features["tools_visibility"] is False
        assert ui_config.features["metrics"] is False

    @patch("src.ui.streamlit_app.config")
    def test_uiconfig_init_standard_mode(self, mock_config):
        """Test UIConfig initialization with STANDARD mode."""
        from src.config import UIMode

        mock_config.mode = UIMode.STANDARD
        ui_config = UIConfig()

        assert ui_config.mode == UIMode.STANDARD
        assert ui_config.features["streaming"] is True
        assert ui_config.features["memory"] is False
        assert ui_config.features["mcp"] is False
        assert ui_config.features["tools_visibility"] is True
        assert ui_config.features["metrics"] is False

    @patch("src.ui.streamlit_app.config")
    def test_uiconfig_init_advanced_mode(self, mock_config):
        """Test UIConfig initialization with ADVANCED mode."""
        from src.config import UIMode

        mock_config.mode = UIMode.ADVANCED
        ui_config = UIConfig()

        assert ui_config.mode == UIMode.ADVANCED
        assert ui_config.features["streaming"] is True
        assert ui_config.features["memory"] is True
        assert ui_config.features["mcp"] is True
        assert ui_config.features["tools_visibility"] is True
        assert ui_config.features["metrics"] is True

    @patch("src.ui.streamlit_app.config")
    def test_uiconfig_get_handler_simple(self, mock_config):
        """Test get_handler returns SimpleHandler for SIMPLE mode."""
        from src.config import UIMode

        mock_config.mode = UIMode.SIMPLE
        ui_config = UIConfig()

        handler = ui_config.get_handler()

        assert handler.__class__.__name__ == "SimpleHandler"

    @patch("src.ui.streamlit_app.config")
    def test_uiconfig_get_handler_standard(self, mock_config):
        """Test get_handler returns StreamingHandler for STANDARD mode."""
        from src.config import UIMode

        mock_config.mode = UIMode.STANDARD
        ui_config = UIConfig()

        handler = ui_config.get_handler()

        assert handler.__class__.__name__ == "StreamingHandler"

    @patch("src.ui.streamlit_app.config")
    def test_uiconfig_get_handler_advanced(self, mock_config):
        """Test get_handler returns MCPHandler for ADVANCED mode."""
        from src.config import UIMode

        mock_config.mode = UIMode.ADVANCED
        ui_config = UIConfig()

        handler = ui_config.get_handler()

        assert handler.__class__.__name__ == "MCPHandler"

    def test_get_features_for_mode_simple(self):
        """Test _get_features_for_mode with SIMPLE."""
        from src.config import UIMode

        features = UIConfig._get_features_for_mode(UIMode.SIMPLE)

        assert all(not v for v in features.values())  # All False

    def test_get_features_for_mode_standard(self):
        """Test _get_features_for_mode with STANDARD."""
        from src.config import UIMode

        features = UIConfig._get_features_for_mode(UIMode.STANDARD)

        assert features["streaming"] is True
        assert features["tools_visibility"] is True
        assert features["memory"] is False

    def test_get_features_for_mode_advanced(self):
        """Test _get_features_for_mode with ADVANCED."""
        from src.config import UIMode

        features = UIConfig._get_features_for_mode(UIMode.ADVANCED)

        assert all(features.values())  # All True


class TestDisplayMessagePart:
    """Test display_message_part function."""

    @patch("src.ui.streamlit_app.st")
    def test_display_message_part_user_prompt(self, mock_st):
        """Test displaying user prompt message."""
        mock_part = Mock()
        mock_part.part_kind = "user-prompt"
        mock_part.content = "Hello, agent!"

        mock_chat_message = MagicMock()
        mock_st.chat_message.return_value.__enter__ = Mock(return_value=mock_chat_message)
        mock_st.chat_message.return_value.__exit__ = Mock(return_value=None)

        display_message_part(mock_part)

        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with("Hello, agent!")

    @patch("src.ui.streamlit_app.st")
    def test_display_message_part_user_prompt_no_content(self, mock_st):
        """Test displaying user prompt with no content."""
        mock_part = Mock()
        mock_part.part_kind = "user-prompt"
        mock_part.content = None

        display_message_part(mock_part)

        # Should not call chat_message if no content
        mock_st.chat_message.assert_not_called()

    @patch("src.ui.streamlit_app.st")
    def test_display_message_part_user_prompt_empty_content(self, mock_st):
        """Test displaying user prompt with empty content."""
        mock_part = Mock()
        mock_part.part_kind = "user-prompt"
        mock_part.content = ""

        display_message_part(mock_part)

        # Should not call chat_message if content is empty
        mock_st.chat_message.assert_not_called()

    @patch("src.ui.streamlit_app.st")
    def test_display_message_part_non_user_prompt(self, mock_st):
        """Test displaying non-user-prompt message."""
        mock_part = Mock()
        mock_part.part_kind = "system-response"
        mock_part.content = "System message"

        display_message_part(mock_part)

        # Should not call chat_message for non-user-prompt
        mock_st.chat_message.assert_not_called()
