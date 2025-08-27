"""FastAPI main application with comprehensive middleware stack."""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from pydantic import BaseModel, Field

# Using unified agent now
from src.agent import super_agent, UnifiedAgentDeps, run_unified_agent
from src.api.health_endpoints import router as health_router
from src.config.api import api_config
from src.config.agent import agent_config
from src.utils.cache import get_cache, cache
from src.utils.monitoring import track_metrics

# Configure structured logging
logger = structlog.get_logger()

# Prometheus metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)
active_connections = Gauge(
    "active_connections", "Number of active connections"
)
cache_hits = Counter("cache_hits_total", "Total cache hits", ["endpoint"])
cache_misses = Counter("cache_misses_total", "Total cache misses", ["endpoint"])
llm_requests_total = Counter(
    "llm_requests_total", "Total LLM API requests", ["model", "endpoint"]
)
llm_tokens_total = Counter(
    "llm_tokens_total", "Total tokens processed", ["model", "type"]
)


# Request/Response models
class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    stream: bool = Field(False, description="Enable streaming response")
    include_sources: bool = Field(True, description="Include source citations")
    search_strategy: Optional[str] = Field(
        None, description="Search strategy to use"
    )
    max_tokens: Optional[int] = Field(2000, description="Maximum response tokens")


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str = Field(..., description="Agent response")
    sources: Optional[List[Dict[str, Any]]] = Field(
        None, description="Source documents"
    )
    confidence: float = Field(..., description="Response confidence score")
    search_strategy_used: Optional[str] = Field(
        None, description="Search strategy that was used"
    )
    session_id: str = Field(..., description="Session ID for context")
    metrics: Optional[Dict[str, Any]] = Field(
        None, description="Performance metrics"
    )


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., description="Search query")
    search_type: str = Field(
        "hybrid", description="Search type: vector, graph, or hybrid"
    )
    limit: int = Field(10, description="Maximum number of results")
    threshold: float = Field(0.7, description="Similarity threshold")


class SearchResponse(BaseModel):
    """Search response model."""

    results: List[Dict[str, Any]] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    search_time_ms: float = Field(..., description="Search time in milliseconds")
    strategy_used: str = Field(..., description="Search strategy used")


# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting Agentic RAG API server")

    # Initialize cache
    cache_instance = get_cache()
    app.state.cache = cache_instance

    # Initialize agent
    try:
        app.state.agent = AgenticRAGChatbot()
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize agent", error=str(e))
        # Continue without agent for health checks

    # Initialize OpenTelemetry if enabled
    if api_config.enable_tracing:
        from opentelemetry import trace
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "agentic-rag-api"})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        jaeger_exporter = JaegerExporter(
            agent_host_name=api_config.jaeger_host,
            agent_port=api_config.jaeger_port,
        )
        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry tracing enabled")

    yield

    # Shutdown
    logger.info("Shutting down Agentic RAG API server")
    # Cleanup resources
    if hasattr(app.state, "agent"):
        # Add any agent cleanup if needed
        pass


# Create FastAPI application
app = FastAPI(
    title="Agentic RAG API",
    description="Production-ready API for Agentic RAG system with caching and monitoring",
    version="0.7.1",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    **api_config.get_cors_config(),
)


