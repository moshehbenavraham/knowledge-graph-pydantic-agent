"""
Comprehensive tests for ConnectionManager with pooling, circuit breakers, and monitoring.

Covers:
- Initialization with various configurations
- PostgreSQL pool creation and management
- Neo4j driver initialization
- Redis client initialization
- Circuit breaker patterns (CLOSED, OPEN, HALF_OPEN)
- Connection context managers
- Health checks and monitoring
- Metrics tracking
- Singleton pattern
- Event loop handling
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agentic_rag.storage.connection_manager import (
    CircuitBreakerConfig,
    ConnectionManager,
    ConnectionState,
    PoolMetrics,
    close_connections,
    get_connection_manager,
)


# ===== Test Data & Fixtures =====


@pytest.fixture
def mock_config():
    """Standard config for testing."""
    return {
        "database_url": "postgresql://user:pass@localhost:5432/test",
        "neo4j_uri": "neo4j://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "password",
        "neo4j_database": "neo4j",
        "redis_url": "redis://localhost:6379",
        "pg_pool_min": 5,
        "pg_pool_max": 20,
        "neo4j_pool_size": 50,
        "redis_pool_size": 10,
        "enable_graph": True,
        "enable_redis_cache": True,
    }


@pytest.fixture
def connection_manager(mock_config):
    """Create a ConnectionManager instance."""
    return ConnectionManager(mock_config)


# ===== Initialization Tests =====


@pytest.mark.asyncio
class TestConnectionManagerInit:
    """Test ConnectionManager initialization."""

    def test_init_with_config(self, mock_config):
        """Test initialization with provided config."""
        cm = ConnectionManager(mock_config)
        assert cm.config == mock_config
        assert cm.pg_pool is None
        assert cm.neo4j_driver is None
        assert cm.redis_client is None
        assert cm.pg_state == ConnectionState.CLOSED
        assert cm.neo4j_state == ConnectionState.CLOSED

    def test_init_without_config(self):
        """Test initialization without config (uses default from get_config)."""
        with patch("src.agentic_rag.storage.connection_manager.get_config") as mock_get_config:
            mock_config_obj = Mock()
            mock_config_obj.dict.return_value = {"database_url": "test"}
            mock_get_config.return_value = mock_config_obj

            cm = ConnectionManager()
            assert cm.config == {"database_url": "test"}

    def test_init_creates_metrics(self, connection_manager):
        """Test that initialization creates metrics objects."""
        assert isinstance(connection_manager.pg_metrics, PoolMetrics)
        assert isinstance(connection_manager.neo4j_metrics, PoolMetrics)
        assert isinstance(connection_manager.redis_metrics, PoolMetrics)

    def test_init_creates_circuit_breaker_config(self, connection_manager):
        """Test that circuit breaker config is created."""
        assert isinstance(connection_manager.circuit_config, CircuitBreakerConfig)
        assert connection_manager.circuit_config.failure_threshold == 5
        assert connection_manager.circuit_config.half_open_requests == 3

    async def test_initialize_all_services(self, connection_manager):
        """Test initializing all services."""
        with patch.object(
            connection_manager, "_init_postgresql", new=AsyncMock()
        ) as mock_pg, patch.object(
            connection_manager, "_init_neo4j", new=AsyncMock()
        ) as mock_neo4j, patch.object(
            connection_manager, "_init_redis", new=AsyncMock()
        ) as mock_redis:
            await connection_manager.initialize()

            mock_pg.assert_called_once()
            mock_neo4j.assert_called_once()
            mock_redis.assert_called_once()

    async def test_initialize_without_graph(self, connection_manager):
        """Test initialization with graph disabled."""
        connection_manager.config["enable_graph"] = False

        with patch.object(
            connection_manager, "_init_postgresql", new=AsyncMock()
        ) as mock_pg, patch.object(
            connection_manager, "_init_neo4j", new=AsyncMock()
        ) as mock_neo4j, patch.object(
            connection_manager, "_init_redis", new=AsyncMock()
        ) as mock_redis:
            await connection_manager.initialize()

            mock_pg.assert_called_once()
            mock_neo4j.assert_not_called()
            mock_redis.assert_called_once()

    async def test_initialize_without_redis(self, connection_manager):
        """Test initialization with Redis disabled."""
        connection_manager.config["enable_redis_cache"] = False

        with patch.object(
            connection_manager, "_init_postgresql", new=AsyncMock()
        ) as mock_pg, patch.object(
            connection_manager, "_init_neo4j", new=AsyncMock()
        ) as mock_neo4j, patch.object(
            connection_manager, "_init_redis", new=AsyncMock()
        ) as mock_redis:
            await connection_manager.initialize()

            mock_pg.assert_called_once()
            mock_neo4j.assert_called_once()
            mock_redis.assert_not_called()

    async def test_initialize_handles_critical_failure(self, connection_manager):
        """Test that critical service failures are raised."""
        with patch.object(
            connection_manager, "_init_postgresql", new=AsyncMock(side_effect=Exception("PG failed"))
        ):
            with pytest.raises(Exception, match="PG failed"):
                await connection_manager.initialize()

    async def test_initialize_handles_non_critical_failure(self, connection_manager):
        """Test that Redis failures don't stop initialization."""
        with patch.object(
            connection_manager, "_init_postgresql", new=AsyncMock()
        ), patch.object(connection_manager, "_init_neo4j", new=AsyncMock()), patch.object(
            connection_manager,
            "_init_redis",
            new=AsyncMock(side_effect=Exception("Redis failed")),
        ):
            # Should not raise (Redis is non-critical)
            await connection_manager.initialize()


