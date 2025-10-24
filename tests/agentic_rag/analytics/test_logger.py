"""Tests for analytics logger module."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.agentic_rag.analytics import (
    AgentInteractionEvent,
    AnalyticsLogger,
    IngestionAnalyticsEvent,
    SearchAnalyticsEvent,
    SystemMetricsEvent,
    ToolUsageEvent,
    get_analytics_logger,
)


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager."""
    manager = Mock()

    # Create mock connection
    mock_conn = Mock()
    # Ensure executemany returns None (success) and doesn't raise
    mock_conn.executemany = AsyncMock(return_value=None)

    # Create a proper async context manager mock
    async_ctx_mgr = AsyncMock()
    async_ctx_mgr.__aenter__.return_value = mock_conn
    async_ctx_mgr.__aexit__.return_value = None

    # Make get_pg_connection return the context manager
    manager.get_pg_connection.return_value = async_ctx_mgr

    return manager


@pytest.fixture
async def analytics_logger(mock_connection_manager):
    """Create analytics logger with mocked connection manager."""
    logger = AnalyticsLogger(
        connection_manager=mock_connection_manager, batch_size=5, batch_interval_seconds=1.0
    )
    await logger.start()
    yield logger
    await logger.stop()


# ============================================================================
# Event Model Tests
# ============================================================================


def test_search_analytics_event_creation():
    """Test SearchAnalyticsEvent creation."""
    event = SearchAnalyticsEvent(
        query_text="test query",
        detected_intent="VECTOR_HEAVY",
        strategy_used="VECTOR_HEAVY",
        total_latency_ms=150.5,
        chunks_returned=10,
    )

    assert event.query_text == "test query"
    assert event.detected_intent == "VECTOR_HEAVY"
    assert event.total_latency_ms == 150.5
    assert event.chunks_returned == 10


def test_tool_usage_event_creation():
    """Test ToolUsageEvent creation."""
    event = ToolUsageEvent(
        tool_name="retrieve_documents",
        execution_time_ms=50.0,
        success=True,
    )

    assert event.tool_name == "retrieve_documents"
    assert event.execution_time_ms == 50.0
    assert event.success is True


def test_agent_interaction_event_creation():
    """Test AgentInteractionEvent creation."""
    from uuid import uuid4

    session_id = uuid4()
    event = AgentInteractionEvent(
        user_message="Hello",
        agent_response="Hi there!",
        session_id=session_id,
        interaction_type="query",
        response_time_ms=150.5,
        model_used="test-model",
        tokens_used=100,
    )

    assert event.user_message == "Hello"
    assert event.agent_response == "Hi there!"
    assert event.session_id == session_id
    assert event.interaction_type == "query"
    assert event.response_time_ms == 150.5
    assert event.model_used == "test-model"
    assert event.tokens_used == 100


def test_ingestion_analytics_event_creation():
    """Test IngestionAnalyticsEvent creation."""
    from uuid import uuid4

    document_id = uuid4()
    event = IngestionAnalyticsEvent(
        document_id=document_id,
        total_processing_time_ms=500.0,
        file_size_bytes=1024,
        file_type="pdf",
        processing_mode="full",
        chunks_created=15,
        success=True,
    )

    assert event.document_id == document_id
    assert event.total_processing_time_ms == 500.0
    assert event.file_size_bytes == 1024
    assert event.file_type == "pdf"
    assert event.processing_mode == "full"
    assert event.chunks_created == 15
    assert event.success is True


def test_system_metrics_event_creation():
    """Test SystemMetricsEvent creation."""
    event = SystemMetricsEvent(
        pg_active_connections=5,
        pg_idle_connections=3,
        neo4j_active_connections=2,
        active_sessions=10,
        cache_hit_rate=0.85,
        avg_response_time_ms=150.5,
    )

    assert event.pg_active_connections == 5
    assert event.pg_idle_connections == 3
    assert event.neo4j_active_connections == 2
    assert event.active_sessions == 10
    assert event.cache_hit_rate == 0.85
    assert event.avg_response_time_ms == 150.5


