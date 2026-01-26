# Incident Response Runbook

## Purpose

This runbook provides step-by-step procedures for responding to incidents in the Knowledge Graph Pydantic Agent / Agentic RAG platform.

## Incident Severity Levels

| Level | Definition | Response Time | Examples |
|-------|------------|---------------|----------|
| **P0 - Critical** | Complete service outage affecting all users | Immediate | Service down, data loss |
| **P1 - High** | Major degradation affecting many users | < 30 minutes | High error rates, severe latency |
| **P2 - Medium** | Partial degradation affecting some users | < 2 hours | Single component failure, moderate latency |
| **P3 - Low** | Minor issues with workarounds | < 24 hours | UI glitches, non-critical warnings |

## Incident Response Process

### 1. Detection & Alert

**Automated Detection**:
- PagerDuty alert for P0/P1
- Slack notification for P2/P3
- Monitoring dashboard shows anomaly

**Manual Detection**:
- User report
- Team member observation

### 2. Initial Response (0-5 minutes)

```bash
# Acknowledge the incident
# In PagerDuty or Slack

# Quick health check
make health-check-prod

# Check service status
docker-compose -f docker/docker-compose.prod.yml ps

# View recent logs
make logs-all | tail -100
```

**Actions**:
1. ✅ Acknowledge alert within 5 minutes
2. ✅ Post initial status update in `#incidents` Slack channel
3. ✅ Assess severity level
4. ✅ Engage additional responders if P0/P1

### 3. Investigation (5-15 minutes)

**Gather Information**:

```bash
# Check application logs
make logs-app
make logs-api

# Check container health
docker ps -a
docker stats

# Check metrics
# Open Grafana: http://grafana.example.com
# Dashboard: "KGPA - Agentic RAG Platform"

# Check recent deployments
cat deploy/backups/production/current-deployment.txt

# Check database connectivity
# Supabase Dashboard: https://supabase.com/dashboard
# Neo4j Browser: http://localhost:7474
```

**Common Investigation Queries**:

```bash
# Search for errors in last 10 minutes
docker logs kgpa-api-prod 2>&1 | grep -i error | tail -50

# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8058/health

# Check database connections
# In Neo4j Browser:
# CALL dbms.listConnections()
```

**Identify Root Cause**:
- [ ] Recent deployment correlation
- [ ] Infrastructure issue (CPU, memory, disk)
- [ ] Database connectivity problem
- [ ] External service degradation (LLM provider, Supabase)
- [ ] Traffic spike
- [ ] Application bug

### 4. Mitigation (15-30 minutes)

#### Option A: Rollback Recent Deployment

```bash
# If incident correlates with recent deployment
make rollback-prod

# Wait for services to stabilize
sleep 60

# Verify health
make health-check-prod
```

#### Option B: Scale Resources

```bash
# Horizontal scaling
docker-compose -f docker/docker-compose.prod.yml up -d --scale api=3

# Check resource allocation
docker stats
```

#### Option C: Restart Affected Service

```bash
# Restart specific service
docker-compose -f docker/docker-compose.prod.yml restart app

# OR restart API only
docker-compose -f docker/docker-compose.prod.yml restart api
```

#### Option D: Traffic Management

```bash
# Enable rate limiting (if not already enabled)
# Update ENABLE_RATE_LIMITING=true in .env.production

# Restart with updated config
make deploy-prod
```

### 5. Verification (30-45 minutes)

**Verify Resolution**:

```bash
# Run health checks
make health-check-prod

# Check error rates in Grafana
# Metric: http_requests_total{status=~"5.."}

# Verify user-facing functionality
# Test critical flows:
# - Chat query
# - RAG search
# - Document retrieval

# Monitor for 15 minutes
watch -n 10 'make health-check-prod'
```

**Success Criteria**:
- [ ] All health checks passing
- [ ] Error rate < 1%
- [ ] Latency p95 < 2 seconds
- [ ] No new alerts firing
- [ ] User reports resolved

### 6. Communication

**During Incident**:

```
🚨 INCIDENT ALERT - P{severity}

**Status**: Investigating / Mitigating / Resolved
**Impact**: {description of user impact}
**Affected**: {which services/features}
**ETA**: {estimated time to resolution}
**Updates**: Every 15 minutes

Latest: {brief status update}
```

**Resolution Message**:

```
✅ INCIDENT RESOLVED - P{severity}

**Duration**: {start time} - {end time}
**Root Cause**: {brief explanation}
**Resolution**: {what was done}
**Follow-up**: Post-incident review scheduled for {date/time}

Users should now be experiencing normal service.
```

### 7. Post-Incident Review

**Schedule PIR**:
- P0/P1: Within 24 hours
- P2: Within 1 week
- P3: Optional

**PIR Agenda**:
1. Timeline of events
2. Root cause analysis (5 Whys)
3. What went well
4. What could be improved
5. Action items with owners

