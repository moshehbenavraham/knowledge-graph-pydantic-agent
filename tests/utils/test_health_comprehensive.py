"""
Comprehensive tests for health check utilities.

Tests:
- HealthStatus and ComponentHealth models
- HealthChecker initialization
- Database health checks
- LLM health checks
- Embedding health checks
- Memory health checks
- Web search health checks
- Running all checks concurrently
- Overall health status determination
"""

import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.utils.health import (
    ComponentHealth,
    HealthChecker,
    HealthStatus,
    health_checker,
)


class TestHealthModels:
    """Test health check models."""

    def test_component_health_creation(self):
        """Test creating ComponentHealth instance."""
        health = ComponentHealth(
            name="test_component",
            status="healthy",
            response_time=0.123,
            last_check=datetime.now(UTC),
            details={"key": "value"},
        )

        assert health.name == "test_component"
        assert health.status == "healthy"
        assert health.response_time == 0.123
        assert health.details == {"key": "value"}

    def test_component_health_with_error(self):
        """Test ComponentHealth with error."""
        health = ComponentHealth(
            name="test",
            status="unhealthy",
            response_time=0.5,
            last_check=datetime.now(UTC),
            error="Connection failed",
        )

        assert health.error == "Connection failed"
        assert health.status == "unhealthy"

    def test_health_status_creation(self):
        """Test creating HealthStatus instance."""
        status = HealthStatus(
            status="healthy",
            timestamp=datetime.now(UTC),
            uptime=3600.0,
            version="1.0.0",
            checks={"database": {"status": "healthy"}},
        )

        assert status.status == "healthy"
        assert status.uptime == 3600.0
        assert status.version == "1.0.0"
        assert "database" in status.checks


class TestHealthCheckerInitialization:
    """Test HealthChecker initialization."""

    def test_health_checker_init(self):
        """Test HealthChecker initialization."""
        with patch("src.utils.health.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                app_version="1.0.0",
                health_check_interval=30,
            )

            checker = HealthChecker()

            assert checker.version == "1.0.0"
            assert checker.check_interval == 30
            assert checker.last_full_check is None

    def test_health_checker_start_time(self):
        """Test HealthChecker records start time."""
        checker = HealthChecker()

        assert checker.start_time > 0
        assert checker.start_time <= time.time()


@pytest.mark.asyncio
class TestDatabaseHealthCheck:
    """Test database health checks."""

    async def test_check_database_health_healthy(self):
        """Test healthy database check."""
        with patch("src.utils.health.get_supabase_client") as mock_get_client:
            mock_client = Mock()
            mock_result = Mock()
            mock_result.data = [{"health_check": 1}]
            mock_client.rpc.return_value.execute.return_value = mock_result
            mock_get_client.return_value = mock_client

            checker = HealthChecker()
            health = await checker.check_database_health()

            assert health.name == "database"
            assert health.status == "healthy"
            assert health.response_time > 0
            assert health.error is None
            assert health.details["connection"] == "ok"

    async def test_check_database_health_degraded(self):
        """Test degraded database check (empty response)."""
        with patch("src.utils.health.get_supabase_client") as mock_get_client:
            mock_client = Mock()
            mock_result = Mock()
            mock_result.data = []  # Empty response
            mock_client.rpc.return_value.execute.return_value = mock_result
            mock_get_client.return_value = mock_client

            checker = HealthChecker()
            health = await checker.check_database_health()

            assert health.name == "database"
            assert health.status == "degraded"
            assert health.error == "Empty response from database"

    async def test_check_database_health_unhealthy(self):
        """Test unhealthy database check (exception)."""
        with patch("src.utils.health.get_supabase_client") as mock_get_client:
            mock_client = Mock()
            mock_client.rpc.side_effect = Exception("Connection failed")
            mock_get_client.return_value = mock_client

            checker = HealthChecker()
            health = await checker.check_database_health()

            assert health.name == "database"
            assert health.status == "unhealthy"
            assert "Connection failed" in health.error

    async def test_check_database_health_client_unavailable(self):
        """Test database check when client is unavailable."""
        with patch("src.utils.health.get_supabase_client", None):
            checker = HealthChecker()
            health = await checker.check_database_health()

            assert health.name == "database"
            assert health.status == "unhealthy"
            assert "not available" in health.error.lower()


