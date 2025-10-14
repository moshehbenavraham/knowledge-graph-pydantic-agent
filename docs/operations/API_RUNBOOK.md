# Agentic RAG API Operations Runbook

**Version**: 1.0.0
**Last Updated**: 2025-01-08
**Owner**: Platform Engineering Team

## Table of Contents

1. [Starting the API](#starting-the-api)
2. [Health Checks](#health-checks)
3. [Common Issues](#common-issues)
4. [Monitoring](#monitoring)
5. [Scaling](#scaling)
6. [Maintenance](#maintenance)
7. [Emergency Procedures](#emergency-procedures)
8. [Performance Tuning](#performance-tuning)

---

## Starting the API

### Development Mode

```bash
# Using Make (recommended)
make run-api

# Or directly with Uvicorn
uvicorn src.api.main:app --reload --port 8058

# With environment file
uvicorn src.api.main:app --reload --port 8058 --env-file .env
```

**Expected Output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8058
```

### Production Mode

```bash
# Using Gunicorn with Uvicorn workers (recommended for production)
gunicorn src.api.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8058 \
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

**Configuration Explanation**:
- `-w 4`: 4 worker processes (adjust based on CPU cores)
- `--timeout 120`: 120 second timeout for requests
- `--max-requests 1000`: Restart workers after 1000 requests (prevents memory leaks)
- `--max-requests-jitter 100`: Randomize restart to prevent thundering herd

### Environment Variables

Required environment variables (see `.env.example`):

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# LLM Provider
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-key
LLM_MODEL=gpt-4o-mini

# API Settings
API_PORT=8058
API_HOST=0.0.0.0
CORS_ORIGINS=["http://localhost:3000"]
ENABLE_TRACING=false
```

---

## Health Checks

### Liveness Probe

Checks if the API is running:

```bash
curl http://localhost:8058/health
```

**Expected Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-01-08T12:00:00Z"
}
```

### Readiness Probe

Checks if the API is ready to accept requests:

```bash
curl http://localhost:8058/api/v1/status
```

**Expected Response** (200 OK):
```json
{
  "status": "operational",
  "version": "0.8.0",
  "components": [
    {"name": "PostgreSQL", "healthy": true},
    {"name": "Neo4j", "healthy": true},
    {"name": "Cache", "healthy": true}
  ]
}
```

### Metrics Endpoint

Prometheus metrics for monitoring:

```bash
curl http://localhost:8058/metrics
```

---

## Common Issues

### Issue 1: API Fails to Start

**Symptoms**:
- API crashes on startup
- Error: "Failed to connect to database"

**Causes**:
- Database connection failure
- Missing environment variables
- Port already in use

**Resolution**:

1. Check database connectivity:
```bash
# Test PostgreSQL
psql $SUPABASE_URL -c "SELECT 1;"

# Test Neo4j
cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1;"
```

2. Verify environment variables:
```bash
# Check .env file exists
ls -la .env

# Verify critical variables are set
env | grep -E "(SUPABASE|NEO4J|LLM)"
```

3. Check port availability:
```bash
# Check if port 8058 is in use
lsof -i :8058

# Or use netstat
netstat -tuln | grep 8058
```

4. Review startup logs:
```bash
# Check application logs
tail -f logs/api.log
```

**Prevention**:
- Use health checks in orchestration (Kubernetes, Docker Compose)
- Implement retry logic for database connections
- Document all required environment variables

---

### Issue 2: 503 Service Unavailable

**Symptoms**:
- All endpoints return 503 errors
- Health check fails

**Causes**:
- Database connection pool exhausted
- Neo4j unavailable
- Worker process crashed

**Resolution**:

1. Check component health:
```bash
curl http://localhost:8058/api/v1/status
```

2. Inspect connection pools:
```bash
# Check PostgreSQL connections
psql $SUPABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Neo4j connections (via metrics)
curl http://localhost:8058/metrics | grep connection
```

3. Restart the API:
```bash
# Graceful restart (if using systemd)
sudo systemctl restart agentic-rag-api

# Or kill and restart
pkill -f "uvicorn src.api.main:app"
make run-api
```

4. Check resource usage:
```bash
# Memory and CPU
top -p $(pgrep -f "uvicorn")

# Disk space
df -h
```

**Prevention**:
- Configure connection pool limits appropriately
- Implement circuit breakers for external dependencies
- Set up alerting for degraded health

---

### Issue 3: Slow Response Times

**Symptoms**:
- P95 latency > 2000ms
- Timeout errors from clients
- High CPU usage

**Causes**:
- Cache miss or cache disabled
- Database query slow
- Connection pool exhausted
- Too few workers

**Resolution**:

1. Check cache health:
```bash
curl http://localhost:8058/api/v1/status | jq '.components[] | select(.name=="Cache")'
```

2. Clear cache if stale:
```bash
curl -X DELETE http://localhost:8058/api/v1/cache
```

3. Review slow queries (PostgreSQL):
```sql
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

4. Increase worker count:
```bash
# Edit gunicorn command to use more workers
gunicorn src.api.main:app -w 8 ...
```

5. Check connection pool size:
```python
# In .env or settings
DATABASE_POOL_SIZE=20  # Increase from default
```

**Prevention**:
- Enable and monitor cache hit rates
- Set up query performance monitoring
- Load test regularly to identify bottlenecks
- Implement request timeouts

---

### Issue 4: High Memory Usage

**Symptoms**:
- Memory usage > 2GB per worker
- OOM (Out of Memory) errors
- Frequent worker restarts

**Causes**:
- Memory leak in application code
- Large document ingestion
- Connection leaks
- Insufficient garbage collection

**Resolution**:

1. Identify memory-heavy processes:
```bash
ps aux --sort=-%mem | head -10
```

2. Restart workers to free memory:
```bash
# Graceful worker restart
kill -HUP $(cat gunicorn.pid)
```

3. Review recent ingestion jobs:
```bash
# Check for large documents
curl http://localhost:8058/api/v1/documents?page_size=10 | jq '.documents[] | {id, title, size}'
```

4. Check for connection leaks:
```bash
# Monitor active connections over time
watch -n 5 'curl -s http://localhost:8058/metrics | grep active_connections'
```

5. Enable memory profiling (development only):
```python
# Add to main.py
import tracemalloc
tracemalloc.start()
```

**Prevention**:
- Set `--max-requests` in Gunicorn to recycle workers
- Implement document size limits
- Use connection context managers (`async with`)
- Monitor memory metrics continuously

---

### Issue 5: Authentication/Authorization Failures

**Symptoms**:
- 401 Unauthorized errors
- 403 Forbidden errors
- Invalid API key messages

**Causes**:
- Expired or invalid API keys
- CORS configuration issues
- Missing authentication headers

**Resolution**:

1. Verify API key configuration:
```bash
# Check environment variable
echo $LLM_API_KEY | head -c 20
```

2. Test CORS configuration:
```bash
# Test preflight request
curl -X OPTIONS http://localhost:8058/api/v1/chat \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"
```

3. Check CORS_ORIGINS setting:
```bash
# Should include your frontend origin
grep CORS_ORIGINS .env
```

4. Validate authentication headers:
```bash
# Test with proper headers
curl -X POST http://localhost:8058/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "test"}'
```

**Prevention**:
- Rotate API keys regularly
- Document CORS requirements for clients
- Implement key validation and logging

---

## Monitoring

### Key Metrics

Monitor these metrics via Prometheus/Grafana:

**Request Metrics**:
- `http_requests_total` - Total request count
- `http_request_duration_seconds` - Request latency (P50, P95, P99)
- `http_requests_in_progress` - Concurrent requests

**Application Metrics**:
- `active_connections{database="postgres"}` - PostgreSQL connections
- `active_connections{database="neo4j"}` - Neo4j connections
- `cache_hits_total` - Cache hit count
- `cache_misses_total` - Cache miss count

**System Metrics**:
- `process_resident_memory_bytes` - Memory usage
- `process_cpu_seconds_total` - CPU usage

### Alert Rules

Recommended Prometheus alert rules:

```yaml
groups:
  - name: agentic_rag_api
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "API error rate above 5%"

      # Slow requests
      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 2
        for: 5m
        annotations:
          summary: "P95 latency above 2 seconds"

      # Connection pool exhaustion
      - alert: ConnectionPoolExhausted
        expr: active_connections / connection_pool_max > 0.8
        for: 5m
        annotations:
          summary: "Connection pool usage above 80%"
```

### Logging

**Log Locations**:
- Application logs: `logs/api.log`
- Access logs: `logs/access.log`
- Error logs: `logs/error.log`

**View Logs**:
```bash
# Tail application logs
tail -f logs/api.log

# Search for errors
grep -i error logs/api.log | tail -20

# Filter by correlation ID
grep "correlation_id=abc123" logs/api.log
```

**Log Levels**:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages (degraded functionality)
- `ERROR`: Error messages (functionality failure)

---

## Scaling

### Horizontal Scaling

Add more API instances:

```bash
# Docker Compose
docker-compose up --scale api=4

# Kubernetes
kubectl scale deployment agentic-rag-api --replicas=4
```

**Load Balancer Configuration**:
```nginx
upstream agentic_rag_api {
    least_conn;
    server api1:8058;
    server api2:8058;
    server api3:8058;
    server api4:8058;
}
```

### Vertical Scaling

Increase worker count and resources:

```bash
# Increase workers (1-2 per CPU core)
gunicorn ... -w 8

# Increase connection pool
export DATABASE_POOL_SIZE=30
export NEO4J_POOL_SIZE=20
```

### Database Scaling

**PostgreSQL**:
- Enable read replicas for vector search
- Increase connection pool: `max_connections=200`
- Tune shared buffers: `shared_buffers=4GB`

**Neo4j**:
- Increase heap size: `-Xmx4G`
- Add read replicas for graph queries
- Enable query caching

---

## Maintenance

### Cache Clearing

```bash
# Clear all cache
curl -X DELETE http://localhost:8058/api/v1/cache

# Pattern-based clearing (future)
curl -X DELETE "http://localhost:8058/api/v1/cache?pattern=search:*"
```

**When to Clear Cache**:
- After major data ingestion
- After configuration changes
- When observing stale results
- As part of deployment process

### Database Maintenance

**PostgreSQL**:

```sql
-- Vacuum and analyze
VACUUM ANALYZE documents;
VACUUM ANALYZE chunks;

-- Reindex for performance
REINDEX TABLE chunks;

-- Update statistics
ANALYZE chunks;
```

**Neo4j**:

```cypher
// Clean up orphaned nodes
MATCH (n)
WHERE NOT EXISTS((n)--())
DELETE n;

// Rebuild indexes
CALL db.index.fulltext.drop('entity_index');
CALL db.index.fulltext.createNodeIndex('entity_index', ['Entity'], ['name']);
```

**Maintenance Windows**:
- Schedule during low-traffic hours (2-4 AM)
- Use rolling restarts for zero downtime
- Monitor connection counts during maintenance

### Backup and Recovery

**Database Backups**:

```bash
# PostgreSQL backup
pg_dump $SUPABASE_URL > backup_$(date +%Y%m%d).sql

# Neo4j backup
neo4j-admin backup --backup-dir=/backups/neo4j

# Automated backups (daily)
0 2 * * * /scripts/backup_databases.sh
```

**Recovery**:

```bash
# Restore PostgreSQL
psql $SUPABASE_URL < backup_20250108.sql

# Restore Neo4j
neo4j-admin restore --from=/backups/neo4j/backup-20250108
```

---

## Emergency Procedures

### Total Outage

**Checklist**:

1. ☐ Check database connectivity
   ```bash
   psql $SUPABASE_URL -c "SELECT 1;"
   cypher-shell -u neo4j "RETURN 1;"
   ```

2. ☐ Check Neo4j status
   ```bash
   systemctl status neo4j
   ```

3. ☐ Review logs for errors
   ```bash
   tail -100 logs/api.log | grep -i error
   ```

4. ☐ Restart service
   ```bash
   systemctl restart agentic-rag-api
   ```

5. ☐ Verify health checks
   ```bash
   curl http://localhost:8058/health
   curl http://localhost:8058/api/v1/status
   ```

6. ☐ Test critical endpoints
   ```bash
   curl -X POST http://localhost:8058/api/v1/search \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "search_type": "vector"}'
   ```

### Partial Outage (Some Endpoints Failing)

1. Identify failing endpoints from metrics:
   ```bash
   curl http://localhost:8058/metrics | grep http_requests_total
   ```

2. Check specific dependency:
   - Chat failures → Check LLM API
   - Search failures → Check PostgreSQL/Neo4j
   - Document operations → Check Supabase

3. Implement degraded mode if possible:
   - Disable graph search, use vector only
   - Serve from cache
   - Return cached responses

4. Monitor and investigate:
   ```bash
   # Watch for pattern of errors
   tail -f logs/api.log | grep "endpoint=/api/v1/chat"
   ```

### Rollback Procedure

If new deployment causes issues:

```bash
# 1. Identify previous working version
git log --oneline -10

# 2. Checkout previous version
git checkout <previous-commit>

# 3. Rebuild and restart
make docker-build
docker-compose up -d

# 4. Verify health
curl http://localhost:8058/health

# 5. Monitor for stability
watch -n 5 'curl -s http://localhost:8058/api/v1/status | jq .status'
```

---

## Performance Tuning

### Database Query Optimization

**PostgreSQL**:

```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1s

-- Create missing indexes
CREATE INDEX CONCURRENTLY idx_chunks_document_id ON chunks(document_id);
CREATE INDEX CONCURRENTLY idx_chunks_embedding_1536 ON chunks USING ivfflat(embedding_1536);

-- Tune configuration
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '64MB';
```

**Neo4j**:

```cypher
// Create indexes
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX episode_timestamp IF NOT EXISTS FOR (ep:Episode) ON (ep.timestamp);

// Tune heap
dbms.memory.heap.max_size=4G
dbms.memory.pagecache.size=2G
```

### Connection Pool Tuning

```python
# In .env or config
DATABASE_POOL_SIZE=20          # PostgreSQL connections
DATABASE_POOL_MAX_OVERFLOW=10  # Extra connections under load
NEO4J_POOL_SIZE=15             # Neo4j connections
CONNECTION_TIMEOUT=30          # Timeout for acquiring connection
```

### Caching Strategy

```python
# Configure cache TTL
CACHE_TTL_SEARCH=300      # 5 minutes for search results
CACHE_TTL_DOCUMENT=3600   # 1 hour for documents
CACHE_TTL_STATUS=60       # 1 minute for status checks
```

### Worker Configuration

```bash
# Calculate optimal workers: (2 * CPU_CORES) + 1
# For 4-core system: (2 * 4) + 1 = 9 workers

gunicorn ... -w 9

# Adjust based on workload:
# - CPU-bound: 1-2 workers per core
# - I/O-bound: 2-4 workers per core
```

---

## Contact Information

**On-Call**:
- Primary: platform-oncall@company.com
- Secondary: engineering@company.com

**Escalation**:
- Severity 1 (Total outage): Page on-call immediately
- Severity 2 (Degraded): Email + Slack alert
- Severity 3 (Minor issue): Create ticket

**Documentation**:
- API Docs: http://localhost:8058/docs
- Architecture: `docs/AGENTIC_RAG.md`
- System Documentation: `docs/ARCHITECTURE.md`

---

**Runbook Version**: 1.0.0
**Last Reviewed**: 2025-01-08
**Next Review**: 2025-02-08
