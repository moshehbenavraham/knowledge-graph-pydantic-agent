"""
Unified Super Agent - The One Agent to Rule Them All
=====================================================

This is the ultimate AI agent that combines all capabilities:
- Intelligent intent-based search routing (from agentic_rag)
- Web search with multiple providers (Jina, Brave, SearXNG)
- Advanced RAG with vector and graph search
- SQL query execution on tabular data
- Image analysis with vision models
- Safe code execution
- Document management
- Memory/personalization support
- Comprehensive search strategies

No more confusion - just one powerful, clean agent.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from httpx import AsyncClient
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from supabase.client import Client

from src.clients.llm import get_model
from src.config.agent import agent_config
from src.tools import (
    execute_safe_code_tool,
    execute_sql_query_tool,
    get_document_content_tool,
    image_analysis_tool,
    list_documents_tool,
    retrieve_relevant_documents_tool,
    web_search_tool,
)
from src.tools.rag import graph_query_tool, graph_traverse_tool, smart_search_tool

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)


# ========== Unified Dependencies ==========
@dataclass
class UnifiedAgentDeps:
    """All dependencies our super-agent needs."""

    # Core clients
    supabase: Client
    embedding_client: AsyncOpenAI
    http_client: AsyncClient

    # Web search configuration
    brave_api_key: str | None = None
    searxng_base_url: str | None = None
    jina_api_key: str | None = None
    web_search_provider: str | None = None

    # User context
    memories: str = ""
    session_id: str = "default"
    user_id: str | None = None

    # Search preferences
    search_config: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.search_config is None:
            self.search_config = {
                "use_vector": True,
                "use_graph": True,
                "use_hybrid": True,
                "confidence_threshold": 0.7,
                "max_results": 20,
            }


# ========== System Prompt ==========
UNIFIED_SYSTEM_PROMPT = """
You are an advanced AI assistant with comprehensive capabilities for research, analysis, and problem-solving.

You excel at:
1. **Intelligent Search**: Analyzing queries to select optimal search strategies
2. **Information Synthesis**: Combining data from multiple sources into coherent answers
3. **Data Analysis**: SQL queries, code execution, and numerical analysis
4. **Document Understanding**: RAG retrieval, image analysis, and content extraction
5. **Web Research**: Real-time information gathering from the internet
6. **Personalization**: Using memories to provide contextual responses

Core Principles:
- Always check memories first for personalized context
- Select the most appropriate tools based on query intent
- Provide well-sourced, accurate information
- Be proactive in offering comprehensive answers
- Acknowledge limitations when information is incomplete

Tool Selection Strategy:

**Search & Retrieval:**
- **smart_search** (PRIMARY): Use for most queries - automatically selects best strategy
  - Handles semantic search, entity queries, temporal queries, relationships
  - Returns chunks + entities + facts with intent analysis
  - Examples: "What does X say about Y?", "Find documents about Z"

- **retrieve_documents**: Simple vector search for straightforward content retrieval
  - Use when you just need similar content without graph context
  - Faster than smart_search but less comprehensive

- **query_knowledge_graph**: Direct graph queries for entity exploration
  - Use for: "How is X related to Y?", "What facts do we have about Z?"
  - Requires entity names, returns facts and relationships
  - Only works when knowledge graph is enabled

- **graph_traverse**: Multi-hop path traversal for discovering indirect connections
  - Use for: "What products did companies acquired by Intel release?"
  - Use for: "Which executives are connected through shared board memberships?"
  - Finds paths through 1-3 relationship hops with strength filtering

- **list_all_documents**: Get inventory of available documents
- **get_full_document**: Retrieve complete document by ID

**Other Tools:**
- **search_web**: Real-time information from the internet (current events)
- **execute_sql** / **query_tabular_data**: Analyze uploaded CSV/Excel datasets
- **analyze_image**: Extract information from images using vision models
- **execute_python_code**: Calculations, data transformation, algorithms
- **comprehensive_search**: Parallel multi-strategy search for complex queries

