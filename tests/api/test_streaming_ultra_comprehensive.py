"""
ULTRA Comprehensive tests for streaming utilities.

Target coverage: 23% → 95%+

Tests SSEManager, WebSocketManager, streaming, heartbeats,
connection lifecycle, error handling, and backpressure.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocketDisconnect

from src.api.streaming import (
    SSEManager,
    WebSocketManager,
    sse_manager,
    websocket_manager,
)


class TestSSEManagerInit:
    """Test SSEManager initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        manager = SSEManager()

        assert manager.heartbeat_interval == 30.0
        assert manager.chunk_size == 5

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        manager = SSEManager(heartbeat_interval=60.0, chunk_size=10)

        assert manager.heartbeat_interval == 60.0
        assert manager.chunk_size == 10


class TestSSEManagerFormatEvent:
    """Test SSE event formatting."""

    def test_format_event_basic(self):
        """Test basic event formatting."""
        manager = SSEManager()

        event = manager._format_event(event="test", data={"message": "hello"})

        assert "event: test" in event
        assert "data: " in event
        assert "hello" in event
        assert event.endswith("\n\n")

    def test_format_event_with_id(self):
        """Test event formatting with event ID."""
        manager = SSEManager()

        event = manager._format_event(event="test", data={"message": "hello"}, event_id="event-123")

        assert "id: event-123" in event

    def test_format_event_with_retry(self):
        """Test event formatting with retry timeout."""
        manager = SSEManager()

        event = manager._format_event(event="test", data={"value": 1}, retry=5000)

        assert "retry: 5000" in event

    def test_format_event_json_serialization(self):
        """Test that data is properly JSON serialized."""
        manager = SSEManager()

        data = {"key": "value", "number": 42, "nested": {"item": "test"}}
        event = manager._format_event(event="test", data=data)

        # Extract data line
        for line in event.split("\n"):
            if line.startswith("data: "):
                json_data = json.loads(line[6:])  # Remove "data: " prefix
                assert json_data == data


class TestSSEManagerChunkStream:
    """Test stream chunking."""

    @pytest.mark.asyncio
    async def test_chunk_stream_single_word(self):
        """Test chunking single word."""
        manager = SSEManager(chunk_size=5)

        mock_result = AsyncMock()

        async def mock_stream():
            yield "word "

        mock_result.stream_text = MagicMock(return_value=mock_stream())

        chunks = []
        async for chunk in manager._chunk_stream(mock_result):
            chunks.append(chunk)

        assert chunks == ["word "]

    @pytest.mark.asyncio
    async def test_chunk_stream_multiple_chunks(self):
        """Test chunking multiple words into chunks."""
        manager = SSEManager(chunk_size=2)  # 2 words per chunk

        mock_result = AsyncMock()

        async def mock_stream():
            yield "word1 "
            yield "word2 "
            yield "word3 "
            yield "word4 "

        mock_result.stream_text = MagicMock(return_value=mock_stream())

        chunks = []
        async for chunk in manager._chunk_stream(mock_result):
            chunks.append(chunk)

        # Should create 2 chunks: "word1 word2 " and "word3 word4 "
        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_chunk_stream_yields_remaining_buffer(self):
        """Test that remaining buffer is yielded."""
        manager = SSEManager(chunk_size=10)

        mock_result = AsyncMock()

        async def mock_stream():
            yield "small "
            yield "text"

        mock_result.stream_text = MagicMock(return_value=mock_stream())

        chunks = []
        async for chunk in manager._chunk_stream(mock_result):
            chunks.append(chunk)

        # Should yield remaining buffer even if smaller than chunk_size
        assert len(chunks) == 1
        assert chunks[0] == "small text"


