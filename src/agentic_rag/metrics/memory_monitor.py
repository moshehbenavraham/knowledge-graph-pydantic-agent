"""
Periodic memory usage monitoring with Prometheus integration.

Provides a background async task that logs memory usage at configurable
intervals and exports metrics to Prometheus.
"""

import asyncio
import threading
from typing import Any

import structlog
from prometheus_client import REGISTRY, Gauge

from src.config import get_settings

logger = structlog.get_logger(__name__)

# Attempt to import psutil, gracefully handle if unavailable
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, memory monitoring will be limited")


def _get_or_create_gauge(
    name: str,
    description: str,
    registry: Any = REGISTRY,
) -> Gauge | None:
    """Get existing gauge or create new one."""
    try:
        for collector in list(registry._collector_to_names.keys()):
            collector_name = getattr(collector, "_name", None)
            if collector_name == name:
                return collector

        if hasattr(registry, "_names_to_collectors"):
            for registered_name, collector in registry._names_to_collectors.items():
                if registered_name == name:
                    return collector
    except (AttributeError, KeyError, RuntimeError):
        pass

    try:
        return Gauge(name, description, registry=registry)
    except ValueError as e:
        if "Duplicated" in str(e):
            for collector in list(registry._collector_to_names.keys()):
                if getattr(collector, "_name", None) == name:
                    return collector
        return None


class MemoryStats:
    """Container for memory statistics."""

    __slots__ = (
        "available_bytes",
        "percent",
        "rss_bytes",
        "total_bytes",
        "vms_bytes",
    )

    def __init__(
        self,
        rss_bytes: int = 0,
        vms_bytes: int = 0,
        percent: float = 0.0,
        available_bytes: int = 0,
        total_bytes: int = 0,
    ) -> None:
        """
        Initialize memory statistics.

        Args:
            rss_bytes: Resident Set Size (physical memory used by process)
            vms_bytes: Virtual Memory Size (total virtual memory)
            percent: Percentage of total system memory used
            available_bytes: Available system memory
            total_bytes: Total system memory
        """
        self.rss_bytes = rss_bytes
        self.vms_bytes = vms_bytes
        self.percent = percent
        self.available_bytes = available_bytes
        self.total_bytes = total_bytes

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rss_bytes": self.rss_bytes,
            "rss_mb": round(self.rss_bytes / (1024 * 1024), 2),
            "vms_bytes": self.vms_bytes,
            "vms_mb": round(self.vms_bytes / (1024 * 1024), 2),
            "percent": round(self.percent, 2),
            "available_mb": round(self.available_bytes / (1024 * 1024), 2),
            "total_mb": round(self.total_bytes / (1024 * 1024), 2),
        }


