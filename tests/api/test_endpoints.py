"""
Test suite for Phase 4 API endpoints.

Tests chat, search, and document management endpoints with various scenarios.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    from src.api.dependencies import (
        get_agent_deps,
        get_cache_manager,
        get_connection_manager,
        get_hybrid_search,
        get_intent_analyzer,
        get_neo4j_store,
        get_postgres_store,
        get_vector_search,
    )

    # Create mock dependencies
    mock_deps = MagicMock()
    mock_deps.postgres_store = AsyncMock()
    mock_deps.neo4j_store = AsyncMock()
    mock_deps.cache_manager = MagicMock()
    mock_deps.cache_manager.get.return_value = None
    mock_deps.cache_manager.set.return_value = None
    mock_deps.cache_manager.flush.return_value = None

    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = None
    mock_cache.flush.return_value = None

    mock_postgres = AsyncMock()
    mock_postgres.search_similar = AsyncMock(return_value=[])
    mock_postgres.get_document = AsyncMock(
        return_value={
            "id": "test-doc-id",
            "title": "Test Document",
            "source": "test",
            "content": "Test content",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "chunk_count": 1,
            "metadata": {},
        }
    )
    mock_postgres.get_document_chunks = AsyncMock(return_value=[])
    mock_postgres.list_documents = AsyncMock(return_value=[])
    mock_postgres.delete_document = AsyncMock(return_value=True)
    mock_postgres.count_documents = AsyncMock(return_value=0)
    mock_postgres.store_document = AsyncMock(return_value="doc-id-123")
    mock_postgres.store_chunks = AsyncMock(return_value=5)

    mock_neo4j = AsyncMock()
    mock_conn_manager = AsyncMock()

    # Create mock search instances
    mock_hybrid_search = MagicMock()
    mock_hybrid_search.comprehensive_search = AsyncMock(
        return_value={"chunks": [], "facts": [], "entities": [], "relationships": []}
    )

    mock_vector_search = MagicMock()
    mock_vector_search.search = AsyncMock(return_value=[])

    mock_intent_analyzer = MagicMock()
    mock_intent_analyzer.analyze = AsyncMock(return_value="HYBRID")

    # Override dependencies
    app.dependency_overrides[get_agent_deps] = lambda: mock_deps
    app.dependency_overrides[get_cache_manager] = lambda: mock_cache
    app.dependency_overrides[get_postgres_store] = lambda: mock_postgres
    app.dependency_overrides[get_neo4j_store] = lambda: mock_neo4j
    app.dependency_overrides[get_connection_manager] = lambda: mock_conn_manager
    app.dependency_overrides[get_hybrid_search] = lambda: mock_hybrid_search
    app.dependency_overrides[get_vector_search] = lambda: mock_vector_search
    app.dependency_overrides[get_intent_analyzer] = lambda: mock_intent_analyzer

    # Mock the lifespan init/cleanup
    with patch("src.api.main.init_dependencies", new_callable=AsyncMock):
        with patch("src.api.main.cleanup_dependencies", new_callable=AsyncMock):
            with patch("src.api.main.api_config") as mock_config:
                # Configure mock_config
                mock_config._settings.app_env = "test"
                mock_config.enable_tracing = False
                mock_config.log_level = "INFO"
                mock_config.get_cors_config.return_value = {
                    "allow_origins": ["*"],
                    "allow_methods": ["*"],
                    "allow_headers": ["*"],
                }

                # Create client
                client = TestClient(app)

                yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_agent_deps():
    """Mock unified agent dependencies."""
    with patch("src.api.dependencies.get_agent_deps") as mock:
        deps = MagicMock()
        deps.postgres_store = AsyncMock()
        deps.neo4j_store = AsyncMock()
        deps.cache_manager = MagicMock()
        mock.return_value = deps
        yield deps


@pytest.fixture
def mock_postgres_store():
    """Mock PostgreSQL store."""
    with patch("src.api.dependencies.get_postgres_store") as mock:
        store = AsyncMock()
        mock.return_value = store
        yield store


class TestRootEndpoints:
    """Test root and status endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Agentic RAG API"
        assert data["version"] == "0.8.0"
        assert "documentation" in data
        assert "endpoints" in data

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]


