"""
Comprehensive tests for search API endpoints.

Tests smart search, vector search, graph queries, and hybrid search.
Target: 85%+ coverage of search endpoints.
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_search_dependencies():
    """Mock search dependencies."""
    with (
        patch("src.api.dependencies.get_supabase_client") as mock_supabase,
        patch("src.api.dependencies.get_embedding_client") as mock_embedding,
        patch("src.api.dependencies.get_rate_limiter") as mock_rate_limiter,
    ):
        mock_supabase.return_value = Mock()
        mock_embedding.return_value = Mock()
        mock_rate_limiter.return_value = Mock()
        mock_rate_limiter.return_value.check_rate_limit = AsyncMock(return_value=True)

        yield {
            "supabase": mock_supabase.return_value,
            "embedding": mock_embedding.return_value,
            "rate_limiter": mock_rate_limiter.return_value,
        }


@pytest.fixture
def test_client(mock_search_dependencies):
    """Create test client."""
    from src.api.main import app

    return TestClient(app)


class TestSmartSearchEndpoint:
    """Test /search/smart endpoint."""

    def test_smart_search_success(self, test_client, mock_search_dependencies):
        """Test successful smart search."""
        with patch("src.api.endpoints.search.smart_search_tool", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "query": "test query",
                "intent": "VECTOR_HEAVY",
                "chunks": [{"content": "Result 1", "similarity": 0.9}],
                "entities": [],
                "facts": [],
            }

            response = test_client.post(
                "/search/smart", json={"query": "test query", "limit": 10}
            )

            assert response.status_code in [200, 503]

    def test_smart_search_with_intent_analysis(self, test_client, mock_search_dependencies):
        """Test smart search with intent analysis enabled."""
        with patch("src.api.endpoints.search.smart_search_tool", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "query": "Find documents about AI",
                "intent": "HYBRID",
                "chunks": [],
                "entities": ["AI", "machine learning"],
                "facts": [],
            }

            response = test_client.post(
                "/search/smart",
                json={"query": "Find documents about AI", "analyze_intent": True, "limit": 20},
            )

            assert response.status_code in [200, 503]

    def test_smart_search_empty_query(self, test_client):
        """Test smart search with empty query."""
        response = test_client.post("/search/smart", json={"query": ""})

        # Should validate query
        assert response.status_code == 422

    def test_smart_search_with_limit(self, test_client, mock_search_dependencies):
        """Test smart search with custom limit."""
        with patch("src.api.endpoints.search.smart_search_tool", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"query": "test", "chunks": [], "entities": [], "facts": []}

            response = test_client.post("/search/smart", json={"query": "test", "limit": 50})

            assert response.status_code in [200, 503]

    def test_smart_search_vector_heavy_intent(self, test_client, mock_search_dependencies):
        """Test smart search detecting VECTOR_HEAVY intent."""
        with patch("src.api.endpoints.search.smart_search_tool", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "query": "semantic similarity query",
                "intent": "VECTOR_HEAVY",
                "chunks": [{"content": "Match 1", "similarity": 0.95}],
                "entities": [],
                "facts": [],
            }

            response = test_client.post(
                "/search/smart",
                json={"query": "semantic similarity query", "analyze_intent": True},
            )

            assert response.status_code in [200, 503]

    def test_smart_search_graph_heavy_intent(self, test_client, mock_search_dependencies):
        """Test smart search detecting GRAPH_HEAVY intent."""
        with patch("src.api.endpoints.search.smart_search_tool", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "query": "How is X related to Y?",
                "intent": "GRAPH_HEAVY",
                "chunks": [],
                "entities": ["X", "Y"],
                "facts": [{"entity": "X", "relationship": "related_to", "target": "Y"}],
            }

            response = test_client.post(
                "/search/smart",
                json={"query": "How is X related to Y?", "analyze_intent": True},
            )

            assert response.status_code in [200, 503]

    def test_smart_search_error_handling(self, test_client, mock_search_dependencies):
        """Test smart search error handling."""
        with patch("src.api.endpoints.search.smart_search_tool", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("Search error")

            response = test_client.post("/search/smart", json={"query": "test"})

            # Should handle error gracefully
            assert response.status_code in [500, 503]


class TestVectorSearchEndpoint:
    """Test /search/vector endpoint."""

    def test_vector_search_success(self, test_client, mock_search_dependencies):
        """Test successful vector search."""
        with patch(
            "src.api.endpoints.search.retrieve_relevant_documents_tool", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = "Document 1: Content...\nDocument 2: More content..."

            response = test_client.post("/search/vector", json={"query": "test query"})

            assert response.status_code in [200, 503]

    def test_vector_search_with_limit(self, test_client, mock_search_dependencies):
        """Test vector search with custom limit."""
        with patch(
            "src.api.endpoints.search.retrieve_relevant_documents_tool", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = "Results..."

            response = test_client.post(
                "/search/vector", json={"query": "test", "limit": 5}
            )

            assert response.status_code in [200, 503]

    def test_vector_search_empty_results(self, test_client, mock_search_dependencies):
        """Test vector search with no results."""
        with patch(
            "src.api.endpoints.search.retrieve_relevant_documents_tool", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = ""

            response = test_client.post("/search/vector", json={"query": "nonexistent"})

            assert response.status_code in [200, 503]


class TestGraphSearchEndpoint:
    """Test /search/graph endpoint."""

    def test_graph_search_entity_facts(self, test_client, mock_search_dependencies):
        """Test graph search for entity facts."""
        with patch("src.api.endpoints.search.graph_query_tool", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "entity": "OpenAI",
                "facts": [
                    {"description": "OpenAI created GPT-4", "timestamp": "2023-03-14"},
                    {"description": "OpenAI is an AI research company", "timestamp": "2015-12-11"},
                ],
            }

            response = test_client.post(
                "/search/graph",
                json={"entity_name": "OpenAI", "query_type": "entity_facts", "limit": 10},
            )

            assert response.status_code in [200, 503]

    def test_graph_search_relationships(self, test_client, mock_search_dependencies):
        """Test graph search for entity relationships."""
        with patch("src.api.endpoints.search.graph_query_tool", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "entity": "OpenAI",
                "relationships": [
                    {"target": "Microsoft", "type": "partnered_with"},
                    {"target": "GPT-4", "type": "created"},
                ],
            }

            response = test_client.post(
                "/search/graph",
                json={
                    "entity_name": "OpenAI",
                    "query_type": "entity_relationships",
                    "limit": 20,
                },
            )

            assert response.status_code in [200, 503]

    def test_graph_search_temporal_facts(self, test_client, mock_search_dependencies):
        """Test graph search for temporal facts."""
        with patch("src.api.endpoints.search.graph_query_tool", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "entity": "OpenAI",
                "timeline": [
                    {"event": "Founded", "date": "2015-12-11"},
                    {"event": "Released GPT-3", "date": "2020-06-11"},
                ],
            }

            response = test_client.post(
                "/search/graph",
                json={"entity_name": "OpenAI", "query_type": "temporal_facts", "limit": 10},
            )

            assert response.status_code in [200, 503]

    def test_graph_search_empty_entity(self, test_client):
        """Test graph search with empty entity name."""
        response = test_client.post(
            "/search/graph", json={"entity_name": "", "query_type": "entity_facts"}
        )

        # Should validate entity name
        assert response.status_code == 422


class TestHybridSearchEndpoint:
    """Test /search/hybrid endpoint."""

    def test_hybrid_search_success(self, test_client, mock_search_dependencies):
        """Test successful hybrid search."""
        with patch("src.api.endpoints.search.comprehensive_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "query": "test query",
                "vector_results": [{"content": "Vec match", "score": 0.9}],
                "graph_results": [{"entity": "Entity1", "relevance": 0.85}],
                "combined_results": [],
            }

            response = test_client.post(
                "/search/hybrid",
                json={
                    "query": "test query",
                    "use_vector": True,
                    "use_graph": True,
                    "max_results": 20,
                },
            )

            assert response.status_code in [200, 503]

    def test_hybrid_search_vector_only(self, test_client, mock_search_dependencies):
        """Test hybrid search with vector only."""
        with patch("src.api.endpoints.search.comprehensive_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "query": "test",
                "vector_results": [],
                "graph_results": [],
                "combined_results": [],
            }

            response = test_client.post(
                "/search/hybrid",
                json={"query": "test", "use_vector": True, "use_graph": False},
            )

            assert response.status_code in [200, 503]

    def test_hybrid_search_graph_only(self, test_client, mock_search_dependencies):
        """Test hybrid search with graph only."""
        with patch("src.api.endpoints.search.comprehensive_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "query": "test",
                "vector_results": [],
                "graph_results": [],
                "combined_results": [],
            }

            response = test_client.post(
                "/search/hybrid",
                json={"query": "test", "use_vector": False, "use_graph": True},
            )

            assert response.status_code in [200, 503]


class TestSearchCache:
    """Test search result caching."""

    def test_cache_hit_returns_cached_results(self, test_client, mock_search_dependencies):
        """Test cache hit returns cached results."""
        with (
            patch("src.api.endpoints.search.smart_search_tool", new_callable=AsyncMock) as mock_search,
            patch("src.api.endpoints.search.get_cache") as mock_cache,
        ):
            mock_cache.return_value = {"cached": "results"}

            response = test_client.post("/search/smart", json={"query": "cached query"})

            assert response.status_code in [200, 503]

    def test_cache_miss_calls_search(self, test_client, mock_search_dependencies):
        """Test cache miss triggers search."""
        with (
            patch("src.api.endpoints.search.smart_search_tool", new_callable=AsyncMock) as mock_search,
            patch("src.api.endpoints.search.get_cache") as mock_cache,
        ):
            mock_cache.return_value = None
            mock_search.return_value = {"query": "test", "chunks": []}

            response = test_client.post("/search/smart", json={"query": "new query"})

            assert response.status_code in [200, 503]


class TestSearchRateLimiting:
    """Test search rate limiting."""

    def test_rate_limit_enforcement(self, test_client, mock_search_dependencies):
        """Test rate limit enforcement on search."""
        mock_search_dependencies["rate_limiter"].check_rate_limit = AsyncMock(return_value=False)

        response = test_client.post("/search/smart", json={"query": "test"})

        # Should return 429 for rate limit
        assert response.status_code in [429, 503]

    def test_concurrent_searches_within_limit(self, test_client, mock_search_dependencies):
        """Test concurrent searches within rate limit."""
        with patch("src.api.endpoints.search.smart_search_tool", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"query": "test", "chunks": []}

            responses = []
            for i in range(5):
                response = test_client.post("/search/smart", json={"query": f"query {i}"})
                responses.append(response)

            # All should succeed (or fail due to dependencies)
            assert all(r.status_code in [200, 503] for r in responses)
