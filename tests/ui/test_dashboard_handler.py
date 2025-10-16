"""
Unit tests for DashboardHandler with persistent analytics.

Tests verify that dashboard queries analytics database correctly.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ui.features.dashboard_handler import DashboardHandler


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager."""
    mock_conn_mgr = MagicMock()

    # Mock PostgreSQL connection
    mock_pg_conn = AsyncMock()
    mock_conn_mgr.get_pg_connection.return_value.__aenter__.return_value = mock_pg_conn

    # Mock Neo4j session
    mock_neo4j_session = AsyncMock()
    mock_conn_mgr.get_neo4j_session.return_value.__aenter__.return_value = mock_neo4j_session

    # Mock connection pool metrics
    mock_conn_mgr.pg_metrics = MagicMock(
        active_connections=5,
        idle_connections=2,
        total_queries=1000,
        failed_queries=5,
        avg_query_time_ms=15.5,
    )
    mock_conn_mgr.neo4j_metrics = MagicMock(
        active_connections=3,
        idle_connections=1,
        total_queries=500,
        failed_queries=2,
        avg_query_time_ms=25.3,
    )

    return mock_conn_mgr


@pytest.mark.asyncio
async def test_get_search_metrics_queries_analytics_table(mock_connection_manager):
    """Test that get_search_metrics queries analytics database."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    # Mock database responses
    mock_conn.fetchrow.return_value = {
        "total_searches": 100,
        "avg_latency_ms": 150.5,
        "avg_vector_latency_ms": 80.2,
        "avg_graph_latency_ms": 70.3,
        "graph_boosts": 30,
        "entity_boosts": 20,
        "cache_hits": 40,
        "avg_entities_found": 5.2,
        "avg_relationships_found": 8.1,
    }

    mock_conn.fetch.return_value = [
        {"strategy_used": "HYBRID", "search_count": 60},
        {"strategy_used": "VECTOR_HEAVY", "search_count": 40},
    ]

    handler = DashboardHandler(mock_connection_manager)
    metrics = await handler.get_search_metrics()

    # Verify metrics structure and values
    assert metrics["total_searches"] == 100
    assert metrics["avg_latency_ms"] == 150.5
    assert metrics["most_used_strategy"] == "HYBRID"
    assert metrics["boost_rate"] == 0.5  # (30 + 20) / 100

    # Verify database was queried
    assert mock_conn.fetchrow.called
    assert mock_conn.fetch.called


@pytest.mark.asyncio
async def test_get_search_metrics_with_time_window(mock_connection_manager):
    """Test that get_search_metrics respects time window parameter."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    mock_conn.fetchrow.return_value = {
        "total_searches": 50,
        "avg_latency_ms": 120.0,
        "avg_vector_latency_ms": 60.0,
        "avg_graph_latency_ms": 60.0,
        "graph_boosts": 15,
        "entity_boosts": 10,
        "cache_hits": 25,
        "avg_entities_found": 3.0,
        "avg_relationships_found": 5.0,
    }

    mock_conn.fetch.return_value = [{"strategy_used": "HYBRID", "search_count": 50}]

    handler = DashboardHandler(mock_connection_manager)
    await handler.get_search_metrics(window="24h")

    # Verify query was called with correct interval
    call_args = mock_conn.fetchrow.call_args
    assert "24 hours" in str(call_args)


