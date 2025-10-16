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
import logging
from typing import Any
from uuid import UUID

from src.agentic_rag.config import get_config
from src.agentic_rag.search.hybrid_search import HybridSearch, HybridSearchResult
from src.agentic_rag.search.intent_analyzer import IntentAnalyzer
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.config import SearchStrategy
from supabase.client import Client

logger = logging.getLogger(__name__)

# Global instances (initialized once per application lifecycle)

_connection_manager: ConnectionManager | None = None
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
            _connection_manager = ConnectionManager()
            await _connection_manager.initialize()
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
    try:
        # Get HybridSearch instance
        hybrid_search = await get_hybrid_search()

        # Perform search (will auto-select strategy if not specified)
        result = await hybrid_search.search(query=user_query, limit=limit, strategy=strategy)

        # Format results for LLM consumption
        return _format_search_results(result)

    except Exception as e:
        logger.exception(f"Document retrieval failed: {e}")
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
    try:
        hybrid_search = await get_hybrid_search()

        # Determine strategy
        strategy = None
        intent = None

        if analyze_intent:
            analyzer = get_intent_analyzer()
            intent_result = analyzer.analyze(user_query)
            intent = intent_result.primary_intent
            # Let HybridSearch select strategy based on intent

        # Perform search
        result = await hybrid_search.search(query=user_query, limit=limit, strategy=strategy)

        # Return rich structured data
        return {
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

    except Exception as e:
        logger.exception(f"Smart search failed: {e}")
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
    try:
        config = get_config()

        # Check if graph is enabled
        if not config.performance.enable_graph:
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

        return {
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

    except Exception as e:
        logger.exception(f"Graph query failed: {e}")
        return {
            "query_type": query_type,
            "entity": entity_name,
            "error": str(e),
        }


async def list_documents_tool(supabase: Client) -> list[str]:
    """
    List all available documents in the knowledge base.

    Args:
        supabase: Supabase client instance

    Returns:
        List of document descriptions with metadata
    """
    try:
        # Query Supabase for unique documents
        result = supabase.from_("documents").select("id, title, source, created_at").execute()

        if not result.data:
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

        return documents

    except Exception as e:
        logger.exception(f"Error listing documents: {e}")
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
    try:
        # Try to parse as UUID
        try:
            doc_uuid = UUID(document_id)
            result = (
                supabase.from_("documents")
                .select("id, title, content, source")
                .eq("id", str(doc_uuid))
                .execute()
            )
        except ValueError:
            # Not a UUID, try matching by title or source
            result = (
                supabase.from_("documents")
                .select("id, title, content, source")
                .or_(f"title.ilike.%{document_id}%,source.ilike.%{document_id}%")
                .limit(1)
                .execute()
            )

        if not result.data:
            return f"No document found with ID: {document_id}"

        doc = result.data[0]

        # Format document
        formatted = f"""# {doc.get('title', 'Untitled')}

**Source:** {doc.get('source', 'N/A')}
**ID:** {doc.get('id', 'unknown')}

---

{doc.get('content', 'No content available')[:20000]}
"""

        return formatted

    except Exception as e:
        logger.exception(f"Error retrieving document: {e}")
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
async def cleanup_rag_tools():
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
    "get_document_content_tool",
    "get_hybrid_search",
    "graph_query_tool",
    "list_documents_tool",
    "retrieve_relevant_documents_tool",
    "smart_search_tool",
]
