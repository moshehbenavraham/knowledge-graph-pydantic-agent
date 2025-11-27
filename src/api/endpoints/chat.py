"""
Chat endpoints for conversational interaction.

Provides synchronous, SSE streaming, and WebSocket interfaces.
"""

import time
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from fastapi.responses import StreamingResponse
from prometheus_client import Counter, Histogram

from src.agent.unified_agent import UnifiedAgentDeps, super_agent
from src.api.dependencies import get_agent_deps, get_cache_manager
from src.api.models import (
    ChatMetrics,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    SourceDocument,
)
from src.api.streaming import sse_manager, websocket_manager
from src.utils.cache import RedisCache

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Metrics
chat_requests_total = Counter("chat_requests_total", "Total chat requests", ["endpoint", "status"])
chat_duration = Histogram("chat_duration_seconds", "Chat request duration", ["endpoint"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    deps: UnifiedAgentDeps = Depends(get_agent_deps),
    cache: RedisCache = Depends(get_cache_manager),
) -> ChatResponse:
    """
    Synchronous chat endpoint.

    Processes message through unified agent and returns response with sources.
    """
    start_time = time.perf_counter()
    message_id = str(uuid4())

    # Check cache if enabled
    cache_key = f"chat:{request.message}:{request.search_strategy}"
    cached_response = None

    if not request.stream:
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.info("cache_hit", message_id=message_id)
            chat_requests_total.labels(endpoint="chat", status="cache_hit").inc()
            return ChatResponse(**cached_response)

    try:
        # Run agent
        logger.info(
            "chat_request_started",
            message_id=message_id,
            session_id=request.session_id,
        )

        # Note: max_tokens and temperature should be configured at model creation time
        # For now, we'll execute without these runtime parameters
        # TODO: Add support for runtime model parameters via model_settings

        # Execute agent
        result = await super_agent.run(request.message, deps=deps)

        # Extract response data
        response_text = result.data if hasattr(result, "data") else str(result)

        # Get usage metrics
        usage: dict[str, Any] = result.usage() if hasattr(result, "usage") else {}  # type: ignore[assignment]

        # Build sources if available
        sources = []
        if request.include_sources and hasattr(result, "all_messages"):
            sources = _extract_sources_from_messages(result.all_messages())

        # Calculate metrics
        duration_ms = (time.perf_counter() - start_time) * 1000

        response = ChatResponse(
            response=response_text,
            sources=sources if sources else None,
            confidence=0.85,  # TODO: Implement confidence scoring
            search_strategy_used=request.search_strategy,
            session_id=request.session_id or "default",
            message_id=message_id,
            metrics=ChatMetrics(
                response_time_ms=duration_ms,
                search_time_ms=None,
                llm_time_ms=None,
                tokens_used=usage.get("total_tokens", 0),
                tokens_prompt=usage.get("prompt_tokens", 0),
                tokens_completion=usage.get("completion_tokens", 0),
                cache_hit=False,
            ),
        )

        # Cache response
        if not request.stream:
            cache.set(cache_key, response.model_dump(), ttl=300)

        # Record metrics
        chat_requests_total.labels(endpoint="chat", status="success").inc()
        chat_duration.labels(endpoint="chat").observe(duration_ms / 1000)

        logger.info(
            "chat_request_completed",
            message_id=message_id,
            duration_ms=duration_ms,
        )

        return response

    except Exception as e:
        logger.error(
            "chat_request_failed",
            message_id=message_id,
            error=str(e),
        )
        chat_requests_total.labels(endpoint="chat", status="error").inc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat request failed: {e!s}",
        )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    deps: UnifiedAgentDeps = Depends(get_agent_deps),
) -> StreamingResponse:
    """
    Streaming chat endpoint using SSE.

    Returns Server-Sent Events stream of response chunks.
    """
    logger.info("chat_stream_started", session_id=request.session_id)

    # Configure agent parameters
    agent_params: dict[str, Any] = {}
    if request.max_tokens:
        agent_params["max_tokens"] = request.max_tokens
    if request.temperature:
        agent_params["temperature"] = request.temperature

    try:
        # Stream response
        async def event_generator() -> AsyncGenerator[str, None]:
            async for event in sse_manager.stream_agent_response(
                agent=super_agent, message=request.message, deps=deps, **agent_params
            ):
                yield event

        chat_requests_total.labels(endpoint="chat_stream", status="started").inc()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error("chat_stream_failed", error=str(e))
        chat_requests_total.labels(endpoint="chat_stream", status="error").inc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stream failed: {e!s}",
        )


