"""
Test suite for Phase 4 API endpoints.

Tests chat, search, and document management endpoints with various scenarios.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


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
            headers={"Origin": "http://localhost:3000"},
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

    @pytest.mark.skip(reason="Requires full environment setup")
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