class TestSSEManagerStreamAgentResponse:
    """Test streaming agent response as SSE."""

    @pytest.mark.asyncio
    async def test_stream_agent_response_success(self):
        """Test successful agent response streaming."""
        manager = SSEManager()

        mock_agent = MagicMock()

        # Create a proper mock that supports async with and await
        async def mock_stream():
            yield "test "
            yield "response"

        class MockStreamResult:
            def __init__(self):
                self.stream_text_value = mock_stream()

            def stream_text(self, **kwargs):
                # Accept any kwargs (like delta=True)
                return self.stream_text_value

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            def __await__(self):
                # Return self when awaited
                async def _await():
                    return self

                return _await().__await__()

            def usage(self):
                return {"tokens": 10}

        mock_result = MockStreamResult()
        mock_agent.run_stream = MagicMock(return_value=mock_result)

        events = []
        async for event in manager.stream_agent_response(
            agent=mock_agent, message="test", deps=None
        ):
            events.append(event)

        # Should have start, content, and done events
        assert len(events) >= 3
        assert any("event: start" in e for e in events)
        assert any("event: content" in e for e in events)
        assert any("event: done" in e for e in events)

    @pytest.mark.asyncio
    async def test_stream_agent_response_cancelled(self):
        """Test handling of cancelled stream."""
        manager = SSEManager()

        mock_agent = MagicMock()
        mock_result = AsyncMock()
        mock_result.__aenter__ = AsyncMock(side_effect=asyncio.CancelledError())
        mock_result.__aexit__ = AsyncMock(return_value=None)

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        events = []
        with pytest.raises(asyncio.CancelledError):
            async for event in manager.stream_agent_response(
                agent=mock_agent, message="test", deps=None
            ):
                events.append(event)

        # Should have start and cancelled events
        assert any("event: cancelled" in e for e in events)

    @pytest.mark.asyncio
    async def test_stream_agent_response_error(self):
        """Test handling of stream error."""
        manager = SSEManager()

        mock_agent = MagicMock()
        mock_result = AsyncMock()
        mock_result.__aenter__ = AsyncMock(side_effect=Exception("Stream error"))
        mock_result.__aexit__ = AsyncMock(return_value=None)

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        events = []
        async for event in manager.stream_agent_response(
            agent=mock_agent, message="test", deps=None
        ):
            events.append(event)

        # Should have error event
        assert any("event: error" in e for e in events)
        assert any("Stream error" in e for e in events)


class TestSSEManagerHeartbeat:
    """Test heartbeat generation."""

    @pytest.mark.asyncio
    async def test_heartbeat_generator(self):
        """Test heartbeat message generation."""
        manager = SSEManager(heartbeat_interval=0.1)

        # Collect a few heartbeats
        heartbeats = []
        async for heartbeat in manager.heartbeat_generator():
            heartbeats.append(heartbeat)
            if len(heartbeats) >= 2:
                break

        assert len(heartbeats) == 2
        assert all("event: heartbeat" in hb for hb in heartbeats)


class TestWebSocketManagerInit:
    """Test WebSocketManager initialization."""

    def test_init(self):
        """Test initialization."""
        manager = WebSocketManager()

        assert manager.active_connections == {}


class TestWebSocketManagerConnect:
    """Test WebSocket connection handling."""

    @pytest.mark.asyncio
    async def test_connect_new_websocket(self):
        """Test connecting new WebSocket."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        connection_id = await manager.connect(mock_websocket)

        assert connection_id in manager.active_connections
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_custom_client_id(self):
        """Test connecting with custom client ID."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        connection_id = await manager.connect(mock_websocket, client_id="custom-id")

        assert connection_id == "custom-id"
        assert connection_id in manager.active_connections

    @pytest.mark.asyncio
    async def test_connect_sends_welcome_message(self):
        """Test that welcome message is sent."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()

        await manager.connect(mock_websocket)

        # Should send welcome message
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connection"
        assert call_args["status"] == "connected"


class TestWebSocketManagerDisconnect:
    """Test WebSocket disconnection."""

    @pytest.mark.asyncio
    async def test_disconnect_existing_connection(self):
        """Test disconnecting existing connection."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()

        connection_id = await manager.connect(mock_websocket)
        await manager.disconnect(connection_id)

        assert connection_id not in manager.active_connections
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self):
        """Test disconnecting nonexistent connection (no error)."""
        manager = WebSocketManager()

        await manager.disconnect("nonexistent-id")  # Should not raise

    @pytest.mark.asyncio
    async def test_disconnect_close_error(self):
        """Test handling error during close."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        mock_websocket.close.side_effect = Exception("Close error")

        connection_id = await manager.connect(mock_websocket)
        await manager.disconnect(connection_id)

        # Should still remove from active connections
        assert connection_id not in manager.active_connections


class TestWebSocketManagerSendMessage:
    """Test sending messages."""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message send."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()

        connection_id = await manager.connect(mock_websocket)
        mock_websocket.send_json.reset_mock()  # Clear welcome message call

        message = {"type": "test", "data": "hello"}
        await manager.send_message(connection_id, message)

        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_message_connection_not_found(self):
        """Test sending to nonexistent connection."""
        manager = WebSocketManager()

        # Should not raise, just log warning
        await manager.send_message("nonexistent-id", {"test": "data"})

    @pytest.mark.asyncio
    async def test_send_message_error_disconnects(self):
        """Test that send error triggers disconnect."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("Send error")

        connection_id = await manager.connect(mock_websocket)

        await manager.send_message(connection_id, {"test": "data"})

        # Should disconnect on error
        assert connection_id not in manager.active_connections


class TestWebSocketManagerBroadcast:
    """Test broadcasting messages."""

    @pytest.mark.asyncio
    async def test_broadcast_to_all_connections(self):
        """Test broadcasting to all connections."""
        manager = WebSocketManager()

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)

        # Reset call counts
        mock_ws1.send_json.reset_mock()
        mock_ws2.send_json.reset_mock()

        message = {"type": "broadcast", "data": "test"}
        await manager.broadcast(message)

        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_disconnects_failed_connections(self):
        """Test that failed broadcasts trigger disconnect."""
        manager = WebSocketManager()

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send_json.side_effect = Exception("Send error")

        id1 = await manager.connect(mock_ws1)
        id2 = await manager.connect(mock_ws2)

        await manager.broadcast({"test": "data"})

        # ws1 should still be connected, ws2 should be disconnected
        assert id1 in manager.active_connections
        assert id2 not in manager.active_connections


