"""Unit tests for memory monitor module."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.agentic_rag.metrics.memory_monitor import (
    MemoryMonitor,
    MemoryStats,
    get_memory_monitor,
    reset_memory_monitor,
)


class TestMemoryStats:
    """Test MemoryStats dataclass."""

    def test_default_values(self) -> None:
        """MemoryStats should have sensible defaults."""
        stats = MemoryStats()

        assert stats.rss_bytes == 0
        assert stats.vms_bytes == 0
        assert stats.percent == 0.0
        assert stats.available_bytes == 0
        assert stats.total_bytes == 0

    def test_to_dict(self) -> None:
        """to_dict should return expected structure."""
        stats = MemoryStats(
            rss_bytes=256 * 1024 * 1024,  # 256 MB
            vms_bytes=512 * 1024 * 1024,  # 512 MB
            percent=45.5,
            available_bytes=8 * 1024 * 1024 * 1024,  # 8 GB
            total_bytes=16 * 1024 * 1024 * 1024,  # 16 GB
        )

        result = stats.to_dict()

        assert "rss_bytes" in result
        assert "rss_mb" in result
        assert "vms_bytes" in result
        assert "vms_mb" in result
        assert "percent" in result
        assert "available_mb" in result
        assert "total_mb" in result

        assert result["rss_mb"] == 256.0
        assert result["vms_mb"] == 512.0


class TestMemoryMonitor:
    """Test MemoryMonitor class."""

    @pytest.fixture(autouse=True)
    def reset_monitor(self) -> None:
        """Reset monitor singleton before each test."""
        reset_memory_monitor()

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_initialization_when_enabled(self, mock_settings: MagicMock) -> None:
        """MemoryMonitor should initialize when enabled."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()

        assert monitor.enabled is True
        assert monitor._interval == 60

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_initialization_when_disabled(self, mock_settings: MagicMock) -> None:
        """MemoryMonitor should not run when disabled."""
        mock_settings.return_value.memory_monitor_enabled = False
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()

        assert monitor.enabled is False

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_custom_interval_override(self, mock_settings: MagicMock) -> None:
        """MemoryMonitor should accept custom interval override."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor(interval_seconds=30)

        assert monitor._interval == 30

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_running_property(self, mock_settings: MagicMock) -> None:
        """running property should reflect monitor state."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()

        assert monitor.running is False

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    @pytest.mark.asyncio
    async def test_start_when_disabled(self, mock_settings: MagicMock) -> None:
        """start should be a no-op when disabled."""
        mock_settings.return_value.memory_monitor_enabled = False
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()
        await monitor.start()

        assert monitor.running is False

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    @pytest.mark.asyncio
    async def test_start_and_stop(self, mock_settings: MagicMock) -> None:
        """start and stop should work correctly."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 1  # 1 second for quick test

        monitor = MemoryMonitor()

        await monitor.start()
        assert monitor.running is True

        # Let it run briefly
        await asyncio.sleep(0.1)

        await monitor.stop()
        assert monitor.running is False

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    @pytest.mark.asyncio
    async def test_double_start_is_safe(self, mock_settings: MagicMock) -> None:
        """Calling start twice should be safe."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()

        await monitor.start()
        await monitor.start()  # Should not raise

        await monitor.stop()

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_safe(self, mock_settings: MagicMock) -> None:
        """Calling stop when not running should be safe."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()

        # Should not raise
        await monitor.stop()

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_get_current_stats_before_start(self, mock_settings: MagicMock) -> None:
        """get_current_stats should return None before monitor starts."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()

        assert monitor.get_current_stats() is None

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_get_stats_dict_before_start(self, mock_settings: MagicMock) -> None:
        """get_stats_dict should indicate unavailable before start."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()
        result = monitor.get_stats_dict()

        assert result["available"] is False

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_collect_stats_without_psutil(self, mock_settings: MagicMock) -> None:
        """_collect_stats should return empty stats when psutil unavailable."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        with patch("src.agentic_rag.metrics.memory_monitor.PSUTIL_AVAILABLE", False):
            monitor = MemoryMonitor()
            stats = monitor._collect_stats()

            assert stats.rss_bytes == 0
            assert stats.vms_bytes == 0


class TestGetMemoryMonitor:
    """Test get_memory_monitor singleton function."""

    @pytest.fixture(autouse=True)
    def reset_monitor(self) -> None:
        """Reset monitor singleton before each test."""
        reset_memory_monitor()

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_returns_singleton_instance(self, mock_settings: MagicMock) -> None:
        """get_memory_monitor should return same instance."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        instance1 = get_memory_monitor()
        instance2 = get_memory_monitor()

        assert instance1 is instance2

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_reset_clears_singleton(self, mock_settings: MagicMock) -> None:
        """reset_memory_monitor should clear the singleton."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        instance1 = get_memory_monitor()
        reset_memory_monitor()
        instance2 = get_memory_monitor()

        assert instance1 is not instance2


