"""Unit tests for cache metrics module."""

from unittest.mock import MagicMock, patch

import pytest

from src.agentic_rag.metrics.cache_metrics import (
    CacheMetricsCollector,
    get_cache_metrics,
    reset_cache_metrics,
)


class TestCacheMetricsCollector:
    """Test CacheMetricsCollector class."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self) -> None:
        """Reset metrics singleton before each test."""
        reset_cache_metrics()

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_initialization_when_enabled(self, mock_settings: MagicMock) -> None:
        """CacheMetricsCollector should initialize when enabled."""
        mock_settings.return_value.cache_metrics_enabled = True

        collector = CacheMetricsCollector()

        assert collector.enabled is True
        assert collector._hits_counter is not None
        assert collector._misses_counter is not None
        assert collector._evictions_counter is not None
        assert collector._hit_rate_gauge is not None
        assert collector._size_gauge is not None

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_initialization_when_disabled(self, mock_settings: MagicMock) -> None:
        """CacheMetricsCollector should not initialize when disabled."""
        mock_settings.return_value.cache_metrics_enabled = False

        collector = CacheMetricsCollector()

        assert collector.enabled is False

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_collect_when_enabled(self, mock_settings: MagicMock) -> None:
        """collect should update metrics when enabled."""
        mock_settings.return_value.cache_metrics_enabled = True

        collector = CacheMetricsCollector()

        stats = {
            "hybrid": {
                "hits": 100,
                "misses": 20,
                "evictions": 5,
                "hit_rate_percent": 83.33,
                "current_size": 50,
            },
            "vector": {
                "hits": 50,
                "misses": 10,
                "evictions": 2,
                "hit_rate_percent": 83.33,
                "current_size": 25,
            },
        }

        # Should not raise
        collector.collect(stats)

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_collect_when_disabled(self, mock_settings: MagicMock) -> None:
        """collect should be a no-op when disabled."""
        mock_settings.return_value.cache_metrics_enabled = False

        collector = CacheMetricsCollector()

        stats = {
            "hybrid": {
                "hits": 100,
                "misses": 20,
                "evictions": 5,
                "hit_rate_percent": 83.33,
                "current_size": 50,
            },
        }

        # Should not raise
        collector.collect(stats)

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_collect_handles_empty_stats(self, mock_settings: MagicMock) -> None:
        """collect should handle empty stats dictionary."""
        mock_settings.return_value.cache_metrics_enabled = True

        collector = CacheMetricsCollector()

        # Should not raise
        collector.collect({})

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_collect_handles_invalid_stats_format(self, mock_settings: MagicMock) -> None:
        """collect should handle invalid stats format gracefully."""
        mock_settings.return_value.cache_metrics_enabled = True

        collector = CacheMetricsCollector()

        # Non-dict values should be skipped
        stats = {
            "hybrid": "invalid",  # Not a dict
            "vector": None,  # None value
        }

        # Should not raise
        collector.collect(stats)  # type: ignore[arg-type]

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_get_stats_returns_expected_structure(self, mock_settings: MagicMock) -> None:
        """get_stats should return expected dictionary structure."""
        mock_settings.return_value.cache_metrics_enabled = True

        collector = CacheMetricsCollector()
        stats = collector.get_stats()

        assert "enabled" in stats
        assert stats["enabled"] is True


class TestGetCacheMetrics:
    """Test get_cache_metrics singleton function."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self) -> None:
        """Reset metrics singleton before each test."""
        reset_cache_metrics()

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_returns_singleton_instance(self, mock_settings: MagicMock) -> None:
        """get_cache_metrics should return same instance."""
        mock_settings.return_value.cache_metrics_enabled = True

        instance1 = get_cache_metrics()
        instance2 = get_cache_metrics()

        assert instance1 is instance2

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_reset_clears_singleton(self, mock_settings: MagicMock) -> None:
        """reset_cache_metrics should clear the singleton."""
        mock_settings.return_value.cache_metrics_enabled = True

        instance1 = get_cache_metrics()
        reset_cache_metrics()
        instance2 = get_cache_metrics()

        assert instance1 is not instance2


