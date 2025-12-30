# Session Specification

**Session ID**: `phase03-session02-performance_monitoring_and_profiling`
**Phase**: 03 - Production Readiness & User Experience
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session implements production-grade performance monitoring, profiling capabilities, and observability enhancements to identify and address bottlenecks in the Agentic GraphRAG system. Building upon the error handling foundation from Session 01 and the existing analytics infrastructure, this session extends the Prometheus metrics system to provide granular visibility into query performance by intent type.

The system already has foundational monitoring infrastructure including Prometheus metrics for HTTP requests, LLM calls, and basic RAG operations (`src/utils/monitoring.py`, `src/api/telemetry.py`). Additionally, a sophisticated analytics logging system exists for PostgreSQL-based event tracking (`src/agentic_rag/analytics/logger.py`). However, critical observability gaps remain: query latency is not segmented by intent type, cache metrics are tracked internally but not exposed to Prometheus, and memory usage monitoring lacks periodic reporting.

This session closes these gaps by adding intent-specific latency histograms, exposing cache statistics to Prometheus, implementing periodic memory usage logging, and providing development profiling utilities. These enhancements will enable operations teams to identify performance bottlenecks, optimize query routing strategies, and establish baseline benchmarks for regression testing.

---

## 2. Objectives

1. Add Prometheus histogram metrics for search latency segmented by intent type (VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, TEMPORAL, ENTITY_FOCUSED, MULTI_HOP, TEMPORAL_TREND, COMPARISON)
2. Expose cache performance metrics (hit rate, miss rate, eviction count, current size) as Prometheus gauges and counters
3. Implement periodic memory usage logging at INFO level with configurable intervals
4. Create performance profiling decorators for development-time bottleneck identification
5. Document performance baseline benchmarks for regression testing

---

## 3. Prerequisites

### Required Sessions
- [x] `phase03-session01-error_handling_and_resilience` - Error handling foundation with circuit breakers

### Required Tools/Knowledge
- Understanding of Prometheus client library for Python (already in use)
- Familiarity with existing monitoring infrastructure (`src/utils/monitoring.py`)
- Understanding of cache implementation (`src/agentic_rag/cache/query_cache.py`)

### Environment Requirements
- Prometheus client library (prometheus_client) - already installed
- psutil library for memory monitoring - already installed
- Running Prometheus server (optional, for visualization)

---

## 4. Scope

### In Scope (MVP)
- Intent-type specific latency histograms integrated with HybridSearch
- Cache metrics collector that bridges QueryCache stats to Prometheus
- Periodic memory monitoring task with configurable interval
- Profiling decorator for async/sync functions with detailed timing
- Updated /metrics endpoint with all new metrics
- Performance benchmark documentation with baseline measurements

### Out of Scope (Deferred)
- Third-party APM integration (Datadog, New Relic) - *Reason: Requires vendor contracts*
- Distributed tracing across services - *Reason: Single-service architecture currently*
- Real-time alerting system - *Reason: Session 05 deliverable*
- Grafana dashboard configuration - *Reason: Operations team responsibility*

---

## 5. Technical Approach

### Architecture

The implementation follows a layered approach that integrates with existing infrastructure:

1. **Metrics Module** (`src/agentic_rag/metrics/`): New module containing intent-specific metrics, cache metrics collector, and profiling utilities
2. **Integration Points**: HybridSearch observes latency metrics after each query, QueryCache periodically exports stats, background task handles memory monitoring
3. **Configuration**: All settings via centralized `get_settings()` with new performance monitoring options

### Design Patterns
- **Observer Pattern**: Metrics collection observes search operations without coupling
- **Singleton Pattern**: Global metrics registry (existing Prometheus pattern)
- **Decorator Pattern**: Profiling decorators wrap functions non-invasively
- **Background Task Pattern**: Memory monitoring runs as periodic async task

