"""
Comprehensive tests for current search API endpoints.

Tests POST /api/v1/search, /suggest, /entities, /relationships endpoints.
Target: 85%+ coverage of search.py.
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


# Mock dataclasses for search results
@dataclass
class MockChunk:
    chunk_id: str
    content: str
    similarity: float
    document_id: str
    metadata: dict


@dataclass
class MockHybridResult:
    chunks: list
    entities: list = None
    relationships: list = None


@dataclass
class MockEntity:
    id: str
    name: str
    type: str
    properties: dict


@dataclass
class MockRelationship:
    source: str
    target: str
    type: str
    properties: dict


@pytest.fixture
def mock_dependencies():
    """Mock all dependencies."""
    with (
        patch("src.api.endpoints.search.get_vector_search") as mock_vector,
        patch("src.api.endpoints.search.get_hybrid_search") as mock_hybrid,
        patch("src.api.endpoints.search.get_intent_analyzer") as mock_intent,
        patch("src.api.endpoints.search.get_cache_manager") as mock_cache,
        patch("src.api.endpoints.search.get_graphiti_client") as mock_graphiti,
    ):
        # Mock vector search
        vector_search = Mock()
        vector_search.search = AsyncMock()
        mock_vector.return_value = vector_search

        # Mock hybrid search
        hybrid_search = Mock()
        hybrid_search.search = AsyncMock()
        mock_hybrid.return_value = hybrid_search

        # Mock intent analyzer
        intent_analyzer = Mock()
        mock_intent.return_value = intent_analyzer

        # Mock cache
        cache = Mock()
        cache.get = Mock(return_value=None)
        cache.set = Mock()
        mock_cache.return_value = cache

        # Mock graphiti
        mock_graphiti.return_value = Mock()

        yield {
            "vector": vector_search,
            "hybrid": hybrid_search,
            "intent": intent_analyzer,
            "cache": cache,
            "graphiti": mock_graphiti.return_value,
        }


@pytest.fixture
def test_client():
    """Create test client."""
    from src.api.main import app

    return TestClient(app)


class TestSearchEndpoint:
    """Test POST /api/v1/search endpoint."""

    def test_vector_search_success(self, test_client, mock_dependencies):
        """Test successful vector search."""
        # Mock vector search results
        mock_results = [
            MockChunk(
                chunk_id="chunk_1",
                content="Test content 1",
                similarity=0.95,
                document_id="doc_1",
                metadata={"source": "test.pdf"},
            ),
            MockChunk(
                chunk_id="chunk_2",
                content="Test content 2",
                similarity=0.88,
                document_id="doc_2",
                metadata={"source": "test2.pdf"},
            ),
        ]
        mock_dependencies["vector"].search.return_value = mock_results

        response = test_client.post(
            "/api/v1/search",
            json={
                "query": "test query",
                "search_type": "vector",
                "limit": 10,
                "threshold": 0.7,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 2
        assert data["strategy_used"] == "vector"
        assert len(data["results"]) == 2

    def test_hybrid_search_success(self, test_client, mock_dependencies):
        """Test successful hybrid search."""
        # Mock hybrid search results
        mock_chunks = [
            MockChunk(
                chunk_id="chunk_1",
                content="Hybrid result",
                similarity=0.92,
                document_id="doc_1",
                metadata={},
            )
        ]
        mock_result = MockHybridResult(chunks=mock_chunks, entities=[], relationships=[])
        mock_dependencies["hybrid"].search.return_value = mock_result

        response = test_client.post(
            "/api/v1/search",
            json={"query": "test query", "search_type": "hybrid", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        assert data["strategy_used"] == "hybrid"

    def test_adaptive_search_vector_intent(self, test_client, mock_dependencies):
        """Test adaptive search with VECTOR_HEAVY intent."""
        from src.agentic_rag.search.intent_analyzer import SearchIntent

        # Mock intent analysis
        mock_dependencies["intent"].analyze.return_value = SearchIntent.VECTOR_HEAVY

        # Mock vector search
        mock_results = [
            MockChunk(
                chunk_id="chunk_1",
                content="Content",
                similarity=0.9,
                document_id="doc_1",
                metadata={},
            )
        ]
        mock_dependencies["vector"].search.return_value = mock_results

        response = test_client.post(
            "/api/v1/search",
            json={"query": "semantic query", "search_type": "adaptive", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy_used"] == "vector"

    def test_adaptive_search_semantic_intent(self, test_client, mock_dependencies):
        """Test adaptive search with SEMANTIC intent."""
        from src.agentic_rag.search.intent_analyzer import SearchIntent

        mock_dependencies["intent"].analyze.return_value = SearchIntent.SEMANTIC

        mock_results = [
            MockChunk(
                chunk_id="chunk_1",
                content="Content",
                similarity=0.9,
                document_id="doc_1",
                metadata={},
            )
        ]
        mock_dependencies["vector"].search.return_value = mock_results

        response = test_client.post(
            "/api/v1/search",
            json={"query": "semantic query", "search_type": "adaptive", "limit": 10},
        )

        assert response.status_code == 200

    def test_adaptive_search_hybrid_intent(self, test_client, mock_dependencies):
        """Test adaptive search with HYBRID intent."""
        from src.agentic_rag.search.intent_analyzer import SearchIntent

        mock_dependencies["intent"].analyze.return_value = SearchIntent.HYBRID

        mock_result = MockHybridResult(chunks=[], entities=[], relationships=[])
        mock_dependencies["hybrid"].search.return_value = mock_result

        response = test_client.post(
            "/api/v1/search",
            json={"query": "hybrid query", "search_type": "adaptive", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy_used"] == "hybrid"

    def test_search_with_cache_hit(self, test_client, mock_dependencies):
        """Test search with cache hit."""
        # Mock cache hit
        cached_response = {
            "results": [
                {
                    "id": "chunk_1",
                    "content": "Cached content",
                    "score": 0.95,
                    "document_id": "doc_1",
                    "metadata": {},
                }
            ],
            "total_results": 1,
            "search_time_ms": 50.0,
            "strategy_used": "vector",
            "entities": None,
            "relationships": None,
        }
        mock_dependencies["cache"].get.return_value = cached_response

        response = test_client.post(
            "/api/v1/search",
            json={"query": "cached query", "search_type": "vector", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        # Should not call vector search on cache hit
        mock_dependencies["vector"].search.assert_not_called()

    def test_search_with_cache_miss(self, test_client, mock_dependencies):
        """Test search with cache miss."""
        mock_dependencies["cache"].get.return_value = None

        mock_results = [
            MockChunk(
                chunk_id="chunk_1",
                content="Content",
                similarity=0.9,
                document_id="doc_1",
                metadata={},
            )
        ]
        mock_dependencies["vector"].search.return_value = mock_results

        response = test_client.post(
            "/api/v1/search",
            json={"query": "new query", "search_type": "vector", "limit": 10},
        )

        assert response.status_code == 200
        # Should call vector search on cache miss
        mock_dependencies["vector"].search.assert_called_once()
        # Should cache result
        mock_dependencies["cache"].set.assert_called_once()

    def test_search_invalid_type(self, test_client, mock_dependencies):
        """Test search with invalid search type."""
        response = test_client.post(
            "/api/v1/search",
            json={"query": "test", "search_type": "invalid_type", "limit": 10},
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_search_with_entities(self, test_client, mock_dependencies):
        """Test hybrid search returning entities."""
        mock_entities = [
            MockEntity(id="entity_1", name="OpenAI", type="Organization", properties={}),
            MockEntity(id="entity_2", name="GPT-4", type="Product", properties={}),
        ]
        mock_result = MockHybridResult(chunks=[], entities=mock_entities, relationships=[])
        mock_dependencies["hybrid"].search.return_value = mock_result

        response = test_client.post(
            "/api/v1/search",
            json={"query": "OpenAI GPT-4", "search_type": "hybrid", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entities"] is not None
        assert len(data["entities"]) == 2

    def test_search_with_relationships(self, test_client, mock_dependencies):
        """Test hybrid search returning relationships."""
        mock_relationships = [
            MockRelationship(source="OpenAI", target="GPT-4", type="CREATED", properties={})
        ]
        mock_result = MockHybridResult(chunks=[], entities=[], relationships=mock_relationships)
        mock_dependencies["hybrid"].search.return_value = mock_result

        response = test_client.post(
            "/api/v1/search",
            json={"query": "OpenAI created GPT-4", "search_type": "hybrid", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["relationships"] is not None
        assert len(data["relationships"]) == 1

    def test_search_error_handling(self, test_client, mock_dependencies):
        """Test search error handling."""
        mock_dependencies["vector"].search.side_effect = Exception("Search failed")

        response = test_client.post(
            "/api/v1/search",
            json={"query": "test", "search_type": "vector", "limit": 10},
        )

        assert response.status_code == 500
        data = response.json()
        assert "Search failed" in data["detail"]

    def test_search_empty_results(self, test_client, mock_dependencies):
        """Test search with no results."""
        mock_dependencies["vector"].search.return_value = []

        response = test_client.post(
            "/api/v1/search",
            json={"query": "nonexistent", "search_type": "vector", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 0
        assert len(data["results"]) == 0

    def test_hybrid_search_entities_without_id(self, test_client, mock_dependencies):
        """Test hybrid search with entities that don't have id attribute."""

        class SimpleEntity:
            def __init__(self, name):
                self.name = name
                self.type = "Test"
                self.properties = {}

        mock_entities = [SimpleEntity("Test1"), SimpleEntity("Test2")]
        mock_result = MockHybridResult(chunks=[], entities=mock_entities, relationships=[])
        mock_dependencies["hybrid"].search.return_value = mock_result

        response = test_client.post(
            "/api/v1/search",
            json={"query": "test", "search_type": "hybrid", "limit": 10},
        )

        assert response.status_code == 200

    def test_hybrid_search_relationships_without_attributes(self, test_client, mock_dependencies):
        """Test hybrid search with relationships missing attributes."""

        class SimpleRelationship:
            pass

        mock_relationships = [SimpleRelationship()]
        mock_result = MockHybridResult(chunks=[], entities=[], relationships=mock_relationships)
        mock_dependencies["hybrid"].search.return_value = mock_result

        response = test_client.post(
            "/api/v1/search",
            json={"query": "test", "search_type": "hybrid", "limit": 10},
        )

        assert response.status_code == 200

    def test_search_with_custom_threshold(self, test_client, mock_dependencies):
        """Test vector search with custom similarity threshold."""
        mock_results = [
            MockChunk(
                chunk_id="chunk_1",
                content="High similarity",
                similarity=0.95,
                document_id="doc_1",
                metadata={},
            )
        ]
        mock_dependencies["vector"].search.return_value = mock_results

        response = test_client.post(
            "/api/v1/search",
            json={"query": "test", "search_type": "vector", "limit": 10, "threshold": 0.9},
        )

        assert response.status_code == 200
        # Verify threshold was passed
        call_args = mock_dependencies["vector"].search.call_args
        assert call_args[1]["similarity_threshold"] == 0.9


