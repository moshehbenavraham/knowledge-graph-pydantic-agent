# Phase 5 Tool Installation Guide

## Required Tools

Phase 5 deployment requires the following tools:

### Critical (Required)
- **Docker** - Container runtime
- **Docker Compose** - Multi-container orchestration
- **jq** - JSON processor for scripts
- **Trivy** - Vulnerability scanner
- **Syft** - SBOM generator
- **Cosign** - Image signing tool

### Already Installed
- **dos2unix** - Line ending converter
- **yamllint** - YAML validation
- **git** - Version control
- **curl** - HTTP client

### Optional (Run in Containers)
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Loki** - Log aggregation

---

## Quick Installation

### Option 1: Automated Script (Recommended)

```bash
# Run the installation script
sudo bash deploy/scripts/install-tools.sh

# Log out and back in for Docker group membership
# Then verify:
bash deploy/scripts/check-tools.sh
```

### Option 2: Manual Installation

#### Ubuntu/Debian

```bash
# Update package manager
sudo apt-get update

# Install jq
sudo apt-get install -y jq

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# Install Trivy
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install -y trivy

# Install Syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sudo sh -s -- -b /usr/local/bin

# Install Cosign
COSIGN_VERSION="2.2.2"
wget "https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-linux-amd64"
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
sudo chmod +x /usr/local/bin/cosign
```

#### CentOS/RHEL/Fedora

```bash
# Update package manager
sudo yum update -y  # or sudo dnf update -y

# Install jq
sudo yum install -y jq

# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Trivy
TRIVY_VERSION="0.48.3"
wget https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz
tar zxvf trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz
sudo mv trivy /usr/local/bin/

# Install Syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sudo sh -s -- -b /usr/local/bin

# Install Cosign
COSIGN_VERSION="2.2.2"
wget "https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-linux-amd64"
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
sudo chmod +x /usr/local/bin/cosign
```

#### macOS (Homebrew)

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install tools
brew install jq
brew install docker docker-compose
brew install trivy
brew install syft
brew install cosign

# Start Docker Desktop
open -a Docker
```

---

## Verification

Run the tool check script:

```bash
bash deploy/scripts/check-tools.sh
```

Expected output:
```
=== Phase 5 Tool Requirements Check ===

Core Tools:
✅ docker
✅ docker-compose
✅ git
✅ curl
✅ jq

Text Processing:
✅ dos2unix
✅ sed

Configuration Validation:
✅ yamllint

Security & Supply Chain:
✅ trivy
✅ syft
✅ cosign

================================
✅ All required tools installed!
```

---

## Version Requirements

| Tool | Minimum Version | Recommended |
|------|----------------|-------------|
| Docker | 20.10+ | 24.0+ |
| Docker Compose | 2.0+ | 2.20+ |
| jq | 1.5+ | 1.6+ |
| Trivy | 0.40+ | 0.48+ |
| Syft | 0.90+ | 1.0+ |
| Cosign | 2.0+ | 2.2+ |

Check versions:
```bash
docker --version
docker-compose --version
jq --version
trivy --version
syft version
cosign version
```

---

## Troubleshooting

### Docker Permission Denied

If you get "permission denied" when running Docker:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Verify
docker ps
```

### Docker Compose Command Not Found

If `docker-compose` is not found but you have the plugin:

```bash
# Use the plugin syntax instead
docker compose version

# Or create an alias
echo 'alias docker-compose="docker compose"' >> ~/.bashrc
source ~/.bashrc
```

### Trivy Database Update Issues

If Trivy fails to update its vulnerability database:

```bash
# Clear cache and update
trivy image --clear-cache
trivy image --download-db-only
```

### WSL2 Docker Issues

If running on Windows WSL2:

```bash
# Install Docker Desktop for Windows
# Enable WSL2 integration in Docker Desktop settings
# Restart WSL2 terminal
```

---

## Tool Usage Quick Reference

### Docker
```bash
# Build image
docker build -f docker/Dockerfile.production -t knowledge-graph-pydantic-agent:latest .

# Run container
docker run -d --name kgpa-app knowledge-graph-pydantic-agent:latest

# View logs
docker logs kgpa-app

# Stop container
docker stop kgpa-app
```

### Docker Compose
```bash
# Start services
docker-compose -f docker/docker-compose.prod.yml up -d

# View status
docker-compose -f docker/docker-compose.prod.yml ps

# Stop services
docker-compose -f docker/docker-compose.prod.yml down
```

### Trivy
```bash
# Scan image
trivy image knowledge-graph-pydantic-agent:latest

# Scan with severity filter
trivy image --severity HIGH,CRITICAL knowledge-graph-pydantic-agent:latest

# Generate report
trivy image --format json --output report.json knowledge-graph-pydantic-agent:latest
```

### Syft
```bash
# Generate SBOM
syft packages knowledge-graph-pydantic-agent:latest -o spdx-json

# Save to file
syft packages knowledge-graph-pydantic-agent:latest -o cyclonedx-json > sbom.json
```

### Cosign
```bash
# Generate keypair (one-time)
cosign generate-key-pair

# Sign image
cosign sign --key cosign.key knowledge-graph-pydantic-agent:latest

# Verify signature
cosign verify --key cosign.pub knowledge-graph-pydantic-agent:latest
```

### jq
```bash
# Parse JSON
echo '{"name": "kgpa", "version": "1.0"}' | jq '.name'

# Pretty print
cat report.json | jq .

# Filter array
cat report.json | jq '.Results[].Vulnerabilities[]?'
```

---

## CI/CD Requirements

For GitHub Actions (already configured in `.github/workflows/`):

- Docker and Docker Compose are pre-installed on GitHub runners
- Trivy is available via GitHub Actions marketplace
- Syft is available via GitHub Actions marketplace
- Cosign is available via GitHub Actions marketplace

No additional setup needed for CI/CD!

---

## Next Steps

After installing tools:

1. **Verify installation**: `bash deploy/scripts/check-tools.sh`
2. **Test Docker**: `docker run hello-world`
3. **Run YAML validation**: `make validate-config` (if defined)
4. **Build production image**: `make image-build`
5. **Scan image**: `make image-scan`
6. **Deploy to dev**: `make deploy-dev`

---

**Last Updated**: 2025-10-08
**Maintainer**: Platform SRE Team