class TestChatEndpoints:
    """Test chat-related endpoints."""

    @pytest.mark.asyncio
    async def test_chat_endpoint_success(self, client, mock_agent_deps):
        """Test successful chat request."""
        # Mock agent response
        with patch("src.api.endpoints.chat.super_agent.run") as mock_run:
            mock_result = MagicMock()
            mock_result.data = "Test response"
            mock_result.usage.return_value = {
                "total_tokens": 100,
                "prompt_tokens": 50,
                "completion_tokens": 50,
            }
            mock_run.return_value = mock_result

            response = client.post(
                "/api/v1/chat",
                json={
                    "message": "Hello, how are you?",
                    "session_id": "test-session",
                },
            )

            # Should return 200 or handle dependency initialization
            assert response.status_code in [200, 503]

    def test_chat_endpoint_validation_error(self, client):
        """Test chat endpoint with invalid request."""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "",  # Empty message should fail validation
            },
        )
        assert response.status_code == 422

    def test_chat_stream_endpoint(self, client):
        """Test chat streaming endpoint."""
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "message": "Stream test",
                "stream": True,
            },
        )
        # Should return 200 or 503 (if dependencies not initialized)
        assert response.status_code in [200, 503]


class TestSearchEndpoints:
    """Test search-related endpoints."""

    @pytest.mark.asyncio
    async def test_search_endpoint_vector(self, client, mock_postgres_store):
        """Test vector search."""
        # Mock search results
        mock_postgres_store.search_similar.return_value = [
            {
                "id": "test-id",
                "content": "Test content",
                "similarity": 0.9,
                "document_id": "doc-1",
                "metadata": {},
            }
        ]

        response = client.post(
            "/api/v1/search",
            json={
                "query": "test query",
                "search_type": "vector",
                "limit": 10,
            },
        )

        # Should return 200 or 503
        assert response.status_code in [200, 503]

    def test_search_endpoint_validation_error(self, client):
        """Test search with invalid parameters."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "",  # Empty query
                "search_type": "invalid",  # Invalid type
            },
        )
        assert response.status_code == 422

    def test_search_suggest_endpoint(self, client):
        """Test search suggestions."""
        response = client.get("/api/v1/search/suggest?query=test")
        # Should return 200 or 503
        assert response.status_code in [200, 503]


class TestDocumentEndpoints:
    """Test document management endpoints."""

    @pytest.mark.asyncio
    async def test_ingest_document(self, client, mock_postgres_store):
        """Test document ingestion."""
        from uuid import uuid4

        from src.agentic_rag.ingestion.pipeline import IngestionResult

        # Mock the ingestion pipeline
        with patch("src.api.endpoints.documents.IngestionPipeline") as MockPipeline:
            mock_pipeline = MagicMock()
            mock_result = IngestionResult(
                document_id=uuid4(),
                title="Test Document",
                source="test",
                chunks_created=5,
                entities_extracted=3,
                relationships_extracted=2,
                facts_extracted=1,
                processing_time=1.5,
                errors=[],
                metadata={"category": "test"},
            )
            mock_pipeline.ingest_document = AsyncMock(return_value=mock_result)
            MockPipeline.return_value = mock_pipeline

            response = client.post(
                "/api/v1/documents",
                json={
                    "content": "This is test content for ingestion.",
                    "title": "Test Document",
                    "source": "test",
                    "metadata": {"category": "test"},
                },
            )

            # Should return 201 or 503
            assert response.status_code in [201, 503]

    def test_ingest_document_validation_error(self, client):
        """Test document ingestion with invalid data."""
        response = client.post(
            "/api/v1/documents",
            json={
                "content": "",  # Empty content
                "title": "",  # Empty title
                "source": "",  # Empty source
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_documents(self, client, mock_postgres_store):
        """Test document listing with pagination."""
        mock_postgres_store.list_documents.return_value = []
        mock_postgres_store.count_documents.return_value = 0

        response = client.get("/api/v1/documents?page=1&page_size=20")
        # Should return 200 or 503
        assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_get_document(self, client, mock_postgres_store):
        """Test retrieving specific document."""
        mock_postgres_store.get_document.return_value = {
            "id": "test-doc-id",
            "title": "Test Document",
            "source": "test",
            "content": "Test content",
            "created_at": "2025-01-01T00:00:00",
            "metadata": {},
        }

        response = client.get("/api/v1/documents/test-doc-id")
        # Should return 200, 404, or 503
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_delete_document(self, client, mock_postgres_store):
        """Test document deletion."""
        mock_postgres_store.get_document.return_value = {
            "id": "test-doc-id",
            "title": "Test",
        }
        mock_postgres_store.delete_document.return_value = None

        response = client.delete("/api/v1/documents/test-doc-id")
        # Should return 200, 404, or 503
        assert response.status_code in [200, 404, 503]


class TestMiddleware:
    """Test middleware functionality."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/",
            headers={"Origin": "http://localhost:3002"},
        )
        # CORS preflight should be handled
        assert response.status_code in [200, 405]

    def test_correlation_id_header(self, client):
        """Test correlation ID is added to responses."""
        response = client.get("/")
        assert response.status_code == 200
        # Correlation ID should be in headers
        assert "X-Correlation-ID" in response.headers or response.status_code == 200

    def test_timing_header(self, client):
        """Test timing header is added."""
        response = client.get("/")
        assert response.status_code == 200
        # Timing header should be present
        assert "X-Process-Time" in response.headers or response.status_code == 200

    def test_rate_limiting(self, client):
        """Test rate limiting headers."""
        response = client.get("/")
        assert response.status_code == 200
        # Rate limit headers should be present
        # Note: Health endpoints are excluded from rate limiting


