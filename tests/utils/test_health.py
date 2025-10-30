"""
Comprehensive tests for health check and monitoring utilities.

Tests system health monitoring across all components.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.health import (
    ComponentHealth,
    HealthChecker,
    HealthStatus,
    health_checker,
)


class TestHealthStatusModel:
    """Test HealthStatus Pydantic model."""

    def test_health_status_creation(self):
        """Test creating a HealthStatus instance."""
        status = HealthStatus(
            status="healthy",
            timestamp=datetime.now(UTC),
            uptime=100.5,
            version="1.0.0",
            checks={
                "database": {"status": "healthy", "response_time": 0.05},
                "llm": {"status": "healthy", "response_time": 0.15},
            },
        )

        assert status.status == "healthy"
        assert status.uptime == 100.5
        assert status.version == "1.0.0"
        assert "database" in status.checks
        assert "llm" in status.checks


class TestComponentHealthModel:
    """Test ComponentHealth Pydantic model."""

    def test_component_health_creation_minimal(self):
        """Test creating ComponentHealth with minimal fields."""
        component = ComponentHealth(
            name="test_component",
            status="healthy",
            last_check=datetime.now(UTC),
        )

        assert component.name == "test_component"
        assert component.status == "healthy"
        assert component.response_time is None
        assert component.error is None
        assert component.details is None

    def test_component_health_creation_full(self):
        """Test creating ComponentHealth with all fields."""
        timestamp = datetime.now(UTC)
        component = ComponentHealth(
            name="test_component",
            status="healthy",
            response_time=0.123,
            error=None,
            last_check=timestamp,
            details={"key": "value"},
        )

        assert component.name == "test_component"
        assert component.status == "healthy"
        assert component.response_time == 0.123
        assert component.details == {"key": "value"}


class TestHealthCheckerInitialization:
    """Test HealthChecker initialization."""

    @patch("src.utils.health.get_settings")
    def test_initialization(self, mock_get_settings):
        """Test HealthChecker initialization."""
        mock_settings = MagicMock()
        mock_settings.app_version = "1.2.3"
        mock_settings.health_check_interval = 60
        mock_get_settings.return_value = mock_settings

        checker = HealthChecker()

        assert checker.version == "1.2.3"
        assert checker.check_interval == 60
        assert checker.component_checks == {}
        assert checker.last_full_check is None
        assert isinstance(checker.start_time, float)


class TestDatabaseHealthCheck:
    """Test database health check functionality."""

    @pytest.mark.asyncio
    @patch("src.utils.health.get_supabase_client")
    async def test_check_database_health_success(self, mock_get_client):
        """Test successful database health check."""
        mock_supabase = MagicMock()
        mock_get_client.return_value = mock_supabase

        mock_result = MagicMock()
        mock_result.data = [{"health_check": 1}]
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        checker = HealthChecker()
        result = await checker.check_database_health()

        assert result.name == "database"
        assert result.status == "healthy"
        assert result.response_time is not None
        assert result.response_time > 0
        assert result.error is None
        assert result.details == {"connection": "ok", "query_time": result.response_time}

    @pytest.mark.asyncio
    @patch("src.utils.health.get_supabase_client")
    async def test_check_database_health_empty_response(self, mock_get_client):
        """Test database health check with empty response."""
        mock_supabase = MagicMock()
        mock_get_client.return_value = mock_supabase

        mock_result = MagicMock()
        mock_result.data = []  # Empty response
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        checker = HealthChecker()
        result = await checker.check_database_health()

        assert result.name == "database"
        assert result.status == "degraded"
        assert result.error == "Empty response from database"

    @pytest.mark.asyncio
    @patch("src.utils.health.get_supabase_client")
    async def test_check_database_health_exception(self, mock_get_client):
        """Test database health check with exception."""
        mock_get_client.side_effect = Exception("Connection failed")

        checker = HealthChecker()
        result = await checker.check_database_health()

        assert result.name == "database"
        assert result.status == "unhealthy"
        assert "Connection failed" in result.error

    @pytest.mark.asyncio
    @patch("src.utils.health.get_supabase_client", None)
    async def test_check_database_health_client_not_available(self):
        """Test database health check when client not available."""
        checker = HealthChecker()
        result = await checker.check_database_health()

        assert result.name == "database"
        assert result.status == "unhealthy"
        assert "not available" in result.error


class TestLLMHealthCheck:
    """Test LLM health check functionality."""

    @pytest.mark.asyncio
    @patch("src.utils.health.get_settings")
    @patch("src.utils.health.get_llm_client")
    async def test_check_llm_health_success(self, mock_get_client, mock_get_settings):
        """Test successful LLM health check."""
        mock_settings = MagicMock()
        mock_settings.llm_choice = "gpt-4"
        mock_get_settings.return_value = mock_settings

        mock_llm = AsyncMock()
        mock_get_client.return_value = mock_llm

        mock_response = MagicMock()
        mock_response.model = "gpt-4"
        mock_response.choices = [MagicMock()]
        mock_response.usage = MagicMock(total_tokens=10)
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)

        checker = HealthChecker()
        result = await checker.check_llm_health()

        assert result.name == "llm"
        assert result.status == "healthy"
        assert result.response_time is not None
        assert result.error is None
        assert result.details["model"] == "gpt-4"
        assert result.details["tokens_used"] == 10

    @pytest.mark.asyncio
    @patch("src.utils.health.get_settings")
    @patch("src.utils.health.get_llm_client")
    async def test_check_llm_health_empty_response(self, mock_get_client, mock_get_settings):
        """Test LLM health check with empty response."""
        mock_settings = MagicMock()
        mock_settings.llm_choice = "gpt-4"
        mock_get_settings.return_value = mock_settings

        mock_llm = AsyncMock()
        mock_get_client.return_value = mock_llm

        mock_response = MagicMock()
        mock_response.choices = []  # Empty choices
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)

        checker = HealthChecker()
        result = await checker.check_llm_health()

        assert result.name == "llm"
        assert result.status == "degraded"
        assert result.error == "Empty response from LLM"

    @pytest.mark.asyncio
    @patch("src.utils.health.get_llm_client")
    async def test_check_llm_health_exception(self, mock_get_client):
        """Test LLM health check with exception."""
        mock_get_client.side_effect = Exception("API error")

        checker = HealthChecker()
        result = await checker.check_llm_health()

        assert result.name == "llm"
        assert result.status == "unhealthy"
        assert "API error" in result.error

    @pytest.mark.asyncio
    @patch("src.utils.health.get_llm_client", None)
    async def test_check_llm_health_client_not_available(self):
        """Test LLM health check when client not available."""
        checker = HealthChecker()
        result = await checker.check_llm_health()

        assert result.name == "llm"
        assert result.status == "unhealthy"
        assert "not available" in result.error


class TestEmbeddingHealthCheck:
    """Test embedding health check functionality."""

    @pytest.mark.asyncio
    @patch("src.utils.health.get_settings")
    @patch("src.utils.health.get_embedding_client")
    async def test_check_embedding_health_success(self, mock_get_client, mock_get_settings):
        """Test successful embedding health check."""
        mock_settings = MagicMock()
        mock_settings.embedding_model_choice = "text-embedding-ada-002"
        mock_get_settings.return_value = mock_settings

        mock_embedding_client = AsyncMock()
        mock_get_client.return_value = mock_embedding_client

        mock_response = MagicMock()
        mock_response.model = "text-embedding-ada-002"
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_embedding_client.embeddings.create = AsyncMock(return_value=mock_response)

        checker = HealthChecker()
        result = await checker.check_embedding_health()

        assert result.name == "embedding"
        assert result.status == "healthy"
        assert result.response_time is not None
        assert result.error is None
        assert result.details["model"] == "text-embedding-ada-002"
        assert result.details["embedding_dim"] == 1536

    @pytest.mark.asyncio
    @patch("src.utils.health.get_settings")
    @patch("src.utils.health.get_embedding_client")
    async def test_check_embedding_health_empty_response(self, mock_get_client, mock_get_settings):
        """Test embedding health check with empty response."""
        mock_settings = MagicMock()
        mock_settings.embedding_model_choice = "text-embedding-ada-002"
        mock_get_settings.return_value = mock_settings

        mock_embedding_client = AsyncMock()
        mock_get_client.return_value = mock_embedding_client

        mock_response = MagicMock()
        mock_response.data = []  # Empty data
        mock_embedding_client.embeddings.create = AsyncMock(return_value=mock_response)

        checker = HealthChecker()
        result = await checker.check_embedding_health()

        assert result.name == "embedding"
        assert result.status == "degraded"
        assert result.error == "Empty response from embedding service"

    @pytest.mark.asyncio
    @patch("src.utils.health.get_embedding_client")
    async def test_check_embedding_health_exception(self, mock_get_client):
        """Test embedding health check with exception."""
        mock_get_client.side_effect = Exception("Embedding service error")

        checker = HealthChecker()
        result = await checker.check_embedding_health()

        assert result.name == "embedding"
        assert result.status == "unhealthy"
        assert "Embedding service error" in result.error

    @pytest.mark.asyncio
    @patch("src.utils.health.get_embedding_client", None)
    async def test_check_embedding_health_client_not_available(self):
        """Test embedding health check when client not available."""
        checker = HealthChecker()
        result = await checker.check_embedding_health()

        assert result.name == "embedding"
        assert result.status == "unhealthy"
        assert "not available" in result.error


class TestMemoryHealthCheck:
    """Test memory health check functionality."""

    @pytest.mark.asyncio
    @patch("src.utils.health.get_mem0_client")
    async def test_check_memory_health_success(self, mock_get_client):
        """Test successful memory health check."""
        mock_memory_client = MagicMock()
        mock_get_client.return_value = mock_memory_client

        mock_memory_client.add.return_value = {"id": "test_memory_123"}
        mock_memory_client.delete.return_value = True

        checker = HealthChecker()
        result = await checker.check_memory_health()

        assert result.name == "memory"
        assert result.status == "healthy"
        assert result.response_time is not None
        assert result.error is None
        assert result.details["test_memory_id"] == "test_memory_123"
        mock_memory_client.add.assert_called_once()
        mock_memory_client.delete.assert_called_once_with("test_memory_123")

    @pytest.mark.asyncio
    @patch("src.utils.health.get_mem0_client")
    async def test_check_memory_health_no_id_returned(self, mock_get_client):
        """Test memory health check when no ID returned."""
        mock_memory_client = MagicMock()
        mock_get_client.return_value = mock_memory_client

        mock_memory_client.add.return_value = {}  # No ID

        checker = HealthChecker()
        result = await checker.check_memory_health()

        assert result.name == "memory"
        assert result.status == "degraded"
        assert result.error == "Failed to create test memory"

    @pytest.mark.asyncio
    @patch("src.utils.health.get_mem0_client")
    async def test_check_memory_health_exception(self, mock_get_client):
        """Test memory health check with exception."""
        mock_get_client.side_effect = Exception("Memory service error")

        checker = HealthChecker()
        result = await checker.check_memory_health()

        assert result.name == "memory"
        assert result.status == "unhealthy"
        assert "Memory service error" in result.error

    @pytest.mark.asyncio
    @patch("src.utils.health.get_mem0_client", None)
    async def test_check_memory_health_client_not_available(self):
        """Test memory health check when client not available."""
        checker = HealthChecker()
        result = await checker.check_memory_health()

        assert result.name == "memory"
        assert result.status == "unhealthy"
        assert "not available" in result.error


class TestWebSearchHealthCheck:
    """Test web search health check functionality."""

    @pytest.mark.asyncio
    @patch("src.utils.health.get_settings")
    @patch("src.utils.health.httpx.AsyncClient")
    async def test_check_web_search_health_brave_success(self, mock_client_class, mock_settings):
        """Test successful web search health check with Brave."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.brave_api_key = "test_brave_key"
        mock_settings_obj.searxng_base_url = None
        mock_settings.return_value = mock_settings_obj

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)

        checker = HealthChecker()
        result = await checker.check_web_search_health()

        assert result.name == "web_search"
        assert result.status == "healthy"
        assert result.details["provider"] == "brave"
        assert result.details["status_code"] == 200

    @pytest.mark.asyncio
    @patch("src.utils.health.get_settings")
    @patch("src.utils.health.httpx.AsyncClient")
    async def test_check_web_search_health_brave_degraded(self, mock_client_class, mock_settings):
        """Test web search health check with Brave returning non-200."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.brave_api_key = "test_brave_key"
        mock_settings_obj.searxng_base_url = None
        mock_settings.return_value = mock_settings_obj

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 429  # Rate limited
        mock_client.get = AsyncMock(return_value=mock_response)

        checker = HealthChecker()
        result = await checker.check_web_search_health()

        assert result.name == "web_search"
        assert result.status == "degraded"
        assert "429" in result.error

    @pytest.mark.asyncio
    @patch("src.utils.health.get_settings")
    @patch("src.utils.health.httpx.AsyncClient")
    async def test_check_web_search_health_searxng_success(self, mock_client_class, mock_settings):
        """Test successful web search health check with SearXNG."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.brave_api_key = None
        mock_settings_obj.searxng_base_url = "http://searxng.local"
        mock_settings.return_value = mock_settings_obj

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)

        checker = HealthChecker()
        result = await checker.check_web_search_health()

        assert result.name == "web_search"
        assert result.status == "healthy"
        assert result.details["provider"] == "searxng"

    @pytest.mark.asyncio
    @patch("src.utils.health.get_settings")
    async def test_check_web_search_health_no_provider(self, mock_settings):
        """Test web search health check with no provider configured."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.brave_api_key = None
        mock_settings_obj.searxng_base_url = None
        mock_settings.return_value = mock_settings_obj

        checker = HealthChecker()
        result = await checker.check_web_search_health()

        assert result.name == "web_search"
        assert result.status == "unhealthy"
        assert "No web search provider configured" in result.error

    @pytest.mark.asyncio
    @patch("src.utils.health.get_settings")
    @patch("src.utils.health.httpx.AsyncClient")
    async def test_check_web_search_health_exception(self, mock_client_class, mock_settings):
        """Test web search health check with exception."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.brave_api_key = "test_brave_key"
        mock_settings_obj.searxng_base_url = None
        mock_settings.return_value = mock_settings_obj

        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))

        checker = HealthChecker()
        result = await checker.check_web_search_health()

        assert result.name == "web_search"
        assert result.status == "unhealthy"
        assert "Network error" in result.error