Response Format:
- Start with a direct answer when possible
- Include supporting evidence and citations
- Explain your reasoning process
- Suggest follow-up questions when appropriate
"""


# ========== Initialize the Super Agent ==========
super_agent = Agent(
    get_model(),
    system_prompt=UNIFIED_SYSTEM_PROMPT,
    deps_type=UnifiedAgentDeps,
    retries=2,
)


# ========== Memory Tool ==========
@super_agent.system_prompt
def add_memories(ctx: RunContext[UnifiedAgentDeps]) -> str:
    """Add user memories to context."""
    if ctx.deps.memories:
        return f"\nUser Memories:\n{ctx.deps.memories}"
    return ""


# ========== Smart Search Tool (Intelligent Routing) ==========
@super_agent.tool
async def smart_search(
    ctx: RunContext[UnifiedAgentDeps], query: str, limit: int = 10
) -> dict[str, Any]:
    """
    Intelligent search using the full Agentic RAG stack.

    This is the PRIMARY search tool that automatically:
    - Analyzes query intent (semantic, entity, temporal, relationship)
    - Selects optimal strategy (vector, graph, hybrid)
    - Combines results from multiple sources
    - Returns comprehensive results with entities and facts

    Use this for most search queries - it will intelligently route to the best approach.

    Args:
        query: User's search query
        limit: Maximum number of results (default 10)

    Returns:
        Rich search results with chunks, entities, facts, and metadata
    """
    logger.info(f"Smart search (Agentic RAG) for: {query}")

    try:
        # Use the new smart_search_tool from rag.py
        result = await smart_search_tool(user_query=query, analyze_intent=True, limit=limit)
        return result

    except Exception as e:
        logger.error(f"Smart search failed: {e}")
        return {
            "query": query,
            "error": str(e),
            "chunks": [],
            "entities": [],
            "facts": [],
        }


# ========== Graph Query Tool ==========
@super_agent.tool
async def query_knowledge_graph(
    ctx: RunContext[UnifiedAgentDeps],
    entity_name: str,
    query_type: str = "entity_facts",
    limit: int = 10,
) -> dict[str, Any]:
    """
    Query the knowledge graph directly for entity and relationship exploration.

    Use when you need to:
    - Find relationships between entities ("How is X related to Y?")
    - Get facts about specific entities ("Tell me about OpenAI")
    - Explore temporal information ("What happened with X in 2024?")
    - Discover entity connections

    Query types:
    - entity_facts: Get all facts about an entity
    - entity_relationships: Get relationships for an entity
    - temporal_facts: Get facts in chronological order

    Args:
        entity_name: Name of the entity to query
        query_type: Type of graph query to perform
        limit: Maximum number of results

    Returns:
        Dictionary with facts, entities, and relationships from the graph
    """
    logger.info(f"Graph query for entity: {entity_name}, type: {query_type}")

    try:
        result = await graph_query_tool(entity_name=entity_name, query_type=query_type, limit=limit)
        return result

    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        return {
            "entity": entity_name,
            "query_type": query_type,
            "error": str(e),
        }


# ========== Graph Traverse Tool (Multi-Hop) ==========
@super_agent.tool
async def graph_traverse(
    ctx: RunContext[UnifiedAgentDeps],
    start_entity: str,
    end_entity: str | None = None,
    max_hops: int = 2,
    min_strength: float = 0.3,
    entity_type_filter: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Traverse the knowledge graph to find multi-hop relationships.

    Use for discovering indirect connections:
    - "What products did companies acquired by Intel release?" (Company -> Acquisition -> Products)
    - "Which executives are connected through shared board memberships?"
    - "How is entity A connected to entity B through intermediaries?"

    The tool finds paths through 1-3 relationship hops, filtering by
    relationship strength to ensure quality connections.

    Args:
        start_entity: Starting entity name or search pattern
        end_entity: Optional ending entity (for specific connections)
        max_hops: Maximum path length 1-3 (default 2)
        min_strength: Minimum relationship strength 0.0-1.0 (default 0.3)
        entity_type_filter: Filter by entity type (e.g., "organization", "person")
        limit: Maximum paths to return (default 20)

    Returns:
        Dictionary with discovered paths, summaries, and metadata
    """
    logger.info(
        f"Graph traverse from {start_entity} "
        f"(end={end_entity}, hops={max_hops}, strength>={min_strength})"
    )

    try:
        result = await graph_traverse_tool(
            start_entity=start_entity,
            end_entity=end_entity,
            max_hops=max_hops,
            min_strength=min_strength,
            entity_type_filter=entity_type_filter,
            limit=limit,
        )
        return result

    except Exception as e:
        logger.error(f"Graph traverse failed: {e}")
        return {
            "start_entity": start_entity,
            "end_entity": end_entity,
            "error": str(e),
            "paths": [],
        }


