"""Unit tests for intent metrics module."""

from unittest.mock import MagicMock, patch

import pytest

from src.agentic_rag.metrics.intent_metrics import (
    INTENT_TYPES,
    LATENCY_BUCKETS,
    IntentMetrics,
    _get_or_create_metric,
    get_intent_metrics,
    reset_intent_metrics,
)


class TestIntentMetricsConstants:
    """Test intent metrics constants."""

    def test_latency_buckets_are_ordered(self) -> None:
        """Latency buckets should be in ascending order."""
        buckets = list(LATENCY_BUCKETS)
        assert buckets == sorted(buckets)

    def test_latency_buckets_cover_expected_range(self) -> None:
        """Latency buckets should cover 50ms to 10s range."""
        assert LATENCY_BUCKETS[0] == 0.05  # 50ms
        assert LATENCY_BUCKETS[-1] == 10.0  # 10s

    def test_intent_types_includes_all_search_intents(self) -> None:
        """Intent types should include all Phase 02 search intents."""
        expected = {
            "VECTOR_HEAVY",
            "GRAPH_HEAVY",
            "HYBRID",
            "TEMPORAL",
            "ENTITY_FOCUSED",
            "MULTI_HOP",
            "TEMPORAL_TREND",
            "COMPARISON",
        }
        assert set(INTENT_TYPES) == expected


class TestIntentMetrics:
    """Test IntentMetrics class."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self) -> None:
        """Reset metrics singleton before each test."""
        reset_intent_metrics()

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_initialization_when_enabled(self, mock_settings: MagicMock) -> None:
        """IntentMetrics should initialize when enabled."""
        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()

        assert metrics.enabled is True
        assert metrics._latency_histogram is not None
        assert metrics._query_counter is not None

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_initialization_when_disabled(self, mock_settings: MagicMock) -> None:
        """IntentMetrics should not initialize metrics when disabled."""
        mock_settings.return_value.intent_metrics_enabled = False

        metrics = IntentMetrics()

        assert metrics.enabled is False
        assert metrics._latency_histogram is None
        assert metrics._query_counter is None

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_observe_latency_when_enabled(self, mock_settings: MagicMock) -> None:
        """observe_latency should record metrics when enabled."""
        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()
        # Should not raise
        metrics.observe_latency("VECTOR_HEAVY", 0.150)

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_observe_latency_when_disabled(self, mock_settings: MagicMock) -> None:
        """observe_latency should be a no-op when disabled."""
        mock_settings.return_value.intent_metrics_enabled = False

        metrics = IntentMetrics()
        # Should not raise
        metrics.observe_latency("VECTOR_HEAVY", 0.150)

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_observe_latency_normalizes_intent_type(self, mock_settings: MagicMock) -> None:
        """observe_latency should normalize intent types to uppercase."""
        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()
        # Should handle lowercase
        metrics.observe_latency("vector_heavy", 0.150)

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_observe_latency_handles_unknown_intent(self, mock_settings: MagicMock) -> None:
        """observe_latency should default unknown intents to HYBRID."""
        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()
        # Unknown intent should default to HYBRID
        metrics.observe_latency("UNKNOWN_INTENT", 0.150)

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_observe_latency_handles_none_intent(self, mock_settings: MagicMock) -> None:
        """observe_latency should handle None intent."""
        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()
        # None should be handled gracefully
        metrics.observe_latency(None, 0.150)  # type: ignore[arg-type]

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_get_stats_returns_expected_structure(self, mock_settings: MagicMock) -> None:
        """get_stats should return expected dictionary structure."""
        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()
        stats = metrics.get_stats()

        assert "enabled" in stats
        assert "intent_types" in stats
        assert "buckets" in stats
        assert stats["enabled"] is True
        assert set(stats["intent_types"]) == set(INTENT_TYPES)
        assert stats["buckets"] == list(LATENCY_BUCKETS)

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_observe_latency_all_intent_types(self, mock_settings: MagicMock) -> None:
        """observe_latency should accept all valid intent types."""
        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()

        for intent_type in INTENT_TYPES:
            # Should not raise
            metrics.observe_latency(intent_type, 0.100)


class TestGetIntentMetrics:
    """Test get_intent_metrics singleton function."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self) -> None:
        """Reset metrics singleton before each test."""
        reset_intent_metrics()

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_returns_singleton_instance(self, mock_settings: MagicMock) -> None:
        """get_intent_metrics should return same instance."""
        mock_settings.return_value.intent_metrics_enabled = True

        instance1 = get_intent_metrics()
        instance2 = get_intent_metrics()

        assert instance1 is instance2

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_reset_clears_singleton(self, mock_settings: MagicMock) -> None:
        """reset_intent_metrics should clear the singleton."""
        mock_settings.return_value.intent_metrics_enabled = True

        instance1 = get_intent_metrics()
        reset_intent_metrics()
        instance2 = get_intent_metrics()

        assert instance1 is not instance2


