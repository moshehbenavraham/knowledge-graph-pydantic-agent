"""
Comprehensive tests for health_endpoints.py module.

Tests all health check endpoints including basic/detailed health, metrics,
rate limits, component health, and Kubernetes probe endpoints.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from src.api.health_endpoints import (
    basic_health_check,
    detailed_health_check,
    get_component_health,
    get_metrics,
    get_rate_limit_status,
    liveness_check,
    readiness_check,
    set_user_tier,
    startup_check,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    settings.app_version = "1.3.0"
    settings.metrics_port = 8002
    settings.enable_metrics = True
    settings.log_level = "INFO"
    return settings


@pytest.fixture
def mock_health_status():
    """Mock HealthStatus object."""
    status = MagicMock()
    status.status = "healthy"
    status.timestamp = datetime.now(UTC)
    status.uptime = 3600.0
    status.version = "1.3.0"
    status.checks = {
        "database": {"status": "healthy", "response_time": 0.05},
        "llm": {"status": "healthy", "response_time": 0.1},
        "embedding": {"status": "healthy", "response_time": 0.08},
    }
    return status


@pytest.fixture
def mock_component_health():
    """Mock ComponentHealth object."""
    health = MagicMock()
    health.name = "database"
    health.status = "healthy"
    health.response_time = 0.05
    health.error = None
    health.last_check = datetime.now(UTC)
    health.details = {"connection_pool": "ok"}
    return health


@pytest.fixture
def mock_system_stats():
    """Mock system statistics."""
    return {
        "cpu_percent": 45.2,
        "memory_percent": 62.5,
        "disk_percent": 55.0,
        "uptime": 7200.0,
        "request_count": 1000,
        "error_count": 5,
    }


# ============================================================================
# basic_health_check Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.get_settings")
async def test_basic_health_check_success(mock_get_settings, mock_settings):
    """Test basic health check returns healthy status."""
    mock_get_settings.return_value = mock_settings

    result = await basic_health_check()

    assert result["status"] == "healthy"
    assert result["service"] == "luminari-ai-agent"
    assert result["version"] == "1.3.0"
    assert "timestamp" in result


@pytest.mark.asyncio
@patch("src.api.health_endpoints.get_settings")
async def test_basic_health_check_timestamp_format(mock_get_settings, mock_settings):
    """Test that timestamp is in ISO format."""
    mock_get_settings.return_value = mock_settings

    result = await basic_health_check()

    # Verify ISO format timestamp
    timestamp = datetime.fromisoformat(result["timestamp"])
    assert isinstance(timestamp, datetime)


# ============================================================================
# detailed_health_check Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_detailed_health_check_healthy(mock_checker, mock_health_status):
    """Test detailed health check when all components healthy."""
    mock_checker.get_health_status = AsyncMock(return_value=mock_health_status)

    result = await detailed_health_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 200


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_detailed_health_check_degraded(mock_checker):
    """Test detailed health check when system is degraded."""
    degraded_status = MagicMock()
    degraded_status.status = "degraded"
    degraded_status.timestamp = datetime.now(UTC)
    degraded_status.uptime = 3600.0
    degraded_status.version = "1.3.0"
    degraded_status.checks = {"database": {"status": "degraded"}}

    mock_checker.get_health_status = AsyncMock(return_value=degraded_status)

    result = await detailed_health_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 200  # Degraded still returns 200


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_detailed_health_check_unhealthy(mock_checker):
    """Test detailed health check when system is unhealthy."""
    unhealthy_status = MagicMock()
    unhealthy_status.status = "unhealthy"
    unhealthy_status.timestamp = datetime.now(UTC)
    unhealthy_status.uptime = 3600.0
    unhealthy_status.version = "1.3.0"
    unhealthy_status.checks = {"database": {"status": "unhealthy"}}

    mock_checker.get_health_status = AsyncMock(return_value=unhealthy_status)

    result = await detailed_health_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 503  # Service unavailable


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_detailed_health_check_exception(mock_checker):
    """Test detailed health check when exception occurs."""
    mock_checker.get_health_status = AsyncMock(side_effect=Exception("Health check failed"))

    result = await detailed_health_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 503


# ============================================================================
# get_metrics Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.monitor")
@patch("src.api.health_endpoints.get_settings")
async def test_get_metrics_success(
    mock_get_settings, mock_monitor, mock_settings, mock_system_stats
):
    """Test successful metrics retrieval."""
    mock_get_settings.return_value = mock_settings
    mock_monitor.get_system_stats.return_value = mock_system_stats

    result = await get_metrics()

    assert "timestamp" in result
    assert "system" in result
    assert result["system"]["cpu_percent"] == 45.2
    assert result["system"]["uptime"] == 7200.0
    assert "prometheus_endpoint" in result


@pytest.mark.asyncio
@patch("src.api.health_endpoints.monitor")
@patch("src.api.health_endpoints.get_settings")
async def test_get_metrics_prometheus_endpoint(
    mock_get_settings, mock_monitor, mock_settings, mock_system_stats
):
    """Test that Prometheus endpoint URL is included."""
    mock_get_settings.return_value = mock_settings
    mock_monitor.get_system_stats.return_value = mock_system_stats

    result = await get_metrics()

    assert "http://localhost:9090/metrics" in result["prometheus_endpoint"]


@pytest.mark.asyncio
@patch("src.api.health_endpoints.monitor")
@patch("src.api.health_endpoints.get_settings")
async def test_get_metrics_exception(mock_get_settings, mock_monitor, mock_settings):
    """Test metrics retrieval when exception occurs."""
    mock_get_settings.return_value = mock_settings
    mock_monitor.get_system_stats.side_effect = Exception("Metrics unavailable")

    with pytest.raises(HTTPException) as exc_info:
        await get_metrics()

    assert exc_info.value.status_code == 500
    assert "Failed to get metrics" in exc_info.value.detail


# ============================================================================
# get_rate_limit_status Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.rate_limiter")
async def test_get_rate_limit_status_success(mock_limiter):
    """Test successful rate limit status retrieval."""
    mock_limiter.get_all_stats.return_value = {
        "user_id": "test_user",
        "tier": "premium",
        "requests_remaining": 850,
        "reset_time": datetime.now(UTC).isoformat(),
    }

    result = await get_rate_limit_status("test_user")

    assert result["user_id"] == "test_user"
    assert result["tier"] == "premium"
    assert result["requests_remaining"] == 850
    mock_limiter.get_all_stats.assert_called_once_with("test_user")


@pytest.mark.asyncio
@patch("src.api.health_endpoints.rate_limiter")
async def test_get_rate_limit_status_free_tier(mock_limiter):
    """Test rate limit status for free tier user."""
    mock_limiter.get_all_stats.return_value = {
        "user_id": "free_user",
        "tier": "free",
        "requests_remaining": 50,
    }

    result = await get_rate_limit_status("free_user")

    assert result["tier"] == "free"
    assert result["requests_remaining"] == 50


@pytest.mark.asyncio
@patch("src.api.health_endpoints.rate_limiter")
async def test_get_rate_limit_status_exception(mock_limiter):
    """Test rate limit status when exception occurs."""
    mock_limiter.get_all_stats.side_effect = Exception("Limiter unavailable")

    with pytest.raises(HTTPException) as exc_info:
        await get_rate_limit_status("test_user")

    assert exc_info.value.status_code == 500
    assert "Failed to get rate limit status" in exc_info.value.detail


# ============================================================================
# set_user_tier Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.rate_limiter")
async def test_set_user_tier_premium(mock_limiter):
    """Test setting user to premium tier."""
    result = await set_user_tier("test_user", tier="premium")

    assert result["user_id"] == "test_user"
    assert result["tier"] == "premium"
    assert "updated_at" in result
    mock_limiter.user_limiter.set_user_tier.assert_called_once_with("test_user", "premium")


@pytest.mark.asyncio
@patch("src.api.health_endpoints.rate_limiter")
async def test_set_user_tier_enterprise(mock_limiter):
    """Test setting user to enterprise tier."""
    result = await set_user_tier("enterprise_user", tier="enterprise")

    assert result["tier"] == "enterprise"
    mock_limiter.user_limiter.set_user_tier.assert_called_once_with("enterprise_user", "enterprise")


@pytest.mark.asyncio
@patch("src.api.health_endpoints.rate_limiter")
async def test_set_user_tier_free(mock_limiter):
    """Test setting user to free tier."""
    result = await set_user_tier("free_user", tier="free")

    assert result["tier"] == "free"


@pytest.mark.asyncio
@patch("src.api.health_endpoints.rate_limiter")
async def test_set_user_tier_exception(mock_limiter):
    """Test setting user tier when exception occurs."""
    mock_limiter.user_limiter.set_user_tier.side_effect = Exception("Update failed")

    with pytest.raises(HTTPException) as exc_info:
        await set_user_tier("test_user", tier="premium")

    assert exc_info.value.status_code == 500
    assert "Failed to set user tier" in exc_info.value.detail


# ============================================================================
# get_component_health Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_get_component_health_database(mock_checker, mock_component_health):
    """Test database component health check."""
    mock_component_health.name = "database"
    mock_checker.check_database_health = AsyncMock(return_value=mock_component_health)

    result = await get_component_health("database")

    assert isinstance(result, JSONResponse)
    assert result.status_code == 200
    mock_checker.check_database_health.assert_called_once()


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_get_component_health_llm(mock_checker, mock_component_health):
    """Test LLM component health check."""
    mock_component_health.name = "llm"
    mock_checker.check_llm_health = AsyncMock(return_value=mock_component_health)

    result = await get_component_health("llm")

    assert isinstance(result, JSONResponse)
    mock_checker.check_llm_health.assert_called_once()


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_get_component_health_embedding(mock_checker, mock_component_health):
    """Test embedding component health check."""
    mock_component_health.name = "embedding"
    mock_checker.check_embedding_health = AsyncMock(return_value=mock_component_health)

    result = await get_component_health("embedding")

    assert isinstance(result, JSONResponse)
    mock_checker.check_embedding_health.assert_called_once()


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_get_component_health_memory(mock_checker, mock_component_health):
    """Test memory component health check."""
    mock_component_health.name = "memory"
    mock_checker.check_memory_health = AsyncMock(return_value=mock_component_health)

    result = await get_component_health("memory")

    assert isinstance(result, JSONResponse)
    mock_checker.check_memory_health.assert_called_once()


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_get_component_health_web_search(mock_checker, mock_component_health):
    """Test web search component health check."""
    mock_component_health.name = "web_search"
    mock_checker.check_web_search_health = AsyncMock(return_value=mock_component_health)

    result = await get_component_health("web_search")

    assert isinstance(result, JSONResponse)
    mock_checker.check_web_search_health.assert_called_once()


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_get_component_health_degraded(mock_checker):
    """Test component health when degraded."""
    degraded_health = MagicMock()
    degraded_health.name = "database"
    degraded_health.status = "degraded"
    degraded_health.response_time = 2.5
    degraded_health.error = None
    degraded_health.last_check = datetime.now(UTC)
    degraded_health.details = {}

    mock_checker.check_database_health = AsyncMock(return_value=degraded_health)

    result = await get_component_health("database")

    assert result.status_code == 200  # Degraded still returns 200


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_get_component_health_unhealthy(mock_checker):
    """Test component health when unhealthy."""
    unhealthy_health = MagicMock()
    unhealthy_health.name = "database"
    unhealthy_health.status = "unhealthy"
    unhealthy_health.response_time = None
    unhealthy_health.error = "Connection timeout"
    unhealthy_health.last_check = datetime.now(UTC)
    unhealthy_health.details = {}

    mock_checker.check_database_health = AsyncMock(return_value=unhealthy_health)

    result = await get_component_health("database")

    assert result.status_code == 503


@pytest.mark.asyncio
async def test_get_component_health_unknown_component():
    """Test component health for unknown component."""
    with pytest.raises(HTTPException) as exc_info:
        await get_component_health("unknown_component")

    assert exc_info.value.status_code == 404
    assert "Unknown component" in exc_info.value.detail


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_get_component_health_exception(mock_checker):
    """Test component health when exception occurs."""
    mock_checker.check_database_health = AsyncMock(side_effect=Exception("Check failed"))

    with pytest.raises(HTTPException) as exc_info:
        await get_component_health("database")

    assert exc_info.value.status_code == 500


# ============================================================================
# readiness_check Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_readiness_check_ready(mock_checker, mock_component_health):
    """Test readiness check when service is ready."""
    db_health = MagicMock()
    db_health.status = "healthy"
    db_health.name = "database"

    llm_health = MagicMock()
    llm_health.status = "healthy"
    llm_health.name = "llm"

    mock_checker.check_database_health = AsyncMock(return_value=db_health)
    mock_checker.check_llm_health = AsyncMock(return_value=llm_health)

    result = await readiness_check()

    assert result["ready"] is True
    assert "timestamp" in result


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_readiness_check_not_ready_db(mock_checker):
    """Test readiness check when database is unhealthy."""
    db_health = MagicMock()
    db_health.status = "unhealthy"
    db_health.name = "database"

    llm_health = MagicMock()
    llm_health.status = "healthy"
    llm_health.name = "llm"

    mock_checker.check_database_health = AsyncMock(return_value=db_health)
    mock_checker.check_llm_health = AsyncMock(return_value=llm_health)

    result = await readiness_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 503


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_readiness_check_not_ready_llm(mock_checker):
    """Test readiness check when LLM is unhealthy."""
    db_health = MagicMock()
    db_health.status = "healthy"
    db_health.name = "database"

    llm_health = MagicMock()
    llm_health.status = "unhealthy"
    llm_health.name = "llm"

    mock_checker.check_database_health = AsyncMock(return_value=db_health)
    mock_checker.check_llm_health = AsyncMock(return_value=llm_health)

    result = await readiness_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 503


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_readiness_check_degraded_still_ready(mock_checker):
    """Test that degraded components don't block readiness."""
    db_health = MagicMock()
    db_health.status = "degraded"
    db_health.name = "database"

    llm_health = MagicMock()
    llm_health.status = "healthy"
    llm_health.name = "llm"

    mock_checker.check_database_health = AsyncMock(return_value=db_health)
    mock_checker.check_llm_health = AsyncMock(return_value=llm_health)

    result = await readiness_check()

    # Degraded doesn't block readiness
    assert result["ready"] is True


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_readiness_check_exception(mock_checker):
    """Test readiness check when exception occurs."""
    mock_checker.check_database_health = AsyncMock(side_effect=Exception("Check failed"))

    result = await readiness_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 503


