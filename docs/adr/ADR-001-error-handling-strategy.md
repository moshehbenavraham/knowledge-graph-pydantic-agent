# ADR-001: Error Handling Strategy

**Status**: Accepted
**Date**: 2025-12-30
**Phase**: 03 - Production Readiness & User Experience
**Session**: 01 - Error Handling and Resilience

---

## Context

The Agentic GraphRAG System depends on multiple external services (Neo4j, Supabase, LLM APIs, embedding APIs) that can fail independently. Without structured error handling, failures cascade unpredictably, users receive unhelpful error messages, and operators lack the context needed to diagnose issues.

Prior to Phase 03, error handling was ad-hoc: try/except blocks with generic messages, no retry logic, and no distinction between transient vs. permanent failures. This led to poor user experience during temporary outages and difficulty debugging production issues.

## Decision

We implemented a **comprehensive error handling framework** with four pillars:

### 1. Error Classification System

All errors are categorized into four types via `ErrorCategory` enum:
- **TRANSIENT**: Temporary failures that may succeed on retry (timeouts, rate limits)
- **FATAL**: Permanent failures that should not be retried (auth failures, invalid queries)
- **USER_ERROR**: Errors caused by invalid user input (bad query syntax)
- **SYSTEM_ERROR**: Internal failures requiring operator attention

The `categorize_exception()` function automatically classifies exceptions based on message patterns, enabling consistent handling across the codebase.

### 2. Circuit Breaker Pattern

The `CircuitBreaker` class prevents cascading failures:
- After `failure_threshold` (default: 5) consecutive failures, circuit opens
- Open circuit rejects requests immediately, preventing resource exhaustion
- After `recovery_timeout` (default: 60s), circuit enters half-open state for testing
- Successful request in half-open state closes circuit; failure reopens it

Implemented as both a class and `@circuit_breaker` decorator for flexibility.

### 3. Retry Strategy with Exponential Backoff

The `RetryStrategy` class handles transient failures:
- Configurable `max_attempts` (default: 3)
- Exponential backoff with `base_delay` and `max_delay`
- Optional jitter to prevent thundering herd
- Exception type filtering via `retriable_exceptions`

Convenience decorators provided: `@retry`, `@retry_on_network_error`, `@retry_on_database_error`.

### 4. Structured Error Context

The `ErrorContext` Pydantic model captures rich diagnostic information:
- Category and service type
- Operation being performed
- Retry count and retriability
- User-friendly message (separate from internal details)
- Additional context for debugging (not exposed to users)
- Timestamp for correlation

Custom exceptions (`ResilienceError`, `CircuitOpenError`, `MaxRetriesExceededError`, `GracefulDegradationError`) carry this context.

## Consequences

### Positive

- **Improved reliability**: Transient failures now recovered automatically via retry
- **Better user experience**: Users see helpful messages, not stack traces
- **Operator visibility**: Structured logging enables effective debugging
- **Cascading failure prevention**: Circuit breakers protect system during outages
- **Consistent handling**: All services use same patterns

### Negative

- **Additional complexity**: Decorators and context objects add cognitive overhead
- **Configuration requirements**: Circuit breaker and retry parameters need tuning
- **Potential latency**: Retries add time to ultimately-failing operations

### Trade-offs

We chose explicit error categorization over automatic retry-everything because:
1. Fatal errors should fail fast, not waste time retrying
2. User errors need different messaging than system errors
3. Operators need category-based alerting

## Implementation

**Key Files**:
- `src/agentic_rag/resilience/error_types.py` - Error categories, context model, custom exceptions
- `src/utils/resilience.py` - CircuitBreaker class, RetryStrategy class, decorators
- `src/ui/components/error_display.py` - User-facing error rendering

**Usage Example**:
```python
from src.utils.resilience import circuit_breaker, retry

@circuit_breaker(name="neo4j", failure_threshold=3)
@retry(max_attempts=2, base_delay=0.5)
async def query_knowledge_graph(query: str) -> list[dict]:
    # Implementation
    pass
```

## Related Decisions

- ADR-002: Performance Monitoring captures error metrics
- ADR-003: UI Component Library renders user-friendly errors

---

**Last Updated**: 2025-12-30