### Technology Stack
- prometheus_client 0.20+ (existing)
- psutil 5.9+ (existing)
- structlog 24.0+ (existing)
- asyncio (Python stdlib)

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/metrics/__init__.py` | Module exports | ~20 |
| `src/agentic_rag/metrics/intent_metrics.py` | Intent-specific latency histograms and counters | ~120 |
| `src/agentic_rag/metrics/cache_metrics.py` | Cache stats collector for Prometheus export | ~100 |
| `src/agentic_rag/metrics/memory_monitor.py` | Periodic memory usage monitoring task | ~80 |
| `src/agentic_rag/metrics/profiler.py` | Development profiling decorators | ~120 |
| `docs/7-operations/observability/performance-metrics.md` | Metrics documentation with baseline benchmarks | ~150 |
| `tests/agentic_rag/metrics/test_intent_metrics.py` | Unit tests for intent metrics | ~100 |
| `tests/agentic_rag/metrics/test_cache_metrics.py` | Unit tests for cache metrics | ~80 |
| `tests/agentic_rag/metrics/test_memory_monitor.py` | Unit tests for memory monitor | ~60 |
| `tests/agentic_rag/metrics/test_profiler.py` | Unit tests for profiler | ~80 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/config/settings.py` | Add performance monitoring configuration fields | ~15 |
| `src/agentic_rag/search/hybrid_search.py` | Integrate intent metrics observation | ~20 |
| `src/agentic_rag/cache/query_cache.py` | Add method to export stats for Prometheus | ~10 |
| `src/api/main.py` | Initialize memory monitor on startup | ~10 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] Query latency histograms available with intent_type label
- [ ] Cache hit/miss/eviction counters visible in /metrics
- [ ] Memory usage logged at INFO level every 60 seconds (configurable)
- [ ] Profiling decorator captures function timing with minimal overhead (<1ms)

### Testing Requirements
- [ ] Unit tests achieve 90%+ coverage for new metrics module
- [ ] Integration test validates metrics appear in /metrics endpoint
- [ ] Manual testing confirms metrics visible in Prometheus (if configured)

### Quality Gates
- [ ] All files ASCII-encoded (0-127 characters only)
- [ ] Unix LF line endings throughout
- [ ] Code follows project conventions (Black, Ruff, MyPy strict)
- [ ] No new Bandit security warnings
- [ ] Metrics collection overhead <5ms per operation

---

## 8. Implementation Notes

### Key Considerations
- Reuse existing `_get_or_create_metric()` helper from `monitoring.py` to avoid Streamlit reload issues
- Coordinate histogram bucket configuration with existing buckets in `monitoring.py` and `telemetry.py`
- Memory monitor must be non-blocking and handle psutil unavailability gracefully

### Potential Challenges
- **Histogram bucket sizing**: Default Prometheus buckets may not suit query latencies. Mitigation: Use custom buckets [0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0] for sub-second to 10s range
- **Streamlit metric re-registration**: Hot reloading causes duplicate metric errors. Mitigation: Use existing `_get_or_create_metric()` pattern
- **Memory monitoring accuracy in async**: psutil calls are synchronous. Mitigation: Run in thread pool executor or accept brief blocking

### Relevant Considerations
- **Analytics batched writes (<5ms overhead)**: New metrics must match this performance target; use Prometheus labels efficiently
- **Centralized configuration**: All new settings (monitor_interval, enable_profiling) must use `get_settings()`
- **Structured logging patterns**: Memory usage logging should use structlog with numeric fields for aggregation

### ASCII Reminder
All output files must use ASCII-only characters (0-127).

---

## 9. Testing Strategy

### Unit Tests
- Test metric registration without duplicates
- Test intent label handling for all 8 intent types
- Test cache stats export matches internal state
- Test profiler captures accurate timing
- Test memory monitor handles psutil unavailability

### Integration Tests
- Test /metrics endpoint returns new metrics
- Test HybridSearch integration observes metrics correctly
- Test memory monitor starts/stops cleanly with API lifecycle

### Manual Testing
- Run queries with different intents and verify metrics increment
- Check Prometheus server (if configured) shows new metrics
- Verify memory usage logs appear at configured interval
- Test profiler decorator on sample async function

### Edge Cases
- Empty cache should return 0 hit rate without errors
- Profiler on already-profiled function should not double-wrap
- Memory monitor should degrade gracefully if psutil import fails
- Metric observation should not block search response

---

## 10. Dependencies

### External Libraries
- prometheus_client: 0.20+ (existing)
- psutil: 5.9+ (existing)
- structlog: 24.0+ (existing)

### Other Sessions
- **Depends on**: `phase03-session01-error_handling_and_resilience` (completed)
- **Depended by**: `phase03-session03-ui_ux_enhancements` (requires monitoring metrics for dashboard)

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