# ========== Core RAG Tools ==========
@super_agent.tool
async def retrieve_documents(ctx: RunContext[UnifiedAgentDeps], query: str, limit: int = 10) -> str:
    """
    Retrieve relevant documents using RAG with vector search.

    Best for:
    - Finding similar content
    - Conceptual matches
    - General information retrieval

    Args:
        query: Search query
        limit: Maximum number of results (default 10)

    Returns:
        Formatted string with relevant document chunks
    """
    logger.info(f"RAG retrieval for: {query}")
    try:
        return await retrieve_relevant_documents_tool(
            ctx.deps.supabase, ctx.deps.embedding_client, query, limit=limit
        )
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        return f"Error: Document retrieval failed - {e!s}"


@super_agent.tool
async def list_all_documents(ctx: RunContext[UnifiedAgentDeps]) -> list[str]:
    """
    List all available documents in the knowledge base.

    Returns metadata including:
    - Document IDs
    - File paths/URLs
    - Document types
    - Schema information for structured data
    """
    logger.info("Listing all documents")
    return await list_documents_tool(ctx.deps.supabase)


@super_agent.tool
async def get_full_document(ctx: RunContext[UnifiedAgentDeps], document_id: str) -> str:
    """
    Get the complete content of a specific document.

    Args:
        document_id: The ID or file path of the document

    Returns:
        Full document content with all chunks combined
    """
    logger.info(f"Getting full document: {document_id}")
    return await get_document_content_tool(ctx.deps.supabase, document_id)


# ========== Web Search Tool ==========
@super_agent.tool
async def search_web(ctx: RunContext[UnifiedAgentDeps], query: str) -> str:
    """
    Search the web for current information.

    Supports multiple providers:
    - Jina.ai: Clean, formatted markdown content
    - Brave: Search results with titles and descriptions
    - SearXNG: Privacy-focused search results

    Args:
        query: Web search query

    Returns:
        Formatted search results from the configured provider
    """
    logger.info(f"Web search for: {query}")
    return await web_search_tool(
        query=query,
        http_client=ctx.deps.http_client,
        brave_api_key=ctx.deps.brave_api_key,
        searxng_base_url=ctx.deps.searxng_base_url,
        jina_api_key=ctx.deps.jina_api_key,
        search_provider=ctx.deps.web_search_provider,
    )


# ========== SQL Query Tool ==========
@super_agent.tool
async def execute_sql(ctx: RunContext[UnifiedAgentDeps], sql_query: str) -> str:
    """
    Execute SQL queries on tabular data.

    Use for:
    - Data analysis
    - Aggregations and statistics
    - Filtering structured data

    IMPORTANT: Always use list_all_documents first to get valid file IDs.

    Example queries:
    ```sql
    SELECT AVG((row_data->>'revenue')::numeric)
    FROM document_rows
    WHERE dataset_id = 'actual_file_id';

    SELECT
        row_data->>'category' as category,
        SUM((row_data->>'sales')::numeric) as total_sales
    FROM document_rows
    WHERE dataset_id = 'actual_file_id'
    GROUP BY row_data->>'category';
    ```

    Args:
        sql_query: Read-only SQL query to execute

    Returns:
        Query results in JSON format
    """
    logger.info(f"Executing SQL: {sql_query}")
    return await execute_sql_query_tool(ctx.deps.supabase, sql_query)


