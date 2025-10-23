"""
Centralized connection management with pooling, circuit breakers, and monitoring.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import asyncpg
import redis.asyncio as redis
from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)


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
        self.neo4j_driver: AsyncGraphDatabase.driver | None = None
        self.redis_client: redis.Redis | None = None

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

    async def initialize(self):
        """Initialize all connection pools with proper error handling."""
        logger.info("=" * 60)
        logger.info("ConnectionManager.initialize() called")

        # Log event loop information
        try:
            loop = asyncio.get_running_loop()
            logger.info(f"Event loop: {loop}")
            logger.info(f"Event loop running: {loop.is_running()}")
            logger.info(f"Event loop closed: {loop.is_closed()}")
        except RuntimeError as e:
            logger.error(f"No running event loop! {e}")
            raise

        logger.info(f"Config keys: {list(self.config.keys())}")
        logger.info(f"Enable graph: {self.config.get('enable_graph', True)}")
        logger.info(f"Enable redis: {self.config.get('enable_redis_cache', False)}")

        initialization_tasks = [
            self._init_postgresql(),
            self._init_neo4j() if self.config.get("enable_graph", True) else None,
            self._init_redis() if self.config.get("enable_redis_cache") else None,
        ]

        tasks_to_run = [t for t in initialization_tasks if t]
        logger.info(f"Running {len(tasks_to_run)} initialization tasks")

        results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service = ["PostgreSQL", "Neo4j", "Redis"][i]
                logger.error(f"Failed to initialize {service}: {result}")
                logger.error(f"Exception type: {type(result).__name__}")
                logger.error(f"Exception args: {result.args}")
                if i < 2:  # PostgreSQL and Neo4j are critical
                    raise result

        logger.info("ConnectionManager.initialize() completed successfully")
        logger.info("=" * 60)

    async def _init_postgresql(self):
        """Initialize PostgreSQL connection pool with optimized settings."""
        logger.info(">>> _init_postgresql() starting")
        logger.info(f"Database URL (masked): {self.config['database_url'][:30]}...")
        logger.info(f"Pool min_size: {self.config.get('pg_pool_min', 5)}")
        logger.info(f"Pool max_size: {self.config.get('pg_pool_max', 20)}")

        try:
            # Check event loop again right before pool creation
            loop = asyncio.get_running_loop()
            logger.info(f"Event loop before pool creation: {loop}")
            logger.info(f"Event loop ID: {id(loop)}")
            logger.info(f"Event loop is running: {loop.is_running()}")
            logger.info(f"Event loop is closed: {loop.is_closed()}")

            # Check if pool already exists
            if self.pg_pool is not None:
                logger.warning(f"PostgreSQL pool already exists! {self.pg_pool}")
                logger.warning(f"Pool is closed: {self.pg_pool._closed}")
                return

            logger.info("Calling asyncpg.create_pool()...")

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

            logger.info(f"asyncpg.create_pool() returned: {self.pg_pool}")
            logger.info(f"Pool type: {type(self.pg_pool)}")
            logger.info(f"Pool closed: {self.pg_pool._closed}")

            self.pg_state = ConnectionState.CLOSED  # CLOSED = healthy/normal operation
            self.pg_metrics.total_connections = self.pg_pool.get_size()
            logger.info(
                f"✅ PostgreSQL pool initialized with {self.pg_metrics.total_connections} connections"
            )

        except Exception as e:
            logger.error("❌ PostgreSQL initialization FAILED")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception message: {e!s}")
            logger.error(f"Exception args: {e.args}")

            # Try to get more details about the error
            import traceback

            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            self.pg_state = ConnectionState.OPEN  # OPEN = broken/failure state
            self.pg_metrics.last_error = str(e)
            self.pg_metrics.last_error_time = datetime.now(UTC)
            raise

    async def _setup_postgres_connection(self, connection):
        """Setup function for each PostgreSQL connection."""
        logger.info(f">>> _setup_postgres_connection() called for {connection}")
        try:
            # Set connection-specific settings
            logger.info("Setting work_mem...")
            await connection.execute("SET work_mem = '50MB'")
            logger.info("Setting maintenance_work_mem...")
            await connection.execute("SET maintenance_work_mem = '256MB'")
            logger.info("✅ Setup complete")
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            raise

    async def _init_postgres_connection(self, connection):
        """Initialize function for new PostgreSQL connections."""
        logger.info(f">>> _init_postgres_connection() called for {connection}")
        # Prepare commonly used statements
        # NOTE: Commented out - schema uses embedding_1536/embedding_768 columns, not 'embedding'
        # await connection.execute(
        #     """
        #     PREPARE vector_search (vector, int) AS
        #     SELECT id, content, 1 - (embedding <=> $1) as similarity
        #     FROM chunks
        #     WHERE embedding IS NOT NULL
        #     ORDER BY embedding <=> $1
        #     LIMIT $2
        # """
        # )
        logger.info("✅ Init complete (no-op)")
        pass

    async def _init_neo4j(self):
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
            logger.info("Neo4j driver initialized successfully")

        except Exception as e:
            self.neo4j_state = ConnectionState.OPEN  # OPEN = broken/failure state
            self.neo4j_metrics.last_error = str(e)
            self.neo4j_metrics.last_error_time = datetime.now(UTC)
            raise

    async def _init_redis(self):
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

            logger.info("Redis client initialized successfully")

        except Exception as e:
            logger.warning(f"Redis initialization failed (non-critical): {e}")
            self.redis_metrics.last_error = str(e)
            self.redis_metrics.last_error_time = datetime.now(UTC)

    @asynccontextmanager
    async def get_pg_connection(self):
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
                logger.info("PostgreSQL circuit breaker CLOSED (healthy) - connection recovered")

        except Exception as e:
            self._record_failure("pg", e)
            raise

        finally:
            self.pg_metrics.active_connections -= 1
            elapsed_ms = (loop.time() - start_time) * 1000
            self._update_query_metrics("pg", elapsed_ms)

    @asynccontextmanager
    async def get_neo4j_session(self, database: str | None = None):
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
                logger.info("Neo4j circuit breaker CLOSED (healthy) - connection recovered")

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
                    logger.info(
                        "PostgreSQL circuit breaker entering HALF_OPEN state for recovery test"
                    )
                else:
                    self.neo4j_state = ConnectionState.HALF_OPEN
                    logger.info("Neo4j circuit breaker entering HALF_OPEN state for recovery test")
                return True
            # Still broken, block request
            return False

        # HALF_OPEN state - allow requests to test recovery
        return True

    def _record_failure(self, service: str, error: Exception):
        """Record connection failure for circuit breaker."""
        if service == "pg":
            self.pg_failures += 1
            self.pg_metrics.failed_connections += 1
            self.pg_metrics.last_error = str(error)
            self.pg_metrics.last_error_time = datetime.now(UTC)

            if self.pg_failures >= self.circuit_config.failure_threshold:
                self.pg_state = ConnectionState.OPEN  # OPEN = broken/failure state
                self.pg_last_failure_time = datetime.now(UTC)
                logger.error(
                    f"PostgreSQL circuit breaker OPEN (blocking requests) after {self.pg_failures} failures. "
                    f"Last error: {str(error)[:100]}"
                )

        else:
            self.neo4j_failures += 1
            self.neo4j_metrics.failed_connections += 1
            self.neo4j_metrics.last_error = str(error)
            self.neo4j_metrics.last_error_time = datetime.now(UTC)

            if self.neo4j_failures >= self.circuit_config.failure_threshold:
                self.neo4j_state = ConnectionState.OPEN  # OPEN = broken/failure state
                self.neo4j_last_failure_time = datetime.now(UTC)
                logger.error(
                    f"Neo4j circuit breaker OPEN (blocking requests) after {self.neo4j_failures} failures. "
                    f"Last error: {str(error)[:100]}"
                )

    def _update_query_metrics(self, service: str, elapsed_ms: float):
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

    async def get_redis(self) -> redis.Redis | None:
        """Get Redis client if available."""
        return self.redis_client

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on all connections."""
        health = {"timestamp": datetime.now(UTC).isoformat(), "services": {}}

        # PostgreSQL health check
        pg_healthy = False
        try:
            async with self.get_pg_connection() as conn:
                await conn.fetchval("SELECT 1")
                pg_healthy = True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")

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
            logger.error(f"Neo4j health check failed: {e}")

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
                logger.warning(f"Redis health check failed: {e}")

        health["services"]["redis"] = {
            "healthy": redis_healthy,
            "enabled": self.redis_client is not None,
        }

        health["overall_health"] = "healthy" if (pg_healthy and neo4j_healthy) else "degraded"

        return health

    async def close(self):
        """Close all connections gracefully."""
        logger.info("=" * 60)
        logger.info(">>> ConnectionManager.close() called")
        logger.info(f"ConnectionManager instance ID: {id(self)}")

        # Log stack trace to see who called close()
        import traceback

        logger.info(f"Close called from:\n{''.join(traceback.format_stack())}")

        close_tasks = []

        if self.pg_pool:
            logger.info(f"Closing PostgreSQL pool: {self.pg_pool}")
            logger.info(f"Pool already closed: {self.pg_pool._closed}")
            close_tasks.append(self.pg_pool.close())

        if self.neo4j_driver:
            logger.info(f"Closing Neo4j driver: {self.neo4j_driver}")
            close_tasks.append(self.neo4j_driver.close())

        if self.redis_client:
            logger.info(f"Closing Redis client: {self.redis_client}")
            close_tasks.append(self.redis_client.aclose())

        logger.info(f"Running {len(close_tasks)} close tasks")
        await asyncio.gather(*close_tasks, return_exceptions=True)
        logger.info("✅ All connections closed")
        logger.info("=" * 60)

    async def __aenter__(self):
        """Async context manager entry - initialize connections."""
        logger.info(">>> ConnectionManager.__aenter__() called")
        logger.info(f"Instance ID: {id(self)}")
        await self.initialize()
        logger.info("<<< ConnectionManager.__aenter__() returning self")
        return self

    async def __aexit__(self, exc_type, exc_val, _exc_tb):
        """Async context manager exit - close connections."""
        logger.info(">>> ConnectionManager.__aexit__() called")
        logger.info(f"Instance ID: {id(self)}")
        logger.info(f"Exception: {exc_type}, {exc_val}")
        await self.close()
        logger.info("<<< ConnectionManager.__aexit__() done")
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
        logger.info(">>> get_connection_manager() called (inside lock)")
        logger.info(f"_connection_manager is None: {_connection_manager is None}")

        # Check if event loop has changed (Streamlit reruns create new event loops)
        try:
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
            loop_changed = (
                _connection_manager_loop_id is not None
                and _connection_manager_loop_id != current_loop_id
            )

            if loop_changed:
                logger.warning(
                    f"Event loop changed (Streamlit rerun detected)! "
                    f"Old: {_connection_manager_loop_id}, New: {current_loop_id}"
                )
                logger.info("Closing old connection manager and creating new one...")
                if _connection_manager is not None:
                    try:
                        await _connection_manager.close()
                    except Exception as e:
                        logger.warning(f"Error closing old connection manager: {e}")
                    _connection_manager = None
                    _connection_manager_loop_id = None

        except RuntimeError:
            logger.warning("No running event loop found")
            current_loop_id = None

        if _connection_manager is not None:
            logger.info(f"Returning existing connection manager: {id(_connection_manager)}")
            logger.info(f"Existing PG pool: {_connection_manager.pg_pool}")
            if _connection_manager.pg_pool:
                logger.info(f"Existing pool closed: {_connection_manager.pg_pool._closed}")
            return _connection_manager

        logger.info("Creating NEW connection manager")

        from src.agentic_rag.config import config  # Import config when needed

        temp_connection_manager = ConnectionManager(config.dict())
        logger.info(f"ConnectionManager instance created: {id(temp_connection_manager)}")

        try:
            logger.info("Calling initialize()...")
            await temp_connection_manager.initialize()
            logger.info("initialize() completed")

            # Initialize analytics logger after connection manager is ready
            try:
                from src.agentic_rag.analytics import initialize_analytics_logger

                await initialize_analytics_logger(temp_connection_manager)
                logger.info("Analytics logger initialized successfully")
            except Exception as e:
                logger.warning(f"Analytics logger initialization failed (non-critical): {e}")

            # Only set global singleton if initialization succeeded
            _connection_manager = temp_connection_manager
            _connection_manager_loop_id = current_loop_id  # Store current loop ID
            logger.info(f"Returning NEW connection manager: {id(_connection_manager)}")
            logger.info(f"Stored event loop ID: {_connection_manager_loop_id}")
            return _connection_manager

        except Exception as e:
            logger.error(
                f"Failed to initialize ConnectionManager: {e}. " f"Will retry on next call."
            )
            # Don't set _connection_manager - leave it None so next call will retry
            raise


async def close_connections():
    """Close all connections."""
    global _connection_manager, _connection_manager_loop_id

    if _connection_manager:
        # Shutdown analytics logger first
        try:
            from src.agentic_rag.analytics import shutdown_analytics_logger

            await shutdown_analytics_logger()
            logger.info("Analytics logger shutdown successfully")
        except Exception as e:
            logger.warning(f"Analytics logger shutdown failed: {e}")

        await _connection_manager.close()
        _connection_manager = None
        _connection_manager_loop_id = None