@pytest.mark.asyncio
async def test_get_intent_distribution_uses_materialized_view(mock_connection_manager):
    """Test that get_intent_distribution uses materialized view for 7d window."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    mock_conn.fetch.return_value = [
        {
            "detected_intent": "HYBRID",
            "search_count": 60,
            "avg_latency_ms": 150.0,
            "avg_chunks_returned": 10,
        },
        {
            "detected_intent": "VECTOR_HEAVY",
            "search_count": 40,
            "avg_latency_ms": 100.0,
            "avg_chunks_returned": 8,
        },
    ]

    handler = DashboardHandler(mock_connection_manager)
    distribution = await handler.get_intent_distribution(window="7d")

    # Verify percentages
    assert distribution["HYBRID"] == 60.0  # 60/100 * 100
    assert distribution["VECTOR_HEAVY"] == 40.0  # 40/100 * 100

    # Verify materialized view was used
    call_args = mock_conn.fetch.call_args
    assert "intent_distribution_7d" in str(call_args[0][0])


@pytest.mark.asyncio
async def test_get_performance_metrics_includes_percentiles(mock_connection_manager):
    """Test that get_performance_metrics includes percentile latency."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    mock_conn.fetchrow.return_value = {
        "avg_vector_latency_ms": 80.0,
        "avg_graph_latency_ms": 70.0,
        "avg_ranking_latency_ms": 10.0,
        "avg_total_latency_ms": 160.0,
        "p50_latency_ms": 150.0,
        "p95_latency_ms": 300.0,
        "p99_latency_ms": 500.0,
        "cache_hits": 40,
        "total_searches": 100,
    }

    handler = DashboardHandler(mock_connection_manager)
    metrics = await handler.get_performance_metrics()

    # Verify percentile metrics are included
    assert "p50_latency_ms" in metrics
    assert "p95_latency_ms" in metrics
    assert "p99_latency_ms" in metrics
    assert metrics["p95_latency_ms"] == 300.0
    assert metrics["cache_hit_rate"] == 0.4  # 40/100


@pytest.mark.asyncio
async def test_get_time_series_data_hourly_for_24h(mock_connection_manager):
    """Test that get_time_series_data uses hourly aggregation for 24h window."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    mock_conn.fetch.return_value = [
        {
            "timestamp": datetime(2025, 1, 1, 0),
            "searches": 10,
            "latency": 150.0,
            "cache_hits": 2,
            "graph_boosts": 3,
        },
        {
            "timestamp": datetime(2025, 1, 1, 1),
            "searches": 15,
            "latency": 140.0,
            "cache_hits": 5,
            "graph_boosts": 4,
        },
    ]

    handler = DashboardHandler(mock_connection_manager)
    series = await handler.get_time_series_data(window="24h", metric="searches")

    # Verify hourly aggregation was used
    call_args = mock_conn.fetch.call_args
    assert "DATE_TRUNC('hour'" in str(call_args[0][0])
    assert len(series) == 2
    assert series[0]["searches"] == 10


@pytest.mark.asyncio
async def test_get_time_series_data_daily_for_7d(mock_connection_manager):
    """Test that get_time_series_data uses daily summary for 7d window."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    mock_conn.fetch.return_value = [
        {
            "timestamp": datetime(2025, 1, 1).date(),
            "searches": 100,
            "latency": 150.0,
            "cache_hits": 40,
            "graph_boosts": 30,
        },
        {
            "timestamp": datetime(2025, 1, 2).date(),
            "searches": 120,
            "latency": 145.0,
            "cache_hits": 50,
            "graph_boosts": 35,
        },
    ]

    handler = DashboardHandler(mock_connection_manager)
    series = await handler.get_time_series_data(window="7d", metric="searches")

    # Verify daily_search_summary view was used
    call_args = mock_conn.fetch.call_args
    assert "daily_search_summary" in str(call_args[0][0])
    assert len(series) == 2