class TestRunAllChecks:
    """Test running all health checks concurrently."""

    @pytest.mark.asyncio
    async def test_run_all_checks(self):
        """Test running all health checks concurrently."""
        checker = HealthChecker()

        # Mock all check methods
        mock_db_check = AsyncMock(
            return_value=ComponentHealth(
                name="database", status="healthy", last_check=datetime.now(UTC)
            )
        )
        mock_llm_check = AsyncMock(
            return_value=ComponentHealth(name="llm", status="healthy", last_check=datetime.now(UTC))
        )
        mock_embedding_check = AsyncMock(
            return_value=ComponentHealth(
                name="embedding", status="degraded", last_check=datetime.now(UTC)
            )
        )
        mock_memory_check = AsyncMock(
            return_value=ComponentHealth(
                name="memory", status="unhealthy", last_check=datetime.now(UTC)
            )
        )
        mock_web_search_check = AsyncMock(
            return_value=ComponentHealth(
                name="web_search", status="healthy", last_check=datetime.now(UTC)
            )
        )

        checker.check_database_health = mock_db_check
        checker.check_llm_health = mock_llm_check
        checker.check_embedding_health = mock_embedding_check
        checker.check_memory_health = mock_memory_check
        checker.check_web_search_health = mock_web_search_check

        results = await checker.run_all_checks()

        assert len(results) == 5
        assert any(r.name == "database" and r.status == "healthy" for r in results)
        assert any(r.name == "llm" and r.status == "healthy" for r in results)
        assert any(r.name == "embedding" and r.status == "degraded" for r in results)
        assert any(r.name == "memory" and r.status == "unhealthy" for r in results)
        assert any(r.name == "web_search" and r.status == "healthy" for r in results)
        assert checker.last_full_check is not None

    @pytest.mark.asyncio
    async def test_run_all_checks_with_exceptions(self):
        """Test running all checks handles exceptions gracefully."""
        checker = HealthChecker()

        # Mock some checks to raise exceptions
        checker.check_database_health = AsyncMock(side_effect=Exception("DB error"))
        checker.check_llm_health = AsyncMock(
            return_value=ComponentHealth(name="llm", status="healthy", last_check=datetime.now(UTC))
        )
        checker.check_embedding_health = AsyncMock(side_effect=Exception("Embedding error"))
        checker.check_memory_health = AsyncMock(
            return_value=ComponentHealth(
                name="memory", status="healthy", last_check=datetime.now(UTC)
            )
        )
        checker.check_web_search_health = AsyncMock(
            return_value=ComponentHealth(
                name="web_search", status="healthy", last_check=datetime.now(UTC)
            )
        )

        results = await checker.run_all_checks()

        assert len(results) == 5
        # Check that exceptions were converted to unhealthy components
        unhealthy_count = sum(1 for r in results if r.status == "unhealthy")
        assert unhealthy_count == 2


