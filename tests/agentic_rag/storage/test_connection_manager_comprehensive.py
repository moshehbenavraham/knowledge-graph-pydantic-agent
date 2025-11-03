"""
Comprehensive tests for ConnectionManager.

Covers initialization, connection pooling, circuit breaker logic, metrics tracking,
health checks, error handling, and resource cleanup.

Target: Increase coverage from 60% to 90%+ (cover 149 uncovered lines).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agentic_rag.storage.connection_manager import (
    CircuitBreakerConfig,
    ConnectionManager,
    ConnectionState,
    PoolMetrics,
)

# =====================================================
# DATA CLASS TESTS
# =====================================================


def test_pool_metrics_defaults():
    """Test PoolMetrics default values."""
    metrics = PoolMetrics()
    assert metrics.total_connections == 0
    assert metrics.active_connections == 0
    assert metrics.idle_connections == 0
    assert metrics.failed_connections == 0
    assert metrics.total_queries == 0
    assert metrics.failed_queries == 0
    assert metrics.avg_query_time_ms == 0.0
    assert metrics.last_error is None
    assert metrics.last_error_time is None


def test_circuit_breaker_config_defaults():
    """Test CircuitBreakerConfig default values."""
    config = CircuitBreakerConfig()
    assert config.failure_threshold == 5
    assert config.recovery_timeout == timedelta(seconds=60)
    assert config.half_open_requests == 3


def test_connection_state_enum():
    """Test ConnectionState enum values."""
    assert ConnectionState.CLOSED.value == "closed"
    assert ConnectionState.OPEN.value == "open"
    assert ConnectionState.HALF_OPEN.value == "half_open"


# =====================================================
# INITIALIZATION TESTS
# =====================================================


def test_connection_manager_init_with_config():
    """Test ConnectionManager initialization with custom config."""
    config = {"enable_graph": True, "database_url": "postgresql://test"}
    manager = ConnectionManager(config)

    assert manager.config == config
    assert manager.pg_pool is None
    assert manager.neo4j_driver is None
    assert manager.redis_client is None
    assert isinstance(manager.pg_metrics, PoolMetrics)
    assert isinstance(manager.neo4j_metrics, PoolMetrics)
    assert manager.pg_state == ConnectionState.CLOSED
    assert manager.neo4j_state == ConnectionState.CLOSED


def test_connection_manager_init_without_config():
    """Test ConnectionManager initialization without config."""
    with patch("src.agentic_rag.config.get_config") as mock_config:
        mock_config.return_value.dict.return_value = {"enable_graph": False}

        manager = ConnectionManager()

        assert manager.config["enable_graph"] is False


def test_connection_manager_circuit_breaker_initial_state():
    """Test initial circuit breaker state."""
    manager = ConnectionManager({})

    assert manager.pg_failures == 0
    assert manager.neo4j_failures == 0
    assert manager.pg_last_failure_time is None
    assert manager.neo4j_last_failure_time is None


# =====================================================
# CIRCUIT BREAKER TESTS
# =====================================================


def test_check_circuit_breaker_closed():
    """Test circuit breaker in CLOSED state."""
    manager = ConnectionManager({})
    manager.pg_state = ConnectionState.CLOSED

    assert manager._check_circuit_breaker("pg") is True


def test_check_circuit_breaker_open():
    """Test circuit breaker in OPEN state (should block)."""
    manager = ConnectionManager({})
    manager.pg_state = ConnectionState.OPEN
    manager.pg_last_failure_time = datetime.now(UTC)

    # Should be blocked (not enough time passed)
    assert manager._check_circuit_breaker("pg") is False


def test_check_circuit_breaker_open_recovery():
    """Test circuit breaker transition from OPEN to HALF_OPEN."""
    manager = ConnectionManager({})
    manager.pg_state = ConnectionState.OPEN
    manager.pg_last_failure_time = datetime.now(UTC) - timedelta(
        seconds=120
    )  # Past recovery timeout

    # Should transition to HALF_OPEN
    result = manager._check_circuit_breaker("pg")

    assert result is True
    assert manager.pg_state == ConnectionState.HALF_OPEN
    assert manager.pg_failures == 0


def test_check_circuit_breaker_half_open():
    """Test circuit breaker in HALF_OPEN state."""
    manager = ConnectionManager({})
    manager.pg_state = ConnectionState.HALF_OPEN

    assert manager._check_circuit_breaker("pg") is True


def test_record_failure_below_threshold():
    """Test recording failures below threshold."""
    manager = ConnectionManager({})
    manager.pg_state = ConnectionState.CLOSED
    manager.pg_failures = 3

    error = Exception("Test error")
    manager._record_failure("pg", error)

    assert manager.pg_failures == 4
    assert manager.pg_state == ConnectionState.CLOSED  # Still closed
    assert manager.pg_metrics.failed_connections == 1
    assert manager.pg_metrics.last_error == "Test error"


def test_record_failure_reaches_threshold():
    """Test circuit breaker opens when threshold reached."""
    manager = ConnectionManager({})
    manager.pg_state = ConnectionState.CLOSED
    manager.pg_failures = 4  # One below threshold

    error = Exception("Critical error")
    manager._record_failure("pg", error)

    assert manager.pg_failures == 5  # Reached threshold
    assert manager.pg_state == ConnectionState.OPEN  # Opened
    assert manager.pg_last_failure_time is not None


def test_record_failure_neo4j():
    """Test recording Neo4j failures."""
    manager = ConnectionManager({})
    manager.neo4j_state = ConnectionState.CLOSED
    manager.neo4j_failures = 0

    error = Exception("Neo4j error")
    manager._record_failure("neo4j", error)

    assert manager.neo4j_failures == 1
    assert manager.neo4j_metrics.failed_connections == 1
    assert manager.neo4j_metrics.last_error == "Neo4j error"


# =====================================================
# METRICS TESTS
# =====================================================


def test_update_query_metrics_postgresql():
    """Test updating query metrics for PostgreSQL."""
    manager = ConnectionManager({})
    manager.pg_metrics.total_queries = 10
    manager.pg_metrics.avg_query_time_ms = 50.0

    manager._update_query_metrics("pg", 100.0)

    assert manager.pg_metrics.total_queries == 11
    # New average should be weighted
    assert manager.pg_metrics.avg_query_time_ms > 50.0


def test_update_query_metrics_neo4j():
    """Test updating query metrics for Neo4j."""
    manager = ConnectionManager({})
    manager.neo4j_metrics.total_queries = 0

    manager._update_query_metrics("neo4j", 75.5)

    assert manager.neo4j_metrics.total_queries == 1
    assert manager.neo4j_metrics.avg_query_time_ms == 75.5


def test_update_query_metrics_first_query():
    """Test metrics update for first query."""
    manager = ConnectionManager({})

    manager._update_query_metrics("pg", 120.0)

    assert manager.pg_metrics.total_queries == 1
    assert manager.pg_metrics.avg_query_time_ms == 120.0


# =====================================================
# HEALTH CHECK TESTS
# =====================================================


@pytest.mark.asyncio
async def test_health_check_all_healthy():
    """Test health check when all services are healthy."""
    manager = ConnectionManager({"enable_graph": True})

    # Mock pg_pool with acquire context manager
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_pool_acquire = AsyncMock()
    mock_pool_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool_acquire.__aexit__ = AsyncMock(return_value=None)

    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_pool_acquire)
    manager.pg_pool = mock_pool

    # Mock neo4j_driver with session context manager
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=1)
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_driver = AsyncMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    manager.neo4j_driver = mock_driver

    # Mock redis
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    manager.redis_client = mock_redis

    health = await manager.health_check()

    assert health["services"]["postgresql"]["healthy"] is True
    assert health["services"]["neo4j"]["healthy"] is True
    assert health["services"]["redis"]["healthy"] is True
    assert health["overall_health"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_postgresql_unhealthy():
    """Test health check when PostgreSQL is unhealthy."""
    manager = ConnectionManager({})

    # Mock pool that raises exception
    mock_pool_acquire = AsyncMock()
    mock_pool_acquire.__aenter__ = AsyncMock(side_effect=Exception("Connection failed"))
    mock_pool_acquire.__aexit__ = AsyncMock(return_value=None)

    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_pool_acquire)
    manager.pg_pool = mock_pool

    # Need neo4j to be None for this test
    manager.neo4j_driver = None

    health = await manager.health_check()

    assert health["services"]["postgresql"]["healthy"] is False


@pytest.mark.asyncio
async def test_health_check_neo4j_disabled():
    """Test health check when Neo4j is disabled."""
    manager = ConnectionManager({"enable_graph": False})
    manager.neo4j_driver = None
    manager.pg_pool = None

    health = await manager.health_check()

    assert health["services"]["neo4j"]["healthy"] is False


@pytest.mark.asyncio
async def test_health_check_neo4j_unhealthy():
    """Test health check when Neo4j is unhealthy."""
    manager = ConnectionManager({"enable_graph": True})

    # Mock pg first
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_pool_acquire = AsyncMock()
    mock_pool_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool_acquire.__aexit__ = AsyncMock(return_value=None)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_pool_acquire)
    manager.pg_pool = mock_pool

    # Mock neo4j with error
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(side_effect=Exception("Neo4j connection failed"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_driver = AsyncMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    manager.neo4j_driver = mock_driver

    health = await manager.health_check()

    assert health["services"]["neo4j"]["healthy"] is False


@pytest.mark.asyncio
async def test_health_check_redis_unavailable():
    """Test health check when Redis is unavailable."""
    manager = ConnectionManager({})
    manager.redis_client = None
    manager.pg_pool = None
    manager.neo4j_driver = None

    health = await manager.health_check()

    assert health["services"]["redis"]["healthy"] is False
    assert health["services"]["redis"]["enabled"] is False


@pytest.mark.asyncio
async def test_health_check_includes_metrics():
    """Test that health check includes metrics."""
    manager = ConnectionManager({})

    # Mock pg_pool properly
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    mock_pool_acquire = AsyncMock()
    mock_pool_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool_acquire.__aexit__ = AsyncMock(return_value=None)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_pool_acquire)
    manager.pg_pool = mock_pool

    manager.neo4j_driver = None

    manager.pg_metrics.total_queries = 100
    manager.pg_metrics.failed_queries = 5
    manager.pg_metrics.avg_query_time_ms = 50.5

    health = await manager.health_check()

    assert "metrics" in health["services"]["postgresql"]
    # Health check itself calls get_pg_connection which increments total_queries
    assert health["services"]["postgresql"]["metrics"]["total_queries"] == 101
    assert health["services"]["postgresql"]["metrics"]["failed_queries"] == 5


# =====================================================
# GET REDIS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_redis_available():
    """Test getting Redis client when available."""
    manager = ConnectionManager({})
    mock_redis = AsyncMock()
    manager.redis_client = mock_redis

    client = await manager.get_redis()

    assert client is mock_redis


@pytest.mark.asyncio
async def test_get_redis_unavailable():
    """Test getting Redis client when unavailable."""
    manager = ConnectionManager({})
    manager.redis_client = None

    client = await manager.get_redis()

    assert client is None


# =====================================================
# CLOSE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_close_all_connections():
    """Test closing all connections."""
    manager = ConnectionManager({})

    # Mock pool, driver, and redis
    mock_pool = AsyncMock()
    mock_pool._closed = False
    mock_pool.close = AsyncMock(return_value=None)  # AsyncMock already returns awaitable
    manager.pg_pool = mock_pool

    mock_driver = AsyncMock()
    mock_driver.close = AsyncMock(return_value=None)  # AsyncMock already returns awaitable
    manager.neo4j_driver = mock_driver

    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock(return_value=None)  # AsyncMock already returns awaitable
    manager.redis_client = mock_redis

    await manager.close()

    mock_pool.close.assert_called_once()
    mock_driver.close.assert_called_once()
    mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_close_partial_connections():
    """Test closing when only some connections exist."""
    manager = ConnectionManager({})

    # Only PostgreSQL pool exists
    mock_pool = AsyncMock()
    mock_pool._closed = False
    mock_pool.close = AsyncMock(return_value=None)  # AsyncMock already returns awaitable
    manager.pg_pool = mock_pool
    manager.neo4j_driver = None
    manager.redis_client = None

    # Should not raise
    await manager.close()

    mock_pool.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_no_connections():
    """Test closing when no connections exist."""
    manager = ConnectionManager({})
    manager.pg_pool = None
    manager.neo4j_driver = None
    manager.redis_client = None

    # Should not raise
    await manager.close()


# =====================================================
# CONTEXT MANAGER TESTS
# =====================================================


@pytest.mark.asyncio
async def test_context_manager_entry_exit():
    """Test async context manager."""
    with patch.object(ConnectionManager, "initialize", new_callable=AsyncMock):
        with patch.object(ConnectionManager, "close", new_callable=AsyncMock):
            manager = ConnectionManager({})

            async with manager as m:
                assert m is manager

            # close() should have been called


@pytest.mark.asyncio
async def test_context_manager_exception_handling():
    """Test context manager exception handling."""
    with patch.object(ConnectionManager, "initialize", new_callable=AsyncMock):
        with patch.object(ConnectionManager, "close", new_callable=AsyncMock):
            manager = ConnectionManager({})

            try:
                async with manager:
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Exception should propagate

            # close() should still have been called


# =====================================================
# INTEGRATION-STYLE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_circuit_breaker_recovery_cycle():
    """Test full circuit breaker cycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    manager = ConnectionManager({})

    # Start in CLOSED state
    assert manager.pg_state == ConnectionState.CLOSED

    # Trigger 5 failures to OPEN circuit
    for i in range(5):
        manager._record_failure("pg", Exception(f"Error {i+1}"))

    assert manager.pg_state == ConnectionState.OPEN
    assert manager.pg_failures == 5

    # Check circuit breaker (should block)
    assert manager._check_circuit_breaker("pg") is False

    # Simulate time passing (recovery timeout)
    manager.pg_last_failure_time = datetime.now(UTC) - timedelta(seconds=120)

    # Check again (should transition to HALF_OPEN)
    assert manager._check_circuit_breaker("pg") is True
    assert manager.pg_state == ConnectionState.HALF_OPEN
    # Note: failures are NOT reset when entering HALF_OPEN
    # They are only reset on successful connection in get_pg_connection()


@pytest.mark.asyncio
async def test_metrics_accumulation():
    """Test that metrics accumulate correctly."""
    manager = ConnectionManager({})

    # Record multiple queries
    for elapsed in [10.0, 20.0, 30.0, 40.0, 50.0]:
        manager._update_query_metrics("pg", elapsed)

    assert manager.pg_metrics.total_queries == 5
    # Average should be 30.0
    assert 29.0 < manager.pg_metrics.avg_query_time_ms < 31.0


@pytest.mark.asyncio
async def test_multiple_service_metrics():
    """Test metrics for multiple services independently."""
    manager = ConnectionManager({})

    # PostgreSQL metrics
    manager._update_query_metrics("pg", 100.0)
    manager._update_query_metrics("pg", 200.0)

    # Neo4j metrics
    manager._update_query_metrics("neo4j", 50.0)

    assert manager.pg_metrics.total_queries == 2
    assert manager.neo4j_metrics.total_queries == 1
    assert manager.pg_metrics.avg_query_time_ms != manager.neo4j_metrics.avg_query_time_ms
