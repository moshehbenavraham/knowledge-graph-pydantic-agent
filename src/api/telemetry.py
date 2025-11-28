"""
OpenTelemetry instrumentation for the Luminari Agent API.

Provides distributed tracing, metrics, and logging integration.
"""

import logging
import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)
struct_logger = structlog.get_logger(__name__)

# ===== Prometheus Metrics =====

# HTTP Metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "path"]
)

# LLM Metrics
llm_requests_total = Counter("llm_requests_total", "Total LLM requests", ["provider", "model"])

llm_requests_failed_total = Counter(
    "llm_requests_failed_total", "Failed LLM requests", ["provider", "model", "error_type"]
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds", "LLM request duration", ["provider", "model"]
)

# RAG Metrics
vector_search_total = Counter("vector_search_total", "Total vector searches", ["search_type"])

vector_search_duration_seconds = Histogram(
    "vector_search_duration_seconds", "Vector search duration", ["search_type"]
)

graph_search_total = Counter("graph_search_total", "Total graph searches", ["query_type"])

graph_search_duration_seconds = Histogram(
    "graph_search_duration_seconds", "Graph search duration", ["query_type"]
)

graph_search_failures_total = Counter(
    "graph_search_failures_total", "Graph search failures", ["error_type"]
)

# Cache Metrics
cache_hits_total = Counter("cache_hits_total", "Cache hits")
cache_misses_total = Counter("cache_misses_total", "Cache misses")

# Database Metrics
db_connections_active = Gauge("db_connections_active", "Active database connections")
db_connections_idle = Gauge("db_connections_idle", "Idle database connections")
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds", "Database query duration", ["query_type"]
)

# Document Ingestion Metrics
document_ingestion_total = Counter("document_ingestion_total", "Documents ingested")
document_ingestion_failures_total = Counter(
    "document_ingestion_failures_total", "Document ingestion failures", ["error_type"]
)

# Embedding Metrics
embedding_generation_duration_seconds = Histogram(
    "embedding_generation_duration_seconds", "Embedding generation duration"
)


class OpenTelemetryConfig:
    """OpenTelemetry configuration for the API."""

    def __init__(
        self,
        service_name: str = "base-agent-api",
        service_version: str = "1.0.0",
        otlp_endpoint: str | None = None,
        enable_console_export: bool = False,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint
        self.enable_console_export = enable_console_export

    def setup_tracing(self) -> TracerProvider:
        """Set up distributed tracing."""
        resource = Resource(
            attributes={
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
            }
        )

        provider = TracerProvider(resource=resource)

        # Add OTLP exporter if endpoint is configured
        if self.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Console exporter for development
        if self.enable_console_export:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))

        trace.set_tracer_provider(provider)
        logger.info(f"OpenTelemetry tracing initialized for {self.service_name}")
        return provider

    def setup_metrics(self) -> MeterProvider:
        """Set up metrics collection."""
        resource = Resource(
            attributes={
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
            }
        )

        # Add OTLP metric exporter if endpoint is configured
        readers = []
        if self.otlp_endpoint:
            otlp_exporter = OTLPMetricExporter(endpoint=self.otlp_endpoint)
            readers.append(PeriodicExportingMetricReader(otlp_exporter))

        provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(provider)
        logger.info(f"OpenTelemetry metrics initialized for {self.service_name}")
        return provider

    def instrument_fastapi(self, app: FastAPI) -> None:
        """Instrument FastAPI application with OpenTelemetry."""
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)

        # Instrument requests library
        RequestsInstrumentor().instrument()

        # Instrument logging
        LoggingInstrumentor().instrument(set_logging_format=True)

        logger.info("FastAPI instrumented with OpenTelemetry")


async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware to collect request metrics."""
    start_time = time.time()
    path = request.url.path
    method = request.method

    try:
        response = await call_next(request)
        status = response.status_code

        # Record metrics
        http_requests_total.labels(method=method, path=path, status=status).inc()
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)

        return response

    except Exception:
        # Record error metrics
        http_requests_total.labels(method=method, path=path, status=500).inc()
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)
        raise


def setup_telemetry(
    app: FastAPI,
    otlp_endpoint: str | None = None,
    enable_console_export: bool = False,
) -> None:
    """
    Set up comprehensive telemetry for the FastAPI application.

    Args:
        app: FastAPI application instance
        otlp_endpoint: Optional OTLP endpoint for exporting traces/metrics
        enable_console_export: Enable console export for development
    """
    config = OpenTelemetryConfig(
        otlp_endpoint=otlp_endpoint,
        enable_console_export=enable_console_export,
    )

    # Set up tracing and metrics
    config.setup_tracing()
    config.setup_metrics()

    # Instrument FastAPI
    config.instrument_fastapi(app)

    # Add metrics middleware
    app.middleware("http")(metrics_middleware)

    logger.info("Telemetry setup complete")


# ===== Convenience functions for application code =====


def record_llm_request(
    provider: str, model: str, duration: float, success: bool, error_type: str = ""
) -> None:
    """Record LLM request metrics."""
    struct_logger.info(
        "Recording LLM request", provider=provider, model=model, duration=duration, success=success
    )
    llm_requests_total.labels(provider=provider, model=model).inc()
    llm_request_duration_seconds.labels(provider=provider, model=model).observe(duration)
    if not success:
        llm_requests_failed_total.labels(
            provider=provider, model=model, error_type=error_type
        ).inc()


def record_vector_search(search_type: str, duration: float) -> None:
    """Record vector search metrics."""
    struct_logger.info("Recording vector search", search_type=search_type, duration=duration)
    vector_search_total.labels(search_type=search_type).inc()
    vector_search_duration_seconds.labels(search_type=search_type).observe(duration)


def record_graph_search(
    query_type: str, duration: float, success: bool, error_type: str = ""
) -> None:
    """Record graph search metrics."""
    struct_logger.info(
        "Recording graph search", query_type=query_type, duration=duration, success=success
    )
    graph_search_total.labels(query_type=query_type).inc()
    graph_search_duration_seconds.labels(query_type=query_type).observe(duration)
    if not success:
        graph_search_failures_total.labels(error_type=error_type).inc()


def record_cache_access(hit: bool) -> None:
    """Record cache access metrics."""
    struct_logger.info("Recording cache access", hit=hit)
    if hit:
        cache_hits_total.inc()
    else:
        cache_misses_total.inc()


def record_document_ingestion(success: bool, error_type: str = "") -> None:
    """Record document ingestion metrics."""
    document_ingestion_total.inc()
    if not success:
        document_ingestion_failures_total.labels(error_type=error_type).inc()
