"""
Comprehensive unit tests for analytics logger.

Tests event validation, batching, flushing, error handling, and performance.
Target: >90% coverage.
"""

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.agentic_rag.analytics import (
    AgentInteractionEvent,
    AnalyticsLogger,
    IngestionAnalyticsEvent,
    SearchAnalyticsEvent,
    SystemMetricsEvent,
    ToolUsageEvent,
    get_analytics_logger,
    initialize_analytics_logger,
    shutdown_analytics_logger,
)


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager."""
    manager = MagicMock()

    # Create mock connection
    mock_conn = MagicMock()
    mock_conn.executemany = AsyncMock()

    # Make get_pg_connection return a proper async context manager
    async_context = AsyncMock()
    async_context.__aenter__ = AsyncMock(return_value=mock_conn)
    async_context.__aexit__ = AsyncMock(return_value=None)

    manager.get_pg_connection = MagicMock(return_value=async_context)

    return manager


@pytest.fixture
def analytics_logger(mock_connection_manager):
    """Create analytics logger instance for testing."""
    logger = AnalyticsLogger(mock_connection_manager, batch_size=10, batch_interval_seconds=0.1)
    # Don't auto-start here - let tests control lifecycle
    return logger


class TestSearchAnalyticsEvent:
    """Test SearchAnalyticsEvent validation."""

    def test_valid_search_event(self):
        """Test creating valid search analytics event."""
        event = SearchAnalyticsEvent(
            query_text="test query",
            detected_intent="VECTOR_HEAVY",
            strategy_used="VECTOR_HEAVY",
            total_latency_ms=150.5,
        )
        assert event.query_text == "test query"
        assert event.detected_intent == "VECTOR_HEAVY"
        assert event.total_latency_ms == 150.5
        assert event.query_hash  # Auto-generated

    def test_query_hash_auto_generation(self):
        """Test query hash is auto-generated from query_text."""
        event = SearchAnalyticsEvent(
            query_text="test query",
            detected_intent="HYBRID",
            strategy_used="HYBRID",
            total_latency_ms=100.0,
        )
        assert event.query_hash
        assert len(event.query_hash) == 32  # MD5 hex digest

    def test_invalid_intent(self):
        """Test validation fails with invalid intent."""
        with pytest.raises(ValueError):
            SearchAnalyticsEvent(
                query_text="test",
                detected_intent="INVALID",
                strategy_used="VECTOR_HEAVY",
                total_latency_ms=100.0,
            )

    def test_negative_latency(self):
        """Test validation fails with negative latency."""
        with pytest.raises(ValueError):
            SearchAnalyticsEvent(
                query_text="test",
                detected_intent="VECTOR_HEAVY",
                strategy_used="VECTOR_HEAVY",
                total_latency_ms=-10.0,
            )

    def test_empty_query_text(self):
        """Test validation fails with empty query text."""
        with pytest.raises(ValueError):
            SearchAnalyticsEvent(
                query_text="",
                detected_intent="VECTOR_HEAVY",
                strategy_used="VECTOR_HEAVY",
                total_latency_ms=100.0,
            )

    def test_optional_fields(self):
        """Test optional fields have correct defaults."""
        event = SearchAnalyticsEvent(
            query_text="test",
            detected_intent="GRAPH_HEAVY",
            strategy_used="GRAPH_HEAVY",
            total_latency_ms=100.0,
        )
        assert event.vector_latency_ms == 0
        assert event.graph_latency_ms == 0
        assert event.chunks_returned == 0
        assert event.cache_hit is False
        assert event.entities_found == 0
        assert event.source == "ui"
        assert event.metadata == {}


class TestToolUsageEvent:
    """Test ToolUsageEvent validation."""

    def test_valid_tool_event(self):
        """Test creating valid tool usage event."""
        event = ToolUsageEvent(
            tool_name="retrieve_documents",
            execution_time_ms=50.0,
            success=True,
        )
        assert event.tool_name == "retrieve_documents"
        assert event.execution_time_ms == 50.0
        assert event.success is True

    def test_tool_event_with_error(self):
        """Test tool event with error information."""
        event = ToolUsageEvent(
            tool_name="sql_query",
            execution_time_ms=25.0,
            success=False,
            error_type="ValueError",
            error_message="Invalid query syntax",
        )
        assert event.success is False
        assert event.error_type == "ValueError"
        assert event.error_message == "Invalid query syntax"

    def test_invalid_triggered_by(self):
        """Test validation fails with invalid triggered_by."""
        with pytest.raises(ValueError):
            ToolUsageEvent(
                tool_name="test_tool",
                execution_time_ms=10.0,
                success=True,
                triggered_by="invalid",
            )


class TestAgentInteractionEvent:
    """Test AgentInteractionEvent validation."""

    def test_valid_interaction_event(self):
        """Test creating valid interaction event."""
        session_id = uuid4()
        event = AgentInteractionEvent(
            session_id=session_id,
            interaction_type="query",
            user_message="What is RAG?",
            agent_response="RAG stands for Retrieval Augmented Generation...",
            response_time_ms=1500.0,
            model_used="gpt-4",
            tools_called=["retrieve_documents"],
            rag_used=True,
        )
        assert event.session_id == session_id
        assert event.interaction_type == "query"
        assert event.response_time_ms == 1500.0
        assert event.rag_used is True

    def test_invalid_interaction_type(self):
        """Test validation fails with invalid interaction type."""
        with pytest.raises(ValueError):
            AgentInteractionEvent(
                session_id=uuid4(),
                interaction_type="invalid",
                user_message="test",
                agent_response="test",
                response_time_ms=100.0,
                model_used="gpt-4",
            )

    def test_invalid_feedback(self):
        """Test validation fails with invalid feedback."""
        with pytest.raises(ValueError):
            AgentInteractionEvent(
                session_id=uuid4(),
                interaction_type="query",
                user_message="test",
                agent_response="test",
                response_time_ms=100.0,
                model_used="gpt-4",
                user_feedback="invalid",
            )


class TestIngestionAnalyticsEvent:
    """Test IngestionAnalyticsEvent validation."""

    def test_valid_ingestion_event(self):
        """Test creating valid ingestion event."""
        event = IngestionAnalyticsEvent(
            document_id=uuid4(),
            total_processing_time_ms=5000.0,
            chunks_created=50,
            entities_extracted=25,
            relationships_extracted=15,
            success=True,
            file_size_bytes=102400,
            file_type="pdf",
            processing_mode="full",
        )
        assert event.success is True
        assert event.chunks_created == 50
        assert event.entities_extracted == 25

    def test_invalid_processing_mode(self):
        """Test validation fails with invalid processing mode."""
        with pytest.raises(ValueError):
            IngestionAnalyticsEvent(
                document_id=uuid4(),
                total_processing_time_ms=1000.0,
                success=True,
                file_size_bytes=1024,
                file_type="txt",
                processing_mode="invalid",
            )


class TestSystemMetricsEvent:
    """Test SystemMetricsEvent validation."""

    def test_valid_system_metrics(self):
        """Test creating valid system metrics event."""
        event = SystemMetricsEvent(
            pg_active_connections=10,
            pg_idle_connections=5,
            pg_total_queries=1000,
            cache_hit_rate=0.85,
            active_sessions=3,
        )
        assert event.pg_active_connections == 10
        assert event.cache_hit_rate == 0.85

    def test_invalid_cache_hit_rate(self):
        """Test validation fails with invalid cache hit rate."""
        with pytest.raises(ValueError):
            SystemMetricsEvent(cache_hit_rate=1.5)

    def test_invalid_error_rate(self):
        """Test validation fails with invalid error rate."""
        with pytest.raises(ValueError):
            SystemMetricsEvent(error_rate=-0.1)


class TestAnalyticsLogger:
    """Test AnalyticsLogger functionality."""

    @pytest.mark.asyncio
    async def test_logger_initialization(self, mock_connection_manager):
        """Test logger initializes correctly."""
        logger = AnalyticsLogger(mock_connection_manager)
        assert logger.events_logged == 0
        assert logger.events_failed == 0
        assert logger._running is False

    @pytest.mark.asyncio
    async def test_logger_start_stop(self, analytics_logger):
        """Test logger starts and stops correctly."""
        await analytics_logger.start()

        assert analytics_logger._running is True
        assert analytics_logger._flush_task is not None

        await analytics_logger.stop()
        assert analytics_logger._running is False

    @pytest.mark.asyncio
    async def test_log_search_event(self, analytics_logger):
        """Test logging search event."""
        event = SearchAnalyticsEvent(
            query_text="test query",
            detected_intent="VECTOR_HEAVY",
            strategy_used="VECTOR_HEAVY",
            total_latency_ms=100.0,
        )

        await analytics_logger.log_search(event)
        assert len(analytics_logger._search_queue) == 1

    @pytest.mark.asyncio
    async def test_log_tool_event(self, analytics_logger):
        """Test logging tool usage event."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            execution_time_ms=50.0,
            success=True,
        )

        await analytics_logger.log_tool_usage(event)
        assert len(analytics_logger._tool_queue) == 1

    @pytest.mark.asyncio
    async def test_batch_flush_on_size(self, analytics_logger):
        """Test automatic flush when batch size reached."""
        await analytics_logger.start()
        try:
            # Add more events than batch size
            for i in range(15):
                event = SearchAnalyticsEvent(
                    query_text=f"query {i}",
                    detected_intent="HYBRID",
                    strategy_used="HYBRID",
                    total_latency_ms=100.0,
                )
                await analytics_logger.log_search(event)

            # Wait for flush
            await asyncio.sleep(0.2)

            # Queue should be smaller than what we added (some flushed)
            assert len(analytics_logger._search_queue) < 15
        finally:
            await analytics_logger.stop()

    @pytest.mark.asyncio
    async def test_periodic_flush(self, analytics_logger):
        """Test periodic flush based on interval."""
        await analytics_logger.start()
        try:
            event = SearchAnalyticsEvent(
                query_text="test",
                detected_intent="VECTOR_HEAVY",
                strategy_used="VECTOR_HEAVY",
                total_latency_ms=100.0,
            )
            await analytics_logger.log_search(event)

            # Wait for flush interval (0.1s + buffer)
            await asyncio.sleep(0.3)

            # Queue should be empty after flush
            assert len(analytics_logger._search_queue) == 0
        finally:
            await analytics_logger.stop()

    @pytest.mark.asyncio
    async def test_get_stats(self, analytics_logger):
        """Test getting logger statistics."""
        stats = analytics_logger.get_stats()

        assert "events_logged" in stats
        assert "events_failed" in stats
        assert "queue_sizes" in stats
        assert "last_flush" in stats
        assert "running" in stats

        assert stats["running"] is True
        assert stats["queue_sizes"]["search"] == 0

    @pytest.mark.asyncio
    async def test_error_handling_in_flush(self, mock_connection_manager):
        """Test error handling during flush."""
        # Make executemany raise an exception
        mock_conn = MagicMock()
        mock_conn.executemany = AsyncMock(side_effect=Exception("Database error"))

        mock_connection_manager.get_pg_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )

        logger = AnalyticsLogger(mock_connection_manager, batch_size=5)
        await logger.start()

        # Add event
        event = SearchAnalyticsEvent(
            query_text="test",
            detected_intent="VECTOR_HEAVY",
            strategy_used="VECTOR_HEAVY",
            total_latency_ms=100.0,
        )
        await logger.log_search(event)

        # Try to flush
        with contextlib.suppress(Exception):
            await logger._flush_search_events()  # Expected to raise

        # Event should be back in queue for retry
        assert len(logger._search_queue) == 1

        await logger.stop()

    @pytest.mark.asyncio
    async def test_concurrent_logging(self, analytics_logger):
        """Test concurrent logging from multiple tasks."""

        async def log_events(count: int):
            for i in range(count):
                event = SearchAnalyticsEvent(
                    query_text=f"concurrent query {i}",
                    detected_intent="HYBRID",
                    strategy_used="HYBRID",
                    total_latency_ms=100.0,
                )
                await analytics_logger.log_search(event)

        # Run multiple concurrent logging tasks
        await asyncio.gather(log_events(5), log_events(5), log_events(5))

        # Wait for flushes
        await asyncio.sleep(0.3)

        # All events should be logged
        assert analytics_logger.events_logged > 0