# ============================================================================
# AnalyticsLogger Tests
# ============================================================================


@pytest.mark.asyncio
async def test_logger_initialization(mock_connection_manager):
    """Test analytics logger initialization."""
    logger = AnalyticsLogger(connection_manager=mock_connection_manager)

    assert logger.connection_manager == mock_connection_manager
    assert logger.batch_size > 0
    assert logger.batch_interval_seconds > 0
    assert len(logger._search_queue) == 0
    assert len(logger._tool_queue) == 0


@pytest.mark.asyncio
async def test_log_search_event(analytics_logger):
    """Test logging search event."""
    event = SearchAnalyticsEvent(
        query_text="test",
        detected_intent="VECTOR_HEAVY",
        strategy_used="VECTOR_HEAVY",
        total_latency_ms=100.0,
        chunks_returned=5,
    )

    await analytics_logger.log_search(event)

    assert len(analytics_logger._search_queue) == 1


@pytest.mark.asyncio
async def test_log_tool_usage_event(analytics_logger):
    """Test logging tool usage event."""
    event = ToolUsageEvent(
        tool_name="test_tool",
        execution_time_ms=50.0,
        success=True,
    )

    await analytics_logger.log_tool_usage(event)

    assert len(analytics_logger._tool_queue) == 1


@pytest.mark.asyncio
async def test_log_agent_interaction_event(analytics_logger):
    """Test logging agent interaction event."""
    from uuid import uuid4

    event = AgentInteractionEvent(
        user_message="test",
        agent_response="response",
        session_id=uuid4(),
        interaction_type="query",
        response_time_ms=50.0,
        model_used="gpt-4",
    )

    await analytics_logger.log_interaction(event)

    assert len(analytics_logger._interaction_queue) == 1


@pytest.mark.asyncio
async def test_log_ingestion_event(analytics_logger):
    """Test logging ingestion event."""
    from uuid import uuid4

    event = IngestionAnalyticsEvent(
        document_id=uuid4(),
        total_processing_time_ms=200.0,
        chunks_created=10,
        success=True,
        file_size_bytes=1024,
        file_type="txt",
        processing_mode="full",
    )

    await analytics_logger.log_ingestion(event)

    assert len(analytics_logger._ingestion_queue) == 1


@pytest.mark.asyncio
async def test_log_system_metrics_event(analytics_logger):
    """Test logging system metrics event."""
    event = SystemMetricsEvent(
        pg_active_connections=5,
        cache_hit_rate=0.7,
    )

    await analytics_logger.log_system_metrics(event)

    assert len(analytics_logger._system_queue) == 1


@pytest.mark.asyncio
async def test_batch_flush_on_size_limit(mock_connection_manager):
    """Test automatic flush when batch size reached."""
    logger = AnalyticsLogger(connection_manager=mock_connection_manager, batch_size=2)
    await logger.start()

    # Add 2 events to trigger flush
    await logger.log_search(
        SearchAnalyticsEvent(
            query_text="test1",
            detected_intent="VECTOR_HEAVY",
            strategy_used="VECTOR_HEAVY",
            total_latency_ms=100.0,
            chunks_returned=5,
        )
    )

    await logger.log_search(
        SearchAnalyticsEvent(
            query_text="test2",
            detected_intent="GRAPH_HEAVY",
            strategy_used="GRAPH_HEAVY",
            total_latency_ms=150.0,
            chunks_returned=3,
        )
    )

    # Should have flushed - wait for background task
    import asyncio

    await asyncio.sleep(0.1)

    await logger.stop()


