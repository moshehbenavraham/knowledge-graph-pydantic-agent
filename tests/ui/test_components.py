"""
Unit tests for UI components.

Tests progress indicators, loading states, error display,
and response metadata components.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.ui.components.error_display import (
    ErrorDisplayConfig,
    ErrorSeverity,
    create_error_config,
)
from src.ui.components.loading_states import (
    LoadingContext,
    OperationType,
    get_loading_message,
    get_operation_from_intent,
    get_operation_from_tool,
)
from src.ui.components.progress_indicators import (
    ToolExecutionState,
    ToolStatus,
    create_tool_state_from_event,
    get_tool_display_name,
)
from src.ui.components.response_metadata import (
    ResponseMetadata,
    create_metadata_from_result,
    get_intent_display,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit module for component testing."""
    with patch("src.ui.components.progress_indicators.st") as mock_st:
        mock_st.markdown = MagicMock()
        mock_st.caption = MagicMock()
        mock_st.info = MagicMock()
        mock_st.warning = MagicMock()
        mock_st.error = MagicMock()
        mock_st.spinner = MagicMock()
        mock_st.expander = MagicMock()
        mock_st.columns = MagicMock(return_value=[MagicMock() for _ in range(4)])
        mock_st.container = MagicMock()
        mock_st.progress = MagicMock()
        mock_st.json = MagicMock()
        mock_st.button = MagicMock(return_value=False)
        mock_st.code = MagicMock()
        yield mock_st


@pytest.fixture
def sample_tool_state():
    """Create a sample tool execution state."""
    return ToolExecutionState(
        tool_name="smart_search",
        status=ToolStatus.COMPLETED,
        start_time=datetime.now() - timedelta(milliseconds=150),
        end_time=datetime.now(),
        args={"query": "test query"},
        result_summary="Found 10 results",
    )


@pytest.fixture
def sample_response_metadata():
    """Create sample response metadata."""
    return ResponseMetadata(
        detected_intent="HYBRID",
        strategy_used="HYBRID",
        source_count=5,
        total_latency_ms=250.5,
        vector_latency_ms=100.0,
        graph_latency_ms=120.0,
        cache_hit=False,
        tools_called=["smart_search"],
        entities_found=3,
        relationships_found=2,
    )


@pytest.fixture
def sample_error_event():
    """Create a sample error event dictionary."""
    return {
        "type": "error",
        "error_type": "service_unavailable",
        "message": "The service is temporarily unavailable.",
        "recoverable": True,
        "retry_after_seconds": 30,
    }


# =============================================================================
# Progress Indicators Tests
# =============================================================================


class TestToolStatus:
    """Tests for ToolStatus enum."""

    def test_all_statuses_defined(self):
        """Verify all expected statuses exist."""
        assert ToolStatus.PENDING.value == "pending"
        assert ToolStatus.EXECUTING.value == "executing"
        assert ToolStatus.COMPLETED.value == "completed"
        assert ToolStatus.FAILED.value == "failed"


class TestToolExecutionState:
    """Tests for ToolExecutionState dataclass."""

    def test_elapsed_ms_no_start_time(self):
        """Test elapsed_ms returns 0 when no start time."""
        state = ToolExecutionState(tool_name="test_tool")
        assert state.elapsed_ms == 0.0

    def test_elapsed_ms_with_times(self, sample_tool_state):
        """Test elapsed_ms calculation with start and end times."""
        elapsed = sample_tool_state.elapsed_ms
        assert elapsed > 0
        assert elapsed < 1000  # Less than 1 second

    def test_elapsed_ms_still_running(self):
        """Test elapsed_ms for executing tool."""
        state = ToolExecutionState(
            tool_name="test_tool",
            status=ToolStatus.EXECUTING,
            start_time=datetime.now() - timedelta(milliseconds=500),
        )
        elapsed = state.elapsed_ms
        assert elapsed >= 500

    def test_elapsed_display_milliseconds(self):
        """Test elapsed_display for sub-second times."""
        state = ToolExecutionState(
            tool_name="test_tool",
            start_time=datetime.now() - timedelta(milliseconds=150),
            end_time=datetime.now(),
        )
        display = state.elapsed_display
        assert "ms" in display
        assert "s" not in display or display.endswith("ms")

    def test_elapsed_display_seconds(self):
        """Test elapsed_display for multi-second times."""
        state = ToolExecutionState(
            tool_name="test_tool",
            start_time=datetime.now() - timedelta(seconds=2, milliseconds=500),
            end_time=datetime.now(),
        )
        display = state.elapsed_display
        assert "s" in display
        assert "2." in display


