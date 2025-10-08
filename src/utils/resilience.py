"""
Resilience utilities for fault tolerance.

Implements circuit breaker pattern and retry logic with exponential backoff.
"""

import asyncio
import time
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any

import structlog

logger = structlog.get_logger()


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by failing fast when service is degraded.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: tuple = (Exception,),
        name: str | None = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            expected_exceptions: Exceptions that trigger circuit
            name: Optional circuit name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        self.name = name or "unnamed"

        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        # Check if circuit should transition to half-open
        if self._state == CircuitState.OPEN:
            if (
                self._last_failure_time
                and time.time() - self._last_failure_time >= self.recovery_timeout
            ):
                logger.info(
                    "circuit_breaker_half_open",
                    circuit=self.name,
                )
                self._state = CircuitState.HALF_OPEN

        return self._state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            logger.warning(
                "circuit_breaker_rejected",
                circuit=self.name,
                failure_count=self._failure_count,
            )
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exceptions:
            self._on_failure()
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            logger.warning(
                "circuit_breaker_rejected",
                circuit=self.name,
                failure_count=self._failure_count,
            )
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exceptions:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info(
                "circuit_breaker_recovered",
                circuit=self.name,
            )

        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed execution."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            logger.error(
                "circuit_breaker_opened",
                circuit=self.name,
                failure_count=self._failure_count,
            )
            self._state = CircuitState.OPEN

    def reset(self):
        """Manually reset circuit breaker."""
        logger.info("circuit_breaker_reset", circuit=self.name)
        self._failure_count = 0
        self._last_failure_time = None
        self._state = CircuitState.CLOSED


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exceptions: tuple = (Exception,),
    name: str | None = None,
):
    """
    Circuit breaker decorator.

    Usage:
        @circuit_breaker(failure_threshold=3, name="llm_api")
        async def call_llm():
            ...
    """
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exceptions=expected_exceptions,
        name=name,
    )

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call_async(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class RetryStrategy:
    """
    Retry strategy with exponential backoff.

    Automatically retries failed operations with increasing delays.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retriable_exceptions: tuple = (Exception,),
    ):
        """
        Initialize retry strategy.

        Args:
            max_attempts: Maximum retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Multiplier for exponential backoff
            jitter: Add random jitter to delays
            retriable_exceptions: Exceptions that trigger retry
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retriable_exceptions = retriable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)

        if self.jitter:
            import random

            delay *= 0.5 + random.random()

        return delay

    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with retry logic.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(
                        "retry_succeeded",
                        function=func.__name__,
                        attempt=attempt + 1,
                    )
                return result

            except self.retriable_exceptions as e:
                last_exception = e

                if attempt < self.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=self.max_attempts,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "retry_exhausted",
                        function=func.__name__,
                        attempts=self.max_attempts,
                        error=str(e),
                    )

        raise last_exception

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic (synchronous).

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(
                        "retry_succeeded",
                        function=func.__name__,
                        attempt=attempt + 1,
                    )
                return result

            except self.retriable_exceptions as e:
                last_exception = e

                if attempt < self.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=self.max_attempts,
                        delay=delay,
                        error=str(e),
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "retry_exhausted",
                        function=func.__name__,
                        attempts=self.max_attempts,
                        error=str(e),
                    )

        raise last_exception


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retriable_exceptions: tuple = (Exception,),
):
    """
    Retry decorator with exponential backoff.

    Usage:
        @retry(max_attempts=3, base_delay=1.0)
        async def unstable_operation():
            ...
    """
    strategy = RetryStrategy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retriable_exceptions=retriable_exceptions,
    )

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await strategy.execute_async(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return strategy.execute(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Convenience decorators for common patterns
def retry_on_network_error(max_attempts: int = 3):
    """Retry decorator for network-related errors."""
    import aiohttp

    return retry(
        max_attempts=max_attempts,
        base_delay=1.0,
        retriable_exceptions=(
            aiohttp.ClientError,
            TimeoutError,
            ConnectionError,
        ),
    )


def retry_on_database_error(max_attempts: int = 3):
    """Retry decorator for database-related errors."""
    return retry(
        max_attempts=max_attempts,
        base_delay=0.5,
        retriable_exceptions=(
            ConnectionError,
            TimeoutError,
        ),
    )
