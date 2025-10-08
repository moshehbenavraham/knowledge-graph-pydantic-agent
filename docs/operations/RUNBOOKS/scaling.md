# Scaling Runbook

## Overview

This runbook covers horizontal and vertical scaling procedures for the Base Agent / Agentic RAG platform.

## Scaling Triggers

### When to Scale

**Scale UP when**:
- CPU usage > 70% for 15+ minutes
- Memory usage > 75% for 15+ minutes
- Request queue depth > 100
- Response time p95 > 3 seconds
- Database connection pool > 80% utilized
- Anticipated traffic increase (marketing campaign, product launch)

**Scale DOWN when**:
- CPU usage < 30% for 2+ hours
- Memory usage < 40% for 2+ hours
- Cost optimization needed
- Post-event traffic normalization

## Horizontal Scaling (Preferred)

### API Service Scaling

**Scale API containers**:

```bash
# Check current scale
docker-compose -f docker/docker-compose.prod.yml ps api

# Scale to 3 replicas
docker-compose -f docker/docker-compose.prod.yml up -d --scale api=3

# Verify scaling
docker-compose -f docker/docker-compose.prod.yml ps api

# Monitor distribution
watch -n 5 'docker stats --no-stream | grep api'
```

**Update configuration** (for persistent scaling):

```yaml
# In docker/docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 3  # Increase from 2 to 3
```

Then redeploy:
```bash
make deploy-prod
```

### Load Balancer Configuration

If using external load balancer (e.g., Nginx, Traefik):

```nginx
# /etc/nginx/conf.d/base-agent.conf
upstream api_backend {
    least_conn;  # Use least connection algorithm
    server api-1:8058 max_fails=3 fail_timeout=30s;
    server api-2:8058 max_fails=3 fail_timeout=30s;
    server api-3:8058 max_fails=3 fail_timeout=30s;
}
```

Reload Nginx:
```bash
nginx -t && nginx -s reload
```

## Vertical Scaling

### Increase Container Resources

**Update resource limits**:

```yaml
# docker/docker-compose.prod.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4'      # Increase from 2
          memory: 8G     # Increase from 4G
        reservations:
          cpus: '2'
          memory: 4G
```

**Apply changes**:
```bash
docker-compose -f docker/docker-compose.prod.yml up -d --force-recreate api

# Verify new limits
docker inspect base-agent-api-prod | grep -A 10 "Memory\|NanoCpus"
```

## Database Scaling

### Neo4j Scaling

**Increase memory allocation**:

```yaml
# docker/docker-compose.prod.yml
neo4j:
  environment:
    - NEO4J_dbms_memory_pagecache_size=8G     # Increase from 4G
    - NEO4J_dbms.memory.heap.initial_size=8G  # Increase from 4G
    - NEO4J_dbms_memory_heap_max__size=16G    # Increase from 8G
```

**For read-heavy workloads**, consider Neo4j read replicas (Enterprise Edition):

```cypher
// On primary instance
CALL dbms.cluster.overview()
```

### Supabase/PostgreSQL Scaling

**Connection pooling**:

```python
# Increase connection pool size in src/config/settings.py
class Settings(BaseSettings):
    database_pool_size: int = 20  # Increase from 10
    database_max_overflow: int = 40  # Increase from 20
```

**Supabase Dashboard**:
1. Navigate to Settings > Database
2. Upgrade to larger instance size if needed
3. Enable read replicas for read-heavy workloads

## Redis Scaling

**Increase memory limit**:

```yaml
# docker/docker-compose.prod.yml
redis:
  command: >
    redis-server
    --appendonly yes
    --maxmemory 8gb         # Increase from 4gb
    --maxmemory-policy allkeys-lru
```

**Redis Cluster** (for very high scale):

```bash
# Deploy Redis cluster with 6 nodes (3 masters, 3 replicas)
docker-compose -f docker/docker-compose.redis-cluster.yml up -d
```

## Auto-Scaling (Future Enhancement)

### Docker Swarm Auto-Scaling

```yaml
# docker-compose.prod.yml (Swarm mode)
services:
  api:
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
      # Auto-scaling with custom script
      labels:
        - "autoscale.enabled=true"
        - "autoscale.min=2"
        - "autoscale.max=10"
        - "autoscale.target_cpu=70"
```

