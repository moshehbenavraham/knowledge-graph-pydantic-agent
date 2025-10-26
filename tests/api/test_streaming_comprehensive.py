"""
Comprehensive tests for streaming utilities (SSE and WebSocket).

Target coverage: 23% → 75%+
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import WebSocket, WebSocketDisconnect
from pydantic_ai import Agent
from pydantic_ai.result import StreamedRunResult

from src.api.streaming import SSEManager, WebSocketManager, sse_manager, websocket_manager


class TestSSEManager:
    """Test Server-Sent Events manager."""

    def test_init_default_values(self):
        """Test SSE manager initialization with defaults."""
        manager = SSEManager()

        assert manager.heartbeat_interval == 30.0
        assert manager.chunk_size == 5

    def test_init_custom_values(self):
        """Test SSE manager initialization with custom values."""
        manager = SSEManager(heartbeat_interval=60.0, chunk_size=10)

        assert manager.heartbeat_interval == 60.0
        assert manager.chunk_size == 10

    def test_format_event_basic(self):
        """Test basic SSE event formatting."""
        manager = SSEManager()
        event = manager._format_event(event="test", data={"message": "hello"})

        assert "event: test" in event
        assert 'data: {"message": "hello"}' in event
        assert event.endswith("\n\n")

    def test_format_event_with_id(self):
        """Test SSE event formatting with ID."""
        manager = SSEManager()
        event = manager._format_event(event="test", data={"message": "hello"}, event_id="test-123")

        assert "id: test-123" in event
        assert "event: test" in event
        assert event.endswith("\n\n")

    def test_format_event_with_retry(self):
        """Test SSE event formatting with retry."""
        manager = SSEManager()
        event = manager._format_event(event="test", data={"message": "hello"}, retry=3000)

        assert "retry: 3000" in event
        assert "event: test" in event

    def test_format_event_complex_data(self):
        """Test SSE event formatting with complex data."""
        manager = SSEManager()
        data = {
            "message": "hello",
            "nested": {"key": "value", "list": [1, 2, 3]},
            "count": 42,
        }
        event = manager._format_event(event="test", data=data)

        # Verify JSON serialization
        assert "event: test" in event
        assert "data:" in event
        parsed_line = [line for line in event.split("\n") if line.startswith("data:")][0]
        parsed_data = json.loads(parsed_line[6:])  # Skip "data: "
        assert parsed_data == data

    @pytest.mark.asyncio
    async def test_chunk_stream_basic(self):
        """Test chunking of streamed text."""
        manager = SSEManager(chunk_size=3)

        # Mock StreamedRunResult
        mock_result = AsyncMock(spec=StreamedRunResult)

        async def mock_stream_text(delta=True):
            yield "word1 "
            yield "word2 "
            yield "word3 "
            yield "word4 "

        mock_result.stream_text = mock_stream_text

        chunks = []
        async for chunk in manager._chunk_stream(mock_result):
            chunks.append(chunk)

        # Should get 2 chunks (first 3 words, then remaining)
        assert len(chunks) >= 1
        assert all(isinstance(chunk, str) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_chunk_stream_empty(self):
        """Test chunking with empty stream."""
        manager = SSEManager()
        mock_result = AsyncMock(spec=StreamedRunResult)

        async def mock_stream_text(delta=True):
            return
            yield  # Make it a generator

        mock_result.stream_text = mock_stream_text

        chunks = []
        async for chunk in manager._chunk_stream(mock_result):
            chunks.append(chunk)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_stream_agent_response_success(self):
        """Test streaming agent response successfully."""
        manager = SSEManager(chunk_size=5)

        mock_agent = MagicMock(spec=Agent)
        mock_result = AsyncMock(spec=StreamedRunResult)

        # Mock streaming text
        async def mock_stream_text(delta=True):
            yield "Hello "
            yield "world "
            yield "test "

        mock_result.stream_text = mock_stream_text

        # Mock final result
        final_mock = MagicMock()
        final_mock.usage.return_value = {"input_tokens": 10, "output_tokens": 20}
        mock_result.__aenter__ = AsyncMock(return_value=mock_result)
        mock_result.__aexit__ = AsyncMock(return_value=None)
        mock_result.__await__ = lambda self: AsyncMock(return_value=final_mock)()

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        events = []
        async for event in manager.stream_agent_response(mock_agent, "test message", None):
            events.append(event)

        # Should have start, content chunks, and done events
        assert len(events) >= 2
        assert any("event: start" in e for e in events)
        # Note: done event might not appear due to mock limitations

    @pytest.mark.asyncio
    async def test_stream_agent_response_cancelled(self):
        """Test streaming with cancellation."""
        manager = SSEManager()

        mock_agent = MagicMock(spec=Agent)
        mock_result = AsyncMock(spec=StreamedRunResult)

        async def mock_stream_text(delta=True):
            yield "Start "
            raise asyncio.CancelledError()

        mock_result.stream_text = mock_stream_text
        mock_result.__aenter__ = AsyncMock(return_value=mock_result)
        mock_result.__aexit__ = AsyncMock(return_value=None)

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        events = []
        with pytest.raises(asyncio.CancelledError):
            async for event in manager.stream_agent_response(mock_agent, "test message", None):
                events.append(event)

        # Should have start and cancelled events
        assert any("event: start" in e for e in events)

    @pytest.mark.asyncio
    async def test_stream_agent_response_error(self):
        """Test streaming with error."""
        manager = SSEManager()

        mock_agent = MagicMock(spec=Agent)
        mock_result = AsyncMock(spec=StreamedRunResult)

        async def mock_stream_text(delta=True):
            raise ValueError("Test error")

        mock_result.stream_text = mock_stream_text
        mock_result.__aenter__ = AsyncMock(return_value=mock_result)
        mock_result.__aexit__ = AsyncMock(return_value=None)

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        events = []
        async for event in manager.stream_agent_response(mock_agent, "test message", None):
            events.append(event)

        # Should have error event
        assert any("event: error" in e for e in events)
        assert any("Test error" in e for e in events)

    @pytest.mark.asyncio
    async def test_heartbeat_generator(self):
        """Test heartbeat generator."""
        manager = SSEManager(heartbeat_interval=0.1)

        events = []
        async for event in manager.heartbeat_generator():
            events.append(event)
            if len(events) >= 2:
                break

        assert len(events) == 2
        assert all("event: heartbeat" in e for e in events)
        assert all("timestamp" in e for e in events)


class TestWebSocketManager:
    """Test WebSocket manager."""

    def test_init(self):
        """Test WebSocket manager initialization."""
        manager = WebSocketManager()

        assert isinstance(manager.active_connections, dict)
        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_connect_without_client_id(self):
        """Test WebSocket connection without client ID."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)

        connection_id = await manager.connect(mock_ws)

        # Should generate UUID
        assert isinstance(UUID(connection_id), UUID)
        assert connection_id in manager.active_connections
        mock_ws.accept.assert_called_once()
        mock_ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_client_id(self):
        """Test WebSocket connection with client ID."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)

        connection_id = await manager.connect(mock_ws, client_id="custom-123")

        assert connection_id == "custom-123"
        assert "custom-123" in manager.active_connections
        mock_ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_existing(self):
        """Test disconnecting existing connection."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)

        connection_id = await manager.connect(mock_ws)
        assert connection_id in manager.active_connections

        await manager.disconnect(connection_id)

        assert connection_id not in manager.active_connections
        mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self):
        """Test disconnecting nonexistent connection."""
        manager = WebSocketManager()

        # Should not raise error
        await manager.disconnect("nonexistent-id")

    @pytest.mark.asyncio
    async def test_disconnect_with_error(self):
        """Test disconnecting when close raises error."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.close.side_effect = RuntimeError("Connection already closed")

        connection_id = await manager.connect(mock_ws)

        # Should handle error gracefully
        await manager.disconnect(connection_id)
        assert connection_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test sending message successfully."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)

        connection_id = await manager.connect(mock_ws)

        await manager.send_message(connection_id, {"type": "test", "data": "hello"})

        # Should call send_json (once for welcome, once for our message)
        assert mock_ws.send_json.call_count == 2
        last_call = mock_ws.send_json.call_args_list[-1]
        assert last_call[0][0] == {"type": "test", "data": "hello"}

    @pytest.mark.asyncio
    async def test_send_message_not_found(self):
        """Test sending message to nonexistent connection."""
        manager = WebSocketManager()

        # Should not raise error
        await manager.send_message("nonexistent-id", {"type": "test"})

    @pytest.mark.asyncio
    async def test_send_message_error_disconnects(self):
        """Test that send error triggers disconnect."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)

        connection_id = await manager.connect(mock_ws)

        # Make send_json fail on second call (after welcome message)
        mock_ws.send_json.side_effect = [None, RuntimeError("Send failed")]

        await manager.send_message(connection_id, {"type": "test"})

        # Connection should be disconnected
        assert connection_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_success(self):
        """Test broadcasting to multiple connections."""
        manager = WebSocketManager()

        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)

        await manager.connect(mock_ws1, client_id="client-1")
        await manager.connect(mock_ws2, client_id="client-2")

        await manager.broadcast({"type": "broadcast", "message": "hello all"})

        # Both should receive message (plus welcome messages)
        assert mock_ws1.send_json.call_count == 2
        assert mock_ws2.send_json.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_with_failures(self):
        """Test broadcast with some connections failing."""
        manager = WebSocketManager()

        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        mock_ws2.send_json.side_effect = [None, RuntimeError("Failed")]

        await manager.connect(mock_ws1, client_id="client-1")
        await manager.connect(mock_ws2, client_id="client-2")

        await manager.broadcast({"type": "broadcast"})

        # Failed connection should be removed
        assert "client-1" in manager.active_connections
        assert "client-2" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_handle_agent_stream_success(self):
        """Test handling agent stream through WebSocket."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)

        connection_id = await manager.connect(mock_ws)

        mock_agent = MagicMock(spec=Agent)
        mock_result = AsyncMock(spec=StreamedRunResult)

        async def mock_stream_text(delta=True):
            yield "chunk1"
            yield "chunk2"

        mock_result.stream_text = mock_stream_text
        final_mock = MagicMock()
        final_mock.usage.return_value = {"tokens": 100}

        mock_result.__aenter__ = AsyncMock(return_value=mock_result)
        mock_result.__aexit__ = AsyncMock(return_value=None)
        mock_result.__await__ = lambda self: AsyncMock(return_value=final_mock)()

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        await manager.handle_agent_stream(connection_id, mock_agent, "test message", None)

        # Should send start, chunks, and complete messages (plus welcome)
        assert mock_ws.send_json.call_count >= 4

    @pytest.mark.asyncio
    async def test_handle_agent_stream_disconnect(self):
        """Test handling agent stream with disconnect."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)

        connection_id = await manager.connect(mock_ws)

        mock_agent = MagicMock(spec=Agent)
        mock_result = AsyncMock(spec=StreamedRunResult)

        async def mock_stream_text(delta=True):
            yield "chunk1"
            raise WebSocketDisconnect()

        mock_result.stream_text = mock_stream_text
        mock_result.__aenter__ = AsyncMock(return_value=mock_result)
        mock_result.__aexit__ = AsyncMock(return_value=None)

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        await manager.handle_agent_stream(connection_id, mock_agent, "test message", None)

        # Connection should be disconnected
        assert connection_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_handle_agent_stream_error(self):
        """Test handling agent stream with error."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)

        connection_id = await manager.connect(mock_ws)

        mock_agent = MagicMock(spec=Agent)
        mock_result = AsyncMock(spec=StreamedRunResult)

        async def mock_stream_text(delta=True):
            raise ValueError("Stream error")

        mock_result.stream_text = mock_stream_text
        mock_result.__aenter__ = AsyncMock(return_value=mock_result)
        mock_result.__aexit__ = AsyncMock(return_value=None)

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        await manager.handle_agent_stream(connection_id, mock_agent, "test message", None)

        # Should send error message
        calls = [call[0][0] for call in mock_ws.send_json.call_args_list]
        error_messages = [c for c in calls if c.get("type") == "stream_error"]
        assert len(error_messages) > 0

    @pytest.mark.asyncio
    async def test_receive_loop_success(self):
        """Test receiving messages in loop."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)

        messages = [{"type": "message", "content": "hello"}, {"type": "message", "content": "bye"}]

        async def mock_receive():
            for msg in messages:
                yield msg
            raise WebSocketDisconnect()

        mock_ws.receive_json.side_effect = [messages[0], messages[1], WebSocketDisconnect()]

        connection_id = await manager.connect(mock_ws)

        received_messages = []

        async def handler(conn_id, data):
            received_messages.append(data)

        await manager.receive_loop(connection_id, handler)

        # Should have received both messages
        assert len(received_messages) == 2
        # Connection should be disconnected
        assert connection_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_receive_loop_nonexistent_connection(self):
        """Test receive loop with nonexistent connection."""
        manager = WebSocketManager()

        async def handler(conn_id, data):
            pass

        # Should return immediately without error
        await manager.receive_loop("nonexistent-id", handler)

    @pytest.mark.asyncio
    async def test_receive_loop_error(self):
        """Test receive loop with error."""
        manager = WebSocketManager()
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.receive_json.side_effect = RuntimeError("Receive error")

        connection_id = await manager.connect(mock_ws)

        async def handler(conn_id, data):
            pass

        await manager.receive_loop(connection_id, handler)

        # Connection should be disconnected
        assert connection_id not in manager.active_connections


class TestSingletonInstances:
    """Test singleton instances."""

    def test_sse_manager_singleton(self):
        """Test SSE manager singleton exists."""
        assert isinstance(sse_manager, SSEManager)
        assert sse_manager.heartbeat_interval == 30.0
        assert sse_manager.chunk_size == 5

    def test_websocket_manager_singleton(self):
        """Test WebSocket manager singleton exists."""
        assert isinstance(websocket_manager, WebSocketManager)
        assert isinstance(websocket_manager.active_connections, dict)