class TestGlobalSingletonFunctions:
    """Test global singleton functions."""

    @pytest.mark.asyncio
    async def test_initialize_and_get_logger(self, mock_connection_manager):
        """Test initialize and get analytics logger."""
        # Initialize
        logger = await initialize_analytics_logger(mock_connection_manager)
        assert logger is not None
        assert logger._running is True

        # Get same instance
        same_logger = get_analytics_logger()
        assert same_logger is logger

        # Shutdown
        await shutdown_analytics_logger()

    def test_get_logger_before_initialization(self):
        """Test get_analytics_logger raises before initialization."""
        # Clear global instance
        import src.agentic_rag.analytics as analytics_module

        analytics_module._analytics_logger = None

        with pytest.raises(RuntimeError, match="not initialized"):
            get_analytics_logger()

    @pytest.mark.asyncio
    async def test_shutdown_logger(self, mock_connection_manager):
        """Test shutdown analytics logger."""
        logger = await initialize_analytics_logger(mock_connection_manager)
        assert logger._running is True

        await shutdown_analytics_logger()

        # Should be able to initialize again
        logger2 = await initialize_analytics_logger(mock_connection_manager)
        assert logger2 is not None

        await shutdown_analytics_logger()


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_logging_overhead(self, analytics_logger):
        """Test logging overhead is <5ms per operation."""
        import time

        event = SearchAnalyticsEvent(
            query_text="performance test",
            detected_intent="VECTOR_HEAVY",
            strategy_used="VECTOR_HEAVY",
            total_latency_ms=100.0,
        )

        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            await analytics_logger.log_search(event)

        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / iterations) * 1000

        # Should be well under 5ms per operation
        assert avg_ms < 5.0, f"Average logging overhead: {avg_ms:.3f}ms"

    @pytest.mark.asyncio
    async def test_batch_performance(self, analytics_logger):
        """Test batch flush completes quickly."""
        import time

        # Add batch of events
        for i in range(100):
            event = SearchAnalyticsEvent(
                query_text=f"batch test {i}",
                detected_intent="HYBRID",
                strategy_used="HYBRID",
                total_latency_ms=100.0,
            )
            await analytics_logger.log_search(event)

        # Measure flush time
        start = time.perf_counter()
        await analytics_logger._flush_all()
        elapsed = (time.perf_counter() - start) * 1000

        # Flush should complete in reasonable time
        assert elapsed < 1000.0, f"Flush took: {elapsed:.2f}ms"
