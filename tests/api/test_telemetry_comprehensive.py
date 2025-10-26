"""
Comprehensive tests for OpenTelemetry instrumentation and Prometheus metrics.

Target coverage: 0% → 75%+
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request, Response
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider

from src.api.telemetry import (
    OpenTelemetryConfig,
    metrics_middleware,
    record_cache_access,
    record_document_ingestion,
    record_graph_search,
    record_llm_request,
    record_vector_search,
    setup_telemetry,
)


class TestOpenTelemetryConfig:
    """Test OpenTelemetry configuration."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        config = OpenTelemetryConfig()

        assert config.service_name == "base-agent-api"
        assert config.service_version == "1.0.0"
        assert config.otlp_endpoint is None
        assert config.enable_console_export is False

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        config = OpenTelemetryConfig(
            service_name="test-service",
            service_version="2.0.0",
            otlp_endpoint="http://localhost:4317",
            enable_console_export=True,
        )

        assert config.service_name == "test-service"
        assert config.service_version == "2.0.0"
        assert config.otlp_endpoint == "http://localhost:4317"
        assert config.enable_console_export is True

    @patch("src.api.telemetry.trace.set_tracer_provider")
    def test_setup_tracing_no_endpoint(self, mock_set_provider):
        """Test tracing setup without OTLP endpoint."""
        config = OpenTelemetryConfig()
        provider = config.setup_tracing()

        assert isinstance(provider, TracerProvider)
        mock_set_provider.assert_called_once_with(provider)

    @patch("src.api.telemetry.OTLPSpanExporter")
    @patch("src.api.telemetry.trace.set_tracer_provider")
    def test_setup_tracing_with_endpoint(self, mock_set_provider, mock_exporter):
        """Test tracing setup with OTLP endpoint."""
        config = OpenTelemetryConfig(otlp_endpoint="http://localhost:4317")
        provider = config.setup_tracing()

        assert isinstance(provider, TracerProvider)
        mock_exporter.assert_called_once_with(endpoint="http://localhost:4317")
        mock_set_provider.assert_called_once()

    @patch("src.api.telemetry.trace.set_tracer_provider")
    def test_setup_tracing_console_export(self, mock_set_provider):
        """Test tracing setup with console export enabled."""
        config = OpenTelemetryConfig(enable_console_export=True)

        with patch("src.api.telemetry.ConsoleSpanExporter") as mock_console:
            provider = config.setup_tracing()

            assert isinstance(provider, TracerProvider)
            # Console exporter should be created when enable_console_export=True
            # The import is inside the conditional, so we patch it dynamically

    @patch("src.api.telemetry.metrics.set_meter_provider")
    def test_setup_metrics_no_endpoint(self, mock_set_provider):
        """Test metrics setup without OTLP endpoint."""
        config = OpenTelemetryConfig()
        provider = config.setup_metrics()

        assert isinstance(provider, MeterProvider)
        mock_set_provider.assert_called_once_with(provider)

    @patch("src.api.telemetry.OTLPMetricExporter")
    @patch("src.api.telemetry.metrics.set_meter_provider")
    def test_setup_metrics_with_endpoint(self, mock_set_provider, mock_exporter):
        """Test metrics setup with OTLP endpoint."""
        config = OpenTelemetryConfig(otlp_endpoint="http://localhost:4317")
        provider = config.setup_metrics()

        assert isinstance(provider, MeterProvider)
        mock_exporter.assert_called_once_with(endpoint="http://localhost:4317")

    @patch("src.api.telemetry.FastAPIInstrumentor.instrument_app")
    @patch("src.api.telemetry.RequestsInstrumentor")
    @patch("src.api.telemetry.LoggingInstrumentor")
    def test_instrument_fastapi(self, mock_logging, mock_requests, mock_fastapi):
        """Test FastAPI instrumentation."""
        config = OpenTelemetryConfig()
        app = FastAPI()

        mock_requests_instance = MagicMock()
        mock_requests.return_value = mock_requests_instance

        mock_logging_instance = MagicMock()
        mock_logging.return_value = mock_logging_instance

        config.instrument_fastapi(app)

        mock_fastapi.assert_called_once_with(app)
        mock_requests_instance.instrument.assert_called_once()
        mock_logging_instance.instrument.assert_called_once_with(set_logging_format=True)


