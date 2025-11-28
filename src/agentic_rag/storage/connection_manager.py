"""
Centralized connection management with pooling, circuit breakers, and monitoring.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from types import TracebackType
from typing import TYPE_CHECKING, Any

import asyncpg
import redis.asyncio as redis
import structlog
from neo4j import AsyncGraphDatabase

if TYPE_CHECKING:
    from neo4j._async.driver import AsyncDriver

logger = logging.getLogger(__name__)
structlog_logger = structlog.get_logger(__name__)


class ConnectionState(Enum):
    """Connection pool states for circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class PoolMetrics:
    """Metrics for connection pool monitoring."""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    avg_query_time_ms: float = 0.0
    last_error: str | None = None
    last_error_time: datetime | None = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""

    failure_threshold: int = 5
    recovery_timeout: timedelta = timedelta(seconds=60)
    half_open_requests: int = 3


class ConnectionManager:
    """
    Centralized connection management with pooling, monitoring, and resilience.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        if config is None:
            from src.agentic_rag.config import get_config

            self.config = get_config().dict()
        else:
            self.config = config
        self.pg_pool: asyncpg.Pool | None = None
        self.neo4j_driver: AsyncDriver | None = None
        self.redis_client: redis.Redis[bytes] | None = None

        # Metrics tracking
        self.pg_metrics = PoolMetrics()
        self.neo4j_metrics = PoolMetrics()
        self.redis_metrics = PoolMetrics()

        # Circuit breaker state
        self.pg_state = ConnectionState.CLOSED
        self.neo4j_state = ConnectionState.CLOSED
        self.pg_failures = 0
        self.neo4j_failures = 0
        self.pg_last_failure_time: datetime | None = None
        self.neo4j_last_failure_time: datetime | None = None

        # Circuit breaker config
        self.circuit_config = CircuitBreakerConfig()

    async def initialize(self) -> None:
        """Initialize all connection pools with proper error handling."""
        structlog_logger.info("ConnectionManager.initialize() called")

        # Log event loop information
        try:
            loop = asyncio.get_running_loop()
            structlog_logger.info(
                "Event loop status",
                loop_id=id(loop),
                is_running=loop.is_running(),
                is_closed=loop.is_closed(),
            )
        except RuntimeError as e:
            structlog_logger.error("No running event loop", error=str(e))
            raise

        structlog_logger.info(
            "Configuration loaded",
            config_keys=list(self.config.keys()),
            enable_graph=self.config.get("enable_graph", True),
            enable_redis=self.config.get("enable_redis_cache", False),
        )

        initialization_tasks = [
            self._init_postgresql(),
            self._init_neo4j() if self.config.get("enable_graph", True) else None,
            self._init_redis() if self.config.get("enable_redis_cache") else None,
        ]

        tasks_to_run = [t for t in initialization_tasks if t]
        structlog_logger.info("Running initialization tasks", task_count=len(tasks_to_run))

        results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service = ["PostgreSQL", "Neo4j", "Redis"][i]
                structlog_logger.error(
                    "Service initialization failed",
                    service=service,
                    error=str(result),
                    error_type=type(result).__name__,
                )
                if i < 2:  # PostgreSQL and Neo4j are critical
                    raise result

        structlog_logger.info("ConnectionManager.initialize() completed successfully")

    async def _init_postgresql(self) -> None:
        """Initialize PostgreSQL connection pool with optimized settings."""
        structlog_logger.info(
            "_init_postgresql() starting",
            database_url_prefix=self.config["database_url"][:30],
            pool_min_size=self.config.get("pg_pool_min", 5),
            pool_max_size=self.config.get("pg_pool_max", 20),
        )

        try:
            # Check event loop again right before pool creation
            loop = asyncio.get_running_loop()
            structlog_logger.debug(
                "Event loop before pool creation",
                loop_id=id(loop),
                is_running=loop.is_running(),
                is_closed=loop.is_closed(),
            )

            # Check if pool already exists
            if self.pg_pool is not None:
                structlog_logger.warning(
                    "PostgreSQL pool already exists", pool_closed=self.pg_pool._closed
                )
                return

            structlog_logger.info("Creating asyncpg connection pool")

            # Create pool with simplified settings to avoid Streamlit event loop conflicts
            self.pg_pool = await asyncpg.create_pool(
                dsn=self.config["database_url"],
                min_size=self.config.get("pg_pool_min", 5),
                max_size=self.config.get("pg_pool_max", 20),
                timeout=30,
                command_timeout=60,
                setup=self._setup_postgres_connection,
                init=self._init_postgres_connection,
            )

            structlog_logger.info(
                "PostgreSQL pool created",
                pool_type=type(self.pg_pool).__name__,
                pool_closed=self.pg_pool._closed,
            )

            self.pg_state = ConnectionState.CLOSED  # CLOSED = healthy/normal operation
            self.pg_metrics.total_connections = self.pg_pool.get_size()
            structlog_logger.info(
                "PostgreSQL pool initialized successfully",
                total_connections=self.pg_metrics.total_connections,
            )

        except Exception as e:
            structlog_logger.error(
                "PostgreSQL initialization FAILED",
                error_type=type(e).__name__,
                error_message=str(e),
            )

            # Try to get more details about the error
            import traceback

            structlog_logger.error("Full traceback", traceback=traceback.format_exc())

            self.pg_state = ConnectionState.OPEN  # OPEN = broken/failure state
            self.pg_metrics.last_error = str(e)
            self.pg_metrics.last_error_time = datetime.now(UTC)
            raise

    async def _setup_postgres_connection(self, connection: asyncpg.Connection) -> None:
        """Setup function for each PostgreSQL connection."""
        structlog_logger.debug("_setup_postgres_connection() called", connection_id=id(connection))
        try:
            # Set connection-specific settings
            await connection.execute("SET work_mem = '50MB'")
            await connection.execute("SET maintenance_work_mem = '256MB'")
            structlog_logger.debug("Connection setup complete")
        except Exception as e:
            structlog_logger.error("Connection setup failed", error=str(e))
            raise

    async def _init_postgres_connection(self, connection: asyncpg.Connection) -> None:
        """Initialize function for new PostgreSQL connections."""
        structlog_logger.debug("_init_postgres_connection() called", connection_id=id(connection))
        # Prepare commonly used statements
        # NOTE: Commented out - schema uses embedding_1536/embedding_768 columns, not 'embedding'
        structlog_logger.debug("Connection init complete (no-op)")
        pass

    async def _init_neo4j(self) -> None:
        """Initialize Neo4j driver with connection pooling."""
        try:
            neo4j_uri = self.config["neo4j_uri"]

            # Build driver config
            driver_config = {
                "max_connection_pool_size": self.config.get("neo4j_pool_size", 50),
                "connection_acquisition_timeout": 30,
                "max_transaction_retry_time": 30,
                "database": self.config.get("neo4j_database", "neo4j"),
                "connection_timeout": 30.0,
                "keep_alive": True,
            }

            # Only add encryption settings if using basic URIs (bolt://, neo4j://)
            # For neo4j+s:// or bolt+s://, encryption is in the URI itself
            if "+s" not in neo4j_uri and "+ssc" not in neo4j_uri:
                from neo4j import TrustSystemCAs

                # Only add encryption config for basic URIs
                if self.config.get("neo4j_encrypted", False):
                    driver_config["encrypted"] = True
                    driver_config["trusted_certificates"] = TrustSystemCAs()

            self.neo4j_driver = AsyncGraphDatabase.driver(
                neo4j_uri,
                auth=(self.config["neo4j_user"], self.config["neo4j_password"]),
                **driver_config,
            )

            # Verify connectivity
            async with self.neo4j_driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()

            self.neo4j_state = ConnectionState.CLOSED  # CLOSED = healthy/normal operation
            structlog_logger.info("Neo4j driver initialized successfully")

        except Exception as e:
            self.neo4j_state = ConnectionState.OPEN  # OPEN = broken/failure state
            self.neo4j_metrics.last_error = str(e)
            self.neo4j_metrics.last_error_time = datetime.now(UTC)
            structlog_logger.error("Neo4j initialization failed", error=str(e))
            raise

    async def _init_redis(self) -> None:
        """Initialize Redis client for caching."""
        try:
            self.redis_client = redis.from_url(
                self.config["redis_url"],
                max_connections=self.config.get("redis_pool_size", 10),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError],
                health_check_interval=30,
            )

            # Verify connectivity
            await self.redis_client.ping()

            structlog_logger.info("Redis client initialized successfully")

        except Exception as e:
            structlog_logger.warning("Redis initialization failed (non-critical)", error=str(e))
            self.redis_metrics.last_error = str(e)
            self.redis_metrics.last_error_time = datetime.now(UTC)

    @asynccontextmanager
    async def get_pg_connection(self) -> AsyncIterator[asyncpg.Connection]:
        """
        Get PostgreSQL connection from pool with circuit breaker.
        """
        # Check if pool is initialized
        if self.pg_pool is None:
            raise ConnectionError(
                "PostgreSQL pool not initialized. "
                "Call await connection_manager.initialize() first."
            )

        if not self._check_circuit_breaker("pg"):
            raise ConnectionError(
                f"PostgreSQL circuit breaker is {self.pg_state.value.upper()} - blocking requests. "
                f"Last error: {self.pg_metrics.last_error}"
            )

        loop = asyncio.get_running_loop()
        start_time = loop.time()

        try:
            async with self.pg_pool.acquire() as conn:
                self.pg_metrics.active_connections += 1
                yield conn

            # Reset failure count on success
            if self.pg_state == ConnectionState.HALF_OPEN:
                self.pg_failures = 0
                self.pg_state = ConnectionState.CLOSED  # Back to healthy state
                structlog_logger.info(
                    "PostgreSQL circuit breaker CLOSED (healthy) - connection recovered"
                )

        except Exception as e:
            self._record_failure("pg", e)
            raise

        finally:
            self.pg_metrics.active_connections -= 1
            elapsed_ms = (loop.time() - start_time) * 1000
            self._update_query_metrics("pg", elapsed_ms)

    @asynccontextmanager
    async def get_neo4j_session(self, database: str | None = None) -> AsyncIterator[Any]:
        """
        Get Neo4j session with circuit breaker.
        """
        # Check if driver is initialized
        if self.neo4j_driver is None:
            raise ConnectionError(
                "Neo4j driver not initialized. "
                "Call await connection_manager.initialize() first or set ENABLE_GRAPH=true."
            )

        if not self._check_circuit_breaker("neo4j"):
            raise ConnectionError(
                f"Neo4j circuit breaker is {self.neo4j_state.value.upper()} - blocking requests. "
                f"Last error: {self.neo4j_metrics.last_error}"
            )

        loop = asyncio.get_running_loop()
        start_time = loop.time()

        try:
            async with self.neo4j_driver.session(database=database) as session:
                self.neo4j_metrics.active_connections += 1
                yield session

            # Reset failure count on success
            if self.neo4j_state == ConnectionState.HALF_OPEN:
                self.neo4j_failures = 0
                self.neo4j_state = ConnectionState.CLOSED  # Back to healthy state
                structlog_logger.info(
                    "Neo4j circuit breaker CLOSED (healthy) - connection recovered"
                )

        except Exception as e:
            self._record_failure("neo4j", e)
            raise

        finally:
            self.neo4j_metrics.active_connections -= 1
            elapsed_ms = (loop.time() - start_time) * 1000
            self._update_query_metrics("neo4j", elapsed_ms)

    def _check_circuit_breaker(self, service: str) -> bool:
        """
        Check if circuit breaker allows request.

        Circuit breaker states:
        - CLOSED = Normal operation (healthy) → Allow requests
        - OPEN = Failure state (broken) → Block requests, check for recovery
        - HALF_OPEN = Testing recovery → Allow limited requests
        """
        if service == "pg":
            state = self.pg_state
            last_failure = self.pg_last_failure_time
        else:
            state = self.neo4j_state
            last_failure = self.neo4j_last_failure_time

        # CLOSED = healthy, allow all requests
        if state == ConnectionState.CLOSED:
            return True

        # OPEN = broken, check if we should try recovery
        if state == ConnectionState.OPEN:
            if (
                last_failure
                and datetime.now(UTC) - last_failure > self.circuit_config.recovery_timeout
            ):
                # Try half-open state to test recovery
                if service == "pg":
                    self.pg_state = ConnectionState.HALF_OPEN
                    structlog_logger.info(
                        "PostgreSQL circuit breaker entering HALF_OPEN state for recovery test"
                    )
                else:
                    self.neo4j_state = ConnectionState.HALF_OPEN
                    structlog_logger.info(
                        "Neo4j circuit breaker entering HALF_OPEN state for recovery test"
                    )
                return True
            # Still broken, block request
            return False

        # HALF_OPEN state - allow requests to test recovery
        return True

    def _record_failure(self, service: str, error: Exception) -> None:
        """Record connection failure for circuit breaker."""
        if service == "pg":
            self.pg_failures += 1
            self.pg_metrics.failed_connections += 1
            self.pg_metrics.last_error = str(error)
            self.pg_metrics.last_error_time = datetime.now(UTC)

            if self.pg_failures >= self.circuit_config.failure_threshold:
                self.pg_state = ConnectionState.OPEN  # OPEN = broken/failure state
                self.pg_last_failure_time = datetime.now(UTC)
                structlog_logger.error(
                    "PostgreSQL circuit breaker OPEN (blocking requests)",
                    failure_count=self.pg_failures,
                    last_error=str(error)[:100],
                )

        else:
            self.neo4j_failures += 1
            self.neo4j_metrics.failed_connections += 1
            self.neo4j_metrics.last_error = str(error)
            self.neo4j_metrics.last_error_time = datetime.now(UTC)

            if self.neo4j_failures >= self.circuit_config.failure_threshold:
                self.neo4j_state = ConnectionState.OPEN  # OPEN = broken/failure state
                self.neo4j_last_failure_time = datetime.now(UTC)
                structlog_logger.error(
                    "Neo4j circuit breaker OPEN (blocking requests)",
                    failure_count=self.neo4j_failures,
                    last_error=str(error)[:100],
                )

    def _update_query_metrics(self, service: str, elapsed_ms: float) -> None:
        """Update query performance metrics."""
        if service == "pg":
            metrics = self.pg_metrics
        else:
            metrics = self.neo4j_metrics

        metrics.total_queries += 1

        # Calculate running average
        metrics.avg_query_time_ms = (
            metrics.avg_query_time_ms * (metrics.total_queries - 1) + elapsed_ms
        ) / metrics.total_queries

    async def get_redis(self) -> "redis.Redis[bytes] | None":
        """Get Redis client if available."""
        return self.redis_client

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on all connections."""
        structlog_logger.info("health_check called")
        health: dict[str, Any] = {"timestamp": datetime.now(UTC).isoformat(), "services": {}}

        # PostgreSQL health check
        pg_healthy = False
        try:
            async with self.get_pg_connection() as conn:
                await conn.fetchval("SELECT 1")
                pg_healthy = True
        except Exception as e:
            structlog_logger.error("PostgreSQL health check failed", error=str(e))

        health["services"]["postgresql"] = {
            "healthy": pg_healthy,
            "state": self.pg_state.value,
            "metrics": {
                "total_connections": self.pg_metrics.total_connections,
                "active_connections": self.pg_metrics.active_connections,
                "total_queries": self.pg_metrics.total_queries,
                "failed_queries": self.pg_metrics.failed_queries,
                "avg_query_time_ms": round(self.pg_metrics.avg_query_time_ms, 2),
            },
        }

        # Neo4j health check
        neo4j_healthy = False
        try:
            async with self.get_neo4j_session() as session:
                result = await session.run("RETURN 1")
                await result.single()
                neo4j_healthy = True
        except Exception as e:
            structlog_logger.error("Neo4j health check failed", error=str(e))

        health["services"]["neo4j"] = {
            "healthy": neo4j_healthy,
            "state": self.neo4j_state.value,
            "metrics": {
                "total_queries": self.neo4j_metrics.total_queries,
                "failed_queries": self.neo4j_metrics.failed_queries,
                "avg_query_time_ms": round(self.neo4j_metrics.avg_query_time_ms, 2),
            },
        }

        # Redis health check
        redis_healthy = False
        if self.redis_client:
            try:
                await self.redis_client.ping()
                redis_healthy = True
            except Exception as e:
                structlog_logger.warning("Redis health check failed", error=str(e))

        health["services"]["redis"] = {
            "healthy": redis_healthy,
            "enabled": self.redis_client is not None,
        }

        health["overall_health"] = "healthy" if (pg_healthy and neo4j_healthy) else "degraded"

        structlog_logger.info(
            "health_check completed",
            overall_health=health["overall_health"],
            pg_healthy=pg_healthy,
            neo4j_healthy=neo4j_healthy,
            redis_healthy=redis_healthy,
        )
        return health

    async def close(self) -> None:
        """Close all connections gracefully."""
        structlog_logger.info("ConnectionManager.close() called", instance_id=id(self))

        # Log stack trace to see who called close()
        import traceback

        structlog_logger.debug("Close called from", stack_trace="".join(traceback.format_stack()))

        close_tasks = []

        if self.pg_pool:
            structlog_logger.info("Closing PostgreSQL pool", pool_closed=self.pg_pool._closed)
            close_tasks.append(self.pg_pool.close())

        if self.neo4j_driver:
            structlog_logger.info("Closing Neo4j driver")
            close_tasks.append(self.neo4j_driver.close())

        if self.redis_client:
            structlog_logger.info("Closing Redis client")
            # aclose() is correct for async Redis - type stubs are incomplete
            close_tasks.append(self.redis_client.aclose())  # type: ignore[attr-defined]

        structlog_logger.info("Running close tasks", task_count=len(close_tasks))
        await asyncio.gather(*close_tasks, return_exceptions=True)
        structlog_logger.info("All connections closed successfully")

    async def __aenter__(self) -> "ConnectionManager":
        """Async context manager entry - initialize connections."""
        structlog_logger.info("ConnectionManager.__aenter__() called", instance_id=id(self))
        await self.initialize()
        structlog_logger.info("ConnectionManager.__aenter__() returning self")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> bool:
        """Async context manager exit - close connections."""
        structlog_logger.info(
            "ConnectionManager.__aexit__() called",
            instance_id=id(self),
            exception_type=exc_type,
            exception_value=str(exc_val) if exc_val else None,
        )
        await self.close()
        structlog_logger.info("ConnectionManager.__aexit__() done")
        return False  # Don't suppress exceptions


