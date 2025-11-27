"""Performance monitoring and logging utilities for the AI agent system."""

import asyncio
import functools
import logging
import time
from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, ParamSpec, TypeVar

import structlog

P = ParamSpec("P")
T = TypeVar("T")
from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

from src.config import get_settings

try:
    import psutil
except ImportError:
    psutil = None


# Configure structured logging
def configure_logging() -> structlog.stdlib.BoundLogger:
    """Configure structured logging with JSON output."""
    # Note: We use basic print here since logger is not yet initialized
    print("Configuring structured logging...")

    settings = get_settings()
    log_level = settings.log_level.upper()

    print(f"Setting log level to: {log_level}")

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set log level
    logging.basicConfig(level=getattr(logging, log_level))

    logger = structlog.get_logger()
    logger.info("Structured logging configured successfully", log_level=log_level)

    return logger


# Initialize logger
logger = configure_logging()


def _get_or_create_metric(
    metric_class: type[Counter] | type[Gauge] | type[Histogram],
    name: str,
    description: str,
    labelnames: list[str] | None = None,
    buckets: list[float] | None = None,
    registry: Any = REGISTRY,
) -> Any:
    """Get existing metric or create new one to avoid duplicates.

    This function is essential for Streamlit compatibility where module reloading
    would otherwise cause Prometheus metric re-registration errors.
    """
    # First, comprehensively check if the metric already exists
    try:
        # Method 1: Check _collector_to_names registry
        for collector in list(registry._collector_to_names.keys()):
            collector_name = getattr(collector, "_name", None)
            if collector_name == name:
                return collector

        # Method 2: Check _names_to_collectors registry (reverse lookup)
        if hasattr(registry, "_names_to_collectors"):
            for registered_name, collector in registry._names_to_collectors.items():
                if registered_name == name:
                    return collector
    except (AttributeError, KeyError, RuntimeError) as e:
        # Registry might be changing during iteration, continue to creation
        logger.debug(f"Error checking for existing metric {name}: {e}")

    # Create new metric
    kwargs = {"name": name, "documentation": description, "registry": registry}
    if labelnames:
        kwargs["labelnames"] = labelnames
    if buckets and metric_class == Histogram:
        kwargs["buckets"] = buckets

    try:
        return metric_class(**kwargs)
    except ValueError as e:
        # Metric already exists - this is the Streamlit reload scenario
        error_msg = str(e)
        if "Duplicated" in error_msg:
            # Try one more time to find it with a more thorough search
            for collector in list(registry._collector_to_names.keys()):
                # Check all possible name attributes
                for attr in ["_name", "name", "_metric_name"]:
                    collector_name = getattr(collector, attr, None)
                    if collector_name == name:
                        return collector

            # If still not found, this is likely a partial registration issue
            # Return None and let calling code handle it gracefully
            logger.error(
                f"Metric '{name}' collision detected but cannot retrieve existing instance. "
                f"Error: {error_msg}"
            )
            # Rather than crash, we'll re-raise with a more helpful message
            raise RuntimeError(
                f"Prometheus metric '{name}' registration conflict. "
                f"This usually happens during Streamlit hot-reload. "
                f"Try restarting the Streamlit server completely. Original error: {error_msg}"
            ) from e
        # Re-raise other ValueErrors
        raise


# Prometheus metrics
REQUEST_COUNT = _get_or_create_metric(
    Counter,
    "luminari_requests_total",
    "Total requests",
    ["method", "endpoint", "status", "user_id"],
)