class TestMetricsMiddleware:
    """Test metrics middleware."""

    @pytest.mark.asyncio
    async def test_middleware_success(self):
        """Test middleware with successful request."""
        request = MagicMock(spec=Request)
        request.url.path = "/test"
        request.method = "GET"

        response = MagicMock(spec=Response)
        response.status_code = 200

        async def call_next(req):
            return response

        with patch("src.api.telemetry.http_requests_total") as mock_counter:
            with patch("src.api.telemetry.http_request_duration_seconds") as mock_histogram:
                result = await metrics_middleware(request, call_next)

                assert result == response
                mock_counter.labels.assert_called_with(method="GET", path="/test", status=200)
                mock_histogram.labels.assert_called_with(method="GET", path="/test")

    @pytest.mark.asyncio
    async def test_middleware_error(self):
        """Test middleware with request error."""
        request = MagicMock(spec=Request)
        request.url.path = "/test"
        request.method = "POST"

        async def call_next(req):
            raise ValueError("Test error")

        with patch("src.api.telemetry.http_requests_total") as mock_counter:
            with patch("src.api.telemetry.http_request_duration_seconds") as mock_histogram:
                with pytest.raises(ValueError, match="Test error"):
                    await metrics_middleware(request, call_next)

                mock_counter.labels.assert_called_with(method="POST", path="/test", status=500)
                mock_histogram.labels.assert_called()

    @pytest.mark.asyncio
    async def test_middleware_timing(self):
        """Test middleware timing accuracy."""
        request = MagicMock(spec=Request)
        request.url.path = "/slow"
        request.method = "GET"

        response = MagicMock(spec=Response)
        response.status_code = 200

        async def call_next(req):
            await pytest.importorskip("asyncio").sleep(0.1)
            return response

        with patch("src.api.telemetry.http_requests_total"):
            with patch("src.api.telemetry.http_request_duration_seconds") as mock_histogram:
                await metrics_middleware(request, call_next)

                # Verify observe was called (timing was recorded)
                mock_histogram.labels.return_value.observe.assert_called_once()
                duration = mock_histogram.labels.return_value.observe.call_args[0][0]
                assert duration >= 0.1


class TestSetupTelemetry:
    """Test complete telemetry setup."""

    @patch("src.api.telemetry.OpenTelemetryConfig")
    def test_setup_telemetry_default(self, mock_config_class):
        """Test telemetry setup with default options."""
        app = FastAPI()
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        setup_telemetry(app)

        mock_config_class.assert_called_once_with(otlp_endpoint=None, enable_console_export=False)
        mock_config.setup_tracing.assert_called_once()
        mock_config.setup_metrics.assert_called_once()
        mock_config.instrument_fastapi.assert_called_once_with(app)

    @patch("src.api.telemetry.OpenTelemetryConfig")
    def test_setup_telemetry_with_endpoint(self, mock_config_class):
        """Test telemetry setup with OTLP endpoint."""
        app = FastAPI()
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        setup_telemetry(app, otlp_endpoint="http://localhost:4317", enable_console_export=True)

        mock_config_class.assert_called_once_with(
            otlp_endpoint="http://localhost:4317", enable_console_export=True
        )
        mock_config.setup_tracing.assert_called_once()
        mock_config.setup_metrics.assert_called_once()
        mock_config.instrument_fastapi.assert_called_once()

    @patch("src.api.telemetry.OpenTelemetryConfig")
    def test_setup_telemetry_adds_middleware(self, mock_config_class):
        """Test that telemetry setup adds middleware to app."""
        app = FastAPI()
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Verify middleware registration
        with patch.object(app, "middleware") as mock_middleware:
            setup_telemetry(app)
            mock_middleware.assert_called_once_with("http")