# ========== Image Analysis Tool ==========
@super_agent.tool
async def analyze_image(
    ctx: RunContext[UnifiedAgentDeps], document_id: str, analysis_query: str
) -> str:
    """
    Analyze images using vision models.

    Process:
    1. Use list_all_documents to find available images
    2. Get the exact document_id for the image
    3. Call this tool with your analysis question

    Args:
        document_id: ID or file path of the image
        analysis_query: What to extract/analyze from the image

    Returns:
        Detailed image analysis based on the query
    """
    logger.info(f"Analyzing image {document_id}: {analysis_query}")
    return await image_analysis_tool(ctx.deps.supabase, document_id, analysis_query)


# ========== Code Execution Tool ==========
@super_agent.tool
async def execute_python_code(ctx: RunContext[UnifiedAgentDeps], code: str) -> str:
    """
    Execute Python code in a safe, sandboxed environment.

    Use for:
    - Data calculations
    - Algorithm implementation
    - Data transformation
    - Generating visualizations (text-based)

    IMPORTANT: Use print() to output results.

    Example:
    ```python
    import math
    result = math.sqrt(16)
    print(f"Square root of 16 is: {result}")
    ```

    Args:
        code: Python code to execute

    Returns:
        Standard output from the code execution
    """
    logger.info(f"Executing Python code: {code[:100]}...")
    return execute_safe_code_tool(code)


# ========== SQL Query Tool ==========
@super_agent.tool
async def query_tabular_data(ctx: RunContext[UnifiedAgentDeps], sql_query: str) -> str:
    """
    Execute SQL queries on uploaded CSV/Excel datasets stored in document_rows table.

    **IMPORTANT**: First use list_documents to find CSV/Excel files and their dataset_ids.
    Then query the document_rows table using the dataset_id.

    The document_rows table structure:
    - dataset_id: UUID of the parent document (get from list_documents)
    - row_data: JSONB containing all column data
    - row_index: Original row number

    Query pattern for CSV data:
    ```sql
    SELECT
        row_data->>'column_name' as column_name,
        SUM((row_data->>'sales')::float) as total
    FROM document_rows
    WHERE dataset_id = 'uuid-from-list-documents'
    GROUP BY row_data->>'column_name'
    ```

    Use for:
    - Analyzing uploaded CSV/Excel files
    - Aggregations (SUM, AVG, COUNT, etc.)
    - Filtering and grouping tabular data
    - Statistical analysis

    Args:
        sql_query: READ-ONLY SQL query (SELECT statements only)

    Returns:
        JSON formatted query results
    """
    logger.info("Executing SQL query on tabular data")
    return await execute_sql_query_tool(ctx.deps.supabase, sql_query)


# ========== Advanced Search Tools ==========
@super_agent.tool
async def comprehensive_search(
    ctx: RunContext[UnifiedAgentDeps],
    query: str,
    use_vector: bool = True,
    use_graph: bool = True,
    max_results: int = 20,
) -> dict[str, Any]:
    """
    Perform comprehensive search using multiple strategies in parallel.

    Executes all search types and intelligently combines results.

    Args:
        query: Search query
        use_vector: Enable vector/semantic search
        use_graph: Enable graph/relationship search (when available)
        max_results: Maximum combined results

    Returns:
        Combined and ranked results from all search methods
    """
    logger.info(f"Comprehensive search for: {query}")

    results = {
        "query": query,
        "search_config": {
            "use_vector": use_vector,
            "use_graph": use_graph,
            "max_results": max_results,
        },
        "vector_results": [],
        "graph_results": [],
        "combined_results": [],
    }

    tasks = []

    # Vector search task
    if use_vector:
        tasks.append(
            (
                "vector",
                retrieve_relevant_documents_tool(
                    ctx.deps.supabase, ctx.deps.embedding_client, query
                ),
            )
        )

    # Execute searches in parallel
    if tasks:
        search_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)

        for (search_type, _), result in zip(tasks, search_results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"{search_type} search failed: {result}")
                results[f"{search_type}_error"] = str(result)
            elif search_type == "vector":
                results["vector_results"] = result  # type: ignore[assignment]
                results["combined_results"] = result  # type: ignore[assignment]

    return results