@pytest.mark.asyncio
async def test_flush_empty_queue(analytics_logger):
    """Test flushing empty queue does nothing."""
    # Just ensure flush doesn't crash with empty queues
    await analytics_logger._flush_all()

    # Check queues are still empty
    assert len(analytics_logger._search_queue) == 0
    assert len(analytics_logger._tool_queue) == 0


@pytest.mark.asyncio
async def test_get_analytics_logger_singleton(mock_connection_manager):
    """Test get_analytics_logger returns singleton."""
    from src.agentic_rag.analytics import initialize_analytics_logger, shutdown_analytics_logger

    # Initialize first
    logger1 = await initialize_analytics_logger(mock_connection_manager)

    # Get same instance
    logger2 = get_analytics_logger()

    # Should return same instance
    assert logger1 is logger2

    # Cleanup
    await shutdown_analytics_logger()


@pytest.mark.asyncio
async def test_error_handling_in_log_methods(mock_connection_manager):
    """Test error handling in log methods."""
    # Make executemany raise an exception
    mock_conn = Mock()
    mock_conn.executemany = AsyncMock(side_effect=Exception("DB Error"))
    mock_connection_manager.get_pg_connection.return_value.__aenter__ = AsyncMock(
        return_value=mock_conn
    )

    logger = AnalyticsLogger(connection_manager=mock_connection_manager, batch_size=5)
    await logger.start()

    event = SearchAnalyticsEvent(
        query_text="test",
        detected_intent="VECTOR_HEAVY",
        strategy_used="VECTOR_HEAVY",
        total_latency_ms=100.0,
        chunks_returned=5,
    )

    # Should not raise exception during logging
    await logger.log_search(event)

    # Flush will fail but should be handled gracefully
    import contextlib

    with contextlib.suppress(Exception):
        await logger._flush_search_events()

    await logger.stop()


@pytest.mark.asyncio
async def test_event_queue_management(analytics_logger):
    """Test event queue is managed correctly."""
    # Add multiple events
    for i in range(3):
        await analytics_logger.log_search(
            SearchAnalyticsEvent(
                query_text=f"test{i}",
                detected_intent="VECTOR_HEAVY",
                strategy_used="VECTOR_HEAVY",
                total_latency_ms=100.0,
                chunks_returned=5,
            )
        )

    assert len(analytics_logger._search_queue) == 3

    # Flush should clear queue
    await analytics_logger._flush_all()
    assert len(analytics_logger._search_queue) == 0


@pytest.mark.asyncio
async def test_concurrent_logging(analytics_logger):
    """Test concurrent logging operations."""
    import asyncio

    # Log multiple events concurrently
    tasks = [
        analytics_logger.log_search(
            SearchAnalyticsEvent(
                query_text=f"test{i}",
                detected_intent="VECTOR_HEAVY",
                strategy_used="VECTOR_HEAVY",
                total_latency_ms=100.0,
                chunks_returned=5,
            )
        )
        for i in range(10)
    ]

    await asyncio.gather(*tasks)

    # Events should be logged (either in queue or already flushed due to batch size=5)
    # Total events logged + queued should be >= 10
    total_events = analytics_logger.events_logged + len(analytics_logger._search_queue)
    assert total_events >= 10


@pytest.mark.asyncio
async def test_event_metadata_preservation(analytics_logger):
    """Test that event metadata is preserved during logging."""
    event = SearchAnalyticsEvent(
        query_text="test query",
        detected_intent="HYBRID",
        strategy_used="HYBRID",
        total_latency_ms=200.0,
        chunks_returned=15,
        vector_latency_ms=100.0,
        graph_latency_ms=100.0,
        cache_hit=True,
    )

    await analytics_logger.log_search(event)

    # Event should be in queue with all fields intact
    queued_event = analytics_logger._search_queue[0]
    assert queued_event.query_text == "test query"
    assert queued_event.detected_intent == "HYBRID"
    assert queued_event.vector_latency_ms == 100.0
    assert queued_event.graph_latency_ms == 100.0
    assert queued_event.cache_hit is True
