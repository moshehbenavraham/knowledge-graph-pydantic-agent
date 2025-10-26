# Supply Chain Security Documentation

## Overview

This document outlines the supply chain security measures for the Luminari Agent / Agentic RAG platform, including image provenance, SBOM generation, vulnerability scanning, and signing procedures.

## Container Image Supply Chain

### Base Images

**Production Image**: `python:3.11-slim`
- **Selection Rationale**: Minimal attack surface, official Python foundation image, regular security updates
- **CVE Monitoring**: Automated scanning via Trivy in CI/CD pipeline
- **Update Cadence**: Review and update base image monthly or on critical CVE disclosure

### Multi-Stage Build Process

Our Dockerfile uses a multi-stage build to minimize the final image size and attack surface:

1. **Builder Stage**: Compiles dependencies with build tools (gcc, g++, etc.)
2. **Runtime Stage**: Minimal runtime with only production dependencies
3. **API Stage**: Specialized variant for FastAPI server

**Benefits**:
- Reduced final image size (~70% smaller than single-stage)
- Elimination of build tools from production
- Separate security boundaries for build vs runtime

## SBOM (Software Bill of Materials) Generation

### Generating SBOM

We use **Syft** to generate Software Bill of Materials for all container images:

```bash
# Generate SBOM for the production image
make image-sbom

# Generate SBOM in multiple formats
syft packages docker:base-agent:latest -o json > sbom.json
syft packages docker:base-agent:latest -o spdx-json > sbom.spdx.json
syft packages docker:base-agent:latest -o cyclonedx-json > sbom.cyclonedx.json
```

### SBOM Storage

- **Location**: `artifacts/sbom/` directory in CI/CD artifacts
- **Formats**: JSON, SPDX-JSON, CycloneDX-JSON
- **Retention**: 90 days for all builds, indefinitely for production releases
- **Access**: Available to security team and compliance auditors

## Vulnerability Scanning

### Trivy Scanning

**Trivy** is our primary vulnerability scanner, integrated into CI/CD:

```bash
# Scan image for vulnerabilities
make image-scan

# Scan with severity filtering
trivy image --severity HIGH,CRITICAL base-agent:latest

# Generate vulnerability report
trivy image --format json --output trivy-report.json base-agent:latest
```

### Scan Policy

| Severity | Action | SLA |
|----------|--------|-----|
| CRITICAL | Block deployment, immediate remediation required | 24 hours |
| HIGH | Alert security team, remediate before next release | 7 days |
| MEDIUM | Track in backlog, remediate in maintenance window | 30 days |
| LOW | Informational, no action required | N/A |

### Exception Process

For vulnerabilities that cannot be immediately remediated:

1. Document exception in `docs/security/CVE_EXCEPTIONS.md`
2. Include:
   - CVE identifier
   - Affected component
   - Business justification
   - Compensating controls
   - Remediation timeline
   - Approver (Security Lead)

## Image Signing and Provenance

### Cosign Integration

We use **Cosign** for image signing to ensure authenticity and integrity:

```bash
# Sign the image
make image-sign

# Verify image signature
cosign verify --key cosign.pub ghcr.io/aiwithapex/base-agent:latest
```

### Signing Process

1. **Key Generation**: ED25519 keypair stored in secure vault
2. **Signing**: Automated in CI/CD post successful build and scan
3. **Verification**: Required before deployment to staging/production
4. **Key Rotation**: Annual rotation with 30-day overlap period

### Provenance Metadata

We generate and attach SLSA provenance metadata to all images:

```json
{
  "buildType": "https://github.com/slsa-framework/slsa/blob/main/docs/source-requirements.md",
  "builder": {
    "id": "https://github.com/actions/runner"
  },
  "invocation": {
    "configSource": {
      "uri": "git+https://github.com/aiwithapex/base_agent@refs/heads/main",
      "digest": {"sha1": "abc123..."}
    }
  }
}
```

## Dependency Management

### Python Dependencies

**File**: `requirements.txt`, `pyproject.toml`

