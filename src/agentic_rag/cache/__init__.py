"""
Query caching module for Agentic GraphRAG.

Provides TTL-based LRU caching for query results with configurable settings,
performance logging, and timeout handling.

Example usage:
    from src.agentic_rag.cache import (
        get_query_cache,
        CacheType,
        with_cache,
        timeout_wrapper,
    )

    # Get cache instance
    cache = get_query_cache()

    # Manual caching
    cache_key = generate_cache_key("my query", {"limit": 10})
    hit, value = cache.get(CacheType.HYBRID, cache_key)
    if not hit:
        value = await expensive_query()
        cache.set(CacheType.HYBRID, cache_key, value)

    # Decorator-based caching
    @with_cache(CacheType.MULTI_HOP, key_prefix="graph")
    async def my_query(query: str, limit: int = 10):
        return await expensive_operation(query, limit)

    # Timeout wrapper
    @timeout_wrapper(timeout_seconds=5.0, fallback=[])
    async def my_slow_query(query: str):
        return await slow_operation(query)
"""

from .config import (
    CacheConfig,
    CacheEntryConfig,
    CacheType,
    get_default_cache_config,
)
from .query_cache import (
    CacheStats,
    QueryCache,
    generate_cache_key,
    get_query_cache,
    reset_query_cache,
    timeout_wrapper,
    with_cache,
    with_timeout,
)

__all__ = [
    "CacheConfig",
    "CacheEntryConfig",
    "CacheStats",
    "CacheType",
    "QueryCache",
    "generate_cache_key",
    "get_default_cache_config",
    "get_query_cache",
    "reset_query_cache",
    "timeout_wrapper",
    "with_cache",
    "with_timeout",
]