@pytest.mark.asyncio
class TestLLMHealthCheck:
    """Test LLM health checks."""

    async def test_check_llm_health_healthy(self):
        """Test healthy LLM check."""
        with patch("src.utils.health.get_llm_client") as mock_get_client:
            with patch("src.utils.health.get_settings") as mock_settings:
                mock_settings.return_value = Mock(
                    llm_choice="gpt-4",
                    app_version="1.0.0",
                    health_check_interval=30,
                )

                mock_client = Mock()
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.model = "gpt-4"
                mock_response.usage = Mock(total_tokens=10)
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                checker = HealthChecker()
                health = await checker.check_llm_health()

                assert health.name == "llm"
                assert health.status == "healthy"
                assert health.response_time > 0
                assert health.details["model"] == "gpt-4"
                assert health.details["tokens_used"] == 10

    async def test_check_llm_health_degraded(self):
        """Test degraded LLM check (empty response)."""
        with patch("src.utils.health.get_llm_client") as mock_get_client:
            with patch("src.utils.health.get_settings") as mock_settings:
                mock_settings.return_value = Mock(
                    llm_choice="gpt-4",
                    app_version="1.0.0",
                    health_check_interval=30,
                )

                mock_client = Mock()
                mock_response = Mock()
                mock_response.choices = []  # Empty choices
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                checker = HealthChecker()
                health = await checker.check_llm_health()

                assert health.name == "llm"
                assert health.status == "degraded"
                assert health.error == "Empty response from LLM"

    async def test_check_llm_health_unhealthy(self):
        """Test unhealthy LLM check (exception)."""
        with patch("src.utils.health.get_llm_client") as mock_get_client:
            with patch("src.utils.health.get_settings") as mock_settings:
                mock_settings.return_value = Mock(
                    llm_choice="gpt-4",
                    app_version="1.0.0",
                    health_check_interval=30,
                )

                mock_client = Mock()
                mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
                mock_get_client.return_value = mock_client

                checker = HealthChecker()
                health = await checker.check_llm_health()

                assert health.name == "llm"
                assert health.status == "unhealthy"
                assert "API error" in health.error

    async def test_check_llm_health_client_unavailable(self):
        """Test LLM check when client is unavailable."""
        with patch("src.utils.health.get_llm_client", None):
            with patch("src.utils.health.get_settings") as mock_settings:
                mock_settings.return_value = Mock(
                    app_version="1.0.0",
                    health_check_interval=30,
                )

                checker = HealthChecker()
                health = await checker.check_llm_health()

                assert health.name == "llm"
                assert health.status == "unhealthy"
                assert "not available" in health.error.lower()


@pytest.mark.asyncio
class TestEmbeddingHealthCheck:
    """Test embedding health checks."""

    async def test_check_embedding_health_healthy(self):
        """Test healthy embedding check."""
        with patch("src.utils.health.get_embedding_client") as mock_get_client:
            with patch("src.utils.health.get_settings") as mock_settings:
                mock_settings.return_value = Mock(
                    embedding_model_choice="text-embedding-ada-002",
                    app_version="1.0.0",
                    health_check_interval=30,
                )

                mock_client = Mock()
                mock_response = Mock()
                mock_response.data = [Mock(embedding=[0.1] * 1536)]
                mock_response.model = "text-embedding-ada-002"
                mock_client.embeddings.create = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                checker = HealthChecker()
                health = await checker.check_embedding_health()

                assert health.name == "embedding"
                assert health.status == "healthy"
                assert health.details["model"] == "text-embedding-ada-002"
                assert health.details["embedding_dim"] == 1536

    async def test_check_embedding_health_degraded(self):
        """Test degraded embedding check (empty response)."""
        with patch("src.utils.health.get_embedding_client") as mock_get_client:
            with patch("src.utils.health.get_settings") as mock_settings:
                mock_settings.return_value = Mock(
                    embedding_model_choice="text-embedding-ada-002",
                    app_version="1.0.0",
                    health_check_interval=30,
                )

                mock_client = Mock()
                mock_response = Mock()
                mock_response.data = []  # Empty data
                mock_client.embeddings.create = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                checker = HealthChecker()
                health = await checker.check_embedding_health()

                assert health.name == "embedding"
                assert health.status == "degraded"
                assert "Empty response" in health.error

    async def test_check_embedding_health_unhealthy(self):
        """Test unhealthy embedding check (exception)."""
        with patch("src.utils.health.get_embedding_client") as mock_get_client:
            with patch("src.utils.health.get_settings") as mock_settings:
                mock_settings.return_value = Mock(
                    embedding_model_choice="text-embedding-ada-002",
                    app_version="1.0.0",
                    health_check_interval=30,
                )

                mock_client = Mock()
                mock_client.embeddings.create = AsyncMock(side_effect=Exception("API error"))
                mock_get_client.return_value = mock_client

                checker = HealthChecker()
                health = await checker.check_embedding_health()

                assert health.name == "embedding"
                assert health.status == "unhealthy"
                assert "API error" in health.error


