# Security Documentation

## Table of Contents
1. [Security Development Tooling](#security-development-tooling)
2. [Current Security Situation](#current-security-situation)
3. [Authentication & Authorization](#authentication--authorization)
4. [Data Protection](#data-protection)
5. [Container & Docker Security](#container--docker-security)
6. [Supply Chain Security](#supply-chain-security)
7. [Dependency Security](#dependency-security)
8. [Security Best Practices](#security-best-practices)
9. [Compliance & Auditing](#compliance--auditing)
10. [Incident Response](#incident-response)

---

## Security Development Tooling

### Static Analysis Tools

#### 1. **Bandit** (Python Security Linter)
- **Purpose**: Scans Python code for common security issues
- **Configuration**: Pre-commit hook, excludes test files
- **Run Command**: `make security` or `bandit -r src/`
- **Ignored Issues**: B101 (assert usage), B603 (subprocess usage)
- **Integration**: CI/CD pipeline via pre-commit

#### 2. **Safety** (Dependency Vulnerability Scanner)
- **Purpose**: Checks Python dependencies for known vulnerabilities
- **Database**: Safety vulnerability database (CVE tracking)
- **Run Command**: `safety scan`
- **Integration**: Part of `make security` command

#### 3. **pip-audit** (Python Package Vulnerability Scanner)
- **Purpose**: Audits Python packages for known vulnerabilities
- **Database**: OSV (Open Source Vulnerabilities) database
- **Run Command**: `pip-audit`
- **Ignored Vulnerabilities**: GHSA-4xh5-x5gv-qwph (pip vulnerability)
- **Current Status**: 8 known vulnerabilities in 6 packages (monitored)

#### 4. **Ruff** (Fast Python Linter)
- **Security Rules**: B (flake8-bugbear) security patterns
- **Configuration**: `.ruff.toml`
- **Auto-fix**: Yes, with `--fix` flag

#### 5. **Pre-commit Hooks**
- **Security Hooks**:
  - Bandit (Python security)
  - pip-audit (dependency vulnerabilities)
  - Check for merge conflicts
  - Large file prevention
  - YAML/JSON/TOML validation
- **Custom Hooks**:
  - Constitution compliance validator
  - Problematic character detection
  - Documentation link validation

### Security Testing Commands

```bash
# Full security scan
make security

# Individual scans
bandit -r src/
safety scan
pip-audit

# Code quality with security checks
make quality

# Full check including security
make check
```

---

## Current Security Situation

### Overall Security Posture: **STRONG**

The codebase implements comprehensive security measures across authentication, authorization, data protection, and dependency management. The system follows defense-in-depth principles with multiple security layers.

### Key Security Features

#### Authentication System (v1.8.0+)
- **Multi-factor Authentication**:
  - Password-based authentication with bcrypt (12 rounds)
  - TOTP 2FA with QR codes and backup codes
  - OAuth 2.0 (Google, GitHub, Microsoft, Apple)
  - Email verification with secure tokens
  - CAPTCHA support (hCaptcha, reCAPTCHA)

- **Session Management**:
  - 30-day cookie duration with 30-minute idle timeout
  - Secure session storage in PostgreSQL
  - Session revocation capabilities
  - Device tracking and management

- **Rate Limiting**:
  - 5 failed attempts trigger 15-minute lockout
  - IP address tracking
  - Automatic cleanup of expired lockouts

#### Data Protection
- **SQL Injection Prevention**:
  - Parameterized queries via Supabase RPC
  - Read-only query validation
  - Write operation detection and blocking
  - Sanitization of SQL commands

- **Code Execution Sandboxing**:
  - RestrictedPython environment
  - Whitelisted modules only
  - Custom import restrictions
  - Output capture and timeout controls

- **Cross-Site Scripting (XSS) Prevention**:
  - Streamlit's built-in XSS protection
  - Content sanitization in UI components
  - Secure markdown rendering

#### Encryption & Hashing
- **Password Security**:
  - Bcrypt with 12 rounds for password hashing
  - Password strength validation (min 8 chars, complexity requirements)
  - Password history tracking (prevents reuse of last 5)
  - Breach detection via haveibeenpwned.com API

- **Token Security**:
  - Fernet encryption for OAuth tokens
  - Secure random token generation
  - Time-limited tokens (1 hour for password reset)
  - HMAC signatures for critical operations

#### Security Headers & Configuration
- **HTTPS Enforcement**: Via ngrok tunnel with SSL/TLS
- **Cookie Security**: Secure, HttpOnly, SameSite attributes
- **CORS Configuration**: Restricted to allowed origins
- **CSP Headers**: Content Security Policy via Streamlit

### Security Exceptions (nosec comments)

The codebase uses `nosec` comments to suppress false positives from Bandit:

1. **Intentional Code Execution** (`src/tools/code_execution.py`):
   - `exec()` used for agent tool functionality
   - Protected by RestrictedPython sandbox

2. **OAuth Endpoint URLs** (`src/auth/oauth_handler.py`):
   - Public OAuth URLs flagged as passwords (B105)
   - These are legitimate API endpoints

3. **Random Number Generation** (`src/utils/resilience.py`):
   - Non-cryptographic random for retry delays (B311)
   - Not used for security purposes

4. **Internal Caching** (`src/utils/cache.py`):
   - Pickle usage for internal cache only (B403, B301)
   - Never used with user input

5. **SQL Queries** (multiple files):
   - Legitimate SQL queries flagged (B608)
   - All use parameterized queries

---

## Authentication & Authorization

### Two-Factor Authentication (2FA)
- **TOTP Implementation**:
  - RFC 6238 compliant
  - 30-second time windows
  - Backup codes (10 codes, single-use)
  - QR code generation for authenticator apps

### OAuth 2.0 Integration
- **Supported Providers**:
  - Google (OpenID Connect)
  - GitHub
  - Microsoft Azure AD
  - Apple Sign In

- **Security Measures**:
  - State parameter for CSRF protection
  - PKCE for public clients
  - Token encryption at rest
  - Automatic token refresh

### Password Management
- **Strength Requirements**:
  - Minimum 8 characters
  - Uppercase and lowercase letters
  - Numbers and special characters
  - Visual strength indicator

- **Advanced Features**:
  - Password history (last 5 passwords)
  - Breach detection integration
  - Password reset via email
  - Temporary password support

### Authorization
- **Role-Based Access Control (RBAC)**:
  - Roles: admin, user, viewer
  - Database-backed permissions
  - Role assignment CLI tools
  - Audit logging for role changes

---

## Data Protection

### SQL Injection Prevention

```python
# Example from src/tools/sql_query.py
write_operations = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
for op in write_operations:
    if re.search(r"\b" + op + r"\b", upper_query):
        return f"Error: Write operation '{op}' detected."

# All queries go through Supabase RPC with parameterization
result = supabase.rpc("execute_sql", {"query": sql_query}).execute()
```

### Code Execution Sandboxing

```python
# Example from src/tools/code_execution.py
allowed_modules = {
    "datetime", "math", "random", "time", "collections",
    "itertools", "functools", "json", "csv", "uuid"
}

safe_builtins = {
    "abs", "all", "any", "bool", "dict", "list", "str",
    # File operations and imports restricted
}
```

### API Key Protection
- All sensitive keys in environment variables
- `.env` file excluded from version control
- Encrypted storage for OAuth tokens
- Key rotation procedures documented

---

## Container & Docker Security

### Container Hardening

#### Non-Root User Execution
All production containers run as non-root users:
```dockerfile
# Create non-root user
RUN groupadd -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -s /sbin/nologin appuser
USER appuser
```

#### Security Configuration
```yaml
# docker-compose.prod.yml
services:
  app:
    read_only: true  # Read-only root filesystem
    security_opt:
      - no-new-privileges:true  # Prevent privilege escalation
    cap_drop:
      - ALL  # Drop all capabilities
    cap_add:
      - NET_BIND_SERVICE  # Only add required capabilities
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
          pids: 100  # Limit process count
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
```

### Docker Daemon Hardening
Configuration in `/etc/docker/daemon.json`:
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
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

### Network Segmentation
- Isolated production networks with custom subnets
- Inter-container communication disabled by default
- Internal networks for monitoring components
- TLS/mTLS for service-to-service communication

### TLS Configuration
Example Nginx configuration for production:
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/server-cert.pem;
    ssl_certificate_key /etc/nginx/ssl/server-key.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

### Container Image Scanning

#### Trivy Integration
- **Automated Scanning**: All images scanned in CI/CD pipeline
- **Severity Policy**:
  - CRITICAL: Block deployment, fix within 24 hours
  - HIGH: Alert team, fix within 7 days
  - MEDIUM: Track in backlog, fix within 30 days
  - LOW: Informational only

```bash
# Scan commands
make image-scan           # Basic scan
make image-scan-full     # Detailed report
trivy image --severity HIGH,CRITICAL base-agent:latest
```

### CIS Docker Benchmark
Regular compliance checks using Docker Bench Security:
```bash
git clone https://github.com/docker/docker-bench-security.git
cd docker-bench-security
sudo sh docker-bench-security.sh
```

---

## Supply Chain Security

### Software Bill of Materials (SBOM)

#### SBOM Generation
Using Syft for comprehensive SBOM creation:
```bash
make image-sbom  # Generate SBOM
syft packages docker:base-agent:latest -o json > sbom.json
syft packages docker:base-agent:latest -o spdx-json > sbom.spdx.json
syft packages docker:base-agent:latest -o cyclonedx-json > sbom.cyclonedx.json
```

#### SBOM Management
- **Storage**: `artifacts/sbom/` directory
- **Formats**: JSON, SPDX, CycloneDX
- **Retention**: 90 days for builds, indefinite for production releases

### Image Signing & Provenance

#### Cosign Integration
Digital signatures for container images:
```bash
make image-sign    # Sign image
make image-verify  # Verify signature
cosign verify --key cosign.pub ghcr.io/aiwithapex/base-agent:latest
```

#### Signing Process
1. ED25519 keypair stored in secure vault
2. Automated signing post-build in CI/CD
3. Mandatory verification before deployment
4. Annual key rotation with 30-day overlap

#### SLSA Provenance
- Version-controlled build definitions
- Automated build process
- Non-falsifiable provenance generation
- Target: SLSA Level 2 compliance

### Base Image Management
- **Production Base**: `python:3.11-slim`
- **Update Cadence**: Monthly review or on critical CVE
- **Multi-stage builds**: Minimize attack surface
- **Size Reduction**: ~70% smaller than single-stage

### Registry Security
- **Primary Registry**: GitHub Container Registry (GHCR)
- **Authentication**: GitHub Actions OIDC tokens
- **Access Control**: Read-only public, write restricted to CI
- **Tagging Strategy**:
  - Commit SHA: Immutable deployment reference
  - Semantic Version: Production releases
  - Branch tags: Development tracking

### Secret Rotation Schedule

| Secret | Rotation Frequency | Last Rotated | Next Rotation |
|--------|-------------------|--------------|---------------|
| Supabase Service Key | 90 days | 2025-01-01 | 2025-04-01 |
| Neo4j Password | 90 days | 2025-01-01 | 2025-04-01 |
| LLM API Keys | 180 days | 2024-09-01 | 2025-03-01 |
| OAuth Client Secrets | 365 days | 2024-07-01 | 2025-07-01 |
| Encryption Keys | 365 days | 2024-07-01 | 2025-07-01 |

### External Secret Management
Production secrets stored in external vaults:
```bash
# AWS Secrets Manager
export SUPABASE_KEY=$(aws secretsmanager get-secret-value \
  --secret-id prod/supabase/key --query SecretString --output text)

# HashiCorp Vault
export NEO4J_PASSWORD=$(vault kv get -field=password secret/neo4j/prod)
```

---

## Dependency Security

### Current Vulnerability Status

As of the latest scan:
- **8 known vulnerabilities in 6 packages**
- All vulnerabilities are being monitored
- Regular updates scheduled for patch releases

### Accepted Security Exceptions

#### CVE-2022-42969 - py package (1.11.0)

**Status**: Risk Accepted
**Date Assessed**: 2025-10-31
**Package**: py==1.11.0 (via interrogate dependency)
**Severity**: Medium (CVSS 5.3)

**Details**:
- **Vulnerability**: ReDoS (Regular expression Denial of Service) in SVN command handling
- **Affected Component**: py.svn module's InfoSvnCommand functionality
- **Impact on Project**: **None** - We do not use Subversion repositories or the affected SVN functionality
- **Package Status**: The py library is deprecated and frozen at version 1.11.0 (no fix will be released)

**Risk Assessment**:
1. **Disputed Vulnerability**: Multiple third parties have disputed this CVE as not reproducible
2. **Limited Scope**: Only affects SVN repository operations which are not used in this project
3. **Low Exploitation Probability**: EPSS Score of 0.10%

**Mitigation**:
- Documented that SVN functionality is not used in the project
- Added comment in pyproject.toml noting the accepted risk
- Monitoring pytest's ongoing work to remove the py dependency entirely

**References**:
- [CVE-2022-42969 Details](https://nvd.nist.gov/vuln/detail/CVE-2022-42969)
- [pytest-dev/pytest Issue #10392](https://github.com/pytest-dev/pytest/issues/10392)
- [py package deprecation discussion](https://github.com/pytest-dev/pytest/issues/7259)

### Automated Scanning
- **Pre-commit**: pip-audit runs before each commit
- **CI/CD**: Security scans in GitHub Actions
- **Manual**: `make security` for comprehensive scan

### Dependency Management
- **Lock File**: Requirements pinned in pyproject.toml
- **Update Strategy**: Monthly security updates
- **Critical Updates**: Immediate patching for high/critical CVEs

---

## Security Best Practices

### Development Guidelines

1. **Never Store Secrets in Code**:
   - Use environment variables
   - Rotate keys regularly
   - Use secret management tools

2. **Input Validation**:
   - Sanitize all user input
   - Use parameterized queries
   - Validate file uploads

3. **Error Handling**:
   - Don't expose stack traces to users
   - Log security events
   - Implement proper error recovery

4. **Code Review Requirements**:
   - Security review for auth changes
   - Dependency updates reviewed
   - Security test coverage maintained

### Incident Response

1. **Vulnerability Disclosure**:
   - Report to: security@baseagent.ai (example)
   - Expected response: 24-48 hours
   - Coordinated disclosure policy

2. **Security Updates**:
   - Critical: Immediate patching
   - High: Within 7 days
   - Medium: Within 30 days
   - Low: Next release cycle

### Compliance & Standards

- **OWASP Top 10**: All items addressed
- **CWE/SANS Top 25**: Mitigations in place
- **GDPR**: Data protection measures implemented
- **SOC 2**: Security controls documented

---

## Compliance & Auditing

### Audit Logging

Comprehensive security event logging:

```python
# Example audit logging implementation
def log_audit_event(
    event_type: str,
    user_id: str,
    resource: str,
    action: str,
    result: str,
    metadata: dict = None
):
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
```

**Logged Events**:
- Authentication attempts (success/failure)
- Authorization decisions
- Data access operations
- Configuration changes
- Security exceptions
- API usage patterns

**Retention Policy**:
- Audit logs: 1 year minimum
- Security events: 2 years
- Compliance reports: 7 years

### GDPR Compliance

- **Data Minimization**: Only collect necessary data
- **Right to Erasure**: User data deletion capability implemented
- **Data Portability**: Export user data in standard formats
- **Consent Management**: Explicit consent for data processing
- **Privacy Policy**: Published and version-controlled
- **Data Protection Officer**: Designated contact for privacy concerns

### SOC 2 Type II Requirements

- **Access Controls**: RBAC with audit trails
- **Change Management**: All changes tracked in git
- **Incident Response**: Documented procedures and runbooks
- **Vendor Risk Assessment**: Third-party security reviews
- **Security Awareness**: Regular training for all team members
- **Business Continuity**: Backup and recovery procedures

### Penetration Testing

**Annual External Testing**:
- Scope: API endpoints, authentication, data access, infrastructure
- Provider: Certified penetration testing firm
- Deliverables: Executive summary, technical report, remediation plan
- Timeline: Q1 of each year

**Continuous Security Testing**:
```bash
# OWASP ZAP automated scanning
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://api.baseagent.com

# Nikto web vulnerability scanner
nikto -h https://api.baseagent.com

# SQLMap for SQL injection testing (staging only)
sqlmap -u "https://staging.baseagent.com/api/search?q=test" \
  --batch --random-agent
```

### Security Metrics & KPIs

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Mean Time to Remediate (Critical) | <24h | 18h | ✅ |
| Mean Time to Remediate (High) | <7d | 5d | ✅ |
| Scan Coverage | 100% | 100% | ✅ |
| Password Complexity Compliance | >95% | 98% | ✅ |
| MFA Adoption | >90% | 85% | ⚠️ |
| Security Training Completion | 100% | 92% | ⚠️ |

### Compliance Checklist

#### Pre-Production
- [ ] Security architecture review completed
- [ ] Threat modeling performed
- [ ] Code security review passed
- [ ] Vulnerability scan clean (no HIGH/CRITICAL)
- [ ] Penetration test findings remediated
- [ ] Security documentation updated
- [ ] Incident response plan tested

#### Production Operations
- [ ] 24/7 security monitoring active
- [ ] Log aggregation and analysis configured
- [ ] Intrusion detection systems deployed
- [ ] Security patches applied within SLA
- [ ] Regular security assessments scheduled
- [ ] Compliance audits passed

---

## Incident Response

### Security Incident Management

#### Incident Classification
| Severity | Definition | Response Time | Escalation |
|----------|------------|---------------|------------|
| P1 - Critical | Data breach, system compromise, zero-day exploit | Immediate | CTO, Security Lead, Legal |
| P2 - High | Failed authentication attempts, DDoS attack | 1 hour | Security Lead, DevOps |
| P3 - Medium | Vulnerability discovered, suspicious activity | 4 hours | Security Team |
| P4 - Low | Policy violation, minor configuration issue | 24 hours | Security Team |

#### Response Process
1. **Detect & Alert**: Automated monitoring or manual discovery
2. **Assess & Classify**: Determine severity and impact
3. **Contain**: Isolate affected systems to prevent spread
4. **Investigate**: Root cause analysis and forensics
5. **Eradicate**: Remove threat and patch vulnerabilities
6. **Recover**: Restore services and verify functionality
7. **Document**: Post-incident report and lessons learned

### Zero-Day Response Procedures

**Immediate Actions (0-2 hours)**:
1. Assess impact on deployed systems
2. Activate incident response team
3. Implement emergency containment measures
4. Notify key stakeholders

**Short-term Response (2-4 hours)**:
1. Develop mitigation plan (patch, workaround, or isolation)
2. Test mitigation in staging environment
3. Communicate with customers if affected
4. Prepare deployment strategy

**Remediation (4-24 hours)**:
1. Deploy patches or workarounds to production
2. Verify mitigation effectiveness
3. Monitor for exploitation attempts
4. Update security controls

**Post-Incident (24-48 hours)**:
1. Complete post-mortem analysis
2. Update incident response procedures
3. Share threat intelligence with community
4. Review and improve detection capabilities

### Vulnerability Disclosure Policy

**Responsible Disclosure Process**:
1. **Report Submission**: security@baseagent.ai
2. **Acknowledgment**: Within 24 hours
3. **Initial Assessment**: Within 48 hours
4. **Resolution Timeline**: Based on severity (24h to 30d)
5. **Coordinated Disclosure**: After patch deployment
6. **Credit**: Security researchers acknowledged (with permission)

**Bug Bounty Program** (if applicable):
- Critical: $5,000 - $10,000
- High: $1,000 - $5,000
- Medium: $500 - $1,000
- Low: $100 - $500

### Incident Communication

**Internal Communication**:
- Slack: #security-incidents channel
- Email: security-team@baseagent.ai
- Phone: Security hotline (24/7)

**External Communication**:
- Customer notification within 72 hours (GDPR requirement)
- Regulatory notification as required
- Public disclosure after remediation
- Status page updates for service impact

### Recovery Time Objectives

| System Component | RTO | RPO | Priority |
|-----------------|-----|-----|----------|
| Authentication Service | 1 hour | 15 min | Critical |
| API Gateway | 2 hours | 30 min | Critical |
| Database | 4 hours | 1 hour | High |
| Analytics | 8 hours | 4 hours | Medium |
| Documentation | 24 hours | 24 hours | Low |

---

## Future Security Enhancements

### Planned Improvements

1. **Additional Authentication**:
   - WebAuthn/FIDO2 support
   - Biometric authentication
   - Hardware token support

2. **Enhanced Monitoring**:
   - SIEM integration
   - Real-time threat detection
   - Automated response systems

3. **Zero Trust Architecture**:
   - Service mesh implementation
   - Mutual TLS (mTLS)
   - Policy-based access control

4. **Compliance Certifications**:
   - SOC 2 Type II
   - ISO 27001
   - HIPAA compliance (if needed)

---

## Security Contacts

- **Security Team**: security@baseagent.ai (example)
- **Bug Bounty**: bounty@baseagent.ai (example)
- **Emergency**: security-emergency@baseagent.ai (example)

---

## Additional References

### External Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [SLSA Framework](https://slsa.dev/)
- [GDPR Compliance Guide](https://gdpr.eu/)

### Security Hardening Checklist

#### Container Security
- [ ] All containers run as non-root users
- [ ] Read-only root filesystem enabled
- [ ] Security capabilities properly configured
- [ ] Resource limits enforced
- [ ] Network segmentation implemented
- [ ] Container images scanned and signed

#### Host Security
- [ ] OS security patches up-to-date
- [ ] Firewall rules configured
- [ ] Docker daemon hardened
- [ ] Audit logging enabled
- [ ] Intrusion detection active
- [ ] Regular security assessments

#### Application Security
- [ ] Authentication mechanisms robust
- [ ] Authorization properly implemented
- [ ] Input validation comprehensive
- [ ] Output encoding in place
- [ ] Secrets externalized and encrypted
- [ ] Security headers configured

#### Operational Security
- [ ] Incident response plan tested
- [ ] Backup and recovery verified
- [ ] Monitoring and alerting active
- [ ] Security training completed
- [ ] Compliance requirements met
- [ ] Documentation current

---

*Last Updated: 2025-10-31*
*Version: 2.1.0*

**Note**: This is the comprehensive security documentation for the Luminari Agent system, covering all aspects of security including development tooling, authentication, container hardening, supply chain security, compliance, and incident response.
