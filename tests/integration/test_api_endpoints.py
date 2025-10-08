"""
Integration tests for API endpoints.
"""

import pytest
from httpx import AsyncClient

from src.api.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestDocumentEndpoints:
    """Integration tests for document management endpoints."""

    @pytest.mark.asyncio
    async def test_full_document_workflow(self, client):
        """Test complete document workflow: ingest -> list -> get -> update -> delete."""
        # 1. Ingest document
        ingest_response = await client.post(
            "/api/v1/documents",
            json={
                "content": "Python is a programming language known for simplicity.",
                "title": "Python Guide",
                "source": "guide.txt",
            },
        )
        assert ingest_response.status_code == 201
        data = ingest_response.json()
        doc_id = data["document_id"]
        assert data["chunks_created"] > 0

        # 2. List documents
        list_response = await client.get("/api/v1/documents?page=1&page_size=20")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert "documents" in list_data
        assert list_data["total"] > 0
        assert any(doc["id"] == doc_id for doc in list_data["documents"])

        # 3. Get specific document
        get_response = await client.get(f"/api/v1/documents/{doc_id}")
        assert get_response.status_code == 200
        doc_data = get_response.json()
        assert doc_data["metadata"]["title"] == "Python Guide"
        assert doc_data["content"] is not None

        # 4. Get document with chunks
        get_chunks_response = await client.get(
            f"/api/v1/documents/{doc_id}?include_chunks=true"
        )
        assert get_chunks_response.status_code == 200
        chunks_data = get_chunks_response.json()
        assert chunks_data["chunks"] is not None
        assert len(chunks_data["chunks"]) > 0

        # 5. Update document
        update_response = await client.patch(
            f"/api/v1/documents/{doc_id}",
            params={"title": "Updated Python Guide"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "updated"

        # 6. Get document stats
        stats_response = await client.get(f"/api/v1/documents/{doc_id}/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["chunk_count"] > 0

        # 7. Delete document
        delete_response = await client.delete(f"/api/v1/documents/{doc_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"

        # 8. Verify deleted (should return 404)
        verify_response = await client.get(f"/api/v1/documents/{doc_id}")
        assert verify_response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_documents_pagination(self, client):
        """Test document listing with pagination."""
        # Ingest multiple documents
        doc_ids = []
        for i in range(15):
            response = await client.post(
                "/api/v1/documents",
                json={
                    "content": f"Test content {i}",
                    "title": f"Test Doc {i}",
                    "source": f"test_{i}.txt",
                },
            )
            if response.status_code == 201:
                doc_ids.append(response.json()["document_id"])

        # Get page 1
        page1 = await client.get("/api/v1/documents?page=1&page_size=10")
        assert page1.status_code == 200
        page1_data = page1.json()
        assert len(page1_data["documents"]) <= 10
        assert page1_data["page"] == 1

        # Get page 2
        page2 = await client.get("/api/v1/documents?page=2&page_size=10")
        assert page2.status_code == 200
        page2_data = page2.json()
        assert page2_data["page"] == 2

        # Cleanup
        for doc_id in doc_ids:
            await client.delete(f"/api/v1/documents/{doc_id}")

    @pytest.mark.asyncio
    async def test_list_documents_filtering(self, client):
        """Test document listing with source filtering."""
        # Ingest documents with different sources
        pdf_doc_response = await client.post(
            "/api/v1/documents",
            json={
                "content": "PDF content",
                "title": "PDF Document",
                "source": "test.pdf",
            },
        )
        txt_doc_response = await client.post(
            "/api/v1/documents",
            json={
                "content": "Text content",
                "title": "Text Document",
                "source": "test.txt",
            },
        )

        pdf_doc_id = pdf_doc_response.json()["document_id"]
        txt_doc_id = txt_doc_response.json()["document_id"]

        # Filter by PDF
        filtered = await client.get("/api/v1/documents?source_filter=%.pdf")
        assert filtered.status_code == 200
        filtered_data = filtered.json()
        pdf_sources = [doc["source"] for doc in filtered_data["documents"]]
        assert any(".pdf" in source for source in pdf_sources)

        # Cleanup
        await client.delete(f"/api/v1/documents/{pdf_doc_id}")
        await client.delete(f"/api/v1/documents/{txt_doc_id}")

    @pytest.mark.asyncio
    async def test_update_document_metadata(self, client):
        """Test updating document title and metadata."""
        # Create document
        create_response = await client.post(
            "/api/v1/documents",
            json={
                "content": "Test content",
                "title": "Original Title",
                "source": "test.txt",
                "metadata": {"key1": "value1"},
            },
        )
        doc_id = create_response.json()["document_id"]

        # Update title
        update_response = await client.patch(
            f"/api/v1/documents/{doc_id}", params={"title": "New Title"}
        )
        assert update_response.status_code == 200

        # Verify update
        get_response = await client.get(f"/api/v1/documents/{doc_id}")
        assert get_response.json()["metadata"]["title"] == "New Title"

        # Cleanup
        await client.delete(f"/api/v1/documents/{doc_id}")

    @pytest.mark.asyncio
    async def test_document_not_found(self, client):
        """Test handling of nonexistent document."""
        from uuid import uuid4

        fake_id = str(uuid4())

        # Get nonexistent document
        get_response = await client.get(f"/api/v1/documents/{fake_id}")
        assert get_response.status_code == 404

        # Update nonexistent document
        update_response = await client.patch(
            f"/api/v1/documents/{fake_id}", params={"title": "New Title"}
        )
        assert update_response.status_code == 404

        # Delete nonexistent document
        delete_response = await client.delete(f"/api/v1/documents/{fake_id}")
        assert delete_response.status_code == 404


class TestSearchEndpoints:
    """Integration tests for search endpoints."""

    @pytest.mark.asyncio
    async def test_vector_search(self, client):
        """Test vector search endpoint."""
        # Ingest test document first
        ingest_response = await client.post(
            "/api/v1/documents",
            json={
                "content": "Machine learning is a subset of artificial intelligence.",
                "title": "ML Guide",
                "source": "ml.txt",
            },
        )
        doc_id = ingest_response.json()["document_id"]

        # Perform search
        search_response = await client.post(
            "/api/v1/search",
            json={
                "query": "machine learning",
                "search_type": "vector",
                "limit": 5,
            },
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert "results" in results
        assert len(results["results"]) > 0

        # Cleanup
        await client.delete(f"/api/v1/documents/{doc_id}")

    @pytest.mark.asyncio
    async def test_hybrid_search(self, client):
        """Test hybrid search combining vector and graph."""
        # Ingest document
        ingest_response = await client.post(
            "/api/v1/documents",
            json={
                "content": (
                    "OpenAI developed GPT-4. Microsoft invested in OpenAI. "
                    "GPT-4 is a large language model."
                ),
                "title": "AI Companies",
                "source": "ai.txt",
            },
        )
        doc_id = ingest_response.json()["document_id"]

        # Perform hybrid search
        search_response = await client.post(
            "/api/v1/search",
            json={
                "query": "OpenAI and Microsoft relationship",
                "search_type": "hybrid",
                "limit": 5,
            },
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert "results" in results

        # Cleanup
        await client.delete(f"/api/v1/documents/{doc_id}")


class TestChatEndpoints:
    """Integration tests for chat endpoints."""

    @pytest.mark.asyncio
    async def test_chat_with_context(self, client):
        """Test chat endpoint with document context."""
        # Ingest document
        ingest_response = await client.post(
            "/api/v1/documents",
            json={
                "content": "Python is a high-level programming language.",
                "title": "Python Intro",
                "source": "python.txt",
            },
        )
        doc_id = ingest_response.json()["document_id"]

        # Chat about content
        chat_response = await client.post(
            "/api/v1/chat",
            json={
                "message": "What programming language is mentioned?",
                "include_sources": True,
            },
        )
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        assert "response" in chat_data
        assert "Python" in chat_data["response"]

        # Cleanup
        await client.delete(f"/api/v1/documents/{doc_id}")

    @pytest.mark.asyncio
    async def test_chat_streaming(self, client):
        """Test streaming chat endpoint (SSE)."""
        # Note: Testing SSE requires special handling
        # This is a basic connection test
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": "Hello, tell me about AI"},
        )

        # Should initiate streaming connection
        assert response.status_code == 200
        # In a real test, we'd consume the stream
        # For now, just verify the connection opens


class TestHealthEndpoints:
    """Integration tests for health and status endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root API endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Agentic RAG API"
        assert "endpoints" in data

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_endpoint(self, client):
        """Test status endpoint with component health."""
        response = await client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert len(data["components"]) > 0

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = await client.get("/metrics")
        assert response.status_code == 200
        # Metrics should be in Prometheus format
        assert "text/plain" in response.headers.get("content-type", "")


class TestCacheEndpoints:
    """Integration tests for cache management."""

    @pytest.mark.asyncio
    async def test_clear_cache(self, client):
        """Test cache clearing endpoint."""
        response = await client.delete("/api/v1/cache")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
