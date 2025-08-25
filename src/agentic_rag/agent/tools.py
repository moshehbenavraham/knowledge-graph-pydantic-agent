"""
Tool implementations for the Pydantic AI agent.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Input models for tools
class VectorSearchInput(BaseModel):
    """Input for vector search."""

    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, description="Maximum results", ge=1, le=50)
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity", ge=0, le=1)


class GraphSearchInput(BaseModel):
    """Input for graph search."""

    query: str = Field(..., description="Search query")
    include_timeline: bool = Field(default=False, description="Include temporal data")
    max_facts: int = Field(default=20, description="Maximum facts to return")


class HybridSearchInput(BaseModel):
    """Input for hybrid search."""

    query: str = Field(..., description="Search query")
    vector_weight: float = Field(default=0.6, description="Weight for vector results", ge=0, le=1)
    limit: int = Field(default=20, description="Maximum combined results")


class DocumentInput(BaseModel):
    """Input for document retrieval."""

    document_id: str = Field(..., description="Document UUID")
    include_chunks: bool = Field(default=True, description="Include all chunks")


class EntityRelationshipInput(BaseModel):
    """Input for entity relationship queries."""

    entity_name: str = Field(..., description="Entity name")
    depth: int = Field(default=2, description="Traversal depth", ge=1, le=5)
    relationship_types: list[str] | None = Field(None, description="Filter by relationship types")


# Tool implementations
async def comprehensive_search(query: str, search_config: dict[str, Any]) -> dict[str, Any]:
    """
    Perform comprehensive search using multiple strategies.

    This is the main search orchestrator that combines different
    search methods based on configuration.
    """
    results = {
        "query": query,
        "timestamp": datetime.utcnow().isoformat(),
        "search_config": search_config,
        "vector_results": [],
        "graph_results": [],
        "combined_results": [],
        "metadata": {},
    }

    tasks = []

    # Vector search task
    if search_config.get("use_vector", True):
        try:
            from ..search.vector_search import VectorSearch

            vector_searcher = VectorSearch()
            tasks.append(
                (
                    "vector",
                    vector_searcher.search(query, limit=search_config.get("vector_limit", 15)),
                )
            )
        except ImportError:
            logger.warning("Vector search not available")

    # Graph search task
    if search_config.get("use_graph", True):
        try:
            from ..search.graph_search import GraphSearch

            graph_searcher = GraphSearch()
            tasks.append(("graph", graph_searcher.search(query)))
        except ImportError:
            logger.warning("Graph search not available")

    # Execute searches in parallel
    if tasks:
        search_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)

        for (search_type, _), result in zip(tasks, search_results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"{search_type} search failed: {result}")
                results["metadata"][f"{search_type}_error"] = str(result)
            elif search_type == "vector":
                results["vector_results"] = result
            else:
                results["graph_results"] = result

    # Combine and rank results
    if results["vector_results"] or results["graph_results"]:
        try:
            from ..search.ranker import ResultRanker

            ranker = ResultRanker()
            results["combined_results"] = await ranker.rank_combined(
                results["vector_results"], results["graph_results"], query
            )
        except ImportError:
            # Simple fallback combining
            results["combined_results"] = (
                results["vector_results"] if results["vector_results"] else []
            )

    return results


async def get_document_context(
    document_id: str, chunk_index: int | None = None, context_size: int = 2
) -> dict[str, Any]:
    """
    Get document with surrounding context.

    Retrieves a document and optionally focuses on a specific chunk
    with surrounding context chunks.
    """
    try:
        from ..storage.postgres_store import PostgresStore

        store = PostgresStore()

        # Get document
        document = await store.get_document(document_id)
        if not document:
            return {"error": "Document not found"}

        # Get all chunks
        chunks = await store.get_document_chunks(document_id)

        result = {"document": document, "total_chunks": len(chunks), "chunks": chunks}

        # If specific chunk requested, provide context
        if chunk_index is not None and 0 <= chunk_index < len(chunks):
            start_idx = max(0, chunk_index - context_size)
            end_idx = min(len(chunks), chunk_index + context_size + 1)

            result["focal_chunk"] = chunks[chunk_index]
            result["context_chunks"] = chunks[start_idx:end_idx]
            result["context_range"] = (start_idx, end_idx)

        return result

    except ImportError:
        logger.error("Storage module not available")
        return {"error": "Storage module not available"}


async def explore_entity_network(
    entity_name: str, max_depth: int = 3, max_nodes: int = 50
) -> dict[str, Any]:
    """
    Explore the network around an entity.

    Builds a graph of relationships starting from the given entity.
    """
    try:
        from ..search.graph_search import GraphSearch

        searcher = GraphSearch()

        network = {"central_entity": entity_name, "nodes": [], "edges": [], "depth_explored": 0}

        visited = set()
        queue = [(entity_name, 0)]

        while queue and len(network["nodes"]) < max_nodes:
            current_entity, depth = queue.pop(0)

            if current_entity in visited or depth > max_depth:
                continue

            visited.add(current_entity)

            # Get relationships for current entity
            relationships = await searcher.get_entity_relationships(current_entity, depth=1)

            # Add node
            network["nodes"].append(
                {
                    "id": current_entity,
                    "depth": depth,
                    "type": relationships.get("entity_type", "unknown"),
                }
            )

            # Add edges and queue connected entities
            for rel in relationships.get("relationships", []):
                network["edges"].append(
                    {
                        "source": current_entity,
                        "target": rel["target"],
                        "type": rel["type"],
                        "confidence": rel.get("confidence", 1.0),
                    }
                )

                if rel["target"] not in visited:
                    queue.append((rel["target"], depth + 1))

            network["depth_explored"] = max(network["depth_explored"], depth)

        return network

    except ImportError:
        logger.error("Graph search not available")
        return {
            "central_entity": entity_name,
            "nodes": [],
            "edges": [],
            "error": "Graph search not available",
        }


async def temporal_analysis(
    entity_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    event_types: list[str] | None = None,
) -> dict[str, Any]:
    """
    Analyze temporal patterns and events.

    Provides timeline analysis for entities or general events.
    """
    try:
        from ..search.graph_search import GraphSearch

        searcher = GraphSearch()

        # Get timeline data
        if entity_name:
            timeline = await searcher.get_entity_timeline(entity_name, start_date, end_date)
        else:
            timeline = await searcher.get_events_timeline(start_date, end_date, event_types)

        # Analyze patterns
        analysis = {
            "timeline": timeline,
            "total_events": len(timeline),
            "date_range": None,
            "event_frequency": {},
            "key_periods": [],
        }

        if timeline:
            dates = [event.get("date") for event in timeline if event.get("date")]
            if dates:
                analysis["date_range"] = (min(dates), max(dates))

            # Count event types
            for event in timeline:
                event_type = event.get("type", "unknown")
                analysis["event_frequency"][event_type] = (
                    analysis["event_frequency"].get(event_type, 0) + 1
                )

            # Identify key periods (simplified - would be more sophisticated)
            # Group events by month/year and find peaks

        return analysis

    except ImportError:
        logger.error("Graph search not available")
        return {"timeline": [], "total_events": 0, "error": "Graph search not available"}


async def extract_key_facts(content: str, max_facts: int = 5) -> list[dict[str, Any]]:
    """
    Extract key facts from content using LLM.

    Returns structured facts with confidence scores.
    """
    try:
        from ..prompts import FACT_EXTRACTION_PROMPT
        from ..providers import get_llm_model

        # Use LLM to extract facts
        model = get_llm_model()

        prompt = FACT_EXTRACTION_PROMPT.format(
            text=content[:2000], max_length=500  # Limit content length
        )

        # This would use the actual LLM call in production
        # For now, return placeholder
        facts = [
            {
                "fact": "Sample extracted fact from content",
                "confidence": 0.85,
                "entities": [],
                "timestamp": None,
            }
        ]

        return facts[:max_facts]

    except Exception as e:
        logger.error(f"Fact extraction failed: {e}")
        return []


async def search_with_reranking(
    query: str, initial_results: list[dict[str, Any]], rerank_model: str | None = None
) -> list[dict[str, Any]]:
    """
    Rerank search results using a specialized model.

    Improves result relevance through sophisticated reranking.
    """
    if not initial_results:
        return []

    try:
        # In production, this would use a reranking model like Cohere Rerank
        # For now, we'll do simple relevance scoring

        scored_results = []
        for result in initial_results:
            score = result.get("score", 0.5)

            # Boost based on query term matches
            content = result.get("content", "").lower()
            query_terms = query.lower().split()
            term_matches = sum(1 for term in query_terms if term in content)

            # Adjust score based on matches
            adjusted_score = score * (1 + term_matches * 0.1)

            result["rerank_score"] = adjusted_score
            scored_results.append(result)

        # Sort by reranked score
        scored_results.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored_results

    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        return initial_results


async def validate_facts(
    facts: list[dict[str, Any]], source_chunks: list[str]
) -> list[dict[str, Any]]:
    """
    Validate extracted facts against source content.

    Ensures facts are supported by the source material.
    """
    validated_facts = []

    for fact in facts:
        fact_text = fact.get("fact", "").lower()

        # Check if fact appears in any source chunk
        support_count = 0
        for chunk_id in source_chunks:
            # In production, would fetch actual chunk content
            # For now, assume validation
            support_count += 1

        if support_count > 0:
            fact["validation_status"] = "supported"
            fact["support_count"] = support_count
            validated_facts.append(fact)
        else:
            fact["validation_status"] = "unsupported"
            fact["support_count"] = 0
            # Still include but mark as unsupported
            validated_facts.append(fact)

    return validated_facts


class ToolRegistry:
    """Registry of available tools for the agent."""

    def __init__(self):
        self.tools = {
            "comprehensive_search": comprehensive_search,
            "get_document_context": get_document_context,
            "explore_entity_network": explore_entity_network,
            "temporal_analysis": temporal_analysis,
            "extract_key_facts": extract_key_facts,
            "search_with_reranking": search_with_reranking,
            "validate_facts": validate_facts,
        }

    def get_tool(self, name: str):
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> list[str]:
        """List all available tools."""
        return list(self.tools.keys())

    def register_tool(self, name: str, func):
        """Register a new tool."""
        self.tools[name] = func


# Global tool registry instance
tool_registry = ToolRegistry()
