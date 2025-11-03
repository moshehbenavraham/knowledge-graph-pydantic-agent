"""
Comprehensive tests for api/endpoints/chat.py - Chat endpoints.

Tests cover:
- Synchronous chat endpoint with caching
- Streaming chat endpoint (SSE)
- WebSocket chat endpoint
- Feedback submission
- Session history retrieval
- Source document extraction
- Error handling and metrics
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from src.api.dependencies import get_agent_deps, get_cache_manager


@pytest.fixture
def mock_agent_deps():
    """Mock UnifiedAgentDeps."""
    mock_deps = Mock()
    mock_deps.supabase = Mock()
    mock_deps.embedding_client = Mock()
    return mock_deps


@pytest.fixture
def mock_cache():
    """Mock Redis cache."""
    cache = Mock()
    cache.get = Mock(return_value=None)
    cache.set = Mock()
    return cache


@pytest.fixture
def mock_agent_result():
    """Mock Pydantic AI agent result."""
    result = Mock()
    result.data = "This is a test response from the agent."
    result.usage = Mock(
        return_value={
            "total_tokens": 150,
            "prompt_tokens": 100,
            "completion_tokens": 50,
        }
    )
    result.all_messages = Mock(return_value=[])
    return result


@pytest.fixture
def app_client(mock_agent_deps, mock_cache):
    """Create test client for chat endpoints."""
    from fastapi import FastAPI

    from src.api.endpoints.chat import router

    app = FastAPI()
    app.include_router(router)

    # Create async dependency override functions
    async def get_mock_agent_deps():
        return mock_agent_deps

    async def get_mock_cache_manager():
        return mock_cache

    # Override dependencies
    app.dependency_overrides[get_agent_deps] = get_mock_agent_deps
    app.dependency_overrides[get_cache_manager] = get_mock_cache_manager

    return TestClient(app)


# ====================
# Synchronous Chat Endpoint Tests
# ====================


def test_chat_endpoint_success(app_client, mock_agent_deps, mock_cache, mock_agent_result):
    """Test successful synchronous chat request."""
    with patch(
        "src.api.endpoints.chat.super_agent.run",
        new_callable=AsyncMock,
        return_value=mock_agent_result,
    ):
        request_data = {
            "message": "What is the meaning of life?",
            "session_id": "test-session",
            "include_sources": False,
            "stream": False,
        }

        response = app_client.post("/api/v1/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert data["response"] == "This is a test response from the agent."
        assert data["session_id"] == "test-session"
        assert "message_id" in data
        assert data["metrics"]["tokens_used"] == 150


def test_chat_endpoint_cache_hit(app_client, mock_agent_deps, mock_cache):
    """Test chat endpoint with cache hit."""
    cached_response = {
        "response": "Cached response",
        "sources": None,
        "confidence": 0.85,
        "search_strategy_used": "VECTOR_HEAVY",
        "session_id": "test-session",
        "message_id": str(uuid4()),
        "metrics": {
            "response_time_ms": 50.0,
            "tokens_used": 100,
            "tokens_prompt": 75,
            "tokens_completion": 25,
            "cache_hit": True,
        },
    }

    mock_cache.get = Mock(return_value=cached_response)

    request_data = {
        "message": "What is the meaning of life?",
        "stream": False,
    }

    response = app_client.post("/api/v1/chat", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Cached response"


def test_chat_endpoint_with_sources(app_client, mock_agent_deps, mock_cache, mock_agent_result):
    """Test chat endpoint with source document extraction."""
    # Mock messages with tool calls
    mock_part = Mock()
    mock_part.tool_name = "retrieve_documents"
    mock_part.tool_return = [
        {
            "id": "doc-123",
            "content": "Test document content",
            "similarity": 0.95,
            "metadata": {"author": "Test"},
            "chunk_index": 0,
        }
    ]

    mock_message = Mock()
    mock_message.parts = [mock_part]

    mock_agent_result.all_messages = Mock(return_value=[mock_message])

    with patch(
        "src.api.endpoints.chat.super_agent.run",
        new_callable=AsyncMock,
        return_value=mock_agent_result,
    ):
        request_data = {
            "message": "Find documents about testing",
            "include_sources": True,
            "stream": False,
        }

        response = app_client.post("/api/v1/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["sources"] is not None
        assert len(data["sources"]) > 0
        assert data["sources"][0]["document_id"] == "doc-123"


def test_chat_endpoint_with_parameters(app_client, mock_agent_deps, mock_cache, mock_agent_result):
    """Test chat endpoint with custom parameters."""
    with patch(
        "src.api.endpoints.chat.super_agent.run",
        new_callable=AsyncMock,
        return_value=mock_agent_result,
    ) as mock_run:
        request_data = {
            "message": "Test message",
            "max_tokens": 500,
            "temperature": 0.7,
            "stream": False,
        }

        response = app_client.post("/api/v1/chat", json=request_data)

        assert response.status_code == 200

        # Verify parameters were passed
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["max_tokens"] == 500
        assert call_kwargs["temperature"] == 0.7


def test_chat_endpoint_error(app_client, mock_agent_deps, mock_cache):
    """Test chat endpoint error handling."""
    with patch(
        "src.api.endpoints.chat.super_agent.run",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Agent failed"),
    ):
        request_data = {
            "message": "Test message",
            "stream": False,
        }

        response = app_client.post("/api/v1/chat", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Agent failed" in data["detail"]


# ====================
# Streaming Chat Endpoint Tests
# ====================


def test_chat_stream_endpoint_success(app_client, mock_agent_deps):
    """Test SSE streaming chat endpoint."""

    async def mock_stream_generator():
        """Mock SSE event generator."""
        yield 'data: {"type": "text", "content": "Hello"}\n\n'
        yield 'data: {"type": "text", "content": " world"}\n\n'
        yield 'data: {"type": "done"}\n\n'

    with patch(
        "src.api.endpoints.chat.sse_manager.stream_agent_response",
        return_value=mock_stream_generator(),
    ):
        request_data = {
            "message": "Test streaming",
        }

        response = app_client.post("/api/v1/chat/stream", json=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "no-cache"


def test_chat_stream_with_parameters(app_client, mock_agent_deps):
    """Test streaming endpoint with custom parameters."""

    async def mock_stream():
        yield 'data: {"type": "text", "content": "test"}\n\n'

    with patch(
        "src.api.endpoints.chat.sse_manager.stream_agent_response",
        return_value=mock_stream(),
    ):
        request_data = {
            "message": "Test",
            "max_tokens": 1000,
            "temperature": 0.3,
        }

        response = app_client.post("/api/v1/chat/stream", json=request_data)

        assert response.status_code == 200


@pytest.mark.skip(
    reason="PERMANENT SKIP: StreamingResponse errors during iteration cannot be properly tested with TestClient. "
    "This is a limitation of the Starlette TestClient with async generators. "
    "Error handling is validated through manual testing and real-world usage. "
    "See docs/b-ongoing-projects/phase9_skip_analysis.md Category 2.2"
)
def test_chat_stream_error(app_client, mock_agent_deps):
    """Test streaming endpoint error handling."""

    # NOTE: This test is skipped because TestClient doesn't handle errors that occur
    # during StreamingResponse iteration in a way that can be tested with pytest.raises.
    # Streaming errors are propagated through the ASGI interface in a way that makes
    # them difficult to catch in unit tests. In production, these errors are logged
    # and the stream is terminated.
    async def failing_generator():
        raise RuntimeError("Stream failed")
        yield  # Never reached

    with patch(
        "src.api.endpoints.chat.sse_manager.stream_agent_response",
        return_value=failing_generator(),
    ):
        request_data = {
            "message": "Test",
        }

        response = app_client.post("/api/v1/chat/stream", json=request_data)
        assert response.status_code == 200


# ====================
# WebSocket Chat Endpoint Tests
# ====================


@pytest.mark.asyncio
async def test_websocket_chat_connection():
    """Test WebSocket chat connection and message handling."""
    from src.api.endpoints.chat import chat_websocket

    mock_websocket = Mock(spec=WebSocket)
    connection_id = str(uuid4())

    with (
        patch(
            "src.api.endpoints.chat.websocket_manager.connect",
            new_callable=AsyncMock,
            return_value=connection_id,
        ),
        patch(
            "src.api.endpoints.chat.websocket_manager.receive_loop",
            new_callable=AsyncMock,
        ) as mock_receive,
        patch(
            "src.api.endpoints.chat.websocket_manager.disconnect",
            new_callable=AsyncMock,
        ),
    ):
        await chat_websocket(mock_websocket)

        # Verify connection was established
        mock_receive.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_chat_message_handler():
    """Test WebSocket message handler for chat messages."""
    from src.api.endpoints.chat import chat_websocket

    mock_websocket = Mock(spec=WebSocket)
    connection_id = str(uuid4())

    # Capture the message handler
    captured_handler = None

    async def capture_handler(conn_id, handler):
        nonlocal captured_handler
        captured_handler = handler

    with (
        patch(
            "src.api.endpoints.chat.websocket_manager.connect",
            new_callable=AsyncMock,
            return_value=connection_id,
        ),
        patch(
            "src.api.endpoints.chat.websocket_manager.receive_loop",
            new_callable=AsyncMock,
            side_effect=capture_handler,
        ),
        patch(
            "src.api.endpoints.chat.websocket_manager.handle_agent_stream",
            new_callable=AsyncMock,
        ) as mock_stream,
        patch(
            "src.api.endpoints.chat.websocket_manager.send_message",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        await chat_websocket(mock_websocket)

        # Test chat message handling
        if captured_handler:
            await captured_handler(connection_id, {"type": "chat", "message": "Hello"})
            mock_stream.assert_called_once()

            # Test ping message
            await captured_handler(connection_id, {"type": "ping"})
            mock_send.assert_called_with(connection_id, {"type": "pong"})


@pytest.mark.asyncio
async def test_websocket_chat_error():
    """Test WebSocket error handling."""
    from src.api.endpoints.chat import chat_websocket

    mock_websocket = Mock(spec=WebSocket)

    with (
        patch(
            "src.api.endpoints.chat.websocket_manager.connect",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Connection failed"),
        ),
        patch(
            "src.api.endpoints.chat.websocket_manager.disconnect",
            new_callable=AsyncMock,
        ),
    ):
        # Should not raise
        await chat_websocket(mock_websocket)


# ====================
# Feedback Endpoint Tests
# ====================


def test_submit_feedback_success(app_client):
    """Test successful feedback submission."""
    feedback_data = {
        "message_id": str(uuid4()),
        "rating": 5,
        "comment": "Great response!",
    }

    response = app_client.post("/api/v1/chat/feedback", json=feedback_data)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "feedback_id" in data


def test_submit_feedback_minimal(app_client):
    """Test feedback submission with minimal data."""
    feedback_data = {
        "message_id": str(uuid4()),
        "rating": 3,
    }

    response = app_client.post("/api/v1/chat/feedback", json=feedback_data)

    assert response.status_code == 200


# ====================
# Session History Endpoint Tests
# ====================


def test_get_session_history_success(app_client):
    """Test getting session history."""
    session_id = str(uuid4())

    response = app_client.get(f"/api/v1/chat/sessions/{session_id}/history")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "messages" in data
    assert "total_messages" in data


def test_get_session_history_with_limit(app_client):
    """Test getting session history with limit."""
    session_id = str(uuid4())

    response = app_client.get(f"/api/v1/chat/sessions/{session_id}/history?limit=10")

    assert response.status_code == 200


# ====================
# Source Extraction Tests
# ====================


def test_extract_sources_from_messages_success():
    """Test source document extraction from messages."""
    from src.api.endpoints.chat import _extract_sources_from_messages

    # Create mock messages with tool returns
    mock_part = Mock()
    mock_part.tool_name = "retrieve_documents"
    mock_part.tool_return = [
        {
            "id": "doc-1",
            "content": "Test content 1",
            "similarity": 0.9,
            "metadata": {"key": "value"},
            "chunk_index": 0,
        },
        {
            "id": "doc-2",
            "content": "Test content 2",
            "similarity": 0.85,
        },
    ]

    mock_message = Mock()
    mock_message.parts = [mock_part]

    sources = _extract_sources_from_messages([mock_message])

    assert len(sources) == 2
    assert sources[0].document_id == "doc-1"
    assert sources[0].similarity_score == 0.9


def test_extract_sources_empty_messages():
    """Test source extraction with empty messages."""
    from src.api.endpoints.chat import _extract_sources_from_messages

    sources = _extract_sources_from_messages([])

    assert sources == []


def test_extract_sources_no_retrieval_tools():
    """Test source extraction with no retrieval tool calls."""
    from src.api.endpoints.chat import _extract_sources_from_messages

    mock_part = Mock()
    mock_part.tool_name = "web_search"
    mock_part.tool_return = {"results": []}

    mock_message = Mock()
    mock_message.parts = [mock_part]

    sources = _extract_sources_from_messages([mock_message])

    assert sources == []


def test_extract_sources_non_list_return():
    """Test source extraction with non-list tool return."""
    from src.api.endpoints.chat import _extract_sources_from_messages

    mock_part = Mock()
    mock_part.tool_name = "retrieve_documents"
    mock_part.tool_return = "not a list"

    mock_message = Mock()
    mock_message.parts = [mock_part]

    sources = _extract_sources_from_messages([mock_message])

    assert sources == []


def test_extract_sources_truncate_content():
    """Test that source content is truncated to 500 chars."""
    from src.api.endpoints.chat import _extract_sources_from_messages

    long_content = "x" * 1000

    mock_part = Mock()
    mock_part.tool_name = "retrieve_documents"
    mock_part.tool_return = [
        {
            "id": "doc-1",
            "content": long_content,
            "similarity": 0.9,
        }
    ]

    mock_message = Mock()
    mock_message.parts = [mock_part]

    sources = _extract_sources_from_messages([mock_message])

    assert len(sources) == 1
    assert len(sources[0].content) == 500


# ====================
# Metrics Tests
# ====================


def test_chat_metrics_recorded(app_client, mock_agent_deps, mock_cache, mock_agent_result):
    """Test that Prometheus metrics are recorded."""
    with (
        patch(
            "src.api.endpoints.chat.super_agent.run",
            new_callable=AsyncMock,
            return_value=mock_agent_result,
        ),
        patch("src.api.endpoints.chat.chat_requests_total") as mock_counter,
        patch("src.api.endpoints.chat.chat_duration") as mock_histogram,
    ):
        request_data = {
            "message": "Test",
            "stream": False,
        }

        response = app_client.post("/api/v1/chat", json=request_data)

        assert response.status_code == 200

        # Verify metrics were recorded
        mock_counter.labels.assert_called()
        mock_histogram.labels.assert_called()


# ====================
# Edge Cases
# ====================


def test_chat_empty_message(app_client, mock_agent_deps, mock_cache):
    """Test chat with empty message."""
    request_data = {
        "message": "",
        "stream": False,
    }

    response = app_client.post("/api/v1/chat", json=request_data)

    # Should either accept or return validation error
    assert response.status_code in [200, 422]


def test_chat_missing_session_id(app_client, mock_agent_deps, mock_cache, mock_agent_result):
    """Test chat without session_id (should use default)."""
    with patch(
        "src.api.endpoints.chat.super_agent.run",
        new_callable=AsyncMock,
        return_value=mock_agent_result,
    ):
        request_data = {
            "message": "Test",
            "stream": False,
        }

        response = app_client.post("/api/v1/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "default"


def test_chat_no_usage_in_result(app_client, mock_agent_deps, mock_cache):
    """Test chat when agent result has no usage info."""
    result = Mock()
    result.data = "Response"
    # Return empty dict for usage (no tokens)
    result.usage = Mock(return_value={})
    result.all_messages = Mock(return_value=[])

    with patch(
        "src.api.endpoints.chat.super_agent.run", new_callable=AsyncMock, return_value=result
    ):
        request_data = {
            "message": "Test",
            "stream": False,
        }

        response = app_client.post("/api/v1/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["tokens_used"] == 0


def test_chat_result_as_string(app_client, mock_agent_deps, mock_cache):
    """Test chat when agent result is just a string."""
    result = "Simple string response"

    with patch(
        "src.api.endpoints.chat.super_agent.run", new_callable=AsyncMock, return_value=result
    ):
        request_data = {
            "message": "Test",
            "stream": False,
        }

        response = app_client.post("/api/v1/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Simple string response"
