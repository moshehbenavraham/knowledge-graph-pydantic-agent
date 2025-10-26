# Production Go-Live Checklist

## Overview

This comprehensive checklist ensures all systems, processes, and documentation are ready for production deployment of the Luminari Agent / Agentic RAG platform.

---

## Phase 1: Infrastructure & Environment

### Environment Setup
- [ ] Production environment provisioned
- [ ] Docker hosts configured and hardened
- [ ] Network segmentation implemented
- [ ] Firewall rules configured and tested
- [ ] Load balancer configured (if applicable)
- [ ] SSL/TLS certificates installed and valid
- [ ] DNS records configured
- [ ] CDN configured (if applicable)

### Database Setup
- [ ] Supabase production project created
- [ ] PostgreSQL schema deployed
- [ ] pgvector extension enabled
- [ ] Database indexes created and optimized
- [ ] Connection pooling configured
- [ ] Backup strategy implemented
- [ ] Read replicas configured (if needed)
- [ ] Neo4j production instance deployed
- [ ] Neo4j authentication configured
- [ ] Neo4j backups configured

### Secret Management
- [ ] All secrets externalized (no hardcoded values)
- [ ] Secret store configured (Vault, AWS Secrets Manager, etc.)
- [ ] API keys for LLM providers secured
- [ ] Database credentials secured
- [ ] Redis password configured
- [ ] Grafana admin password secured
- [ ] Secret rotation schedule documented

---

## Phase 2: Application Deployment

### Container Images
- [ ] Production images built and tagged
- [ ] Images scanned for vulnerabilities (Trivy)
- [ ] SBOM generated for all images
- [ ] Images signed with Cosign
- [ ] Images pushed to registry
- [ ] Image provenance metadata attached

### Docker Compose
- [ ] `docker-compose.prod.yml` reviewed and approved
- [ ] Environment variables configured
- [ ] Resource limits set appropriately
- [ ] Health checks configured
- [ ] Restart policies configured
- [ ] Logging drivers configured
- [ ] Network isolation verified

### Deployment Validation
- [ ] Deployment scripts tested in staging
- [ ] Health check script validated
- [ ] Rollback script tested
- [ ] Blue-green deployment strategy defined (if applicable)
- [ ] Deployment automation working
- [ ] Post-deployment validation automated

---

## Phase 3: Security

### Container Security
- [ ] Containers run as non-root users
- [ ] Read-only root filesystem enabled
- [ ] Security options configured (no-new-privileges)
- [ ] Capabilities dropped (cap_drop: ALL)
- [ ] AppArmor/SELinux profiles applied

### Network Security
- [ ] TLS enabled for all external endpoints
- [ ] mTLS configured between services (optional)
- [ ] Network policies enforced
- [ ] Inter-container communication restricted
- [ ] Rate limiting enabled
- [ ] DDoS protection configured

### Access Control
- [ ] SSH key-based authentication only
- [ ] Bastion host configured (if needed)
- [ ] Service accounts created with least privilege
- [ ] Database access restricted to application only
- [ ] Admin access logged and monitored

### Vulnerability Management
- [ ] Automated vulnerability scanning in place
- [ ] CVE exception process documented
- [ ] Patch management process defined
- [ ] Security update schedule established

### Compliance
- [ ] Audit logging enabled
- [ ] Log retention policy configured (1 year minimum)
- [ ] Data encryption at rest verified
- [ ] Data encryption in transit verified
- [ ] Privacy policy published (if applicable)
- [ ] GDPR compliance verified (if applicable)

---

## Phase 4: Observability & Monitoring

### Metrics & Monitoring
- [ ] Prometheus deployed and configured
- [ ] Grafana deployed and configured
- [ ] Dashboards created and tested
- [ ] Metrics exporter configured
- [ ] Service discovery configured
- [ ] Retention policies set

### Alerting
- [ ] Alert rules defined and tested
- [ ] PagerDuty integration configured
- [ ] Slack integration configured
- [ ] Alert routing rules configured
- [ ] Escalation policies defined
- [ ] Alert thresholds tuned

### Logging
- [ ] Centralized logging configured (Loki, ELK, etc.)
- [ ] Log aggregation working
- [ ] Structured logging enabled
- [ ] Log retention policy configured
- [ ] Log search working
- [ ] Correlation IDs implemented

### Tracing
- [ ] OpenTelemetry instrumentation added
- [ ] Trace exporter configured
- [ ] Distributed tracing working end-to-end
- [ ] Trace sampling configured
- [ ] Trace retention policy set

---

## Phase 5: Performance & Reliability

### Performance Testing
- [ ] Load testing completed
- [ ] Stress testing completed
- [ ] Baseline metrics established
- [ ] Performance benchmarks documented
- [ ] Bottlenecks identified and addressed
- [ ] Caching strategy implemented
- [ ] Query optimization completed

### Reliability Testing
- [ ] Health checks validated
- [ ] Circuit breakers implemented (if applicable)
- [ ] Retry logic tested
- [ ] Timeout configurations verified
- [ ] Graceful shutdown tested
- [ ] Connection pool tuning completed

### Capacity Planning
- [ ] Current capacity documented
- [ ] Growth projections estimated
- [ ] Scaling strategy defined
- [ ] Resource limits set with headroom
- [ ] Auto-scaling configured (if applicable)