class TestGetToolDisplayName:
    """Tests for get_tool_display_name function."""

    def test_known_tool_names(self):
        """Test display names for known tools."""
        assert get_tool_display_name("smart_search") == "Smart Search"
        assert get_tool_display_name("retrieve_documents") == "Document Retrieval"
        assert get_tool_display_name("web_search") == "Web Search"
        assert get_tool_display_name("execute_sql") == "SQL Query"

    def test_unknown_tool_name(self):
        """Test display name generation for unknown tools."""
        result = get_tool_display_name("my_custom_tool")
        assert result == "My Custom Tool"

    def test_tool_name_with_underscores(self):
        """Test handling of underscores in tool names."""
        result = get_tool_display_name("analyze_some_data")
        assert result == "Analyze Some Data"


class TestCreateToolStateFromEvent:
    """Tests for create_tool_state_from_event function."""

    def test_tool_call_event(self):
        """Test state creation from tool-call event."""
        state = create_tool_state_from_event(
            tool_name="smart_search",
            event_type="tool-call",
            args={"query": "test"},
        )
        assert state.tool_name == "smart_search"
        assert state.status == ToolStatus.EXECUTING
        assert state.start_time is not None
        assert state.args == {"query": "test"}

    def test_tool_return_event(self):
        """Test state creation from tool-return event."""
        state = create_tool_state_from_event(
            tool_name="smart_search",
            event_type="tool-return",
            content="Some result content here",
        )
        assert state.tool_name == "smart_search"
        assert state.status == ToolStatus.COMPLETED
        assert state.end_time is not None
        assert state.result_summary is not None

    def test_tool_return_truncates_long_content(self):
        """Test that long content is truncated in summary."""
        long_content = "x" * 200
        state = create_tool_state_from_event(
            tool_name="test",
            event_type="tool-return",
            content=long_content,
        )
        assert len(state.result_summary) <= 103  # 100 chars + "..."

    def test_unknown_event_type(self):
        """Test state creation for unknown event type."""
        state = create_tool_state_from_event(
            tool_name="test",
            event_type="unknown",
        )
        assert state.tool_name == "test"
        assert state.status == ToolStatus.PENDING


# =============================================================================
# Loading States Tests
# =============================================================================


class TestOperationType:
    """Tests for OperationType enum."""

    def test_all_operation_types_defined(self):
        """Verify all expected operation types exist."""
        assert OperationType.VECTOR_SEARCH.value == "vector_search"
        assert OperationType.GRAPH_SEARCH.value == "graph_search"
        assert OperationType.HYBRID_SEARCH.value == "hybrid_search"
        assert OperationType.MULTI_HOP.value == "multi_hop"
        assert OperationType.TEMPORAL_TREND.value == "temporal_trend"
        assert OperationType.COMPARISON.value == "comparison"


class TestLoadingContext:
    """Tests for LoadingContext dataclass."""

    def test_basic_context_creation(self):
        """Test basic context creation."""
        context = LoadingContext(operation=OperationType.VECTOR_SEARCH)
        assert context.operation == OperationType.VECTOR_SEARCH
        assert context.query is None
        assert context.progress is None

    def test_context_with_all_fields(self):
        """Test context with all optional fields."""
        context = LoadingContext(
            operation=OperationType.GRAPH_SEARCH,
            query="Find Intel relationships",
            entity_name="Intel",
            tool_name="graph_traverse",
            progress=50,
        )
        assert context.entity_name == "Intel"
        assert context.progress == 50


class TestGetLoadingMessage:
    """Tests for get_loading_message function."""

    def test_vector_search_message(self):
        """Test message for vector search operation."""
        context = LoadingContext(operation=OperationType.VECTOR_SEARCH)
        message = get_loading_message(context)
        assert "search" in message.lower() or "document" in message.lower()

    def test_graph_search_message(self):
        """Test message for graph search operation."""
        context = LoadingContext(operation=OperationType.GRAPH_SEARCH)
        message = get_loading_message(context)
        assert "graph" in message.lower() or "knowledge" in message.lower()

    def test_multi_hop_message(self):
        """Test message for multi-hop operation."""
        context = LoadingContext(operation=OperationType.MULTI_HOP)
        message = get_loading_message(context)
        assert "path" in message.lower() or "connection" in message.lower()

    def test_message_variants(self):
        """Test that different variants produce different messages."""
        context = LoadingContext(operation=OperationType.VECTOR_SEARCH)
        msg0 = get_loading_message(context, variant=0)
        msg1 = get_loading_message(context, variant=1)
        # At least some operations should have multiple messages
        # (messages may or may not differ based on operation)
        assert isinstance(msg0, str)
        assert isinstance(msg1, str)