@pytest.mark.asyncio
async def test_get_tool_usage_metrics_uses_materialized_view(mock_connection_manager):
    """Test that get_tool_usage_metrics uses materialized view for 7d."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    mock_conn.fetchrow.return_value = {
        "total_calls": 500,
        "unique_tools": 5,
        "avg_success_rate": 0.95,
    }

    mock_conn.fetch.return_value = [
        {
            "tool_name": "retrieve_documents",
            "total_calls": 200,
            "success_rate": 0.98,
            "avg_execution_time_ms": 120.0,
            "p95_execution_time_ms": 250.0,
        },
        {
            "tool_name": "web_search",
            "total_calls": 150,
            "success_rate": 0.92,
            "avg_execution_time_ms": 300.0,
            "p95_execution_time_ms": 600.0,
        },
    ]

    handler = DashboardHandler(mock_connection_manager)
    metrics = await handler.get_tool_usage_metrics(window="7d")

    # Verify metrics structure
    assert metrics["total_calls"] == 500
    assert metrics["unique_tools"] == 5
    assert len(metrics["tools"]) == 2

    # Verify materialized view was used
    call_args = mock_conn.fetchrow.call_args
    assert "tool_performance_7d" in str(call_args[0][0])


@pytest.mark.asyncio
async def test_get_agent_interaction_metrics(mock_connection_manager):
    """Test that get_agent_interaction_metrics queries correctly."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    mock_conn.fetchrow.return_value = {
        "total_interactions": 200,
        "unique_sessions": 50,
        "avg_response_time_ms": 1500.0,
        "rag_usage_rate": 0.75,
        "thumbs_up": 40,
        "thumbs_down": 10,
        "feedback_rate": 0.25,
    }

    handler = DashboardHandler(mock_connection_manager)
    metrics = await handler.get_agent_interaction_metrics()

    # Verify metrics
    assert metrics["total_interactions"] == 200
    assert metrics["unique_sessions"] == 50
    assert metrics["rag_usage_rate"] == 0.75
    assert metrics["thumbs_up"] == 40
    assert metrics["thumbs_down"] == 10


@pytest.mark.asyncio
async def test_caching_prevents_redundant_queries(mock_connection_manager):
    """Test that dashboard handler caches results."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    mock_conn.fetchrow.return_value = {
        "total_searches": 100,
        "avg_latency_ms": 150.5,
        "avg_vector_latency_ms": 80.2,
        "avg_graph_latency_ms": 70.3,
        "graph_boosts": 30,
        "entity_boosts": 20,
        "cache_hits": 40,
        "avg_entities_found": 5.2,
        "avg_relationships_found": 8.1,
    }

    mock_conn.fetch.return_value = [{"strategy_used": "HYBRID", "search_count": 100}]

    handler = DashboardHandler(mock_connection_manager)

    # First call - should query database
    metrics1 = await handler.get_search_metrics()
    call_count_after_first = mock_conn.fetchrow.call_count

    # Second call - should use cache
    metrics2 = await handler.get_search_metrics()
    call_count_after_second = mock_conn.fetchrow.call_count

    # Verify cache was used
    assert metrics1 == metrics2
    assert call_count_after_first == call_count_after_second


@pytest.mark.asyncio
async def test_graceful_degradation_on_error(mock_connection_manager):
    """Test that handler returns error info gracefully."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value
    mock_conn.fetchrow.side_effect = Exception("Database connection failed")

    handler = DashboardHandler(mock_connection_manager)
    metrics = await handler.get_search_metrics()

    # Verify graceful degradation
    assert "error" in metrics
    assert metrics["total_searches"] == 0  # Default values provided


@pytest.mark.asyncio
async def test_clear_cache(mock_connection_manager):
    """Test that clear_cache invalidates cached data."""
    mock_conn = mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value

    mock_conn.fetchrow.return_value = {
        "total_searches": 100,
        "avg_latency_ms": 150.5,
        "avg_vector_latency_ms": 80.2,
        "avg_graph_latency_ms": 70.3,
        "graph_boosts": 30,
        "entity_boosts": 20,
        "cache_hits": 40,
        "avg_entities_found": 5.2,
        "avg_relationships_found": 8.1,
    }

    mock_conn.fetch.return_value = [{"strategy_used": "HYBRID", "search_count": 100}]

    handler = DashboardHandler(mock_connection_manager)

    # First call
    await handler.get_search_metrics()
    first_call_count = mock_conn.fetchrow.call_count

    # Clear cache
    handler.clear_cache()

    # Second call - should query again
    await handler.get_search_metrics()
    second_call_count = mock_conn.fetchrow.call_count

    assert second_call_count > first_call_count