@pytest.mark.asyncio
class TestMemoryHealthCheck:
    """Test memory health checks."""

    async def test_check_memory_health_healthy(self):
        """Test healthy memory check."""
        with patch("src.utils.health.get_mem0_client") as mock_get_client:
            mock_client = Mock()
            mock_client.add.return_value = {"id": "mem-123"}
            mock_client.delete = Mock()
            mock_get_client.return_value = mock_client

            checker = HealthChecker()
            health = await checker.check_memory_health()

            assert health.name == "memory"
            assert health.status == "healthy"
            assert health.details["test_memory_id"] == "mem-123"
            # Verify cleanup was called
            mock_client.delete.assert_called_once_with("mem-123")

    async def test_check_memory_health_degraded(self):
        """Test degraded memory check (no ID returned)."""
        with patch("src.utils.health.get_mem0_client") as mock_get_client:
            mock_client = Mock()
            mock_client.add.return_value = {}  # No ID
            mock_get_client.return_value = mock_client

            checker = HealthChecker()
            health = await checker.check_memory_health()

            assert health.name == "memory"
            assert health.status == "degraded"
            assert "Failed to create test memory" in health.error

    async def test_check_memory_health_unhealthy(self):
        """Test unhealthy memory check (exception)."""
        with patch("src.utils.health.get_mem0_client") as mock_get_client:
            mock_client = Mock()
            mock_client.add.side_effect = Exception("Memory service error")
            mock_get_client.return_value = mock_client

            checker = HealthChecker()
            health = await checker.check_memory_health()

            assert health.name == "memory"
            assert health.status == "unhealthy"
            assert "Memory service error" in health.error

    async def test_check_memory_health_cleanup_error_suppressed(self):
        """Test memory check suppresses cleanup errors."""
        with patch("src.utils.health.get_mem0_client") as mock_get_client:
            mock_client = Mock()
            mock_client.add.return_value = {"id": "mem-123"}
            mock_client.delete.side_effect = Exception("Delete failed")  # Cleanup error
            mock_get_client.return_value = mock_client

            checker = HealthChecker()
            health = await checker.check_memory_health()

            # Should still be healthy despite cleanup error
            assert health.name == "memory"
            assert health.status == "healthy"