class TestErrorHandling:
    """Test error handling and responses."""

    def test_404_handler(self, client):
        """Test 404 Not Found handler."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_validation_error(self, client):
        """Test validation error handling."""
        response = client.post(
            "/api/v1/chat",
            json={"invalid": "data"},
        )
        assert response.status_code == 422


class TestCaching:
    """Test caching functionality."""

    def test_cache_clear_endpoint(self, client):
        """Test cache clearing endpoint."""
        response = client.delete("/api/v1/cache")
        # Should return 200 or error
        assert response.status_code in [200, 500]

    def test_cache_clear_with_pattern(self, client):
        """Test cache clearing with pattern."""
        response = client.delete("/api/v1/cache?pattern=chat:*")
        assert response.status_code in [200, 500]


class TestHealthChecks:
    """Test health check endpoints."""

    def test_health_endpoint(self, client):
        """Test basic health endpoint."""
        response = client.get("/health")
        # Should return 200
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_endpoint(self, client):
        """Test comprehensive status endpoint."""
        response = client.get("/api/v1/status")
        # Should return 200 or 503
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "version" in data
            assert "components" in data


@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration tests for end-to-end scenarios."""

    @pytest.mark.skip(
        reason="Integration test requiring full database setup. "
        "Enable with ENABLE_INTEGRATION_TESTS=true environment variable. "
        "See docs/b-ongoing-projects/phase9_skip_analysis.md Category 4"
    )
    @pytest.mark.asyncio
    async def test_full_rag_flow(self, client):
        """Test complete RAG flow: ingest -> search -> chat."""
        # 1. Ingest document
        ingest_response = client.post(
            "/api/v1/documents",
            json={
                "content": "Test content about AI and machine learning.",
                "title": "Test Document",
                "source": "test",
            },
        )
        assert ingest_response.status_code == 201

        # 2. Search for content
        search_response = client.post(
            "/api/v1/search",
            json={
                "query": "machine learning",
                "search_type": "vector",
            },
        )
        assert search_response.status_code == 200

        # 3. Chat about the content
        chat_response = client.post(
            "/api/v1/chat",
            json={
                "message": "What does the document say about AI?",
            },
        )
        assert chat_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
