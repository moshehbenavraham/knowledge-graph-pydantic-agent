"""
User-friendly error display component.

Transforms technical errors into actionable user messages
with appropriate severity indicators and recovery guidance.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import streamlit as st
import structlog

from src.agentic_rag.resilience import format_error_for_user

logger = structlog.get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for display styling."""

    INFO = "info"  # Informational, not an error
    WARNING = "warning"  # Recoverable, may affect results
    ERROR = "error"  # Action failed, retry possible
    CRITICAL = "critical"  # Serious error, may require support


@dataclass
class ErrorDisplayConfig:
    """
    Configuration for error display rendering.

    Attributes:
        severity: Error severity level
        title: Short error title
        message: User-friendly error message
        recovery_suggestion: Actionable next steps
        retry_enabled: Whether to show retry option
        retry_after_seconds: Wait time before retry (if applicable)
        show_details: Whether to allow showing technical details
        technical_details: Technical error info (hidden by default)
    """

    severity: ErrorSeverity
    title: str
    message: str
    recovery_suggestion: str | None = None
    retry_enabled: bool = False
    retry_after_seconds: int | None = None
    show_details: bool = False
    technical_details: str | None = None


# Error type to severity mapping
ERROR_TYPE_SEVERITY: dict[str, ErrorSeverity] = {
    "service_unavailable": ErrorSeverity.WARNING,
    "retry_exhausted": ErrorSeverity.WARNING,
    "resilience_error": ErrorSeverity.WARNING,
    "timeout": ErrorSeverity.WARNING,
    "rate_limit": ErrorSeverity.WARNING,
    "connection": ErrorSeverity.ERROR,
    "authentication": ErrorSeverity.ERROR,
    "validation": ErrorSeverity.INFO,
    "not_found": ErrorSeverity.INFO,
    "unexpected": ErrorSeverity.ERROR,
}

# Recovery suggestions by error type
RECOVERY_SUGGESTIONS: dict[str, str] = {
    "service_unavailable": "The service will recover automatically. Please try again in a moment.",
    "retry_exhausted": "Try simplifying your query or breaking it into smaller parts.",
    "resilience_error": "The system is working to recover. Please wait and try again.",
    "timeout": "Try a more specific query or reduce the scope of your search.",
    "rate_limit": "Please wait a moment before making more requests.",
    "connection": "Check your network connection and try again.",
    "authentication": "Please verify your credentials and try again.",
    "validation": "Please check your input and try again with valid data.",
    "not_found": "Try different search terms or check the document exists.",
    "unexpected": "If this persists, please contact support.",
}

# Severity display configuration
SEVERITY_STYLES: dict[ErrorSeverity, dict[str, str]] = {
    ErrorSeverity.INFO: {
        "icon": "[i]",
        "color": "blue",
        "streamlit_type": "info",
    },
    ErrorSeverity.WARNING: {
        "icon": "[!]",
        "color": "orange",
        "streamlit_type": "warning",
    },
    ErrorSeverity.ERROR: {
        "icon": "[X]",
        "color": "red",
        "streamlit_type": "error",
    },
    ErrorSeverity.CRITICAL: {
        "icon": "[!!!]",
        "color": "red",
        "streamlit_type": "error",
    },
}


def create_error_config(
    error: Exception | None = None,
    error_type: str = "unexpected",
    message: str | None = None,
    recoverable: bool = True,
    retry_after_seconds: int | None = None,
) -> ErrorDisplayConfig:
    """
    Create an ErrorDisplayConfig from an error or error type.

    Args:
        error: Exception instance (optional)
        error_type: Type of error (e.g., 'service_unavailable')
        message: Custom message (uses format_error_for_user if not provided)
        recoverable: Whether the error is recoverable
        retry_after_seconds: Wait time before retry

    Returns:
        ErrorDisplayConfig ready for rendering
    """
    # Determine severity
    severity = ERROR_TYPE_SEVERITY.get(error_type, ErrorSeverity.ERROR)

    # Get user-friendly message
    if message is None and error is not None:
        message = format_error_for_user(error)
    elif message is None:
        message = "An unexpected error occurred."

    # Get recovery suggestion
    recovery = RECOVERY_SUGGESTIONS.get(error_type)
    if retry_after_seconds:
        if retry_after_seconds > 60:
            time_str = f"{retry_after_seconds // 60} minutes"
        else:
            time_str = f"{retry_after_seconds} seconds"
        recovery = f"Please try again in about {time_str}."

    # Build title
    title_map = {
        "service_unavailable": "Service Temporarily Unavailable",
        "retry_exhausted": "Request Could Not Complete",
        "resilience_error": "Temporary Issue",
        "timeout": "Request Timed Out",
        "rate_limit": "Too Many Requests",
        "connection": "Connection Error",
        "authentication": "Authentication Failed",
        "validation": "Invalid Input",
        "not_found": "Not Found",
        "unexpected": "Error",
    }
    title = title_map.get(error_type, "Error")

    # Technical details
    technical = None
    if error is not None:
        technical = f"{type(error).__name__}: {error!s}"

    return ErrorDisplayConfig(
        severity=severity,
        title=title,
        message=message,
        recovery_suggestion=recovery,
        retry_enabled=recoverable,
        retry_after_seconds=retry_after_seconds,
        show_details=error is not None,
        technical_details=technical,
    )


def render_error_display(
    config: ErrorDisplayConfig,
    on_retry: Any | None = None,
) -> None:
    """
    Render a user-friendly error display.

    Args:
        config: Error display configuration
        on_retry: Callback function for retry button (optional)
    """
    style = SEVERITY_STYLES.get(config.severity, SEVERITY_STYLES[ErrorSeverity.ERROR])

    # Use appropriate Streamlit message type
    streamlit_type = style["streamlit_type"]

    # Build message content
    content_parts = [config.message]

    if config.recovery_suggestion:
        content_parts.append("")
        content_parts.append(f"**What to do:** {config.recovery_suggestion}")

    content = "\n".join(content_parts)

    # Render with appropriate type
    if streamlit_type == "info":
        st.info(content, icon=style["icon"])
    elif streamlit_type == "warning":
        st.warning(content, icon=style["icon"])
    else:
        st.error(content, icon=style["icon"])

    # Retry button if applicable
    if config.retry_enabled and on_retry is not None:
        col1, _col2 = st.columns([1, 4])
        with col1:
            if st.button("Try Again", type="primary"):
                on_retry()

    # Technical details expander (for debugging)
    if config.show_details and config.technical_details:
        with st.expander("Technical Details", expanded=False):
            st.code(config.technical_details, language="text")


def render_error_from_event(
    event: dict[str, Any],
    on_retry: Any | None = None,
) -> None:
    """
    Render an error display from a streaming error event.

    Args:
        event: Error event dictionary with type, error_type, message, etc.
        on_retry: Callback function for retry button (optional)
    """
    error_type = event.get("error_type", "unexpected")
    message = event.get("message")
    recoverable = event.get("recoverable", False)
    retry_after = event.get("retry_after_seconds")

    config = create_error_config(
        error_type=error_type,
        message=message,
        recoverable=recoverable,
        retry_after_seconds=retry_after,
    )

    render_error_display(config, on_retry=on_retry)


def render_degradation_notice(
    service_name: str,
    fallback_description: str,
) -> None:
    """
    Render a graceful degradation notice.

    Shows users when a backup/fallback is being used.

    Args:
        service_name: Name of the unavailable service
        fallback_description: Description of what's being used instead
    """
    message = (
        f"Note: Using {fallback_description} while {service_name} is unavailable. "
        "Results may be limited."
    )

    st.info(message, icon="[i]")
