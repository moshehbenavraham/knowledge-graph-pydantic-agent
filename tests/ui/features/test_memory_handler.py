"""Comprehensive tests for memory_handler.py module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient

from src.ui.features.memory_handler import MemoryHandler


@pytest.fixture
def memory_config():
    """Create a config for MemoryHandler."""
    return {
        "llm_provider": "openai",
        "model": "gpt-4",
        "enable_memory": True,
        "enable_streaming": True,
        "user_id": "test_user",
        "memory_limit": 3,
    }


@pytest.fixture
def memory_config_disabled():
    """Create a config with memory disabled."""
    return {
        "llm_provider": "openai",
        "model": "gpt-4",
        "enable_memory": False,
        "enable_streaming": True,
        "user_id": "test_user",
    }


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    return AsyncMock(spec=AsyncClient)


@pytest.fixture
def mock_message_history():
    """Create mock message history."""
    return []


@pytest.fixture
def mock_mem0_client():
    """Create a mock Mem0 client."""
    client = Mock()
    client.search.return_value = {
        "results": [
            {"memory": "User likes Python programming"},
            {"memory": "User is working on a RAG system"},
            {"memory": "User prefers OpenAI models"},
        ]
    }
    client.add = Mock()
    return client


# ============================================================================
# MemoryHandler Initialization Tests
# ============================================================================


def test_memory_handler_init_with_memory_enabled(memory_config):
    """Test MemoryHandler initialization with memory enabled."""
    with patch("src.ui.features.memory_handler.get_mem0_client") as mock_get_mem0:
        mock_get_mem0.return_value = Mock()

        handler = MemoryHandler(memory_config)

        assert handler.user_id == "test_user"
        assert handler.memory_client is not None
        mock_get_mem0.assert_called_once()


def test_memory_handler_init_with_memory_disabled(memory_config_disabled):
    """Test MemoryHandler initialization with memory disabled."""
    with patch("src.ui.features.memory_handler.get_mem0_client") as mock_get_mem0:
        handler = MemoryHandler(memory_config_disabled)

        assert handler.user_id == "test_user"
        assert handler.memory_client is None
        mock_get_mem0.assert_not_called()


def test_memory_handler_init_mem0_error(memory_config):
    """Test MemoryHandler initialization when Mem0 client fails."""
    with patch(
        "src.ui.features.memory_handler.get_mem0_client", side_effect=Exception("Mem0 error")
    ):
        handler = MemoryHandler(memory_config)

        assert handler.user_id == "test_user"
        assert handler.memory_client is None


def test_memory_handler_default_user_id():
    """Test MemoryHandler uses default user_id if not provided."""
    config = {"enable_memory": True}

    with patch("src.ui.features.memory_handler.get_mem0_client"):
        handler = MemoryHandler(config)

        assert handler.user_id == "streamlit_user"


# ============================================================================
# MemoryHandler.get_memories Tests
# ============================================================================


def test_get_memories_success(memory_config, mock_mem0_client):
    """Test successful memory retrieval."""
    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        memories = handler.get_memories("test query")

        assert "Python programming" in memories
        assert "RAG system" in memories
        assert "OpenAI models" in memories
        mock_mem0_client.search.assert_called_once_with(
            query="test query", user_id="test_user", limit=3
        )


def test_get_memories_no_client(memory_config_disabled):
    """Test get_memories when no memory client exists."""
    handler = MemoryHandler(memory_config_disabled)

    memories = handler.get_memories("test query")

    assert memories == ""


def test_get_memories_empty_results(memory_config):
    """Test get_memories when Mem0 returns no results."""
    mock_client = Mock()
    mock_client.search.return_value = {"results": []}

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
        handler = MemoryHandler(memory_config)

        memories = handler.get_memories("test query")

        assert memories == ""


def test_get_memories_exception(memory_config, mock_mem0_client):
    """Test get_memories when Mem0 raises exception."""
    mock_mem0_client.search.side_effect = Exception("Search failed")

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        memories = handler.get_memories("test query")

        assert memories == ""


def test_get_memories_custom_limit(memory_config, mock_mem0_client):
    """Test get_memories with custom memory limit."""
    memory_config["memory_limit"] = 5

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        handler.get_memories("test query")

        mock_mem0_client.search.assert_called_once_with(
            query="test query", user_id="test_user", limit=5
        )


def test_get_memories_long_query(memory_config, mock_mem0_client):
    """Test get_memories with very long query."""
    long_query = "This is a very long query. " * 100

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        handler.get_memories(long_query)

        mock_mem0_client.search.assert_called_once()
        assert mock_mem0_client.search.call_args[1]["query"] == long_query


# ============================================================================
# MemoryHandler.add_memory Tests
# ============================================================================


def test_add_memory_success(memory_config, mock_mem0_client):
    """Test successful memory addition."""
    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        handler.add_memory("User question", "Agent response")

        mock_mem0_client.add.assert_called_once()
        call_args = mock_mem0_client.add.call_args
        messages = call_args[0][0]

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "User question"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Agent response"
        assert call_args[1]["user_id"] == "test_user"


def test_add_memory_no_client(memory_config_disabled):
    """Test add_memory when no memory client exists."""
    handler = MemoryHandler(memory_config_disabled)

    # Should not raise exception
    handler.add_memory("User question", "Agent response")


def test_add_memory_no_response(memory_config, mock_mem0_client):
    """Test add_memory with only user input."""
    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        handler.add_memory("User question", None)

        mock_mem0_client.add.assert_called_once()
        messages = mock_mem0_client.add.call_args[0][0]

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "User question"


def test_add_memory_exception(memory_config, mock_mem0_client):
    """Test add_memory when Mem0 raises exception."""
    mock_mem0_client.add.side_effect = Exception("Add failed")

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        # Should not raise exception
        handler.add_memory("User question", "Agent response")


def test_add_memory_empty_response(memory_config, mock_mem0_client):
    """Test add_memory with empty agent response."""
    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        handler.add_memory("User question", "")

        mock_mem0_client.add.assert_called_once()
        messages = mock_mem0_client.add.call_args[0][0]

        # Empty response is still added
        assert len(messages) == 2
        assert messages[1]["content"] == ""


# ============================================================================
# MemoryHandler.run_agent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_run_agent_with_memories(
    memory_config, mock_mem0_client, mock_http_client, mock_message_history
):
    """Test run_agent retrieves and uses memories."""

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent."""
        yield {"type": "start", "content": "Hello"}
        yield {"type": "delta", "content": " world"}
        yield {"type": "complete", "new_messages": [], "streaming": True}

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            events = []
            async for event in handler.run_agent(
                "test input", mock_message_history, mock_http_client
            ):
                events.append(event)

            # Verify memories were retrieved
            mock_mem0_client.search.assert_called_once()

            # Verify we got all streaming events
            assert len(events) == 3
            assert events[0]["type"] == "start"
            assert events[1]["type"] == "delta"
            assert events[2]["type"] == "complete"


