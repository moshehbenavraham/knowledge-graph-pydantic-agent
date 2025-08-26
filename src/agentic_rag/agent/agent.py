"""
Main Pydantic AI agent with intelligent search capabilities.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext

from .intent_analyzer import IntentAnalyzer, SearchStrategy
from .prompts import SYSTEM_PROMPT
from .providers import get_llm_model
from .response_generator import ResponseGenerator

# Import search modules for tools
try:
    from src.agentic_rag.search.graph_search import GraphSearch
    from src.agentic_rag.search.ranker import ResultRanker
    from src.agentic_rag.search.vector_search import VectorSearch
    from src.agentic_rag.storage.postgres_store import PostgresStore
except ImportError:
    # Graceful fallback when modules aren't available
    VectorSearch = None
    GraphSearch = None
    ResultRanker = None
    PostgresStore = None

logger = logging.getLogger(__name__)


@dataclass
class AgentDependencies:
    """Dependencies and context for the agent."""

    session_id: str
    user_id: str | None = None
    search_preferences: dict[str, Any] | None = None
    intent_analyzer: IntentAnalyzer | None = None
    response_generator: ResponseGenerator | None = None
    max_tools_per_query: int = 5
    enable_caching: bool = True

    def __post_init__(self):
        if self.search_preferences is None:
            self.search_preferences = {
                "use_vector": True,
                "use_graph": True,
                "default_limit": 10,
                "confidence_threshold": 0.7,
            }
        if self.intent_analyzer is None:
            self.intent_analyzer = IntentAnalyzer()
        if self.response_generator is None:
            self.response_generator = ResponseGenerator()


# Initialize the agent
rag_agent = Agent(model=get_llm_model(), deps_type=AgentDependencies, system_prompt=SYSTEM_PROMPT)


# Tool: Smart Search
@rag_agent.tool
async def smart_search(ctx: RunContext[AgentDependencies], query: str) -> dict[str, Any]:
    """
    Intelligent search that analyzes intent and routes to appropriate strategy.

    This is the primary tool that orchestrates all search operations.
    """
    # Analyze query intent
    analyzed_query = await ctx.deps.intent_analyzer.analyze(query)

    logger.info(
        f"Query intent: {analyzed_query.primary_intent}, "
        f"Strategy: {analyzed_query.search_strategy}"
    )

    # Route based on strategy
    if analyzed_query.search_strategy == SearchStrategy.VECTOR_ONLY:
        return await vector_search(ctx, query, limit=20)

    if analyzed_query.search_strategy == SearchStrategy.GRAPH_ONLY:
        return await graph_search(ctx, query)

    if analyzed_query.search_strategy == SearchStrategy.GRAPH_FIRST:
        # Graph search with vector enrichment
        graph_results = await graph_search(ctx, query)

        # Get supporting chunks for top facts
        if graph_results.get("facts"):
            chunk_ids = [f["source_chunk"] for f in graph_results["facts"][:5]]
            chunks = await get_chunks_by_ids(ctx, chunk_ids)
            graph_results["supporting_chunks"] = chunks

        return graph_results

    if analyzed_query.search_strategy == SearchStrategy.HYBRID:
        # Parallel execution
        vector_task = vector_search(ctx, query, limit=15)
        graph_task = graph_search(ctx, query)

        vector_results, graph_results = await asyncio.gather(vector_task, graph_task)

        # Merge and rank
        return await ctx.deps.response_generator.merge_results(
            vector_results, graph_results, analyzed_query
        )

    # ITERATIVE
    return await iterative_search(ctx, query, analyzed_query)


# Tool: Vector Search
@rag_agent.tool
async def vector_search(
    ctx: RunContext[AgentDependencies], query: str, limit: int = 10
) -> dict[str, Any]:
    """
    Semantic similarity search using embeddings.

    Best for:
    - Finding similar content
    - Conceptual matches
    - General information retrieval
    """
    try:
        if VectorSearch is None:
            return {
                "type": "vector",
                "query": query,
                "results": [],
                "error": "VectorSearch not available",
            }

        searcher = VectorSearch()
        results = await searcher.search(query, limit)

        return {
            "type": "vector",
            "query": query,
            "results": [
                {
                    "content": r.content,
                    "score": r.score,
                    "document_title": r.document_title,
                    "chunk_id": r.chunk_id,
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "total_results": len(results),
        }
    except ImportError:
        # Fallback for when search module isn't implemented yet
        logger.warning("Vector search module not available, returning mock results")
        return {
            "type": "vector",
            "query": query,
            "results": [],
            "total_results": 0,
            "error": "Vector search not yet implemented",
        }


# Tool: Graph Search
@rag_agent.tool
async def graph_search(ctx: RunContext[AgentDependencies], query: str) -> dict[str, Any]:
    """
    Knowledge graph search for facts and relationships.

    Best for:
    - Entity relationships
    - Temporal information
    - Specific facts
    """
    try:
        if GraphSearch is None:
            return {
                "type": "graph",
                "query": query,
                "results": [],
                "error": "GraphSearch not available",
            }

        searcher = GraphSearch()
        results = await searcher.search(query)

        return {
            "type": "graph",
            "query": query,
            "facts": results.facts,
            "entities": results.entities,
            "relationships": results.relationships,
            "timeline": results.timeline if hasattr(results, "timeline") else None,
            "total_facts": len(results.facts),
        }
    except ImportError:
        logger.warning("Graph search module not available, returning mock results")
        return {
            "type": "graph",
            "query": query,
            "facts": [],
            "entities": [],
            "relationships": [],
            "timeline": None,
            "total_facts": 0,
            "error": "Graph search not yet implemented",
        }


# Tool: Get Entity Relationships
@rag_agent.tool
async def get_entity_relationships(
    ctx: RunContext[AgentDependencies], entity_name: str, depth: int = 2
) -> dict[str, Any]:
    """
    Explore relationships for a specific entity.

    Returns the entity's connections up to specified depth.
    """
    try:
        if GraphSearch is None:
            return {
                "type": "graph",
                "entity": entity_name,
                "results": [],
                "error": "GraphSearch not available",
            }

        searcher = GraphSearch()
        relationships = await searcher.get_entity_relationships(entity_name, depth)

        return {
            "entity": entity_name,
            "depth": depth,
            "relationships": relationships,
            "total_connections": len(relationships),
        }
    except ImportError:
        logger.warning("Graph search module not available")
        return {
            "entity": entity_name,
            "depth": depth,
            "relationships": [],
            "total_connections": 0,
            "error": "Graph search not yet implemented",
        }


# Tool: Get Entity Timeline
@rag_agent.tool
async def get_entity_timeline(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get chronological facts about an entity.

    Shows how information about the entity has evolved over time.
    """
    try:
        if GraphSearch is None:
            return {
                "type": "graph",
                "entity": entity_name,
                "results": [],
                "error": "GraphSearch not available",
            }

        searcher = GraphSearch()
        timeline = await searcher.get_entity_timeline(entity_name, start_date, end_date)

        return timeline
    except ImportError:
        logger.warning("Graph search module not available")
        return []


