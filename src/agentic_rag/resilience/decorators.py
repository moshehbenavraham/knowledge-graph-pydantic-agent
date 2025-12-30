"""
Resilience decorators for async operations.

Provides retry and circuit breaker decorators for wrapping async functions
with automatic error handling and recovery.
"""

import asyncio
import functools
import random
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import structlog

from .circuit_breaker import CircuitBreaker, get_circuit_breaker
from .error_types import (
    ErrorCategory,
    MaxRetriesExceededError,
    ServiceType,
    categorize_exception,
)

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def calculate_backoff_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    jitter: bool = True,
) -> float:
    """
    Calculate delay for exponential backoff.

    Uses exponential backoff with optional jitter to prevent thundering herd.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds to wait before next attempt
    """
    # Exponential backoff: base_delay * 2^attempt
    delay = base_delay * (2**attempt)

    # Cap at max delay
    delay = min(delay, max_delay)

    # Add jitter (0-50% of delay)
    if jitter:
        jitter_amount = delay * 0.5 * random.random()  # nosec B311 - Not used for security
        delay = delay + jitter_amount

    return float(delay)


def with_retry(
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
    retriable_exceptions: tuple[type[Exception], ...] | None = None,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for async functions with retry logic.

    Implements exponential backoff with jitter for transient failures.

    Args:
        max_attempts: Maximum retry attempts (default from settings)
        base_delay: Base delay for backoff in seconds (default from settings)
        max_delay: Maximum delay between retries (default from settings)
        retriable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called before each retry (attempt, error)

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(max_attempts=3, base_delay=1.0)
        async def fetch_data():
            return await external_api.get()
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Import settings here to avoid circular imports
            from src.config import get_settings

            settings = get_settings()

            _max_attempts = (
                max_attempts if max_attempts is not None else settings.retry_max_attempts
            )
            _base_delay = (
                base_delay if base_delay is not None else settings.retry_base_delay_seconds
            )
            _max_delay = max_delay if max_delay is not None else settings.retry_max_delay_seconds

            last_exception: Exception | None = None
            operation = func.__name__

            for attempt in range(_max_attempts):
                try:
                    return await func(*args, **kwargs)  # type: ignore[misc,no-any-return]
                except Exception as e:
                    last_exception = e

                    # Check if exception is retriable
                    if retriable_exceptions is not None:
                        if not isinstance(e, retriable_exceptions):
                            logger.warning(
                                "Non-retriable exception, not retrying",
                                operation=operation,
                                attempt=attempt + 1,
                                error_type=type(e).__name__,
                                error=str(e),
                            )
                            raise

                    # Categorize exception to check if retriable
                    error_context = categorize_exception(e, operation=operation)
                    if not error_context.is_retriable:
                        if error_context.category == ErrorCategory.FATAL:
                            logger.warning(
                                "Fatal error, not retrying",
                                operation=operation,
                                attempt=attempt + 1,
                                error_type=type(e).__name__,
                                error=str(e),
                            )
                            raise

                    # Last attempt - don't retry
                    if attempt == _max_attempts - 1:
                        logger.error(
                            "Max retries exceeded",
                            operation=operation,
                            max_attempts=_max_attempts,
                            error_type=type(e).__name__,
                            error=str(e),
                        )
                        raise MaxRetriesExceededError(
                            operation=operation,
                            max_attempts=_max_attempts,
                            last_error=e,
                        ) from e

                    # Calculate delay and wait
                    delay = calculate_backoff_delay(attempt, _base_delay, _max_delay)

                    logger.info(
                        "Retrying after error",
                        operation=operation,
                        attempt=attempt + 1,
                        max_attempts=_max_attempts,
                        delay_seconds=round(delay, 2),
                        error_type=type(e).__name__,
                        error=str(e),
                    )

                    # Call retry callback if provided
                    if on_retry is not None:
                        on_retry(attempt + 1, e)

                    # Wait before retry (async!)
                    await asyncio.sleep(delay)

            # Should not reach here, but just in case
            if last_exception is not None:
                raise MaxRetriesExceededError(
                    operation=operation,
                    max_attempts=_max_attempts,
                    last_error=last_exception,
                )
            raise RuntimeError(f"Unexpected state in retry decorator for {operation}")

        return wrapper  # type: ignore[return-value]

    return decorator


def with_circuit_breaker(
    service: ServiceType,
    failure_threshold: int | None = None,
    recovery_timeout: int | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for async functions with circuit breaker protection.

    Wraps the function with circuit breaker logic that:
    - Allows requests when circuit is closed
    - Rejects requests when circuit is open
    - Tests recovery when circuit is half-open

    Args:
        service: The external service being protected
        failure_threshold: Override default failure threshold
        recovery_timeout: Override default recovery timeout

    Returns:
        Decorated function with circuit breaker protection

    Example:
        @with_circuit_breaker(ServiceType.NEO4J)
        async def query_graph():
            return await neo4j.run(query)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Get or create circuit breaker for this service
        breaker: CircuitBreaker | None = None

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal breaker

            # Lazy initialization of circuit breaker
            if breaker is None:
                breaker = get_circuit_breaker(service)

            return await breaker.execute(func, *args, **kwargs)  # type: ignore[no-any-return]

        return wrapper  # type: ignore[return-value]

    return decorator


def with_resilience(
    service: ServiceType,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
    failure_threshold: int | None = None,
    recovery_timeout: int | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Combined decorator for retry + circuit breaker protection.

    Applies both retry logic and circuit breaker in the correct order:
    1. Circuit breaker checks if request can proceed
    2. If allowed, executes with retry logic
    3. Records success/failure in circuit breaker

    Args:
        service: The external service being protected
        max_attempts: Maximum retry attempts
        base_delay: Base delay for backoff in seconds
        max_delay: Maximum delay between retries
        failure_threshold: Circuit breaker failure threshold
        recovery_timeout: Circuit breaker recovery timeout

    Returns:
        Decorated function with full resilience protection

    Example:
        @with_resilience(ServiceType.NEO4J, max_attempts=3)
        async def query_graph():
            return await neo4j.run(query)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        breaker: CircuitBreaker | None = None

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal breaker

            # Import settings here to avoid circular imports
            from src.config import get_settings

            settings = get_settings()

            # Lazy initialization of circuit breaker
            if breaker is None:
                from .circuit_breaker import get_circuit_breaker_registry

                registry = get_circuit_breaker_registry()
                breaker = registry.get_breaker(
                    service,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                )

            # Check circuit breaker first
            if not await breaker.can_execute():
                from .error_types import CircuitOpenError

                time_remaining = breaker.recovery_timeout - breaker._time_since_last_failure()
                raise CircuitOpenError(
                    service=service,
                    recovery_time_seconds=max(0, time_remaining),
                )

            # Get retry settings
            _max_attempts = (
                max_attempts if max_attempts is not None else settings.retry_max_attempts
            )
            _base_delay = (
                base_delay if base_delay is not None else settings.retry_base_delay_seconds
            )
            _max_delay = max_delay if max_delay is not None else settings.retry_max_delay_seconds

            last_exception: Exception | None = None
            operation = func.__name__

            for attempt in range(_max_attempts):
                try:
                    result = await func(*args, **kwargs)  # type: ignore[misc]
                    await breaker.record_success()
                    return result  # type: ignore[no-any-return]
                except Exception as e:
                    last_exception = e

                    # Categorize exception
                    error_context = categorize_exception(e, service=service, operation=operation)

                    # Record failure in circuit breaker
                    await breaker.record_failure(e)

                    # Check if circuit just opened
                    if breaker.is_open:
                        logger.warning(
                            "Circuit breaker opened, stopping retries",
                            service=service.value,
                            operation=operation,
                            error=str(e),
                        )
                        raise

                    # Non-retriable errors - don't retry
                    if not error_context.is_retriable:
                        raise

                    # Last attempt - don't retry
                    if attempt == _max_attempts - 1:
                        raise MaxRetriesExceededError(
                            operation=operation,
                            max_attempts=_max_attempts,
                            last_error=e,
                        ) from e

                    # Calculate delay and wait
                    delay = calculate_backoff_delay(attempt, _base_delay, _max_delay)

                    logger.info(
                        "Retrying after error",
                        operation=operation,
                        service=service.value,
                        attempt=attempt + 1,
                        max_attempts=_max_attempts,
                        delay_seconds=round(delay, 2),
                        error_type=type(e).__name__,
                    )

                    await asyncio.sleep(delay)

            # Should not reach here
            if last_exception is not None:
                raise MaxRetriesExceededError(
                    operation=operation,
                    max_attempts=_max_attempts,
                    last_error=last_exception,
                )
            raise RuntimeError(f"Unexpected state in resilience decorator for {operation}")

        return wrapper  # type: ignore[return-value]

    return decorator
