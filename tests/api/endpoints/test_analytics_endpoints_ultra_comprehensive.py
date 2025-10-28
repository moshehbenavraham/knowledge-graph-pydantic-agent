"""
ULTRA Comprehensive tests for analytics API endpoints.

Target coverage: 26% → 95%+

Tests all analytics endpoints, error handling, parameter validation,
and dashboard handler integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

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


class TestGetSearchMetrics:
    """Test search metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_search_metrics_success(self):
        """Test successful search metrics retrieval."""
        mock_conn_manager = MagicMock()

        mock_metrics = {
            "total_searches": 1000,
            "avg_latency_ms": 150.5,
            "strategies": {"vector": 600, "hybrid": 400},
        }

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_search_metrics.return_value = mock_metrics
            mock_handler_class.return_value = mock_handler

            result = await get_search_metrics(window="7d", conn_manager=mock_conn_manager)

            assert result == mock_metrics
            mock_handler.get_search_metrics.assert_called_once_with(window="7d")

    @pytest.mark.asyncio
    async def test_get_search_metrics_partial_failure(self):
        """Test search metrics with partial failure."""
        mock_conn_manager = MagicMock()

        mock_metrics = {"error": "Some metrics unavailable", "total_searches": 100}

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_search_metrics.return_value = mock_metrics
            mock_handler_class.return_value = mock_handler

            result = await get_search_metrics(window="24h", conn_manager=mock_conn_manager)

            assert "error" in result
            assert result["total_searches"] == 100

    @pytest.mark.asyncio
    async def test_get_search_metrics_error(self):
        """Test search metrics error handling."""
        mock_conn_manager = MagicMock()

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_search_metrics.side_effect = Exception("Database error")
            mock_handler_class.return_value = mock_handler

            with pytest.raises(HTTPException) as exc_info:
                await get_search_metrics(window="7d", conn_manager=mock_conn_manager)

            assert exc_info.value.status_code == 500
            assert "Failed to retrieve search metrics" in exc_info.value.detail


class TestGetIntentDistribution:
    """Test intent distribution endpoint."""

    @pytest.mark.asyncio
    async def test_get_intent_distribution_success(self):
        """Test successful intent distribution retrieval."""
        mock_conn_manager = MagicMock()

        mock_distribution = {
            "vector_heavy": 0.45,
            "graph_heavy": 0.30,
            "hybrid": 0.25,
        }

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_intent_distribution.return_value = mock_distribution
            mock_handler_class.return_value = mock_handler

            result = await get_intent_distribution(window="30d", conn_manager=mock_conn_manager)

            assert result == mock_distribution

    @pytest.mark.asyncio
    async def test_get_intent_distribution_error(self):
        """Test intent distribution error handling."""
        mock_conn_manager = MagicMock()

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_intent_distribution.side_effect = Exception("Query error")
            mock_handler_class.return_value = mock_handler

            with pytest.raises(HTTPException) as exc_info:
                await get_intent_distribution(window="7d", conn_manager=mock_conn_manager)

            assert exc_info.value.status_code == 500


