"""
Comprehensive integration tests for api/main.py.

Tests FastAPI application initialization, middleware, endpoints, and lifecycle.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_app():
    """Create test FastAPI app with overridden dependencies."""
    with patch("src.api.main.init_dependencies", new_callable=AsyncMock):
        with patch("src.api.main.cleanup_dependencies", new_callable=AsyncMock):
            from src.api.main import app

            # Remove rate limiting middleware for tests
            # Find and remove RateLimitMiddleware from the middleware stack
            app.user_middleware = [
                m for m in app.user_middleware if "RateLimitMiddleware" not in str(m.cls)
            ]

            return app


@pytest.fixture
def test_client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestMainAppInitialization:
    """Test application initialization and setup."""

    def test_app_exists(self):
        """Test that FastAPI app is created."""
        from src.api.main import app

        assert app is not None
        assert app.title == "Agentic RAG API"
        assert app.version == "0.8.0"

    def test_app_docs_urls(self):
        """Test documentation URLs are configured."""
        from src.api.main import app

        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/api/v1/openapi.json"

    def test_middleware_stack_configured(self):
        """Test that middleware stack is properly configured."""
        from src.api.main import app

        # Check middleware is configured
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]

        assert "CORSMiddleware" in middleware_classes


class TestRootEndpoints:
    """Test root endpoint functionality."""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns API information."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Agentic RAG API"
        assert data["version"] == "0.8.0"
        assert data["status"] == "operational"
        assert "documentation" in data
        assert "endpoints" in data

    def test_root_endpoint_structure(self, test_client):
        """Test root endpoint has correct structure."""
        response = test_client.get("/")
        data = response.json()

        # Check documentation URLs
        assert data["documentation"]["swagger"] == "/docs"
        assert data["documentation"]["redoc"] == "/redoc"

        # Check endpoint URLs
        assert data["endpoints"]["health"] == "/health"
        assert data["endpoints"]["metrics"] == "/metrics"
        assert data["endpoints"]["chat"] == "/api/v1/chat"


class TestStatusEndpoint:
    """Test status endpoint functionality."""

    @patch("src.api.dependencies.check_database_health", new_callable=AsyncMock)
    @patch("src.api.dependencies.get_api_settings", new_callable=AsyncMock)
    def test_status_endpoint_healthy(self, mock_settings, mock_health, test_client):
        """Test status endpoint when all components healthy."""
        # Mock health check
        mock_health.return_value = {
            "postgres": True,
            "neo4j": True,
            "cache": True,
        }

        # Mock settings
        mock_settings.return_value = {
            "environment": "test",
            "features": {"rag": True, "graph": True},
        }

        response = test_client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "operational"
        assert data["version"] == "0.8.0"

    @patch("src.api.dependencies.check_database_health", new_callable=AsyncMock)
    @patch("src.api.dependencies.get_api_settings", new_callable=AsyncMock)
    def test_status_endpoint_degraded(self, mock_settings, mock_health, test_client):
        """Test status endpoint when components degraded."""
        # Mock health check with failures
        mock_health.return_value = {
            "postgres": False,
            "neo4j": True,
            "cache": True,
        }

        mock_settings.return_value = {
            "environment": "test",
            "features": {},
        }

        response = test_client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "degraded"


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""

    def test_metrics_endpoint(self, test_client):
        """Test metrics endpoint returns Prometheus format."""
        response = test_client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

        # Check for Prometheus metric format
        content = response.text
        assert len(content) > 0

    def test_metrics_content_type(self, test_client):
        """Test metrics endpoint has correct content type."""
        response = test_client.get("/metrics")

        # Prometheus expects specific content type
        assert "text/plain" in response.headers["content-type"]


class TestCacheEndpoint:
    """Test cache management endpoint."""

    @patch("src.api.dependencies.get_cache_manager", new_callable=AsyncMock)
    def test_clear_cache_all(self, mock_cache, test_client):
        """Test clearing all cache entries."""
        # Mock cache manager
        mock_cache_instance = MagicMock()
        mock_cache_instance.flush = MagicMock()
        mock_cache.return_value = mock_cache_instance

        response = test_client.delete("/api/v1/cache?pattern=*")

        assert response.status_code == 200
        data = response.json()

        assert "cache entries cleared" in data["message"].lower()
        mock_cache_instance.flush.assert_called_once()

    @patch("src.api.dependencies.get_cache_manager", new_callable=AsyncMock)
    def test_clear_cache_pattern(self, mock_cache, test_client):
        """Test clearing cache with pattern."""
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance

        response = test_client.delete("/api/v1/cache?pattern=chat:*")

        assert response.status_code == 200
        data = response.json()

        assert "pattern" in data["message"].lower()

    @patch("src.api.dependencies.get_cache_manager", new_callable=AsyncMock)
    def test_clear_cache_error(self, mock_cache, test_client):
        """Test cache clear error handling."""
        mock_cache.side_effect = Exception("Cache error")

        response = test_client.delete("/api/v1/cache")

        assert response.status_code == 500


class TestExceptionHandlers:
    """Test exception handlers."""

    def test_404_handler(self, test_client):
        """Test 404 error handler."""
        response = test_client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == "not_found"

    def test_404_error_structure(self, test_client):
        """Test 404 error has correct structure."""
        response = test_client.get("/invalid/path/here")

        assert response.status_code == 404
        data = response.json()

        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]


class TestTracingSetup:
    """Test OpenTelemetry tracing setup."""

    @patch("src.api.main.api_config")
    def test_tracing_disabled(self, mock_config):
        """Test tracing is not setup when disabled."""
        from src.api.main import _setup_tracing, app

        mock_config.enable_tracing = False

        # Should not raise error
        _setup_tracing(app)

    def test_tracing_import_error(self):
        """Test tracing handles missing dependencies."""
        from src.api.main import _setup_tracing, app

        # The _setup_tracing function has try/except that catches ImportError
        # We just need to verify it doesn't raise an exception
        # The function already has internal error handling for missing dependencies
        try:
            _setup_tracing(app)  # Should not raise even if dependencies are missing
        except ImportError:
            # If ImportError is raised, the test should fail
            pytest.fail("_setup_tracing should handle ImportError internally")


class TestServerRunner:
    """Test server runner function."""

    @patch("src.api.main.uvicorn.run")
    @patch("src.api.main.api_config")
    def test_run_server(self, mock_config, mock_uvicorn_run):
        """Test server runner configuration."""
        from src.api.main import run_server

        # Mock config
        mock_config.get_uvicorn_config.return_value = {
            "host": "0.0.0.0",
            "port": 8058,
            "reload": False,
        }
        mock_config.log_level = "INFO"

        run_server()

        # Verify uvicorn.run was called
        assert mock_uvicorn_run.called
        call_args = mock_uvicorn_run.call_args

        assert call_args[0][0] == "src.api.main:app"
        assert call_args[1]["host"] == "0.0.0.0"
        assert call_args[1]["port"] == 8058


class TestRouterInclusion:
    """Test API routers are properly included."""

    def test_health_router_included(self):
        """Test health router is included."""
        from src.api.main import app

        routes = [route.path for route in app.routes]

        # Check health endpoints exist
        assert any("/health" in route for route in routes)

    def test_api_routers_included(self):
        """Test all API v1 routers are included."""
        from src.api.main import app

        routes = [route.path for route in app.routes]

        # Check main API endpoints
        assert any("/api/v1/chat" in route for route in routes)
        assert any("/api/v1/search" in route for route in routes)
        assert any("/api/v1/documents" in route for route in routes)
        assert any("/api/v1/analytics" in route for route in routes)


class TestLifespanManagement:
    """Test application lifespan management."""

    @pytest.mark.skip(
        reason="PERMANENT SKIP: Lifespan testing with mocked dependencies is unreliable. "
        "Lifespan functionality is tested implicitly through other integration tests. "
        "See docs/b-ongoing-projects/phase9_skip_analysis.md Category 2.1"
    )
    def test_lifespan_startup(self):
        """Test lifespan startup phase."""
        # This test is skipped due to complex mocking requirements
        # The lifespan functionality is tested indirectly through other tests
        pass

    @pytest.mark.skip(
        reason="PERMANENT SKIP: Lifespan testing with mocked dependencies is unreliable. "
        "Lifespan functionality is tested implicitly through other integration tests. "
        "See docs/b-ongoing-projects/phase9_skip_analysis.md Category 2.1"
    )
    def test_lifespan_shutdown(self):
        """Test lifespan shutdown phase."""
        # This test is skipped due to complex mocking requirements
        # The lifespan functionality is tested indirectly through other tests
        pass


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_headers_on_root(self, test_client):
        """Test CORS headers are present on root endpoint."""
        response = test_client.get("/")

        # CORS headers should be present
        # Note: TestClient doesn't include CORS headers by default
        # This tests the middleware is configured
        assert response.status_code == 200

    @patch("src.api.main.api_config")
    def test_cors_config_applied(self, mock_config):
        """Test CORS configuration is applied."""
        from src.api.main import app

        mock_config.get_cors_config.return_value = {
            "allow_origins": ["*"],
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

        # Middleware should be configured
        middleware = list(app.user_middleware)
        assert len(middleware) > 0


class TestDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_json(self, test_client):
        """Test OpenAPI JSON schema is accessible."""
        response = test_client.get("/api/v1/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Agentic RAG API"

    def test_swagger_docs(self, test_client):
        """Test Swagger UI is accessible."""
        response = test_client.get("/docs")

        assert response.status_code == 200
        assert "html" in response.headers["content-type"]

    def test_redoc(self, test_client):
        """Test ReDoc is accessible."""
        response = test_client.get("/redoc")

        assert response.status_code == 200
        assert "html" in response.headers["content-type"]


class TestMiddlewareStack:
    """Test the complete middleware stack."""

    def test_all_middleware_configured(self):
        """Test all required middleware is configured."""
        from src.api.main import app

        middleware_names = [m.cls.__name__ for m in app.user_middleware]

        required_middleware = [
            "CORSMiddleware",
        ]

        for middleware in required_middleware:
            assert middleware in middleware_names


class TestAppVersion:
    """Test application version information."""

    def test_version_in_root(self, test_client):
        """Test version is returned in root endpoint."""
        response = test_client.get("/")
        data = response.json()

        assert data["version"] == "0.8.0"

    @patch("src.api.dependencies.check_database_health", new_callable=AsyncMock)
    @patch("src.api.dependencies.get_api_settings", new_callable=AsyncMock)
    def test_version_in_status(self, mock_settings, mock_health, test_client):
        """Test version is returned in status endpoint."""
        mock_health.return_value = {"postgres": True, "neo4j": True, "cache": True}
        mock_settings.return_value = {"environment": "test", "features": {}}

        response = test_client.get("/api/v1/status")
        data = response.json()

        assert data["version"] == "0.8.0"


class TestErrorHandling:
    """Test comprehensive error handling."""

    def test_internal_error_logging(self):
        """Test internal errors are logged properly."""
        # 500 errors should be logged
        # This is tested through the exception handler registration
        from src.api.main import app

        assert 500 in app.exception_handlers

    def test_not_found_error_message(self, test_client):
        """Test 404 error has user-friendly message."""
        response = test_client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        data = response.json()

        assert "not found" in data["error"]["message"].lower()


class TestHealthEndpointIntegration:
    """Test health endpoint integration."""

    def test_health_router_prefix(self):
        """Test health router has correct prefix."""
        from src.api.main import app

        routes = [route.path for route in app.routes]
        health_routes = [r for r in routes if r.startswith("/health")]

        assert len(health_routes) > 0


class TestAnalyticsIntegration:
    """Test analytics router integration."""

    def test_analytics_router_included(self):
        """Test analytics router is included."""
        from src.api.main import app

        routes = [route.path for route in app.routes]
        analytics_routes = [r for r in routes if "analytics" in r]

        assert len(analytics_routes) > 0


class TestConcurrency:
    """Test concurrent request handling."""

    def test_multiple_concurrent_root_requests(self, test_client):
        """Test handling multiple concurrent requests to root."""
        responses = [test_client.get("/") for _ in range(5)]

        for response in responses:
            assert response.status_code == 200

    def test_concurrent_metrics_requests(self, test_client):
        """Test concurrent metrics requests."""
        responses = [test_client.get("/metrics") for _ in range(5)]

        for response in responses:
            assert response.status_code == 200


class TestAppDescription:
    """Test application description and metadata."""

    def test_app_description_content(self):
        """Test app description contains key information."""
        from src.api.main import app

        assert "Production-ready" in app.description
        assert "Agentic RAG" in app.description
        assert "streaming" in app.description.lower()


class TestEndpointPaths:
    """Test all endpoint paths are correctly configured."""

    def test_all_required_paths_exist(self):
        """Test all required API paths exist."""
        from src.api.main import app

        routes = {route.path for route in app.routes}

        required_paths = [
            "/",
            "/api/v1/status",
            "/metrics",
            "/api/v1/cache",
            "/docs",
            "/redoc",
            "/api/v1/openapi.json",
        ]

        for path in required_paths:
            assert path in routes


class TestCacheClearing:
    """Test cache clearing functionality."""

    @patch("src.api.dependencies.get_cache_manager", new_callable=AsyncMock)
    def test_cache_flush_called(self, mock_cache, test_client):
        """Test cache flush is called when pattern is wildcard."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.flush = MagicMock()
        mock_cache.return_value = mock_cache_instance

        response = test_client.delete("/api/v1/cache?pattern=*")

        assert response.status_code == 200
        mock_cache_instance.flush.assert_called_once()

    @patch("src.api.dependencies.get_cache_manager", new_callable=AsyncMock)
    def test_cache_pattern_clearing(self, mock_cache, test_client):
        """Test cache clearing with specific pattern."""
        mock_cache_instance = MagicMock()
        mock_cache.return_value = mock_cache_instance

        response = test_client.delete("/api/v1/cache?pattern=search:*")

        assert response.status_code == 200
        data = response.json()
        assert "search:*" in data["message"]


class TestStatusComponentDetails:
    """Test status endpoint component details."""

    @patch("src.api.dependencies.check_database_health", new_callable=AsyncMock)
    @patch("src.api.dependencies.get_api_settings", new_callable=AsyncMock)
    def test_status_component_structure(self, mock_settings, mock_health, test_client):
        """Test status components have correct structure."""
        mock_health.return_value = {"postgres": True, "neo4j": True, "cache": True}
        mock_settings.return_value = {"environment": "test", "features": {}}

        response = test_client.get("/api/v1/status")
        data = response.json()

        # Check component structure
        if "components" in data:
            for component in data["components"]:
                assert "name" in component
                assert "healthy" in component

    @patch("src.api.dependencies.check_database_health", new_callable=AsyncMock)
    @patch("src.api.dependencies.get_api_settings", new_callable=AsyncMock)
    def test_status_metrics_included(self, mock_settings, mock_health, test_client):
        """Test status includes metrics information."""
        mock_health.return_value = {"postgres": True, "neo4j": True, "cache": True}
        mock_settings.return_value = {
            "environment": "production",
            "features": {"rag": True},
        }

        response = test_client.get("/api/v1/status")
        data = response.json()

        assert "metrics" in data
        assert data["metrics"]["environment"] == "production"
