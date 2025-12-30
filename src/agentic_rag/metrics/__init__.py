"""
Performance metrics module for Agentic GraphRAG system.

Provides Prometheus metrics for:
- Intent-specific query latency histograms
- Cache hit/miss/eviction counters
- Memory usage monitoring
- Development profiling utilities

Example:
    from src.agentic_rag.metrics import IntentMetrics, get_intent_metrics

    metrics = get_intent_metrics()
    metrics.observe_latency("VECTOR_HEAVY", 0.150)

Example with profiling:
    from src.agentic_rag.metrics import profile_async

    @profile_async(name="my_search")
    async def search(query: str) -> list:
        return await do_search(query)

Example with memory monitoring:
    from src.agentic_rag.metrics import get_memory_monitor

    monitor = get_memory_monitor()
    await monitor.start()
    # ... application runs ...
    await monitor.stop()
"""

from .cache_metrics import (
    CacheMetricsCollector,
    get_cache_metrics,
    reset_cache_metrics,
)
from .intent_metrics import (
    INTENT_TYPES,
    LATENCY_BUCKETS,
    IntentMetrics,
    get_intent_metrics,
    reset_intent_metrics,
)
from .memory_monitor import (
    MemoryMonitor,
    MemoryStats,
    get_memory_monitor,
    reset_memory_monitor,
)
from .profiler import (
    Profiler,
    ProfileResult,
    profile,
    profile_async,
    profile_sync,
)

__all__ = [
    "INTENT_TYPES",
    "LATENCY_BUCKETS",
    "CacheMetricsCollector",
    "IntentMetrics",
    "MemoryMonitor",
    "MemoryStats",
    "ProfileResult",
    "Profiler",
    "get_cache_metrics",
    "get_intent_metrics",
    "get_memory_monitor",
    "profile",
    "profile_async",
    "profile_sync",
    "reset_cache_metrics",
    "reset_intent_metrics",
    "reset_memory_monitor",
]