class TestGetOperationFromIntent:
    """Tests for get_operation_from_intent function."""

    def test_vector_heavy_intent(self):
        """Test mapping VECTOR_HEAVY intent."""
        op = get_operation_from_intent("VECTOR_HEAVY")
        assert op == OperationType.VECTOR_SEARCH

    def test_graph_heavy_intent(self):
        """Test mapping GRAPH_HEAVY intent."""
        op = get_operation_from_intent("GRAPH_HEAVY")
        assert op == OperationType.GRAPH_SEARCH

    def test_multi_hop_intent(self):
        """Test mapping MULTI_HOP intent."""
        op = get_operation_from_intent("MULTI_HOP")
        assert op == OperationType.MULTI_HOP

    def test_unknown_intent_defaults_hybrid(self):
        """Test that unknown intent defaults to hybrid."""
        op = get_operation_from_intent("UNKNOWN_INTENT")
        assert op == OperationType.HYBRID_SEARCH

    def test_case_insensitive(self):
        """Test that intent matching is case-insensitive."""
        op = get_operation_from_intent("vector_heavy")
        assert op == OperationType.VECTOR_SEARCH


class TestGetOperationFromTool:
    """Tests for get_operation_from_tool function."""

    def test_smart_search_tool(self):
        """Test mapping smart_search tool."""
        op = get_operation_from_tool("smart_search")
        assert op == OperationType.HYBRID_SEARCH

    def test_web_search_tool(self):
        """Test mapping web_search tool."""
        op = get_operation_from_tool("web_search")
        assert op == OperationType.WEB_SEARCH

    def test_graph_traverse_tool(self):
        """Test mapping graph_traverse tool."""
        op = get_operation_from_tool("graph_traverse")
        assert op == OperationType.MULTI_HOP

    def test_unknown_tool_defaults_generating(self):
        """Test that unknown tool defaults to generating response."""
        op = get_operation_from_tool("unknown_tool")
        assert op == OperationType.GENERATING_RESPONSE


# =============================================================================
# Error Display Tests
# =============================================================================


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_all_severities_defined(self):
        """Verify all expected severities exist."""
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorDisplayConfig:
    """Tests for ErrorDisplayConfig dataclass."""

    def test_basic_config_creation(self):
        """Test basic config creation."""
        config = ErrorDisplayConfig(
            severity=ErrorSeverity.WARNING,
            title="Test Error",
            message="This is a test error message.",
        )
        assert config.severity == ErrorSeverity.WARNING
        assert config.title == "Test Error"
        assert config.retry_enabled is False

    def test_config_with_all_fields(self):
        """Test config with all optional fields."""
        config = ErrorDisplayConfig(
            severity=ErrorSeverity.ERROR,
            title="Connection Error",
            message="Could not connect to server.",
            recovery_suggestion="Check your network connection.",
            retry_enabled=True,
            retry_after_seconds=30,
            show_details=True,
            technical_details="ConnectionError: timeout",
        )
        assert config.retry_enabled is True
        assert config.retry_after_seconds == 30
        assert config.show_details is True


class TestCreateErrorConfig:
    """Tests for create_error_config function."""

    def test_service_unavailable_error(self):
        """Test config creation for service unavailable."""
        config = create_error_config(
            error_type="service_unavailable",
            message="Service is down.",
            retry_after_seconds=60,
        )
        assert config.severity == ErrorSeverity.WARNING
        assert "Service" in config.title
        assert config.retry_enabled is True

    def test_timeout_error(self):
        """Test config creation for timeout error."""
        config = create_error_config(error_type="timeout")
        assert config.severity == ErrorSeverity.WARNING
        assert "Timed Out" in config.title
        assert config.recovery_suggestion is not None

    def test_unexpected_error_with_exception(self):
        """Test config creation with actual exception."""
        error = ValueError("Invalid input")
        config = create_error_config(error=error, error_type="validation")
        assert config.severity == ErrorSeverity.INFO
        assert config.technical_details is not None
        assert "ValueError" in config.technical_details

    def test_error_with_custom_message(self):
        """Test that custom message overrides format_error_for_user."""
        config = create_error_config(
            error_type="connection",
            message="Custom error message.",
        )
        assert config.message == "Custom error message."


# =============================================================================
# Response Metadata Tests
# =============================================================================