# Tool: Get Chunks by IDs
@rag_agent.tool
async def get_chunks_by_ids(
    ctx: RunContext[AgentDependencies], chunk_ids: list[str]
) -> list[dict[str, Any]]:
    """
    Retrieve specific chunks by their IDs.

    Used for getting full content when we have chunk references from graph search.
    """
    try:
        if PostgresStore is None:
            return {"type": "storage", "error": "PostgresStore not available"}

        store = PostgresStore()
        chunks = await store.get_chunks_by_ids(chunk_ids)

        return [
            {
                "chunk_id": c["id"],
                "content": c["content"],
                "document_title": c["document_title"],
                "metadata": c["metadata"],
            }
            for c in chunks
        ]
    except ImportError:
        logger.warning("Storage module not available")
        return []


# Helper function for iterative search
async def iterative_search(
    ctx: RunContext[AgentDependencies], query: str, analyzed_query
) -> dict[str, Any]:
    """
    Multi-step iterative search for complex queries.
    """
    results = {"type": "iterative", "steps": []}

    # Step 1: Initial broad search
    initial = await vector_search(ctx, query, limit=5)
    results["steps"].append({"step": 1, "action": "initial_search", "results": initial})

    # Step 2: Extract entities and search graph
    if analyzed_query.entities:
        for entity in analyzed_query.entities[:3]:  # Limit to top 3
            entity_info = await get_entity_relationships(ctx, entity, depth=1)
            results["steps"].append(
                {"step": 2, "action": f"explore_entity_{entity}", "results": entity_info}
            )

    # Step 3: Refine based on findings
    # This would be more sophisticated in production
    # Could use LLM to generate refined queries based on initial results

    return results


