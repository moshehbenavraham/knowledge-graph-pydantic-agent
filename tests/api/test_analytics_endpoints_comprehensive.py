"""
Comprehensive tests for analytics API endpoints.

Tests all analytics endpoints including search metrics, intent distribution,
performance metrics, time-series data, tool usage, agent interactions, and health checks.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.api.endpoints.analytics import (
    analytics_health,
    get_agent_interaction_metrics,
    get_intent_distribution,
    get_performance_metrics,
    get_search_metrics,
    get_time_series_data,
    get_tool_usage_metrics,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_connection_manager():
    """Mock ConnectionManager with pg connection."""
    manager = AsyncMock()

    # Mock pg connection context manager
    conn = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.fetch = AsyncMock()

    pg_context = AsyncMock()
    pg_context.__aenter__ = AsyncMock(return_value=conn)
    pg_context.__aexit__ = AsyncMock(return_value=None)

    manager.get_pg_connection.return_value = pg_context

    return manager


@pytest.fixture
def mock_dashboard_handler():
    """Mock DashboardHandler with all methods."""
    handler = AsyncMock()

    # Mock search metrics
    handler.get_search_metrics = AsyncMock(
        return_value={
            "total_searches": 1000,
            "avg_latency_ms": 125.5,
            "graph_boost_rate": 0.35,
            "strategy_distribution": {"VECTOR_HEAVY": 40, "COMPREHENSIVE": 60},
        }
    )

    # Mock intent distribution
    handler.get_intent_distribution = AsyncMock(
        return_value={
            "VECTOR_HEAVY": 45.0,
            "GRAPH_HEAVY": 25.0,
            "COMPREHENSIVE": 30.0,
        }
    )

    # Mock performance metrics
    handler.get_performance_metrics = AsyncMock(
        return_value={
            "latency": {
                "avg": 125.5,
                "p50": 100.0,
                "p95": 250.0,
                "p99": 500.0,
            },
            "cache": {"hit_rate": 0.75, "hits": 750, "total": 1000},
        }
    )

    # Mock time-series data
    handler.get_time_series_data = AsyncMock(
        return_value=[
            {"timestamp": "2025-01-01T00:00:00Z", "value": 100},
            {"timestamp": "2025-01-01T01:00:00Z", "value": 120},
        ]
    )

    # Mock tool usage metrics
    handler.get_tool_usage_metrics = AsyncMock(
        return_value={
            "summary": {"total_calls": 500, "success_rate": 0.95, "avg_duration_ms": 250.0},
            "tools": {
                "web_search": {"calls": 200, "success_rate": 0.98},
                "rag_search": {"calls": 300, "success_rate": 0.93},
            },
        }
    )

    # Mock agent interaction metrics
    handler.get_agent_interaction_metrics = AsyncMock(
        return_value={
            "total_interactions": 800,
            "avg_response_time_ms": 1500.0,
            "positive_feedback": 720,
            "negative_feedback": 50,
            "satisfaction_rate": 0.9,
        }
    )

    return handler


# ============================================================================
# get_search_metrics Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_search_metrics_success(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test successful search metrics retrieval."""
    mock_handler_class.return_value = mock_dashboard_handler

    result = await get_search_metrics(window="7d", conn_manager=mock_connection_manager)

    assert result["total_searches"] == 1000
    assert result["avg_latency_ms"] == 125.5
    assert result["graph_boost_rate"] == 0.35
    assert "strategy_distribution" in result

    mock_dashboard_handler.get_search_metrics.assert_called_once_with(window="7d")


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_search_metrics_24h_window(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test search metrics with 24h window."""
    mock_handler_class.return_value = mock_dashboard_handler

    await get_search_metrics(window="24h", conn_manager=mock_connection_manager)

    mock_dashboard_handler.get_search_metrics.assert_called_once_with(window="24h")


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_search_metrics_30d_window(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test search metrics with 30d window."""
    mock_handler_class.return_value = mock_dashboard_handler

    await get_search_metrics(window="30d", conn_manager=mock_connection_manager)

    mock_dashboard_handler.get_search_metrics.assert_called_once_with(window="30d")


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_search_metrics_partial_error(mock_handler_class, mock_connection_manager):
    """Test search metrics with partial error in response."""
    handler = AsyncMock()
    handler.get_search_metrics = AsyncMock(
        return_value={"total_searches": 100, "error": "Some tables missing"}
    )
    mock_handler_class.return_value = handler

    result = await get_search_metrics(window="7d", conn_manager=mock_connection_manager)

    assert "error" in result
    assert result["total_searches"] == 100


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_search_metrics_handler_exception(mock_handler_class, mock_connection_manager):
    """Test search metrics when handler raises exception."""
    handler = AsyncMock()
    handler.get_search_metrics.side_effect = Exception("Database connection lost")
    mock_handler_class.return_value = handler

    with pytest.raises(HTTPException) as exc_info:
        await get_search_metrics(window="7d", conn_manager=mock_connection_manager)

    assert exc_info.value.status_code == 500
    assert "Failed to retrieve search metrics" in exc_info.value.detail


# ============================================================================
# get_intent_distribution Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_intent_distribution_success(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test successful intent distribution retrieval."""
    mock_handler_class.return_value = mock_dashboard_handler

    result = await get_intent_distribution(window="7d", conn_manager=mock_connection_manager)

    assert result["VECTOR_HEAVY"] == 45.0
    assert result["GRAPH_HEAVY"] == 25.0
    assert result["COMPREHENSIVE"] == 30.0
    assert sum(result.values()) == 100.0

    mock_dashboard_handler.get_intent_distribution.assert_called_once_with(window="7d")


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_intent_distribution_empty_result(mock_handler_class, mock_connection_manager):
    """Test intent distribution with no data."""
    handler = AsyncMock()
    handler.get_intent_distribution = AsyncMock(return_value={})
    mock_handler_class.return_value = handler

    result = await get_intent_distribution(window="24h", conn_manager=mock_connection_manager)

    assert result == {}


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_intent_distribution_handler_exception(
    mock_handler_class, mock_connection_manager
):
    """Test intent distribution when handler raises exception."""
    handler = AsyncMock()
    handler.get_intent_distribution.side_effect = Exception("Query failed")
    mock_handler_class.return_value = handler

    with pytest.raises(HTTPException) as exc_info:
        await get_intent_distribution(window="7d", conn_manager=mock_connection_manager)

    assert exc_info.value.status_code == 500
    assert "Failed to retrieve intent distribution" in exc_info.value.detail


# ============================================================================
# get_performance_metrics Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_performance_metrics_success(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test successful performance metrics retrieval."""
    mock_handler_class.return_value = mock_dashboard_handler

    result = await get_performance_metrics(window="7d", conn_manager=mock_connection_manager)

    assert "latency" in result
    assert result["latency"]["avg"] == 125.5
    assert result["latency"]["p95"] == 250.0
    assert "cache" in result
    assert result["cache"]["hit_rate"] == 0.75

    mock_dashboard_handler.get_performance_metrics.assert_called_once_with(window="7d")


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_performance_metrics_partial_error(mock_handler_class, mock_connection_manager):
    """Test performance metrics with partial error in response."""
    handler = AsyncMock()
    handler.get_performance_metrics = AsyncMock(
        return_value={
            "latency": {"avg": 100.0},
            "error": "Cache stats unavailable",
        }
    )
    mock_handler_class.return_value = handler

    result = await get_performance_metrics(window="7d", conn_manager=mock_connection_manager)

    assert "error" in result
    assert "latency" in result


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_performance_metrics_handler_exception(
    mock_handler_class, mock_connection_manager
):
    """Test performance metrics when handler raises exception."""
    handler = AsyncMock()
    handler.get_performance_metrics.side_effect = Exception("Metrics unavailable")
    mock_handler_class.return_value = handler

    with pytest.raises(HTTPException) as exc_info:
        await get_performance_metrics(window="7d", conn_manager=mock_connection_manager)

    assert exc_info.value.status_code == 500
    assert "Failed to retrieve performance metrics" in exc_info.value.detail


# ============================================================================
# get_time_series_data Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_time_series_data_searches(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test time-series data for searches metric."""
    mock_handler_class.return_value = mock_dashboard_handler

    result = await get_time_series_data(
        window="7d", metric="searches", conn_manager=mock_connection_manager
    )

    assert len(result) == 2
    assert result[0]["timestamp"] == "2025-01-01T00:00:00Z"
    assert result[0]["value"] == 100

    mock_dashboard_handler.get_time_series_data.assert_called_once_with(
        window="7d", metric="searches"
    )


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_time_series_data_latency(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test time-series data for latency metric."""
    mock_handler_class.return_value = mock_dashboard_handler

    await get_time_series_data(window="24h", metric="latency", conn_manager=mock_connection_manager)

    mock_dashboard_handler.get_time_series_data.assert_called_once_with(
        window="24h", metric="latency"
    )


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_time_series_data_cache_hits(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test time-series data for cache_hits metric."""
    mock_handler_class.return_value = mock_dashboard_handler

    await get_time_series_data(
        window="30d", metric="cache_hits", conn_manager=mock_connection_manager
    )

    mock_dashboard_handler.get_time_series_data.assert_called_once_with(
        window="30d", metric="cache_hits"
    )


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_time_series_data_graph_boosts(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test time-series data for graph_boosts metric."""
    mock_handler_class.return_value = mock_dashboard_handler

    await get_time_series_data(
        window="7d", metric="graph_boosts", conn_manager=mock_connection_manager
    )

    mock_dashboard_handler.get_time_series_data.assert_called_once_with(
        window="7d", metric="graph_boosts"
    )


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_time_series_data_empty_result(mock_handler_class, mock_connection_manager):
    """Test time-series data with no data points."""
    handler = AsyncMock()
    handler.get_time_series_data = AsyncMock(return_value=[])
    mock_handler_class.return_value = handler

    result = await get_time_series_data(
        window="7d", metric="searches", conn_manager=mock_connection_manager
    )

    assert result == []


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_time_series_data_handler_exception(mock_handler_class, mock_connection_manager):
    """Test time-series data when handler raises exception."""
    handler = AsyncMock()
    handler.get_time_series_data.side_effect = Exception("Data retrieval failed")
    mock_handler_class.return_value = handler

    with pytest.raises(HTTPException) as exc_info:
        await get_time_series_data(
            window="7d", metric="searches", conn_manager=mock_connection_manager
        )

    assert exc_info.value.status_code == 500
    assert "Failed to retrieve time-series data" in exc_info.value.detail


# ============================================================================
# get_tool_usage_metrics Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_tool_usage_metrics_success(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test successful tool usage metrics retrieval."""
    mock_handler_class.return_value = mock_dashboard_handler

    result = await get_tool_usage_metrics(window="7d", conn_manager=mock_connection_manager)

    assert "summary" in result
    assert result["summary"]["total_calls"] == 500
    assert result["summary"]["success_rate"] == 0.95
    assert "tools" in result
    assert "web_search" in result["tools"]

    mock_dashboard_handler.get_tool_usage_metrics.assert_called_once_with(window="7d")


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_tool_usage_metrics_partial_error(mock_handler_class, mock_connection_manager):
    """Test tool usage metrics with partial error in response."""
    handler = AsyncMock()
    handler.get_tool_usage_metrics = AsyncMock(
        return_value={
            "summary": {"total_calls": 100},
            "error": "Some tool stats missing",
        }
    )
    mock_handler_class.return_value = handler

    result = await get_tool_usage_metrics(window="7d", conn_manager=mock_connection_manager)

    assert "error" in result
    assert "summary" in result


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_tool_usage_metrics_handler_exception(
    mock_handler_class, mock_connection_manager
):
    """Test tool usage metrics when handler raises exception."""
    handler = AsyncMock()
    handler.get_tool_usage_metrics.side_effect = Exception("Metrics query failed")
    mock_handler_class.return_value = handler

    with pytest.raises(HTTPException) as exc_info:
        await get_tool_usage_metrics(window="7d", conn_manager=mock_connection_manager)

    assert exc_info.value.status_code == 500
    assert "Failed to retrieve tool usage metrics" in exc_info.value.detail


# ============================================================================
# get_agent_interaction_metrics Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_agent_interaction_metrics_success(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test successful agent interaction metrics retrieval."""
    mock_handler_class.return_value = mock_dashboard_handler

    result = await get_agent_interaction_metrics(window="7d", conn_manager=mock_connection_manager)

    assert result["total_interactions"] == 800
    assert result["avg_response_time_ms"] == 1500.0
    assert result["positive_feedback"] == 720
    assert result["satisfaction_rate"] == 0.9

    mock_dashboard_handler.get_agent_interaction_metrics.assert_called_once_with(window="7d")


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_agent_interaction_metrics_partial_error(
    mock_handler_class, mock_connection_manager
):
    """Test agent interaction metrics with partial error in response."""
    handler = AsyncMock()
    handler.get_agent_interaction_metrics = AsyncMock(
        return_value={
            "total_interactions": 500,
            "error": "Feedback stats incomplete",
        }
    )
    mock_handler_class.return_value = handler

    result = await get_agent_interaction_metrics(window="7d", conn_manager=mock_connection_manager)

    assert "error" in result
    assert result["total_interactions"] == 500


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_get_agent_interaction_metrics_handler_exception(
    mock_handler_class, mock_connection_manager
):
    """Test agent interaction metrics when handler raises exception."""
    handler = AsyncMock()
    handler.get_agent_interaction_metrics.side_effect = Exception("Interaction query failed")
    mock_handler_class.return_value = handler

    with pytest.raises(HTTPException) as exc_info:
        await get_agent_interaction_metrics(window="7d", conn_manager=mock_connection_manager)

    assert exc_info.value.status_code == 500
    assert "Failed to retrieve agent interaction metrics" in exc_info.value.detail


# ============================================================================
# analytics_health Tests
# ============================================================================


@pytest.mark.asyncio
async def test_analytics_health_healthy(mock_connection_manager):
    """Test analytics health check when fully healthy."""
    # Mock successful health checks
    conn = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.fetchval.side_effect = [1, True]  # First for SELECT 1, second for table check

    pg_context = AsyncMock()
    pg_context.__aenter__ = AsyncMock(return_value=conn)
    pg_context.__aexit__ = AsyncMock(return_value=None)

    mock_connection_manager.get_pg_connection.return_value = pg_context

    result = await analytics_health(conn_manager=mock_connection_manager)

    assert result["status"] == "healthy"
    assert result["database_connected"] is True
    assert result["analytics_tables_exist"] is True
    assert "operational" in result["message"]


@pytest.mark.asyncio
async def test_analytics_health_degraded_missing_tables(mock_connection_manager):
    """Test analytics health check when tables are missing."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.fetchval.side_effect = [1, False]  # DB connected but tables missing

    pg_context = AsyncMock()
    pg_context.__aenter__ = AsyncMock(return_value=conn)
    pg_context.__aexit__ = AsyncMock(return_value=None)

    mock_connection_manager.get_pg_connection.return_value = pg_context

    result = await analytics_health(conn_manager=mock_connection_manager)

    assert result["status"] == "degraded"
    assert result["database_connected"] is True
    assert result["analytics_tables_exist"] is False
    assert "not fully initialized" in result["message"]


@pytest.mark.asyncio
async def test_analytics_health_degraded_db_issue(mock_connection_manager):
    """Test analytics health check with database connectivity issues."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.fetchval.side_effect = [0, False]  # SELECT 1 returns wrong value

    pg_context = AsyncMock()
    pg_context.__aenter__ = AsyncMock(return_value=conn)
    pg_context.__aexit__ = AsyncMock(return_value=None)

    mock_connection_manager.get_pg_connection.return_value = pg_context

    result = await analytics_health(conn_manager=mock_connection_manager)

    assert result["status"] == "degraded"
    assert result["database_connected"] is False


@pytest.mark.asyncio
async def test_analytics_health_unhealthy_exception(mock_connection_manager):
    """Test analytics health check when exception occurs."""
    mock_connection_manager.get_pg_connection.side_effect = Exception("Connection refused")

    result = await analytics_health(conn_manager=mock_connection_manager)

    assert result["status"] == "unhealthy"
    assert result["database_connected"] is False
    assert result["analytics_tables_exist"] is False
    assert "Health check failed" in result["message"]


@pytest.mark.asyncio
async def test_analytics_health_connection_timeout(mock_connection_manager):
    """Test analytics health check with connection timeout."""
    pg_context = AsyncMock()
    pg_context.__aenter__.side_effect = TimeoutError("Connection timeout")

    mock_connection_manager.get_pg_connection.return_value = pg_context

    result = await analytics_health(conn_manager=mock_connection_manager)

    assert result["status"] == "unhealthy"


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_multiple_metrics_concurrent_calls(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test multiple metrics endpoints called concurrently."""
    mock_handler_class.return_value = mock_dashboard_handler

    import asyncio

    results = await asyncio.gather(
        get_search_metrics(window="7d", conn_manager=mock_connection_manager),
        get_intent_distribution(window="7d", conn_manager=mock_connection_manager),
        get_performance_metrics(window="7d", conn_manager=mock_connection_manager),
    )

    assert len(results) == 3
    assert all(isinstance(r, dict) for r in results)


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_all_time_windows(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test that all time windows work correctly."""
    mock_handler_class.return_value = mock_dashboard_handler

    for window in ["24h", "7d", "30d"]:
        result = await get_search_metrics(window=window, conn_manager=mock_connection_manager)
        assert isinstance(result, dict)


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_all_time_series_metrics(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test that all time-series metrics work correctly."""
    mock_handler_class.return_value = mock_dashboard_handler

    for metric in ["searches", "latency", "cache_hits", "graph_boosts"]:
        result = await get_time_series_data(
            window="7d", metric=metric, conn_manager=mock_connection_manager
        )
        assert isinstance(result, list)


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
@patch("src.api.endpoints.analytics.logger")
async def test_logging_on_partial_error(mock_logger, mock_handler_class, mock_connection_manager):
    """Test that partial errors are logged appropriately."""
    handler = AsyncMock()
    handler.get_search_metrics = AsyncMock(
        return_value={"total_searches": 100, "error": "Partial failure"}
    )
    mock_handler_class.return_value = handler

    await get_search_metrics(window="7d", conn_manager=mock_connection_manager)

    # Verify warning was logged
    mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
@patch("src.api.endpoints.analytics.logger")
async def test_logging_on_exception(mock_logger, mock_handler_class, mock_connection_manager):
    """Test that exceptions are logged appropriately."""
    handler = AsyncMock()
    handler.get_search_metrics.side_effect = Exception("Test error")
    mock_handler_class.return_value = handler

    with pytest.raises(HTTPException):
        await get_search_metrics(window="7d", conn_manager=mock_connection_manager)

    # Verify exception was logged
    mock_logger.exception.assert_called_once()


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_handler_initialization(
    mock_handler_class, mock_dashboard_handler, mock_connection_manager
):
    """Test that DashboardHandler is properly initialized."""
    mock_handler_class.return_value = mock_dashboard_handler

    await get_search_metrics(window="7d", conn_manager=mock_connection_manager)

    # Verify handler was initialized with connection manager
    mock_handler_class.assert_called_once_with(mock_connection_manager)


@pytest.mark.asyncio
async def test_analytics_health_proper_table_check(mock_connection_manager):
    """Test that health check verifies all 5 required tables."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.fetchval.side_effect = [1, True]

    pg_context = AsyncMock()
    pg_context.__aenter__ = AsyncMock(return_value=conn)
    pg_context.__aexit__ = AsyncMock(return_value=None)

    mock_connection_manager.get_pg_connection.return_value = pg_context

    await analytics_health(conn_manager=mock_connection_manager)

    # Verify the table check query was called
    calls = conn.fetchval.call_args_list
    assert len(calls) == 2
    # Second call should check for tables
    table_query = calls[1][0][0]
    assert "search_analytics" in table_query
    assert "tool_usage_analytics" in table_query
    assert "agent_interactions" in table_query
    assert "ingestion_analytics" in table_query
    assert "system_metrics" in table_query


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_very_large_result_sets(mock_handler_class, mock_connection_manager):
    """Test handling of very large metric result sets."""
    handler = AsyncMock()

    # Create large time-series data
    large_series = [{"timestamp": f"2025-01-{i:02d}T00:00:00Z", "value": i} for i in range(1000)]
    handler.get_time_series_data = AsyncMock(return_value=large_series)
    mock_handler_class.return_value = handler

    result = await get_time_series_data(
        window="30d", metric="searches", conn_manager=mock_connection_manager
    )

    assert len(result) == 1000


@pytest.mark.asyncio
@patch("src.api.endpoints.analytics.DashboardHandler")
async def test_empty_metrics_responses(mock_handler_class, mock_connection_manager):
    """Test handling of empty/zero metric responses."""
    handler = AsyncMock()
    handler.get_search_metrics = AsyncMock(
        return_value={
            "total_searches": 0,
            "avg_latency_ms": 0,
            "graph_boost_rate": 0,
        }
    )
    mock_handler_class.return_value = handler

    result = await get_search_metrics(window="24h", conn_manager=mock_connection_manager)

    assert result["total_searches"] == 0
    assert isinstance(result, dict)