@pytest.mark.asyncio
async def test_run_agent_stores_memory(
    memory_config, mock_mem0_client, mock_http_client, mock_message_history
):
    """Test run_agent stores interaction in memory."""

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent."""
        yield {"type": "delta", "content": "Response "}
        yield {"type": "delta", "content": "text"}
        yield {"type": "complete", "new_messages": [], "streaming": True}

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            events = []
            async for event in handler.run_agent(
                "test input", mock_message_history, mock_http_client
            ):
                events.append(event)

            # Verify memory was stored
            mock_mem0_client.add.assert_called_once()
            messages = mock_mem0_client.add.call_args[0][0]

            assert len(messages) == 2
            assert messages[0]["content"] == "test input"
            # Full response should be accumulated
            assert messages[1]["content"] == "Response text"


@pytest.mark.asyncio
async def test_run_agent_no_memory_client(
    memory_config_disabled, mock_http_client, mock_message_history
):
    """Test run_agent when memory is disabled."""

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent."""
        yield {"type": "start", "content": "Hello"}
        yield {"type": "complete", "new_messages": [], "streaming": True}

    handler = MemoryHandler(memory_config_disabled)

    with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
        events = []
        async for event in handler.run_agent("test input", mock_message_history, mock_http_client):
            events.append(event)

        # Should complete without errors
        assert len(events) == 2