REQUEST_DURATION = _get_or_create_metric(
    Histogram,
    "luminari_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint", "user_id"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

TOOL_EXECUTION_COUNT = _get_or_create_metric(
    Counter,
    "luminari_tool_executions_total",
    "Total tool executions",
    ["tool_name", "status", "user_id"],
)

TOOL_EXECUTION_DURATION = _get_or_create_metric(
    Histogram,
    "luminari_tool_execution_duration_seconds",
    "Tool execution duration in seconds",
    ["tool_name", "user_id"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

LLM_TOKEN_COUNT = _get_or_create_metric(
    Counter,
    "luminari_llm_tokens_total",
    "Total LLM tokens used",
    ["model", "type", "user_id"],
)

DATABASE_QUERY_COUNT = _get_or_create_metric(
    Counter,
    "luminari_database_queries_total",
    "Total database queries",
    ["operation", "table", "status"],
)

DATABASE_QUERY_DURATION = _get_or_create_metric(
    Histogram,
    "luminari_database_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0],
)

MEMORY_USAGE = _get_or_create_metric(
    Gauge, "luminari_memory_usage_bytes", "Current memory usage in bytes"
)

ACTIVE_SESSIONS = _get_or_create_metric(
    Gauge, "luminari_active_sessions", "Number of active user sessions"
)

ERROR_COUNT = _get_or_create_metric(
    Counter, "luminari_errors_total", "Total errors", ["error_type", "component", "severity"]
)


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""

    def __init__(self) -> None:
        self.start_time = time.time()
        self.active_requests: dict[str, dict[str, Any]] = {}
        self.session_count = 0

    def start_metrics_server(self, port: int = 8000) -> None:
        """Start Prometheus metrics server."""
        try:
            start_http_server(port)
            logger.info("Metrics server started", port=port)
        except Exception as e:
            logger.error("Failed to start metrics server", error=str(e), port=port)

    @contextmanager
    def track_request(
        self, method: str, endpoint: str, user_id: str = "anonymous"
    ) -> Generator[None, None, None]:
        """Context manager to track request metrics."""
        start_time = time.time()
        request_id = f"{method}_{endpoint}_{user_id}_{start_time}"

        self.active_requests[request_id] = {
            "method": method,
            "endpoint": endpoint,
            "user_id": user_id,
            "start_time": start_time,
        }

        try:
            yield
            status = "success"
        except Exception as e:
            status = "error"
            ERROR_COUNT.labels(
                error_type=type(e).__name__, component="request", severity="error"
            ).inc()
            raise
        finally:
            duration = time.time() - start_time

            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint, status=status, user_id=user_id
            ).inc()

            REQUEST_DURATION.labels(method=method, endpoint=endpoint, user_id=user_id).observe(
                duration
            )

            self.active_requests.pop(request_id, None)

            logger.info(
                "Request completed",
                method=method,
                endpoint=endpoint,
                user_id=user_id,
                duration=duration,
                status=status,
            )

    @asynccontextmanager
    async def track_tool_execution(
        self, tool_name: str, user_id: str = "anonymous"
    ) -> AsyncGenerator[None, None]:
        """Context manager to track tool execution metrics."""
        start_time = time.time()

        try:
            yield
            status = "success"
        except Exception as e:
            status = "error"
            ERROR_COUNT.labels(
                error_type=type(e).__name__, component="tool", severity="error"
            ).inc()
            raise
        finally:
            duration = time.time() - start_time

            TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status=status, user_id=user_id).inc()

            TOOL_EXECUTION_DURATION.labels(tool_name=tool_name, user_id=user_id).observe(duration)

            logger.info(
                "Tool execution completed",
                tool_name=tool_name,
                user_id=user_id,
                duration=duration,
                status=status,
            )

    @contextmanager
    def track_database_query(self, operation: str, table: str) -> Generator[None, None, None]:
        """Context manager to track database query metrics."""
        start_time = time.time()

        try:
            yield
            status = "success"
        except Exception as e:
            status = "error"
            ERROR_COUNT.labels(
                error_type=type(e).__name__, component="database", severity="error"
            ).inc()
            raise
        finally:
            duration = time.time() - start_time

            DATABASE_QUERY_COUNT.labels(operation=operation, table=table, status=status).inc()

            DATABASE_QUERY_DURATION.labels(operation=operation, table=table).observe(duration)

            logger.debug(
                "Database query completed",
                operation=operation,
                table=table,
                duration=duration,
                status=status,
            )

    def track_llm_tokens(
        self, model: str, input_tokens: int, output_tokens: int, user_id: str = "anonymous"
    ) -> None:
        """Track LLM token usage."""
        LLM_TOKEN_COUNT.labels(model=model, type="input", user_id=user_id).inc(input_tokens)

        LLM_TOKEN_COUNT.labels(model=model, type="output", user_id=user_id).inc(output_tokens)

        logger.info(
            "LLM tokens tracked",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            user_id=user_id,
        )

    def update_session_count(self, count: int) -> None:
        """Update active session count."""
        ACTIVE_SESSIONS.set(count)
        self.session_count = count

    def get_system_stats(self) -> dict[str, Any]:
        """Get current system statistics."""
        logger.debug("Getting system statistics...")

        stats = {
            "uptime": time.time() - self.start_time,
            "active_requests": len(self.active_requests),
            "active_sessions": self.session_count,
        }

        logger.debug(
            "Basic stats collected",
            uptime=stats["uptime"],
            active_requests=stats["active_requests"],
            active_sessions=stats["active_sessions"],
        )

        if psutil:
            logger.debug("Collecting psutil system metrics...")
            try:
                stats.update(
                    {
                        "memory_usage": psutil.virtual_memory().used,
                        "cpu_percent": psutil.cpu_percent(),
                        "disk_usage": psutil.disk_usage("/").percent,
                    }
                )
                logger.debug(
                    "psutil metrics collected",
                    memory_usage=stats["memory_usage"],
                    cpu_percent=stats["cpu_percent"],
                    disk_usage=stats["disk_usage"],
                )
            except Exception as e:
                logger.exception("Failed to collect psutil metrics", error=str(e))
        else:
            logger.debug("psutil not available, skipping system metrics")

        # Update Prometheus gauge if available
        if "memory_usage" in stats:
            logger.debug("Updating Prometheus memory gauge", memory_usage=stats["memory_usage"])
            MEMORY_USAGE.set(stats["memory_usage"])

        logger.info(
            "System statistics retrieved",
            stat_count=len(stats),
            has_psutil_metrics=psutil is not None,
        )

        return stats


# Global monitor instance
monitor = PerformanceMonitor()


def track_performance(
    tool_name: str | None = None, endpoint: str | None = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to track function performance."""
    logger.debug("Creating performance tracking decorator", tool_name=tool_name, endpoint=endpoint)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        func_name = func.__name__
        is_async = asyncio.iscoroutinefunction(func)

        logger.debug(
            "Decorating function for performance tracking",
            function=func_name,
            is_async=is_async,
            tool_name=tool_name,
            endpoint=endpoint,
        )

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            name = tool_name or func.__name__
            user_id = str(kwargs.get("user_id", "anonymous"))

            logger.debug(
                "Starting async function execution tracking",
                function=func.__name__,
                tracked_name=name,
                user_id=user_id,
                has_endpoint=endpoint is not None,
                arg_count=len(args),
                kwarg_count=len(kwargs),
            )

            if endpoint:
                logger.debug(
                    "Tracking with request context", endpoint=endpoint, function=func.__name__
                )
                with monitor.track_request("CALL", endpoint, user_id):
                    async with monitor.track_tool_execution(name, user_id):
                        result = await func(*args, **kwargs)  # type: ignore[misc]
                        logger.debug(
                            "Async function execution completed with request tracking",
                            function=func.__name__,
                            user_id=user_id,
                        )
                        return result
            else:
                logger.debug("Tracking without request context", function=func.__name__)
                async with monitor.track_tool_execution(name, user_id):
                    result = await func(*args, **kwargs)  # type: ignore[misc]
                    logger.debug(
                        "Async function execution completed",
                        function=func.__name__,
                        user_id=user_id,
                    )
                    return result

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            name = tool_name or func.__name__
            user_id = str(kwargs.get("user_id", "anonymous"))

            logger.debug(
                "Starting sync function execution tracking",
                function=func.__name__,
                tracked_name=name,
                user_id=user_id,
                has_endpoint=endpoint is not None,
                arg_count=len(args),
                kwarg_count=len(kwargs),
            )

            if endpoint:
                logger.debug(
                    "Tracking sync function with request context",
                    endpoint=endpoint,
                    function=func.__name__,
                )
                with monitor.track_request("CALL", endpoint, user_id):
                    # For sync functions, we can't use async context manager
                    start_time = time.time()
                    status = "unknown"
                    try:
                        logger.debug("Executing sync function...", function=func.__name__)
                        result = func(*args, **kwargs)
                        status = "success"
                        logger.debug(
                            "Sync function executed successfully",
                            function=func.__name__,
                            duration=time.time() - start_time,
                        )
                        return result
                    except Exception as e:
                        status = "error"
                        logger.exception(
                            "Sync function execution failed",
                            function=func.__name__,
                            error=str(e),
                            error_type=type(e).__name__,
                            duration=time.time() - start_time,
                        )
                        ERROR_COUNT.labels(
                            error_type=type(e).__name__, component="tool", severity="error"
                        ).inc()
                        raise
                    finally:
                        duration = time.time() - start_time
                        TOOL_EXECUTION_COUNT.labels(
                            tool_name=name, status=status, user_id=user_id
                        ).inc()
                        TOOL_EXECUTION_DURATION.labels(tool_name=name, user_id=user_id).observe(
                            duration
                        )
                        logger.info(
                            "Sync function tracking completed",
                            function=func.__name__,
                            status=status,
                            duration=duration,
                            user_id=user_id,
                        )
            else:
                logger.debug(
                    "Tracking sync function without request context", function=func.__name__
                )
                start_time = time.time()
                try:
                    logger.debug("Executing sync function...", function=func.__name__)
                    result = func(*args, **kwargs)
                    status = "success"
                    logger.debug(
                        "Sync function executed successfully",
                        function=func.__name__,
                        duration=time.time() - start_time,
                    )
                    return result
                except Exception as e:
                    status = "error"
                    logger.exception(
                        "Sync function execution failed",
                        function=func.__name__,
                        error=str(e),
                        error_type=type(e).__name__,
                        duration=time.time() - start_time,
                    )
                    ERROR_COUNT.labels(
                        error_type=type(e).__name__, component="tool", severity="error"
                    ).inc()
                    raise
                finally:
                    duration = time.time() - start_time
                    TOOL_EXECUTION_COUNT.labels(
                        tool_name=name, status=status, user_id=user_id
                    ).inc()
                    TOOL_EXECUTION_DURATION.labels(tool_name=name, user_id=user_id).observe(
                        duration
                    )
                    logger.info(
                        "Sync function tracking completed",
                        function=func.__name__,
                        status=status,
                        duration=duration,
                        user_id=user_id,
                    )

        wrapper: Callable[P, T] = async_wrapper if is_async else sync_wrapper  # type: ignore[assignment]
        logger.debug(
            "Performance tracking decorator created",
            function=func_name,
            wrapper_type="async" if is_async else "sync",
        )
        return wrapper

    return decorator
