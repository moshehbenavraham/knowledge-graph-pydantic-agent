"""
User-friendly error message formatting.

Converts technical errors into actionable user messages without
exposing internal system details (connection strings, API keys, etc.).
"""

from .error_types import (
    CircuitOpenError,
    ErrorCategory,
    GracefulDegradationError,
    MaxRetriesExceededError,
    ResilienceError,
    ServiceType,
)

# Service-specific user-friendly names
SERVICE_DISPLAY_NAMES: dict[ServiceType, str] = {
    ServiceType.NEO4J: "knowledge graph",
    ServiceType.SUPABASE: "document database",
    ServiceType.EMBEDDING_API: "text analysis service",
    ServiceType.LLM_API: "AI service",
    ServiceType.WEB_SEARCH: "web search",
}


# Error category to user message templates
CATEGORY_MESSAGES: dict[ErrorCategory, str] = {
    ErrorCategory.TRANSIENT: ("A temporary issue occurred. Please try again in a moment."),
    ErrorCategory.FATAL: (
        "Unable to complete your request due to a configuration issue. "
        "Please contact support if this persists."
    ),
    ErrorCategory.USER_ERROR: (
        "There was an issue with your request. Please check your input and try again."
    ),
    ErrorCategory.SYSTEM_ERROR: ("An unexpected error occurred. Our team has been notified."),
}


def get_service_display_name(service: ServiceType | None) -> str:
    """
    Get user-friendly display name for a service.

    Args:
        service: Service type or None

    Returns:
        Human-readable service name
    """
    if service is None:
        return "service"
    return SERVICE_DISPLAY_NAMES.get(service, service.value)


def format_error_for_user(
    error: Exception,
    include_retry_hint: bool = True,
) -> str:
    """
    Format an error into a user-friendly message.

    Converts technical exceptions into actionable messages without
    exposing internal details like connection strings or API keys.

    Args:
        error: The exception to format
        include_retry_hint: Whether to include retry suggestions

    Returns:
        User-friendly error message
    """
    # Handle resilience-specific errors
    if isinstance(error, CircuitOpenError):
        service_name = get_service_display_name(error.service)
        if error.recovery_time_seconds > 60:
            time_hint = f"about {int(error.recovery_time_seconds / 60)} minutes"
        else:
            time_hint = f"about {int(error.recovery_time_seconds)} seconds"
        return (
            f"The {service_name} is temporarily unavailable. " f"Please try again in {time_hint}."
        )

    if isinstance(error, MaxRetriesExceededError):
        return (
            "The request could not be completed after several attempts. "
            "Please try again later or simplify your query."
        )

    if isinstance(error, GracefulDegradationError):
        service_name = get_service_display_name(error.primary_service)
        return (
            f"Using backup search while the {service_name} is unavailable. "
            "Results may be limited."
        )

    if isinstance(error, ResilienceError) and error.context is not None:
        if error.context.user_message:
            return error.context.user_message
        return CATEGORY_MESSAGES.get(
            error.context.category,
            CATEGORY_MESSAGES[ErrorCategory.SYSTEM_ERROR],
        )

    # Handle common exception types
    error_message = str(error).lower()

    # Timeout errors
    if "timeout" in error_message or "timed out" in error_message:
        msg = "The request took too long to complete."
        if include_retry_hint:
            msg += " Please try again with a simpler query."
        return msg

    # Connection errors
    if "connection" in error_message or "network" in error_message:
        msg = "Unable to connect to the server."
        if include_retry_hint:
            msg += " Please check your connection and try again."
        return msg

    # Rate limiting
    if "rate limit" in error_message or "too many requests" in error_message:
        return "Too many requests. Please wait a moment before trying again."

    # Authentication errors (don't expose details)
    if "authentication" in error_message or "unauthorized" in error_message:
        return "Authentication failed. Please check your credentials."

    # Permission errors
    if "permission" in error_message or "forbidden" in error_message:
        return "You don't have permission to perform this action."

    # Validation errors (safe to show some details)
    if "validation" in error_message or "invalid" in error_message:
        # Try to extract the useful part without exposing internals
        if "query" in error_message:
            return "Invalid query format. Please check your input."
        return "Invalid request. Please check your input and try again."

    # Not found errors
    if "not found" in error_message:
        return "The requested resource could not be found."

    # Generic fallback - never expose the actual error message
    return CATEGORY_MESSAGES[ErrorCategory.SYSTEM_ERROR]


def format_degradation_notice(
    primary_service: ServiceType,
    fallback_description: str,
) -> str:
    """
    Format a notice about graceful degradation.

    Args:
        primary_service: The service that is unavailable
        fallback_description: Description of the fallback being used

    Returns:
        User-friendly degradation notice
    """
    service_name = get_service_display_name(primary_service)
    return f"Note: Using {fallback_description} while {service_name} is unavailable."


def format_retry_notice(
    attempt: int,
    max_attempts: int,
) -> str:
    """
    Format a notice about retry attempts.

    Args:
        attempt: Current attempt number
        max_attempts: Maximum attempts configured

    Returns:
        User-friendly retry notice
    """
    remaining = max_attempts - attempt
    if remaining == 1:
        return "Retrying... (final attempt)"
    return f"Retrying... ({remaining} attempts remaining)"


class ErrorMessageFormatter:
    """
    Formatter for converting errors to user-friendly messages.

    Provides consistent error message formatting with context awareness.
    """

    def __init__(
        self,
        include_retry_hints: bool = True,
        include_service_names: bool = True,
    ) -> None:
        """
        Initialize formatter.

        Args:
            include_retry_hints: Whether to include retry suggestions
            include_service_names: Whether to include service names in messages
        """
        self.include_retry_hints = include_retry_hints
        self.include_service_names = include_service_names

    def format(self, error: Exception) -> str:
        """
        Format an error for user display.

        Args:
            error: The exception to format

        Returns:
            User-friendly error message
        """
        return format_error_for_user(
            error,
            include_retry_hint=self.include_retry_hints,
        )

    def format_with_context(
        self,
        error: Exception,
        operation: str | None = None,
        service: ServiceType | None = None,
    ) -> str:
        """
        Format an error with additional context.

        Args:
            error: The exception to format
            operation: The operation that was being performed
            service: The service that failed

        Returns:
            User-friendly error message with context
        """
        base_message = self.format(error)

        # Add operation context if available and useful
        if operation and self.include_service_names:
            operation_display = operation.replace("_", " ")
            if not base_message.lower().startswith(operation_display.lower()):
                base_message = f"Error during {operation_display}: {base_message}"

        return base_message

    def format_recovery_suggestion(
        self,
        error: Exception,
    ) -> str | None:
        """
        Get a recovery suggestion for an error.

        Args:
            error: The exception to suggest recovery for

        Returns:
            Recovery suggestion or None if no specific suggestion
        """
        error_message = str(error).lower()

        if "timeout" in error_message or "timed out" in error_message:
            return "Try simplifying your query or breaking it into smaller parts."

        if "rate limit" in error_message:
            return "Wait a minute before making more requests."

        if isinstance(error, CircuitOpenError):
            return "The service is recovering. Try again shortly."

        if isinstance(error, GracefulDegradationError):
            return "Results may be less comprehensive while backup search is active."

        return None
