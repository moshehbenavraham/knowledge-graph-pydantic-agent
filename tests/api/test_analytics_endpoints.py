"""
Integration tests for analytics API endpoints.

Tests verify that FastAPI endpoints correctly serve analytics data.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager for testing."""
    mock_conn_mgr = MagicMock()

    # Mock PostgreSQL connection
    mock_pg_conn = AsyncMock()
    mock_conn_mgr.get_pg_connection.return_value.__aenter__.return_value = mock_pg_conn
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

    return mock_conn_mgr, mock_pg_conn


@pytest.fixture
def client():
    """Create test client for API."""
    from src.api.main import app

    return TestClient(app)


def test_get_search_metrics_endpoint(client, mock_connection_manager):
    """Test GET /api/v1/analytics/search-metrics endpoint."""
    mock_conn_mgr, mock_pg_conn = mock_connection_manager

    # Mock database responses
    mock_pg_conn.fetchrow.return_value = {
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

    mock_pg_conn.fetch.return_value = [
        {"strategy_used": "HYBRID", "search_count": 60},
        {"strategy_used": "VECTOR_HEAVY", "search_count": 40},
    ]

    with patch("src.api.endpoints.analytics.get_connection_manager", return_value=mock_conn_mgr):
        response = client.get("/api/v1/analytics/search-metrics?window=7d")

    assert response.status_code == 200
    data = response.json()
    assert data["total_searches"] == 100
    assert "avg_latency_ms" in data
    assert "strategy_distribution" in data


def test_get_intent_distribution_endpoint(client, mock_connection_manager):
    """Test GET /api/v1/analytics/intent-distribution endpoint."""
    mock_conn_mgr, mock_pg_conn = mock_connection_manager

    mock_pg_conn.fetch.return_value = [
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

    with patch("src.api.endpoints.analytics.get_connection_manager", return_value=mock_conn_mgr):
        response = client.get("/api/v1/analytics/intent-distribution?window=7d")

    assert response.status_code == 200
    data = response.json()
    assert "HYBRID" in data
    assert "VECTOR_HEAVY" in data
    assert data["HYBRID"] == 60.0


def test_get_performance_metrics_endpoint(client, mock_connection_manager):
    """Test GET /api/v1/analytics/performance-metrics endpoint."""
    mock_conn_mgr, mock_pg_conn = mock_connection_manager

    mock_pg_conn.fetchrow.return_value = {
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

    with patch("src.api.endpoints.analytics.get_connection_manager", return_value=mock_conn_mgr):
        response = client.get("/api/v1/analytics/performance-metrics?window=7d")

    assert response.status_code == 200
    data = response.json()
    assert "p50_latency_ms" in data
    assert "p95_latency_ms" in data
    assert "p99_latency_ms" in data
    assert data["p95_latency_ms"] == 300.0


def test_get_time_series_endpoint(client, mock_connection_manager):
    """Test GET /api/v1/analytics/time-series endpoint."""
    mock_conn_mgr, mock_pg_conn = mock_connection_manager

    from datetime import datetime

    mock_pg_conn.fetch.return_value = [
        {"timestamp": datetime(2025, 1, 1).date(), "searches": 100},
        {"timestamp": datetime(2025, 1, 2).date(), "searches": 120},
    ]

    with patch("src.api.endpoints.analytics.get_connection_manager", return_value=mock_conn_mgr):
        response = client.get("/api/v1/analytics/time-series?window=7d&metric=searches")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["searches"] == 100


def test_get_tool_usage_endpoint(client, mock_connection_manager):
    """Test GET /api/v1/analytics/tool-usage endpoint."""
    mock_conn_mgr, mock_pg_conn = mock_connection_manager

    mock_pg_conn.fetchrow.return_value = {
        "total_calls": 500,
        "unique_tools": 5,
        "avg_success_rate": 0.95,
    }

    mock_pg_conn.fetch.return_value = [
        {
            "tool_name": "retrieve_documents",
            "total_calls": 200,
            "success_rate": 0.98,
            "avg_execution_time_ms": 120.0,
            "p95_execution_time_ms": 250.0,
        },
    ]

    with patch("src.api.endpoints.analytics.get_connection_manager", return_value=mock_conn_mgr):
        response = client.get("/api/v1/analytics/tool-usage?window=7d")

    assert response.status_code == 200
    data = response.json()
    assert data["total_calls"] == 500
    assert "tools" in data
    assert len(data["tools"]) == 1


def test_get_agent_interactions_endpoint(client, mock_connection_manager):
    """Test GET /api/v1/analytics/agent-interactions endpoint."""
    mock_conn_mgr, mock_pg_conn = mock_connection_manager

    mock_pg_conn.fetchrow.return_value = {
        "total_interactions": 200,
        "unique_sessions": 50,
        "avg_response_time_ms": 1500.0,
        "rag_usage_rate": 0.75,
        "thumbs_up": 40,
        "thumbs_down": 10,
        "feedback_rate": 0.25,
    }

    with patch("src.api.endpoints.analytics.get_connection_manager", return_value=mock_conn_mgr):
        response = client.get("/api/v1/analytics/agent-interactions?window=7d")

    assert response.status_code == 200
    data = response.json()
    assert data["total_interactions"] == 200
    assert data["thumbs_up"] == 40
    assert data["thumbs_down"] == 10


def test_analytics_health_endpoint(client, mock_connection_manager):
    """Test GET /api/v1/analytics/health endpoint."""
    mock_conn_mgr, mock_pg_conn = mock_connection_manager

    # Mock database health check
    mock_pg_conn.fetchval.side_effect = [1, True]  # First call returns 1, second returns True

    with patch("src.api.endpoints.analytics.get_connection_manager", return_value=mock_conn_mgr):
        response = client.get("/api/v1/analytics/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database_connected" in data
    assert "analytics_tables_exist" in data


def test_invalid_window_parameter(client, mock_connection_manager):
    """Test that invalid window parameter is rejected."""
    response = client.get("/api/v1/analytics/search-metrics?window=invalid")
    assert response.status_code == 422  # Validation error


def test_invalid_metric_parameter(client, mock_connection_manager):
    """Test that invalid metric parameter is rejected."""
    response = client.get("/api/v1/analytics/time-series?window=7d&metric=invalid_metric")
    assert response.status_code == 422  # Validation error


def test_endpoint_error_handling(client, mock_connection_manager):
    """Test that endpoints handle database errors gracefully."""
    mock_conn_mgr, mock_pg_conn = mock_connection_manager
    mock_pg_conn.fetchrow.side_effect = Exception("Database error")

    with patch("src.api.endpoints.analytics.get_connection_manager", return_value=mock_conn_mgr):
        response = client.get("/api/v1/analytics/search-metrics?window=7d")

    # Should return 500 error
    assert response.status_code == 500
    assert "detail" in response.json()
