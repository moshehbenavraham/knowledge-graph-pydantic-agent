"""
Search endpoints for document retrieval.

Provides vector, graph, hybrid, and intent-driven search capabilities.
"""

import time
from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from prometheus_client import Counter, Histogram

from src.agentic_rag.search.hybrid_search import HybridSearch
from src.agentic_rag.search.intent_analyzer import IntentAnalyzer, SearchIntent
from src.agentic_rag.search.vector_search import VectorSearch
from src.api.dependencies import (
    get_cache_manager,
    get_graphiti_client,
    get_hybrid_search,
    get_intent_analyzer,
    get_postgres_store,
    get_vector_search,
)
from src.api.models import (
    GraphEntity,
    GraphRelationship,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchType,
)
from src.utils.cache import CacheManager

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/search", tags=["search"])

# Metrics
search_requests_total = Counter(
    "search_requests_total",
    "Total search requests",
    ["search_type", "status"]
)
search_duration = Histogram(
    "search_duration_seconds",
    "Search duration",
    ["search_type"]
)


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    vector_search: VectorSearch = Depends(get_vector_search),
    hybrid_search: HybridSearch = Depends(get_hybrid_search),
    intent_analyzer: IntentAnalyzer = Depends(get_intent_analyzer),
    cache: CacheManager = Depends(get_cache_manager),
) -> SearchResponse:
    """
    Unified search endpoint with strategy selection.

    Supports vector, graph, hybrid, and adaptive search strategies.
    """
    start_time = time.perf_counter()

    # Check cache
    cache_key = f"search:{request.search_type}:{request.query}:{request.limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info("search_cache_hit", query=request.query)
        search_requests_total.labels(
            search_type=request.search_type,
            status="cache_hit"
        ).inc()
        return SearchResponse(**cached_result)

    try:
        logger.info(
            "search_started",
            query=request.query,
            search_type=request.search_type,
        )

        # Execute search based on type
        if request.search_type == SearchType.VECTOR:
            results = await _execute_vector_search(
                vector_search,
                request
            )
        elif request.search_type == SearchType.HYBRID:
            results = await _execute_hybrid_search(
                hybrid_search,
                request
            )
        elif request.search_type == SearchType.ADAPTIVE:
            # Use intent analysis to select strategy
            intent = intent_analyzer.analyze(request.query)
            results = await _execute_adaptive_search(
                vector_search,
                hybrid_search,
                request,
                intent
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported search type: {request.search_type}"
            )

        # Calculate metrics
        search_time_ms = (time.perf_counter() - start_time) * 1000

        response = SearchResponse(
            results=results["results"],
            total_results=len(results["results"]),
            search_time_ms=search_time_ms,
            strategy_used=results["strategy_used"],
            entities=results.get("entities"),
            relationships=results.get("relationships"),
        )

        # Cache result
        cache.set(cache_key, response.model_dump(), ttl=600)

        # Record metrics
        search_requests_total.labels(
            search_type=request.search_type,
            status="success"
        ).inc()
        search_duration.labels(search_type=request.search_type).observe(
            search_time_ms / 1000
        )

        logger.info(
            "search_completed",
            query=request.query,
            results=len(results["results"]),
            duration_ms=search_time_ms,
        )

        return response

    except Exception as e:
        logger.error("search_failed", query=request.query, error=str(e))
        search_requests_total.labels(
            search_type=request.search_type,
            status="error"
        ).inc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.get("/suggest")
