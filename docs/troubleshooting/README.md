# Troubleshooting Documentation

This directory contains troubleshooting guides for the Agentic GraphRAG System.

---

## Quick Links

| Guide | Description |
|-------|-------------|
| [Error Patterns](error_patterns.md) | Phase 03 error handling patterns and solutions |
| [Main Troubleshooting Guide](../10-troubleshooting/index.md) | Comprehensive troubleshooting reference |

---

## Phase 03 Specific Guides

### Error Handling and Resilience

The system implements structured error handling with automatic classification and recovery:

- **Error Categories**: TRANSIENT, FATAL, USER_ERROR, SYSTEM_ERROR
- **Circuit Breaker**: Prevents cascading failures (5 failures -> 60s recovery)
- **Retry Logic**: Exponential backoff with jitter for transient errors

See [error_patterns.md](error_patterns.md) for common error patterns and solutions.

### Performance Monitoring

Debug performance issues using built-in profiling:

```bash
# Enable profiling
export PROFILING_ENABLED=true
export LOG_LEVEL=DEBUG

# Run with profiling
make run-ui
```

Profiled operations are logged with `duration_ms` metrics.

### UI Component Issues

The UI component library provides consistent error display and loading states.

**Common issues:**
- Loading spinner not showing: Check `LoadingContext` operation type
- Error not user-friendly: Use `render_error_display()` from `src/ui/components`
- Missing intent badge: Verify `ResponseMetadata` is passed correctly

### Graph Visualization

The Graph Explorer dashboard uses pyvis for network rendering.

**Common issues:**
- Graph not loading: Check Neo4j connection status
- Too many nodes: Reduce `max_nodes` filter (default: 100)
- Slow rendering: Increase `min_strength` threshold to filter weak edges

---

## Debug Utilities

Debug scripts are available in `scripts/debug/`:

| Script | Purpose |
|--------|---------|
| `check_connections.sh` | Test all external service connections |
| `analyze_logs.sh` | Parse and analyze application logs |
| `health_check.sh` | Comprehensive system health verification |

Run debug scripts:

```bash
# Check all connections
bash scripts/debug/check_connections.sh

# Analyze recent logs
bash scripts/debug/analyze_logs.sh /path/to/logfile

# Full health check
bash scripts/debug/health_check.sh
```

Or use Makefile targets:

```bash
make debug-connections
make debug-logs
make debug-health
```

---

## Common Diagnostic Commands

### Quick Health Check

```bash
# API health endpoint
curl http://localhost:8058/health

# Detailed health
curl http://localhost:8058/health/detailed

# Component-specific
curl http://localhost:8058/health/components/database
curl http://localhost:8058/health/components/neo4j
```

### Log Analysis

```bash
# Run UI with debug logging
LOG_LEVEL=DEBUG make run-ui

# Filter logs by component
make run-ui | grep "Handler"
make run-ui | grep "ConnectionManager"
make run-ui | grep "circuit_breaker"

# Save logs to file
make run-ui 2>&1 | tee debug.log
```

### Connection Testing

```bash
# Test database connectivity
python scripts/check_database_connectivity.py

# Test Neo4j
python scripts/test_neo4j_connection.py

# Test all services
bash scripts/debug/check_connections.sh
```

---

## Getting Help

1. Check the [main troubleshooting guide](../10-troubleshooting/index.md) for comprehensive solutions
2. Review [error_patterns.md](error_patterns.md) for Phase 03 specific errors
3. Run debug scripts to gather diagnostic information
4. Check CLAUDE.md for development guidance

---

**Last Updated**: 2025-12-30
