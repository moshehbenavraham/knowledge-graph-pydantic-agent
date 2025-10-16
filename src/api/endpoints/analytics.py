"""
Analytics API endpoints for GraphRAG Dashboard.

Provides REST API access to persistent analytics data stored in PostgreSQL.
All endpoints query analytics tables and materialized views.
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.api.dependencies import get_connection_manager
from src.ui.features.dashboard_handler import DashboardHandler

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# ===== Response Models =====


class SearchMetricsResponse(dict):
    """Search metrics response model."""

    pass


class IntentDistributionResponse(dict):
    """Intent distribution response model."""

    pass


class PerformanceMetricsResponse(dict):
    """Performance metrics response model."""

    pass


class TimeSeriesResponse(list):
    """Time-series data response model."""

    pass


class ToolUsageResponse(dict):
    """Tool usage metrics response model."""

    pass


class AgentInteractionResponse(dict):
    """Agent interaction metrics response model."""

    pass


# ===== Endpoints =====


@router.get(
    "/search-metrics",
    response_model=SearchMetricsResponse,
    summary="Get search metrics",
    description="Retrieve aggregated search statistics including latency, strategies, and boost rates.",
)
async def get_search_metrics(
    window: str = Query("7d", pattern="^(24h|7d|30d)$", description="Time window for metrics"),
    conn_manager: ConnectionManager = Depends(get_connection_manager),
) -> dict[str, Any]:
    """
    Get search metrics from analytics database.

    Args:
        window: Time window (24h, 7d, 30d)
        conn_manager: Database connection manager

    Returns:
        Search metrics dictionary

    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        handler = DashboardHandler(conn_manager)
        metrics = await handler.get_search_metrics(window=window)

        # Check for errors in response
        if "error" in metrics:
            logger.warning("search_metrics_partial_failure", error=metrics["error"])

        return metrics

    except Exception as e:
        logger.exception("search_metrics_endpoint_error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve search metrics: {e!s}",
        ) from e


@router.get(
    "/intent-distribution",
    response_model=IntentDistributionResponse,
    summary="Get intent distribution",
    description="Retrieve percentage distribution of detected query intents.",
)
async def get_intent_distribution(
    window: str = Query("7d", pattern="^(24h|7d|30d)$", description="Time window for metrics"),
    conn_manager: ConnectionManager = Depends(get_connection_manager),
) -> dict[str, float]:
    """
    Get intent distribution from analytics database.

    Args:
        window: Time window (24h, 7d, 30d)
        conn_manager: Database connection manager

    Returns:
        Intent distribution dictionary (intent -> percentage)

    Raises:
        HTTPException: If distribution retrieval fails
    """
    try:
        handler = DashboardHandler(conn_manager)
        distribution = await handler.get_intent_distribution(window=window)
        return distribution

    except Exception as e:
        logger.exception("intent_distribution_endpoint_error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve intent distribution: {e!s}",
        ) from e