async def search_suggest(
    query: str = Query(..., min_length=2, description="Search query prefix"),
    limit: int = Query(5, ge=1, le=20, description="Maximum suggestions"),
):
    """
    Search query suggestions/autocomplete.

    Returns query suggestions based on previous searches or common patterns.
    """
    try:
        # TODO: Implement query suggestion logic
        suggestions = []

        return {
            "query": query,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error("search_suggest_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate suggestions",
        )


@router.get("/entities/{entity_name}")
async def get_entity_info(
    entity_name: str,
    graphiti_client = Depends(get_graphiti_client),
):
    """
    Get information about specific entity from knowledge graph.

    Returns entity properties and relationships.
    """
    if not graphiti_client:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Knowledge graph not enabled",
        )

    try:
        # TODO: Implement entity lookup
        entity_info = {
            "name": entity_name,
            "type": "unknown",
            "properties": {},
            "relationships": [],
        }

        return entity_info

    except Exception as e:
        logger.error("entity_lookup_failed", entity=entity_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entity information",
        )


@router.get("/relationships")
async def find_relationships(
    entity1: str = Query(..., description="First entity name"),
    entity2: str = Query(..., description="Second entity name"),
    max_depth: int = Query(3, ge=1, le=5, description="Max relationship depth"),
    graphiti_client = Depends(get_graphiti_client),
):
    """
    Find relationships between two entities in knowledge graph.

    Returns path of relationships connecting the entities.
    """
    if not graphiti_client:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Knowledge graph not enabled",
        )

    try:
        # TODO: Implement relationship path finding
        relationships = []

        return {
            "entity1": entity1,
            "entity2": entity2,
            "relationships": relationships,
            "shortest_path_length": 0,
        }

    except Exception as e:
        logger.error("relationship_search_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find relationships",
        )


# ===== Helper functions =====


async def _execute_vector_search(
    vector_search: VectorSearch,
    request: SearchRequest,
) -> dict:
    """Execute vector similarity search."""
    results = await vector_search.search(
        query=request.query,
        limit=request.limit,
        similarity_threshold=request.threshold,
    )

    return {
        "results": [
            SearchResult(
                id=str(r.chunk_id),
                content=r.content,
                score=r.similarity,
                document_id=str(r.document_id),
                metadata=r.metadata,
            )
            for r in results
        ],
        "strategy_used": "vector",
    }


async def _execute_hybrid_search(
    hybrid_search: HybridSearch,
    request: SearchRequest,
) -> dict:
    """Execute hybrid vector + graph search."""
    results = await hybrid_search.search(
        query=request.query,
        limit=request.limit,
    )

    # Extract results from HybridSearchResult dataclass
    search_results = [
        SearchResult(
            id=str(chunk.chunk_id),
            content=chunk.content,
            score=chunk.similarity,
            document_id=str(chunk.document_id),
            metadata=chunk.metadata,
        )
        for chunk in results.chunks
    ]

    # Extract entities (if any graph entities exist)
    entities = []
    if results.entities:
        entities = [
            GraphEntity(
                id=str(e.id) if hasattr(e, "id") else str(e),
                name=e.name if hasattr(e, "name") else "",
                type=e.type if hasattr(e, "type") else "",
                properties=e.properties if hasattr(e, "properties") else {},
            )
            for e in results.entities
        ]

    # Extract relationships (if any)
    relationships = []
    if results.relationships:
        relationships = [
            GraphRelationship(
                source=r.source if hasattr(r, "source") else "",
                target=r.target if hasattr(r, "target") else "",
                type=r.type if hasattr(r, "type") else "",
                properties=r.properties if hasattr(r, "properties") else {},
            )
            for r in results.relationships
        ]

    return {
        "results": search_results,
        "strategy_used": "hybrid",
        "entities": entities if entities else None,
        "relationships": relationships if relationships else None,
    }


async def _execute_adaptive_search(
    vector_search: VectorSearch,
    hybrid_search: HybridSearch,
    request: SearchRequest,
    intent: SearchIntent,
) -> dict:
    """Execute adaptive search based on intent analysis."""
    if intent in [SearchIntent.VECTOR_HEAVY, SearchIntent.SEMANTIC]:
        return await _execute_vector_search(vector_search, request)
    else:
        return await _execute_hybrid_search(hybrid_search, request)
