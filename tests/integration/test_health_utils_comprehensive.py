"""
Comprehensive integration tests for utils/health.py.

Tests health checking system for all components.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def health_checker():
    """Create HealthChecker instance."""
    from src.utils.health import HealthChecker

    return HealthChecker()


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = MagicMock()
    return client


class TestHealthCheckerInit:
    """Test HealthChecker initialization."""

    def test_health_checker_initialization(self):
        """Test HealthChecker initializes correctly."""
        from src.utils.health import HealthChecker

        checker = HealthChecker()

        assert checker is not None
        assert checker.start_time > 0
        assert isinstance(checker.version, str)

    @patch("src.utils.health.get_settings")
    def test_health_checker_loads_settings(self, mock_settings):
        """Test settings are loaded on init."""
        from src.utils.health import HealthChecker

        mock_settings.return_value = MagicMock(
            app_version="1.0.0",
            health_check_interval=60,
        )

        checker = HealthChecker()

        assert checker.version == "1.0.0"
        assert checker.check_interval == 60


class TestCheckDatabaseHealth:
    """Test database health checking."""

    @patch("src.utils.health.get_supabase_client")
    async def test_database_health_check_healthy(
        self, mock_get_client, health_checker, mock_supabase
    ):
        """Test successful database health check."""
        mock_get_client.return_value = mock_supabase

        mock_result = MagicMock()
        mock_result.data = [{"health_check": 1}]

        mock_supabase.rpc.return_value.execute.return_value = mock_result

        health = await health_checker.check_database_health()

        assert health.status == "healthy"
        assert health.name == "database"
        assert health.response_time is not None
        assert health.response_time > 0

    @patch("src.utils.health.get_supabase_client")
    async def test_database_health_check_degraded(
        self, mock_get_client, health_checker, mock_supabase
    ):
        """Test degraded database health."""
        mock_get_client.return_value = mock_supabase

        mock_result = MagicMock()
        mock_result.data = []

        mock_supabase.rpc.return_value.execute.return_value = mock_result

        health = await health_checker.check_database_health()

        assert health.status == "degraded"
        assert health.error is not None

    @patch("src.utils.health.get_supabase_client")
    async def test_database_health_check_unhealthy(self, mock_get_client, health_checker):
        """Test unhealthy database."""
        mock_get_client.side_effect = Exception("Connection failed")

        health = await health_checker.check_database_health()

        assert health.status == "unhealthy"
        assert "Connection failed" in health.error

    @patch("src.utils.health.get_supabase_client")
    async def test_database_health_check_missing_client(self, mock_get_client, health_checker):
        """Test database check when client not available."""
        # Simulate ImportError
        with patch("src.utils.health.get_supabase_client", None):
            health = await health_checker.check_database_health()

            assert health.status == "unhealthy"


class TestCheckLLMHealth:
    """Test LLM health checking."""

    @patch("src.utils.health.get_llm_client")
    @patch("src.utils.health.get_settings")
    async def test_llm_health_check_healthy(
        self, mock_settings, mock_get_client, health_checker, mock_llm_client
    ):
        """Test successful LLM health check."""
        mock_settings.return_value = MagicMock(llm_choice="gpt-4")
        mock_get_client.return_value = mock_llm_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.model = "gpt-4"
        mock_response.usage = MagicMock(total_tokens=10)

        mock_llm_client.chat.completions.create = AsyncMock(return_value=mock_response)

        health = await health_checker.check_llm_health()

        assert health.status == "healthy"
        assert health.name == "llm"
        assert health.details["model"] == "gpt-4"

    @patch("src.utils.health.get_llm_client")
    @patch("src.utils.health.get_settings")
    async def test_llm_health_check_degraded(
        self, mock_settings, mock_get_client, health_checker, mock_llm_client
    ):
        """Test degraded LLM health."""
        mock_settings.return_value = MagicMock(llm_choice="gpt-4")
        mock_get_client.return_value = mock_llm_client

        mock_response = MagicMock()
        mock_response.choices = []

        mock_llm_client.chat.completions.create = AsyncMock(return_value=mock_response)

        health = await health_checker.check_llm_health()

        assert health.status == "degraded"

    @patch("src.utils.health.get_llm_client")
    async def test_llm_health_check_unhealthy(self, mock_get_client, health_checker):
        """Test unhealthy LLM."""
        mock_get_client.side_effect = Exception("LLM connection failed")

        health = await health_checker.check_llm_health()

        assert health.status == "unhealthy"
        assert "LLM connection failed" in health.error


class TestCheckEmbeddingHealth:
    """Test embedding service health checking."""

    @patch("src.utils.health.get_embedding_client")
    @patch("src.utils.health.get_settings")
    async def test_embedding_health_check_healthy(
        self, mock_settings, mock_get_client, health_checker
    ):
        """Test successful embedding health check."""
        mock_settings.return_value = MagicMock(embedding_model_choice="text-embedding-3-small")
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_response.model = "text-embedding-3-small"

        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        health = await health_checker.check_embedding_health()

        assert health.status == "healthy"
        assert health.name == "embedding"
        assert health.details["embedding_dim"] == 1536

    @patch("src.utils.health.get_embedding_client")
    async def test_embedding_health_check_unhealthy(self, mock_get_client, health_checker):
        """Test unhealthy embedding service."""
        mock_get_client.side_effect = Exception("Embedding service down")

        health = await health_checker.check_embedding_health()

        assert health.status == "unhealthy"


class TestCheckMemoryHealth:
    """Test memory service health checking."""

    @patch("src.utils.health.get_mem0_client")
    async def test_memory_health_check_healthy(self, mock_get_client, health_checker):
        """Test successful memory health check."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.add.return_value = {"id": "test-id"}
        mock_client.delete = MagicMock()

        health = await health_checker.check_memory_health()

        assert health.status == "healthy"
        assert health.name == "memory"
        assert mock_client.add.called

    @patch("src.utils.health.get_mem0_client")
    async def test_memory_health_check_degraded(self, mock_get_client, health_checker):
        """Test degraded memory health."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.add.return_value = {}

        health = await health_checker.check_memory_health()

        assert health.status == "degraded"

    @patch("src.utils.health.get_mem0_client")
    async def test_memory_health_check_unhealthy(self, mock_get_client, health_checker):
        """Test unhealthy memory service."""
        mock_get_client.side_effect = Exception("Memory service error")

        health = await health_checker.check_memory_health()

        assert health.status == "unhealthy"


class TestCheckWebSearchHealth:
    """Test web search service health checking."""

    @patch("src.utils.health.httpx.AsyncClient")
    @patch("src.utils.health.get_settings")
    async def test_web_search_brave_healthy(self, mock_settings, mock_async_client, health_checker):
        """Test successful Brave web search health check."""
        mock_settings.return_value = MagicMock(
            brave_api_key="test-key",
            searxng_base_url=None,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.return_value = mock_client_instance

        health = await health_checker.check_web_search_health()

        assert health.status == "healthy"
        assert health.details["provider"] == "brave"

    @patch("src.utils.health.httpx.AsyncClient")
    @patch("src.utils.health.get_settings")
    async def test_web_search_searxng_healthy(
        self, mock_settings, mock_async_client, health_checker
    ):
        """Test successful SearXNG health check."""
        mock_settings.return_value = MagicMock(
            brave_api_key=None,
            searxng_base_url="https://searxng.local",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.return_value = mock_client_instance

        health = await health_checker.check_web_search_health()

        assert health.status == "healthy"
        assert health.details["provider"] == "searxng"

    @patch("src.utils.health.get_settings")
    async def test_web_search_no_provider(self, mock_settings, health_checker):
        """Test web search health when no provider configured."""
        mock_settings.return_value = MagicMock(
            brave_api_key=None,
            searxng_base_url=None,
        )

        health = await health_checker.check_web_search_health()

        assert health.status == "unhealthy"
        assert "No web search provider configured" in health.error

    @patch("src.utils.health.httpx.AsyncClient")
    @patch("src.utils.health.get_settings")
    async def test_web_search_degraded(self, mock_settings, mock_async_client, health_checker):
        """Test degraded web search."""
        mock_settings.return_value = MagicMock(
            brave_api_key="test-key",
            searxng_base_url=None,
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        mock_async_client.return_value = mock_client_instance

        health = await health_checker.check_web_search_health()

        assert health.status == "degraded"


class TestRunAllChecks:
    """Test running all health checks."""

    @patch("src.utils.health.HealthChecker.check_database_health")
    @patch("src.utils.health.HealthChecker.check_llm_health")
    @patch("src.utils.health.HealthChecker.check_embedding_health")
    @patch("src.utils.health.HealthChecker.check_memory_health")
    @patch("src.utils.health.HealthChecker.check_web_search_health")
    async def test_run_all_checks_success(
        self, mock_web, mock_memory, mock_embedding, mock_llm, mock_db, health_checker
    ):
        """Test running all checks successfully."""
        from src.utils.health import ComponentHealth

        mock_db.return_value = ComponentHealth(
            name="database", status="healthy", last_check=datetime.utcnow()
        )
        mock_llm.return_value = ComponentHealth(
            name="llm", status="healthy", last_check=datetime.utcnow()
        )
        mock_embedding.return_value = ComponentHealth(
            name="embedding", status="healthy", last_check=datetime.utcnow()
        )
        mock_memory.return_value = ComponentHealth(
            name="memory", status="healthy", last_check=datetime.utcnow()
        )
        mock_web.return_value = ComponentHealth(
            name="web_search", status="healthy", last_check=datetime.utcnow()
        )

        checks = await health_checker.run_all_checks()

        assert len(checks) == 5
        assert all(check.status == "healthy" for check in checks)

    @patch("src.utils.health.HealthChecker.check_database_health")
    @patch("src.utils.health.HealthChecker.check_llm_health")
    @patch("src.utils.health.HealthChecker.check_embedding_health")
    @patch("src.utils.health.HealthChecker.check_memory_health")
    @patch("src.utils.health.HealthChecker.check_web_search_health")
    async def test_run_all_checks_handles_exceptions(
        self, mock_web, mock_memory, mock_embedding, mock_llm, mock_db, health_checker
    ):
        """Test running all checks handles exceptions."""
        from src.utils.health import ComponentHealth

        mock_db.side_effect = Exception("Database exception")
        mock_llm.return_value = ComponentHealth(
            name="llm", status="healthy", last_check=datetime.utcnow()
        )
        mock_embedding.return_value = ComponentHealth(
            name="embedding", status="healthy", last_check=datetime.utcnow()
        )
        mock_memory.return_value = ComponentHealth(
            name="memory", status="healthy", last_check=datetime.utcnow()
        )
        mock_web.return_value = ComponentHealth(
            name="web_search", status="healthy", last_check=datetime.utcnow()
        )

        checks = await health_checker.run_all_checks()

        # Should handle exception and return other checks
        assert len(checks) == 5


class TestGetHealthStatus:
    """Test overall health status."""

    @patch("src.utils.health.HealthChecker.run_all_checks")
    @patch("src.utils.health.monitor")
    async def test_get_health_status_healthy(self, mock_monitor, mock_run_checks, health_checker):
        """Test overall status when all healthy."""
        from src.utils.health import ComponentHealth

        mock_run_checks.return_value = [
            ComponentHealth(name="db", status="healthy", last_check=datetime.utcnow()),
            ComponentHealth(name="llm", status="healthy", last_check=datetime.utcnow()),
        ]

        mock_monitor.get_system_stats.return_value = {
            "cpu_percent": 50,
            "memory_usage": 60,
            "disk_usage": 70,
            "uptime": 3600,
            "active_requests": 5,
            "active_sessions": 10,
        }

        status = await health_checker.get_health_status()

        assert status.status == "healthy"
        assert len(status.checks) == 3  # 2 components + system

    @patch("src.utils.health.HealthChecker.run_all_checks")
    @patch("src.utils.health.monitor")
    async def test_get_health_status_degraded(self, mock_monitor, mock_run_checks, health_checker):
        """Test overall status when some degraded."""
        from src.utils.health import ComponentHealth

        mock_run_checks.return_value = [
            ComponentHealth(name="db", status="healthy", last_check=datetime.utcnow()),
            ComponentHealth(name="llm", status="degraded", last_check=datetime.utcnow()),
        ]

        mock_monitor.get_system_stats.return_value = {
            "cpu_percent": 50,
            "memory_usage": 60,
            "disk_usage": 70,
            "uptime": 3600,
            "active_requests": 5,
            "active_sessions": 10,
        }

        status = await health_checker.get_health_status()

        assert status.status == "degraded"

    @patch("src.utils.health.HealthChecker.run_all_checks")
    @patch("src.utils.health.monitor")
    async def test_get_health_status_unhealthy(self, mock_monitor, mock_run_checks, health_checker):
        """Test overall status when some unhealthy."""
        from src.utils.health import ComponentHealth

        mock_run_checks.return_value = [
            ComponentHealth(name="db", status="unhealthy", last_check=datetime.utcnow()),
            ComponentHealth(name="llm", status="healthy", last_check=datetime.utcnow()),
        ]

        mock_monitor.get_system_stats.return_value = {
            "cpu_percent": 50,
            "memory_usage": 60,
            "disk_usage": 70,
            "uptime": 3600,
            "active_requests": 5,
            "active_sessions": 10,
        }

        status = await health_checker.get_health_status()

        assert status.status == "unhealthy"

    @patch("src.utils.health.HealthChecker.run_all_checks")
    @patch("src.utils.health.monitor")
    async def test_get_health_status_includes_system_stats(
        self, mock_monitor, mock_run_checks, health_checker
    ):
        """Test status includes system statistics."""
        from src.utils.health import ComponentHealth

        mock_run_checks.return_value = [
            ComponentHealth(name="db", status="healthy", last_check=datetime.utcnow()),
        ]

        mock_monitor.get_system_stats.return_value = {
            "cpu_percent": 85,
            "memory_usage": 60,
            "disk_usage": 95,
            "uptime": 3600,
            "active_requests": 5,
            "active_sessions": 10,
        }

        status = await health_checker.get_health_status()

        assert "system" in status.checks
        assert status.checks["system"]["cpu_percent"] == 85
        assert status.checks["system"]["disk_usage"] == 95

    @patch("src.utils.health.HealthChecker.run_all_checks")
    @patch("src.utils.health.monitor")
    async def test_get_health_status_system_degraded(
        self, mock_monitor, mock_run_checks, health_checker
    ):
        """Test system marked degraded when resources high."""
        from src.utils.health import ComponentHealth

        mock_run_checks.return_value = [
            ComponentHealth(name="db", status="healthy", last_check=datetime.utcnow()),
        ]

        mock_monitor.get_system_stats.return_value = {
            "cpu_percent": 95,  # Over 80%
            "memory_usage": 60,
            "disk_usage": 95,  # Over 90%
            "uptime": 3600,
            "active_requests": 5,
            "active_sessions": 10,
        }

        status = await health_checker.get_health_status()

        assert status.checks["system"]["status"] == "degraded"


class TestComponentHealthModel:
    """Test ComponentHealth data model."""

    def test_component_health_creation(self):
        """Test creating ComponentHealth instance."""
        from src.utils.health import ComponentHealth

        health = ComponentHealth(
            name="test_component",
            status="healthy",
            response_time=0.123,
            last_check=datetime.utcnow(),
            details={"key": "value"},
        )

        assert health.name == "test_component"
        assert health.status == "healthy"
        assert health.response_time == 0.123
        assert health.details["key"] == "value"

    def test_component_health_optional_fields(self):
        """Test ComponentHealth with optional fields."""
        from src.utils.health import ComponentHealth

        health = ComponentHealth(
            name="test",
            status="unhealthy",
            last_check=datetime.utcnow(),
            error="Test error",
        )

        assert health.error == "Test error"
        assert health.response_time is None
        assert health.details is None


class TestHealthStatusModel:
    """Test HealthStatus data model."""

    def test_health_status_creation(self):
        """Test creating HealthStatus instance."""
        from src.utils.health import HealthStatus

        status = HealthStatus(
            status="healthy",
            timestamp=datetime.utcnow(),
            uptime=3600.5,
            version="1.0.0",
            checks={"db": {"status": "healthy"}},
        )

        assert status.status == "healthy"
        assert status.uptime == 3600.5
        assert status.version == "1.0.0"
        assert "db" in status.checks


class TestGlobalHealthChecker:
    """Test global health_checker instance."""

    def test_global_health_checker_exists(self):
        """Test global health_checker instance exists."""
        from src.utils.health import health_checker

        assert health_checker is not None

    def test_global_health_checker_is_singleton(self):
        """Test global health_checker is singleton."""
        from src.utils.health import health_checker as checker1
        from src.utils.health import health_checker as checker2

        assert checker1 is checker2

    async def test_global_health_checker_usable(self):
        """Test global health_checker can be used."""
        from src.utils.health import health_checker

        # Should be able to access properties
        assert hasattr(health_checker, "start_time")
        assert hasattr(health_checker, "version")