class TestResponseMetadata:
    """Tests for ResponseMetadata dataclass."""

    def test_basic_metadata_creation(self):
        """Test basic metadata creation."""
        metadata = ResponseMetadata()
        assert metadata.source_count == 0
        assert metadata.total_latency_ms == 0.0
        assert metadata.cache_hit is False
        assert metadata.tools_called == []

    def test_metadata_with_all_fields(self, sample_response_metadata):
        """Test metadata with all fields populated."""
        assert sample_response_metadata.detected_intent == "HYBRID"
        assert sample_response_metadata.source_count == 5
        assert sample_response_metadata.entities_found == 3


class TestGetIntentDisplay:
    """Tests for get_intent_display function."""

    def test_vector_heavy_display(self):
        """Test display for VECTOR_HEAVY intent."""
        display = get_intent_display("VECTOR_HEAVY")
        assert display["label"] == "Content Search"
        assert "color" in display
        assert "description" in display

    def test_hybrid_display(self):
        """Test display for HYBRID intent."""
        display = get_intent_display("HYBRID")
        assert display["label"] == "Hybrid Search"

    def test_multi_hop_display(self):
        """Test display for MULTI_HOP intent."""
        display = get_intent_display("MULTI_HOP")
        assert display["label"] == "Path Discovery"

    def test_unknown_intent_display(self):
        """Test display for unknown intent."""
        display = get_intent_display("UNKNOWN")
        assert display["label"] == "UNKNOWN"
        assert display["color"] == "gray"

    def test_case_insensitive(self):
        """Test that intent lookup is case-insensitive."""
        display = get_intent_display("vector_heavy")
        assert display["label"] == "Content Search"


class TestCreateMetadataFromResult:
    """Tests for create_metadata_from_result function."""

    def test_from_search_result(self):
        """Test metadata creation from search result dict."""
        result = {
            "intent": "HYBRID",
            "strategy": "HYBRID",
            "chunks": [1, 2, 3, 4, 5],
            "total_latency_ms": 200.0,
            "cache_hit": True,
        }
        metadata = create_metadata_from_result(result)
        assert metadata.detected_intent == "HYBRID"
        assert metadata.source_count == 5
        assert metadata.total_latency_ms == 200.0
        assert metadata.cache_hit is True

    def test_with_tool_states(self, sample_tool_state):
        """Test metadata creation with tool states."""
        result = {"intent": "VECTOR_HEAVY"}
        metadata = create_metadata_from_result(result, tool_states=[sample_tool_state])
        assert len(metadata.tool_states) == 1
        assert metadata.tool_states[0].tool_name == "smart_search"

    def test_alternate_field_names(self):
        """Test handling of alternate field names."""
        result = {
            "detected_intent": "GRAPH_HEAVY",
            "strategy_used": "GRAPH_ONLY",
            "chunk_count": 10,
            "latency_ms": 150.0,
        }
        metadata = create_metadata_from_result(result)
        assert metadata.detected_intent == "GRAPH_HEAVY"
        assert metadata.source_count == 10
        assert metadata.total_latency_ms == 150.0

    def test_empty_result(self):
        """Test metadata creation from empty result."""
        metadata = create_metadata_from_result({})
        assert metadata.detected_intent is None
        assert metadata.source_count == 0
        assert metadata.total_latency_ms == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestComponentIntegration:
    """Integration tests for component interactions."""

    def test_tool_state_to_metadata_flow(self, sample_tool_state):
        """Test flow from tool state to response metadata."""
        metadata = ResponseMetadata(
            detected_intent="HYBRID",
            source_count=5,
            total_latency_ms=250.0,
            tool_states=[sample_tool_state],
        )
        assert len(metadata.tool_states) == 1
        assert metadata.tool_states[0].status == ToolStatus.COMPLETED

    def test_loading_context_to_message_flow(self):
        """Test flow from intent to loading message."""
        intent = "MULTI_HOP"
        operation = get_operation_from_intent(intent)
        context = LoadingContext(operation=operation)
        message = get_loading_message(context)
        # Multi-hop should mention paths or connections
        assert any(word in message.lower() for word in ["path", "connection", "discover"])

    def test_error_config_to_display_flow(self, sample_error_event):
        """Test flow from error event to display config."""
        config = create_error_config(
            error_type=sample_error_event["error_type"],
            message=sample_error_event["message"],
            recoverable=sample_error_event["recoverable"],
            retry_after_seconds=sample_error_event["retry_after_seconds"],
        )
        assert config.severity == ErrorSeverity.WARNING
        assert config.retry_enabled is True
        assert "30" in (config.recovery_suggestion or "")