**Vulnerability Scanning**:
```bash
# Scan Python dependencies
make security

# Individual tools
pip-audit
safety check
bandit -r src/
```

**Update Process**:
- **Patch updates**: Automated via Dependabot (weekly)
- **Minor updates**: Reviewed monthly in maintenance window
- **Major updates**: Planned with feature releases

### Pinning Strategy

- **Production**: Exact version pinning (e.g., `pydantic-ai==0.1.2`)
- **Development**: Compatible version ranges (e.g., `pydantic-ai>=0.1.2,<0.2.0`)
- **Hash Verification**: Use `--require-hashes` for production installs

## Registry Security

### Container Registry

- **Primary**: GitHub Container Registry (GHCR)
- **Authentication**: GitHub Actions OIDC tokens (no long-lived credentials)
- **Access Control**: Read-only for public images, write restricted to CI service account
- **Scanning**: Automatic vulnerability scanning by GitHub

### Image Tagging Strategy

| Tag Type | Pattern | Use Case | Mutability |
|----------|---------|----------|------------|
| Commit SHA | `sha-abc123` | Immutable reference for deployments | Immutable |
| Semantic Version | `v1.2.3` | Production releases | Immutable |
| Branch | `main`, `develop` | Development tracking | Mutable |
| Environment | `staging`, `production` | Environment deployment | Mutable |

## Compliance and Auditing

### Audit Trail

All supply chain activities are logged:

- **Image builds**: GitHub Actions logs (90-day retention)
- **Vulnerability scans**: Trivy reports stored in S3 (1-year retention)
- **Image signatures**: Transparency log (Rekor) for permanent record
- **Deployments**: Deployment logs with image SHA and signature verification

### Compliance Reporting

**Quarterly Report** includes:
- SBOM for all production images
- Vulnerability scan summary (Critical/High/Medium counts)
- Exception log with remediation status
- Base image update history
- Dependency update log

### SLSA Compliance

**Target**: SLSA Level 2
- ✅ Version-controlled build definitions
- ✅ Automated build process
- ✅ Provenance generation
- ✅ Non-falsifiable provenance

## Incident Response

### Vulnerability Disclosure

**Process**:
1. Security team notified via vulnerability scanner alert
2. Triage within 4 business hours
3. Severity assessment and SLA assignment
4. Remediation tracked in JIRA with security label
5. Deployment of patched image
6. Post-incident review

### Zero-Day Response

For critical zero-day vulnerabilities:
1. **Immediate**: Assess impact on deployed images
2. **Within 2 hours**: Communication to stakeholders
3. **Within 4 hours**: Mitigation plan (patch, workaround, or isolation)
4. **Within 24 hours**: Deployment of remediation
5. **Within 48 hours**: Post-mortem and process improvements

## Continuous Improvement

### Metrics

- **Mean Time to Remediate (MTTR)**: Target <7 days for HIGH severity
- **Scan Coverage**: 100% of production images
- **Signature Verification Rate**: 100% before deployment
- **SBOM Freshness**: <24 hours from image build

### Review Cadence

- **Weekly**: Vulnerability scan review
- **Monthly**: Dependency update review
- **Quarterly**: Supply chain policy review
- **Annually**: Third-party security audit

## Tools and Commands

### Quick Reference

```bash
# Full supply chain workflow
make image-build          # Multi-stage build
make image-sbom           # Generate SBOM
make image-scan           # Vulnerability scan
make image-sign           # Sign with Cosign
make image-push           # Push to registry
make image-verify         # Verify signature

# CI/CD integration
make ci-supply-chain      # Run all supply chain checks in CI
```

## References

- [SLSA Framework](https://slsa.dev/)
- [NIST Secure Software Development Framework (SSDF)](https://csrc.nist.gov/publications/detail/sp/800-218/final)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Cosign Documentation](https://docs.sigstore.dev/cosign/overview/)
- [SBOM Tool: Syft](https://github.com/anchore/syft)

---

**Last Updated**: 2025-10-08
**Owner**: Platform Security Team
**Reviewers**: DevOps, Compliance