@pytest.mark.asyncio
class TestWebSearchHealthCheck:
    """Test web search health checks."""

    async def test_check_web_search_health_brave_healthy(self):
        """Test healthy Brave web search check."""
        with patch("src.utils.health.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                brave_api_key="test-brave-key",
                searxng_base_url=None,
                app_version="1.0.0",
                health_check_interval=30,
            )

            with patch("src.utils.health.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock()
                mock_client_class.return_value = mock_client

                checker = HealthChecker()
                health = await checker.check_web_search_health()

                assert health.name == "web_search"
                assert health.status == "healthy"
                assert health.details["provider"] == "brave"

    async def test_check_web_search_health_searxng_healthy(self):
        """Test healthy SearXNG web search check."""
        with patch("src.utils.health.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                brave_api_key=None,
                searxng_base_url="http://searxng:8080",
                app_version="1.0.0",
                health_check_interval=30,
            )

            with patch("src.utils.health.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock()
                mock_client_class.return_value = mock_client

                checker = HealthChecker()
                health = await checker.check_web_search_health()

                assert health.name == "web_search"
                assert health.status == "healthy"
                assert health.details["provider"] == "searxng"

    async def test_check_web_search_health_degraded(self):
        """Test degraded web search check (non-200 status)."""
        with patch("src.utils.health.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                brave_api_key="test-key",
                searxng_base_url=None,
                app_version="1.0.0",
                health_check_interval=30,
            )

            with patch("src.utils.health.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 429  # Rate limited
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock()
                mock_client_class.return_value = mock_client

                checker = HealthChecker()
                health = await checker.check_web_search_health()

                assert health.name == "web_search"
                assert health.status == "degraded"
                assert "429" in health.error

    async def test_check_web_search_health_no_provider(self):
        """Test web search check with no provider configured."""
        with patch("src.utils.health.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                brave_api_key=None,
                searxng_base_url=None,
                app_version="1.0.0",
                health_check_interval=30,
            )

            checker = HealthChecker()
            health = await checker.check_web_search_health()

            assert health.name == "web_search"
            assert health.status == "unhealthy"
            assert "No web search provider configured" in health.error

    async def test_check_web_search_health_exception(self):
        """Test web search check exception handling."""
        with patch("src.utils.health.get_settings") as mock_settings:
            mock_settings.return_value = Mock(
                brave_api_key="test-key",
                searxng_base_url=None,
                app_version="1.0.0",
                health_check_interval=30,
            )

            with patch("src.utils.health.httpx.AsyncClient") as mock_client_class:
                mock_client_class.side_effect = Exception("Network error")

                checker = HealthChecker()
                health = await checker.check_web_search_health()

                assert health.name == "web_search"
                assert health.status == "unhealthy"
                assert "Network error" in health.error


@pytest.mark.asyncio
class TestRunAllChecks:
    """Test running all health checks."""

    async def test_run_all_checks_all_healthy(self):
        """Test running all checks when all are healthy."""
        checker = HealthChecker()

        with patch.object(checker, "check_database_health") as mock_db:
            with patch.object(checker, "check_llm_health") as mock_llm:
                with patch.object(checker, "check_embedding_health") as mock_emb:
                    with patch.object(checker, "check_memory_health") as mock_mem:
                        with patch.object(checker, "check_web_search_health") as mock_web:
                            # All return healthy
                            mock_db.return_value = ComponentHealth(
                                name="database",
                                status="healthy",
                                response_time=0.1,
                                last_check=datetime.now(UTC),
                            )
                            mock_llm.return_value = ComponentHealth(
                                name="llm",
                                status="healthy",
                                response_time=0.2,
                                last_check=datetime.now(UTC),
                            )
                            mock_emb.return_value = ComponentHealth(
                                name="embedding",
                                status="healthy",
                                response_time=0.15,
                                last_check=datetime.now(UTC),
                            )
                            mock_mem.return_value = ComponentHealth(
                                name="memory",
                                status="healthy",
                                response_time=0.3,
                                last_check=datetime.now(UTC),
                            )
                            mock_web.return_value = ComponentHealth(
                                name="web_search",
                                status="healthy",
                                response_time=0.5,
                                last_check=datetime.now(UTC),
                            )

                            results = await checker.run_all_checks()

                            assert len(results) == 5
                            assert all(check.status == "healthy" for check in results)
                            assert checker.last_full_check is not None

    async def test_run_all_checks_handles_exceptions(self):
        """Test running all checks handles exceptions."""
        checker = HealthChecker()

        with patch.object(checker, "check_database_health") as mock_db:
            with patch.object(checker, "check_llm_health") as mock_llm:
                with patch.object(checker, "check_embedding_health") as mock_emb:
                    with patch.object(checker, "check_memory_health") as mock_mem:
                        with patch.object(checker, "check_web_search_health") as mock_web:
                            # One check raises exception
                            mock_db.side_effect = Exception("Database error")
                            mock_llm.return_value = ComponentHealth(
                                name="llm",
                                status="healthy",
                                response_time=0.2,
                                last_check=datetime.now(UTC),
                            )
                            mock_emb.return_value = ComponentHealth(
                                name="embedding",
                                status="healthy",
                                response_time=0.15,
                                last_check=datetime.now(UTC),
                            )
                            mock_mem.return_value = ComponentHealth(
                                name="memory",
                                status="healthy",
                                response_time=0.3,
                                last_check=datetime.now(UTC),
                            )
                            mock_web.return_value = ComponentHealth(
                                name="web_search",
                                status="healthy",
                                response_time=0.5,
                                last_check=datetime.now(UTC),
                            )

                            results = await checker.run_all_checks()

                            # Should have 5 checks (exception converted to unhealthy)
                            assert len(results) == 5
                            # One should be marked as unhealthy
                            unhealthy = [c for c in results if c.status == "unhealthy"]
                            assert len(unhealthy) == 1


@pytest.mark.asyncio
class TestGetHealthStatus:
    """Test getting overall health status."""

    async def test_get_health_status_all_healthy(self):
        """Test overall status when all components are healthy."""
        checker = HealthChecker()

        with patch.object(checker, "run_all_checks") as mock_checks:
            with patch("src.utils.health.monitor") as mock_monitor:
                mock_checks.return_value = [
                    ComponentHealth(
                        name="database",
                        status="healthy",
                        response_time=0.1,
                        last_check=datetime.now(UTC),
                    ),
                    ComponentHealth(
                        name="llm",
                        status="healthy",
                        response_time=0.2,
                        last_check=datetime.now(UTC),
                    ),
                ]

                mock_monitor.get_system_stats.return_value = {
                    "uptime": 3600,
                    "active_requests": 5,
                    "active_sessions": 10,
                    "cpu_percent": 50,
                    "memory_usage": 60,
                    "disk_usage": 70,
                }

                status = await checker.get_health_status()

                assert status.status == "healthy"
                assert "database" in status.checks
                assert "llm" in status.checks
                assert "system" in status.checks
                assert status.checks["system"]["status"] == "healthy"

    async def test_get_health_status_degraded(self):
        """Test overall status when some components are degraded."""
        checker = HealthChecker()

        with patch.object(checker, "run_all_checks") as mock_checks:
            with patch("src.utils.health.monitor") as mock_monitor:
                mock_checks.return_value = [
                    ComponentHealth(
                        name="database",
                        status="healthy",
                        response_time=0.1,
                        last_check=datetime.now(UTC),
                    ),
                    ComponentHealth(
                        name="llm",
                        status="degraded",
                        response_time=5.0,
                        last_check=datetime.now(UTC),
                        error="Slow response",
                    ),
                ]

                mock_monitor.get_system_stats.return_value = {
                    "uptime": 3600,
                    "active_requests": 5,
                    "active_sessions": 10,
                    "cpu_percent": 50,
                    "memory_usage": 60,
                    "disk_usage": 70,
                }

                status = await checker.get_health_status()

                assert status.status == "degraded"

    async def test_get_health_status_unhealthy(self):
        """Test overall status when some components are unhealthy."""
        checker = HealthChecker()

        with patch.object(checker, "run_all_checks") as mock_checks:
            with patch("src.utils.health.monitor") as mock_monitor:
                mock_checks.return_value = [
                    ComponentHealth(
                        name="database",
                        status="unhealthy",
                        response_time=10.0,
                        last_check=datetime.now(UTC),
                        error="Connection failed",
                    ),
                    ComponentHealth(
                        name="llm",
                        status="healthy",
                        response_time=0.2,
                        last_check=datetime.now(UTC),
                    ),
                ]

                mock_monitor.get_system_stats.return_value = {
                    "uptime": 3600,
                    "active_requests": 5,
                    "active_sessions": 10,
                    "cpu_percent": 50,
                    "memory_usage": 60,
                    "disk_usage": 70,
                }

                status = await checker.get_health_status()

                assert status.status == "unhealthy"

    async def test_get_health_status_system_degraded(self):
        """Test system status is degraded with high CPU/disk usage."""
        checker = HealthChecker()

        with patch.object(checker, "run_all_checks") as mock_checks:
            with patch("src.utils.health.monitor") as mock_monitor:
                mock_checks.return_value = [
                    ComponentHealth(
                        name="database",
                        status="healthy",
                        response_time=0.1,
                        last_check=datetime.now(UTC),
                    ),
                ]

                mock_monitor.get_system_stats.return_value = {
                    "uptime": 3600,
                    "active_requests": 5,
                    "active_sessions": 10,
                    "cpu_percent": 85,  # High CPU
                    "memory_usage": 60,
                    "disk_usage": 95,  # High disk
                }

                status = await checker.get_health_status()

                assert status.checks["system"]["status"] == "degraded"


class TestGlobalHealthChecker:
    """Test global health_checker instance."""

    def test_health_checker_global_instance_exists(self):
        """Test global health_checker instance exists."""
        assert health_checker is not None
        assert isinstance(health_checker, HealthChecker)

    def test_health_checker_global_has_start_time(self):
        """Test global health_checker has start time."""
        assert health_checker.start_time > 0