class TestGetHealthStatus:
    """Test getting overall health status."""

    @pytest.mark.asyncio
    @patch("src.utils.health.monitor")
    async def test_get_health_status_all_healthy(self, mock_monitor):
        """Test get_health_status when all components are healthy."""
        mock_monitor.get_system_stats.return_value = {
            "uptime": 1000,
            "active_requests": 5,
            "active_sessions": 10,
            "cpu_percent": 50.0,
            "memory_usage": 60.0,
            "disk_usage": 70.0,
        }

        checker = HealthChecker()

        # Mock run_all_checks
        checker.run_all_checks = AsyncMock(
            return_value=[
                ComponentHealth(
                    name="database",
                    status="healthy",
                    response_time=0.05,
                    last_check=datetime.now(UTC),
                    details={"connection": "ok"},
                ),
                ComponentHealth(
                    name="llm",
                    status="healthy",
                    response_time=0.15,
                    last_check=datetime.now(UTC),
                ),
            ]
        )

        status = await checker.get_health_status()

        assert status.status == "healthy"
        assert "database" in status.checks
        assert "llm" in status.checks
        assert "system" in status.checks
        assert status.checks["system"]["status"] == "healthy"

    @pytest.mark.asyncio
    @patch("src.utils.health.monitor")
    async def test_get_health_status_degraded(self, mock_monitor):
        """Test get_health_status when some components are degraded."""
        mock_monitor.get_system_stats.return_value = {
            "uptime": 1000,
            "active_requests": 5,
            "active_sessions": 10,
            "cpu_percent": 50.0,
            "memory_usage": 60.0,
            "disk_usage": 70.0,
        }

        checker = HealthChecker()

        # Mock run_all_checks
        checker.run_all_checks = AsyncMock(
            return_value=[
                ComponentHealth(
                    name="database",
                    status="healthy",
                    response_time=0.05,
                    last_check=datetime.now(UTC),
                ),
                ComponentHealth(
                    name="llm",
                    status="degraded",
                    response_time=2.5,
                    last_check=datetime.now(UTC),
                    error="Slow response",
                ),
            ]
        )

        status = await checker.get_health_status()

        assert status.status == "degraded"
        assert status.checks["llm"]["status"] == "degraded"
        assert status.checks["llm"]["error"] == "Slow response"

    @pytest.mark.asyncio
    @patch("src.utils.health.monitor")
    async def test_get_health_status_unhealthy(self, mock_monitor):
        """Test get_health_status when components are unhealthy."""
        mock_monitor.get_system_stats.return_value = {
            "uptime": 1000,
            "active_requests": 5,
            "active_sessions": 10,
            "cpu_percent": 50.0,
            "memory_usage": 60.0,
            "disk_usage": 70.0,
        }

        checker = HealthChecker()

        # Mock run_all_checks
        checker.run_all_checks = AsyncMock(
            return_value=[
                ComponentHealth(
                    name="database",
                    status="healthy",
                    response_time=0.05,
                    last_check=datetime.now(UTC),
                ),
                ComponentHealth(
                    name="llm",
                    status="unhealthy",
                    response_time=None,
                    last_check=datetime.now(UTC),
                    error="Connection failed",
                ),
            ]
        )

        status = await checker.get_health_status()

        assert status.status == "unhealthy"
        assert status.checks["llm"]["status"] == "unhealthy"
        assert status.checks["llm"]["error"] == "Connection failed"

    @pytest.mark.asyncio
    @patch("src.utils.health.monitor")
    async def test_get_health_status_system_degraded(self, mock_monitor):
        """Test get_health_status includes degraded system stats."""
        mock_monitor.get_system_stats.return_value = {
            "uptime": 1000,
            "active_requests": 5,
            "active_sessions": 10,
            "cpu_percent": 85.0,  # High CPU
            "memory_usage": 75.0,
            "disk_usage": 92.0,  # High disk usage
        }

        checker = HealthChecker()

        # Mock run_all_checks
        checker.run_all_checks = AsyncMock(
            return_value=[
                ComponentHealth(
                    name="database",
                    status="healthy",
                    response_time=0.05,
                    last_check=datetime.now(UTC),
                ),
            ]
        )

        status = await checker.get_health_status()

        # Overall status is healthy (only components affect overall status)
        assert status.status == "healthy"
        # But system stats should show degraded
        assert status.checks["system"]["status"] == "degraded"
        assert status.checks["system"]["cpu_percent"] == 85.0
        assert status.checks["system"]["disk_usage"] == 92.0


class TestGlobalHealthChecker:
    """Test global health checker instance."""

    def test_global_health_checker_instance(self):
        """Test that global health_checker is initialized."""
        assert health_checker is not None
        assert isinstance(health_checker, HealthChecker)
        assert hasattr(health_checker, "start_time")
        assert hasattr(health_checker, "version")
