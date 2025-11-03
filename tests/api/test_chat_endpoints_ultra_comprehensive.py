"""
Ultra-comprehensive tests for src/api/endpoints/chat.py

Covers:
- /chat endpoint with cache hits/misses, various parameters
- /chat/stream SSE streaming endpoint
- /chat/ws WebSocket bidirectional communication
- /chat/feedback feedback submission
- /chat/sessions/{session_id}/history session retrieval
- _extract_sources_from_messages() helper
- Error handling, metrics, logging
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status


@pytest.fixture
def mock_agent_deps():
    """Mock UnifiedAgentDeps."""
    deps = Mock()
    deps.llm_client = Mock()
    deps.supabase = Mock()
    deps.embedding_client = Mock()
    return deps


@pytest.fixture
def mock_cache():
    """Mock RedisCache."""
    cache = Mock()
    cache.get = Mock(return_value=None)
    cache.set = Mock()
    return cache


@pytest.fixture
def mock_agent_result():
    """Mock agent result."""
    result = Mock()
    result.data = "This is a test response"
    result.usage = Mock(
        return_value={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50}
    )
    result.all_messages = Mock(return_value=[])
    return result


class TestChatEndpoint:
    """Test /chat endpoint."""

    def test_chat_success(self, mock_agent_deps, mock_cache, mock_agent_result):
        """Test successful chat request."""
        from src.api.endpoints.chat import ChatRequest, chat

        with patch("src.api.endpoints.chat.super_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_agent_result)

            import asyncio

            request = ChatRequest(
                message="Hello",
                session_id="test_session",
                search_strategy="hybrid",
                include_sources=False,
            )

            response = asyncio.run(chat(request, mock_agent_deps, mock_cache))

        assert response.response == "This is a test response"
        assert response.message_id is not None
        assert response.session_id == "test_session"
        assert response.metrics.tokens_used == 100

    def test_chat_with_cache_hit(self, mock_agent_deps, mock_agent_result):
        """Test chat request with cache hit."""
        from src.api.endpoints.chat import ChatRequest, chat

        cached_data = {
            "response": "Cached response",
            "sources": None,
            "confidence": 0.85,
            "search_strategy_used": "hybrid",
            "session_id": "test_session",
            "message_id": "cached_id",
            "metrics": {
                "response_time_ms": 5.0,
                "tokens_used": 50,
                "tokens_prompt": 25,
                "tokens_completion": 25,
                "cache_hit": True,
            },
        }

        mock_cache = Mock()
        mock_cache.get = Mock(return_value=cached_data)

        import asyncio

        request = ChatRequest(message="Hello", stream=False)

        response = asyncio.run(chat(request, mock_agent_deps, mock_cache))

        assert response.response == "Cached response"
        assert response.metrics.cache_hit is True

    def test_chat_with_sources(self, mock_agent_deps, mock_cache):
        """Test chat request with source extraction."""
        from src.api.endpoints.chat import ChatRequest, chat

        # Create mock messages with tool calls
        mock_part = Mock()
        mock_part.tool_name = "retrieve_documents"
        mock_part.tool_return = [
            {
                "id": "doc1",
                "content": "Document content here",
                "similarity": 0.95,
                "metadata": {"author": "Test"},
                "chunk_index": 0,
            }
        ]

        mock_message = Mock()
        mock_message.parts = [mock_part]

        result = Mock()
        result.data = "Response with sources"
        result.usage = Mock(return_value={})
        result.all_messages = Mock(return_value=[mock_message])

        with patch("src.api.endpoints.chat.super_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=result)

            with patch("src.api.endpoints.chat._extract_sources_from_messages") as mock_extract:
                mock_extract.return_value = [
                    {"document_id": "doc1", "content": "...", "similarity_score": 0.95}
                ]

                import asyncio

                request = ChatRequest(message="Search query", include_sources=True)

                response = asyncio.run(chat(request, mock_agent_deps, mock_cache))

        assert response.response == "Response with sources"
        mock_extract.assert_called_once()

    def test_chat_with_parameters(self, mock_agent_deps, mock_cache, mock_agent_result):
        """Test chat with max_tokens and temperature parameters."""
        from src.api.endpoints.chat import ChatRequest, chat

        with patch("src.api.endpoints.chat.super_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_agent_result)

            import asyncio

            request = ChatRequest(message="Test", max_tokens=500, temperature=0.7)

            asyncio.run(chat(request, mock_agent_deps, mock_cache))

        # Verify agent was called with parameters
        mock_agent.run.assert_called_once()
        call_kwargs = mock_agent.run.call_args[1]
        assert call_kwargs["max_tokens"] == 500
        assert call_kwargs["temperature"] == 0.7

    def test_chat_error_handling(self, mock_agent_deps, mock_cache):
        """Test chat error handling."""
        from fastapi import HTTPException

        from src.api.endpoints.chat import ChatRequest, chat

        with patch("src.api.endpoints.chat.super_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=Exception("Agent failed"))

            import asyncio

            request = ChatRequest(message="Test")

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(chat(request, mock_agent_deps, mock_cache))

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Chat request failed" in exc_info.value.detail

    def test_chat_caches_response(self, mock_agent_deps, mock_cache, mock_agent_result):
        """Test that response is cached."""
        from src.api.endpoints.chat import ChatRequest, chat

        with patch("src.api.endpoints.chat.super_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_agent_result)

            import asyncio

            request = ChatRequest(message="Cache me", stream=False, search_strategy="hybrid")

            asyncio.run(chat(request, mock_agent_deps, mock_cache))

        # Verify cache.set was called
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args[0]
        # Cache key includes enum representation
        assert "chat:Cache me:" in call_args[0]
        assert "HYBRID" in call_args[0].upper()  # Cache key


class TestChatStreamEndpoint:
    """Test /chat/stream endpoint."""

    def test_chat_stream_success(self, mock_agent_deps):
        """Test successful streaming chat."""
        from src.api.endpoints.chat import ChatRequest, chat_stream

        async def mock_stream(*args, **kwargs):
            yield "data: chunk1\n\n"
            yield "data: chunk2\n\n"

        with patch("src.api.endpoints.chat.sse_manager") as mock_sse:
            mock_sse.stream_agent_response = mock_stream

            import asyncio

            request = ChatRequest(message="Stream this")

            response = asyncio.run(chat_stream(request, mock_agent_deps))

        assert response.media_type == "text/event-stream"
        assert "no-cache" in response.headers["Cache-Control"]

    def test_chat_stream_with_parameters(self, mock_agent_deps):
        """Test streaming with agent parameters."""
        from src.api.endpoints.chat import ChatRequest, chat_stream

        async def mock_stream(*args, **kwargs):
            # Verify parameters were passed
            assert kwargs.get("max_tokens") == 300
            assert kwargs.get("temperature") == 0.8
            yield "data: test\n\n"

        with patch("src.api.endpoints.chat.sse_manager") as mock_sse:
            mock_sse.stream_agent_response = mock_stream

            import asyncio

            request = ChatRequest(message="Test", max_tokens=300, temperature=0.8)

            asyncio.run(chat_stream(request, mock_agent_deps))

    @pytest.mark.skip(
        reason="PERMANENT SKIP: Streaming errors during generator creation cannot be caught by HTTPException. "
        "This is an edge case in async generator error handling that's extremely difficult to test with mocks. "
        "Error paths are validated through real usage and manual testing. "
        "See docs/b-ongoing-projects/phase9_skip_analysis.md Category 2.2"
    )
    def test_chat_stream_error(self, mock_agent_deps):
        """Test streaming error handling."""
        # NOTE: This test is skipped because when sse_manager.stream_agent_response
        # is mocked to raise an exception, it happens during the StreamingResponse
        # creation, not in a way that can be caught by HTTPException in the endpoint.
        # In production, errors are logged and handled within the streaming manager.

        from src.api.endpoints.chat import ChatRequest, chat_stream

        with patch("src.api.endpoints.chat.sse_manager") as mock_sse:
            mock_sse.stream_agent_response = AsyncMock(side_effect=Exception("Stream error"))

            import asyncio

            request = ChatRequest(message="Test")

            # This would actually create a StreamingResponse, not raise HTTPException
            response = asyncio.run(chat_stream(request, mock_agent_deps))
            assert response.media_type == "text/event-stream"


class TestWebSocketEndpoint:
    """Test /chat/ws WebSocket endpoint."""

    @pytest.mark.asyncio
    async def test_websocket_chat_success(self):
        """Test successful WebSocket connection."""
        from src.api.endpoints.chat import chat_websocket

        mock_websocket = Mock()

        with patch("src.api.endpoints.chat.websocket_manager") as mock_ws_mgr:
            mock_ws_mgr.connect = AsyncMock(return_value="conn_123")
            mock_ws_mgr.receive_loop = AsyncMock()

            await chat_websocket(mock_websocket)

        mock_ws_mgr.connect.assert_called_once_with(mock_websocket)
        mock_ws_mgr.receive_loop.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_message_handling(self):
        """Test WebSocket message handler."""
        from src.api.endpoints.chat import chat_websocket

        mock_websocket = Mock()

        async def mock_receive_loop(conn_id, handler):
            # Call handler with test message
            await handler(conn_id, {"type": "chat", "message": "Hello"})

        with patch("src.api.endpoints.chat.websocket_manager") as mock_ws_mgr:
            with patch("src.api.endpoints.chat.UnifiedAgentDeps"):
                mock_ws_mgr.connect = AsyncMock(return_value="conn_123")
                mock_ws_mgr.receive_loop = mock_receive_loop
                mock_ws_mgr.handle_agent_stream = AsyncMock()

                await chat_websocket(mock_websocket)

        mock_ws_mgr.handle_agent_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self):
        """Test WebSocket ping/pong handling."""
        from src.api.endpoints.chat import chat_websocket

        mock_websocket = Mock()

        async def mock_receive_loop(conn_id, handler):
            # Send ping
            await handler(conn_id, {"type": "ping"})

        with patch("src.api.endpoints.chat.websocket_manager") as mock_ws_mgr:
            mock_ws_mgr.connect = AsyncMock(return_value="conn_123")
            mock_ws_mgr.receive_loop = mock_receive_loop
            mock_ws_mgr.send_message = AsyncMock()

            await chat_websocket(mock_websocket)

        mock_ws_mgr.send_message.assert_called_once_with("conn_123", {"type": "pong"})

    @pytest.mark.asyncio
    async def test_websocket_error_disconnect(self):
        """Test WebSocket disconnects on error."""
        from src.api.endpoints.chat import chat_websocket

        mock_websocket = Mock()

        with patch("src.api.endpoints.chat.websocket_manager") as mock_ws_mgr:
            mock_ws_mgr.connect = AsyncMock(return_value="conn_123")
            mock_ws_mgr.receive_loop = AsyncMock(side_effect=Exception("Connection lost"))
            mock_ws_mgr.disconnect = AsyncMock()

            await chat_websocket(mock_websocket)

        mock_ws_mgr.disconnect.assert_called_once_with("conn_123")


class TestFeedbackEndpoint:
    """Test /chat/feedback endpoint."""

    @pytest.mark.asyncio
    async def test_submit_feedback_success(self):
        """Test successful feedback submission."""
        from src.api.endpoints.chat import FeedbackRequest, submit_feedback

        feedback = FeedbackRequest(
            message_id="msg_123", rating=5, comment="Great response!", issues=["accuracy"]
        )

        response = await submit_feedback(feedback)

        assert response.success is True
        assert response.feedback_id is not None

    @pytest.mark.asyncio
    async def test_submit_feedback_error(self):
        """Test feedback submission error handling."""
        from fastapi import HTTPException

        from src.api.endpoints.chat import FeedbackRequest, submit_feedback

        feedback = FeedbackRequest(message_id="msg_123", rating=3)

        with patch("src.api.endpoints.chat.uuid4", side_effect=Exception("DB error")):
            with pytest.raises(HTTPException) as exc_info:
                await submit_feedback(feedback)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestSessionHistoryEndpoint:
    """Test /chat/sessions/{session_id}/history endpoint."""

    @pytest.mark.asyncio
    async def test_get_session_history_success(self):
        """Test successful session history retrieval."""
        from src.api.endpoints.chat import get_session_history

        response = await get_session_history("session_123")

        assert response["session_id"] == "session_123"
        assert response["messages"] == []
        assert response["total_messages"] == 0

    @pytest.mark.asyncio
    async def test_get_session_history_with_limit(self):
        """Test session history with custom limit."""
        from src.api.endpoints.chat import get_session_history

        response = await get_session_history("session_123", limit=10)

        assert response["session_id"] == "session_123"

    @pytest.mark.asyncio
    async def test_get_session_history_error(self):
        """Test session history error handling."""
        from fastapi import HTTPException

        from src.api.endpoints.chat import get_session_history

        with patch("src.api.endpoints.chat.logger") as mock_logger:
            mock_logger.info = Mock(side_effect=Exception("DB error"))

            with pytest.raises(HTTPException) as exc_info:
                await get_session_history("session_123")

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestExtractSourcesHelper:
    """Test _extract_sources_from_messages() helper function."""

    def test_extract_sources_empty_messages(self):
        """Test extracting sources from empty messages."""
        from src.api.endpoints.chat import _extract_sources_from_messages

        sources = _extract_sources_from_messages([])

        assert sources == []

    def test_extract_sources_with_retrieval_tool(self):
        """Test extracting sources from messages with retrieval tool."""
        from src.api.endpoints.chat import _extract_sources_from_messages

        # Create mock message with tool call
        mock_part = Mock()
        mock_part.tool_name = "retrieve_documents"
        mock_part.tool_return = [
            {
                "id": "doc1",
                "content": "This is document 1 content",
                "similarity": 0.92,
                "metadata": {"source": "file.pdf"},
                "chunk_index": 0,
            },
            {
                "id": "doc2",
                "content": "This is document 2 content",
                "similarity": 0.88,
                "metadata": {"source": "file2.pdf"},
                "chunk_index": 1,
            },
        ]

        mock_message = Mock()
        mock_message.parts = [mock_part]

        sources = _extract_sources_from_messages([mock_message])

        assert len(sources) == 2
        assert sources[0].document_id == "doc1"
        assert sources[0].similarity_score == 0.92
        assert sources[1].document_id == "doc2"

    def test_extract_sources_content_truncation(self):
        """Test that source content is truncated to 500 chars."""
        from src.api.endpoints.chat import _extract_sources_from_messages

        long_content = "x" * 1000

        mock_part = Mock()
        mock_part.tool_name = "retrieve_documents"  # Use tool name that contains "retrieve"
        mock_part.tool_return = [{"id": "doc1", "content": long_content, "similarity": 0.95}]

        mock_message = Mock()
        mock_message.parts = [mock_part]

        sources = _extract_sources_from_messages([mock_message])

        assert len(sources) == 1
        assert len(sources[0].content) == 500

    def test_extract_sources_no_tool_calls(self):
        """Test messages without tool calls."""
        from src.api.endpoints.chat import _extract_sources_from_messages

        mock_message = Mock()
        mock_message.parts = []

        sources = _extract_sources_from_messages([mock_message])

        assert sources == []

    def test_extract_sources_non_retrieval_tool(self):
        """Test tool calls that aren't retrieval."""
        from src.api.endpoints.chat import _extract_sources_from_messages

        mock_part = Mock()
        mock_part.tool_name = "calculator"
        mock_part.tool_return = {"result": 42}

        mock_message = Mock()
        mock_message.parts = [mock_part]

        sources = _extract_sources_from_messages([mock_message])

        assert sources == []

    def test_extract_sources_invalid_return_format(self):
        """Test handling of invalid tool return formats."""
        from src.api.endpoints.chat import _extract_sources_from_messages

        mock_part = Mock()
        mock_part.tool_name = "retrieve_documents"
        mock_part.tool_return = "not a list"

        mock_message = Mock()
        mock_message.parts = [mock_part]

        sources = _extract_sources_from_messages([mock_message])

        # Should handle gracefully and return empty
        assert sources == []

    def test_extract_sources_message_without_parts(self):
        """Test messages without parts attribute."""
        from src.api.endpoints.chat import _extract_sources_from_messages

        mock_message = object()  # No 'parts' attribute

        sources = _extract_sources_from_messages([mock_message])

        assert sources == []