class TestRecordingFunctions:
    """Test convenience recording functions."""

    def test_record_llm_request_success(self):
        """Test recording successful LLM request."""
        with patch("src.api.telemetry.llm_requests_total") as mock_total:
            with patch("src.api.telemetry.llm_request_duration_seconds") as mock_duration:
                record_llm_request(provider="openai", model="gpt-4", duration=1.5, success=True)

                mock_total.labels.assert_called_with(provider="openai", model="gpt-4")
                mock_duration.labels.assert_called_with(provider="openai", model="gpt-4")
                mock_duration.labels.return_value.observe.assert_called_with(1.5)

    def test_record_llm_request_failure(self):
        """Test recording failed LLM request."""
        with patch("src.api.telemetry.llm_requests_total") as mock_total:
            with patch("src.api.telemetry.llm_request_duration_seconds") as mock_duration:
                with patch("src.api.telemetry.llm_requests_failed_total") as mock_failed:
                    record_llm_request(
                        provider="openai",
                        model="gpt-4",
                        duration=0.5,
                        success=False,
                        error_type="timeout",
                    )

                    mock_total.labels.assert_called()
                    mock_duration.labels.return_value.observe.assert_called_with(0.5)
                    mock_failed.labels.assert_called_with(
                        provider="openai", model="gpt-4", error_type="timeout"
                    )

    def test_record_vector_search(self):
        """Test recording vector search."""
        with patch("src.api.telemetry.vector_search_total") as mock_total:
            with patch("src.api.telemetry.vector_search_duration_seconds") as mock_duration:
                record_vector_search(search_type="semantic", duration=0.25)

                mock_total.labels.assert_called_with(search_type="semantic")
                mock_duration.labels.assert_called_with(search_type="semantic")
                mock_duration.labels.return_value.observe.assert_called_with(0.25)

    def test_record_graph_search_success(self):
        """Test recording successful graph search."""
        with patch("src.api.telemetry.graph_search_total") as mock_total:
            with patch("src.api.telemetry.graph_search_duration_seconds") as mock_duration:
                record_graph_search(query_type="entity", duration=0.5, success=True)

                mock_total.labels.assert_called_with(query_type="entity")
                mock_duration.labels.assert_called_with(query_type="entity")
                mock_duration.labels.return_value.observe.assert_called_with(0.5)

    def test_record_graph_search_failure(self):
        """Test recording failed graph search."""
        with patch("src.api.telemetry.graph_search_total") as mock_total:
            with patch("src.api.telemetry.graph_search_duration_seconds") as mock_duration:
                with patch("src.api.telemetry.graph_search_failures_total") as mock_failures:
                    record_graph_search(
                        query_type="relationship",
                        duration=0.3,
                        success=False,
                        error_type="connection_error",
                    )

                    mock_total.labels.assert_called()
                    mock_duration.labels.return_value.observe.assert_called_with(0.3)
                    mock_failures.labels.assert_called_with(error_type="connection_error")

    def test_record_cache_hit(self):
        """Test recording cache hit."""
        with patch("src.api.telemetry.cache_hits_total") as mock_hits:
            record_cache_access(hit=True)
            mock_hits.inc.assert_called_once()

    def test_record_cache_miss(self):
        """Test recording cache miss."""
        with patch("src.api.telemetry.cache_misses_total") as mock_misses:
            record_cache_access(hit=False)
            mock_misses.inc.assert_called_once()

    def test_record_document_ingestion_success(self):
        """Test recording successful document ingestion."""
        with patch("src.api.telemetry.document_ingestion_total") as mock_total:
            record_document_ingestion(success=True)
            mock_total.inc.assert_called_once()

    def test_record_document_ingestion_failure(self):
        """Test recording failed document ingestion."""
        with patch("src.api.telemetry.document_ingestion_total") as mock_total:
            with patch("src.api.telemetry.document_ingestion_failures_total") as mock_failures:
                record_document_ingestion(success=False, error_type="parse_error")

                mock_total.inc.assert_called_once()
                mock_failures.labels.assert_called_with(error_type="parse_error")


class TestPrometheusMetrics:
    """Test Prometheus metrics initialization."""

    def test_metrics_exist_in_registry(self):
        """Test that all metrics are registered."""
        from src.api.telemetry import (
            cache_hits_total,
            cache_misses_total,
            db_connections_active,
            db_connections_idle,
            db_query_duration_seconds,
            document_ingestion_failures_total,
            document_ingestion_total,
            embedding_generation_duration_seconds,
            graph_search_duration_seconds,
            graph_search_failures_total,
            graph_search_total,
            http_request_duration_seconds,
            http_requests_total,
            llm_request_duration_seconds,
            llm_requests_failed_total,
            llm_requests_total,
            vector_search_duration_seconds,
            vector_search_total,
        )

        # Verify metrics are not None
        assert http_requests_total is not None
        assert http_request_duration_seconds is not None
        assert llm_requests_total is not None
        assert llm_requests_failed_total is not None
        assert llm_request_duration_seconds is not None
        assert vector_search_total is not None
        assert vector_search_duration_seconds is not None
        assert graph_search_total is not None
        assert graph_search_duration_seconds is not None
        assert graph_search_failures_total is not None
        assert cache_hits_total is not None
        assert cache_misses_total is not None
        assert db_connections_active is not None
        assert db_connections_idle is not None
        assert db_query_duration_seconds is not None
        assert document_ingestion_total is not None
        assert document_ingestion_failures_total is not None
        assert embedding_generation_duration_seconds is not None

    def test_http_metrics_labels(self):
        """Test HTTP metrics with labels."""
        from src.api.telemetry import http_request_duration_seconds, http_requests_total

        # Test that labels work correctly
        http_requests_total.labels(method="GET", path="/test", status="200")
        http_request_duration_seconds.labels(method="GET", path="/test")

    def test_llm_metrics_labels(self):
        """Test LLM metrics with labels."""
        from src.api.telemetry import llm_request_duration_seconds, llm_requests_total

        llm_requests_total.labels(provider="openai", model="gpt-4")
        llm_request_duration_seconds.labels(provider="openai", model="gpt-4")

    def test_rag_metrics_labels(self):
        """Test RAG metrics with labels."""
        from src.api.telemetry import (
            graph_search_duration_seconds,
            graph_search_total,
            vector_search_duration_seconds,
            vector_search_total,
        )

        vector_search_total.labels(search_type="semantic")
        vector_search_duration_seconds.labels(search_type="semantic")
        graph_search_total.labels(query_type="entity")
        graph_search_duration_seconds.labels(query_type="entity")
