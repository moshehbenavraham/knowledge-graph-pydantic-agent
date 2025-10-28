"""
Additional coverage tests targeting specific modules and functions.

These tests focus on covering code paths that may have been missed.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestAPIModelsValidation:
    """Test API model validation and creation."""

    def test_chat_request_minimal(self):
        """Test ChatRequest with minimal data."""
        from src.api.models import ChatRequest

        request = ChatRequest(message="Test message")

        assert request.message == "Test message"
        assert request.stream is False
        assert request.include_sources is True

    def test_chat_request_full(self):
        """Test ChatRequest with all fields."""
        from src.api.models import ChatRequest

        request = ChatRequest(
            message="Test",
            session_id="test-session",
            stream=True,
            include_sources=False,
            max_tokens=1000,
            temperature=0.7,
            search_strategy="vector",
        )

        assert request.session_id == "test-session"
        assert request.max_tokens == 1000
        assert request.temperature == 0.7

    def test_chat_metrics_creation(self):
        """Test ChatMetrics creation."""
        from src.api.models import ChatMetrics

        metrics = ChatMetrics(
            response_time_ms=150.5,
            tokens_used=100,
            tokens_prompt=50,
            tokens_completion=50,
            cache_hit=False,
        )

        assert metrics.response_time_ms == 150.5
        assert metrics.tokens_used == 100

    def test_source_document_creation(self):
        """Test SourceDocument creation."""
        from src.api.models import SourceDocument

        doc = SourceDocument(
            document_id="test-id",
            content="Test content",
            similarity_score=0.95,
        )

        assert doc.document_id == "test-id"
        assert doc.similarity_score == 0.95

    def test_feedback_request_creation(self):
        """Test FeedbackRequest creation."""
        from src.api.models import FeedbackRequest

        feedback = FeedbackRequest(
            message_id="test-msg",
            rating=5,
            comment="Great!",
        )

        assert feedback.message_id == "test-msg"
        assert feedback.rating == 5

    def test_feedback_response_creation(self):
        """Test FeedbackResponse creation."""
        from src.api.models import FeedbackResponse

        response = FeedbackResponse(
            success=True,
            feedback_id="feedback-123",
        )

        assert response.success is True
        assert response.feedback_id == "feedback-123"

    def test_status_response_creation(self):
        """Test StatusResponse creation."""
        from src.api.models import StatusResponse

        response = StatusResponse(
            status="operational",
            version="1.0.0",
            components=[],
            metrics={},
        )

        assert response.status == "operational"
        assert response.version == "1.0.0"


class TestMiddlewareInitialization:
    """Test middleware can be initialized."""

    def test_security_headers_middleware_init(self):
        """Test SecurityHeadersMiddleware initialization."""
        from fastapi import FastAPI

        from src.api.middleware import SecurityHeadersMiddleware

        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app)

        assert middleware is not None

    def test_compression_middleware_init(self):
        """Test CompressionMiddleware initialization."""
        from fastapi import FastAPI

        from src.api.middleware import CompressionMiddleware

        app = FastAPI()
        middleware = CompressionMiddleware(app, minimum_size=1000)

        assert middleware is not None

    def test_rate_limit_middleware_init(self):
        """Test RateLimitMiddleware initialization."""
        from fastapi import FastAPI

        from src.api.middleware import RateLimitMiddleware

        app = FastAPI()
        middleware = RateLimitMiddleware(app, requests_per_minute=60)

        assert middleware is not None


class TestHealthModelsEdgeCases:
    """Test health models with edge cases."""

    def test_component_health_with_error(self):
        """Test ComponentHealth with error."""
        from src.utils.health import ComponentHealth

        health = ComponentHealth(
            name="database",
            status="unhealthy",
            last_check=datetime.utcnow(),
            error="Connection failed",
            response_time=5.0,
        )

        assert health.error == "Connection failed"
        assert health.status == "unhealthy"

    def test_component_health_with_details(self):
        """Test ComponentHealth with details."""
        from src.utils.health import ComponentHealth

        health = ComponentHealth(
            name="llm",
            status="healthy",
            last_check=datetime.utcnow(),
            response_time=0.5,
            details={"model": "gpt-4", "tokens": 100},
        )

        assert health.details["model"] == "gpt-4"
        assert health.details["tokens"] == 100

    def test_health_status_with_checks(self):
        """Test HealthStatus with multiple checks."""
        from src.utils.health import HealthStatus

        status = HealthStatus(
            status="degraded",
            timestamp=datetime.utcnow(),
            uptime=3600.0,
            version="1.0.0",
            checks={
                "database": {"status": "healthy"},
                "llm": {"status": "degraded"},
            },
        )

        assert status.status == "degraded"
        assert "database" in status.checks
        assert "llm" in status.checks


class TestRAGToolsBasicFunctions:
    """Test basic RAG tool functions."""

    def test_get_intent_analyzer_singleton(self):
        """Test IntentAnalyzer is singleton."""
        from src.tools.rag import get_intent_analyzer

        analyzer1 = get_intent_analyzer()
        analyzer2 = get_intent_analyzer()

        assert analyzer1 is analyzer2

    async def test_list_documents_empty_result(self):
        """Test list_documents with empty result."""
        from src.tools.rag import list_documents_tool

        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []

        mock_supabase.from_.return_value.select.return_value.execute.return_value = mock_result

        docs = await list_documents_tool(mock_supabase)

        assert len(docs) == 0

    async def test_get_document_content_not_found(self):
        """Test get_document_content with not found."""
        from src.tools.rag import get_document_content_tool

        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []

        mock_supabase.from_.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        content = await get_document_content_tool(mock_supabase, str(uuid4()))

        assert "No document found" in content


class TestWebSearchBasicFunctions:
    """Test basic web search functions."""

    async def test_web_search_no_provider(self):
        """Test web_search_tool with no provider."""
        from src.tools.web_search import web_search_tool

        mock_client = MagicMock()

        result = await web_search_tool(
            query="test",
            http_client=mock_client,
        )

        assert "No web search provider configured" in result

    async def test_web_search_invalid_provider(self):
        """Test web_search_tool with invalid provider."""
        from src.tools.web_search import web_search_tool

        mock_client = MagicMock()

        result = await web_search_tool(
            query="test",
            http_client=mock_client,
            search_provider="invalid",
        )

        assert "not available" in result


class TestAPIEndpointsBasicPaths:
    """Test basic API endpoint paths."""

    def test_chat_router_prefix(self):
        """Test chat router has correct prefix."""
        from src.api.endpoints.chat import router

        assert router.prefix == "/api/v1/chat"
        assert "chat" in router.tags

    def test_chat_metrics_counters_exist(self):
        """Test Prometheus metrics exist."""
        from src.api.endpoints.chat import chat_duration, chat_requests_total

        assert chat_requests_total is not None
        assert chat_duration is not None


class TestHealthCheckerMethods:
    """Test HealthChecker methods."""

    @patch("src.utils.health.get_settings")
    def test_health_checker_init_with_settings(self, mock_settings):
        """Test HealthChecker initializes with settings."""
        from src.utils.health import HealthChecker

        mock_settings.return_value = MagicMock(
            app_version="2.0.0",
            health_check_interval=120,
        )

        checker = HealthChecker()

        assert checker.version == "2.0.0"
        assert checker.check_interval == 120

    async def test_health_checker_run_all_checks_empty(self):
        """Test run_all_checks with mocked checks."""
        from src.utils.health import ComponentHealth, HealthChecker

        checker = HealthChecker()

        with patch.object(checker, "check_database_health", new_callable=AsyncMock) as mock_db:
            with patch.object(checker, "check_llm_health", new_callable=AsyncMock) as mock_llm:
                with patch.object(
                    checker, "check_embedding_health", new_callable=AsyncMock
                ) as mock_emb:
                    with patch.object(
                        checker, "check_memory_health", new_callable=AsyncMock
                    ) as mock_mem:
                        with patch.object(
                            checker, "check_web_search_health", new_callable=AsyncMock
                        ) as mock_web:
                            mock_db.return_value = ComponentHealth(
                                name="db", status="healthy", last_check=datetime.utcnow()
                            )
                            mock_llm.return_value = ComponentHealth(
                                name="llm", status="healthy", last_check=datetime.utcnow()
                            )
                            mock_emb.return_value = ComponentHealth(
                                name="emb", status="healthy", last_check=datetime.utcnow()
                            )
                            mock_mem.return_value = ComponentHealth(
                                name="mem", status="healthy", last_check=datetime.utcnow()
                            )
                            mock_web.return_value = ComponentHealth(
                                name="web", status="healthy", last_check=datetime.utcnow()
                            )

                            checks = await checker.run_all_checks()

                            assert len(checks) == 5
                            assert all(check.status == "healthy" for check in checks)


class TestStreamingManagersBasics:
    """Test streaming managers basic functionality."""

    def test_sse_manager_exists(self):
        """Test SSE manager can be imported."""
        from src.api.streaming import sse_manager

        assert sse_manager is not None

    def test_websocket_manager_exists(self):
        """Test WebSocket manager can be imported."""
        from src.api.streaming import websocket_manager

        assert websocket_manager is not None


class TestMiddlewareConfiguration:
    """Test middleware configuration."""

    def test_middleware_classes_importable(self):
        """Test all middleware classes can be imported."""
        from src.api.middleware import (
            CompressionMiddleware,
            CorrelationIDMiddleware,
            ErrorHandlingMiddleware,
            RateLimitMiddleware,
            RequestLoggingMiddleware,
            SecurityHeadersMiddleware,
            TimingMiddleware,
        )

        assert all(
            [
                SecurityHeadersMiddleware,
                CompressionMiddleware,
                RateLimitMiddleware,
                CorrelationIDMiddleware,
                TimingMiddleware,
                ErrorHandlingMiddleware,
                RequestLoggingMiddleware,
            ]
        )


class TestDependenciesFunctions:
    """Test API dependencies functions."""

    @patch("src.api.dependencies.get_settings")
    async def test_init_dependencies_callable(self, mock_settings):
        """Test init_dependencies can be called."""
        from src.api.dependencies import init_dependencies

        mock_settings.return_value = MagicMock()

        # Should be callable
        assert callable(init_dependencies)

    @patch("src.api.dependencies.get_settings")
    async def test_cleanup_dependencies_callable(self, mock_settings):
        """Test cleanup_dependencies can be called."""
        from src.api.dependencies import cleanup_dependencies

        mock_settings.return_value = MagicMock()

        # Should be callable
        assert callable(cleanup_dependencies)


class TestConfigImports:
    """Test config module imports."""

    def test_search_strategy_enum(self):
        """Test SearchStrategy enum."""
        from src.config import SearchStrategy

        assert hasattr(SearchStrategy, "VECTOR_ONLY")
        assert hasattr(SearchStrategy, "GRAPH_ONLY")
        assert hasattr(SearchStrategy, "HYBRID")

    def test_search_intent_enum(self):
        """Test SearchIntent enum."""
        from src.config import SearchIntent

        assert SearchIntent is not None

    def test_get_settings_singleton(self):
        """Test get_settings returns same instance."""
        from src.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2


class TestAgentImports:
    """Test agent module imports."""

    def test_unified_agent_import(self):
        """Test unified agent can be imported."""
        from src.agent.unified_agent import super_agent

        assert super_agent is not None

    def test_unified_agent_deps_import(self):
        """Test UnifiedAgentDeps can be imported."""
        from src.agent.unified_agent import UnifiedAgentDeps

        assert UnifiedAgentDeps is not None


class TestStorageImports:
    """Test storage module imports."""

    def test_connection_manager_import(self):
        """Test ConnectionManager can be imported."""
        from src.agentic_rag.storage.connection_manager import ConnectionManager

        assert ConnectionManager is not None

    def test_get_connection_manager_import(self):
        """Test get_connection_manager can be imported."""
        from src.agentic_rag.storage.connection_manager import get_connection_manager

        assert callable(get_connection_manager)


class TestSearchImports:
    """Test search module imports."""

    def test_hybrid_search_import(self):
        """Test HybridSearch can be imported."""
        from src.agentic_rag.search.hybrid_search import HybridSearch

        assert HybridSearch is not None

    def test_intent_analyzer_import(self):
        """Test IntentAnalyzer can be imported."""
        from src.agentic_rag.search.intent_analyzer import IntentAnalyzer

        assert IntentAnalyzer is not None

    def test_vector_search_import(self):
        """Test VectorSearch can be imported."""
        from src.agentic_rag.search.vector_search import VectorSearch

        assert VectorSearch is not None
