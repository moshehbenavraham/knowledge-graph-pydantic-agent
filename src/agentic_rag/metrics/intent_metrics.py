"""
Intent-specific latency metrics for Prometheus.

Provides histogram metrics for search latency segmented by intent type,
enabling granular performance monitoring across different query patterns.
"""

import threading
from typing import Any

import structlog
from prometheus_client import REGISTRY, Counter, Histogram

from src.config import get_settings

logger = structlog.get_logger(__name__)

# Custom histogram buckets optimized for query latencies (in seconds)
# Covers sub-100ms to 10+ second range for various query complexities
LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

# All supported intent types from SearchIntent enum
INTENT_TYPES = (
    "VECTOR_HEAVY",
    "GRAPH_HEAVY",
    "HYBRID",
    "TEMPORAL",
    "ENTITY_FOCUSED",
    "MULTI_HOP",
    "TEMPORAL_TREND",
    "COMPARISON",
)


def _get_or_create_metric(
    metric_class: type[Counter] | type[Histogram],
    name: str,
    description: str,
    labelnames: list[str] | None = None,
    buckets: tuple[float, ...] | None = None,
    registry: Any = REGISTRY,
) -> Any:
    """
    Get existing metric or create new one to avoid duplicates.

    This function is essential for Streamlit compatibility where module reloading
    would otherwise cause Prometheus metric re-registration errors.

    Args:
        metric_class: Prometheus metric class (Counter, Histogram)
        name: Metric name
        description: Metric description
        labelnames: Optional label names
        buckets: Optional histogram buckets
        registry: Prometheus registry

    Returns:
        Prometheus metric instance
    """
    try:
        for collector in list(registry._collector_to_names.keys()):
            collector_name = getattr(collector, "_name", None)
            if collector_name == name:
                return collector

        if hasattr(registry, "_names_to_collectors"):
            for registered_name, collector in registry._names_to_collectors.items():
                if registered_name == name:
                    return collector
    except (AttributeError, KeyError, RuntimeError) as e:
        logger.debug("Error checking for existing metric", name=name, error=str(e))

    kwargs: dict[str, Any] = {
        "name": name,
        "documentation": description,
        "registry": registry,
    }
    if labelnames:
        kwargs["labelnames"] = labelnames
    if buckets and metric_class == Histogram:
        kwargs["buckets"] = buckets

    try:
        return metric_class(**kwargs)
    except ValueError as e:
        error_msg = str(e)
        if "Duplicated" in error_msg:
            for collector in list(registry._collector_to_names.keys()):
                for attr in ["_name", "name", "_metric_name"]:
                    collector_name = getattr(collector, attr, None)
                    if collector_name == name:
                        return collector
            raise RuntimeError(
                f"Prometheus metric '{name}' registration conflict. "
                f"Try restarting the server. Original error: {error_msg}"
            ) from e
        raise


class IntentMetrics:
    """
    Prometheus metrics for intent-specific query latency tracking.

    Provides histogram metrics segmented by intent type (VECTOR_HEAVY, GRAPH_HEAVY,
    HYBRID, TEMPORAL, ENTITY_FOCUSED, MULTI_HOP, TEMPORAL_TREND, COMPARISON).

    Attributes:
        latency_histogram: Prometheus Histogram for query latency
        query_counter: Prometheus Counter for total queries by intent
    """

    def __init__(self) -> None:
        """Initialize intent metrics with Prometheus histograms and counters."""
        settings = get_settings()

        if not settings.intent_metrics_enabled:
            logger.info("Intent metrics disabled via configuration")
            self._enabled = False
            self._latency_histogram = None
            self._query_counter = None
            return

        self._enabled = True
        self._lock = threading.Lock()

        # Create histogram for latency by intent type
        self._latency_histogram = _get_or_create_metric(
            Histogram,
            "agentic_rag_search_latency_seconds",
            "Search query latency in seconds by intent type",
            labelnames=["intent_type"],
            buckets=LATENCY_BUCKETS,
        )

        # Create counter for total queries by intent
        self._query_counter = _get_or_create_metric(
            Counter,
            "agentic_rag_search_queries_total",
            "Total search queries by intent type",
            labelnames=["intent_type"],
        )

        logger.info(
            "IntentMetrics initialized",
            enabled=True,
            buckets=LATENCY_BUCKETS,
            intent_types=INTENT_TYPES,
        )

    @property
    def enabled(self) -> bool:
        """Check if intent metrics are enabled."""
        return self._enabled

    def observe_latency(self, intent_type: str, latency_seconds: float) -> None:
        """
        Observe a query latency for the given intent type.

        Records the latency in the histogram and increments the query counter.
        Thread-safe and non-blocking.

        Args:
            intent_type: The detected intent type (e.g., "VECTOR_HEAVY", "HYBRID")
            latency_seconds: Query execution time in seconds

        Example:
            >>> metrics = IntentMetrics()
            >>> metrics.observe_latency("VECTOR_HEAVY", 0.150)
        """
        if not self._enabled:
            return

        # Normalize intent type to uppercase
        normalized_intent = intent_type.upper() if intent_type else "HYBRID"

        # Validate intent type, default to HYBRID for unknown types
        if normalized_intent not in INTENT_TYPES:
            logger.warning(
                "Unknown intent type, defaulting to HYBRID",
                original_intent=intent_type,
            )
            normalized_intent = "HYBRID"

        with self._lock:
            try:
                if self._latency_histogram is not None:
                    self._latency_histogram.labels(intent_type=normalized_intent).observe(
                        latency_seconds
                    )
                if self._query_counter is not None:
                    self._query_counter.labels(intent_type=normalized_intent).inc()

                logger.debug(
                    "Intent latency observed",
                    intent_type=normalized_intent,
                    latency_seconds=round(latency_seconds, 4),
                )
            except Exception as e:
                # Never let metrics observation fail the actual query
                logger.warning(
                    "Failed to observe intent latency",
                    error=str(e),
                    intent_type=normalized_intent,
                )

    def get_stats(self) -> dict[str, Any]:
        """
        Get current metrics statistics.

        Returns:
            Dictionary with enabled status and intent types tracked
        """
        return {
            "enabled": self._enabled,
            "intent_types": list(INTENT_TYPES),
            "buckets": list(LATENCY_BUCKETS),
        }


# Global singleton instance
_intent_metrics: IntentMetrics | None = None
_metrics_lock = threading.Lock()


def get_intent_metrics() -> IntentMetrics:
    """
    Get the global IntentMetrics instance (singleton).

    Returns:
        IntentMetrics instance
    """
    global _intent_metrics

    with _metrics_lock:
        if _intent_metrics is None:
            _intent_metrics = IntentMetrics()
        return _intent_metrics


def reset_intent_metrics() -> None:
    """Reset the global IntentMetrics instance (for testing)."""
    global _intent_metrics
    with _metrics_lock:
        _intent_metrics = None
