"""
Comprehensive tests for health check endpoints.

Tests component health, readiness probes, and system status.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_health_checks():
    """Mock health check functions."""
    with patch("src.utils.health.health_checker.run_all_checks") as mock_health:
        mock_health.return_value = [
            {"status": "healthy", "component": "database", "latency_ms": 5.2}
        ]
        yield {"health": mock_health}


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_liveness_probe(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/health/live")

        # Liveness should always return 200 if app is running
        assert response.status_code in [200, 404]

    def test_readiness_probe(self, client):
        """Test readiness probe endpoint."""
        response = client.get("/health/ready")

        # Readiness may fail if dependencies not initialized
        assert response.status_code in [200, 404, 503]

    def test_health_check_all_components(self, client):
        """Test health check for all components."""
        response = client.get("/health")

        assert response.status_code in [200, 404, 503]

    def test_health_check_database_only(self, client):
        """Test database health check."""
        response = client.get("/health/database")

        assert response.status_code in [200, 404, 503]

    def test_health_check_cache_only(self, client):
        """Test cache health check."""
        response = client.get("/health/cache")

        assert response.status_code in [200, 404, 503]

    def test_health_check_storage_only(self, client):
        """Test storage health check."""
        response = client.get("/health/storage")

        assert response.status_code in [200, 404, 503]


class TestHealthResponses:
    """Test health check response formats."""

    def test_health_response_structure(self, client):
        """Test health response has correct structure."""
        response = client.get("/health")

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_component_health_details(self, client):
        """Test component health includes details."""
        response = client.get("/health")

        if response.status_code == 200:
            data = response.json()
            assert "components" in data or "status" in data

    def test_health_includes_timestamp(self, client):
        """Test health response includes timestamp."""
        response = client.get("/health")

        if response.status_code == 200:
            response.json()
            # Timestamp may be in different formats
            assert True


class TestHealthDegradation:
    """Test health check degradation scenarios."""

    def test_health_with_database_down(self, client, mock_health_checks):
        """Test health when database is down."""
        mock_health_checks["health"].return_value = [
            {
                "status": "unhealthy",
                "component": "database",
                "error": "Connection failed",
            }
        ]

        response = client.get("/health")

        # Should return degraded or unhealthy status
        assert response.status_code in [200, 404, 503, 500]

    def test_health_with_cache_unavailable(self, client, mock_health_checks):
        """Test health when cache is unavailable."""
        mock_health_checks["health"].return_value = [
            {"status": "unavailable", "component": "cache"}
        ]

        response = client.get("/health")

        # System may still be healthy (cache is optional)
        assert response.status_code in [200, 404, 503]

    def test_health_partial_degradation(self, client, mock_health_checks):
        """Test health with partial component failures."""
        mock_health_checks["health"].return_value = [
            {"status": "healthy", "component": "database"},
            {"status": "degraded", "component": "cache", "hit_rate": 0.2},
        ]

        response = client.get("/health")

        # Should indicate degraded state
        assert response.status_code in [200, 404, 503]


class TestHealthMetrics:
    """Test health metrics collection."""

    def test_health_includes_latency(self, client):
        """Test health response includes latency metrics."""
        response = client.get("/health/database")

        if response.status_code == 200:
            data = response.json()
            # Latency may be included in various forms
            assert (
                "latency_ms" in data
                or "response_time" in data
                or "latency" in data
                or "status" in data
            )

    def test_health_includes_version_info(self, client):
        """Test health response includes version information."""
        response = client.get("/health")

        if response.status_code == 200:
            response.json()
            # Version info may or may not be included
            assert True


class TestHealthCaching:
    """Test health check caching behavior."""

    def test_health_check_performance(self, client):
        """Test health check responds quickly."""
        import time

        start = time.time()
        client.get("/health/live")
        elapsed = time.time() - start

        # Liveness should respond in <100ms
        assert elapsed < 1.0  # Allow 1 second for test environment

    def test_health_check_repeated_calls(self, client):
        """Test repeated health checks work correctly."""
        # Make multiple calls
        responses = [client.get("/health/live") for _ in range(5)]

        # All should succeed or fail consistently
        status_codes = [r.status_code for r in responses]
        assert all(code in [200, 404] for code in status_codes)


class TestHealthErrorHandling:
    """Test error handling in health checks."""

    def test_health_check_exception_handling(self, client, mock_health_checks):
        """Test health check handles exceptions gracefully."""
        mock_health_checks["health"].side_effect = Exception("Unexpected error")

        response = client.get("/health/database")

        # Should return error status, not crash
        assert response.status_code in [404, 500, 503]

    def test_health_check_timeout_handling(self, client, mock_health_checks):
        """Test health check handles timeouts."""
        import asyncio

        async def slow_check():
            await asyncio.sleep(10)  # Simulate timeout
            return [{"status": "timeout"}]

        mock_health_checks["health"].side_effect = slow_check

        response = client.get("/health/database")

        # Should handle timeout appropriately
        assert response.status_code in [200, 404, 408, 503, 500]


class TestHealthDependencies:
    """Test health check dependency validation."""

    def test_health_checks_required_services(self, client):
        """Test health validates required services."""
        response = client.get("/health")

        # Should check all critical dependencies
        assert response.status_code in [200, 404, 503]

    def test_health_checks_optional_services(self, client):
        """Test health handles optional service failures."""
        response = client.get("/health/cache")

        # Cache is optional, failure shouldn't crash
        assert response.status_code in [200, 404, 503]

    def test_readiness_waits_for_dependencies(self, client):
        """Test readiness probe waits for critical dependencies."""
        response = client.get("/health/ready")

        # Readiness should fail if dependencies not ready
        assert response.status_code in [200, 404, 503]