@super_agent.tool
async def iterative_search(
    ctx: RunContext[UnifiedAgentDeps], query: str, _max_iterations: int = 3
) -> dict[str, Any]:
    """
    Multi-step iterative search for complex queries.

    Process:
    1. Initial broad search
    2. Extract key entities/concepts
    3. Deep dive into specific aspects
    4. Synthesize comprehensive answer

    Args:
        query: Complex query requiring multiple search steps
        _max_iterations: Maximum refinement iterations (reserved for future use)

    Returns:
        Detailed results from iterative exploration
    """
    logger.info(f"Iterative search for: {query}")

    iterations: list[dict[str, Any]] = []
    results: dict[str, Any] = {"query": query, "iterations": iterations, "final_answer": ""}

    # Step 1: Initial search
    initial_results = await retrieve_relevant_documents_tool(
        ctx.deps.supabase, ctx.deps.embedding_client, query
    )

    iterations.append({"step": 1, "action": "initial_search", "results": initial_results})

    # Step 2: Would extract entities and refine search
    # This is where we'd use NER and query expansion

    # Step 3: Final synthesis
    results["final_answer"] = initial_results

    return results


# ========== Main Execution Function ==========
async def run_unified_agent(
    query: str,
    session_id: str = "default",
    user_id: str | None = None,
    supabase_client: Client | None = None,
    embedding_client: AsyncOpenAI | None = None,
    http_client: AsyncClient | None = None,
    memories: str = "",
    search_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Main entry point for the unified super-agent.

    Args:
        query: User's question or request
        session_id: Session identifier for context
        user_id: Optional user identifier
        supabase_client: Supabase client instance
        embedding_client: OpenAI client for embeddings
        http_client: HTTP client for web requests
        memories: User context/memories
        search_config: Search configuration preferences

    Returns:
        Agent response with answer and metadata
    """
    # Create dependencies
    from src.clients.database import get_supabase_client
    from src.clients.embedding import get_embedding_client
    from src.config.clients import clients_config

    # Use provided clients or get from centralized config
    resolved_supabase = supabase_client or get_supabase_client()
    resolved_embedding = embedding_client or get_embedding_client()

    deps = UnifiedAgentDeps(
        supabase=resolved_supabase,
        embedding_client=resolved_embedding,
        http_client=http_client
        or clients_config.create_http_client(),  # CONST-III-001 - Use centralized HTTP client factory
        brave_api_key=agent_config.brave_api_key,
        searxng_base_url=agent_config.searxng_base_url,
        jina_api_key=agent_config.jina_api_key,
        web_search_provider=(
            agent_config.web_search_provider.value if agent_config.web_search_provider else None
        ),
        memories=memories,
        session_id=session_id,
        user_id=user_id,
        search_config=search_config,
    )

    try:
        # Run the agent
        result = await super_agent.run(query, deps=deps)

        return {
            "status": "success",
            "query": query,
            "response": result.output,
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


# Export the main components
__all__ = [
    "UnifiedAgentDeps",
    "add_memories",
    "analyze_image",
    "comprehensive_search",
    "execute_python_code",
    "execute_sql",
    "get_full_document",
    "graph_traverse",
    "iterative_search",
    "list_all_documents",
    "query_knowledge_graph",
    "query_tabular_data",
    "retrieve_documents",
    "run_unified_agent",
    "search_web",
    "smart_search",
    "super_agent",
]