# Tool: Comprehensive Search
@rag_agent.tool
async def comprehensive_search(
    ctx: RunContext[AgentDependencies], query: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Perform comprehensive search using multiple strategies in parallel.

    This tool executes all search types and combines results intelligently.
    """
    config = config or ctx.deps.search_preferences

    results = {
        "query": query,
        "search_config": config,
        "vector_results": [],
        "graph_results": [],
        "combined_results": [],
        "metadata": {},
    }

    tasks = []

    # Vector search task
    if config.get("use_vector", True):
        tasks.append(("vector", vector_search(ctx, query, limit=config.get("vector_limit", 15))))

    # Graph search task
    if config.get("use_graph", True):
        tasks.append(("graph", graph_search(ctx, query)))

    # Execute searches in parallel
    if tasks:
        search_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)

        for (search_type, _), result in zip(tasks, search_results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"{search_type} search failed: {result}")
                results["metadata"][f"{search_type}_error"] = str(result)
            elif search_type == "vector":
                results["vector_results"] = result.get("results", [])
            else:
                results["graph_results"] = result

    # Combine and rank results
    if results["vector_results"] or results["graph_results"]:
        try:
            if ResultRanker is None:
                return {"error": "ResultRanker not available", "results": []}

            ranker = ResultRanker()
            results["combined_results"] = await ranker.rank_combined(
                results["vector_results"], results["graph_results"], query
            )
        except ImportError:
            # Simple fallback merging
            results["combined_results"] = results["vector_results"]
            if isinstance(results["graph_results"], dict) and "facts" in results["graph_results"]:
                # Add graph facts as additional results
                for fact in results["graph_results"]["facts"][:5]:
                    results["combined_results"].append(
                        {
                            "content": fact.get("fact", ""),
                            "score": fact.get("confidence", 0.8),
                            "source_type": "graph",
                        }
                    )

    return results


# Tool: Generate Response
@rag_agent.tool
async def generate_response(
    ctx: RunContext[AgentDependencies], query: str, search_results: dict[str, Any]
) -> dict[str, Any]:
    """
    Generate a comprehensive response from search results.

    This tool synthesizes information from multiple sources into a coherent answer.
    """
    # Analyze query for context
    analyzed_query = await ctx.deps.intent_analyzer.analyze(query)

    # Generate response using the response generator
    response = await ctx.deps.response_generator.generate_response(
        query, search_results, analyzed_query
    )

    return {
        "answer": response.answer,
        "citations": [
            {
                "document_title": c.document_title,
                "confidence": c.confidence,
                "content_preview": c.content[:200],
            }
            for c in response.citations
        ],
        "confidence": response.confidence,
        "search_strategy": response.search_strategy_used,
        "follow_up_questions": response.follow_up_questions,
    }


# Main agent execution function
async def run_query(query: str, session_id: str, user_id: str | None = None) -> dict[str, Any]:
    """
    Main entry point for running a query through the agent.

    Args:
        query: User's question
        session_id: Session identifier for context
        user_id: Optional user identifier

    Returns:
        Agent response with answer and metadata
    """
    deps = AgentDependencies(session_id=session_id, user_id=user_id)

    try:
        # Run the agent with the query
        result = await rag_agent.run(query, deps=deps)

        return {
            "status": "success",
            "query": query,
            "response": result.data,
            "metadata": {
                "session_id": session_id,
                "user_id": user_id,
                "model_used": result.model_used if hasattr(result, "model_used") else None,
                "tools_used": result.tools_used if hasattr(result, "tools_used") else [],
            },
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return {
            "status": "error",
            "query": query,
            "error": str(e),
            "metadata": {"session_id": session_id, "user_id": user_id},
        }
