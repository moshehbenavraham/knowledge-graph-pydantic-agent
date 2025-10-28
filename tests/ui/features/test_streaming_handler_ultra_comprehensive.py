"""Ultra comprehensive tests for streaming_handler.py - targeting 45 uncovered lines."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient
from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPartDelta

from src.ui.features.streaming_handler import StreamingHandler


# Helper functions to create real Pydantic AI event instances
def create_part_start_event(part_kind, content=None, tool_name=None, args=None):
    """Create a PartStartEvent with mocked part."""
    part = Mock()
    part.part_kind = part_kind
    if content is not None:
        part.content = content
    if tool_name is not None:
        part.tool_name = tool_name
    if args is not None:
        part.args = args
    elif part_kind == "tool-call":
        part.args = {}

    # Create real PartStartEvent instance
    event = Mock(spec=PartStartEvent)
    event.part = part
    # Make isinstance work by setting the class
    event.__class__ = PartStartEvent
    return event


def create_part_delta_event(content_delta):
    """Create a PartDeltaEvent with TextPartDelta."""
    # Create real TextPartDelta
    delta = TextPartDelta(content_delta=content_delta)

    # Create real PartDeltaEvent instance
    event = Mock(spec=PartDeltaEvent)
    event.delta = delta
    # Make isinstance work by setting the class
    event.__class__ = PartDeltaEvent
    return event


class TestStreamingHandler:
    """Test StreamingHandler class."""

    def test_init(self):
        """Test initialization."""
        config = {"enable_memory": False, "user_id": "test_user"}
        handler = StreamingHandler(config)
        assert handler.config == config

    @pytest.mark.asyncio
    async def test_run_agent(self):
        """Test run_agent streaming response."""
        config = {"enable_memory": False, "user_id": "test_user"}
        handler = StreamingHandler(config)
        mock_http_client = AsyncMock(spec=AsyncClient)

        async def mock_stream_generator():
            """Mock stream of events."""
            # Text start
            yield create_part_start_event("text", content="Hello")
            # Text delta
            yield create_part_delta_event(" world")

        # Mock the agent iteration
        with (
            patch("src.ui.features.streaming_handler.super_agent") as mock_agent,
            patch("src.ui.features.streaming_handler.Agent") as MockAgent,
        ):
            mock_run = AsyncMock()
            mock_node = Mock()
            mock_node_stream = AsyncMock()
            mock_ctx = Mock()

            # Setup mock returns
            MockAgent.is_model_request_node.return_value = True
            mock_node_stream.__aenter__.return_value = mock_stream_generator()
            mock_node.stream.return_value = mock_node_stream

            # Mock run result
            mock_result = Mock()
            mock_result.new_messages.return_value = []
            mock_run.result = mock_result
            mock_run.ctx = mock_ctx

            # Mock run context
            mock_run.__aenter__.return_value = mock_run
            mock_run.__aexit__.return_value = None

            async def mock_node_iter():
                yield mock_node

            mock_run.__aiter__ = lambda self: mock_node_iter()
            mock_agent.iter.return_value = mock_run

            # Execute
            events = []
            async for event in handler.run_agent("test input", [], mock_http_client):
                events.append(event)

            # Verify events
            assert len(events) >= 3  # start + delta + complete
            assert events[0]["type"] == "start"
            assert events[0]["content"] == "Hello"
            assert events[1]["type"] == "delta"
            assert events[1]["content"] == " world"
            complete_events = [e for e in events if e["type"] == "complete"]
            assert len(complete_events) == 1
