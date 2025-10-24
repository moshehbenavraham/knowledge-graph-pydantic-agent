"""Comprehensive tests for streaming_handler.py module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient

from src.ui.features.streaming_handler import StreamingHandler


# Mock event classes for streaming
class MockPartStartEvent:
    """Mock PartStartEvent."""

    def __init__(self, part_kind, content=None, tool_name=None, args=None):
        self.part = Mock()
        self.part.part_kind = part_kind
        if content is not None:
            self.part.content = content
        if tool_name is not None:
            self.part.tool_name = tool_name
            self.part.args = args or {}


class MockPartDeltaEvent:
    """Mock PartDeltaEvent."""

    def __init__(self, content_delta):
        self.delta = Mock()
        self.delta.content_delta = content_delta


class MockTextPartDelta:
    """Mock TextPartDelta."""

    def __init__(self, content_delta):
        self.content_delta = content_delta


@pytest.fixture
def streaming_handler():
    """Create a StreamingHandler instance."""
    config = {
        "llm_provider": "openai",
        "model": "gpt-4",
        "enable_streaming": True,
    }
    return StreamingHandler(config)


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    return AsyncMock(spec=AsyncClient)


@pytest.fixture
def mock_message_history():
    """Create mock message history."""
    return []


# ============================================================================
# StreamingHandler.run_agent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_streaming_handler_basic_text_stream(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test basic text streaming."""

    async def mock_stream_generator():
        """Mock stream of events."""
        # Text start
        yield MockPartStartEvent("text", content="Hello")
        # Text deltas
        yield MockPartDeltaEvent(" world")
        yield MockPartDeltaEvent("!")

    # Mock the agent iteration
    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        # Setup mock returns
        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        # Mock run result
        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result

        # Mock run context
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify events
        assert len(events) >= 3  # start + 2 deltas + complete
        assert events[0]["type"] == "start"
        assert events[0]["content"] == "Hello"
        assert events[1]["type"] == "delta"
        assert events[2]["type"] == "delta"