# ============================================================================
# liveness_check Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.monitor")
async def test_liveness_check_alive(mock_monitor):
    """Test liveness check when service is alive."""
    mock_monitor.get_system_stats.return_value = {"uptime": 3600.0}

    result = await liveness_check()

    assert result["alive"] is True
    assert result["uptime"] == 3600.0
    assert "timestamp" in result


@pytest.mark.asyncio
@patch("src.api.health_endpoints.monitor")
async def test_liveness_check_exception(mock_monitor):
    """Test liveness check when exception occurs."""
    mock_monitor.get_system_stats.side_effect = Exception("Monitor failed")

    result = await liveness_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 503


# ============================================================================
# startup_check Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_startup_check_started(mock_checker, mock_health_status):
    """Test startup check when service has started."""
    mock_checker.get_health_status = AsyncMock(return_value=mock_health_status)

    result = await startup_check()

    assert result["started"] is True
    assert result["uptime"] == 3600.0
    assert "timestamp" in result


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_startup_check_not_started(mock_checker):
    """Test startup check when service hasn't started."""
    unhealthy_status = MagicMock()
    unhealthy_status.status = "unhealthy"
    unhealthy_status.uptime = 10.0
    unhealthy_status.checks = {
        "database": {"status": "unhealthy"},
        "llm": {"status": "healthy"},
    }

    mock_checker.get_health_status = AsyncMock(return_value=unhealthy_status)

    result = await startup_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 503


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_startup_check_degraded_still_started(mock_checker):
    """Test that degraded components don't block startup."""
    degraded_status = MagicMock()
    degraded_status.status = "degraded"
    degraded_status.uptime = 3600.0
    degraded_status.checks = {"memory": {"status": "degraded"}}

    mock_checker.get_health_status = AsyncMock(return_value=degraded_status)

    result = await startup_check()

    # Degraded components don't prevent startup
    assert result["started"] is True


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_startup_check_exception(mock_checker):
    """Test startup check when exception occurs."""
    mock_checker.get_health_status = AsyncMock(side_effect=Exception("Startup check failed"))

    result = await startup_check()

    assert isinstance(result, JSONResponse)
    assert result.status_code == 503


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_all_kubernetes_probes_together(mock_checker, mock_health_status):
    """Test all Kubernetes probe endpoints work together."""
    db_health = MagicMock()
    db_health.status = "healthy"
    db_health.name = "database"

    llm_health = MagicMock()
    llm_health.status = "healthy"
    llm_health.name = "llm"

    mock_checker.get_health_status = AsyncMock(return_value=mock_health_status)
    mock_checker.check_database_health = AsyncMock(return_value=db_health)
    mock_checker.check_llm_health = AsyncMock(return_value=llm_health)

    with patch("src.api.health_endpoints.monitor") as mock_monitor:
        mock_monitor.get_system_stats.return_value = {"uptime": 3600.0}

        liveness_result = await liveness_check()
        readiness_result = await readiness_check()
        startup_result = await startup_check()

        assert liveness_result["alive"] is True
        assert readiness_result["ready"] is True
        assert startup_result["started"] is True


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_all_component_health_checks(mock_checker, mock_component_health):
    """Test all component health checks."""
    mock_checker.check_database_health = AsyncMock(return_value=mock_component_health)
    mock_checker.check_llm_health = AsyncMock(return_value=mock_component_health)
    mock_checker.check_embedding_health = AsyncMock(return_value=mock_component_health)
    mock_checker.check_memory_health = AsyncMock(return_value=mock_component_health)
    mock_checker.check_web_search_health = AsyncMock(return_value=mock_component_health)

    components = ["database", "llm", "embedding", "memory", "web_search"]

    for component in components:
        result = await get_component_health(component)
        assert isinstance(result, JSONResponse)
        assert result.status_code == 200


