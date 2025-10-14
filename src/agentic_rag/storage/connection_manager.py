"""
Centralized connection management with pooling, circuit breakers, and monitoring.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
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
        initialization_tasks = [
            self._init_postgresql(),
            self._init_neo4j() if self.config.get("enable_graph", True) else None,
            self._init_redis() if self.config.get("enable_redis_cache") else None,
        ]

        results = await asyncio.gather(
            *[t for t in initialization_tasks if t], return_exceptions=True
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service = ["PostgreSQL", "Neo4j", "Redis"][i]
                logger.error(f"Failed to initialize {service}: {result}")
                if i < 2:  # PostgreSQL and Neo4j are critical
                    raise result

    async def _init_postgresql(self):
        """Initialize PostgreSQL connection pool with optimized settings."""
        try:
            # Get current event loop to bind the pool to
            import asyncio

            loop = asyncio.get_running_loop()

            self.pg_pool = await asyncpg.create_pool(
                dsn=self.config["database_url"],
                min_size=self.config.get("pg_pool_min", 5),
                max_size=self.config.get("pg_pool_max", 20),
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=60,
                setup=self._setup_postgres_connection,
                init=self._init_postgres_connection,
                server_settings={
                    "jit": "off",  # Disable JIT for consistent performance
                    "search_path": "public",
                    "statement_timeout": "30s",
                    "lock_timeout": "10s",
                    "idle_in_transaction_session_timeout": "60s",
                },
                loop=loop,  # Explicitly bind to current event loop
            )

            self.pg_state = ConnectionState.OPEN
            self.pg_metrics.total_connections = self.pg_pool.get_size()
            logger.info(
                f"PostgreSQL pool initialized with {self.pg_metrics.total_connections} connections"
            )

        except Exception as e:
            self.pg_state = ConnectionState.CLOSED
            self.pg_metrics.last_error = str(e)
            self.pg_metrics.last_error_time = datetime.utcnow()
            raise

    async def _setup_postgres_connection(self, connection):
        """Setup function for each PostgreSQL connection."""
        # Set connection-specific settings
        await connection.execute("SET work_mem = '50MB'")
        await connection.execute("SET maintenance_work_mem = '256MB'")

    async def _init_postgres_connection(self, connection):
        """Initialize function for new PostgreSQL connections."""
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

            self.neo4j_state = ConnectionState.OPEN
            logger.info("Neo4j driver initialized successfully")

        except Exception as e:
            self.neo4j_state = ConnectionState.CLOSED
            self.neo4j_metrics.last_error = str(e)
            self.neo4j_metrics.last_error_time = datetime.utcnow()
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
            self.redis_metrics.last_error_time = datetime.utcnow()

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
                f"PostgreSQL circuit breaker is {self.pg_state.value}. "
                f"Last error: {self.pg_metrics.last_error}"
            )

        start_time = asyncio.get_event_loop().time()

        try:
            async with self.pg_pool.acquire() as conn:
                self.pg_metrics.active_connections += 1
                yield conn

            # Reset failure count on success
            if self.pg_state == ConnectionState.HALF_OPEN:
                self.pg_failures = 0
                self.pg_state = ConnectionState.OPEN
                logger.info("PostgreSQL circuit breaker closed - connection recovered")

        except Exception as e:
            self._record_failure("pg", e)
            raise

        finally:
            self.pg_metrics.active_connections -= 1
            elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
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
                f"Neo4j circuit breaker is {self.neo4j_state.value}. "
                f"Last error: {self.neo4j_metrics.last_error}"
            )

        start_time = asyncio.get_event_loop().time()

        try:
            async with self.neo4j_driver.session(database=database) as session:
                self.neo4j_metrics.active_connections += 1
                yield session

            # Reset failure count on success
            if self.neo4j_state == ConnectionState.HALF_OPEN:
                self.neo4j_failures = 0
                self.neo4j_state = ConnectionState.OPEN
                logger.info("Neo4j circuit breaker closed - connection recovered")

        except Exception as e:
            self._record_failure("neo4j", e)
            raise

        finally:
            self.neo4j_metrics.active_connections -= 1
            elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self._update_query_metrics("neo4j", elapsed_ms)

    def _check_circuit_breaker(self, service: str) -> bool:
        """Check if circuit breaker allows request."""
        if service == "pg":
            state = self.pg_state
            last_failure = self.pg_last_failure_time
        else:
            state = self.neo4j_state
            last_failure = self.neo4j_last_failure_time

        if state == ConnectionState.OPEN:
            return True

        if state == ConnectionState.CLOSED:
            if (
                last_failure
                and datetime.utcnow() - last_failure > self.circuit_config.recovery_timeout
            ):
                # Try half-open state
                if service == "pg":
                    self.pg_state = ConnectionState.HALF_OPEN
                else:
                    self.neo4j_state = ConnectionState.HALF_OPEN
                return True
            return False

        # HALF_OPEN state
        return True

    def _record_failure(self, service: str, error: Exception):
        """Record connection failure for circuit breaker."""
        if service == "pg":
            self.pg_failures += 1
            self.pg_metrics.failed_connections += 1
            self.pg_metrics.last_error = str(error)
            self.pg_metrics.last_error_time = datetime.utcnow()

            if self.pg_failures >= self.circuit_config.failure_threshold:
                self.pg_state = ConnectionState.CLOSED
                self.pg_last_failure_time = datetime.utcnow()
                logger.error(f"PostgreSQL circuit breaker opened after {self.pg_failures} failures")

        else:
            self.neo4j_failures += 1
            self.neo4j_metrics.failed_connections += 1
            self.neo4j_metrics.last_error = str(error)
            self.neo4j_metrics.last_error_time = datetime.utcnow()

            if self.neo4j_failures >= self.circuit_config.failure_threshold:
                self.neo4j_state = ConnectionState.CLOSED
                self.neo4j_last_failure_time = datetime.utcnow()
                logger.error(f"Neo4j circuit breaker opened after {self.neo4j_failures} failures")

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
        health = {"timestamp": datetime.utcnow().isoformat(), "services": {}}

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
        close_tasks = []

        if self.pg_pool:
            close_tasks.append(self.pg_pool.close())

        if self.neo4j_driver:
            close_tasks.append(self.neo4j_driver.close())

        if self.redis_client:
            close_tasks.append(self.redis_client.close())

        await asyncio.gather(*close_tasks, return_exceptions=True)
        logger.info("All connections closed")

    async def __aenter__(self):
        """Async context manager entry - initialize connections."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close connections."""
        await self.close()
        return False  # Don't suppress exceptions


# Global connection manager instance
_connection_manager: ConnectionManager | None = None


async def get_connection_manager() -> ConnectionManager:
    """Get or create the global connection manager."""
    global _connection_manager

    if _connection_manager is None:
        from src.agentic_rag.config import config  # Import config when needed

        _connection_manager = ConnectionManager(config.dict())
        await _connection_manager.initialize()

    return _connection_manager


async def close_connections():
    """Close all connections."""
    global _connection_manager

    if _connection_manager:
        await _connection_manager.close()
        _connection_manager = None
