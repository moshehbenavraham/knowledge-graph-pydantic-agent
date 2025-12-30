"""
Advanced RAG tools using Agentic Graph RAG architecture.

This module provides intelligent document retrieval using:
- HybridSearch: Combines vector + graph search
- IntentAnalyzer: Routes queries to optimal search strategy
- ConnectionManager: Manages database connections

Architecture:
- Vector search via PostgreSQL + pgvector
- Graph search via Neo4j + Graphiti (when enabled)
- Intelligent fallback when graph is unavailable
"""

import asyncio
import warnings
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from supabase.client import Client

from src.agentic_rag.config import get_config
from src.agentic_rag.search.hybrid_search import HybridSearch, HybridSearchResult
from src.agentic_rag.search.intent_analyzer import IntentAnalyzer
from src.config import SearchStrategy

if TYPE_CHECKING:
    from src.agentic_rag.storage.connection_manager import ConnectionManager

# Filter Supabase deprecation warnings (from internal library code)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="supabase",
    message=".*timeout.*parameter is deprecated.*",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="supabase",
    message=".*verify.*parameter is deprecated.*",
)

logger = structlog.get_logger(__name__)

# Global instances (initialized once per application lifecycle)

_connection_manager: "ConnectionManager | None" = None
_hybrid_search: HybridSearch | None = None
_intent_analyzer: IntentAnalyzer | None = None
_current_loop: asyncio.AbstractEventLoop | None = None


async def get_hybrid_search() -> HybridSearch:
    """
    Get or create HybridSearch instance with proper initialization.

    Returns:
        Initialized HybridSearch instance
    """
    global _connection_manager, _hybrid_search, _current_loop

    # Check if we're in a different event loop (Streamlit can switch loops)
    current_loop = asyncio.get_running_loop()
    if _current_loop is not current_loop:
        # Different loop - reset everything
        _connection_manager = None
        _hybrid_search = None
        _current_loop = current_loop
        logger.info("Event loop changed - resetting connection manager")

    if _hybrid_search is None:
        if _connection_manager is None:
            # Use singleton get_connection_manager which properly initializes analytics
            from src.agentic_rag.storage.connection_manager import get_connection_manager

            _connection_manager = await get_connection_manager()
            logger.info("ConnectionManager initialized for RAG tools")

        _hybrid_search = HybridSearch(_connection_manager)
        logger.info("HybridSearch initialized")

    return _hybrid_search


def get_intent_analyzer() -> IntentAnalyzer:
    """Get or create IntentAnalyzer instance."""
    global _intent_analyzer

    if _intent_analyzer is None:
        _intent_analyzer = IntentAnalyzer()
        logger.info("IntentAnalyzer initialized")

    return _intent_analyzer


async def retrieve_relevant_documents_tool(
    supabase: Client | None,
    embedding_client: Any | None,
    user_query: str,
    strategy: SearchStrategy | None = None,
    limit: int = 10,
) -> str:
    """
    Retrieve relevant documents using intelligent hybrid search.

    This function uses the full Agentic RAG stack:
    1. Intent analysis determines optimal search strategy
    2. HybridSearch combines vector + graph (when available)
    3. Results ranked and formatted for LLM consumption

    Args:
        supabase: Legacy parameter (unused, for backward compatibility)
        embedding_client: Legacy parameter (unused, for backward compatibility)
        user_query: User's search query
        strategy: Force specific strategy (optional, auto-selected if None)
        limit: Maximum number of results

    Returns:
        Formatted string with relevant document chunks and metadata
    """
    logger.info(
        "retrieve_relevant_documents_tool called",
        query_length=len(user_query),
        limit=limit,
        strategy=strategy,
    )

    try:
        # Get HybridSearch instance
        hybrid_search = await get_hybrid_search()

        # Perform search (will auto-select strategy if not specified)
        result = await hybrid_search.search(query=user_query, limit=limit, strategy=strategy)

        # Format results for LLM consumption
        formatted = _format_search_results(result)
        logger.info(
            "Document retrieval completed",
            chunks_returned=len(result.chunks),
            strategy_used=result.search_strategy.value,
        )
        return formatted

    except Exception as e:
        logger.exception("Document retrieval failed", query=user_query, error=str(e))
        return f"Error retrieving documents: {e}"