class TestCacheMetricsThreadSafety:
    """Test thread safety of CacheMetricsCollector."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self) -> None:
        """Reset metrics singleton before each test."""
        reset_cache_metrics()

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_concurrent_collections(self, mock_settings: MagicMock) -> None:
        """Multiple concurrent collections should not cause errors."""
        import threading

        mock_settings.return_value.cache_metrics_enabled = True

        collector = CacheMetricsCollector()
        errors: list[Exception] = []

        stats = {
            "hybrid": {
                "hits": 100,
                "misses": 20,
                "evictions": 5,
                "hit_rate_percent": 83.33,
                "current_size": 50,
            },
        }

        def collect_many() -> None:
            try:
                for _ in range(100):
                    collector.collect(stats)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=collect_many) for _ in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestGetOrCreateMetricEdgeCases:
    """Test _get_or_create_metric edge cases for coverage."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self) -> None:
        """Reset metrics singleton before each test."""
        reset_cache_metrics()

    def test_handles_registry_attribute_error(self) -> None:
        """Should handle AttributeError when checking registry."""
        from prometheus_client import Counter

        from src.agentic_rag.metrics.cache_metrics import _get_or_create_metric

        # Create a mock registry that raises AttributeError
        mock_registry = MagicMock()
        mock_registry._collector_to_names = MagicMock()
        mock_registry._collector_to_names.keys.side_effect = AttributeError("test")

        # Should not raise, should create new metric
        metric = _get_or_create_metric(
            Counter,
            "test_attr_error_counter",
            "Test counter",
            registry=mock_registry,
        )

        assert metric is not None

    def test_handles_registry_runtime_error(self) -> None:
        """Should handle RuntimeError when checking registry."""
        from prometheus_client import Counter

        from src.agentic_rag.metrics.cache_metrics import _get_or_create_metric

        mock_registry = MagicMock()
        mock_registry._collector_to_names = MagicMock()
        mock_registry._collector_to_names.keys.side_effect = RuntimeError("test")

        metric = _get_or_create_metric(
            Counter,
            "test_runtime_error_counter",
            "Test counter",
            registry=mock_registry,
        )

        assert metric is not None

    def test_handles_duplicate_metric_fallback(self) -> None:
        """Should find existing metric on duplicate ValueError."""
        from prometheus_client import CollectorRegistry, Counter

        from src.agentic_rag.metrics.cache_metrics import _get_or_create_metric

        registry = CollectorRegistry()

        # Create the metric first
        first_metric = Counter("test_dup_fallback", "Test counter", registry=registry)

        # Mock the registry to simulate duplicate error scenario
        original_keys = registry._collector_to_names.keys

        def mock_keys_then_succeed() -> list:
            # First call returns empty, second call returns actual
            return list(original_keys())

        # Patch to force ValueError path and then fallback search
        with patch.object(Counter, "__init__") as mock_init:
            mock_init.side_effect = ValueError("Duplicated timeseries in CollectorRegistry")

            # This should trigger the fallback search in the ValueError handler
            result = _get_or_create_metric(
                Counter,
                "test_dup_fallback",
                "Test counter",
                registry=registry,
            )

            # Should return the existing metric
            assert result is first_metric

    def test_handles_duplicate_metric_not_found_raises(self) -> None:
        """Should raise RuntimeError if duplicate metric cannot be found."""
        from prometheus_client import CollectorRegistry, Counter

        from src.agentic_rag.metrics.cache_metrics import _get_or_create_metric

        registry = CollectorRegistry()

        # Empty registry but ValueError claims duplicate
        with patch.object(Counter, "__init__") as mock_init:
            mock_init.side_effect = ValueError("Duplicated timeseries in CollectorRegistry")

            with pytest.raises(RuntimeError, match="registration conflict"):
                _get_or_create_metric(
                    Counter,
                    "nonexistent_metric",
                    "Test counter",
                    registry=registry,
                )

    def test_handles_non_duplicate_value_error(self) -> None:
        """Should re-raise non-duplicate ValueError."""
        from prometheus_client import CollectorRegistry, Counter

        from src.agentic_rag.metrics.cache_metrics import _get_or_create_metric

        registry = CollectorRegistry()

        with patch.object(Counter, "__init__") as mock_init:
            mock_init.side_effect = ValueError("Some other error")

            with pytest.raises(ValueError, match="Some other error"):
                _get_or_create_metric(
                    Counter,
                    "error_metric",
                    "Test counter",
                    registry=registry,
                )


class TestCacheMetricsCollectorExceptionHandling:
    """Test exception handling in CacheMetricsCollector."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self) -> None:
        """Reset metrics singleton before each test."""
        reset_cache_metrics()

    @patch("src.agentic_rag.metrics.cache_metrics.get_settings")
    def test_collect_handles_metric_update_exception(self, mock_settings: MagicMock) -> None:
        """collect should handle exceptions during metric updates."""
        mock_settings.return_value.cache_metrics_enabled = True

        collector = CacheMetricsCollector()

        # Mock a counter to raise an exception
        collector._hits_counter = MagicMock()
        collector._hits_counter.labels.side_effect = Exception("Metric update failed")

        stats = {
            "hybrid": {
                "hits": 100,
                "misses": 20,
                "evictions": 5,
                "hit_rate_percent": 83.33,
                "current_size": 50,
            },
        }

        # Should not raise, should log warning
        collector.collect(stats)