class TestGetPerformanceMetrics:
    """Test performance metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_performance_metrics_success(self):
        """Test successful performance metrics retrieval."""
        mock_conn_manager = MagicMock()

        mock_metrics = {
            "avg_latency_ms": 120.5,
            "p50_latency_ms": 100.0,
            "p95_latency_ms": 250.0,
            "p99_latency_ms": 400.0,
            "cache_hit_rate": 0.75,
        }

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_performance_metrics.return_value = mock_metrics
            mock_handler_class.return_value = mock_handler

            result = await get_performance_metrics(window="7d", conn_manager=mock_conn_manager)

            assert result == mock_metrics

    @pytest.mark.asyncio
    async def test_get_performance_metrics_partial_failure(self):
        """Test performance metrics with partial failure."""
        mock_conn_manager = MagicMock()

        mock_metrics = {
            "error": "Some metrics unavailable",
            "avg_latency_ms": 120.5,
        }

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_performance_metrics.return_value = mock_metrics
            mock_handler_class.return_value = mock_handler

            result = await get_performance_metrics(window="24h", conn_manager=mock_conn_manager)

            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_performance_metrics_error(self):
        """Test performance metrics error handling."""
        mock_conn_manager = MagicMock()

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_performance_metrics.side_effect = Exception("Error")
            mock_handler_class.return_value = mock_handler

            with pytest.raises(HTTPException) as exc_info:
                await get_performance_metrics(window="7d", conn_manager=mock_conn_manager)

            assert exc_info.value.status_code == 500


class TestGetTimeSeriesData:
    """Test time-series data endpoint."""

    @pytest.mark.asyncio
    async def test_get_time_series_searches(self):
        """Test getting time-series search data."""
        mock_conn_manager = MagicMock()

        mock_series = [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 100},
            {"timestamp": "2024-01-02T00:00:00Z", "value": 150},
        ]

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_time_series_data.return_value = mock_series
            mock_handler_class.return_value = mock_handler

            result = await get_time_series_data(
                window="7d", metric="searches", conn_manager=mock_conn_manager
            )

            assert result == mock_series
            mock_handler.get_time_series_data.assert_called_once_with(
                window="7d", metric="searches"
            )

    @pytest.mark.asyncio
    async def test_get_time_series_latency(self):
        """Test getting time-series latency data."""
        mock_conn_manager = MagicMock()

        mock_series = [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 120.5},
        ]

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_time_series_data.return_value = mock_series
            mock_handler_class.return_value = mock_handler

            result = await get_time_series_data(
                window="24h", metric="latency", conn_manager=mock_conn_manager
            )

            assert result == mock_series

    @pytest.mark.asyncio
    async def test_get_time_series_error(self):
        """Test time-series data error handling."""
        mock_conn_manager = MagicMock()

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_time_series_data.side_effect = Exception("Query error")
            mock_handler_class.return_value = mock_handler

            with pytest.raises(HTTPException) as exc_info:
                await get_time_series_data(
                    window="7d", metric="searches", conn_manager=mock_conn_manager
                )

            assert exc_info.value.status_code == 500


class TestGetToolUsageMetrics:
    """Test tool usage metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_tool_usage_metrics_success(self):
        """Test successful tool usage metrics retrieval."""
        mock_conn_manager = MagicMock()

        mock_metrics = {
            "total_tool_calls": 500,
            "success_rate": 0.95,
            "tools": {
                "smart_search": {"calls": 200, "success_rate": 0.98},
                "web_search": {"calls": 150, "success_rate": 0.92},
            },
        }

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_tool_usage_metrics.return_value = mock_metrics
            mock_handler_class.return_value = mock_handler

            result = await get_tool_usage_metrics(window="7d", conn_manager=mock_conn_manager)

            assert result == mock_metrics

    @pytest.mark.asyncio
    async def test_get_tool_usage_metrics_partial_failure(self):
        """Test tool usage metrics with partial failure."""
        mock_conn_manager = MagicMock()

        mock_metrics = {
            "error": "Some tools data unavailable",
            "total_tool_calls": 500,
        }

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_tool_usage_metrics.return_value = mock_metrics
            mock_handler_class.return_value = mock_handler

            result = await get_tool_usage_metrics(window="30d", conn_manager=mock_conn_manager)

            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_tool_usage_metrics_error(self):
        """Test tool usage metrics error handling."""
        mock_conn_manager = MagicMock()

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_tool_usage_metrics.side_effect = Exception("Error")
            mock_handler_class.return_value = mock_handler

            with pytest.raises(HTTPException) as exc_info:
                await get_tool_usage_metrics(window="7d", conn_manager=mock_conn_manager)

            assert exc_info.value.status_code == 500