@router.get(
    "/performance-metrics",
    response_model=PerformanceMetricsResponse,
    summary="Get performance metrics",
    description="Retrieve latency breakdown, percentiles, and cache statistics.",
)
async def get_performance_metrics(
    window: str = Query("7d", pattern="^(24h|7d|30d)$", description="Time window for metrics"),
    conn_manager: ConnectionManager = Depends(get_connection_manager),
) -> dict[str, Any]:
    """
    Get performance metrics from analytics database.

    Args:
        window: Time window (24h, 7d, 30d)
        conn_manager: Database connection manager

    Returns:
        Performance metrics dictionary with latency and cache stats

    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        handler = DashboardHandler(conn_manager)
        metrics = await handler.get_performance_metrics(window=window)

        # Check for errors in response
        if "error" in metrics:
            logger.warning("performance_metrics_partial_failure", error=metrics["error"])

        return metrics

    except Exception as e:
        logger.exception("performance_metrics_endpoint_error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve performance metrics: {e!s}",
        ) from e


@router.get(
    "/time-series",
    response_model=TimeSeriesResponse,
    summary="Get time-series data",
    description="Retrieve time-series data for trending analysis and visualization.",
)
async def get_time_series_data(
    window: str = Query("7d", pattern="^(24h|7d|30d)$", description="Time window for data"),
    metric: str = Query(
        "searches",
        pattern="^(searches|latency|cache_hits|graph_boosts)$",
        description="Metric to retrieve",
    ),
    conn_manager: ConnectionManager = Depends(get_connection_manager),
) -> list[dict[str, Any]]:
    """
    Get time-series data from analytics database.

    Args:
        window: Time window (24h, 7d, 30d)
        metric: Metric to retrieve (searches, latency, cache_hits, graph_boosts)
        conn_manager: Database connection manager

    Returns:
        List of time-stamped data points

    Raises:
        HTTPException: If time-series retrieval fails
    """
    try:
        handler = DashboardHandler(conn_manager)
        series = await handler.get_time_series_data(window=window, metric=metric)
        return series

    except Exception as e:
        logger.exception("time_series_endpoint_error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve time-series data: {e!s}",
        ) from e


@router.get(
    "/tool-usage",
    response_model=ToolUsageResponse,
    summary="Get tool usage metrics",
    description="Retrieve tool usage statistics including success rates and execution times.",
)
async def get_tool_usage_metrics(
    window: str = Query("7d", pattern="^(24h|7d|30d)$", description="Time window for metrics"),
    conn_manager: ConnectionManager = Depends(get_connection_manager),
) -> dict[str, Any]:
    """
    Get tool usage metrics from analytics database.

    Args:
        window: Time window (24h, 7d, 30d)
        conn_manager: Database connection manager

    Returns:
        Tool usage metrics dictionary with summary and per-tool stats

    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        handler = DashboardHandler(conn_manager)
        metrics = await handler.get_tool_usage_metrics(window=window)

        # Check for errors in response
        if "error" in metrics:
            logger.warning("tool_usage_partial_failure", error=metrics["error"])

        return metrics

    except Exception as e:
        logger.exception("tool_usage_endpoint_error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tool usage metrics: {e!s}",
        ) from e


@router.get(
    "/agent-interactions",
    response_model=AgentInteractionResponse,
    summary="Get agent interaction metrics",
    description="Retrieve agent-user interaction statistics including feedback and response times.",
)
async def get_agent_interaction_metrics(
    window: str = Query("7d", pattern="^(24h|7d|30d)$", description="Time window for metrics"),
    conn_manager: ConnectionManager = Depends(get_connection_manager),
) -> dict[str, Any]:
    """
    Get agent interaction metrics from analytics database.

    Args:
        window: Time window (24h, 7d, 30d)
        conn_manager: Database connection manager

    Returns:
        Agent interaction metrics dictionary with feedback and performance stats

    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        handler = DashboardHandler(conn_manager)
        metrics = await handler.get_agent_interaction_metrics(window=window)

        # Check for errors in response
        if "error" in metrics:
            logger.warning("agent_interactions_partial_failure", error=metrics["error"])

        return metrics

    except Exception as e:
        logger.exception("agent_interactions_endpoint_error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent interaction metrics: {e!s}",
        ) from e


@router.get(
    "/health",
    summary="Analytics service health",
    description="Check if analytics database and services are operational.",
)
async def analytics_health(
    conn_manager: ConnectionManager = Depends(get_connection_manager),
) -> dict[str, Any]:
    """
    Check analytics service health.

    Args:
        conn_manager: Database connection manager

    Returns:
        Health status dictionary

    Raises:
        HTTPException: If health check fails critically
    """
    try:
        # Test database connectivity
        async with conn_manager.get_pg_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            db_healthy = result == 1

        # Check if analytics tables exist
        async with conn_manager.get_pg_connection() as conn:
            tables_exist = await conn.fetchval(
                """
                SELECT COUNT(*) = 5 FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN (
                    'search_analytics', 'tool_usage_analytics',
                    'agent_interactions', 'ingestion_analytics', 'system_metrics'
                )
                """
            )

        return {
            "status": "healthy" if (db_healthy and tables_exist) else "degraded",
            "database_connected": db_healthy,
            "analytics_tables_exist": tables_exist,
            "message": (
                "Analytics service operational"
                if (db_healthy and tables_exist)
                else "Analytics tables not fully initialized"
            ),
        }

    except Exception as e:
        logger.exception("analytics_health_check_error")
        return {
            "status": "unhealthy",
            "database_connected": False,
            "analytics_tables_exist": False,
            "message": f"Health check failed: {e!s}",
        }