async def smart_search_tool(
    user_query: str, analyze_intent: bool = True, limit: int = 10
) -> dict[str, Any]:
    """
    Intelligent search with intent analysis and rich results.

    Returns comprehensive search results including:
    - Matched chunks with similarity scores
    - Identified entities (if graph enabled)
    - Relationships found (if graph enabled)
    - Search strategy used
    - Query metadata

    Args:
        user_query: User's search query
        analyze_intent: Whether to analyze query intent (default True)
        limit: Maximum number of results

    Returns:
        Dictionary with search results and metadata
    """
    logger.info(
        "smart_search_tool called",
        query_length=len(user_query),
        analyze_intent=analyze_intent,
        limit=limit,
    )

    try:
        hybrid_search = await get_hybrid_search()

        # Determine strategy
        strategy = None
        intent = None

        if analyze_intent:
            analyzer = get_intent_analyzer()
            intent_result = analyzer.analyze(user_query)
            intent = intent_result.primary_intent
            logger.debug("Intent analyzed", intent=intent.value)
            # Let HybridSearch select strategy based on intent

        # Perform search
        result = await hybrid_search.search(query=user_query, limit=limit, strategy=strategy)

        # Return rich structured data
        result_dict: dict[str, Any] = {
            "query": user_query,
            "chunks": [
                {
                    "chunk_id": str(c.chunk_id),
                    "content": c.content,
                    "document_id": str(c.document_id),
                    "document_title": c.document_title,
                    "source": c.document_source,
                    "similarity": c.similarity,
                    "entities": c.entities,
                }
                for c in result.chunks[:limit]
            ],
            "entities": (
                [
                    {
                        "name": e.name if hasattr(e, "name") else str(e),
                        "type": e.type if hasattr(e, "type") else "unknown",
                    }
                    for e in result.entities[:10]
                ]
                if result.entities
                else []
            ),
            "facts": (
                [
                    {
                        "description": f.description if hasattr(f, "description") else str(f),
                    }
                    for f in result.facts[:10]
                ]
                if result.facts
                else []
            ),
            "intent": intent.value if intent else None,
            "strategy_used": result.search_strategy.value,
            "query_time_ms": result.query_time * 1000,
            "total_results": len(result.chunks),
        }

        # Include enhanced Phase 02 metadata when available
        search_type = result.metadata.get("search_type", "")
        if search_type == "multi_hop":
            result_dict["multi_hop_data"] = {
                "paths_found": result.metadata.get("paths_found", 0),
                "path_summaries": result.metadata.get("path_summaries", []),
            }
        elif search_type == "temporal_trend":
            result_dict["temporal_trend_data"] = {
                "data_points": result.metadata.get("data_points", 0),
                "direction": result.metadata.get("direction"),
                "percent_change": result.metadata.get("percent_change"),
                "summary": result.metadata.get("summary", ""),
            }
        elif search_type == "comparison":
            result_dict["comparison_data"] = {
                "entities_compared": result.metadata.get("entities_compared", 0),
                "entities_with_data": result.metadata.get("entities_with_data", 0),
                "metric": result.metadata.get("metric", ""),
                "ranking": result.metadata.get("ranking", []),
                "summary": result.metadata.get("summary", ""),
            }

        logger.info(
            "Smart search completed",
            chunks=len(result.chunks),
            entities=len(result.entities or []),
            facts=len(result.facts or []),
            strategy=result.search_strategy.value,
        )
        return result_dict

    except Exception as e:
        logger.exception("Smart search failed", query=user_query, error=str(e))
        return {
            "query": user_query,
            "error": str(e),
            "chunks": [],
            "entities": [],
            "facts": [],
        }


