"""
Error type definitions for the resilience module.

This module defines error categories, exception classes, and context models
for consistent error handling across the Agentic GraphRAG system.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCategory(str, Enum):
    """
    Categories of errors for routing to appropriate handlers.

    TRANSIENT: Temporary failures that may succeed on retry (network timeouts, rate limits)
    FATAL: Permanent failures that should not be retried (invalid queries, auth failures)
    USER_ERROR: Errors caused by invalid user input
    SYSTEM_ERROR: Internal system failures requiring operator attention
    """

    TRANSIENT = "transient"
    FATAL = "fatal"
    USER_ERROR = "user_error"
    SYSTEM_ERROR = "system_error"


class ServiceType(str, Enum):
    """External services that may fail and require resilience handling."""

    NEO4J = "neo4j"
    SUPABASE = "supabase"
    EMBEDDING_API = "embedding_api"
    LLM_API = "llm_api"
    WEB_SEARCH = "web_search"


class ErrorContext(BaseModel):
    """
    Structured error context for logging and handling.

    Captures all relevant information about an error occurrence
    for debugging, monitoring, and user feedback.
    """

    category: ErrorCategory = Field(description="Error category for routing to appropriate handler")
    service: ServiceType | None = Field(
        default=None,
        description="External service that caused the error, if applicable",
    )
    operation: str = Field(description="Operation that was being performed when error occurred")
    error_type: str = Field(description="Python exception class name")
    error_message: str = Field(description="Original error message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retry attempts made",
    )
    is_retriable: bool = Field(
        default=False,
        description="Whether this error can be retried",
    )
    user_message: str | None = Field(
        default=None,
        description="User-friendly error message (no internal details)",
    )
    additional_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for debugging (not exposed to users)",
    )

    def to_log_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for structured logging.

        Returns:
            Dictionary with all error context fields for structlog.
        """
        return {
            "error_category": self.category.value,
            "error_service": self.service.value if self.service else None,
            "error_operation": self.operation,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "error_timestamp": self.timestamp.isoformat(),
            "error_retry_count": self.retry_count,
            "error_is_retriable": self.is_retriable,
            **self.additional_context,
        }


class ResilienceError(Exception):
    """
    Base exception for resilience module errors.

    All custom exceptions in this module inherit from this class.
    """

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
    ) -> None:
        """
        Initialize resilience error.

        Args:
            message: Error message
            context: Structured error context
        """
        super().__init__(message)
        self.context = context


class CircuitOpenError(ResilienceError):
    """
    Raised when circuit breaker is open and rejecting requests.

    This error is not retriable - the caller should use a fallback
    or inform the user that the service is temporarily unavailable.
    """

    def __init__(
        self,
        service: ServiceType,
        recovery_time_seconds: float,
    ) -> None:
        """
        Initialize circuit open error.

        Args:
            service: The service whose circuit is open
            recovery_time_seconds: Seconds until circuit enters half-open state
        """
        self.service = service
        self.recovery_time_seconds = recovery_time_seconds
        context = ErrorContext(
            category=ErrorCategory.TRANSIENT,
            service=service,
            operation="circuit_breaker_check",
            error_type="CircuitOpenError",
            error_message=f"Circuit breaker open for {service.value}",
            is_retriable=False,
            user_message=(
                f"The {service.value} service is temporarily unavailable. "
                f"Please try again in {int(recovery_time_seconds)} seconds."
            ),
        )
        super().__init__(
            f"Circuit breaker open for {service.value}, "
            f"recovery in {recovery_time_seconds:.1f}s",
            context=context,
        )


class MaxRetriesExceededError(ResilienceError):
    """
    Raised when maximum retry attempts have been exhausted.

    The original error is preserved in the context for debugging.
    """

    def __init__(
        self,
        operation: str,
        max_attempts: int,
        last_error: Exception,
    ) -> None:
        """
        Initialize max retries exceeded error.

        Args:
            operation: The operation that failed
            max_attempts: Maximum retry attempts configured
            last_error: The last exception that occurred
        """
        self.operation = operation
        self.max_attempts = max_attempts
        self.last_error = last_error
        context = ErrorContext(
            category=ErrorCategory.TRANSIENT,
            operation=operation,
            error_type=type(last_error).__name__,
            error_message=str(last_error),
            retry_count=max_attempts,
            is_retriable=False,
            user_message=(
                f"Operation failed after {max_attempts} attempts. " "Please try again later."
            ),
        )
        super().__init__(
            f"Max retries ({max_attempts}) exceeded for {operation}: {last_error}",
            context=context,
        )


class GracefulDegradationError(ResilienceError):
    """
    Raised when graceful degradation is triggered.

    This is an informational exception indicating that a fallback
    strategy is being used instead of the primary service.
    """

    def __init__(
        self,
        primary_service: ServiceType,
        fallback_description: str,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize graceful degradation error.

        Args:
            primary_service: Service that failed
            fallback_description: Description of fallback being used
            original_error: The error that triggered degradation
        """
        self.primary_service = primary_service
        self.fallback_description = fallback_description
        self.original_error = original_error
        context = ErrorContext(
            category=ErrorCategory.TRANSIENT,
            service=primary_service,
            operation="graceful_degradation",
            error_type=type(original_error).__name__ if original_error else "Unknown",
            error_message=str(original_error) if original_error else "Service unavailable",
            is_retriable=True,
            user_message=(
                f"Using {fallback_description} while {primary_service.value} is unavailable."
            ),
            additional_context={
                "fallback": fallback_description,
            },
        )
        super().__init__(
            f"Graceful degradation: {primary_service.value} -> {fallback_description}",
            context=context,
        )


def categorize_exception(
    exc: Exception,
    service: ServiceType | None = None,
    operation: str = "unknown",
) -> ErrorContext:
    """
    Categorize an exception into the appropriate error category.

    Uses exception type and message patterns to determine if the error
    is transient (retriable) or fatal (not retriable).

    Args:
        exc: The exception to categorize
        service: Optional service that raised the exception
        operation: The operation being performed

    Returns:
        ErrorContext with appropriate category and metadata
    """
    error_type = type(exc).__name__
    error_message = str(exc).lower()

    # Transient error patterns (retriable)
    transient_patterns = [
        "timeout",
        "timed out",
        "connection refused",
        "connection reset",
        "temporarily unavailable",
        "rate limit",
        "too many requests",
        "503",
        "502",
        "504",
        "service unavailable",
        "network",
        "socket",
        "eof",
        "broken pipe",
    ]

    # Fatal error patterns (not retriable)
    fatal_patterns = [
        "authentication",
        "unauthorized",
        "forbidden",
        "not found",
        "invalid",
        "syntax error",
        "parse error",
        "permission denied",
        "access denied",
    ]

    # User error patterns
    user_error_patterns = [
        "invalid query",
        "empty query",
        "query too long",
        "unsupported",
        "invalid parameter",
        "missing required",
    ]

    # Determine category based on patterns
    category = ErrorCategory.SYSTEM_ERROR
    is_retriable = False

    for pattern in transient_patterns:
        if pattern in error_message or pattern in error_type.lower():
            category = ErrorCategory.TRANSIENT
            is_retriable = True
            break

    for pattern in fatal_patterns:
        if pattern in error_message:
            category = ErrorCategory.FATAL
            is_retriable = False
            break

    for pattern in user_error_patterns:
        if pattern in error_message:
            category = ErrorCategory.USER_ERROR
            is_retriable = False
            break

    return ErrorContext(
        category=category,
        service=service,
        operation=operation,
        error_type=error_type,
        error_message=str(exc),
        is_retriable=is_retriable,
    )