class TestWebSocketManagerHandleAgentStream:
    """Test agent streaming through WebSocket."""

    @pytest.mark.asyncio
    async def test_handle_agent_stream_success(self):
        """Test successful agent streaming."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()

        connection_id = await manager.connect(mock_websocket)
        mock_websocket.send_json.reset_mock()

        mock_agent = MagicMock()
        mock_result = AsyncMock()

        async def mock_stream():
            yield "test "
            yield "response"

        mock_result.stream_text = MagicMock(return_value=mock_stream())
        mock_result.__aenter__ = AsyncMock(return_value=mock_result)
        mock_result.__aexit__ = AsyncMock(return_value=None)
        mock_result.__await__ = lambda self: asyncio.coroutine(lambda: mock_result)()
        mock_result.usage = MagicMock(return_value={"tokens": 10})

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        await manager.handle_agent_stream(
            connection_id=connection_id, agent=mock_agent, message="test", deps=None
        )

        # Should have sent start, chunks, and complete messages
        assert mock_websocket.send_json.call_count >= 3

    @pytest.mark.asyncio
    async def test_handle_agent_stream_websocket_disconnect(self):
        """Test handling WebSocket disconnect during stream."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()

        connection_id = await manager.connect(mock_websocket)

        mock_agent = MagicMock()
        mock_result = AsyncMock()
        mock_result.__aenter__ = AsyncMock(side_effect=WebSocketDisconnect())
        mock_result.__aexit__ = AsyncMock(return_value=None)

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        await manager.handle_agent_stream(
            connection_id=connection_id, agent=mock_agent, message="test", deps=None
        )

        # Should disconnect
        assert connection_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_handle_agent_stream_error(self):
        """Test handling error during stream."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()

        connection_id = await manager.connect(mock_websocket)
        mock_websocket.send_json.reset_mock()

        mock_agent = MagicMock()
        mock_result = AsyncMock()
        mock_result.__aenter__ = AsyncMock(side_effect=Exception("Stream error"))
        mock_result.__aexit__ = AsyncMock(return_value=None)

        mock_agent.run_stream = MagicMock(return_value=mock_result)

        await manager.handle_agent_stream(
            connection_id=connection_id, agent=mock_agent, message="test", deps=None
        )

        # Should send error message
        error_calls = [
            call
            for call in mock_websocket.send_json.call_args_list
            if call[0][0].get("type") == "stream_error"
        ]
        assert len(error_calls) > 0


class TestWebSocketManagerReceiveLoop:
    """Test WebSocket receive loop."""

    @pytest.mark.asyncio
    async def test_receive_loop_processes_messages(self):
        """Test that receive loop processes messages."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()

        messages = [{"type": "test1"}, {"type": "test2"}]
        mock_websocket.receive_json.side_effect = messages + [WebSocketDisconnect()]

        connection_id = await manager.connect(mock_websocket)

        received_messages = []

        async def message_handler(conn_id, data):
            received_messages.append(data)

        await manager.receive_loop(connection_id, message_handler)

        assert len(received_messages) == 2
        assert received_messages[0]["type"] == "test1"
        assert received_messages[1]["type"] == "test2"

    @pytest.mark.asyncio
    async def test_receive_loop_handles_disconnect(self):
        """Test handling WebSocket disconnect in receive loop."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        mock_websocket.receive_json.side_effect = WebSocketDisconnect()

        connection_id = await manager.connect(mock_websocket)

        await manager.receive_loop(connection_id, lambda x, y: None)

        # Should disconnect
        assert connection_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_receive_loop_handles_error(self):
        """Test handling error in receive loop."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        mock_websocket.receive_json.side_effect = Exception("Receive error")

        connection_id = await manager.connect(mock_websocket)

        await manager.receive_loop(connection_id, lambda x, y: None)

        # Should disconnect on error
        assert connection_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_receive_loop_nonexistent_connection(self):
        """Test receive loop with nonexistent connection."""
        manager = WebSocketManager()

        # Should return immediately without error
        await manager.receive_loop("nonexistent-id", lambda x, y: None)


class TestSingletonInstances:
    """Test singleton instances."""

    def test_sse_manager_instance_exists(self):
        """Test that SSE manager singleton exists."""
        assert isinstance(sse_manager, SSEManager)

    def test_websocket_manager_instance_exists(self):
        """Test that WebSocket manager singleton exists."""
        assert isinstance(websocket_manager, WebSocketManager)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