async def graph_query_tool(
    entity_name: str | None = None, query_type: str = "entity_facts", limit: int = 10
) -> dict[str, Any]:
    """
    Query the knowledge graph directly for entity/relationship exploration.

    Query types:
    - entity_facts: Get all facts about an entity
    - entity_relationships: Get relationships for an entity
    - temporal_facts: Get facts in chronological order

    Args:
        entity_name: Name of entity to query
        query_type: Type of graph query to perform
        limit: Maximum number of results

    Returns:
        Dictionary with graph query results
    """
    logger.info(
        "graph_query_tool called", entity_name=entity_name, query_type=query_type, limit=limit
    )

    try:
        config = get_config()

        # Check if graph is enabled
        if not config.performance.enable_graph:
            logger.warning("Graph query attempted but graph is disabled")
            return {
                "error": "Knowledge graph is not enabled. Set ENABLE_GRAPH=true in .env",
                "query_type": query_type,
                "entity": entity_name,
            }

        hybrid_search = await get_hybrid_search()

        # For now, use hybrid search with graph-only strategy
        # TODO: Implement dedicated GraphSearch methods for specific query types
        result = await hybrid_search.search(
            query=entity_name or "", limit=limit, strategy=SearchStrategy.GRAPH_ONLY
        )

        result_dict = {
            "query_type": query_type,
            "entity": entity_name,
            "facts": [
                {
                    "description": f.description if hasattr(f, "description") else str(f),
                    "created_at": str(f.created_at) if hasattr(f, "created_at") else None,
                }
                for f in result.facts
            ],
            "entities": [
                {
                    "name": e.name if hasattr(e, "name") else str(e),
                    "type": e.type if hasattr(e, "type") else "unknown",
                }
                for e in result.entities
            ],
            "relationships": (
                [
                    {
                        "source": r.source if hasattr(r, "source") else str(r),
                        "target": r.target if hasattr(r, "target") else str(r),
                        "type": r.type if hasattr(r, "type") else "unknown",
                    }
                    for r in result.relationships
                ]
                if result.relationships
                else []
            ),
        }

        logger.info(
            "Graph query completed",
            facts=len(result.facts),
            entities=len(result.entities),
            relationships=len(result.relationships or []),
        )
        return result_dict

    except Exception as e:
        logger.exception(
            "Graph query failed", entity_name=entity_name, query_type=query_type, error=str(e)
        )
        return {
            "query_type": query_type,
            "entity": entity_name,
            "error": str(e),
        }


