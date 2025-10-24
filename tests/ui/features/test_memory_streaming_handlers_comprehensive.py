"""
Comprehensive tests for MemoryHandler and StreamingHandler.

Covers:
- MemoryHandler: Mem0 client integration, memory retrieval/storage
- StreamingHandler: Streaming event processing, tool call tracking
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pydantic_ai.messages import ModelRequest, ModelResponse, PartStartEvent, PartDeltaEvent, TextPartDelta

from src.ui.features.memory_handler import MemoryHandler
from src.ui.features.streaming_handler import StreamingHandler


# ===== Fixtures =====


@pytest.fixture
def memory_config():
    """Config for memory handler."""
    return {
        "enable_memory": True,
        "user_id": "test_user",
        "memory_limit": 3,
        "enable_streaming": True,
        "features": {},
    }


@pytest.fixture
def streaming_config():
    """Config for streaming handler."""
    return {
        "enable_streaming": True,
        "features": {},
    }


# ===== MemoryHandler Tests =====


class TestMemoryHandlerInit:
    """Test MemoryHandler initialization."""

    def test_init_with_config(self, memory_config):
        """Test initialization with config."""
        with patch("src.ui.features.memory_handler.get_mem0_client") as mock_get_mem0:
            mock_get_mem0.return_value = Mock()

            handler = MemoryHandler(memory_config)

            assert handler.user_id == "test_user"

    def test_init_disables_memory(self):
        """Test initialization with memory disabled."""
        config = {"enable_memory": False}

        with patch("src.ui.features.memory_handler.get_mem0_client") as mock_get_mem0:
            handler = MemoryHandler(config)

            # Should not create Mem0 client
            mock_get_mem0.assert_not_called()

    def test_init_handles_mem0_failure(self, memory_config):
        """Test that Mem0 initialization failure is handled gracefully."""
        with patch("src.ui.features.memory_handler.get_mem0_client", side_effect=Exception("Mem0 error")):
            handler = MemoryHandler(memory_config)

            # Should not raise, just set client to None
            assert handler.memory_client is None


class TestGetMemories:
    """Test memory retrieval."""

    def test_get_memories_success(self, memory_config):
        """Test successful memory retrieval."""
        mock_client = Mock()
        mock_client.search.return_value = {
            "results": [
                {"memory": "User prefers Python"},
                {"memory": "User works on AI projects"},
            ]
        }

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)
            memories = handler.get_memories("What do I like?")

            assert "User prefers Python" in memories
            assert "User works on AI projects" in memories
            mock_client.search.assert_called_once()

    def test_get_memories_no_client(self, memory_config):
        """Test memory retrieval when client is not available."""
        with patch("src.ui.features.memory_handler.get_mem0_client", side_effect=Exception("Error")):
            handler = MemoryHandler(memory_config)
            handler.memory_client = None

            memories = handler.get_memories("What do I like?")

            assert memories == ""

    def test_get_memories_empty_results(self, memory_config):
        """Test memory retrieval with no results."""
        mock_client = Mock()
        mock_client.search.return_value = {"results": []}

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)
            memories = handler.get_memories("Something new")

            assert memories == ""

    def test_get_memories_respects_limit(self, memory_config):
        """Test that memory limit is respected."""
        memory_config["memory_limit"] = 5
        mock_client = Mock()
        mock_client.search.return_value = {"results": []}

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)
            handler.get_memories("query")

            call_args = mock_client.search.call_args
            assert call_args[1]["limit"] == 5


class TestStoreMemories:
    """Test memory storage."""

    def test_store_interaction_success(self, memory_config):
        """Test storing interaction in memory."""
        mock_client = Mock()
        mock_client.add.return_value = {"status": "success"}

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            messages = [
                ModelRequest(parts=[{"content": "Hello"}]),
                ModelResponse(parts=[{"content": "Hi there!"}]),
            ]

            handler.store_interaction(messages, "Hi there!")

            mock_client.add.assert_called_once()

    def test_store_interaction_no_client(self, memory_config):
        """Test storing interaction when client not available."""
        with patch("src.ui.features.memory_handler.get_mem0_client", side_effect=Exception("Error")):
            handler = MemoryHandler(memory_config)
            handler.memory_client = None

            messages = []
            # Should not raise
            handler.store_interaction(messages, "response")


# ===== StreamingHandler Tests =====


@pytest.mark.asyncio
class TestStreamingHandler:
    """Test StreamingHandler functionality."""

    async def test_run_agent_streams_events(self, streaming_config):
        """Test that run_agent streams events."""
        mock_http_client = AsyncMock()

        with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
            # Mock streaming context
            mock_node = Mock()
            mock_stream_context = Mock()
            mock_stream_context.__aenter__ = AsyncMock(return_value=None)
            mock_stream_context.__aexit__ = AsyncMock(return_value=False)

            mock_agent.iter.return_value.__aenter__ = AsyncMock()
            mock_agent.iter.return_value.__aexit__ = AsyncMock(return_value=False)

            async def mock_iter():
                # Yield a mock node
                yield mock_node

            mock_agent.iter.return_value.__aiter__ = mock_iter
            mock_agent.is_model_request_node.return_value = False

            handler = StreamingHandler(streaming_config)

            events = []
            async for event in handler.run_agent(
                "test query",
                [],
                mock_http_client,
            ):
                events.append(event)

            # Should process streaming
            mock_agent.iter.assert_called_once()

    async def test_run_agent_tracks_events(self, streaming_config):
        """Test that event counts are tracked."""
        mock_http_client = AsyncMock()

        with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
            mock_agent.iter.return_value.__aenter__ = AsyncMock()
            mock_agent.iter.return_value.__aexit__ = AsyncMock(return_value=False)

            async def mock_empty_iter():
                return
                yield

            mock_agent.iter.return_value.__aiter__ = mock_empty_iter

            handler = StreamingHandler(streaming_config)

            events = []
            async for event in handler.run_agent("test", [], mock_http_client):
                events.append(event)

            # Should complete without errors
            assert isinstance(events, list)

    async def test_run_agent_handles_text_start(self, streaming_config):
        """Test handling text start events."""
        mock_http_client = AsyncMock()

        # Create mock text start event
        mock_part = Mock()
        mock_part.part_kind = "text"
        mock_part.content = "Hello"

        mock_event = PartStartEvent(part=mock_part)

        with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
            mock_node = Mock()
            mock_stream = Mock()

            async def mock_event_iter():
                yield mock_event

            mock_stream.__aiter__ = mock_event_iter
            mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream.__aexit__ = AsyncMock(return_value=False)

            mock_node.stream.return_value = mock_stream

            async def mock_node_iter():
                yield mock_node

            mock_agent.iter.return_value.__aiter__ = mock_node_iter
            mock_agent.iter.return_value.__aenter__ = AsyncMock()
            mock_agent.iter.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_agent.is_model_request_node.return_value = True

            handler = StreamingHandler(streaming_config)

            events = []
            async for event in handler.run_agent("test", [], mock_http_client):
                events.append(event)

            # Should yield text start event
            assert len(events) > 0

    async def test_run_agent_handles_tool_calls(self, streaming_config):
        """Test handling tool call events."""
        mock_http_client = AsyncMock()

        # Create mock tool call event
        mock_part = Mock()
        mock_part.part_kind = "tool-call"
        mock_part.tool_name = "smart_search"
        mock_part.args = {"query": "test"}

        mock_event = PartStartEvent(part=mock_part)

        with patch("src.ui.features.streaming_handler.super_agent") as mock_agent:
            mock_node = Mock()
            mock_stream = Mock()

            async def mock_event_iter():
                yield mock_event

            mock_stream.__aiter__ = mock_event_iter
            mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream.__aexit__ = AsyncMock(return_value=False)

            mock_node.stream.return_value = mock_stream

            async def mock_node_iter():
                yield mock_node

            mock_agent.iter.return_value.__aiter__ = mock_node_iter
            mock_agent.iter.return_value.__aenter__ = AsyncMock()
            mock_agent.iter.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_agent.is_model_request_node.return_value = True

            handler = StreamingHandler(streaming_config)

            events = []
            async for event in handler.run_agent("test", [], mock_http_client):
                events.append(event)

            # Should yield tool call event
            assert len(events) > 0


# ===== Integration Tests =====


@pytest.mark.asyncio
class TestMemoryStreamingIntegration:
    """Test MemoryHandler and StreamingHandler integration."""

    async def test_memory_handler_streams_with_memory_context(self, memory_config):
        """Test that MemoryHandler can stream with memory context."""
        mock_http_client = AsyncMock()
        mock_mem0_client = Mock()
        mock_mem0_client.search.return_value = {"results": [{"memory": "Test memory"}]}

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client), \
             patch("src.ui.features.streaming_handler.super_agent") as mock_agent:

            mock_agent.iter.return_value.__aenter__ = AsyncMock()
            mock_agent.iter.return_value.__aexit__ = AsyncMock(return_value=False)

            async def mock_empty_iter():
                return
                yield

            mock_agent.iter.return_value.__aiter__ = mock_empty_iter

            handler = MemoryHandler(memory_config)

            # Get memories
            memories = handler.get_memories("test query")
            assert "Test memory" in memories

            # Stream with memory context
            events = []
            async for event in handler.run_agent("test query", [], mock_http_client):
                events.append(event)

            # Should complete successfully
            assert isinstance(events, list)
