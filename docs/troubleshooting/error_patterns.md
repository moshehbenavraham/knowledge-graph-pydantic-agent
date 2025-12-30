# Error Patterns Troubleshooting Guide

Phase 03 error handling patterns and solutions for the Agentic GraphRAG System.

---

## Table of Contents

- [Error Classification System](#error-classification-system)
- [Circuit Breaker Patterns](#circuit-breaker-patterns)
- [Retry Strategy Patterns](#retry-strategy-patterns)
- [Common Error Patterns](#common-error-patterns)
- [UI Error Display](#ui-error-display)
- [Debugging Errors](#debugging-errors)

---

## Error Classification System

Phase 03 introduced structured error handling with automatic classification.

### Error Categories

| Category | Description | Action |
|----------|-------------|--------|
| `TRANSIENT` | Temporary failures | Automatic retry |
| `FATAL` | Permanent failures | Fail fast |
| `USER_ERROR` | Invalid user input | User feedback |
| `SYSTEM_ERROR` | Internal failures | Operator alert |

### Using Error Classification

```python
from src.agentic_rag.resilience import ErrorCategory, categorize_exception

try:
    result = await database_query()
except Exception as e:
    category = categorize_exception(e)

    if category == ErrorCategory.TRANSIENT:
        # Safe to retry
        result = await retry_operation()
    elif category == ErrorCategory.USER_ERROR:
        # Return user-friendly message
        return {"error": "Invalid query syntax"}
    else:
        # Log and escalate
        logger.error("Fatal error", error=str(e))
        raise
```

### Error Category Patterns

**TRANSIENT** patterns:
- "timeout"
- "connection refused"
- "rate limit"
- "temporary"
- "try again"

**FATAL** patterns:
- "authentication failed"
- "unauthorized"
- "invalid credentials"
- "not found" (for resources that should exist)

**USER_ERROR** patterns:
- "invalid"
- "syntax error"
- "malformed"
- "missing required"

---

## Circuit Breaker Patterns

Circuit breakers prevent cascading failures when services are unhealthy.

### States

```
CLOSED (healthy) -> OPEN (broken) -> HALF_OPEN (testing)
```

- **CLOSED**: Requests pass through normally
- **OPEN**: Requests rejected immediately (service is down)
- **HALF_OPEN**: Limited requests allowed to test recovery

### Configuration

Default settings:
- `failure_threshold`: 5 consecutive failures
- `recovery_timeout`: 60 seconds

### Using Circuit Breakers

```python
from src.utils.resilience import circuit_breaker

@circuit_breaker(name="neo4j", failure_threshold=3, recovery_timeout=30)
async def query_graph(query: str) -> list:
    return await neo4j_client.run(query)
```

### Circuit Breaker Errors

**Error**: `CircuitOpenError: Circuit breaker 'neo4j' is OPEN`

**Meaning**: Service has failed too many times, circuit is protecting system.

**Solution**:
1. Check the underlying service health
2. Wait for recovery timeout
3. Or manually reset:
   ```python
   from src.utils.resilience import get_circuit_breaker
   cb = get_circuit_breaker("neo4j")
   cb.reset()
   ```

### Monitoring Circuit State

```python
from src.utils.resilience import get_circuit_breaker

cb = get_circuit_breaker("neo4j")
print(f"State: {cb.state}")
print(f"Failures: {cb.failure_count}")
print(f"Last failure: {cb.last_failure_time}")
```

---

## Retry Strategy Patterns

Retry strategies handle transient failures with exponential backoff.

### Configuration

```python
from src.utils.resilience import RetryStrategy

strategy = RetryStrategy(
    max_attempts=3,
    base_delay=0.5,    # Start with 500ms
    max_delay=10.0,    # Cap at 10 seconds
    exponential=True,
    jitter=True,       # Prevent thundering herd
)
```

### Using Retry Decorators

```python
from src.utils.resilience import retry, retry_on_network_error

# General retry
@retry(max_attempts=3, base_delay=1.0)
async def fetch_data():
    return await api_call()

# Network-specific retry
@retry_on_network_error
async def external_api_call():
    return await httpx.get(url)
```

### Retry Errors

**Error**: `MaxRetriesExceededError: Max retries (3) exceeded`

**Meaning**: Operation failed all retry attempts.

**Solution**:
1. Check if error is actually transient
2. Consider increasing max_attempts
3. Implement fallback behavior:
   ```python
   from src.utils.resilience import retry

   @retry(max_attempts=3, fallback=lambda: {"default": True})
   async def operation_with_fallback():
       return await risky_operation()
   ```

---

## Common Error Patterns

### Database Connection Errors

**Pattern**: `PostgreSQL pool not initialized`

**Cause**: ConnectionManager not initialized before use.

**Solution**:
```python
# Use the singleton
from src.agentic_rag.storage import get_connection_manager

conn = await get_connection_manager()
await conn.initialize()
```

### Neo4j Authentication Errors

**Pattern**: `Neo.ClientError.Security.Unauthorized`

**Cause**: Invalid credentials or paused instance.

**Solution**:
1. Check Neo4j Aura console for instance status
2. Resume if paused
3. Reset password if needed
4. Verify `.env` has correct `NEO4J_USER=neo4j` (not "Aura")

### Embedding Dimension Mismatch

**Pattern**: `vector dimension mismatch`

**Cause**: Query embedding dimensions don't match stored embeddings.

**Solution**:
```sql
-- Check current dimensions
SELECT array_length(embedding, 1) FROM documents LIMIT 1;

-- Update if needed (1536 for OpenAI, 768 for Ollama)
ALTER TABLE documents ALTER COLUMN embedding TYPE vector(1536);
```

### Rate Limit Errors

**Pattern**: `Rate limit exceeded` or `429 Too Many Requests`

**Cause**: Too many API calls to external service.

**Solution**:
1. Wait for rate limit reset
2. Implement backoff:
   ```python
   @retry_on_rate_limit
   async def api_call():
       return await external_api()
   ```
3. Upgrade API tier

### Memory Errors

**Pattern**: `MemoryError` or OOM during embedding generation

**Cause**: Processing too many documents at once.

**Solution**:
```bash
# Reduce batch sizes in .env
EMBEDDING_BATCH_SIZE=5
INGESTION_BATCH_SIZE=3
MAX_CONCURRENT_EMBEDDINGS=2
```

---

## UI Error Display

Phase 03 introduced consistent error display components.

### Error Severity Levels

| Level | Display | Use Case |
|-------|---------|----------|
| INFO | Blue | Informational messages |
| WARNING | Yellow | Non-critical issues |
| ERROR | Red | Operation failures |
| CRITICAL | Dark red | System failures |

### Using Error Components

```python
from src.ui.components import render_error_display, ErrorSeverity

# Display user-friendly error
render_error_display(
    title="Search Failed",
    message="Unable to connect to search service.",
    severity=ErrorSeverity.ERROR,
    suggestions=[
        "Check your internet connection",
        "Try again in a few moments",
        "Contact support if issue persists"
    ],
)
```

### Error Message Guidelines

**Good error messages**:
- Clear, non-technical language
- Actionable suggestions
- No stack traces for users

**Example**:
```python
# Good
render_error_display(
    title="Connection Error",
    message="We couldn't connect to the database.",
    suggestions=["Check your network connection", "Try again later"],
)

# Bad
render_error_display(
    title="Error",
    message="asyncpg.exceptions.ConnectionDoesNotExistError",
)
```

---

## Debugging Errors

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG
PROFILING_ENABLED=true

# Run with debug output
LOG_LEVEL=DEBUG make run-ui
```

### Filter Logs by Component

```bash
# Circuit breaker events
make run-ui | grep "circuit_breaker"

# Retry attempts
make run-ui | grep "retry"

# Error categories
make run-ui | grep "ErrorCategory"
```

### Inspect Error Context

```python
from src.agentic_rag.resilience import ErrorContext

try:
    result = await operation()
except ResilienceError as e:
    ctx = e.context
    print(f"Category: {ctx.category}")
    print(f"Service: {ctx.service}")
    print(f"Retry count: {ctx.retry_count}")
    print(f"Retriable: {ctx.retriable}")
    print(f"User message: {ctx.user_message}")
```

### Common Debug Patterns

**1. Check circuit breaker state**:
```python
from src.utils.resilience import list_circuit_breakers

for name, cb in list_circuit_breakers().items():
    print(f"{name}: {cb.state} (failures: {cb.failure_count})")
```

**2. Test connectivity**:
```bash
# PostgreSQL
python test_db_connection.py

# Neo4j
python scripts/test_neo4j_connection.py

# All services
bash scripts/debug/check_connections.sh
```

**3. Analyze error frequency**:
```sql
-- Query analytics for error patterns
SELECT
    error_type,
    COUNT(*) as count,
    MAX(created_at) as last_occurrence
FROM search_analytics
WHERE success = false
GROUP BY error_type
ORDER BY count DESC;
```

---

## Error Recovery Strategies

### Graceful Degradation

When services are unavailable, provide reduced functionality:

```python
from src.utils.resilience import GracefulDegradationError

async def search_with_fallback(query: str):
    try:
        # Try hybrid search (vector + graph)
        return await hybrid_search(query)
    except CircuitOpenError:
        logger.warning("Graph unavailable, falling back to vector-only")
        # Fall back to vector-only search
        return await vector_search(query)
```

### Timeout Handling

```python
import asyncio
from src.utils.resilience import retry

@retry(max_attempts=2)
async def operation_with_timeout():
    try:
        return await asyncio.wait_for(
            slow_operation(),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        raise TransientError("Operation timed out")
```

### Bulk Operation Recovery

For batch operations, track progress for recovery:

```python
async def batch_ingest(documents: list) -> dict:
    results = {"success": [], "failed": []}

    for doc in documents:
        try:
            result = await ingest_document(doc)
            results["success"].append(doc.id)
        except Exception as e:
            results["failed"].append({"id": doc.id, "error": str(e)})

    return results
```

---

## Related Documentation

- [Main Troubleshooting Guide](../10-troubleshooting/index.md)
- [ADR-001: Error Handling Strategy](../adr/ADR-001-error-handling-strategy.md)
- [Debug Scripts](../../scripts/debug/)

---

**Last Updated**: 2025-12-30