@pytest.mark.asyncio
@patch("src.api.health_endpoints.rate_limiter")
async def test_all_user_tiers(mock_limiter):
    """Test setting all user tier types."""
    tiers = ["free", "premium", "enterprise"]

    for tier in tiers:
        result = await set_user_tier("test_user", tier=tier)
        assert result["tier"] == tier


@pytest.mark.asyncio
@patch("src.api.health_endpoints.health_checker")
async def test_concurrent_health_checks(mock_checker, mock_health_status, mock_component_health):
    """Test concurrent health check requests."""
    mock_checker.get_health_status = AsyncMock(return_value=mock_health_status)
    mock_checker.check_database_health = AsyncMock(return_value=mock_component_health)

    import asyncio

    results = await asyncio.gather(
        detailed_health_check(),
        get_component_health("database"),
        basic_health_check(),
    )

    assert len(results) == 3


@pytest.mark.asyncio
@patch("src.api.health_endpoints.get_settings")
async def test_basic_health_check_timestamp_recent(mock_get_settings, mock_settings):
    """Test that basic health check timestamp is recent."""
    mock_get_settings.return_value = mock_settings

    result = await basic_health_check()

    timestamp = datetime.fromisoformat(result["timestamp"])
    now = datetime.now(UTC)
    time_diff = now - timestamp

    # Timestamp should be within last second
    assert time_diff < timedelta(seconds=1)


@pytest.mark.asyncio
@patch("src.api.health_endpoints.monitor")
@patch("src.api.health_endpoints.get_settings")
async def test_metrics_high_values(mock_get_settings, mock_monitor, mock_settings):
    """Test metrics with high system usage values."""
    mock_get_settings.return_value = mock_settings
    mock_monitor.get_system_stats.return_value = {
        "cpu_percent": 99.9,
        "memory_percent": 95.0,
        "disk_percent": 88.0,
        "uptime": 86400.0 * 30,  # 30 days
        "request_count": 1000000,
        "error_count": 1000,
    }

    result = await get_metrics()

    assert result["system"]["cpu_percent"] == 99.9
    assert result["system"]["memory_percent"] == 95.0


@pytest.mark.asyncio
@patch("src.api.health_endpoints.rate_limiter")
async def test_rate_limit_status_multiple_users(mock_limiter):
    """Test getting rate limit status for multiple users."""
    users = [("user1", "free"), ("user2", "premium"), ("user3", "enterprise")]

    for user_id, tier in users:
        mock_limiter.get_all_stats.return_value = {
            "user_id": user_id,
            "tier": tier,
        }

        result = await get_rate_limit_status(user_id)
        assert result["user_id"] == user_id
        assert result["tier"] == tier
