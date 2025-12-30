"""
Cache metrics collector for Prometheus.

Exports cache statistics (hit rate, miss rate, eviction count, current size)
as Prometheus gauges and counters for observability.
"""

import threading
from typing import Any

import structlog
from prometheus_client import REGISTRY, Counter, Gauge

from src.config import get_settings

logger = structlog.get_logger(__name__)


def _get_or_create_metric(
    metric_class: type[Counter] | type[Gauge],
    name: str,
    description: str,
    labelnames: list[str] | None = None,
    registry: Any = REGISTRY,
) -> Any:
    """
    Get existing metric or create new one to avoid duplicates.

    Args:
        metric_class: Prometheus metric class (Counter, Gauge)
        name: Metric name
        description: Metric description
        labelnames: Optional label names
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


class CacheMetricsCollector:
    """
    Collects cache statistics and exports them to Prometheus.

    Creates gauges and counters for:
    - Cache hits (counter)
    - Cache misses (counter)
    - Cache evictions (counter)
    - Cache hit rate (gauge, percentage)
    - Current cache size (gauge)

    All metrics are labeled by cache_type for granular visibility.
    """

    def __init__(self) -> None:
        """Initialize cache metrics collector with Prometheus metrics."""
        settings = get_settings()

        if not settings.cache_metrics_enabled:
            logger.info("Cache metrics disabled via configuration")
            self._enabled = False
            return

        self._enabled = True
        self._lock = threading.Lock()

        # Counters for cache operations
        self._hits_counter = _get_or_create_metric(
            Counter,
            "agentic_rag_cache_hits_total",
            "Total cache hits",
            labelnames=["cache_type"],
        )

        self._misses_counter = _get_or_create_metric(
            Counter,
            "agentic_rag_cache_misses_total",
            "Total cache misses",
            labelnames=["cache_type"],
        )

        self._evictions_counter = _get_or_create_metric(
            Counter,
            "agentic_rag_cache_evictions_total",
            "Total cache evictions",
            labelnames=["cache_type"],
        )

        # Gauges for current state
        self._hit_rate_gauge = _get_or_create_metric(
            Gauge,
            "agentic_rag_cache_hit_rate_percent",
            "Cache hit rate percentage",
            labelnames=["cache_type"],
        )

        self._size_gauge = _get_or_create_metric(
            Gauge,
            "agentic_rag_cache_current_size",
            "Current number of entries in cache",
            labelnames=["cache_type"],
        )

        logger.info("CacheMetricsCollector initialized", enabled=True)

    @property
    def enabled(self) -> bool:
        """Check if cache metrics are enabled."""
        return self._enabled

    def collect(self, cache_stats: dict[str, Any]) -> None:
        """
        Collect and export cache statistics to Prometheus.

        This method should be called periodically or after cache operations
        to update Prometheus metrics with current cache state.

        Args:
            cache_stats: Dictionary from QueryCache.get_prometheus_stats()
                Expected structure per cache type:
                {
                    "cache_type": {
                        "hits": int,
                        "misses": int,
                        "evictions": int,
                        "hit_rate_percent": float,
                        "current_size": int,
                    },
                    ...
                }

        Example:
            >>> collector = CacheMetricsCollector()
            >>> cache = get_query_cache()
            >>> collector.collect(cache.get_prometheus_stats())
        """
        if not self._enabled:
            return

        with self._lock:
            try:
                for cache_type, stats in cache_stats.items():
                    if not isinstance(stats, dict):
                        continue

                    # Update counters (these are monotonically increasing)
                    # Note: We set to current value, Prometheus handles diffs
                    hits = stats.get("hits", 0)
                    misses = stats.get("misses", 0)
                    evictions = stats.get("evictions", 0)

                    # For counters, we need to track deltas
                    # Instead, we'll use the raw values and let consumers calculate rates
                    if self._hits_counter is not None:
                        self._hits_counter.labels(cache_type=cache_type)._value.set(hits)

                    if self._misses_counter is not None:
                        self._misses_counter.labels(cache_type=cache_type)._value.set(misses)

                    if self._evictions_counter is not None:
                        self._evictions_counter.labels(cache_type=cache_type)._value.set(evictions)

                    # Update gauges
                    hit_rate = stats.get("hit_rate_percent", 0.0)
                    if self._hit_rate_gauge is not None:
                        self._hit_rate_gauge.labels(cache_type=cache_type).set(hit_rate)

                    current_size = stats.get("current_size", 0)
                    if self._size_gauge is not None:
                        self._size_gauge.labels(cache_type=cache_type).set(current_size)

                logger.debug(
                    "Cache metrics collected",
                    cache_types=list(cache_stats.keys()),
                )

            except Exception as e:
                logger.warning("Failed to collect cache metrics", error=str(e))

    def get_stats(self) -> dict[str, Any]:
        """
        Get current collector statistics.

        Returns:
            Dictionary with enabled status
        """
        return {"enabled": self._enabled}


# Global singleton instance
_cache_metrics: CacheMetricsCollector | None = None
_metrics_lock = threading.Lock()


def get_cache_metrics() -> CacheMetricsCollector:
    """
    Get the global CacheMetricsCollector instance (singleton).

    Returns:
        CacheMetricsCollector instance
    """
    global _cache_metrics

    with _metrics_lock:
        if _cache_metrics is None:
            _cache_metrics = CacheMetricsCollector()
        return _cache_metrics


def reset_cache_metrics() -> None:
    """Reset the global CacheMetricsCollector instance (for testing)."""
    global _cache_metrics
    with _metrics_lock:
        _cache_metrics = None