async def graph_traverse_tool(
    start_entity: str,
    end_entity: str | None = None,
    max_hops: int = 2,
    min_strength: float = 0.3,
    entity_type_filter: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Traverse the knowledge graph to find multi-hop relationships between entities.

    Use for discovering indirect connections like:
    - "What products did companies acquired by Intel release?"
    - "Which executives are connected through shared board memberships?"
    - "How is entity A connected to entity B?"

    Args:
        start_entity: Starting entity name or search pattern
        end_entity: Optional ending entity (if searching for specific connection)
        max_hops: Maximum path length (1-3, default 2)
        min_strength: Minimum relationship strength threshold (0.0-1.0, default 0.3)
        entity_type_filter: Optional filter for entity types (e.g., "organization", "person")
        limit: Maximum number of paths to return (default 20)

    Returns:
        Dictionary with paths found, including:
        - paths: List of discovered paths with nodes and relationships
        - path_summaries: Human-readable path descriptions
        - total_paths: Number of paths found
        - query_info: Query parameters used
    """
    logger.info(
        "graph_traverse_tool called",
        start_entity=start_entity,
        end_entity=end_entity,
        max_hops=max_hops,
        min_strength=min_strength,
        entity_type_filter=entity_type_filter,
        limit=limit,
    )

    try:
        config = get_config()

        # Check if graph is enabled
        if not config.performance.enable_graph:
            logger.warning("Graph traverse attempted but graph is disabled")
            return {
                "error": "Knowledge graph is not enabled. Set ENABLE_GRAPH=true in .env",
                "start_entity": start_entity,
                "paths": [],
            }

        # Get connection manager
        global _connection_manager

        if _connection_manager is None:
            from src.agentic_rag.storage.connection_manager import get_connection_manager

            _connection_manager = await get_connection_manager()

        # Import multi-hop module
        from src.agentic_rag.graph.multi_hop import MultiHopQuery, execute_multi_hop

        # Build query
        query = MultiHopQuery(
            start_entity=start_entity,
            end_entity=end_entity,
            min_hops=1,
            max_hops=min(3, max(1, max_hops)),
            min_strength=min(1.0, max(0.0, min_strength)),
            entity_type_filter=entity_type_filter,
            limit=min(100, max(1, limit)),
        )

        # Execute multi-hop traversal
        path_results = await execute_multi_hop(_connection_manager, query)

        # Format results
        paths = []
        summaries = []

        for path in path_results:
            path_data = {
                "nodes": [
                    {
                        "name": node.name,
                        "type": node.type,
                    }
                    for node in path.nodes
                ],
                "relationships": [
                    {
                        "from": step.source_id,
                        "to": step.target_id,
                        "type": step.subtype,
                        "strength": step.strength,
                    }
                    for step in path.steps
                ],
                "cumulative_strength": path.cumulative_strength,
                "hop_count": path.hop_count,
            }
            paths.append(path_data)
            summaries.append(path.get_path_summary())

        result_dict = {
            "start_entity": start_entity,
            "end_entity": end_entity,
            "paths": paths,
            "path_summaries": summaries,
            "total_paths": len(path_results),
            "query_info": {
                "max_hops": query.max_hops,
                "min_strength": query.min_strength,
                "entity_type_filter": entity_type_filter,
            },
        }

        logger.info(
            "Graph traverse completed",
            start_entity=start_entity,
            paths_found=len(path_results),
        )
        return result_dict

    except Exception as e:
        logger.exception(
            "Graph traverse failed",
            start_entity=start_entity,
            end_entity=end_entity,
            error=str(e),
        )
        return {
            "start_entity": start_entity,
            "end_entity": end_entity,
            "error": str(e),
            "paths": [],
        }


async def temporal_trend_tool(
    entity: str,
    metric: str | None = None,
    start_year: int = 2020,
    end_year: int = 2025,
    target_quarter: str | None = None,
    comparison_type: str = "none",
    limit: int = 50,
) -> dict[str, Any]:
    """
    Query temporal trends and time-series data from the knowledge graph.

    Use for time-based questions like:
    - "How has Intel's revenue changed over time?"
    - "Compare Apple Q3 2023 vs Q3 2024"
    - "Show AMD revenue year-over-year"

    Args:
        entity: Entity name to query (e.g., "Intel", "Apple", "AMD")
        metric: Optional metric filter (e.g., "revenue", "profit", "margin")
        start_year: Start of time range (default 2020)
        end_year: End of time range (default 2025)
        target_quarter: Quarter for comparison (Q1-Q4), required for QoQ/YoY
        comparison_type: "none" for trend, "qoq" for quarter-over-quarter,
                        "yoy" for year-over-year
        limit: Maximum data points to return (default 50)

    Returns:
        Dictionary with trend or comparison data:
        - For trend: data_points, direction, percent_change, time_span
        - For comparison: baseline, current, delta, percent_change
    """
    logger.info(
        "temporal_trend_tool called",
        entity=entity,
        metric=metric,
        year_range=f"{start_year}-{end_year}",
        comparison_type=comparison_type,
        target_quarter=target_quarter,
    )

    try:
        config = get_config()

        # Check if graph is enabled
        if not config.performance.enable_graph:
            logger.warning("Temporal trend attempted but graph is disabled")
            return {
                "error": "Knowledge graph is not enabled. Set ENABLE_GRAPH=true in .env",
                "entity": entity,
            }

        # Get connection manager
        global _connection_manager

        if _connection_manager is None:
            from src.agentic_rag.storage.connection_manager import get_connection_manager

            _connection_manager = await get_connection_manager()

        # Import temporal query module
        from src.agentic_rag.graph.temporal_queries import (
            ComparisonType,
            TemporalQuery,
            compare_quarters,
            execute_temporal_query,
        )

        # Handle comparison types
        if comparison_type.lower() in ("qoq", "yoy"):
            if not target_quarter:
                return {
                    "error": "target_quarter is required for QoQ/YoY comparisons",
                    "entity": entity,
                    "comparison_type": comparison_type,
                }

            comp_type = (
                ComparisonType.QOQ if comparison_type.lower() == "qoq" else ComparisonType.YOY
            )

            comparison = await compare_quarters(
                connection_manager=_connection_manager,
                entity=entity,
                target_year=end_year,
                target_quarter=target_quarter,
                comparison_type=comp_type,
                metric=metric,
            )

            result_dict = {
                "type": "comparison",
                "comparison_type": comparison.comparison_type.value,
                "entity": comparison.entity,
                "metric": comparison.metric,
                "summary": comparison.get_summary(),
                "baseline": comparison.baseline.to_dict() if comparison.baseline else None,
                "current": comparison.current.to_dict() if comparison.current else None,
                "delta": comparison.delta,
                "percent_change": comparison.percent_change,
                "baseline_missing": comparison.baseline_missing,
                "current_missing": comparison.current_missing,
            }

            logger.info(
                "Temporal comparison completed",
                entity=entity,
                comparison_type=comparison_type,
                has_baseline=not comparison.baseline_missing,
                has_current=not comparison.current_missing,
            )
            return result_dict

        # Standard trend query
        query = TemporalQuery(
            entity=entity,
            metric=metric,
            start_year=start_year,
            end_year=end_year,
            limit=limit,
        )

        trend = await execute_temporal_query(_connection_manager, query)

        trend_result: dict[str, Any] = {
            "type": "trend",
            "entity": trend.entity,
            "metric": trend.metric,
            "summary": trend.get_summary(),
            "direction": trend.direction.value,
            "percent_change": trend.percent_change,
            "time_span": trend.time_span,
            "start_period": trend.start_period,
            "end_period": trend.end_period,
            "data_points": [dp.to_dict() for dp in trend.data_points],
            "data_point_count": len(trend.data_points),
            "missing_periods": trend.missing_periods,
        }

        logger.info(
            "Temporal trend completed",
            entity=entity,
            data_points=len(trend.data_points),
            direction=trend.direction.value,
        )
        return trend_result

    except Exception as e:
        logger.exception(
            "Temporal trend failed",
            entity=entity,
            metric=metric,
            error=str(e),
        )
        return {
            "entity": entity,
            "metric": metric,
            "error": str(e),
        }


async def compare_entities_tool(
    entity_names: list[str],
    metric: str,
    fiscal_quarter: str | None = None,
    fiscal_year: int | None = None,
    entity_type_filter: str | None = None,
    include_growth: bool = False,
    growth_type: str = "percentage",
    sort_order: str = "descending",
) -> dict[str, Any]:
    """
    Compare multiple entities on a specific metric from the knowledge graph.

    Use for comparative analysis questions like:
    - "Compare Microsoft vs Intel revenue"
    - "How do Apple and NVIDIA profit margins differ?"
    - "Rank Intel, AMD, and NVIDIA by Q3 2024 revenue"

    Supports 2-5 entities with type compatibility validation - entities must
    share the same parent type (e.g., all companies, all products).

    Args:
        entity_names: List of 2-5 entity names to compare
        metric: Metric to compare (e.g., "revenue", "profit", "margin")
        fiscal_quarter: Optional quarter filter (Q1-Q4)
        fiscal_year: Optional year filter (e.g., 2024)
        entity_type_filter: Optional entity type for disambiguation
                           (e.g., "organization", "company")
        include_growth: Whether to include growth rate calculations
        growth_type: Type of growth calculation: "percentage", "absolute",
                    "qoq" (quarter-over-quarter), "yoy" (year-over-year)
        sort_order: Sort results: "ascending" or "descending" (default)

    Returns:
        Dictionary with comparison results:
        - entities: List of entity metrics with values and metadata
        - ranking: Entities sorted by metric value
        - comparison_valid: Whether comparison was valid (same entity types)
        - error_message: Error details if comparison invalid
        - growth_metrics: Growth calculations if include_growth=True
        - query_time_ms: Query execution time
    """
    logger.info(
        "compare_entities_tool called",
        entity_names=entity_names,
        metric=metric,
        fiscal_quarter=fiscal_quarter,
        fiscal_year=fiscal_year,
        include_growth=include_growth,
    )

    try:
        config = get_config()

        # Check if graph is enabled
        if not config.performance.enable_graph:
            logger.warning("Entity comparison attempted but graph is disabled")
            return {
                "error": "Knowledge graph is not enabled. Set ENABLE_GRAPH=true in .env",
                "entity_names": entity_names,
                "comparison_valid": False,
            }

        # Validate entity count
        if len(entity_names) < 2:
            return {
                "error": "At least 2 entity names required for comparison",
                "entity_names": entity_names,
                "comparison_valid": False,
            }

        if len(entity_names) > 5:
            return {
                "error": "At most 5 entity names allowed for comparison",
                "entity_names": entity_names,
                "comparison_valid": False,
            }

        # Get connection manager
        global _connection_manager

        if _connection_manager is None:
            from src.agentic_rag.storage.connection_manager import get_connection_manager

            _connection_manager = await get_connection_manager()

        # Import entity comparison module
        from src.agentic_rag.graph.entity_comparison import (
            ComparisonQuery,
            GrowthType,
            SortOrder,
            execute_comparison,
        )

        # Map growth type string to enum
        growth_type_map = {
            "percentage": GrowthType.PERCENTAGE,
            "absolute": GrowthType.ABSOLUTE,
            "qoq": GrowthType.QOQ,
            "yoy": GrowthType.YOY,
        }
        growth_enum = growth_type_map.get(growth_type.lower(), GrowthType.PERCENTAGE)

        # Map sort order string to enum
        sort_enum = (
            SortOrder.ASCENDING if sort_order.lower() == "ascending" else SortOrder.DESCENDING
        )

        # Build query
        query = ComparisonQuery(
            entity_names=entity_names,
            metric=metric,
            entity_type_filter=entity_type_filter,
            fiscal_quarter=fiscal_quarter,
            fiscal_year=fiscal_year,
            include_growth=include_growth,
            growth_type=growth_enum,
            sort_order=sort_enum,
        )

        # Execute comparison
        result = await execute_comparison(_connection_manager, query)

        # Format result
        result_dict: dict[str, Any] = {
            "entity_names": entity_names,
            "metric": result.metric,
            "comparison_valid": result.comparison_valid,
            "error_message": result.error_message,
            "entities_compared": result.entities_compared,
            "entities_with_data": result.entities_with_data,
            "ranking": result.ranking,
            "query_time_ms": result.query_time_ms,
            "summary": result.get_summary(),
            "entities": [
                {
                    "entity_name": e.entity_name,
                    "entity_type": e.entity_type,
                    "value": e.value,
                    "unit": e.unit,
                    "metric_type": e.metric_type,
                    "fiscal_quarter": e.fiscal_quarter,
                    "fiscal_year": e.fiscal_year,
                    "fact_count": e.fact_count,
                    "source_documents": e.source_documents,
                }
                for e in result.entities
            ],
        }

        # Add growth metrics if requested
        if include_growth and result.growth_metrics:
            result_dict["growth_metrics"] = [
                {
                    "entity_name": g.entity_name,
                    "baseline_value": g.baseline_value,
                    "current_value": g.current_value,
                    "absolute_delta": g.absolute_delta,
                    "percent_change": g.percent_change,
                    "growth_type": g.growth_type.value,
                    "baseline_period": g.baseline_period,
                    "current_period": g.current_period,
                    "summary": g.get_summary(),
                }
                for g in result.growth_metrics
            ]

        logger.info(
            "Entity comparison completed",
            entities_compared=result.entities_compared,
            entities_with_data=result.entities_with_data,
            comparison_valid=result.comparison_valid,
            query_time_ms=result.query_time_ms,
        )
        return result_dict

    except Exception as e:
        logger.exception(
            "Entity comparison failed",
            entity_names=entity_names,
            metric=metric,
            error=str(e),
        )
        return {
            "entity_names": entity_names,
            "metric": metric,
            "error": str(e),
            "comparison_valid": False,
        }


async def list_documents_tool(supabase: Client) -> list[str]:
    """
    List all available documents in the knowledge base.

    Args:
        supabase: Supabase client instance

    Returns:
        List of document descriptions with metadata
    """
    logger.info("list_documents_tool called")

    try:
        # Query Supabase for unique documents
        result = supabase.from_("documents").select("id, title, source, created_at").execute()

        if not result.data:
            logger.info("No documents found in database")
            return []

        # Format the data
        documents = []
        for doc in result.data:
            doc_str = (
                f"ID: {doc.get('id', 'unknown')}, "
                f"Title: {doc.get('title', 'Untitled')}, "
                f"Source: {doc.get('source', 'N/A')}, "
                f"Created: {doc.get('created_at', 'N/A')}"
            )
            documents.append(doc_str)

        logger.info("Documents listed successfully", document_count=len(documents))
        return documents

    except Exception as e:
        logger.exception("Error listing documents", error=str(e))
        return []


async def get_document_content_tool(supabase: Client, document_id: str) -> str:
    """
    Retrieve the full content of a specific document.

    Args:
        supabase: Supabase client instance
        document_id: Document ID or UUID

    Returns:
        Complete document content
    """
    logger.info("get_document_content_tool called", document_id=document_id)

    try:
        # Try to parse as UUID
        try:
            doc_uuid = UUID(document_id)
            logger.debug("Document ID is valid UUID", document_id=document_id)
            result = (
                supabase.from_("documents")
                .select("id, title, content, source")
                .eq("id", str(doc_uuid))
                .execute()
            )
        except ValueError:
            # Not a UUID, try matching by title or source
            logger.debug(
                "Document ID is not UUID, searching by title/source", document_id=document_id
            )
            result = (
                supabase.from_("documents")
                .select("id, title, content, source")
                .or_(f"title.ilike.%{document_id}%,source.ilike.%{document_id}%")
                .limit(1)
                .execute()
            )

        if not result.data:
            logger.warning("Document not found", document_id=document_id)
            return f"No document found with ID: {document_id}"

        doc = result.data[0]

        # Format document
        formatted = f"""# {doc.get('title', 'Untitled')}

**Source:** {doc.get('source', 'N/A')}
**ID:** {doc.get('id', 'unknown')}

---

{doc.get('content', 'No content available')[:20000]}
"""

        logger.info(
            "Document retrieved successfully",
            document_id=document_id,
            content_length=len(doc.get("content", "")),
        )
        return formatted

    except Exception as e:
        logger.exception("Error retrieving document", document_id=document_id, error=str(e))
        return f"Error retrieving document: {e}"


def _format_search_results(result: HybridSearchResult) -> str:
    """
    Format HybridSearchResult for LLM consumption.

    Args:
        result: Hybrid search result object

    Returns:
        Formatted markdown string
    """
    if not result.chunks:
        return "No relevant documents found."

    formatted_parts = []

    # Add entity context if available
    if result.entities:
        entity_names = [e.name if hasattr(e, "name") else str(e) for e in result.entities[:5]]
        formatted_parts.append(f"**Related Entities:** {', '.join(entity_names)}\n")

    # Add document chunks
    for i, chunk in enumerate(result.chunks, 1):
        chunk_text = f"""### Chunk {i} - {chunk.document_title}
**Source:** {chunk.document_source}
**Relevance Score:** {chunk.similarity:.2f}
{f"**Entities:** {', '.join(chunk.entities)}" if chunk.entities else ""}

{chunk.content}
"""
        formatted_parts.append(chunk_text)

    # Add metadata footer
    footer = f"""
---
**Search Strategy:** {result.search_strategy.value}
**Query Time:** {result.query_time * 1000:.0f}ms
**Total Results:** {len(result.chunks)}
"""
    formatted_parts.append(footer)

    return "\n\n---\n\n".join(formatted_parts)


# Cleanup function for graceful shutdown
async def cleanup_rag_tools() -> None:
    """
    Cleanup RAG tool resources.

    Should be called on application shutdown.
    """
    global _connection_manager, _hybrid_search, _intent_analyzer

    if _connection_manager:
        await _connection_manager.close()
        logger.info("ConnectionManager closed")

    _connection_manager = None
    _hybrid_search = None
    _intent_analyzer = None


__all__ = [
    "cleanup_rag_tools",
    "compare_entities_tool",
    "get_document_content_tool",
    "get_hybrid_search",
    "graph_query_tool",
    "graph_traverse_tool",
    "list_documents_tool",
    "retrieve_relevant_documents_tool",
    "smart_search_tool",
    "temporal_trend_tool",
]
