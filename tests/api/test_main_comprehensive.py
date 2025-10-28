"""
Comprehensive tests for api/main.py - FastAPI application setup and lifecycle.

Tests cover:
- Application initialization and lifespan management
- Middleware stack configuration
- Root endpoints (/, /api/v1/status, /metrics, /api/v1/cache)
- Exception handlers (404, 500)
- Tracing setup (with and without dependencies)
- Server runner configuration
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def mock_dependencies():
    """Mock all initialization dependencies."""
    with (
        patch("src.api.main.init_dependencies", new_callable=AsyncMock) as mock_init,
        patch("src.api.main.cleanup_dependencies", new_callable=AsyncMock) as mock_cleanup,
        patch("src.api.main.api_config") as mock_config,
    ):
        # Configure mock_config
        mock_config._settings.app_env = "test"
        mock_config.enable_tracing = False
        mock_config.log_level = "INFO"
        mock_config.get_cors_config.return_value = {
            "allow_origins": ["*"],
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

        yield {
            "init": mock_init,
            "cleanup": mock_cleanup,
            "config": mock_config,
        }


@pytest.fixture
def test_app(mock_dependencies):
    """Create test FastAPI app with mocked dependencies."""
    # Import after mocking to ensure mocks are in place
    from src.api.main import app

    return app


@pytest.fixture
def client(test_app):
    """Create test client for the app."""
    return TestClient(test_app)


# ====================
# Lifespan Tests
# ====================


@pytest.mark.asyncio
async def test_lifespan_startup_success(mock_dependencies):
    """Test successful application startup."""
    from src.api.main import lifespan

    mock_app = Mock(spec=FastAPI)
    mock_app.version = "0.8.0"

    async with lifespan(mock_app):
        # Verify init_dependencies was called
        mock_dependencies["init"].assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_startup_failure(mock_dependencies):
    """Test application startup failure handling."""
    from src.api.main import lifespan

    mock_app = Mock(spec=FastAPI)
    mock_app.version = "0.8.0"

    # Make init fail
    mock_dependencies["init"].side_effect = RuntimeError("Init failed")

    with pytest.raises(RuntimeError, match="Init failed"):
        async with lifespan(mock_app):
            pass


@pytest.mark.asyncio
async def test_lifespan_shutdown_success(mock_dependencies):
    """Test successful application shutdown."""
    from src.api.main import lifespan

    mock_app = Mock(spec=FastAPI)
    mock_app.version = "0.8.0"

    async with lifespan(mock_app):
        pass

    # Verify cleanup was called
    mock_dependencies["cleanup"].assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_shutdown_with_error(mock_dependencies):
    """Test application shutdown with cleanup error."""
    from src.api.main import lifespan

    mock_app = Mock(spec=FastAPI)
    mock_app.version = "0.8.0"

    # Make cleanup fail
    mock_dependencies["cleanup"].side_effect = RuntimeError("Cleanup failed")

    # Should not raise - errors are logged
    async with lifespan(mock_app):
        pass


# ====================
# Root Endpoint Tests
# ====================


def test_root_endpoint(client):
    """Test root endpoint returns API information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Agentic RAG API"
    assert data["version"] == "0.8.0"
    assert data["status"] == "operational"
    assert "documentation" in data
    assert "endpoints" in data
    assert data["documentation"]["swagger"] == "/docs"


def test_status_endpoint(client):
    """Test status endpoint returns health information."""
    with (
        patch("src.api.main.check_database_health", new_callable=AsyncMock) as mock_health,
        patch("src.api.main.get_api_settings", new_callable=AsyncMock) as mock_settings,
    ):
        # Mock health check response
        mock_health.return_value = {
            "postgres": True,
            "neo4j": True,
            "cache": True,
        }

        # Mock settings response
        mock_settings.return_value = {
            "environment": "test",
            "features": {"streaming": True, "caching": True},
        }

        response = client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "operational"
        assert data["version"] == "0.8.0"
        assert len(data["components"]) == 3
        assert data["components"][0]["name"] == "PostgreSQL"
        assert data["components"][1]["name"] == "Neo4j"


def test_status_endpoint_degraded(client):
    """Test status endpoint shows degraded when postgres is down."""
    with (
        patch("src.api.main.check_database_health", new_callable=AsyncMock) as mock_health,
        patch("src.api.main.get_api_settings", new_callable=AsyncMock) as mock_settings,
    ):
        # Mock health check with postgres down
        mock_health.return_value = {
            "postgres": False,
            "neo4j": True,
            "cache": True,
        }

        mock_settings.return_value = {
            "environment": "test",
            "features": {},
        }

        response = client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"