class TestGetOrCreateMetric:
    """Test _get_or_create_metric helper function."""

    def test_creates_new_metric(self) -> None:
        """Should create a new metric if it does not exist."""
        from prometheus_client import CollectorRegistry, Counter

        registry = CollectorRegistry()
        metric = _get_or_create_metric(
            Counter,
            "test_counter_new",
            "Test counter",
            registry=registry,
        )

        assert metric is not None

    def test_returns_existing_metric(self) -> None:
        """Should return existing metric if it already exists."""
        from prometheus_client import CollectorRegistry, Counter

        registry = CollectorRegistry()

        metric1 = _get_or_create_metric(
            Counter,
            "test_counter_existing",
            "Test counter",
            registry=registry,
        )
        metric2 = _get_or_create_metric(
            Counter,
            "test_counter_existing",
            "Test counter",
            registry=registry,
        )

        assert metric1 is metric2

    def test_handles_labelnames(self) -> None:
        """Should handle metrics with labels."""
        from prometheus_client import CollectorRegistry, Counter

        registry = CollectorRegistry()
        metric = _get_or_create_metric(
            Counter,
            "test_counter_labels",
            "Test counter with labels",
            labelnames=["label1", "label2"],
            registry=registry,
        )

        assert metric is not None


class TestIntentMetricsThreadSafety:
    """Test thread safety of IntentMetrics."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self) -> None:
        """Reset metrics singleton before each test."""
        reset_intent_metrics()

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_concurrent_observations(self, mock_settings: MagicMock) -> None:
        """Multiple concurrent observations should not cause errors."""
        import threading

        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()
        errors: list[Exception] = []

        def observe_many() -> None:
            try:
                for _ in range(100):
                    metrics.observe_latency("VECTOR_HEAVY", 0.1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=observe_many) for _ in range(4)]

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
        reset_intent_metrics()

    def test_handles_registry_attribute_error(self) -> None:
        """Should handle AttributeError when checking registry."""
        from prometheus_client import Histogram

        mock_registry = MagicMock()
        mock_registry._collector_to_names = MagicMock()
        mock_registry._collector_to_names.keys.side_effect = AttributeError("test")

        metric = _get_or_create_metric(
            Histogram,
            "test_intent_attr_error",
            "Test histogram",
            registry=mock_registry,
        )

        assert metric is not None

    def test_handles_registry_key_error(self) -> None:
        """Should handle KeyError when checking registry."""
        from prometheus_client import Histogram

        mock_registry = MagicMock()
        mock_registry._collector_to_names = MagicMock()
        mock_registry._collector_to_names.keys.side_effect = KeyError("test")

        metric = _get_or_create_metric(
            Histogram,
            "test_intent_key_error",
            "Test histogram",
            registry=mock_registry,
        )

        assert metric is not None

    def test_handles_registry_runtime_error(self) -> None:
        """Should handle RuntimeError when checking registry."""
        from prometheus_client import Histogram

        mock_registry = MagicMock()
        mock_registry._collector_to_names = MagicMock()
        mock_registry._collector_to_names.keys.side_effect = RuntimeError("test")

        metric = _get_or_create_metric(
            Histogram,
            "test_intent_runtime_error",
            "Test histogram",
            registry=mock_registry,
        )

        assert metric is not None

    def test_handles_duplicate_histogram_fallback(self) -> None:
        """Should find existing histogram on duplicate ValueError."""
        from prometheus_client import CollectorRegistry, Histogram

        registry = CollectorRegistry()

        first_metric = Histogram("test_intent_dup_hist", "Test histogram", registry=registry)

        with patch.object(Histogram, "__init__") as mock_init:
            mock_init.side_effect = ValueError("Duplicated timeseries in CollectorRegistry")

            result = _get_or_create_metric(
                Histogram,
                "test_intent_dup_hist",
                "Test histogram",
                registry=registry,
            )

            assert result is first_metric

    def test_handles_duplicate_not_found_raises(self) -> None:
        """Should raise RuntimeError if duplicate metric cannot be found."""
        from prometheus_client import CollectorRegistry, Histogram

        registry = CollectorRegistry()

        with patch.object(Histogram, "__init__") as mock_init:
            mock_init.side_effect = ValueError("Duplicated timeseries in CollectorRegistry")

            with pytest.raises(RuntimeError, match="registration conflict"):
                _get_or_create_metric(
                    Histogram,
                    "nonexistent_intent_metric",
                    "Test histogram",
                    registry=registry,
                )

    def test_handles_non_duplicate_value_error(self) -> None:
        """Should re-raise non-duplicate ValueError."""
        from prometheus_client import CollectorRegistry, Histogram

        registry = CollectorRegistry()

        with patch.object(Histogram, "__init__") as mock_init:
            mock_init.side_effect = ValueError("Invalid bucket configuration")

            with pytest.raises(ValueError, match="Invalid bucket"):
                _get_or_create_metric(
                    Histogram,
                    "intent_error_metric",
                    "Test histogram",
                    registry=registry,
                )

    def test_creates_histogram_with_buckets(self) -> None:
        """Should pass buckets to histogram creation."""
        from prometheus_client import CollectorRegistry, Histogram

        registry = CollectorRegistry()
        custom_buckets = (0.1, 0.5, 1.0, 5.0)

        metric = _get_or_create_metric(
            Histogram,
            "test_intent_buckets",
            "Test histogram with buckets",
            buckets=custom_buckets,
            registry=registry,
        )

        assert metric is not None


class TestIntentMetricsObserveLatencyExceptionHandling:
    """Test exception handling in IntentMetrics.observe_latency."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self) -> None:
        """Reset metrics singleton before each test."""
        reset_intent_metrics()

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_observe_latency_handles_histogram_exception(self, mock_settings: MagicMock) -> None:
        """observe_latency should handle exceptions during histogram update."""
        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()

        # Mock histogram to raise exception
        metrics._latency_histogram = MagicMock()
        metrics._latency_histogram.labels.side_effect = Exception("Histogram error")

        # Should not raise, should log warning
        metrics.observe_latency("VECTOR_HEAVY", 0.150)

    @patch("src.agentic_rag.metrics.intent_metrics.get_settings")
    def test_observe_latency_handles_counter_exception(self, mock_settings: MagicMock) -> None:
        """observe_latency should handle exceptions during counter update."""
        mock_settings.return_value.intent_metrics_enabled = True

        metrics = IntentMetrics()

        # Mock counter to raise exception
        metrics._query_counter = MagicMock()
        metrics._query_counter.labels.side_effect = Exception("Counter error")

        # Should not raise, should log warning
        metrics.observe_latency("HYBRID", 0.200)
