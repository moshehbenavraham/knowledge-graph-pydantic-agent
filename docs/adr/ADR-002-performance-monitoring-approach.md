# ADR-002: Performance Monitoring Approach

**Status**: Accepted
**Date**: 2025-12-30
**Phase**: 03 - Production Readiness & User Experience
**Session**: 02 - Performance Monitoring and Profiling

---

## Context

As the Agentic GraphRAG System grew across Phases 01 and 02, identifying performance bottlenecks became increasingly difficult. Queries could be slow due to vector search, graph traversal, embedding generation, or LLM calls - but without instrumentation, pinpointing the cause required manual debugging.

We needed a lightweight profiling system that:
1. Could be enabled/disabled without code changes
2. Had minimal overhead when disabled (<1ms)
3. Integrated with existing structlog infrastructure
4. Supported both sync and async code paths

## Decision

We implemented a **decorator-based profiling system** with the following components:

### 1. Profiling Decorators

Three decorator variants for different use cases:
- `@profile_async` - For async functions (validates function is coroutine)
- `@profile_sync` - For sync functions (validates function is not coroutine)
- `@profile` - Universal decorator that auto-detects async vs sync

All decorators support:
- Custom naming via `name` parameter
- Optional argument logging via `log_args`
- Optional result preview logging via `log_result`

### 2. Configuration-Controlled Overhead

Profiling is controlled via `PROFILING_ENABLED` setting:
- When disabled: decorators pass through directly (<1ms overhead)
- When enabled: timing captured and logged via structlog

This allows production deployments to keep decorators in place but disabled.

### 3. ProfileResult Data Class

Captures execution metrics:
- `function_name`: Identifier for the profiled function
- `duration_seconds` / `duration_ms`: Execution time
- `success`: Whether execution completed without exception
- `error`: Error message if execution failed

### 4. Profiler Context Manager

For profiling arbitrary code blocks (not just functions):
```python
with Profiler("database_query") as p:
    result = execute_query(sql)
print(f"Query took {p.duration_ms:.2f}ms")
```

### 5. Metrics Modules

Additional specialized metrics in `src/agentic_rag/metrics/`:
- `intent_metrics.py` - Query intent analysis statistics
- `cache_metrics.py` - Cache hit/miss rates
- `memory_monitor.py` - Memory usage tracking

## Consequences

### Positive

- **Zero-cost when disabled**: Production deployments unaffected
- **Easy instrumentation**: Single decorator to profile any function
- **Structured output**: Integrates with structlog for consistent logging
- **Flexible**: Supports async, sync, and code block profiling
- **Safe**: Exceptions properly propagated, timing still captured

### Negative

- **Requires configuration**: Must set `PROFILING_ENABLED=true` to see output
- **Log volume**: Enabling profiling increases log output significantly
- **No aggregation**: Individual timings only, no built-in histograms

### Trade-offs

We chose decorator-based profiling over APM integration because:
1. Zero external dependencies
2. Works in development and production
3. Integrates with existing structlog pipeline
4. No vendor lock-in

For production monitoring at scale, this can be supplemented with Prometheus metrics (separate concern).

## Implementation

**Key Files**:
- `src/agentic_rag/metrics/profiler.py` - Core profiling decorators and context manager
- `src/agentic_rag/metrics/intent_metrics.py` - Intent analysis metrics
- `src/agentic_rag/metrics/cache_metrics.py` - Cache performance metrics
- `src/agentic_rag/metrics/memory_monitor.py` - Memory usage tracking

**Usage Example**:
```python
from src.agentic_rag.metrics import profile_async, Profiler

@profile_async(name="vector_search")
async def search_documents(query: str) -> list[dict]:
    # Implementation
    pass

# Or for code blocks:
async def complex_operation():
    with Profiler("embedding_generation") as p:
        embeddings = await generate_embeddings(texts)
    logger.info("Embeddings generated", duration_ms=p.duration_ms)
```

**Configuration**:
```bash
# In .env
PROFILING_ENABLED=true  # Enable profiling (false by default)
LOG_LEVEL=DEBUG         # See detailed profiling output
```

## Related Decisions

- ADR-001: Error handling captures failure metrics alongside timing
- Analytics System (existing): Long-term metrics storage in PostgreSQL

---

**Last Updated**: 2025-12-30