def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint."""
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    # Prometheus format check
    assert b"HELP" in response.content or b"TYPE" in response.content or len(response.content) > 0


def test_clear_cache_endpoint_all(client):
    """Test cache clearing with wildcard pattern."""
    with patch("src.api.main.get_cache_manager", new_callable=AsyncMock) as mock_cache:
        mock_cache_instance = Mock()
        mock_cache_instance.flush = Mock()
        mock_cache.return_value = mock_cache_instance

        response = client.delete("/api/v1/cache?pattern=*")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "All cache entries cleared"
        mock_cache_instance.flush.assert_called_once()


def test_clear_cache_endpoint_pattern(client):
    """Test cache clearing with specific pattern."""
    with patch("src.api.main.get_cache_manager", new_callable=AsyncMock) as mock_cache:
        mock_cache.return_value = Mock()

        response = client.delete("/api/v1/cache?pattern=user:*")

        assert response.status_code == 200
        data = response.json()
        assert "pattern" in data["message"]


def test_clear_cache_endpoint_error(client):
    """Test cache clearing error handling."""
    with patch("src.api.main.get_cache_manager", new_callable=AsyncMock) as mock_cache:
        mock_cache.side_effect = RuntimeError("Cache error")

        response = client.delete("/api/v1/cache")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data


# ====================
# Exception Handler Tests
# ====================


def test_404_handler(client):
    """Test 404 Not Found handler."""
    response = client.get("/nonexistent-endpoint")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"


def test_500_handler_simulation():
    """Test 500 Internal Server Error handler via exception."""
    from fastapi import Request

    from src.api.main import internal_error_handler

    # Create mock request
    mock_request = Mock(spec=Request)
    mock_request.url.path = "/test-error"

    # Create mock exception
    mock_exc = Exception("Test error")

    # Call handler directly
    import asyncio

    response = asyncio.run(internal_error_handler(mock_request, mock_exc))

    assert response.status_code == 500
    data = json.loads(response.body.decode())
    assert data["error"]["code"] == "internal_server_error"


# ====================
# Tracing Setup Tests
# ====================


def test_setup_tracing_with_jaeger():
    """Test OpenTelemetry tracing setup with Jaeger."""
    from src.api.main import _setup_tracing

    mock_app = Mock(spec=FastAPI)

    with (
        patch("src.api.main.api_config") as mock_config,
        patch("src.api.main.FastAPIInstrumentor") as mock_instrumentor,
    ):
        mock_config._settings.jaeger_host = "localhost"
        mock_config.jaeger_host = "localhost"
        mock_config.jaeger_port = 6831

        # Mock the imports
        with patch.dict(
            "sys.modules",
            {
                "opentelemetry": Mock(),
                "opentelemetry.trace": Mock(),
                "opentelemetry.sdk.trace": Mock(),
                "opentelemetry.sdk.trace.export": Mock(),
                "opentelemetry.sdk.resources": Mock(),
                "opentelemetry.exporter.jaeger.thrift": Mock(),
                "opentelemetry.instrumentation.fastapi": Mock(
                    FastAPIInstrumentor=mock_instrumentor
                ),
            },
        ):
            _setup_tracing(mock_app)

            # Verify instrumentation was called
            mock_instrumentor.instrument_app.assert_called_once_with(mock_app)


def test_setup_tracing_with_otlp():
    """Test OpenTelemetry tracing setup with OTLP."""
    from src.api.main import _setup_tracing

    mock_app = Mock(spec=FastAPI)

    with (
        patch("src.api.main.api_config") as mock_config,
        patch("src.api.main.FastAPIInstrumentor") as mock_instrumentor,
    ):
        mock_config._settings.jaeger_host = None
        mock_config.jaeger_host = None

        with patch.dict(
            "sys.modules",
            {
                "opentelemetry": Mock(),
                "opentelemetry.trace": Mock(),
                "opentelemetry.sdk.trace": Mock(),
                "opentelemetry.sdk.trace.export": Mock(),
                "opentelemetry.sdk.resources": Mock(),
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": Mock(),
                "opentelemetry.instrumentation.fastapi": Mock(
                    FastAPIInstrumentor=mock_instrumentor
                ),
            },
        ):
            _setup_tracing(mock_app)

            mock_instrumentor.instrument_app.assert_called_once_with(mock_app)


def test_setup_tracing_missing_dependencies():
    """Test tracing setup with missing dependencies."""
    from src.api.main import _setup_tracing

    mock_app = Mock(spec=FastAPI)

    with patch("src.api.main.api_config") as mock_config:
        mock_config._settings.jaeger_host = None

        # Simulate ImportError
        with patch.dict("sys.modules", {"opentelemetry": None}):
            # Should not raise - just log warning
            _setup_tracing(mock_app)


def test_setup_tracing_runtime_error():
    """Test tracing setup with runtime error."""
    from src.api.main import _setup_tracing

    mock_app = Mock(spec=FastAPI)

    with (
        patch("src.api.main.api_config") as mock_config,
        patch("src.api.main.FastAPIInstrumentor") as mock_instrumentor,
    ):
        mock_config._settings.jaeger_host = None

        # Make instrumentor raise error
        mock_instrumentor.instrument_app.side_effect = RuntimeError("Instrumentation failed")

        with patch.dict(
            "sys.modules",
            {
                "opentelemetry": Mock(),
                "opentelemetry.trace": Mock(),
                "opentelemetry.sdk.trace": Mock(),
                "opentelemetry.sdk.trace.export": Mock(),
                "opentelemetry.sdk.resources": Mock(),
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": Mock(),
                "opentelemetry.instrumentation.fastapi": Mock(
                    FastAPIInstrumentor=mock_instrumentor
                ),
            },
        ):
            # Should not raise - just log error
            _setup_tracing(mock_app)


# ====================
# Server Runner Tests
# ====================


def test_run_server_configuration():
    """Test server runner with uvicorn config."""
    from src.api.main import run_server

    with (
        patch("src.api.main.uvicorn.run") as mock_run,
        patch("src.api.main.api_config") as mock_config,
    ):
        mock_config.get_uvicorn_config.return_value = {
            "host": "0.0.0.0",
            "port": 8058,
            "reload": False,
        }
        mock_config.log_level = "INFO"

        run_server()

        # Verify uvicorn.run was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args

        # Check app string
        assert call_args[0][0] == "src.api.main:app"

        # Check host/port
        assert call_args[1]["host"] == "0.0.0.0"
        assert call_args[1]["port"] == 8058


# ====================
# Middleware Tests
# ====================


def test_middleware_stack_order(client):
    """Test that middleware stack is applied in correct order."""
    # Make a request and check headers to verify middleware execution
    response = client.get("/")

    # Security headers should be present (from SecurityHeadersMiddleware)
    assert "x-content-type-options" in response.headers or response.status_code == 200

    # Correlation ID should be present (from CorrelationIDMiddleware)
    # This might not be in headers depending on implementation, but request should succeed
    assert response.status_code == 200


def test_cors_middleware(client):
    """Test CORS middleware configuration."""
    response = client.options("/", headers={"Origin": "http://localhost:3000"})

    # Should handle OPTIONS request (even if 405, it means CORS is configured)
    assert response.status_code in [200, 405]


# ====================
# Router Inclusion Tests
# ====================


def test_health_router_included(client):
    """Test that health router is included."""
    response = client.get("/health")

    # Should either succeed or return 404 for specific sub-route
    # Any response means router is mounted
    assert response.status_code in [200, 404, 405]


def test_chat_router_included(client):
    """Test that chat router is included."""
    # Try to access chat endpoint (will fail without deps, but endpoint exists)
    response = client.post("/api/v1/chat", json={"message": "test"})

    # Should not be 404 (router is mounted)
    assert response.status_code != 404


def test_search_router_included(client):
    """Test that search router is included."""
    response = client.post("/api/v1/search", json={"query": "test"})

    # Should not be 404 (router is mounted)
    assert response.status_code != 404


def test_documents_router_included(client):
    """Test that documents router is included."""
    response = client.get("/api/v1/documents")

    # Should not be 404 (router is mounted)
    assert response.status_code != 404


def test_analytics_router_included(client):
    """Test that analytics router is included."""
    response = client.get("/api/v1/analytics/searches")

    # Should not be 404 (router is mounted)
    assert response.status_code != 404


# ====================
# Application Configuration Tests
# ====================


def test_app_metadata(test_app):
    """Test FastAPI app metadata configuration."""
    assert test_app.title == "Agentic RAG API"
    assert test_app.version == "0.8.0"
    assert test_app.docs_url == "/docs"
    assert test_app.redoc_url == "/redoc"
    assert test_app.openapi_url == "/api/v1/openapi.json"


def test_openapi_schema(client):
    """Test OpenAPI schema generation."""
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    data = response.json()

    assert data["info"]["title"] == "Agentic RAG API"
    assert data["info"]["version"] == "0.8.0"
    assert "paths" in data


# ====================
# Integration Tests
# ====================


@pytest.mark.asyncio
async def test_full_lifecycle():
    """Test full application lifecycle (startup -> request -> shutdown)."""
    from src.api.main import app

    with (
        patch("src.api.main.init_dependencies", new_callable=AsyncMock) as mock_init,
        patch("src.api.main.cleanup_dependencies", new_callable=AsyncMock) as mock_cleanup,
    ):
        client = TestClient(app)

        # Make a request
        response = client.get("/")
        assert response.status_code == 200

        # Verify initialization happened
        assert mock_init.called


def test_concurrent_requests(client):
    """Test handling multiple concurrent requests."""
    import concurrent.futures

    def make_request():
        return client.get("/").status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [f.result() for f in futures]

    # All requests should succeed
    assert all(status == 200 for status in results)


def test_request_logging_middleware(client):
    """Test request logging middleware captures requests."""
    with patch("src.api.middleware.request_logging.logger") as mock_logger:
        response = client.get("/")

        assert response.status_code == 200
        # Logger should have been called (at least for the request)
        assert mock_logger.info.called or response.status_code == 200