# Global connection manager instance
_connection_manager: ConnectionManager | None = None
_connection_manager_lock: asyncio.Lock | None = None
_connection_manager_loop_id: int | None = None  # Track event loop ID


async def get_connection_manager() -> ConnectionManager:
    """
    Get or create the global connection manager.

    Thread-safe singleton pattern with async lock to prevent race conditions.
    Automatically reinitializes if the event loop has changed (e.g., Streamlit reruns).
    """
    global _connection_manager, _connection_manager_lock, _connection_manager_loop_id

    # Create lock if needed (not async, so safe to do without lock)
    if _connection_manager_lock is None:
        _connection_manager_lock = asyncio.Lock()

    # Use lock to prevent race condition where multiple coroutines
    # try to create the connection manager simultaneously
    async with _connection_manager_lock:
        structlog_logger.info(
            "get_connection_manager() called (inside lock)", is_none=_connection_manager is None
        )

        # Check if event loop has changed (Streamlit reruns create new event loops)
        try:
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
            loop_changed = (
                _connection_manager_loop_id is not None
                and _connection_manager_loop_id != current_loop_id
            )

            if loop_changed:
                structlog_logger.info(
                    "Event loop changed (Streamlit rerun detected) - normal behavior",
                    old_loop_id=_connection_manager_loop_id,
                    new_loop_id=current_loop_id,
                )
                structlog_logger.info("Closing old connection manager and creating new one")
                if _connection_manager is not None:
                    try:
                        await _connection_manager.close()
                    except Exception as e:
                        structlog_logger.warning(
                            "Error closing old connection manager", error=str(e)
                        )
                    _connection_manager = None
                    _connection_manager_loop_id = None

        except RuntimeError:
            structlog_logger.warning("No running event loop found")
            current_loop_id = None

        if _connection_manager is not None:
            structlog_logger.info(
                "Returning existing connection manager",
                instance_id=id(_connection_manager),
                has_pg_pool=_connection_manager.pg_pool is not None,
            )
            return _connection_manager

        structlog_logger.info("Creating NEW connection manager")

        from src.agentic_rag.config import config  # Import config when needed

        temp_connection_manager = ConnectionManager(config.dict())
        structlog_logger.info(
            "ConnectionManager instance created", instance_id=id(temp_connection_manager)
        )

        try:
            structlog_logger.info("Calling initialize()")
            await temp_connection_manager.initialize()
            structlog_logger.info("initialize() completed")

            # Initialize analytics logger after connection manager is ready
            try:
                from src.agentic_rag.analytics import initialize_analytics_logger

                await initialize_analytics_logger(temp_connection_manager)
                structlog_logger.info("Analytics logger initialized successfully")
            except Exception as e:
                structlog_logger.warning(
                    "Analytics logger initialization failed (non-critical)", error=str(e)
                )

            # Only set global singleton if initialization succeeded
            _connection_manager = temp_connection_manager
            _connection_manager_loop_id = current_loop_id  # Store current loop ID
            structlog_logger.info(
                "Returning NEW connection manager",
                instance_id=id(_connection_manager),
                loop_id=_connection_manager_loop_id,
            )
            return _connection_manager

        except Exception as e:
            structlog_logger.error(
                "Failed to initialize ConnectionManager - will retry on next call", error=str(e)
            )
            # Don't set _connection_manager - leave it None so next call will retry
            raise


async def close_connections() -> None:
    """Close all connections."""
    global _connection_manager, _connection_manager_loop_id

    structlog_logger.info("close_connections() called")

    if _connection_manager:
        # Shutdown analytics logger first
        try:
            from src.agentic_rag.analytics import shutdown_analytics_logger

            await shutdown_analytics_logger()
            structlog_logger.info("Analytics logger shutdown successfully")
        except Exception as e:
            structlog_logger.warning("Analytics logger shutdown failed", error=str(e))

        await _connection_manager.close()
        _connection_manager = None
        _connection_manager_loop_id = None
        structlog_logger.info("close_connections() completed")
