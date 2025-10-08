"""
Streaming utilities for SSE and WebSocket support.

Handles token streaming, heartbeats, backpressure, and connection lifecycle.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from pydantic_ai import Agent
from pydantic_ai.result import StreamedRunResult

logger = structlog.get_logger()


class SSEManager:
    """
    Server-Sent Events (SSE) manager for streaming responses.

    Handles token streaming, heartbeat, and backpressure.
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        chunk_size: int = 5,
    ):
        """
        Initialize SSE manager.

        Args:
            heartbeat_interval: Seconds between heartbeat messages
            chunk_size: Number of tokens per chunk
        """
        self.heartbeat_interval = heartbeat_interval
        self.chunk_size = chunk_size

    async def stream_agent_response(
        self, agent: Agent, message: str, deps: Any, **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream agent response as SSE events.

        Args:
            agent: Pydantic AI agent instance
            message: User message
            deps: Agent dependencies
            **kwargs: Additional agent run parameters

        Yields:
            SSE-formatted event strings
        """
        event_id = str(uuid4())

        try:
            # Start agent run with streaming
            async with agent.run_stream(message, deps=deps, **kwargs) as result:
                # Send start event
                yield self._format_event(
                    event="start", data={"message_id": event_id}, event_id=event_id
                )

                # Stream content chunks
                async for chunk in self._chunk_stream(result):
                    yield self._format_event(
                        event="content", data={"text": chunk}, event_id=event_id
                    )

                # Get final result with metadata
                final_result = await result

                # Send completion event with metadata
                yield self._format_event(
                    event="done",
                    data={
                        "message_id": event_id,
                        "usage": final_result.usage() if hasattr(final_result, "usage") else {},
                    },
                    event_id=event_id,
                )

        except asyncio.CancelledError:
            logger.info("stream_cancelled", event_id=event_id)
            yield self._format_event(
                event="cancelled", data={"message_id": event_id}, event_id=event_id
            )
            raise

        except Exception as e:
            logger.error("stream_error", event_id=event_id, error=str(e))
            yield self._format_event(
                event="error", data={"message_id": event_id, "error": str(e)}, event_id=event_id
            )

    async def _chunk_stream(self, result: StreamedRunResult) -> AsyncGenerator[str, None]:
        """
        Chunk streamed result into smaller pieces.

        Args:
            result: Streamed agent result

        Yields:
            Content chunks
        """
        buffer = ""
        word_count = 0

        async for text in result.stream_text(delta=True):
            buffer += text
            word_count += len(text.split())

            # Yield chunk when buffer reaches chunk_size words
            if word_count >= self.chunk_size:
                yield buffer
                buffer = ""
                word_count = 0

                # Small delay for backpressure
                await asyncio.sleep(0.01)

        # Yield remaining buffer
        if buffer:
            yield buffer

    def _format_event(
        self,
        event: str,
        data: dict[str, Any],
        event_id: str | None = None,
        retry: int | None = None,
    ) -> str:
        """
        Format data as SSE event.

        Args:
            event: Event type
            data: Event data
            event_id: Optional event ID
            retry: Optional retry timeout in ms

        Returns:
            SSE-formatted string
        """
        lines = []

        if event_id:
            lines.append(f"id: {event_id}")

        lines.append(f"event: {event}")

        # Serialize data as JSON
        data_json = json.dumps(data)
        lines.append(f"data: {data_json}")

        if retry:
            lines.append(f"retry: {retry}")

        # SSE format requires \n\n at the end
        return "\n".join(lines) + "\n\n"

    async def heartbeat_generator(self) -> AsyncGenerator[str, None]:
        """
        Generate heartbeat messages to keep connection alive.

        Yields:
            SSE heartbeat events
        """
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            yield self._format_event(
                event="heartbeat", data={"timestamp": asyncio.get_event_loop().time()}
            )


class WebSocketManager:
    """
    WebSocket manager for real-time bidirectional communication.

    Handles connection lifecycle, message routing, and error resilience.
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str | None = None) -> str:
        """
        Accept and register WebSocket connection.

        Args:
            websocket: WebSocket instance
            client_id: Optional client ID

        Returns:
            Connection ID
        """
        await websocket.accept()

        connection_id = client_id or str(uuid4())
        self.active_connections[connection_id] = websocket

        logger.info("websocket_connected", connection_id=connection_id)

        # Send welcome message
        await self.send_message(
            connection_id,
            {"type": "connection", "status": "connected", "connection_id": connection_id},
        )

        return connection_id

    async def disconnect(self, connection_id: str):
        """
        Close and unregister WebSocket connection.

        Args:
            connection_id: Connection ID to disconnect
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]

            try:
                await websocket.close()
            except Exception as e:
                logger.error("websocket_close_error", connection_id=connection_id, error=str(e))

            del self.active_connections[connection_id]
            logger.info("websocket_disconnected", connection_id=connection_id)

    async def send_message(self, connection_id: str, message: dict[str, Any]):
        """
        Send message to specific connection.

        Args:
            connection_id: Target connection ID
            message: Message data to send
        """
        if connection_id not in self.active_connections:
            logger.warning("websocket_send_failed_not_found", connection_id=connection_id)
            return

        websocket = self.active_connections[connection_id]

        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("websocket_send_error", connection_id=connection_id, error=str(e))
            # Disconnect on error
            await self.disconnect(connection_id)

    async def broadcast(self, message: dict[str, Any]):
        """
        Broadcast message to all connections.

        Args:
            message: Message data to broadcast
        """
        disconnected = []

        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("websocket_broadcast_error", connection_id=connection_id, error=str(e))
                disconnected.append(connection_id)

        # Clean up failed connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)

    async def handle_agent_stream(
        self, connection_id: str, agent: Agent, message: str, deps: Any, **kwargs
    ):
        """
        Stream agent response through WebSocket.

        Args:
            connection_id: Target connection ID
            agent: Pydantic AI agent instance
            message: User message
            deps: Agent dependencies
            **kwargs: Additional agent run parameters
        """
        try:
            # Send start message
            await self.send_message(
                connection_id, {"type": "stream_start", "message_id": str(uuid4())}
            )

            # Stream response
            async with agent.run_stream(message, deps=deps, **kwargs) as result:
                async for text in result.stream_text(delta=True):
                    await self.send_message(
                        connection_id, {"type": "stream_chunk", "content": text}
                    )

                # Get final result
                final_result = await result

                # Send completion message
                await self.send_message(
                    connection_id,
                    {
                        "type": "stream_complete",
                        "usage": final_result.usage() if hasattr(final_result, "usage") else {},
                    },
                )

        except WebSocketDisconnect:
            logger.info("websocket_disconnected_during_stream", connection_id=connection_id)
            await self.disconnect(connection_id)

        except Exception as e:
            logger.error("websocket_stream_error", connection_id=connection_id, error=str(e))
            await self.send_message(connection_id, {"type": "stream_error", "error": str(e)})

    async def receive_loop(self, connection_id: str, message_handler: callable):
        """
        Receive messages from WebSocket in loop.

        Args:
            connection_id: Connection ID
            message_handler: Async function to handle received messages
        """
        if connection_id not in self.active_connections:
            return

        websocket = self.active_connections[connection_id]

        try:
            while True:
                # Receive message
                data = await websocket.receive_json()

                # Handle message
                await message_handler(connection_id, data)

        except WebSocketDisconnect:
            logger.info("websocket_client_disconnected", connection_id=connection_id)
            await self.disconnect(connection_id)

        except Exception as e:
            logger.error("websocket_receive_error", connection_id=connection_id, error=str(e))
            await self.disconnect(connection_id)


# Singleton instances
sse_manager = SSEManager()
websocket_manager = WebSocketManager()
