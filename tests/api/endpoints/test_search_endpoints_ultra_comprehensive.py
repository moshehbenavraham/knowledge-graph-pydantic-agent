"""
ULTRA Comprehensive tests for search API endpoints.

Target coverage: 28% → 95%+

Tests all search endpoints, request/response models, caching,
error handling, metrics, and search strategy selection.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.agentic_rag.search.intent_analyzer import IntentAnalysisResult, SearchIntent
from src.api.endpoints.search import (
    _execute_adaptive_search,
    _execute_hybrid_search,
    _execute_vector_search,
    find_relationships,
    get_entity_info,
    search,
    search_suggest,
)
from src.api.models import SearchRequest, SearchResponse, SearchType


class TestSearchEndpoint:
    """Test main search endpoint."""

    @pytest.mark.asyncio
    async def test_search_vector_cache_hit(self):
        """Test vector search with cache hit."""
        request = SearchRequest(query="test query", search_type=SearchType.VECTOR, limit=10)

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "results": [],
            "total_results": 0,
            "search_time_ms": 100.0,
            "strategy_used": "vector",
        }

        result = await search(
            request=request,
            vector_search=MagicMock(),
            hybrid_search=MagicMock(),
            intent_analyzer=MagicMock(),
            cache=mock_cache,
        )

        assert isinstance(result, SearchResponse)
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_vector_cache_miss(self):
        """Test vector search with cache miss."""
        request = SearchRequest(query="test query", search_type=SearchType.VECTOR, limit=10)

        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        mock_vector_search = AsyncMock()

        with patch(
            "src.api.endpoints.search._execute_vector_search",
            return_value={"results": [], "strategy_used": "vector"},
        ):
            result = await search(
                request=request,
                vector_search=mock_vector_search,
                hybrid_search=MagicMock(),
                intent_analyzer=MagicMock(),
                cache=mock_cache,
            )

            assert isinstance(result, SearchResponse)
            assert result.strategy_used == "vector"

    @pytest.mark.asyncio
    async def test_search_hybrid(self):
        """Test hybrid search."""
        request = SearchRequest(query="test query", search_type=SearchType.HYBRID, limit=10)

        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        with patch(
            "src.api.endpoints.search._execute_hybrid_search",
            return_value={"results": [], "strategy_used": "hybrid"},
        ):
            result = await search(
                request=request,
                vector_search=MagicMock(),
                hybrid_search=MagicMock(),
                intent_analyzer=MagicMock(),
                cache=mock_cache,
            )

            assert result.strategy_used == "hybrid"

    @pytest.mark.asyncio
    async def test_search_adaptive_uses_intent(self):
        """Test adaptive search uses intent analysis."""
        request = SearchRequest(query="test query", search_type=SearchType.ADAPTIVE, limit=10)

        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        mock_intent_analyzer = MagicMock()
        mock_intent = IntentAnalysisResult(
            primary_intent=SearchIntent.VECTOR_HEAVY,
            confidence=0.9,
            entities_mentioned=[],
            temporal_markers=[],
            relationship_indicators=[],
        )
        mock_intent_analyzer.analyze.return_value = mock_intent

        with patch(
            "src.api.endpoints.search._execute_adaptive_search",
            return_value={"results": [], "strategy_used": "vector"},
        ):
            await search(
                request=request,
                vector_search=MagicMock(),
                hybrid_search=MagicMock(),
                intent_analyzer=mock_intent_analyzer,
                cache=mock_cache,
            )

            mock_intent_analyzer.analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_unsupported_type(self):
        """Test error with unsupported search type."""
        # Create request with invalid search type by mocking
        request = MagicMock()
        request.query = "test"
        request.limit = 10
        request.search_type = "invalid_type"

        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await search(
                request=request,
                vector_search=MagicMock(),
                hybrid_search=MagicMock(),
                intent_analyzer=MagicMock(),
                cache=mock_cache,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_search_caches_result(self):
        """Test that successful search caches result."""
        request = SearchRequest(query="test", search_type=SearchType.VECTOR, limit=10)

        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        with patch(
            "src.api.endpoints.search._execute_vector_search",
            return_value={"results": [], "strategy_used": "vector"},
        ):
            await search(
                request=request,
                vector_search=MagicMock(),
                hybrid_search=MagicMock(),
                intent_analyzer=MagicMock(),
                cache=mock_cache,
            )

            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        """Test error handling in search endpoint."""
        request = SearchRequest(query="test", search_type=SearchType.VECTOR, limit=10)

        mock_cache = MagicMock()
        mock_cache.get.side_effect = Exception("Cache error")

        with pytest.raises(HTTPException) as exc_info:
            await search(
                request=request,
                vector_search=MagicMock(),
                hybrid_search=MagicMock(),
                intent_analyzer=MagicMock(),
                cache=mock_cache,
            )

        assert exc_info.value.status_code == 500


class TestSearchSuggest:
    """Test search suggestion endpoint."""

    @pytest.mark.asyncio
    async def test_search_suggest_basic(self):
        """Test basic search suggestion."""
        result = await search_suggest(query="test", limit=5)

        assert "query" in result
        assert "suggestions" in result
        assert result["query"] == "test"

    @pytest.mark.asyncio
    async def test_search_suggest_empty_list(self):
        """Test that suggestions returns empty list (not implemented)."""
        result = await search_suggest(query="anything", limit=10)

        assert result["suggestions"] == []


class TestGetEntityInfo:
    """Test get entity info endpoint."""

    @pytest.mark.asyncio
    async def test_get_entity_info_no_graphiti(self):
        """Test error when graphiti not enabled."""
        with pytest.raises(HTTPException) as exc_info:
            await get_entity_info(entity_name="OpenAI", graphiti_client=None)

        assert exc_info.value.status_code == 501
        assert "not enabled" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_entity_info_with_graphiti(self):
        """Test getting entity info."""
        mock_client = MagicMock()

        result = await get_entity_info(entity_name="OpenAI", graphiti_client=mock_client)

        assert result["name"] == "OpenAI"
        assert "type" in result
        assert "properties" in result
        assert "relationships" in result


class TestFindRelationships:
    """Test find relationships endpoint."""

    @pytest.mark.asyncio
    async def test_find_relationships_no_graphiti(self):
        """Test error when graphiti not enabled."""
        with pytest.raises(HTTPException) as exc_info:
            await find_relationships(
                entity1="OpenAI", entity2="Microsoft", max_depth=3, graphiti_client=None
            )

        assert exc_info.value.status_code == 501

    @pytest.mark.asyncio
    async def test_find_relationships_with_graphiti(self):
        """Test finding relationships."""
        mock_client = MagicMock()

        result = await find_relationships(
            entity1="OpenAI", entity2="Microsoft", max_depth=3, graphiti_client=mock_client
        )

        assert result["entity1"] == "OpenAI"
        assert result["entity2"] == "Microsoft"
        assert "relationships" in result
        assert "shortest_path_length" in result


class TestExecuteVectorSearch:
    """Test vector search execution helper."""

    @pytest.mark.asyncio
    async def test_execute_vector_search(self):
        """Test executing vector search."""
        request = SearchRequest(
            query="test", search_type=SearchType.VECTOR, limit=10, threshold=0.7
        )

        mock_result = MagicMock()
        mock_result.chunk_id = "chunk-1"
        mock_result.content = "Test content"
        mock_result.similarity = 0.95
        mock_result.document_id = "doc-1"
        mock_result.metadata = {}

        mock_vector_search = AsyncMock()
        mock_vector_search.search.return_value = [mock_result]

        result = await _execute_vector_search(mock_vector_search, request)

        assert result["strategy_used"] == "vector"
        assert len(result["results"]) == 1
        assert result["results"][0].score == 0.95

    @pytest.mark.asyncio
    async def test_execute_vector_search_empty_results(self):
        """Test vector search with no results."""
        request = SearchRequest(query="test", search_type=SearchType.VECTOR, limit=10)

        mock_vector_search = AsyncMock()
        mock_vector_search.search.return_value = []

        result = await _execute_vector_search(mock_vector_search, request)

        assert result["results"] == []


class TestExecuteHybridSearch:
    """Test hybrid search execution helper."""

    @pytest.mark.asyncio
    async def test_execute_hybrid_search(self):
        """Test executing hybrid search."""
        request = SearchRequest(query="test", search_type=SearchType.HYBRID, limit=10)

        # Create mock chunk
        mock_chunk = MagicMock()
        mock_chunk.chunk_id = "chunk-1"
        mock_chunk.content = "Test content"
        mock_chunk.similarity = 0.95
        mock_chunk.document_id = "doc-1"
        mock_chunk.metadata = {}

        # Create mock hybrid result
        mock_result = MagicMock()
        mock_result.chunks = [mock_chunk]
        mock_result.entities = []
        mock_result.relationships = []

        mock_hybrid_search = AsyncMock()
        mock_hybrid_search.search.return_value = mock_result

        result = await _execute_hybrid_search(mock_hybrid_search, request)

        assert result["strategy_used"] == "hybrid"
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_execute_hybrid_search_with_entities(self):
        """Test hybrid search with entities."""
        request = SearchRequest(query="test", search_type=SearchType.HYBRID, limit=10)

        mock_chunk = MagicMock()
        mock_chunk.chunk_id = "chunk-1"
        mock_chunk.content = "Content"
        mock_chunk.similarity = 0.9
        mock_chunk.document_id = "doc-1"
        mock_chunk.metadata = {}

        mock_entity = MagicMock()
        mock_entity.id = "e1"
        mock_entity.name = "OpenAI"
        mock_entity.type = "company"
        mock_entity.properties = {}

        mock_result = MagicMock()
        mock_result.chunks = [mock_chunk]
        mock_result.entities = [mock_entity]
        mock_result.relationships = []

        mock_hybrid_search = AsyncMock()
        mock_hybrid_search.search.return_value = mock_result

        result = await _execute_hybrid_search(mock_hybrid_search, request)

        assert result["entities"] is not None
        assert len(result["entities"]) == 1

    @pytest.mark.asyncio
    async def test_execute_hybrid_search_with_relationships(self):
        """Test hybrid search with relationships."""
        request = SearchRequest(query="test", search_type=SearchType.HYBRID, limit=10)

        mock_chunk = MagicMock()
        mock_chunk.chunk_id = "chunk-1"
        mock_chunk.content = "Content"
        mock_chunk.similarity = 0.9
        mock_chunk.document_id = "doc-1"
        mock_chunk.metadata = {}

        mock_rel = MagicMock()
        mock_rel.source = "OpenAI"
        mock_rel.target = "Microsoft"
        mock_rel.type = "partners_with"
        mock_rel.properties = {}

        mock_result = MagicMock()
        mock_result.chunks = [mock_chunk]
        mock_result.entities = []
        mock_result.relationships = [mock_rel]

        mock_hybrid_search = AsyncMock()
        mock_hybrid_search.search.return_value = mock_result

        result = await _execute_hybrid_search(mock_hybrid_search, request)

        assert result["relationships"] is not None
        assert len(result["relationships"]) == 1


class TestExecuteAdaptiveSearch:
    """Test adaptive search execution helper."""

    @pytest.mark.asyncio
    async def test_execute_adaptive_vector_heavy(self):
        """Test adaptive search routing to vector."""
        request = SearchRequest(query="test", search_type=SearchType.ADAPTIVE, limit=10)

        mock_intent = IntentAnalysisResult(
            primary_intent=SearchIntent.VECTOR_HEAVY,
            confidence=0.9,
            entities_mentioned=[],
            temporal_markers=[],
            relationship_indicators=[],
        )

        with patch(
            "src.api.endpoints.search._execute_vector_search",
            return_value={"results": [], "strategy_used": "vector"},
        ) as mock_vector:
            result = await _execute_adaptive_search(
                vector_search=MagicMock(),
                hybrid_search=MagicMock(),
                request=request,
                intent=mock_intent,
            )

            mock_vector.assert_called_once()
            assert result["strategy_used"] == "vector"

    @pytest.mark.asyncio
    async def test_execute_adaptive_graph_heavy(self):
        """Test adaptive search routing to hybrid."""
        request = SearchRequest(query="test", search_type=SearchType.ADAPTIVE, limit=10)

        mock_intent = IntentAnalysisResult(
            primary_intent=SearchIntent.GRAPH_HEAVY,
            confidence=0.9,
            entities_mentioned=[],
            temporal_markers=[],
            relationship_indicators=[],
        )

        with patch(
            "src.api.endpoints.search._execute_hybrid_search",
            return_value={"results": [], "strategy_used": "hybrid"},
        ) as mock_hybrid:
            result = await _execute_adaptive_search(
                vector_search=MagicMock(),
                hybrid_search=MagicMock(),
                request=request,
                intent=mock_intent,
            )

            mock_hybrid.assert_called_once()
            assert result["strategy_used"] == "hybrid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