@pytest.mark.asyncio
async def test_run_agent_memory_retrieval_error(
    memory_config, mock_mem0_client, mock_http_client, mock_message_history
):
    """Test run_agent when memory retrieval fails."""
    mock_mem0_client.search.side_effect = Exception("Search failed")

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent."""
        yield {"type": "start", "content": "Hello"}
        yield {"type": "complete", "new_messages": [], "streaming": True}

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            events = []
            async for event in handler.run_agent(
                "test input", mock_message_history, mock_http_client
            ):
                events.append(event)

            # Should continue despite memory error
            assert len(events) == 2


@pytest.mark.asyncio
async def test_run_agent_memory_storage_error(
    memory_config, mock_mem0_client, mock_http_client, mock_message_history
):
    """Test run_agent when memory storage fails."""
    mock_mem0_client.add.side_effect = Exception("Add failed")

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent."""
        yield {"type": "delta", "content": "Response"}
        yield {"type": "complete", "new_messages": [], "streaming": True}

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            events = []
            async for event in handler.run_agent(
                "test input", mock_message_history, mock_http_client
            ):
                events.append(event)

            # Should complete despite memory storage error
            assert len(events) == 2


@pytest.mark.asyncio
async def test_run_agent_passes_memories_to_parent(
    memory_config, mock_mem0_client, mock_http_client, mock_message_history
):
    """Test that memories are passed to parent run_agent via kwargs."""
    memories_passed = None

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent that captures kwargs."""
        nonlocal memories_passed
        memories_passed = kwargs.get("memories_str")
        yield {"type": "complete", "new_messages": [], "streaming": True}

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            async for _ in handler.run_agent("test input", mock_message_history, mock_http_client):
                pass

            # Verify memories were passed
            assert memories_passed is not None
            assert "Python programming" in memories_passed


@pytest.mark.asyncio
async def test_run_agent_accumulates_full_response(
    memory_config, mock_mem0_client, mock_http_client, mock_message_history
):
    """Test that full response is properly accumulated from deltas."""

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent with multiple deltas."""
        yield {"type": "delta", "content": "First "}
        yield {"type": "delta", "content": "Second "}
        yield {"type": "delta", "content": "Third"}
        yield {"type": "complete", "new_messages": [], "streaming": True}

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            async for _ in handler.run_agent("test input", mock_message_history, mock_http_client):
                pass

            # Verify full response was accumulated
            mock_mem0_client.add.assert_called_once()
            messages = mock_mem0_client.add.call_args[0][0]
            assert messages[1]["content"] == "First Second Third"


@pytest.mark.asyncio
async def test_run_agent_no_storage_on_incomplete_stream(
    memory_config, mock_mem0_client, mock_http_client, mock_message_history
):
    """Test that memory is not stored if stream doesn't complete."""

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent without completion event."""
        yield {"type": "delta", "content": "Response"}
        # No complete event

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            async for _ in handler.run_agent("test input", mock_message_history, mock_http_client):
                pass

            # Memory should not be stored without complete event
            mock_mem0_client.add.assert_not_called()


@pytest.mark.asyncio
async def test_run_agent_exception_propagation(
    memory_config, mock_mem0_client, mock_http_client, mock_message_history
):
    """Test that exceptions from parent are properly propagated."""

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent that raises exception."""
        yield {"type": "delta", "content": "Start"}
        raise Exception("Streaming error")

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            with pytest.raises(Exception, match="Streaming error"):
                async for _ in handler.run_agent(
                    "test input", mock_message_history, mock_http_client
                ):
                    pass


@pytest.mark.asyncio
async def test_run_agent_with_message_history(memory_config, mock_mem0_client, mock_http_client):
    """Test run_agent with existing message history."""
    message_history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent."""
        yield {"type": "complete", "new_messages": [], "streaming": True}

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            async for _ in handler.run_agent("new input", message_history, mock_http_client):
                pass

            # Should complete successfully with history
            assert True


@pytest.mark.asyncio
async def test_run_agent_chunk_counting(
    memory_config, mock_mem0_client, mock_http_client, mock_message_history
):
    """Test that chunk count is tracked correctly."""

    async def mock_parent_run_agent(*args, **kwargs):
        """Mock parent run_agent with many chunks."""
        for i in range(50):
            yield {"type": "delta", "content": f"chunk{i} "}
        yield {"type": "complete", "new_messages": [], "streaming": True}

    with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_mem0_client):
        handler = MemoryHandler(memory_config)

        with patch.object(handler.__class__.__bases__[0], "run_agent", new=mock_parent_run_agent):
            chunk_count = 0
            async for event in handler.run_agent(
                "test input", mock_message_history, mock_http_client
            ):
                if event["type"] == "delta":
                    chunk_count += 1

            assert chunk_count == 50
