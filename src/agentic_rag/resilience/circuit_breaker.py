"""
Circuit breaker implementation for external service protection.

Implements the circuit breaker pattern to prevent cascading failures
when external services (Neo4j, Supabase, embedding APIs) become unavailable.

State Machine:
    CLOSED -> (failures >= threshold) -> OPEN
    OPEN -> (timeout elapsed) -> HALF_OPEN
    HALF_OPEN -> (success) -> CLOSED
    HALF_OPEN -> (failure) -> OPEN
"""

import asyncio
import time
from enum import Enum
from typing import Any

import structlog

from .error_types import CircuitOpenError, ServiceType

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failing, requests are rejected immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for protecting external service calls.

    Tracks failures and opens the circuit when the failure threshold
    is exceeded, preventing further requests until recovery.

    Thread-safe for concurrent async operations.
    """

    def __init__(
        self,
        service: ServiceType,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_requests: int = 3,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            service: The service this circuit breaker protects
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before entering half-open state
            half_open_requests: Max requests allowed in half-open state
        """
        self.service = service
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests

        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._half_open_count = 0

        # Thread safety
        self._lock = asyncio.Lock()

        logger.info(
            "Circuit breaker initialized",
            service=service.value,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    def _time_since_last_failure(self) -> float:
        """Get seconds since last failure."""
        if self._last_failure_time is None:
            return float("inf")
        return time.monotonic() - self._last_failure_time

    def _should_attempt_recovery(self) -> bool:
        """Check if recovery timeout has elapsed."""
        return self._time_since_last_failure() >= self.recovery_timeout

    async def can_execute(self) -> bool:
        """
        Check if a request can be executed.

        Handles state transitions based on timeouts.

        Returns:
            True if request can proceed, False otherwise
        """
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    # Transition to half-open
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_count = 0
                    logger.info(
                        "Circuit breaker transitioning to half-open",
                        service=self.service.value,
                        time_in_open=self._time_since_last_failure(),
                    )
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_count < self.half_open_requests:
                    self._half_open_count += 1
                    return True
                return False

            return False

    async def record_success(self) -> None:
        """
        Record a successful request.

        In half-open state, this closes the circuit.
        In closed state, this resets the failure count.
        """
        async with self._lock:
            self._success_count += 1

            if self._state == CircuitState.HALF_OPEN:
                # Recovery successful, close the circuit
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_count = 0
                logger.info(
                    "Circuit breaker closed after successful recovery",
                    service=self.service.value,
                    success_count=self._success_count,
                )
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def record_failure(self, error: Exception | None = None) -> None:
        """
        Record a failed request.

        Args:
            error: The exception that caused the failure (for logging)
        """
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Recovery failed, open the circuit again
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker re-opened after half-open failure",
                    service=self.service.value,
                    error=str(error) if error else None,
                )
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    # Too many failures, open the circuit
                    self._state = CircuitState.OPEN
                    logger.error(
                        "Circuit breaker opened due to failures",
                        service=self.service.value,
                        failure_count=self._failure_count,
                        threshold=self.failure_threshold,
                        error=str(error) if error else None,
                    )

    async def execute(
        self,
        func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of the function call

        Raises:
            CircuitOpenError: If circuit is open and not accepting requests
            Exception: Any exception raised by the function
        """
        if not await self.can_execute():
            time_remaining = self.recovery_timeout - self._time_since_last_failure()
            raise CircuitOpenError(
                service=self.service,
                recovery_time_seconds=max(0, time_remaining),
            )

        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure(e)
            raise

    async def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._half_open_count = 0
            logger.info(
                "Circuit breaker reset",
                service=self.service.value,
            )

    def get_status(self) -> dict[str, Any]:
        """
        Get current circuit breaker status.

        Returns:
            Dictionary with circuit breaker metrics
        """
        return {
            "service": self.service.value,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "time_since_last_failure": (
                self._time_since_last_failure() if self._last_failure_time is not None else None
            ),
            "half_open_count": self._half_open_count,
            "half_open_requests": self.half_open_requests,
        }


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Provides singleton-like access to circuit breakers for each service.
    """

    _instance: "CircuitBreakerRegistry | None" = None
    _lock: asyncio.Lock | None = None
    _breakers: dict[ServiceType, CircuitBreaker]
    _initialized: bool

    def __new__(cls) -> "CircuitBreakerRegistry":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._breakers = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize registry (only on first call)."""
        if not self._initialized:
            self._initialized = True
            if CircuitBreakerRegistry._lock is None:
                CircuitBreakerRegistry._lock = asyncio.Lock()

    def get_breaker(
        self,
        service: ServiceType,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
        half_open_requests: int | None = None,
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a service.

        Args:
            service: The service to get a breaker for
            failure_threshold: Override default failure threshold
            recovery_timeout: Override default recovery timeout
            half_open_requests: Override default half-open requests

        Returns:
            CircuitBreaker instance for the service
        """
        if service not in self._breakers:
            # Import settings here to avoid circular imports
            from src.config import get_settings

            settings = get_settings()

            self._breakers[service] = CircuitBreaker(
                service=service,
                failure_threshold=(
                    failure_threshold
                    if failure_threshold is not None
                    else settings.circuit_breaker_failure_threshold
                ),
                recovery_timeout=(
                    recovery_timeout
                    if recovery_timeout is not None
                    else settings.circuit_breaker_recovery_timeout
                ),
                half_open_requests=(
                    half_open_requests
                    if half_open_requests is not None
                    else settings.circuit_breaker_half_open_requests
                ),
            )

        return self._breakers[service]

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """
        Get status of all circuit breakers.

        Returns:
            Dictionary mapping service names to their status
        """
        return {service.value: breaker.get_status() for service, breaker in self._breakers.items()}

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """
    Get the circuit breaker registry singleton.

    Returns:
        CircuitBreakerRegistry instance
    """
    return CircuitBreakerRegistry()


def get_circuit_breaker(service: ServiceType) -> CircuitBreaker:
    """
    Get circuit breaker for a specific service.

    Convenience function for common usage.

    Args:
        service: The service to get a breaker for

    Returns:
        CircuitBreaker instance for the service
    """
    return get_circuit_breaker_registry().get_breaker(service)