---

## Phase 6: Operations & Runbooks

### Documentation
- [ ] Architecture documentation complete
- [ ] API documentation published
- [ ] Configuration documentation updated
- [ ] Deployment documentation validated
- [ ] Troubleshooting guide created

### Runbooks
- [ ] Incident response runbook created and tested
- [ ] Scaling runbook created
- [ ] Deployment runbook validated
- [ ] Rollback procedure documented and tested
- [ ] Database failover runbook created
- [ ] Disaster recovery plan documented

### Training
- [ ] Operations team trained on deployment
- [ ] On-call rotation established
- [ ] Runbooks reviewed with team
- [ ] Escalation paths documented
- [ ] War room procedures established

---

## Phase 7: Disaster Recovery & Business Continuity

### Backup & Recovery
- [ ] Database backup strategy implemented
- [ ] Backup testing completed
- [ ] Recovery time objective (RTO) defined
- [ ] Recovery point objective (RPO) defined
- [ ] Backup retention policy configured
- [ ] Disaster recovery plan tested

### High Availability
- [ ] Database replication configured (if required)
- [ ] Service redundancy implemented
- [ ] Failover procedures documented
- [ ] Health monitoring configured
- [ ] Automatic failover tested (if applicable)

---

## Phase 8: Go-Live Preparation

### Pre-Launch
- [ ] Staging environment mirrors production
- [ ] End-to-end testing in staging passed
- [ ] Performance testing in staging passed
- [ ] Security scanning passed
- [ ] Penetration testing completed (if required)
- [ ] User acceptance testing completed

### Communication
- [ ] Stakeholders notified of go-live date
- [ ] Maintenance window scheduled
- [ ] Status page configured
- [ ] Communication plan documented
- [ ] Rollback decision criteria defined

### Final Checks
- [ ] All checklist items above completed
- [ ] Production deployment plan reviewed
- [ ] Rollback plan reviewed and validated
- [ ] On-call team available during launch
- [ ] Monitoring dashboards ready
- [ ] Incident response team on standby

---

## Phase 9: Go-Live Execution

### Deployment
- [ ] **T-1 hour**: Final staging validation
- [ ] **T-30 min**: Pre-deployment backup taken
- [ ] **T-15 min**: Announce deployment starting
- [ ] **T-0**: Execute deployment
  ```bash
  make deploy-prod
  ```
- [ ] **T+5 min**: Health checks passing
  ```bash
  make health-check-prod
  ```
- [ ] **T+10 min**: Functional testing passed
- [ ] **T+15 min**: Monitoring dashboards green
- [ ] **T+30 min**: User acceptance validated
- [ ] **T+1 hour**: Announce successful deployment

### Smoke Tests
- [ ] UI accessible and responsive
- [ ] API health endpoint responding
- [ ] Authentication working
- [ ] RAG search working
- [ ] Document retrieval working
- [ ] LLM integration working
- [ ] Database connectivity verified
- [ ] Cache working

---

## Phase 10: Post-Launch

### Monitoring
- [ ] Monitor metrics for 24 hours
- [ ] Review error logs for anomalies
- [ ] Verify alerts are working
- [ ] Check performance against baselines
- [ ] Monitor costs

### Documentation
- [ ] Update deployment date in docs
- [ ] Document any issues encountered
- [ ] Update runbooks based on learnings
- [ ] Capture lessons learned

### Validation
- [ ] All services healthy for 48 hours
- [ ] Error rates within acceptable thresholds
- [ ] Performance metrics meeting SLAs
- [ ] No critical alerts
- [ ] User feedback positive

### Handoff
- [ ] Production access documented
- [ ] On-call schedule published
- [ ] Support escalation paths confirmed
- [ ] Post-launch review scheduled

---

## Rollback Criteria

**Initiate rollback if**:
- [ ] Error rate > 5% for 10 minutes
- [ ] Critical service unavailable for > 5 minutes
- [ ] Data integrity issue detected
- [ ] Security breach detected
- [ ] Performance degradation > 50%
- [ ] Database connectivity lost

**Rollback Procedure**:
```bash
# Execute rollback
make rollback-prod

# Verify health
make health-check-prod

# Communicate status
# Post in #incidents channel
```

---

## Sign-Off

### Approvals

| Role | Name | Signature | Date |
|------|------|-----------|------|
| **Engineering Lead** | | | |
| **Platform Manager** | | | |
| **Security Lead** | | | |
| **Product Owner** | | | |
| **CTO** (for P0 launches) | | | |

### Declaration

**By signing below, I confirm**:
- All checklist items have been completed
- Production environment is ready for launch
- Rollback procedures are tested and documented
- On-call team is prepared to respond
- Risk mitigation strategies are in place

**Deployment Authorized**: _________________ (Signature)

**Date**: _________________

---

## Post-Launch Review

**Schedule**: Within 48 hours of go-live

**Agenda**:
1. Deployment timeline review
2. Issues encountered and resolutions
3. Performance against baselines
4. Process improvements identified
5. Action items with owners

**Document**: `docs/operations/POST_LAUNCH_REVIEWS/YYYY-MM-DD-production-launch.md`

---

**Last Updated**: 2025-10-08
**Owner**: Platform Team
**Version**: 1.0
