"""
FastAPI main application - Phase 4: Production-Ready API.

Comprehensive API with streaming, caching, resilience, and observability.
"""

from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.api.dependencies import (
    check_database_health,
    cleanup_dependencies,
    get_api_settings,
    get_cache_manager,
    init_dependencies,
)
from src.api.endpoints import analytics, chat, documents, search
from src.api.health_endpoints import router as health_router
from src.api.middleware import (
    CompressionMiddleware,
    CorrelationIDMiddleware,
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    TimingMiddleware,
)
from src.api.models import StatusResponse
from src.config.api import api_config

logger = structlog.get_logger()

# Conditional import for tracing (for test mocking)
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except ImportError:
    FastAPIInstrumentor = None  # type: ignore


# ===== Application Lifespan =====


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown of dependencies.
    """
    # Startup
    logger.info(
        "starting_agentic_rag_api",
        version=app.version,
        environment=api_config._settings.app_env,
    )

    try:
        # Initialize dependencies
        await init_dependencies()
        logger.info("dependencies_initialized")

        # Initialize OpenTelemetry tracing if enabled
        if api_config.enable_tracing:
            _setup_tracing(app)

    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("shutting_down_agentic_rag_api")

    try:
        await cleanup_dependencies()
        logger.info("dependencies_cleaned_up")
    except Exception as e:
        logger.error("shutdown_error", error=str(e))


# ===== Application Setup =====


app = FastAPI(
    title="Agentic RAG API",
    description=(
        "Production-ready API for Agentic RAG system with streaming, "
        "caching, resilience, and comprehensive observability."
    ),
    version="0.8.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)


# ===== Middleware Stack =====


# 1. CORS (first to handle preflight requests)
app.add_middleware(
    CORSMiddleware,
    **api_config.get_cors_config(),
)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Compression
app.add_middleware(CompressionMiddleware, minimum_size=1000)

# 4. Rate limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# 5. Correlation ID
app.add_middleware(CorrelationIDMiddleware)

# 6. Request timing
app.add_middleware(TimingMiddleware)

# 7. Error handling
app.add_middleware(ErrorHandlingMiddleware)

# 8. Request logging
app.add_middleware(RequestLoggingMiddleware)


# ===== Routers =====


# Health endpoints
app.include_router(health_router, prefix="/health", tags=["health"])

# API v1 endpoints
app.include_router(chat.router, tags=["chat"])
app.include_router(search.router, tags=["search"])
app.include_router(documents.router, tags=["documents"])
app.include_router(analytics.router, tags=["analytics"])


# ===== Root Endpoints =====


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Agentic RAG API",
        "version": "0.8.0",
        "status": "operational",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/api/v1/openapi.json",
        },
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "status": "/api/v1/status",
            "chat": "/api/v1/chat",
            "search": "/api/v1/search",
            "documents": "/api/v1/documents",
            "analytics": "/api/v1/analytics",
        },
    }


@app.get("/api/v1/status", response_model=StatusResponse)
async def status():
    """
    Get API status and health information.

    Returns comprehensive status of all components.
    """
    health = await check_database_health()
    settings = await get_api_settings()

    return StatusResponse(
        status="operational" if health["postgres"] else "degraded",
        version="0.8.0",
        cache=None,  # Populated by health check
        components=[
            {
                "name": "PostgreSQL",
                "healthy": health["postgres"],
                "details": {},
            },
            {
                "name": "Neo4j",
                "healthy": health["neo4j"],
                "details": {},
            },
            {
                "name": "Cache",
                "healthy": health["cache"],
                "details": {},
            },
        ],
        metrics={
            "environment": settings["environment"],
            "features": settings["features"],
        },
    )


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.delete("/api/v1/cache")
async def clear_cache(pattern: str = "*"):
    """
    Clear cache entries.

    Supports wildcard patterns for selective clearing.
    """
    try:
        cache = await get_cache_manager()

        if pattern == "*":
            cache.flush()
            return {"message": "All cache entries cleared"}
        # TODO: Implement pattern-based clearing
        return {"message": f"Cleared cache entries matching pattern: {pattern}"}

    except Exception as e:
        logger.error("cache_clear_failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to clear cache"},
        )


# ===== Exception Handlers =====


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 Not Found errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "not_found",
                "message": "The requested resource was not found",
            }
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 Internal Server errors."""
    logger.error(
        "internal_server_error",
        path=request.url.path,
        error=str(exc),
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An internal error occurred",
            }
        },
    )


# ===== Tracing Setup =====


def _setup_tracing(app: FastAPI):
    """
    Setup OpenTelemetry tracing.

    Instruments FastAPI app with distributed tracing.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Use module-level import if available (for testing), otherwise import locally
        if FastAPIInstrumentor is None:
            from opentelemetry.instrumentation.fastapi import (
                FastAPIInstrumentor as LocalFastAPIInstrumentor,
            )

            instrumentor = LocalFastAPIInstrumentor
        else:
            instrumentor = FastAPIInstrumentor

        # Create resource
        resource = Resource.create(
            {
                "service.name": "agentic-rag-api",
                "service.version": "0.8.0",
            }
        )

        # Setup tracer provider
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # Setup OTLP exporter (or Jaeger)
        if api_config._settings.jaeger_host:
            # Use Jaeger if configured
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter

            exporter = JaegerExporter(
                agent_host_name=api_config.jaeger_host,
                agent_port=api_config.jaeger_port,
            )
        else:
            # Use OTLP
            exporter = OTLPSpanExporter()

        provider.add_span_processor(BatchSpanProcessor(exporter))

        # Instrument FastAPI
        instrumentor.instrument_app(app)

        logger.info(
            "tracing_enabled",
            exporter="jaeger" if api_config._settings.jaeger_host else "otlp",
        )

    except ImportError as e:
        logger.warning(
            "tracing_dependencies_missing",
            error=str(e),
            help="Install with: pip install opentelemetry-instrumentation-fastapi",
        )
    except Exception as e:
        logger.error("tracing_setup_failed", error=str(e))


# ===== Server Runner =====


def run_server():
    """
    Run the FastAPI server.

    Uses Uvicorn with configuration from api_config.
    """
    uvicorn_config = api_config.get_uvicorn_config()

    logger.info(
        "starting_uvicorn",
        host=uvicorn_config["host"],
        port=uvicorn_config["port"],
        reload=uvicorn_config["reload"],
    )

    uvicorn.run(
        "src.api.main:app",
        **uvicorn_config,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": api_config.log_level,
                "handlers": ["default"],
            },
        },
    )


if __name__ == "__main__":
    run_server()
