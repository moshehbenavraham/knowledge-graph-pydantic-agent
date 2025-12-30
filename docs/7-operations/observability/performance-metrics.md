# Performance Metrics Guide

This document describes the performance metrics available in the Agentic GraphRAG system for monitoring, profiling, and establishing baseline benchmarks.

## Overview

The system provides four categories of performance metrics:

1. **Intent-Specific Latency Histograms** - Query latency segmented by detected intent
2. **Cache Statistics** - Hit/miss rates and eviction tracking
3. **Memory Monitoring** - Periodic memory usage logging and gauges
4. **Development Profiling** - Function-level timing for bottleneck identification

All metrics are exported to Prometheus and available at the `/metrics` endpoint.

---

## Intent-Specific Latency Metrics

### Metric Names

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `agentic_rag_search_latency_seconds` | Histogram | `intent_type` | Search query latency in seconds |
| `agentic_rag_search_queries_total` | Counter | `intent_type` | Total search queries by intent |

### Intent Types

The following intent types are tracked:

- `VECTOR_HEAVY` - Semantic content search
- `GRAPH_HEAVY` - Entity/relationship-focused queries
- `HYBRID` - Combined vector and graph search
- `TEMPORAL` - Time-based queries
- `ENTITY_FOCUSED` - Entity-centric queries
- `MULTI_HOP` - Path traversal queries
- `TEMPORAL_TREND` - Time-series analysis
- `COMPARISON` - Cross-entity comparison

### Histogram Buckets

Latency histogram uses custom buckets optimized for query performance:

```
[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0] seconds
```

### Example Prometheus Queries

```promql
# Average latency by intent type (5 minute window)
rate(agentic_rag_search_latency_seconds_sum[5m])
/ rate(agentic_rag_search_latency_seconds_count[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(agentic_rag_search_latency_seconds_bucket[5m]))

# Query rate by intent type
rate(agentic_rag_search_queries_total[5m])
```

### Configuration

```bash
# .env
INTENT_METRICS_ENABLED=true  # Enable/disable intent metrics (default: true)
```

---

## Cache Metrics

### Metric Names

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `agentic_rag_cache_hits_total` | Counter | `cache_type` | Total cache hits |
| `agentic_rag_cache_misses_total` | Counter | `cache_type` | Total cache misses |
| `agentic_rag_cache_evictions_total` | Counter | `cache_type` | Total cache evictions |
| `agentic_rag_cache_hit_rate_percent` | Gauge | `cache_type` | Current hit rate percentage |
| `agentic_rag_cache_current_size` | Gauge | `cache_type` | Current number of cached entries |

### Cache Types

- `vector` - Vector search results
- `graph` - Graph query results
- `hybrid` - Combined search results
- `entity` - Entity lookup results
- `document` - Document metadata

### Example Prometheus Queries

```promql
# Cache hit rate over time
agentic_rag_cache_hit_rate_percent

# Cache utilization
agentic_rag_cache_current_size / agentic_rag_cache_max_size

# Eviction rate
rate(agentic_rag_cache_evictions_total[5m])
```

### Configuration

```bash
# .env
CACHE_METRICS_ENABLED=true  # Enable/disable cache metrics (default: true)
```

---

## Memory Monitoring

### Metric Names

| Metric | Type | Description |
|--------|------|-------------|
| `agentic_rag_memory_rss_bytes` | Gauge | Process resident set size |
| `agentic_rag_memory_vms_bytes` | Gauge | Process virtual memory size |
| `agentic_rag_memory_percent` | Gauge | System memory usage percentage |

### Log Output

Memory usage is logged at INFO level with structured fields:

```json
{
  "event": "Memory usage",
  "rss_mb": 256.4,
  "vms_mb": 512.8,
  "system_percent": 45.2,
  "available_mb": 8192.0
}
```

### Configuration

```bash
# .env
MEMORY_MONITOR_ENABLED=true     # Enable/disable memory monitoring (default: true)
MEMORY_MONITOR_INTERVAL=60      # Logging interval in seconds (default: 60)
```

---

## Development Profiling

### Decorators

#### `@profile_async`

Profile async functions with detailed timing:

```python
from src.agentic_rag.metrics import profile_async

@profile_async(name="vector_search")
async def search(query: str) -> list[dict]:
    return await perform_search(query)

@profile_async(log_args=True, log_result=True)
async def detailed_search(query: str) -> dict:
    return await search(query)
```

#### `@profile_sync`

Profile synchronous functions:

