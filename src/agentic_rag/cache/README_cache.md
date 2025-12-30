# Query Cache Package

TTL-based LRU query result caching for the Agentic GraphRAG system.

## Overview

This package provides a thread-safe, async-compatible caching layer for query results with configurable TTL, size limits, and performance logging. Caching reduces latency for repeated queries and decreases load on Neo4j and PostgreSQL databases.

## Modules

### config.py

Pydantic-based cache configuration models.

```python
from src.agentic_rag.cache import CacheConfig, CacheType, get_default_cache_config

# Get default configuration
config = get_default_cache_config()

# Custom configuration
config = CacheConfig(
    enabled=True,
    default_ttl_seconds=300,
    default_max_size=500,
    cache_empty_results=True,
)
```

**Cache Types:**

| CacheType | Default TTL | Max Size | Purpose |
|-----------|-------------|----------|---------|
| VECTOR_SEARCH | 300s | 500 | Semantic vector search results |
| GRAPH_SEARCH | 300s | 200 | Entity and relationship queries |
| MULTI_HOP | 600s | 100 | Path traversal results |
| TEMPORAL_TREND | 600s | 100 | Time-series trend data |
| COMPARISON | 600s | 100 | Entity comparison results |
| HYBRID | 300s | 300 | Combined search results |

### query_cache.py

Core caching implementation with TTL-based LRU eviction.

```python
from src.agentic_rag.cache import (
    get_query_cache,
    generate_cache_key,
    CacheType,
)

# Get singleton cache instance
cache = get_query_cache()

# Generate deterministic cache key
key = generate_cache_key(
    query="Intel revenue trend",
    params={"limit": 10, "quarters": 4},
    prefix="temporal",
)

# Manual cache operations
hit, value = cache.get(CacheType.TEMPORAL_TREND, key)
if not hit:
    value = await expensive_query()
    cache.set(CacheType.TEMPORAL_TREND, key, value)

# Get statistics
stats = cache.get_stats(CacheType.TEMPORAL_TREND)
# Returns: {'hits': 42, 'misses': 8, 'hit_rate_percent': 84.0, ...}

# Invalidate entries
cache.invalidate(CacheType.TEMPORAL_TREND)  # Clear all temporal
cache.invalidate_all()  # Clear everything
```

## Decorators

### with_cache

Decorator for caching async function results.

```python
from src.agentic_rag.cache import with_cache, CacheType

@with_cache(CacheType.MULTI_HOP, key_prefix="graph")
async def find_paths(query: str, max_hops: int = 2):
    return await graph_traverse(query, max_hops)
```

### timeout_wrapper

Decorator for timeout with graceful degradation.

```python
from src.agentic_rag.cache import timeout_wrapper

@timeout_wrapper(timeout_seconds=5.0, fallback=[])
async def slow_query(query: str):
    return await expensive_operation(query)
```

### with_timeout

Async context manager for timeout handling.

```python
from src.agentic_rag.cache import with_timeout

result = await with_timeout(
    expensive_coroutine(),
    timeout_seconds=5.0,
    fallback={"error": "timeout"},
)
```

## Integration

### Phase 02 Query Engines

Caching is integrated into all Phase 02 query engines:

```python
# multi_hop.py
results = await execute_multi_hop(
    connection_manager,
    query,
    use_cache=True,  # Enable caching
    timeout_seconds=5.0,
)

# temporal_queries.py
trend = await execute_temporal_query(
    connection_manager,
    query,
    use_cache=True,
    timeout_seconds=3.0,
)

# entity_comparison.py
comparison = await execute_comparison(
    connection_manager,
    query,
    use_cache=True,
    timeout_seconds=3.0,
)
```

### HybridSearch

HybridSearch caches combined search results:

```python
from src.agentic_rag.search import HybridSearch

search = HybridSearch(connection_manager)
results = await search.search(
    query="Intel acquisitions",
    use_cache=True,  # Default: True
)
```

## Configuration

Environment variables (via settings.py):

| Variable | Default | Description |
|----------|---------|-------------|
| QUERY_CACHE_TTL_SECONDS | 300 | Default TTL for cached results |
| QUERY_CACHE_MAX_SIZE | 500 | Maximum entries per cache type |
| QUERY_CACHE_EMPTY_RESULTS | true | Cache empty results |
| QUERY_TIMEOUT_SECONDS | 5.0 | Default query timeout |

## Performance

**Targets:**
- Cache hit rate: 80%+ for repeated queries
- Latency reduction: 80%+ for cached results
- Memory usage: <100MB for 500 entries per type

**Monitoring:**

```python
cache = get_query_cache()

# Get all statistics
all_stats = cache.get_stats()

# Per-type statistics
stats = cache.get_stats(CacheType.MULTI_HOP)
print(f"Hit rate: {stats['hit_rate_percent']}%")
print(f"Evictions: {stats['evictions']}")
```

## Testing

```bash
# Run cache tests
pytest tests/test_cache.py -v

# Test with coverage
pytest tests/test_cache.py --cov=src/agentic_rag/cache
```

## Dependencies

- cachetools: TTL-based LRU cache implementation
- pydantic: Configuration validation
- structlog: Structured logging

## Related Documentation

- [CLAUDE.md](../../../CLAUDE.md) - Session 05 caching integration
- [Phase 02 Completion Report](../../../PHASE02_COMPLETION_REPORT.md)