### Kubernetes Auto-Scaling (Migration Target)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: base-agent-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: base-agent-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 75
```

## Scaling Checklist

### Pre-Scaling

- [ ] Review current metrics (CPU, memory, latency, error rate)
- [ ] Identify bottleneck (app tier, database, cache, LLM)
- [ ] Estimate required capacity
- [ ] Check budget approval for cost increase
- [ ] Notify team in #platform-ops channel
- [ ] Create change request ticket

### During Scaling

- [ ] Execute scaling commands
- [ ] Monitor deployment progress
- [ ] Run health checks
- [ ] Verify load distribution
- [ ] Check for any errors in logs
- [ ] Monitor metrics for 15 minutes

### Post-Scaling

- [ ] Confirm performance improvement
- [ ] Update capacity planning docs
- [ ] Document cost impact
- [ ] Schedule scale-down if temporary
- [ ] Update runbook with learnings

## Scaling Scenarios

### Scenario 1: Marketing Campaign (Predictable Spike)

**Expected**: 5x normal traffic for 3 days

**Action**:
```bash
# 1 day before campaign
# Scale API
docker-compose -f docker/docker-compose.prod.yml up -d --scale api=5

# Increase database connections
# Update SUPABASE_POOL_SIZE=50 in .env.production

# Warm up caches
python scripts/cache_warmup.py

# Pre-generate embeddings for campaign content
make ingest --path campaign_content/

# Monitor
# Set up additional Grafana alerts for the campaign period
```

**Post-Campaign**:
```bash
# 1 day after campaign ends
# Scale down
docker-compose -f docker/docker-compose.prod.yml up -d --scale api=2

# Reset database pool
# Revert SUPABASE_POOL_SIZE=20
```

### Scenario 2: Unexpected Traffic Spike

**Detected**: CPU > 90%, latency increasing

**Immediate Action**:
```bash
# Quick horizontal scale
docker-compose -f docker/docker-compose.prod.yml up -d --scale api=4

# Enable rate limiting if not already
# ENABLE_RATE_LIMITING=true

# Monitor and adjust
watch -n 10 'docker stats --no-stream'
```

### Scenario 3: Database Bottleneck

**Detected**: Slow queries, high DB CPU

**Action**:
```bash
# Optimize queries first
# Review slow query log in Supabase

# Add indexes if missing
# Example: CREATE INDEX idx_documents_embedding ON documents USING ivfflat(embedding);

# Scale database (Supabase dashboard)
# Settings > Database > Upgrade Instance

# Enable query caching
# Update ENABLE_QUERY_CACHE=true

# Consider read replicas for read-heavy workloads
```

## Cost Optimization

### Right-Sizing Analysis

**Monthly review**:
```bash
# Generate resource utilization report
python scripts/resource_analysis.py --period 30d

# Review output:
# - Average CPU utilization
# - Average memory utilization
# - Peak usage times
# - Idle capacity
```

**Optimize**:
- Scale down during off-peak hours (night/weekend)
- Right-size container limits based on actual usage
- Consolidate under-utilized services

### Cost Monitoring

**Track costs**:
- Supabase: Database instance costs
- Cloud provider: Compute/storage costs
- LLM providers: API call costs

**Set budget alerts**:
- Weekly cost threshold: $XXX
- Monthly cost threshold: $XXX
- Alert channel: #finance-ops

## Monitoring During Scaling

### Key Metrics to Watch

```bash
# CPU Usage
docker stats --no-stream | awk '{print $3}'

# Memory Usage
docker stats --no-stream | awk '{print $7}'

# Request Rate
curl http://localhost:8058/metrics | grep http_requests_total

# Latency
curl http://localhost:8058/metrics | grep http_request_duration_seconds

# Error Rate
curl http://localhost:8058/metrics | grep 'status="5'
```

### Grafana Dashboards

- **Dashboard**: "Base Agent - Scaling View"
- **Panels**:
  - Container replica count
  - CPU/Memory per replica
  - Request distribution
  - Database connection pool usage
  - Cache hit rate

## Rollback Procedure

If scaling causes issues:

```bash
# Revert to previous scale
docker-compose -f docker/docker-compose.prod.yml up -d --scale api=2

# Restore previous resource limits
# Restore backup of docker-compose.prod.yml
cp docker/docker-compose.prod.yml.backup docker/docker-compose.prod.yml

# Redeploy
make deploy-prod

# Verify
make health-check-prod
```

## Capacity Planning

### Current Capacity

| Component | Current | Peak Capacity | Headroom |
|-----------|---------|---------------|----------|
| API Replicas | 2 | 10 | 5x |
| Database | Medium | Large | 2x |
| Redis | 4GB | 16GB | 4x |
| Neo4j | 8GB heap | 32GB heap | 4x |

### Growth Projections

- **Q1 2026**: 2x current traffic → Scale API to 4 replicas
- **Q2 2026**: 5x current traffic → Scale API to 8 replicas, upgrade DB
- **Q3 2026**: 10x current traffic → Consider Kubernetes migration

---

**Last Updated**: 2025-10-08
**Owner**: Platform SRE Team
**Review Cadence**: Quarterly
