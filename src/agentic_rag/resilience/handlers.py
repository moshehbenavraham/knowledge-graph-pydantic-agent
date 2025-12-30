"""
Graceful degradation handlers for service fallbacks.

Provides handlers that automatically switch to fallback strategies
when primary services are unavailable.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

import structlog

from .circuit_breaker import get_circuit_breaker
from .error_types import (
    GracefulDegradationError,
    ServiceType,
    categorize_exception,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class DegradationState:
    """
    Tracks the current degradation state for a service.

    Records when degradation started, how many times fallback was used,
    and when the service last recovered.
    """

    is_degraded: bool = False
    degraded_since: datetime | None = None
    fallback_count: int = 0
    last_recovery: datetime | None = None
    last_error: str | None = None

    def enter_degraded_mode(self, error: str) -> None:
        """
        Enter degraded mode.

        Args:
            error: Description of the error that triggered degradation
        """
        if not self.is_degraded:
            self.is_degraded = True
            self.degraded_since = datetime.utcnow()
        self.last_error = error
        self.fallback_count += 1

    def exit_degraded_mode(self) -> None:
        """Exit degraded mode (service recovered)."""
        self.is_degraded = False
        self.last_recovery = datetime.utcnow()
        self.degraded_since = None
        self.last_error = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/monitoring."""
        return {
            "is_degraded": self.is_degraded,
            "degraded_since": (self.degraded_since.isoformat() if self.degraded_since else None),
            "fallback_count": self.fallback_count,
            "last_recovery": (self.last_recovery.isoformat() if self.last_recovery else None),
            "last_error": self.last_error,
        }