# Middleware for metrics and logging
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track metrics for all requests."""
    start_time = time.time()
    active_connections.inc()

    # Extract endpoint path
    endpoint = request.url.path

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method=request.method, endpoint=endpoint, status=response.status_code
        ).inc()
        http_request_duration.labels(
            method=request.method, endpoint=endpoint
        ).observe(duration)

        # Log request
        logger.info(
            "Request completed",
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
            duration_ms=duration * 1000,
        )

        return response
    except Exception as e:
        duration = time.time() - start_time
        http_requests_total.labels(
            method=request.method, endpoint=endpoint, status=500
        ).inc()
        logger.error(
            "Request failed",
            method=request.method,
            endpoint=endpoint,
            error=str(e),
            duration_ms=duration * 1000,
        )
        raise
    finally:
        active_connections.dec()


# Include health router
app.include_router(health_router, prefix="/health", tags=["health"])


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Agentic RAG API",
        "version": "0.7.1",
        "status": "operational",
        "documentation": "/docs",
    }


@app.post("/api/v1/chat", response_model=ChatResponse)
@cache(prefix="chat", ttl=300)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint with caching and streaming support."""
    if not hasattr(app.state, "agent"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent not initialized",
        )

    start_time = time.time()

    try:
        # Track LLM request
        llm_requests_total.labels(
            model=agent_config.llm_model, endpoint="chat"
        ).inc()

        # Get response from agent
        if request.stream:
            # TODO: Implement streaming
            pass

        # Use agent to get response
        agent_response = await asyncio.to_thread(
            app.state.agent.chat,
            request.message,
            session_id=request.session_id,
            search_strategy=request.search_strategy,
        )

        # Calculate metrics
        response_time = (time.time() - start_time) * 1000

        return ChatResponse(
            response=agent_response.get("response", ""),
            sources=agent_response.get("sources"),
            confidence=agent_response.get("confidence", 0.0),
            search_strategy_used=agent_response.get("search_strategy"),
            session_id=request.session_id or "default",
            metrics={
                "response_time_ms": response_time,
                "tokens_used": agent_response.get("tokens_used", 0),
            },
        )

    except Exception as e:
        logger.error("Chat request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat request failed: {str(e)}",
        )


@app.post("/api/v1/search", response_model=SearchResponse)
@cache(prefix="search", ttl=600)
async def search(request: SearchRequest) -> SearchResponse:
    """Search endpoint with caching."""
    if not hasattr(app.state, "agent"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent not initialized",
        )

    start_time = time.time()

    try:
        # Perform search using agent's search capabilities
        if request.search_type == "vector":
            results = await asyncio.to_thread(
                app.state.agent.vector_search,
                request.query,
                limit=request.limit,
                threshold=request.threshold,
            )
        elif request.search_type == "graph":
            results = await asyncio.to_thread(
                app.state.agent.graph_search,
                request.query,
                limit=request.limit,
            )
        else:  # hybrid
            results = await asyncio.to_thread(
                app.state.agent.hybrid_search,
                request.query,
                limit=request.limit,
            )

        search_time = (time.time() - start_time) * 1000

        return SearchResponse(
            results=results.get("results", []),
            total_results=len(results.get("results", [])),
            search_time_ms=search_time,
            strategy_used=request.search_type,
        )

    except Exception as e:
        logger.error("Search request failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search request failed: {str(e)}",
        )


@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint."""
    if not hasattr(app.state, "agent"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent not initialized",
        )

    async def generate():
        """Generate streaming response."""
        try:
            # TODO: Implement actual streaming from agent
            response = await asyncio.to_thread(
                app.state.agent.chat,
                request.message,
                session_id=request.session_id,
            )

            # Simulate streaming by yielding chunks
            text = response.get("response", "")
            words = text.split()
            for i in range(0, len(words), 5):
                chunk = " ".join(words[i : i + 5]) + " "
                yield f"data: {chunk}\n\n"
                await asyncio.sleep(0.05)

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.delete("/api/v1/cache")
async def clear_cache(pattern: Optional[str] = "*"):
    """Clear cache entries matching pattern."""
    try:
        cache_instance = app.state.cache
        if pattern == "*":
            cache_instance.flush()
            return {"message": "All cache entries cleared"}
        else:
            from src.utils.cache import invalidate_cache

            deleted = invalidate_cache(pattern)
            return {
                "message": f"Cleared {deleted} cache entries matching pattern",
                "pattern": pattern,
            }
    except Exception as e:
        logger.error("Cache clear failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache clear failed: {str(e)}",
        )


@app.get("/api/v1/status")
async def status():
    """Get API status and statistics."""
    cache_instance = app.state.cache

    return {
        "status": "operational",
        "version": "0.7.1",
        "cache": {
            "enabled": cache_instance is not None,
            "healthy": cache_instance.health_check() if cache_instance else False,
        },
        "agent": {
            "initialized": hasattr(app.state, "agent"),
        },
        "metrics": {
            "active_connections": active_connections._value._value,
            "total_requests": sum(
                [
                    sample.value
                    for sample in http_requests_total.collect()[0].samples
                ]
            ),
        },
    }


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception", error=str(exc), path=request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
        },
    )


def run_server():
    """Run the FastAPI server."""
    uvicorn_config = api_config.get_uvicorn_config()

    logger.info(f"Starting API server on {uvicorn_config['host']}:{uvicorn_config['port']}")

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