class TestGetAgentInteractionMetrics:
    """Test agent interaction metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_agent_interaction_metrics_success(self):
        """Test successful agent interaction metrics retrieval."""
        mock_conn_manager = MagicMock()

        mock_metrics = {
            "total_interactions": 1000,
            "avg_response_time_ms": 1500.0,
            "positive_feedback_rate": 0.85,
        }

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_agent_interaction_metrics.return_value = mock_metrics
            mock_handler_class.return_value = mock_handler

            result = await get_agent_interaction_metrics(
                window="7d", conn_manager=mock_conn_manager
            )

            assert result == mock_metrics

    @pytest.mark.asyncio
    async def test_get_agent_interaction_metrics_partial_failure(self):
        """Test agent interaction metrics with partial failure."""
        mock_conn_manager = MagicMock()

        mock_metrics = {
            "error": "Feedback data incomplete",
            "total_interactions": 1000,
        }

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_agent_interaction_metrics.return_value = mock_metrics
            mock_handler_class.return_value = mock_handler

            result = await get_agent_interaction_metrics(
                window="24h", conn_manager=mock_conn_manager
            )

            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_agent_interaction_metrics_error(self):
        """Test agent interaction metrics error handling."""
        mock_conn_manager = MagicMock()

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_agent_interaction_metrics.side_effect = Exception("Error")
            mock_handler_class.return_value = mock_handler

            with pytest.raises(HTTPException) as exc_info:
                await get_agent_interaction_metrics(window="7d", conn_manager=mock_conn_manager)

            assert exc_info.value.status_code == 500


class TestAnalyticsHealth:
    """Test analytics health check endpoint."""

    @pytest.mark.asyncio
    async def test_analytics_health_success(self):
        """Test successful health check."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[1, True])  # DB check, tables check

        mock_conn_manager = MagicMock()
        mock_conn_manager.get_pg_connection.return_value.__aenter__.return_value = mock_conn
        mock_conn_manager.get_pg_connection.return_value.__aexit__.return_value = None

        result = await analytics_health(conn_manager=mock_conn_manager)

        assert result["status"] == "healthy"
        assert result["database_connected"] is True
        assert result["analytics_tables_exist"] is True

    @pytest.mark.asyncio
    async def test_analytics_health_tables_missing(self):
        """Test health check with missing tables."""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[1, False])  # DB ok, tables missing

        mock_conn_manager = MagicMock()
        mock_conn_manager.get_pg_connection.return_value.__aenter__.return_value = mock_conn
        mock_conn_manager.get_pg_connection.return_value.__aexit__.return_value = None

        result = await analytics_health(conn_manager=mock_conn_manager)

        assert result["status"] == "degraded"
        assert result["database_connected"] is True
        assert result["analytics_tables_exist"] is False

    @pytest.mark.asyncio
    async def test_analytics_health_db_error(self):
        """Test health check with database error."""
        mock_conn_manager = MagicMock()
        mock_conn_manager.get_pg_connection.side_effect = Exception("Connection error")

        result = await analytics_health(conn_manager=mock_conn_manager)

        assert result["status"] == "unhealthy"
        assert result["database_connected"] is False
        assert result["analytics_tables_exist"] is False


class TestParameterValidation:
    """Test parameter validation across endpoints."""

    @pytest.mark.asyncio
    async def test_window_parameter_24h(self):
        """Test 24h window parameter."""
        mock_conn_manager = MagicMock()

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_search_metrics.return_value = {}
            mock_handler_class.return_value = mock_handler

            await get_search_metrics(window="24h", conn_manager=mock_conn_manager)

            mock_handler.get_search_metrics.assert_called_with(window="24h")

    @pytest.mark.asyncio
    async def test_window_parameter_7d(self):
        """Test 7d window parameter."""
        mock_conn_manager = MagicMock()

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_search_metrics.return_value = {}
            mock_handler_class.return_value = mock_handler

            await get_search_metrics(window="7d", conn_manager=mock_conn_manager)

            mock_handler.get_search_metrics.assert_called_with(window="7d")

    @pytest.mark.asyncio
    async def test_window_parameter_30d(self):
        """Test 30d window parameter."""
        mock_conn_manager = MagicMock()

        with patch("src.api.endpoints.analytics.DashboardHandler") as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.get_search_metrics.return_value = {}
            mock_handler_class.return_value = mock_handler

            await get_search_metrics(window="30d", conn_manager=mock_conn_manager)

            mock_handler.get_search_metrics.assert_called_with(window="30d")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