@dataclass
class DegradationResult(Generic[T]):
    """
    Result from a degradation-aware operation.

    Contains the result value along with metadata about whether
    a fallback was used.
    """

    value: T
    used_fallback: bool = False
    fallback_reason: str | None = None
    primary_service: ServiceType | None = None
    fallback_description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure metadata is initialized."""
        if self.metadata is None:
            self.metadata = {}


class GracefulDegradationHandler(Generic[T]):
    """
    Handler for graceful degradation between primary and fallback operations.

    Automatically uses the fallback function when the primary fails or
    the circuit breaker is open.

    Example:
        handler = GracefulDegradationHandler(
            primary_service=ServiceType.NEO4J,
            fallback_description="vector-only search",
        )

        result = await handler.execute(
            primary_func=lambda: hybrid_search(query),
            fallback_func=lambda: vector_search(query),
        )

        if result.used_fallback:
            print(f"Used fallback: {result.fallback_reason}")
    """

    def __init__(
        self,
        primary_service: ServiceType,
        fallback_description: str,
        enabled: bool | None = None,
    ) -> None:
        """
        Initialize degradation handler.

        Args:
            primary_service: The primary service that may fail
            fallback_description: Human-readable description of fallback
            enabled: Whether degradation is enabled (default from settings)
        """
        self.primary_service = primary_service
        self.fallback_description = fallback_description
        self.state = DegradationState()

        # Load enabled state from settings if not specified
        if enabled is None:
            from src.config import get_settings

            settings = get_settings()
            self._enabled = settings.graceful_degradation_enabled
        else:
            self._enabled = enabled

    @property
    def is_enabled(self) -> bool:
        """Check if graceful degradation is enabled."""
        return self._enabled

    @property
    def is_degraded(self) -> bool:
        """Check if currently in degraded mode."""
        return self.state.is_degraded

    def _should_use_fallback_preemptively(self) -> bool:
        """
        Check if we should use fallback before even trying primary.

        This happens when the circuit breaker is open.
        """
        breaker = get_circuit_breaker(self.primary_service)
        return breaker.is_open

    async def execute(
        self,
        primary_func: Callable[[], Awaitable[T]],
        fallback_func: Callable[[], Awaitable[T]],
        raise_on_fallback_failure: bool = True,
    ) -> DegradationResult[T]:
        """
        Execute operation with graceful degradation.

        Tries the primary function first. If it fails and degradation is enabled,
        falls back to the fallback function.

        Args:
            primary_func: Primary async function to try
            fallback_func: Fallback async function if primary fails
            raise_on_fallback_failure: Whether to raise if fallback also fails

        Returns:
            DegradationResult with the value and fallback metadata

        Raises:
            Exception: If primary fails, degradation is disabled, and fallback fails
        """
        # Check if circuit is open - use fallback preemptively
        if self._enabled and self._should_use_fallback_preemptively():
            logger.info(
                "Using fallback preemptively (circuit open)",
                primary_service=self.primary_service.value,
                fallback=self.fallback_description,
            )
            return await self._execute_fallback(
                fallback_func=fallback_func,
                reason="Circuit breaker is open",
                raise_on_failure=raise_on_fallback_failure,
            )

        # Try primary function
        try:
            result = await primary_func()

            # Primary succeeded - exit degraded mode if we were in it
            if self.state.is_degraded:
                logger.info(
                    "Exiting degraded mode (primary recovered)",
                    primary_service=self.primary_service.value,
                    fallback_count=self.state.fallback_count,
                )
                self.state.exit_degraded_mode()

            return DegradationResult(
                value=result,
                used_fallback=False,
                primary_service=self.primary_service,
            )

        except Exception as e:
            # Check if we should fall back
            if not self._enabled:
                logger.warning(
                    "Graceful degradation disabled, raising primary error",
                    primary_service=self.primary_service.value,
                    error=str(e),
                )
                raise

            # Categorize the error
            error_context = categorize_exception(
                e,
                service=self.primary_service,
                operation="primary_execution",
            )

            # Log the degradation
            logger.warning(
                "Primary service failed, using fallback",
                primary_service=self.primary_service.value,
                fallback=self.fallback_description,
                error_type=type(e).__name__,
                error_category=error_context.category.value,
                is_retriable=error_context.is_retriable,
            )

            return await self._execute_fallback(
                fallback_func=fallback_func,
                reason=str(e),
                original_error=e,
                raise_on_failure=raise_on_fallback_failure,
            )

    async def _execute_fallback(
        self,
        fallback_func: Callable[[], Awaitable[T]],
        reason: str,
        original_error: Exception | None = None,
        raise_on_failure: bool = True,
    ) -> DegradationResult[T]:
        """
        Execute the fallback function.

        Args:
            fallback_func: Fallback async function
            reason: Reason for using fallback
            original_error: Original exception that triggered fallback
            raise_on_failure: Whether to raise if fallback also fails

        Returns:
            DegradationResult with fallback metadata

        Raises:
            GracefulDegradationError: If fallback fails and raise_on_failure is True
        """
        # Enter degraded mode
        self.state.enter_degraded_mode(reason)

        try:
            result = await fallback_func()

            return DegradationResult(
                value=result,
                used_fallback=True,
                fallback_reason=reason,
                primary_service=self.primary_service,
                fallback_description=self.fallback_description,
                metadata={
                    "fallback_count": self.state.fallback_count,
                    "degraded_since": (
                        self.state.degraded_since.isoformat() if self.state.degraded_since else None
                    ),
                },
            )

        except Exception as fallback_error:
            logger.error(
                "Fallback also failed (double failure)",
                primary_service=self.primary_service.value,
                fallback=self.fallback_description,
                primary_error=str(original_error) if original_error else None,
                fallback_error=str(fallback_error),
            )

            if raise_on_failure:
                raise GracefulDegradationError(
                    primary_service=self.primary_service,
                    fallback_description=self.fallback_description,
                    original_error=fallback_error,
                ) from fallback_error

            # Return a result indicating total failure
            raise

    def get_status(self) -> dict[str, Any]:
        """
        Get current handler status.

        Returns:
            Dictionary with handler status and metrics
        """
        return {
            "primary_service": self.primary_service.value,
            "fallback_description": self.fallback_description,
            "enabled": self._enabled,
            "degradation_state": self.state.to_dict(),
            "circuit_breaker_open": self._should_use_fallback_preemptively(),
        }


class SearchDegradationHandler(GracefulDegradationHandler[Any]):
    """
    Specialized degradation handler for search operations.

    Handles the specific case of falling back from hybrid search
    (vector + graph) to vector-only search.
    """

    def __init__(self, enabled: bool | None = None) -> None:
        """
        Initialize search degradation handler.

        Args:
            enabled: Whether degradation is enabled (default from settings)
        """
        super().__init__(
            primary_service=ServiceType.NEO4J,
            fallback_description="vector-only search",
            enabled=enabled,
        )

    async def execute_search(
        self,
        hybrid_search_func: Callable[[], Awaitable[T]],
        vector_search_func: Callable[[], Awaitable[T]],
    ) -> DegradationResult[T]:
        """
        Execute search with automatic fallback.

        Args:
            hybrid_search_func: Function performing hybrid (vector + graph) search
            vector_search_func: Function performing vector-only search

        Returns:
            DegradationResult with search results and fallback metadata
        """
        return await self.execute(
            primary_func=hybrid_search_func,
            fallback_func=vector_search_func,
            raise_on_fallback_failure=True,
        )


# Global search degradation handler instance
_search_handler: SearchDegradationHandler | None = None


def get_search_degradation_handler() -> SearchDegradationHandler:
    """
    Get the global search degradation handler.

    Returns:
        SearchDegradationHandler singleton instance
    """
    global _search_handler
    if _search_handler is None:
        _search_handler = SearchDegradationHandler()
    return _search_handler