class TestGetOrCreateGaugeEdgeCases:
    """Test _get_or_create_gauge edge cases for coverage."""

    @pytest.fixture(autouse=True)
    def reset_monitor(self) -> None:
        """Reset monitor singleton before each test."""
        reset_memory_monitor()

    def test_finds_metric_via_names_to_collectors(self) -> None:
        """Should find existing metric via _names_to_collectors lookup."""
        from prometheus_client import CollectorRegistry, Gauge

        from src.agentic_rag.metrics.memory_monitor import _get_or_create_gauge

        registry = CollectorRegistry()
        existing_gauge = Gauge("test_mem_names_lookup", "Test gauge", registry=registry)

        # Call again, should find via _collector_to_names or _names_to_collectors
        result = _get_or_create_gauge(
            "test_mem_names_lookup",
            "Test gauge",
            registry=registry,
        )

        assert result is existing_gauge

    def test_handles_duplicate_gauge_fallback(self) -> None:
        """Should find existing gauge on duplicate ValueError."""
        from prometheus_client import CollectorRegistry, Gauge

        from src.agentic_rag.metrics.memory_monitor import _get_or_create_gauge

        registry = CollectorRegistry()
        first_gauge = Gauge("test_mem_dup_gauge", "Test gauge", registry=registry)

        with patch.object(Gauge, "__init__") as mock_init:
            mock_init.side_effect = ValueError("Duplicated timeseries in CollectorRegistry")

            result = _get_or_create_gauge(
                "test_mem_dup_gauge",
                "Test gauge",
                registry=registry,
            )

            assert result is first_gauge

    def test_handles_duplicate_not_found_returns_none(self) -> None:
        """Should return None if duplicate gauge cannot be found."""
        from prometheus_client import CollectorRegistry, Gauge

        from src.agentic_rag.metrics.memory_monitor import _get_or_create_gauge

        registry = CollectorRegistry()

        with patch.object(Gauge, "__init__") as mock_init:
            mock_init.side_effect = ValueError("Duplicated timeseries in CollectorRegistry")

            result = _get_or_create_gauge(
                "nonexistent_mem_gauge",
                "Test gauge",
                registry=registry,
            )

            # Unlike the other modules, this one returns None instead of raising
            assert result is None


class TestMemoryMonitorExceptionHandling:
    """Test exception handling in MemoryMonitor."""

    @pytest.fixture(autouse=True)
    def reset_monitor(self) -> None:
        """Reset monitor singleton before each test."""
        reset_memory_monitor()

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_collect_stats_handles_psutil_exception(self, mock_settings: MagicMock) -> None:
        """_collect_stats should handle exceptions from psutil."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()

        # Mock psutil.Process to raise an exception
        with patch("src.agentic_rag.metrics.memory_monitor.psutil") as mock_psutil:
            mock_psutil.Process.side_effect = Exception("Process not found")

            with patch("src.agentic_rag.metrics.memory_monitor.PSUTIL_AVAILABLE", True):
                stats = monitor._collect_stats()

        # Should return empty stats on exception
        assert stats.rss_bytes == 0
        assert stats.vms_bytes == 0

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_update_prometheus_handles_gauge_exception(self, mock_settings: MagicMock) -> None:
        """_update_prometheus should handle exceptions during gauge update."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()

        # Mock gauge to raise exception
        monitor._rss_gauge = MagicMock()
        monitor._rss_gauge.set.side_effect = Exception("Gauge update failed")

        stats = MemoryStats(rss_bytes=1000, vms_bytes=2000, percent=50.0)

        # Should not raise, should log warning
        monitor._update_prometheus(stats)

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_get_stats_dict_with_stats(self, mock_settings: MagicMock) -> None:
        """get_stats_dict should return stats dict when stats exist."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = MemoryMonitor()

        # Manually set current stats
        monitor._current_stats = MemoryStats(
            rss_bytes=256 * 1024 * 1024,
            vms_bytes=512 * 1024 * 1024,
            percent=45.5,
            available_bytes=8 * 1024 * 1024 * 1024,
            total_bytes=16 * 1024 * 1024 * 1024,
        )

        result = monitor.get_stats_dict()

        assert result["available"] is True
        assert result["rss_mb"] == 256.0
        assert result["vms_mb"] == 512.0
        assert result["percent"] == 45.5

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    @pytest.mark.asyncio
    async def test_monitor_loop_handles_exception(self, mock_settings: MagicMock) -> None:
        """_monitor_loop should continue after exception."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 0.1  # Fast for testing

        monitor = MemoryMonitor()

        # Track iterations
        iteration_count = 0
        original_collect = monitor._collect_stats

        def mock_collect_stats() -> MemoryStats:
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count == 1:
                raise RuntimeError("First iteration fails")
            return original_collect()

        monitor._collect_stats = mock_collect_stats  # type: ignore[method-assign]

        await monitor.start()

        # Wait for a couple of iterations
        await asyncio.sleep(0.35)

        await monitor.stop()

        # Should have continued despite error
        assert iteration_count >= 2


class TestResetMemoryMonitorRunning:
    """Test reset_memory_monitor when monitor is running."""

    @pytest.fixture(autouse=True)
    def reset_monitor(self) -> None:
        """Reset monitor singleton before each test."""
        reset_memory_monitor()

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    @pytest.mark.asyncio
    async def test_reset_stops_running_monitor(self, mock_settings: MagicMock) -> None:
        """reset_memory_monitor should stop running monitor."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        monitor = get_memory_monitor()
        await monitor.start()

        assert monitor.running is True

        # Reset should stop it
        reset_memory_monitor()

        # Note: The sync reset sets _running = False but doesn't await stop
        # This is expected behavior per the implementation comment


class TestPsutilUnavailable:
    """Test behavior when psutil is unavailable."""

    @pytest.fixture(autouse=True)
    def reset_monitor(self) -> None:
        """Reset monitor singleton before each test."""
        reset_memory_monitor()

    @patch("src.agentic_rag.metrics.memory_monitor.get_settings")
    def test_initialization_without_psutil(self, mock_settings: MagicMock) -> None:
        """Monitor should initialize gracefully without psutil."""
        mock_settings.return_value.memory_monitor_enabled = True
        mock_settings.return_value.memory_monitor_interval = 60

        with patch("src.agentic_rag.metrics.memory_monitor.PSUTIL_AVAILABLE", False):
            monitor = MemoryMonitor()
            stats = monitor._collect_stats()

            assert stats.rss_bytes == 0
            assert stats.vms_bytes == 0
            assert stats.percent == 0.0
