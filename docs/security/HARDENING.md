# Docker Host & Container Hardening Guide

## Overview

This document provides security hardening guidelines for the Base Agent / Agentic RAG platform deployment on Docker hosts.

## Container Security

### 1. Non-Root User Execution

**All containers MUST run as non-root users.**

✅ **Implemented in Dockerfile**:
```dockerfile
# Create non-root user
RUN groupadd -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -s /sbin/nologin appuser

# Switch to non-root
USER appuser
```

**Verify**:
```bash
docker inspect base-agent-prod | grep '"User"'
# Should show: "User": "appuser" or "User": "1001"
```

### 2. Read-Only Root Filesystem

**Production containers use read-only root filesystem.**

```yaml
# docker/docker-compose.prod.yml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
```

**Benefits**:
- Prevents runtime modifications
- Limits attack surface
- Enforces immutability

### 3. Security Options

```yaml
services:
  app:
    security_opt:
      - no-new-privileges:true  # Prevents privilege escalation
    cap_drop:
      - ALL  # Drop all capabilities
    cap_add:
      - NET_BIND_SERVICE  # Only add required capabilities
```

### 4. Resource Limits

**Prevent resource exhaustion attacks**:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
      pids: 100  # Limit process count
```

## Docker Host Hardening

### 1. Operating System Hardening

**CIS Benchmark Compliance**:

```bash
# Install CIS Docker Benchmark
git clone https://github.com/docker/docker-bench-security.git
cd docker-bench-security
sudo sh docker-bench-security.sh

# Review and remediate findings
```

**Key OS Security Settings**:

```bash
# Disable unnecessary services
systemctl list-units --state=running

# Enable automatic security updates (Ubuntu)
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Disable IPv6 if not used
echo "net.ipv6.conf.all.disable_ipv6 = 1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 2. Docker Daemon Security

**Daemon configuration** (`/etc/docker/daemon.json`):

```json
{
  "icc": false,
  "userland-proxy": false,
  "no-new-privileges": true,
  "live-restore": true,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
```

### 3. Network Segmentation

**Isolate production networks**:

```yaml
# docker/docker-compose.prod.yml
networks:
  prod-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
    driver_opts:
      com.docker.network.bridge.name: br-prod
      com.docker.network.bridge.enable_icc: "false"  # Disable inter-container communication by default

  monitoring-network:
    driver: bridge
    internal: true  # No external access
```

### 4. TLS/mTLS Configuration

**Enable TLS between services**:

**Generate certificates**:
```bash
# Create CA
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem

# Create server certificate
openssl genrsa -out server-key.pem 4096
openssl req -new -key server-key.pem -out server.csr
openssl x509 -req -days 365 -in server.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out server-cert.pem

# Store in deploy/config/ssl/
```

**Nginx TLS configuration**:

```nginx
# deploy/config/nginx.conf
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/nginx/ssl/server-cert.pem;
    ssl_certificate_key /etc/nginx/ssl/server-key.pem;
    ssl_client_certificate /etc/nginx/ssl/ca.pem;
    ssl_verify_client optional;  # or 'on' for strict mTLS

    # Modern TLS configuration
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    location / {
        proxy_pass http://api_backend;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
    }
}
```

## Secret Management

### 1. Never Commit Secrets

**Enforce with git hooks**:

```bash
# .git/hooks/pre-commit
#!/bin/sh
if grep -r "sk-.*" . --exclude-dir=.git; then
    echo "Potential secret detected!"
    exit 1
fi
```

**Use gitleaks in CI** (already implemented):
```yaml
# .github/workflows/security-supply-chain.yml includes gitleaks
```

### 2. Environment Variable Best Practices

**Production secret injection**:

```bash
# Use external secret store (e.g., AWS Secrets Manager, HashiCorp Vault)

# Load secrets at runtime
export SUPABASE_SERVICE_KEY=$(aws secretsmanager get-secret-value --secret-id prod/supabase/key --query SecretString --output text)
export NEO4J_PASSWORD=$(vault kv get -field=password secret/neo4j/prod)

# Then start services
make deploy-prod
```

**Docker secrets** (for Swarm mode):

```yaml
services:
  app:
    secrets:
      - supabase_key
      - neo4j_password

secrets:
  supabase_key:
    external: true
  neo4j_password:
    external: true
```

