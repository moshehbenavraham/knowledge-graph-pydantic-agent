"""
Analytics infrastructure - core component.

Provides centralized analytics logging with async batching.
This is NOT optional - it's foundational system infrastructure.
"""

from .logger import (
    AgentInteractionEvent,
    AnalyticsLogger,
    IngestionAnalyticsEvent,
    SearchAnalyticsEvent,
    SystemMetricsEvent,
    ToolUsageEvent,
)

# Global singleton instance
_analytics_logger: AnalyticsLogger | None = None


def get_analytics_logger() -> AnalyticsLogger:
    """
    Get shared analytics logger instance.

    REQUIRED component - raises if not initialized.

    Returns:
        AnalyticsLogger: The global analytics logger instance

    Raises:
        RuntimeError: If analytics logger not initialized
    """
    if _analytics_logger is None:
        raise RuntimeError(
            "Analytics logger not initialized. "
            "Call initialize_analytics_logger() during application startup."
        )
    return _analytics_logger


async def initialize_analytics_logger(connection_manager) -> AnalyticsLogger:
    """
    Initialize global analytics logger.

    Must be called during application startup.

    Args:
        connection_manager: ConnectionManager instance for database access

    Returns:
        AnalyticsLogger: The initialized analytics logger instance
    """
    global _analytics_logger
    if _analytics_logger is None:
        _analytics_logger = AnalyticsLogger(connection_manager)
        await _analytics_logger.start()
    return _analytics_logger


async def shutdown_analytics_logger() -> None:
    """
    Shutdown analytics logger and flush remaining events.

    Should be called during application shutdown.
    """
    global _analytics_logger
    if _analytics_logger is not None:
        await _analytics_logger.stop()
        _analytics_logger = None


__all__ = [
    "AgentInteractionEvent",
    "AnalyticsLogger",
    "IngestionAnalyticsEvent",
    "SearchAnalyticsEvent",
    "SystemMetricsEvent",
    "ToolUsageEvent",
    "get_analytics_logger",
    "initialize_analytics_logger",
    "shutdown_analytics_logger",
]
