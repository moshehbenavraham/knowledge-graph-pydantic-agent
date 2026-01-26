"""
Development profiling decorators for bottleneck identification.

Provides lightweight decorators for timing async and sync functions
with minimal overhead (<1ms when disabled).
"""

import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class ProfileResult:
    """Result of a profiled function execution."""

    __slots__ = ("duration_ms", "duration_seconds", "error", "function_name", "success")

    def __init__(
        self,
        function_name: str,
        duration_seconds: float,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """
        Initialize profile result.

        Args:
            function_name: Name of the profiled function
            duration_seconds: Execution duration in seconds
            success: Whether execution was successful
            error: Error message if execution failed
        """
        self.function_name = function_name
        self.duration_seconds = duration_seconds
        self.duration_ms = duration_seconds * 1000
        self.success = success
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "function_name": self.function_name,
            "duration_seconds": round(self.duration_seconds, 6),
            "duration_ms": round(self.duration_ms, 3),
            "success": self.success,
            "error": self.error,
        }


def _check_profiling_enabled() -> bool:
    """Check if profiling is enabled via configuration."""
    try:
        settings = get_settings()
        return settings.profiling_enabled
    except Exception:
        return False


def profile_async(
    name: str | None = None,
    log_args: bool = False,
    log_result: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for profiling async functions with detailed timing.

    When profiling is disabled via configuration, this decorator has
    minimal overhead (<1ms) and passes through to the original function.

    Args:
        name: Optional custom name for logging (defaults to function name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result

    Returns:
        Decorated function with profiling

    Example:
        >>> @profile_async(name="vector_search")
        ... async def search(query: str) -> list[dict]:
        ...     return await perform_search(query)

        >>> @profile_async(log_args=True, log_result=True)
        ... async def detailed_search(query: str) -> dict:
        ...     return await search(query)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"profile_async can only be used with async functions. "
                f"'{func.__name__}' is not async. Use profile_sync instead."
            )

        func_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if not _check_profiling_enabled():
                return await func(*args, **kwargs)

            start_time = time.perf_counter()
            error_msg: str | None = None
            success = True

            try:
                # Log start with optional args
                log_data: dict[str, Any] = {"function": func_name}
                if log_args:
                    log_data["args_count"] = len(args)
                    log_data["kwargs_keys"] = list(kwargs.keys())

                logger.debug("Profiling async function start", **log_data)

                result = await func(*args, **kwargs)

                # Log result preview if requested
                if log_result:
                    result_preview = str(result)[:100] if result else "None"
                    logger.debug(
                        "Profiling async function result",
                        function=func_name,
                        result_preview=result_preview,
                    )

                return result

            except Exception as e:
                success = False
                error_msg = str(e)
                raise

            finally:
                duration = time.perf_counter() - start_time
                profile_result = ProfileResult(
                    function_name=func_name,
                    duration_seconds=duration,
                    success=success,
                    error=error_msg,
                )

                logger.info(
                    "Profiling async function complete",
                    function=func_name,
                    duration_ms=round(profile_result.duration_ms, 3),
                    success=success,
                    error=error_msg,
                )

        return wrapper  # type: ignore[return-value]

    return decorator


def profile_sync(
    name: str | None = None,
    log_args: bool = False,
    log_result: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for profiling synchronous functions with detailed timing.

    When profiling is disabled via configuration, this decorator has
    minimal overhead (<1ms) and passes through to the original function.

    Args:
        name: Optional custom name for logging (defaults to function name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result

    Returns:
        Decorated function with profiling

    Example:
        >>> @profile_sync(name="data_processing")
        ... def process_data(data: list) -> dict:
        ...     return {"count": len(data)}

        >>> @profile_sync(log_args=True)
        ... def compute(x: int, y: int) -> int:
        ...     return x + y
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"profile_sync can only be used with sync functions. "
                f"'{func.__name__}' is async. Use profile_async instead."
            )

        func_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if not _check_profiling_enabled():
                return func(*args, **kwargs)

            start_time = time.perf_counter()
            error_msg: str | None = None
            success = True

            try:
                # Log start with optional args
                log_data: dict[str, Any] = {"function": func_name}
                if log_args:
                    log_data["args_count"] = len(args)
                    log_data["kwargs_keys"] = list(kwargs.keys())

                logger.debug("Profiling sync function start", **log_data)

                result = func(*args, **kwargs)

                # Log result preview if requested
                if log_result:
                    result_preview = str(result)[:100] if result else "None"
                    logger.debug(
                        "Profiling sync function result",
                        function=func_name,
                        result_preview=result_preview,
                    )

                return result

            except Exception as e:
                success = False
                error_msg = str(e)
                raise

            finally:
                duration = time.perf_counter() - start_time
                profile_result = ProfileResult(
                    function_name=func_name,
                    duration_seconds=duration,
                    success=success,
                    error=error_msg,
                )

                logger.info(
                    "Profiling sync function complete",
                    function=func_name,
                    duration_ms=round(profile_result.duration_ms, 3),
                    success=success,
                    error=error_msg,
                )

        return wrapper

    return decorator


def profile(
    name: str | None = None,
    log_args: bool = False,
    log_result: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Universal profiling decorator that auto-detects async vs sync functions.

    Args:
        name: Optional custom name for logging (defaults to function name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result

    Returns:
        Decorated function with profiling

    Example:
        >>> @profile(name="any_function")
        ... def sync_func(x: int) -> int:
        ...     return x * 2

        >>> @profile()
        ... async def async_func(x: int) -> int:
        ...     return x * 2
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if asyncio.iscoroutinefunction(func):
            return profile_async(name=name, log_args=log_args, log_result=log_result)(func)  # type: ignore[arg-type]
        return profile_sync(name=name, log_args=log_args, log_result=log_result)(func)

    return decorator


class Profiler:
    """
    Context manager for manual profiling of code blocks.

    Useful for profiling arbitrary code sections rather than whole functions.

    Example:
        >>> with Profiler("database_query") as p:
        ...     result = execute_query(sql)
        >>> print(f"Query took {p.duration_ms:.2f}ms")
    """

    __slots__ = ("duration_ms", "duration_seconds", "error", "name", "start_time", "success")

    def __init__(self, name: str) -> None:
        """
        Initialize profiler context.

        Args:
            name: Name for the profiled code block
        """
        self.name = name
        self.start_time: float = 0.0
        self.duration_seconds: float = 0.0
        self.duration_ms: float = 0.0
        self.success = True
        self.error: str | None = None

    def __enter__(self) -> "Profiler":
        """Start timing."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Stop timing and log results."""
        self.duration_seconds = time.perf_counter() - self.start_time
        self.duration_ms = self.duration_seconds * 1000

        if exc_type is not None:
            self.success = False
            self.error = str(exc_val) if exc_val else exc_type.__name__

        if _check_profiling_enabled():
            logger.info(
                "Profiler block complete",
                block_name=self.name,
                duration_ms=round(self.duration_ms, 3),
                success=self.success,
                error=self.error,
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "duration_seconds": round(self.duration_seconds, 6),
            "duration_ms": round(self.duration_ms, 3),
            "success": self.success,
            "error": self.error,
        }