@pytest.mark.asyncio
async def test_streaming_handler_tool_call_event(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test streaming with tool call events."""

    async def mock_stream_generator():
        """Mock stream with tool call."""
        yield MockPartStartEvent("tool-call", tool_name="search_web", args={"query": "test"})
        yield MockPartStartEvent("tool-return", tool_name="search_web")

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify tool call event
        tool_call_events = [e for e in events if e["type"] == "tool-call"]
        assert len(tool_call_events) == 1
        assert tool_call_events[0]["tool_name"] == "search_web"
        assert tool_call_events[0]["args"] == {"query": "test"}

        # Verify tool return event
        tool_return_events = [e for e in events if e["type"] == "tool-return"]
        assert len(tool_return_events) == 1
        assert tool_return_events[0]["tool_name"] == "search_web"


@pytest.mark.asyncio
async def test_streaming_handler_multiple_nodes(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test streaming with multiple nodes."""

    async def mock_stream_generator_1():
        yield MockPartStartEvent("text", content="First")

    async def mock_stream_generator_2():
        yield MockPartStartEvent("text", content="Second")

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node_1 = Mock()
        mock_node_2 = Mock()

        mock_agent.is_model_request_node.return_value = True

        # Setup first node
        mock_node_stream_1 = AsyncMock()
        mock_node_stream_1.__aenter__.return_value = mock_stream_generator_1()
        mock_node_1.stream.return_value = mock_node_stream_1

        # Setup second node
        mock_node_stream_2 = AsyncMock()
        mock_node_stream_2.__aenter__.return_value = mock_stream_generator_2()
        mock_node_2.stream.return_value = mock_node_stream_2

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node_1
            yield mock_node_2

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify we got events from both nodes
        start_events = [e for e in events if e["type"] == "start"]
        assert len(start_events) == 2


@pytest.mark.asyncio
async def test_streaming_handler_text_delta_batching(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that text deltas are properly streamed."""

    async def mock_stream_generator():
        """Mock stream with many deltas."""
        yield MockPartStartEvent("text", content="Start")
        for i in range(20):
            yield MockPartDeltaEvent(f" delta{i}")

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify we got all deltas
        delta_events = [e for e in events if e["type"] == "delta"]
        assert len(delta_events) == 20


@pytest.mark.asyncio
async def test_streaming_handler_completion_event(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that completion event includes new_messages."""

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Done")

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        # Mock new messages
        mock_messages = [{"role": "assistant", "content": "Response"}]
        mock_result = Mock()
        mock_result.new_messages.return_value = mock_messages
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify completion event
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) == 1
        assert complete_events[0]["streaming"] is True
        assert complete_events[0]["new_messages"] == mock_messages


@pytest.mark.asyncio
async def test_streaming_handler_non_model_request_node(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test handling of non-model request nodes."""

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()

        # This node is NOT a model request
        mock_agent.is_model_request_node.return_value = False

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Should only have completion event
        assert len(events) == 1
        assert events[0]["type"] == "complete"


@pytest.mark.asyncio
async def test_streaming_handler_error_handling(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test error handling during streaming."""

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_agent.iter.side_effect = Exception("Streaming failed")

        # Execute and expect exception
        with pytest.raises(Exception, match="Streaming failed"):
            async for _ in streaming_handler.run_agent(
                "test input", mock_message_history, mock_http_client
            ):
                pass


@pytest.mark.asyncio
async def test_streaming_handler_empty_input(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test streaming with empty input."""

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="")

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent("", mock_message_history, mock_http_client):
            events.append(event)

        # Should complete successfully
        assert any(e["type"] == "complete" for e in events)


@pytest.mark.asyncio
async def test_streaming_handler_tool_call_with_complex_args(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test tool call with complex arguments."""
    complex_args = {
        "query": "test search",
        "filters": {"date": "2024-01-01", "category": "tech"},
        "limit": 10,
        "nested": {"key": "value"},
    }

    async def mock_stream_generator():
        yield MockPartStartEvent("tool-call", tool_name="complex_search", args=complex_args)

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify complex args were preserved
        tool_call_events = [e for e in events if e["type"] == "tool-call"]
        assert len(tool_call_events) == 1
        assert tool_call_events[0]["args"] == complex_args


@pytest.mark.asyncio
async def test_streaming_handler_long_content(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test streaming with long content."""
    long_content = "This is a very long response. " * 100

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Start: ")
        # Simulate streaming in chunks
        for i in range(0, len(long_content), 50):
            yield MockPartDeltaEvent(long_content[i : i + 50])

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify we got many delta events
        delta_events = [e for e in events if e["type"] == "delta"]
        assert len(delta_events) > 50


@pytest.mark.asyncio
async def test_streaming_handler_message_history_passed(streaming_handler, mock_http_client):
    """Test that message history is properly passed to agent."""
    message_history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Response")

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "new input", message_history, mock_http_client
        ):
            events.append(event)

        # Verify message_history was passed to iter
        mock_agent.iter.assert_called_once()
        call_kwargs = mock_agent.iter.call_args[1]
        assert "message_history" in call_kwargs
        assert call_kwargs["message_history"] == message_history


@pytest.mark.asyncio
async def test_streaming_handler_kwargs_passed_to_deps(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that kwargs are passed to get_agent_deps."""

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Response")

    with (
        patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
        patch.object(streaming_handler, "get_agent_deps") as mock_get_deps,
    ):
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Mock get_agent_deps return
        mock_get_deps.return_value = Mock()

        # Execute with custom kwargs
        custom_kwargs = {"memories_str": "test memory", "custom_param": "value"}
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client, **custom_kwargs
        ):
            events.append(event)

        # Verify kwargs were passed to get_agent_deps
        mock_get_deps.assert_called_once()
        call_args = mock_get_deps.call_args
        assert call_args[0][0] == mock_http_client
        assert "memories_str" in call_args[1]
        assert "custom_param" in call_args[1]


@pytest.mark.asyncio
async def test_streaming_handler_tool_return_with_content(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test tool return with actual content."""
    tool_content = {"results": ["item1", "item2", "item3"], "count": 3}

    async def mock_stream_generator():
        yield MockPartStartEvent("tool-call", tool_name="search", args={"q": "test"})
        part = Mock()
        part.part_kind = "tool-return"
        part.tool_name = "search"
        part.content = tool_content
        yield type("MockEvent", (), {"part": part})()

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify tool return content
        tool_return_events = [e for e in events if e["type"] == "tool-return"]
        assert len(tool_return_events) == 1
        assert tool_return_events[0]["content"] == tool_content


@pytest.mark.asyncio
async def test_streaming_handler_initialization(streaming_handler):
    """Test StreamingHandler initialization from config."""
    assert streaming_handler.config is not None
    assert streaming_handler.config["enable_streaming"] is True


@pytest.mark.asyncio
async def test_streaming_handler_ctx_attribute_access(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that ctx attribute is accessible in nodes."""

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Test")

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        # Add ctx attribute to run
        mock_ctx = Mock()
        mock_run.ctx = mock_ctx

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify node.stream was called with run.ctx
        mock_node.stream.assert_called_once_with(mock_ctx)


@pytest.mark.asyncio
async def test_streaming_handler_event_counts_tracking(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that event counts are properly tracked."""

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Hello")
        for i in range(5):
            yield MockPartDeltaEvent(f" delta{i}")
        yield MockPartStartEvent("tool-call", tool_name="test", args={})
        yield MockPartStartEvent("tool-return", tool_name="test")

    with (
        patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
        patch("src.ui.features.streaming_handler.logger") as mock_logger,
    ):
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify logger was called with event counts
        assert mock_logger.info.called


@pytest.mark.asyncio
async def test_streaming_handler_text_delta_logging_frequency(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that text deltas are logged every 10 events."""

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Start")
        for i in range(25):  # More than 10
            yield MockPartDeltaEvent(f" delta{i}")

    with (
        patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
        patch("src.ui.features.streaming_handler.logger") as mock_logger,
    ):
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify deltas were logged (every 10th)
        delta_logs = [
            call for call in mock_logger.debug.call_args_list if "Text delta streaming" in str(call)
        ]
        # Should log at delta 10 and 20
        assert len(delta_logs) >= 2


@pytest.mark.asyncio
async def test_streaming_handler_long_text_content_preview(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that long text content is previewed in logs."""
    very_long_content = "x" * 200

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content=very_long_content)

    with (
        patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
        patch("src.ui.features.streaming_handler.logger") as mock_logger,
    ):
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify preview was created (should be <= 50 chars + "...")
        assert mock_logger.debug.called


@pytest.mark.asyncio
async def test_streaming_handler_long_user_input_preview(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that long user input is previewed in logs."""
    very_long_input = "x" * 200

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Response")

    with (
        patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
        patch("src.ui.features.streaming_handler.logger") as mock_logger,
    ):
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            very_long_input, mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify user input preview was logged
        assert mock_logger.info.called


@pytest.mark.asyncio
async def test_streaming_handler_tool_call_non_dict_args(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test tool call with non-dict args."""

    async def mock_stream_generator():
        part = Mock()
        part.part_kind = "tool-call"
        part.tool_name = "test_tool"
        part.args = "string_args"  # Non-dict args
        yield type("MockEvent", (), {"part": part})()

    with (
        patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
        patch("src.ui.features.streaming_handler.logger") as mock_logger,
    ):
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify logger handled non-dict args
        assert mock_logger.info.called


@pytest.mark.asyncio
async def test_streaming_handler_long_tool_return_preview(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that long tool return content is previewed."""
    very_long_return = "x" * 200

    async def mock_stream_generator():
        part = Mock()
        part.part_kind = "tool-return"
        part.tool_name = "test_tool"
        part.content = very_long_return
        yield type("MockEvent", (), {"part": part})()

    with (
        patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
        patch("src.ui.features.streaming_handler.logger") as mock_logger,
    ):
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify preview was created
        assert mock_logger.info.called


@pytest.mark.asyncio
async def test_streaming_handler_error_with_event_tracking(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that event counts are logged even on error."""

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Start")
        yield MockPartDeltaEvent(" delta1")
        raise RuntimeError("Streaming error")

    with (
        patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
        patch("src.ui.features.streaming_handler.logger") as mock_logger,
    ):
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute and expect error
        with pytest.raises(RuntimeError, match="Streaming error"):
            async for _ in streaming_handler.run_agent(
                "test input", mock_message_history, mock_http_client
            ):
                pass

        # Verify exception was logged with event counts
        assert mock_logger.exception.called
        exception_call = mock_logger.exception.call_args
        assert "events_before_failure" in str(exception_call)


@pytest.mark.asyncio
async def test_streaming_handler_get_agent_deps_call(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that get_agent_deps is called correctly."""

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Test")

    with (
        patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
        patch.object(streaming_handler, "get_agent_deps", return_value=Mock()) as mock_get_deps,
    ):
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        mock_result = Mock()
        mock_result.new_messages.return_value = []
        mock_run.result = mock_result
        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify get_agent_deps was called
        mock_get_deps.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_handler_result_attribute_access(
    streaming_handler, mock_http_client, mock_message_history
):
    """Test that run.result is accessible after iteration."""

    async def mock_stream_generator():
        yield MockPartStartEvent("text", content="Test")

    with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
        mock_run = AsyncMock()
        mock_node = Mock()
        mock_node_stream = AsyncMock()

        mock_agent.is_model_request_node.return_value = True
        mock_node_stream.__aenter__.return_value = mock_stream_generator()
        mock_node.stream.return_value = mock_node_stream

        # Create mock result with new_messages
        mock_result = Mock()
        mock_result.new_messages.return_value = [{"role": "assistant", "content": "Test"}]
        mock_run.result = mock_result

        mock_run.__aenter__.return_value = mock_run
        mock_run.__aexit__.return_value = None

        async def mock_node_iter():
            yield mock_node

        mock_run.__aiter__.return_value = mock_node_iter()
        mock_agent.iter.return_value = mock_run

        # Execute
        events = []
        async for event in streaming_handler.run_agent(
            "test input", mock_message_history, mock_http_client
        ):
            events.append(event)

        # Verify result.new_messages was called
        mock_result.new_messages.assert_called()