class TestSearchSuggestEndpoint:
    """Test GET /api/v1/search/suggest endpoint."""

    def test_suggest_success(self, test_client, mock_dependencies):
        """Test successful search suggestions."""
        response = test_client.get("/api/v1/search/suggest?query=ope&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "suggestions" in data
        assert data["query"] == "ope"

    def test_suggest_with_min_length(self, test_client, mock_dependencies):
        """Test suggestions with minimum query length."""
        response = test_client.get("/api/v1/search/suggest?query=ab")

        assert response.status_code == 200

    def test_suggest_query_too_short(self, test_client, mock_dependencies):
        """Test suggestions with query too short."""
        response = test_client.get("/api/v1/search/suggest?query=a")

        # Should fail validation (min_length=2)
        assert response.status_code == 422

    def test_suggest_custom_limit(self, test_client, mock_dependencies):
        """Test suggestions with custom limit."""
        response = test_client.get("/api/v1/search/suggest?query=test&limit=20")

        assert response.status_code == 200

    def test_suggest_limit_too_low(self, test_client, mock_dependencies):
        """Test suggestions with limit too low."""
        response = test_client.get("/api/v1/search/suggest?query=test&limit=0")

        # Should fail validation (ge=1)
        assert response.status_code == 422

    def test_suggest_limit_too_high(self, test_client, mock_dependencies):
        """Test suggestions with limit too high."""
        response = test_client.get("/api/v1/search/suggest?query=test&limit=100")

        # Should fail validation (le=20)
        assert response.status_code == 422

    def test_suggest_missing_query(self, test_client, mock_dependencies):
        """Test suggestions without query parameter."""
        response = test_client.get("/api/v1/search/suggest")

        # Should fail validation (required)
        assert response.status_code == 422


class TestEntityInfoEndpoint:
    """Test GET /api/v1/search/entities/{entity_name} endpoint."""

    def test_get_entity_success(self, test_client, mock_dependencies):
        """Test successful entity lookup."""
        response = test_client.get("/api/v1/search/entities/OpenAI")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "OpenAI"
        assert "type" in data
        assert "properties" in data
        assert "relationships" in data

    def test_get_entity_with_spaces(self, test_client, mock_dependencies):
        """Test entity lookup with URL-encoded spaces."""
        response = test_client.get("/api/v1/search/entities/Open%20AI")

        assert response.status_code == 200

    def test_get_entity_no_graphiti(self, test_client):
        """Test entity lookup when graphiti is not enabled."""
        with patch("src.api.endpoints.search.get_graphiti_client") as mock_graphiti:
            mock_graphiti.return_value = None

            response = test_client.get("/api/v1/search/entities/Test")

            assert response.status_code == 501
            data = response.json()
            assert "not enabled" in data["detail"]

    def test_get_entity_special_characters(self, test_client, mock_dependencies):
        """Test entity lookup with special characters."""
        response = test_client.get("/api/v1/search/entities/Test%26Entity")

        assert response.status_code == 200


class TestRelationshipsEndpoint:
    """Test GET /api/v1/search/relationships endpoint."""

    def test_find_relationships_success(self, test_client, mock_dependencies):
        """Test successful relationship finding."""
        response = test_client.get("/api/v1/search/relationships?entity1=OpenAI&entity2=GPT-4")

        assert response.status_code == 200
        data = response.json()
        assert data["entity1"] == "OpenAI"
        assert data["entity2"] == "GPT-4"
        assert "relationships" in data
        assert "shortest_path_length" in data

    def test_find_relationships_custom_depth(self, test_client, mock_dependencies):
        """Test relationship finding with custom max depth."""
        response = test_client.get("/api/v1/search/relationships?entity1=A&entity2=B&max_depth=5")

        assert response.status_code == 200

    def test_find_relationships_min_depth(self, test_client, mock_dependencies):
        """Test relationship finding with minimum depth."""
        response = test_client.get("/api/v1/search/relationships?entity1=A&entity2=B&max_depth=1")

        assert response.status_code == 200

    def test_find_relationships_max_depth_limit(self, test_client, mock_dependencies):
        """Test relationship finding with max depth at limit."""
        response = test_client.get("/api/v1/search/relationships?entity1=A&entity2=B&max_depth=5")

        assert response.status_code == 200

    def test_find_relationships_depth_too_low(self, test_client, mock_dependencies):
        """Test relationship finding with depth too low."""
        response = test_client.get("/api/v1/search/relationships?entity1=A&entity2=B&max_depth=0")

        # Should fail validation (ge=1)
        assert response.status_code == 422

    def test_find_relationships_depth_too_high(self, test_client, mock_dependencies):
        """Test relationship finding with depth too high."""
        response = test_client.get("/api/v1/search/relationships?entity1=A&entity2=B&max_depth=10")

        # Should fail validation (le=5)
        assert response.status_code == 422

    def test_find_relationships_missing_entity1(self, test_client, mock_dependencies):
        """Test relationship finding without entity1."""
        response = test_client.get("/api/v1/search/relationships?entity2=B")

        # Should fail validation (required)
        assert response.status_code == 422

    def test_find_relationships_missing_entity2(self, test_client, mock_dependencies):
        """Test relationship finding without entity2."""
        response = test_client.get("/api/v1/search/relationships?entity1=A")

        # Should fail validation (required)
        assert response.status_code == 422

    def test_find_relationships_no_graphiti(self, test_client):
        """Test relationship finding when graphiti is not enabled."""
        with patch("src.api.endpoints.search.get_graphiti_client") as mock_graphiti:
            mock_graphiti.return_value = None

            response = test_client.get("/api/v1/search/relationships?entity1=A&entity2=B")

            assert response.status_code == 501
            data = response.json()
            assert "not enabled" in data["detail"]

    def test_find_relationships_default_depth(self, test_client, mock_dependencies):
        """Test relationship finding with default depth."""
        response = test_client.get("/api/v1/search/relationships?entity1=OpenAI&entity2=GPT-4")

        assert response.status_code == 200