# ===== PostgreSQL Tests =====


@pytest.mark.asyncio
class TestPostgreSQLPool:
    """Test PostgreSQL connection pool."""

    async def test_init_postgresql_creates_pool(self, connection_manager):
        """Test that PostgreSQL pool is created."""
        mock_pool = Mock()
        mock_pool.get_size.return_value = 5
        mock_pool._closed = False

        with patch("src.agentic_rag.storage.connection_manager.asyncpg.create_pool") as mock_create:
            mock_create.return_value = mock_pool

            await connection_manager._init_postgresql()

            assert connection_manager.pg_pool == mock_pool
            assert connection_manager.pg_state == ConnectionState.CLOSED
            assert connection_manager.pg_metrics.total_connections == 5

    async def test_init_postgresql_with_custom_pool_size(self, connection_manager):
        """Test PostgreSQL initialization with custom pool sizes."""
        connection_manager.config["pg_pool_min"] = 10
        connection_manager.config["pg_pool_max"] = 50

        mock_pool = Mock()
        mock_pool.get_size.return_value = 10
        mock_pool._closed = False

        with patch("src.agentic_rag.storage.connection_manager.asyncpg.create_pool") as mock_create:
            mock_create.return_value = mock_pool

            await connection_manager._init_postgresql()

            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["min_size"] == 10
            assert call_kwargs["max_size"] == 50

    async def test_init_postgresql_failure(self, connection_manager):
        """Test PostgreSQL initialization failure."""
        with patch(
            "src.agentic_rag.storage.connection_manager.asyncpg.create_pool",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(Exception, match="Connection failed"):
                await connection_manager._init_postgresql()

            assert connection_manager.pg_state == ConnectionState.OPEN
            assert connection_manager.pg_metrics.last_error == "Connection failed"

    async def test_setup_postgres_connection(self, connection_manager):
        """Test PostgreSQL connection setup."""
        mock_conn = AsyncMock()

        await connection_manager._setup_postgres_connection(mock_conn)

        # Verify settings were applied
        assert mock_conn.execute.call_count == 2
        calls = [call[0][0] for call in mock_conn.execute.call_args_list]
        assert "SET work_mem = '50MB'" in calls
        assert "SET maintenance_work_mem = '256MB'" in calls

    async def test_init_postgres_connection(self, connection_manager):
        """Test PostgreSQL connection init (no-op currently)."""
        mock_conn = Mock()
        await connection_manager._init_postgres_connection(mock_conn)
        # Should not raise

    async def test_get_pg_connection_success(self, connection_manager):
        """Test getting PostgreSQL connection."""
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = AsyncMock(return_value=False)

        connection_manager.pg_pool = mock_pool

        async with connection_manager.get_pg_connection() as conn:
            assert conn == mock_conn
            assert connection_manager.pg_metrics.active_connections == 1

        # Should be decremented after exit
        assert connection_manager.pg_metrics.active_connections == 0
        assert connection_manager.pg_metrics.total_queries == 1

    async def test_get_pg_connection_not_initialized(self, connection_manager):
        """Test getting connection when pool not initialized."""
        with pytest.raises(ConnectionError, match="PostgreSQL pool not initialized"):
            async with connection_manager.get_pg_connection():
                pass

    async def test_get_pg_connection_circuit_breaker_open(self, connection_manager):
        """Test connection blocked when circuit breaker is open."""
        mock_pool = Mock()
        connection_manager.pg_pool = mock_pool
        connection_manager.pg_state = ConnectionState.OPEN
        connection_manager.pg_metrics.last_error = "Test error"

        with pytest.raises(ConnectionError, match="circuit breaker is OPEN"):
            async with connection_manager.get_pg_connection():
                pass


# ===== Neo4j Tests =====


@pytest.mark.asyncio
class TestNeo4jDriver:
    """Test Neo4j driver initialization and usage."""

    async def test_init_neo4j_basic_uri(self, connection_manager):
        """Test Neo4j initialization with basic URI."""
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock()

        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = AsyncMock(return_value=False)
        mock_session.run.return_value = mock_result

        with patch(
            "src.agentic_rag.storage.connection_manager.AsyncGraphDatabase.driver"
        ) as mock_create:
            mock_create.return_value = mock_driver

            await connection_manager._init_neo4j()

            assert connection_manager.neo4j_driver == mock_driver
            assert connection_manager.neo4j_state == ConnectionState.CLOSED
            mock_create.assert_called_once()

    async def test_init_neo4j_secure_uri(self, connection_manager):
        """Test Neo4j initialization with secure URI."""
        connection_manager.config["neo4j_uri"] = "neo4j+s://localhost:7687"

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock()

        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = AsyncMock(return_value=False)
        mock_session.run.return_value = mock_result

        with patch(
            "src.agentic_rag.storage.connection_manager.AsyncGraphDatabase.driver"
        ) as mock_create:
            mock_create.return_value = mock_driver

            await connection_manager._init_neo4j()

            # Verify no encryption config was added (it's in URI)
            call_kwargs = mock_create.call_args[1]
            assert "encrypted" not in call_kwargs

    async def test_init_neo4j_with_encryption_config(self, connection_manager):
        """Test Neo4j initialization with encryption config."""
        connection_manager.config["neo4j_encrypted"] = True
        connection_manager.config["neo4j_uri"] = "bolt://localhost:7687"  # Basic URI

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock()

        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = AsyncMock(return_value=False)
        mock_session.run.return_value = mock_result

        with patch(
            "src.agentic_rag.storage.connection_manager.AsyncGraphDatabase.driver"
        ) as mock_create, patch("src.agentic_rag.storage.connection_manager.TrustSystemCAs"):
            mock_create.return_value = mock_driver

            await connection_manager._init_neo4j()

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["encrypted"] is True

    async def test_init_neo4j_failure(self, connection_manager):
        """Test Neo4j initialization failure."""
        with patch(
            "src.agentic_rag.storage.connection_manager.AsyncGraphDatabase.driver",
            side_effect=Exception("Neo4j connection failed"),
        ):
            with pytest.raises(Exception, match="Neo4j connection failed"):
                await connection_manager._init_neo4j()

            assert connection_manager.neo4j_state == ConnectionState.OPEN
            assert connection_manager.neo4j_metrics.last_error == "Neo4j connection failed"

    async def test_get_neo4j_session_success(self, connection_manager):
        """Test getting Neo4j session."""
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = AsyncMock(return_value=False)

        connection_manager.neo4j_driver = mock_driver

        async with connection_manager.get_neo4j_session() as session:
            assert session == mock_session
            assert connection_manager.neo4j_metrics.active_connections == 1

        assert connection_manager.neo4j_metrics.active_connections == 0

    async def test_get_neo4j_session_with_database(self, connection_manager):
        """Test getting Neo4j session with specific database."""
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = AsyncMock(return_value=False)

        connection_manager.neo4j_driver = mock_driver

        async with connection_manager.get_neo4j_session(database="mydb") as session:
            assert session == mock_session

        mock_driver.session.assert_called_with(database="mydb")

    async def test_get_neo4j_session_not_initialized(self, connection_manager):
        """Test getting session when driver not initialized."""
        with pytest.raises(ConnectionError, match="Neo4j driver not initialized"):
            async with connection_manager.get_neo4j_session():
                pass


# ===== Redis Tests =====


@pytest.mark.asyncio
class TestRedisClient:
    """Test Redis client initialization."""

    async def test_init_redis_success(self, connection_manager):
        """Test Redis initialization."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        with patch("src.agentic_rag.storage.connection_manager.redis.from_url") as mock_from_url:
            mock_from_url.return_value = mock_redis

            await connection_manager._init_redis()

            assert connection_manager.redis_client == mock_redis
            mock_redis.ping.assert_called_once()

    async def test_init_redis_failure(self, connection_manager):
        """Test Redis initialization failure (non-critical)."""
        with patch(
            "src.agentic_rag.storage.connection_manager.redis.from_url",
            side_effect=Exception("Redis failed"),
        ):
            # Should not raise (Redis is non-critical)
            await connection_manager._init_redis()

            assert connection_manager.redis_client is None
            assert connection_manager.redis_metrics.last_error == "Redis failed"

    async def test_get_redis_client(self, connection_manager):
        """Test getting Redis client."""
        mock_redis = Mock()
        connection_manager.redis_client = mock_redis

        result = await connection_manager.get_redis()
        assert result == mock_redis

    async def test_get_redis_client_none(self, connection_manager):
        """Test getting Redis client when not initialized."""
        result = await connection_manager.get_redis()
        assert result is None


# ===== Circuit Breaker Tests =====


@pytest.mark.asyncio
class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_check_circuit_breaker_closed(self, connection_manager):
        """Test circuit breaker allows requests when CLOSED."""
        connection_manager.pg_state = ConnectionState.CLOSED
        assert connection_manager._check_circuit_breaker("pg") is True

    def test_check_circuit_breaker_open_no_recovery(self, connection_manager):
        """Test circuit breaker blocks requests when OPEN and recovery timeout not reached."""
        connection_manager.pg_state = ConnectionState.OPEN
        connection_manager.pg_last_failure_time = datetime.now(UTC)

        assert connection_manager._check_circuit_breaker("pg") is False

    def test_check_circuit_breaker_open_recovery_timeout(self, connection_manager):
        """Test circuit breaker enters HALF_OPEN after recovery timeout."""
        connection_manager.pg_state = ConnectionState.OPEN
        connection_manager.pg_last_failure_time = datetime.now(UTC) - timedelta(seconds=120)

        assert connection_manager._check_circuit_breaker("pg") is True
        assert connection_manager.pg_state == ConnectionState.HALF_OPEN

    def test_check_circuit_breaker_half_open(self, connection_manager):
        """Test circuit breaker allows requests in HALF_OPEN state."""
        connection_manager.pg_state = ConnectionState.HALF_OPEN
        assert connection_manager._check_circuit_breaker("pg") is True

    def test_record_failure_below_threshold(self, connection_manager):
        """Test recording failures below threshold."""
        error = Exception("Test error")

        connection_manager._record_failure("pg", error)

        assert connection_manager.pg_failures == 1
        assert connection_manager.pg_metrics.failed_connections == 1
        assert connection_manager.pg_metrics.last_error == "Test error"
        assert connection_manager.pg_state == ConnectionState.CLOSED

    def test_record_failure_reaches_threshold(self, connection_manager):
        """Test circuit breaker opens after reaching failure threshold."""
        error = Exception("Test error")

        # Record failures up to threshold
        for _ in range(5):
            connection_manager._record_failure("pg", error)

        assert connection_manager.pg_failures == 5
        assert connection_manager.pg_state == ConnectionState.OPEN
        assert connection_manager.pg_last_failure_time is not None

    def test_record_failure_neo4j(self, connection_manager):
        """Test recording Neo4j failures."""
        error = Exception("Neo4j error")

        for _ in range(5):
            connection_manager._record_failure("neo4j", error)

        assert connection_manager.neo4j_failures == 5
        assert connection_manager.neo4j_state == ConnectionState.OPEN

    async def test_connection_recovery_from_half_open(self, connection_manager):
        """Test successful connection recovery from HALF_OPEN."""
        mock_pool = Mock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = AsyncMock(return_value=False)

        connection_manager.pg_pool = mock_pool
        connection_manager.pg_state = ConnectionState.HALF_OPEN
        connection_manager.pg_failures = 3

        async with connection_manager.get_pg_connection():
            pass

        # Should transition back to CLOSED
        assert connection_manager.pg_state == ConnectionState.CLOSED
        assert connection_manager.pg_failures == 0


# ===== Metrics Tests =====


class TestMetrics:
    """Test metrics tracking."""

    def test_update_query_metrics_first_query(self, connection_manager):
        """Test updating metrics for first query."""
        connection_manager._update_query_metrics("pg", 100.0)

        assert connection_manager.pg_metrics.total_queries == 1
        assert connection_manager.pg_metrics.avg_query_time_ms == 100.0

    def test_update_query_metrics_running_average(self, connection_manager):
        """Test running average calculation."""
        connection_manager._update_query_metrics("pg", 100.0)
        connection_manager._update_query_metrics("pg", 200.0)
        connection_manager._update_query_metrics("pg", 300.0)

        assert connection_manager.pg_metrics.total_queries == 3
        assert connection_manager.pg_metrics.avg_query_time_ms == 200.0

    def test_update_neo4j_metrics(self, connection_manager):
        """Test Neo4j metrics tracking."""
        connection_manager._update_query_metrics("neo4j", 50.0)
        connection_manager._update_query_metrics("neo4j", 150.0)

        assert connection_manager.neo4j_metrics.total_queries == 2
        assert connection_manager.neo4j_metrics.avg_query_time_ms == 100.0


# ===== Health Check Tests =====


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check functionality."""

    async def test_health_check_all_healthy(self, connection_manager):
        """Test health check when all services are healthy."""
        # Mock PostgreSQL
        mock_pg_pool = Mock()
        mock_pg_conn = AsyncMock()
        mock_pg_conn.fetchval = AsyncMock(return_value=1)
        mock_pg_pool.acquire.return_value.__aenter__.return_value = mock_pg_conn
        mock_pg_pool.acquire.return_value.__aexit__.return_value = AsyncMock(return_value=False)

        # Mock Neo4j
        mock_neo4j_driver = AsyncMock()
        mock_neo4j_session = AsyncMock()
        mock_neo4j_result = AsyncMock()
        mock_neo4j_result.single = AsyncMock()
        mock_neo4j_session.run.return_value = mock_neo4j_result
        mock_neo4j_driver.session.return_value.__aenter__.return_value = mock_neo4j_session
        mock_neo4j_driver.session.return_value.__aexit__.return_value = AsyncMock(
            return_value=False
        )

        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        connection_manager.pg_pool = mock_pg_pool
        connection_manager.neo4j_driver = mock_neo4j_driver
        connection_manager.redis_client = mock_redis

        health = await connection_manager.health_check()

        assert health["overall_health"] == "healthy"
        assert health["services"]["postgresql"]["healthy"] is True
        assert health["services"]["neo4j"]["healthy"] is True
        assert health["services"]["redis"]["healthy"] is True

    async def test_health_check_degraded(self, connection_manager):
        """Test health check when services are degraded."""
        # Mock PostgreSQL failure
        mock_pg_pool = Mock()
        mock_pg_pool.acquire.side_effect = Exception("PG failed")

        # Mock Neo4j success
        mock_neo4j_driver = AsyncMock()
        mock_neo4j_session = AsyncMock()
        mock_neo4j_result = AsyncMock()
        mock_neo4j_result.single = AsyncMock()
        mock_neo4j_session.run.return_value = mock_neo4j_result
        mock_neo4j_driver.session.return_value.__aenter__.return_value = mock_neo4j_session
        mock_neo4j_driver.session.return_value.__aexit__.return_value = AsyncMock(
            return_value=False
        )

        connection_manager.pg_pool = mock_pg_pool
        connection_manager.neo4j_driver = mock_neo4j_driver
        connection_manager.redis_client = None

        health = await connection_manager.health_check()

        assert health["overall_health"] == "degraded"
        assert health["services"]["postgresql"]["healthy"] is False
        assert health["services"]["neo4j"]["healthy"] is True

    async def test_health_check_includes_metrics(self, connection_manager):
        """Test that health check includes metrics."""
        # Mock successful connections
        mock_pg_pool = Mock()
        mock_pg_conn = AsyncMock()
        mock_pg_conn.fetchval = AsyncMock(return_value=1)
        mock_pg_pool.acquire.return_value.__aenter__.return_value = mock_pg_conn
        mock_pg_pool.acquire.return_value.__aexit__.return_value = AsyncMock(return_value=False)

        mock_neo4j_driver = AsyncMock()
        mock_neo4j_session = AsyncMock()
        mock_neo4j_result = AsyncMock()
        mock_neo4j_result.single = AsyncMock()
        mock_neo4j_session.run.return_value = mock_neo4j_result
        mock_neo4j_driver.session.return_value.__aenter__.return_value = mock_neo4j_session
        mock_neo4j_driver.session.return_value.__aexit__.return_value = AsyncMock(
            return_value=False
        )

        connection_manager.pg_pool = mock_pg_pool
        connection_manager.neo4j_driver = mock_neo4j_driver
        connection_manager.pg_metrics.total_queries = 100
        connection_manager.pg_metrics.avg_query_time_ms = 50.5

        health = await connection_manager.health_check()

        pg_metrics = health["services"]["postgresql"]["metrics"]
        assert pg_metrics["total_queries"] == 100
        assert pg_metrics["avg_query_time_ms"] == 50.5


# ===== Context Manager Tests =====


@pytest.mark.asyncio
class TestContextManager:
    """Test async context manager."""

    async def test_context_manager_aenter(self, connection_manager):
        """Test __aenter__ initializes connections."""
        with patch.object(connection_manager, "initialize", new=AsyncMock()) as mock_init:
            result = await connection_manager.__aenter__()

            assert result == connection_manager
            mock_init.assert_called_once()

    async def test_context_manager_aexit(self, connection_manager):
        """Test __aexit__ closes connections."""
        with patch.object(connection_manager, "close", new=AsyncMock()) as mock_close:
            await connection_manager.__aexit__(None, None, None)

            mock_close.assert_called_once()

    async def test_context_manager_aexit_does_not_suppress(self, connection_manager):
        """Test that __aexit__ doesn't suppress exceptions."""
        with patch.object(connection_manager, "close", new=AsyncMock()):
            result = await connection_manager.__aexit__(Exception, "test", None)

            assert result is False


# ===== Close Tests =====


@pytest.mark.asyncio
class TestClose:
    """Test connection closing."""

    async def test_close_all_connections(self, connection_manager):
        """Test closing all connections."""
        mock_pg_pool = AsyncMock()
        mock_neo4j_driver = AsyncMock()
        mock_redis = AsyncMock()

        connection_manager.pg_pool = mock_pg_pool
        connection_manager.neo4j_driver = mock_neo4j_driver
        connection_manager.redis_client = mock_redis

        await connection_manager.close()

        mock_pg_pool.close.assert_called_once()
        mock_neo4j_driver.close.assert_called_once()
        mock_redis.aclose.assert_called_once()

    async def test_close_partial_connections(self, connection_manager):
        """Test closing when some connections are None."""
        mock_pg_pool = AsyncMock()
        connection_manager.pg_pool = mock_pg_pool
        connection_manager.neo4j_driver = None
        connection_manager.redis_client = None

        await connection_manager.close()

        mock_pg_pool.close.assert_called_once()


# ===== Singleton Pattern Tests =====


@pytest.mark.asyncio
class TestSingletonPattern:
    """Test global singleton pattern."""

    async def test_get_connection_manager_creates_singleton(self):
        """Test that get_connection_manager creates and returns singleton."""
        with patch(
            "src.agentic_rag.storage.connection_manager.config"
        ) as mock_config, patch.object(
            ConnectionManager, "initialize", new=AsyncMock()
        ), patch(
            "src.agentic_rag.storage.connection_manager.initialize_analytics_logger",
            new=AsyncMock(),
        ):
            mock_config.dict.return_value = {"database_url": "test"}

            cm1 = await get_connection_manager()
            cm2 = await get_connection_manager()

            # Should return same instance
            assert cm1 is cm2

    async def test_get_connection_manager_event_loop_change(self):
        """Test that singleton is recreated when event loop changes."""
        # Clean up first
        await close_connections()

        with patch(
            "src.agentic_rag.storage.connection_manager.config"
        ) as mock_config, patch.object(
            ConnectionManager, "initialize", new=AsyncMock()
        ), patch.object(
            ConnectionManager, "close", new=AsyncMock()
        ), patch(
            "src.agentic_rag.storage.connection_manager.initialize_analytics_logger",
            new=AsyncMock(),
        ):
            mock_config.dict.return_value = {"database_url": "test"}

            # Get first instance
            cm1 = await get_connection_manager()
            cm1_id = id(cm1)

            # Close and reset
            await close_connections()

            # Get new instance (simulates new event loop)
            cm2 = await get_connection_manager()
            cm2_id = id(cm2)

            # Should be different instances
            assert cm1_id != cm2_id

    async def test_get_connection_manager_initialization_failure(self):
        """Test that failed initialization doesn't set singleton."""
        # Clean up first
        await close_connections()

        with patch(
            "src.agentic_rag.storage.connection_manager.config"
        ) as mock_config, patch.object(
            ConnectionManager,
            "initialize",
            new=AsyncMock(side_effect=Exception("Init failed")),
        ):
            mock_config.dict.return_value = {"database_url": "test"}

            with pytest.raises(Exception, match="Init failed"):
                await get_connection_manager()

            # Singleton should still be None
            import src.agentic_rag.storage.connection_manager as cm_module

            assert cm_module._connection_manager is None

    async def test_close_connections_global(self):
        """Test close_connections clears global singleton."""
        with patch(
            "src.agentic_rag.storage.connection_manager.config"
        ) as mock_config, patch.object(
            ConnectionManager, "initialize", new=AsyncMock()
        ), patch.object(
            ConnectionManager, "close", new=AsyncMock()
        ), patch(
            "src.agentic_rag.storage.connection_manager.initialize_analytics_logger",
            new=AsyncMock(),
        ), patch(
            "src.agentic_rag.storage.connection_manager.shutdown_analytics_logger",
            new=AsyncMock(),
        ):
            mock_config.dict.return_value = {"database_url": "test"}

            # Create singleton
            await get_connection_manager()

            # Close it
            await close_connections()

            # Should be None
            import src.agentic_rag.storage.connection_manager as cm_module

            assert cm_module._connection_manager is None
            assert cm_module._connection_manager_loop_id is None