```python
from src.agentic_rag.metrics import profile_sync

@profile_sync(name="data_processing")
def process_data(data: list) -> dict:
    return {"count": len(data)}
```

#### `@profile`

Universal decorator that auto-detects async vs sync:

```python
from src.agentic_rag.metrics import profile

@profile()
def any_function(x: int) -> int:
    return x * 2

@profile()
async def any_async_function(x: int) -> int:
    return x * 2
```

### Context Manager

For manual profiling of code blocks:

```python
from src.agentic_rag.metrics import Profiler

with Profiler("database_query") as p:
    result = execute_query(sql)

print(f"Query took {p.duration_ms:.2f}ms")
```

### Log Output

When profiling is enabled, logs include timing information:

```json
{
  "event": "Profiling async function complete",
  "function": "vector_search",
  "duration_ms": 150.234,
  "success": true
}
```

### Configuration

```bash
# .env
PROFILING_ENABLED=false  # Enable/disable profiling (default: false)
                         # Adds minimal overhead (~1ms) when disabled
```

---

## Baseline Benchmarks

These benchmarks establish performance expectations for regression testing.

### Query Latency Targets

| Intent Type | P50 Target | P95 Target | P99 Target |
|-------------|------------|------------|------------|
| VECTOR_HEAVY | < 100ms | < 250ms | < 500ms |
| GRAPH_HEAVY | < 200ms | < 500ms | < 1000ms |
| HYBRID | < 300ms | < 750ms | < 1500ms |
| TEMPORAL | < 150ms | < 400ms | < 800ms |
| ENTITY_FOCUSED | < 150ms | < 400ms | < 800ms |
| MULTI_HOP | < 500ms | < 1000ms | < 2000ms |
| TEMPORAL_TREND | < 300ms | < 750ms | < 1500ms |
| COMPARISON | < 500ms | < 1000ms | < 2000ms |

### Cache Performance Targets

| Metric | Target |
|--------|--------|
| Hit Rate | > 70% (warm cache) |
| Miss Rate | < 30% |
| P99 Lookup Time | < 5ms |

### Memory Targets

| Metric | Target |
|--------|--------|
| Idle RSS | < 500MB |
| Peak RSS (under load) | < 2GB |
| System Memory Usage | < 80% |

### Metrics Collection Overhead

| Operation | Overhead Target |
|-----------|-----------------|
| Intent latency observation | < 0.1ms |
| Cache metrics collection | < 1ms |
| Memory stats collection | < 5ms |
| Profiler (when disabled) | < 0.01ms |

---

## Grafana Dashboard Configuration

Example dashboard JSON snippets for common panels:

### Query Latency Panel

```json
{
  "title": "Query Latency by Intent",
  "type": "graph",
  "targets": [
    {
      "expr": "histogram_quantile(0.95, rate(agentic_rag_search_latency_seconds_bucket[5m]))",
      "legendFormat": "P95 - {{intent_type}}"
    }
  ]
}
```

### Cache Hit Rate Panel

```json
{
  "title": "Cache Hit Rate",
  "type": "stat",
  "targets": [
    {
      "expr": "avg(agentic_rag_cache_hit_rate_percent)",
      "legendFormat": "Hit Rate %"
    }
  ]
}
```

### Memory Usage Panel

```json
{
  "title": "Memory Usage",
  "type": "graph",
  "targets": [
    {
      "expr": "agentic_rag_memory_rss_bytes / 1024 / 1024",
      "legendFormat": "RSS (MB)"
    }
  ]
}
```

---

## Troubleshooting

### Metrics Not Appearing

1. Verify metrics are enabled in configuration
2. Check `/metrics` endpoint returns expected metrics
3. Ensure Prometheus is scraping the correct port
4. Check for duplicate metric registration errors in logs

### High Latency

1. Check intent distribution - complex intents (MULTI_HOP, COMPARISON) take longer
2. Review cache hit rates - low hit rates increase latency
3. Check memory usage - high memory can cause GC pauses
4. Enable profiling to identify bottlenecks

### Memory Growth

1. Check cache size limits
2. Review connection pool sizes
3. Look for memory leaks using `Profiler` context manager
4. Check for large result sets being cached

---

## Related Documentation

- Analytics System (see CLAUDE.md section 7) - PostgreSQL-based event logging
- [Alerts Configuration](./alerts.md) - Alerting rules
- [CONVENTIONS.md](../../../.spec_system/CONVENTIONS.md) - Project guidelines