**Document in**: `docs/operations/POST_MORTEMS/YYYY-MM-DD-{incident-name}.md`

## Common Incident Scenarios

### Scenario 1: Service Completely Down

**Symptoms**:
- All health checks failing
- No response from UI/API
- "Service unavailable" errors

**Response**:
```bash
# Check if containers are running
docker ps -a | grep kgpa

# If stopped, check why
docker logs kgpa-prod --tail 100

# Restart services
make deploy-prod

# If that fails, rollback
make rollback-prod
```

**Root Causes**:
- OOM kill due to memory leak
- Database connection failure
- Bad deployment
- Infrastructure failure

### Scenario 2: High Error Rate (>5%)

**Symptoms**:
- PagerDuty alert: "HighErrorRate"
- 5xx errors in logs
- User reports of failures

**Response**:
```bash
# Identify error pattern
make logs-api | grep "HTTP/1.1\" 5" | tail -50

# Check database connectivity
# Supabase: Check dashboard
# Neo4j: cypher-shell -u neo4j -p <password>

# Check LLM provider status
# OpenAI: https://status.openai.com
# Anthropic: https://status.anthropic.com

# If database issue, restart connections
docker-compose -f docker/docker-compose.prod.yml restart app

# If LLM provider issue, switch provider or wait
```

**Root Causes**:
- Database connection pool exhausted
- LLM provider rate limiting
- Application bug in new code
- Network connectivity issue

### Scenario 3: High Latency (p95 > 5s)

**Symptoms**:
- PagerDuty alert: "HighLatency"
- Slow response times
- User complaints of sluggishness

**Response**:
```bash
# Check distributed traces in Grafana/Jaeger
# Identify slow span

# Check database query performance
# In Supabase: Performance > Query Performance

# Check LLM response times
make logs-api | grep "llm_duration"

# If database slow:
# - Check for missing indexes
# - Review slow query log
# - Consider read replica

# If LLM slow:
# - Check provider status
# - Consider caching strategy
```

**Root Causes**:
- Slow database queries
- LLM provider degradation
- Large result sets
- Network latency

### Scenario 4: Memory Leak / OOM

**Symptoms**:
- Container restarts
- Memory usage climbing
- OOM killed messages in logs

**Response**:
```bash
# Check memory usage
docker stats

# Identify leaking container
docker stats --no-stream | sort -k 7 -h

# Temporary fix: restart container
docker-compose -f docker/docker-compose.prod.yml restart {service}

# Long-term: profile application
# Add memory profiling
# Review code for leaks
```

**Root Causes**:
- Application memory leak
- Large in-memory caches
- Unbounded data structures
- Connection leaks

## Escalation Matrix

| Role | Escalate When | Contact |
|------|---------------|---------|
| **On-Call Engineer** | Initial responder | PagerDuty |
| **Engineering Lead** | P0/P1 after 15 min | Slack: @eng-lead |
| **Platform Manager** | P0 after 30 min | Phone: +1-xxx-xxx-xxxx |
| **CTO** | P0 affecting revenue > 1 hour | Phone: +1-xxx-xxx-xxxx |
| **Database Team** | Database-specific issues | Slack: #database-team |
| **Security Team** | Security incident suspected | Slack: #security-alerts |

## Tools & Access

- **Grafana**: http://grafana.example.com (SSO)
- **Prometheus**: http://prometheus.example.com (internal)
- **PagerDuty**: https://example.pagerduty.com
- **Slack**: #incidents, #kgpa-alerts
- **Deployment Access**: SSH key required, stored in 1Password
- **Database Access**: Supabase dashboard, Neo4j Browser
- **Runbook Repository**: `docs/operations/RUNBOOKS/`

## Incident Command Roles

For P0/P1 incidents, assign these roles:

- **Incident Commander**: Coordinates response, makes decisions
- **Tech Lead**: Investigates and implements fixes
- **Communications Lead**: Updates stakeholders
- **Scribe**: Documents timeline and actions

## Prevention Checklist

After incident resolution, review:

- [ ] Can this be detected earlier with better monitoring?
- [ ] Should alert thresholds be adjusted?
- [ ] Are runbooks accurate and helpful?
- [ ] Do we need additional automation?
- [ ] What testing would have caught this?
- [ ] Should we add this scenario to chaos engineering?

## Additional Resources

- [Scaling Runbook](./scaling.md)
- [Alert Documentation](../observability/alerts.md)
- [Architecture Documentation](../../3-architecture/index.md)

<!-- TODO: Add runbooks when created:
- Database Issues Runbook (./database_issues.md)
- Deployment Runbook (./deployment.md)
-->

---

**Last Updated**: 2025-10-08
**Owner**: Platform SRE Team
**Review**: After each P0/P1 incident