### 3. Secret Rotation

**Quarterly rotation schedule**:

| Secret | Rotation Frequency | Owner | Last Rotated |
|--------|-------------------|-------|--------------|
| Supabase Service Key | 90 days | Platform Team | 2025-10-01 |
| Neo4j Password | 90 days | Platform Team | 2025-10-01 |
| LLM API Keys | 180 days | Platform Team | 2025-09-01 |
| Redis Password | 90 days | Platform Team | 2025-10-01 |
| Grafana Admin | 90 days | SRE Team | 2025-10-01 |

**Rotation procedure**:
1. Generate new secret
2. Update in secret store
3. Update environment variables
4. Rolling restart services
5. Verify functionality
6. Revoke old secret
7. Document rotation date

## Vulnerability Management

### 1. Container Image Scanning

**Automated scanning** (already implemented):
- Trivy scans in CI/CD
- Block critical vulnerabilities
- SBOM generation

**Manual scans**:
```bash
# Scan production image
make image-scan

# Full report
make image-scan-full
```

### 2. Dependency Scanning

**Python dependencies**:
```bash
# Regular scans
make security

# Individual tools
pip-audit --format json
safety check --json
bandit -r src/
```

**Update policy**:
- **Critical**: Patch within 24 hours
- **High**: Patch within 7 days
- **Medium**: Patch in next release
- **Low**: Backlog

### 3. Penetration Testing

**Annual external pen test**:
- Scope: API endpoints, authentication, data access
- Provider: Reputable security firm
- Deliverable: Full report with remediation plan

**Continuous testing**:
```bash
# OWASP ZAP automated scan
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://api.example.com

# Nikto web scanner
nikto -h https://api.example.com
```

## Compliance & Auditing

### 1. Audit Logging

**Comprehensive logging**:

```python
# src/api/audit.py
import logging
import json
from datetime import datetime

audit_logger = logging.getLogger('audit')

def log_audit_event(
    event_type: str,
    user_id: str,
    resource: str,
    action: str,
    result: str,
    metadata: dict = None
):
    """Log security-relevant events."""
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'resource': resource,
        'action': action,
        'result': result,
        'metadata': metadata or {}
    }
    audit_logger.info(json.dumps(event))

# Usage
log_audit_event(
    event_type='DATA_ACCESS',
    user_id='user_123',
    resource='documents',
    action='SEARCH',
    result='SUCCESS',
    metadata={'query': 'sensitive query', 'result_count': 5}
)
```

**Audit log retention**: 1 year minimum

### 2. Compliance Requirements

**GDPR Compliance**:
- [ ] Data minimization implemented
- [ ] Right to erasure capability
- [ ] Data portability endpoints
- [ ] Consent management
- [ ] Privacy policy published

**SOC 2 Type II** (if applicable):
- [ ] Access controls documented
- [ ] Change management process
- [ ] Incident response plan
- [ ] Vendor risk assessment
- [ ] Security awareness training

## Incident Response

**Security Incident Escalation**:

1. **Detect**: Automated alerts, manual discovery
2. **Contain**: Isolate affected systems
3. **Investigate**: Determine scope and impact
4. **Eradicate**: Remove threat
5. **Recover**: Restore services
6. **Lessons Learned**: Post-incident review

**Security Contacts**:
- **Security Team**: security@example.com
- **Incident Commander**: +1-xxx-xxx-xxxx
- **Legal**: legal@example.com

## Hardening Checklist

### Pre-Production

- [ ] All containers run as non-root
- [ ] Read-only root filesystem enabled
- [ ] Security options configured (no-new-privileges, cap-drop)
- [ ] Resource limits set
- [ ] Network segmentation implemented
- [ ] TLS enabled for all external communication
- [ ] Secrets externalized (no hardcoded secrets)
- [ ] Vulnerability scans passing
- [ ] Audit logging enabled
- [ ] Firewall rules configured
- [ ] Docker daemon hardened
- [ ] OS security updates automated

### Post-Production

- [ ] Penetration test completed
- [ ] Security monitoring active
- [ ] Incident response plan tested
- [ ] Secret rotation schedule established
- [ ] Compliance requirements met
- [ ] Security training completed

## References

- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [NIST Container Security Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf)

---

**Last Updated**: 2025-10-08
**Owner**: Security Team
**Review Cadence**: Quarterly