class MemoryMonitor:
    """
    Async background task for periodic memory usage monitoring.

    Collects memory statistics at configurable intervals and:
    - Logs memory usage at INFO level using structlog
    - Exports metrics to Prometheus gauges
    - Provides current stats via get_current_stats()

    Non-blocking and handles psutil unavailability gracefully.
    """

    def __init__(self, interval_seconds: int | None = None) -> None:
        """
        Initialize memory monitor.

        Args:
            interval_seconds: Override default interval from settings
        """
        settings = get_settings()

        self._enabled = settings.memory_monitor_enabled
        self._interval = interval_seconds or settings.memory_monitor_interval
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._lock = threading.Lock()
        self._current_stats: MemoryStats | None = None

        # Initialize Prometheus gauges
        self._rss_gauge: Gauge | None = None
        self._vms_gauge: Gauge | None = None
        self._percent_gauge: Gauge | None = None

        if self._enabled:
            self._rss_gauge = _get_or_create_gauge(
                "agentic_rag_memory_rss_bytes",
                "Process resident set size in bytes",
            )
            self._vms_gauge = _get_or_create_gauge(
                "agentic_rag_memory_vms_bytes",
                "Process virtual memory size in bytes",
            )
            self._percent_gauge = _get_or_create_gauge(
                "agentic_rag_memory_percent",
                "System memory usage percentage",
            )

        logger.info(
            "MemoryMonitor initialized",
            enabled=self._enabled,
            interval_seconds=self._interval,
            psutil_available=PSUTIL_AVAILABLE,
        )

    @property
    def enabled(self) -> bool:
        """Check if memory monitoring is enabled."""
        return self._enabled

    @property
    def running(self) -> bool:
        """Check if monitor is currently running."""
        return self._running

    def _collect_stats(self) -> MemoryStats:
        """
        Collect current memory statistics.

        Returns:
            MemoryStats with current memory information
        """
        if not PSUTIL_AVAILABLE:
            return MemoryStats()

        try:
            # Get process memory info
            process = psutil.Process()
            mem_info = process.memory_info()

            # Get system memory info
            virtual_mem = psutil.virtual_memory()

            return MemoryStats(
                rss_bytes=mem_info.rss,
                vms_bytes=mem_info.vms,
                percent=virtual_mem.percent,
                available_bytes=virtual_mem.available,
                total_bytes=virtual_mem.total,
            )

        except Exception as e:
            logger.warning("Failed to collect memory stats", error=str(e))
            return MemoryStats()

    def _update_prometheus(self, stats: MemoryStats) -> None:
        """Update Prometheus gauges with current stats."""
        try:
            if self._rss_gauge is not None:
                self._rss_gauge.set(stats.rss_bytes)
            if self._vms_gauge is not None:
                self._vms_gauge.set(stats.vms_bytes)
            if self._percent_gauge is not None:
                self._percent_gauge.set(stats.percent)
        except Exception as e:
            logger.warning("Failed to update Prometheus metrics", error=str(e))

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        logger.info("Memory monitor loop starting", interval=self._interval)

        while self._running:
            try:
                # Collect stats (run in thread pool to avoid blocking)
                loop = asyncio.get_running_loop()
                stats = await loop.run_in_executor(None, self._collect_stats)

                with self._lock:
                    self._current_stats = stats

                # Update Prometheus
                self._update_prometheus(stats)

                # Log at INFO level with numeric fields for aggregation
                logger.info(
                    "Memory usage",
                    rss_mb=round(stats.rss_bytes / (1024 * 1024), 2),
                    vms_mb=round(stats.vms_bytes / (1024 * 1024), 2),
                    system_percent=round(stats.percent, 1),
                    available_mb=round(stats.available_bytes / (1024 * 1024), 2),
                )

                # Wait for next interval
                await asyncio.sleep(self._interval)

            except asyncio.CancelledError:
                logger.info("Memory monitor loop cancelled")
                break
            except Exception as e:
                logger.exception("Error in memory monitor loop", error=str(e))
                # Continue monitoring despite errors
                await asyncio.sleep(self._interval)

        logger.info("Memory monitor loop stopped")

    async def start(self) -> None:
        """Start the background monitoring task."""
        if not self._enabled:
            logger.info("Memory monitor disabled, not starting")
            return

        if self._running:
            logger.warning("Memory monitor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Memory monitor started", interval=self._interval)

    async def stop(self) -> None:
        """Stop the background monitoring task."""
        if not self._running:
            return

        self._running = False

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Memory monitor stopped")

    def get_current_stats(self) -> MemoryStats | None:
        """
        Get the most recently collected memory statistics.

        Returns:
            MemoryStats or None if no stats collected yet
        """
        with self._lock:
            return self._current_stats

    def get_stats_dict(self) -> dict[str, Any]:
        """
        Get current stats as dictionary.

        Returns:
            Dictionary with memory statistics
        """
        stats = self.get_current_stats()
        if stats is None:
            return {"available": False}

        result = stats.to_dict()
        result["available"] = True
        return result


# Global singleton instance
_memory_monitor: MemoryMonitor | None = None
_monitor_lock = threading.Lock()


def get_memory_monitor() -> MemoryMonitor:
    """
    Get the global MemoryMonitor instance (singleton).

    Returns:
        MemoryMonitor instance
    """
    global _memory_monitor

    with _monitor_lock:
        if _memory_monitor is None:
            _memory_monitor = MemoryMonitor()
        return _memory_monitor


def reset_memory_monitor() -> None:
    """Reset the global MemoryMonitor instance (for testing)."""
    global _memory_monitor
    with _monitor_lock:
        if _memory_monitor is not None and _memory_monitor.running:
            # Note: This is sync, caller should handle async stop if needed
            _memory_monitor._running = False
        _memory_monitor = None
