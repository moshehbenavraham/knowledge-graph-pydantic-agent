"""
Dependency injection layer for FastAPI endpoints.

Provides database sessions, search clients, agent orchestrator, and cache.
"""

from collections.abc import AsyncGenerator

import structlog
from fastapi import Depends, HTTPException, status

from src.agent.unified_agent import UnifiedAgentDeps
from src.agentic_rag.search.hybrid_search import HybridSearch
from src.agentic_rag.search.intent_analyzer import IntentAnalyzer
from src.agentic_rag.search.vector_search import VectorSearch
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.agentic_rag.storage.graphiti_client import GraphitiClient
from src.agentic_rag.storage.neo4j_store import Neo4jStore
from src.agentic_rag.storage.postgres_store import PostgresStore
from src.config import get_settings
from src.utils.cache import RedisCache, get_cache

logger = structlog.get_logger()

# Global instances (initialized in lifespan)
_connection_manager: ConnectionManager | None = None
_postgres_store: PostgresStore | None = None
_neo4j_store: Neo4jStore | None = None
_graphiti_client: GraphitiClient | None = None
_cache_manager: RedisCache | None = None


async def init_dependencies():
    """Initialize global dependencies during app startup."""
    global _connection_manager, _postgres_store, _neo4j_store
    global _graphiti_client, _cache_manager

    settings = get_settings()
    logger.info("Initializing API dependencies")

    try:
        # Initialize cache manager
        _cache_manager = get_cache()
        logger.info("Cache manager initialized")

        # Initialize connection manager
        _connection_manager = ConnectionManager()
        logger.info("Connection manager initialized")

        # Initialize storage layers
        _postgres_store = PostgresStore(_connection_manager)
        logger.info("PostgreSQL store initialized")

        # Initialize Neo4j if enabled
        if settings.enable_graph_rag:
            _neo4j_store = Neo4jStore(_connection_manager)
            _graphiti_client = GraphitiClient()
            logger.info("Neo4j and Graphiti initialized")
        else:
            logger.info("Graph RAG disabled, skipping Neo4j initialization")

    except Exception as e:
        logger.error("Failed to initialize dependencies", error=str(e))
        raise


async def cleanup_dependencies():
    """Cleanup dependencies during app shutdown."""
    global _connection_manager, _postgres_store, _neo4j_store
    global _graphiti_client

    logger.info("Cleaning up API dependencies")

    try:
        # Close database connections
        if _connection_manager:
            await _connection_manager.close_all()
            logger.info("Database connections closed")

        # Cleanup stores
        if _postgres_store:
            await _postgres_store.close()

        if _neo4j_store:
            await _neo4j_store.close()

    except Exception as e:
        logger.error("Error during dependency cleanup", error=str(e))


# ===== Dependency providers =====


async def get_connection_manager() -> ConnectionManager:
    """Get connection manager instance."""
    if _connection_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection manager not initialized",
        )
    return _connection_manager


async def get_postgres_store() -> PostgresStore:
    """Get PostgreSQL store instance."""
    if _postgres_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL store not initialized",
        )
    return _postgres_store


async def get_neo4j_store() -> Neo4jStore | None:
    """Get Neo4j store instance (if enabled)."""
    return _neo4j_store


async def get_graphiti_client() -> GraphitiClient | None:
    """Get Graphiti client instance (if enabled)."""
    return _graphiti_client


async def get_cache_manager() -> RedisCache:
    """Get cache manager instance."""
    if _cache_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cache manager not initialized"
        )
    return _cache_manager


async def get_vector_search(
    postgres_store: PostgresStore = Depends(get_postgres_store),
) -> VectorSearch:
    """Get vector search instance."""
    return VectorSearch(postgres_store)


async def get_hybrid_search(
    connection_manager: ConnectionManager = Depends(get_connection_manager),
) -> HybridSearch:
    """Get hybrid search instance."""
    return HybridSearch(connection_manager)


async def get_intent_analyzer() -> IntentAnalyzer:
    """Get intent analyzer instance."""
    return IntentAnalyzer()


async def get_agent_deps(
    postgres_store: PostgresStore = Depends(get_postgres_store),
    neo4j_store: Neo4jStore | None = Depends(get_neo4j_store),
    cache_manager: RedisCache = Depends(get_cache_manager),
) -> UnifiedAgentDeps:
    """
    Get unified agent dependencies.

    Returns configured UnifiedAgentDeps for use with super_agent.
    """
    settings = get_settings()

    return UnifiedAgentDeps(
        postgres_store=postgres_store,
        neo4j_store=neo4j_store,
        cache_manager=cache_manager,
        enable_web_search=settings.enable_web_search,
        enable_sql_query=settings.enable_sql_query,
        enable_code_execution=settings.enable_code_execution,
    )


# ===== Database session providers =====


async def get_postgres_session() -> AsyncGenerator:
    """
    Get PostgreSQL async session.

    Yields session and ensures cleanup.
    """
    conn_manager = await get_connection_manager()

    async with conn_manager.get_postgres_connection() as conn:
        yield conn


async def get_neo4j_session() -> AsyncGenerator:
    """
    Get Neo4j async session.

    Yields session and ensures cleanup.
    """
    conn_manager = await get_connection_manager()

    if not conn_manager.neo4j_driver:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Neo4j not available"
        )

    async with conn_manager.get_neo4j_session() as session:
        yield session


# ===== Health check dependency =====


async def check_database_health() -> dict:
    """
    Check health of database connections.

    Returns health status dict.
    """
    health = {
        "postgres": False,
        "neo4j": False,
        "cache": False,
    }

    try:
        # Check PostgreSQL
        if _postgres_store:
            health["postgres"] = await _postgres_store.health_check()

        # Check Neo4j
        if _neo4j_store:
            health["neo4j"] = await _neo4j_store.health_check()

        # Check cache
        if _cache_manager:
            health["cache"] = _cache_manager.health_check()

    except Exception as e:
        logger.error("Health check failed", error=str(e))

    return health


# ===== Configuration dependency =====


async def get_api_settings() -> dict:
    """Get API configuration settings."""
    settings = get_settings()

    return {
        "version": "0.8.0",
        "environment": settings.app_env,
        "features": {
            "graph_rag": settings.enable_graph,
            "web_search": settings.web_search_provider is not None,
            "streaming": True,
            "caching": settings.enable_redis_cache,
        },
        "limits": {
            "max_chunk_size": settings.chunk_size,
            "max_results": 100,
            "rate_limit_per_minute": 60,
        },
    }