@router.websocket("/ws")
async def chat_websocket(
    websocket: WebSocket,
    deps: UnifiedAgentDeps = Depends(get_agent_deps),
) -> None:
    """
    WebSocket endpoint for bidirectional chat.

    Supports real-time streaming and interactive conversations.
    """
    connection_id = None

    try:
        # Accept connection
        connection_id = await websocket_manager.connect(  # Constitution exception: CONST-III-001 - WebSocket connection method
            websocket
        )  # Constitution exception: CONST-III-001 - WebSocket connection, not client instantiation

        logger.info("websocket_chat_started", connection_id=connection_id)

        # Message handler
        async def handle_message(conn_id: str, data: dict[str, Any]) -> None:
            """Handle received WebSocket messages."""
            message_type = data.get("type", "chat")

            if message_type == "chat":
                # Stream agent response using injected deps
                await websocket_manager.handle_agent_stream(
                    connection_id=conn_id,
                    agent=super_agent,
                    message=data.get("message", ""),
                    deps=deps,
                )

            elif message_type == "ping":
                await websocket_manager.send_message(conn_id, {"type": "pong"})

        # Start receive loop
        await websocket_manager.receive_loop(connection_id, handle_message)

    except Exception as e:
        logger.error(
            "websocket_chat_error",
            connection_id=connection_id,
            error=str(e),
        )
        if connection_id:
            await websocket_manager.disconnect(connection_id)


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
) -> FeedbackResponse:
    """
    Submit user feedback on chat response.

    Captures ratings and issues for response improvement.
    """
    try:
        # TODO: Store feedback in database
        feedback_id = str(uuid4())

        logger.info(
            "feedback_received",
            message_id=feedback.message_id,
            rating=feedback.rating,
            feedback_id=feedback_id,
        )

        return FeedbackResponse(
            success=True,
            feedback_id=feedback_id,
        )

    except Exception as e:
        logger.error("feedback_submission_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback",
        )


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Get chat history for session.

    Returns previous messages in chronological order.
    """
    try:
        # TODO: Implement session history retrieval from database
        logger.info("session_history_requested", session_id=session_id)

        return {
            "session_id": session_id,
            "messages": [],
            "total_messages": 0,
        }

    except Exception as e:
        logger.error("session_history_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session history",
        )


def _extract_sources_from_messages(messages: list) -> list[SourceDocument]:
    """
    Extract source documents from agent messages.

    Args:
        messages: List of agent messages

    Returns:
        List of source documents
    """
    sources = []

    for message in messages:
        # Look for tool calls with document retrieval
        if hasattr(message, "parts"):
            for part in message.parts:
                if hasattr(part, "tool_name") and "retrieve" in part.tool_name.lower():
                    # Extract source from tool response
                    if hasattr(part, "tool_return"):
                        tool_return = part.tool_return
                        if isinstance(tool_return, list):
                            for item in tool_return:
                                if isinstance(item, dict):
                                    sources.append(
                                        SourceDocument(
                                            document_id=item.get("id", "unknown"),
                                            content=item.get("content", "")[:500],
                                            similarity_score=item.get("similarity", 0.0),
                                            metadata=item.get("metadata"),
                                            chunk_index=item.get("chunk_index"),
                                        )
                                    )

    return sources
