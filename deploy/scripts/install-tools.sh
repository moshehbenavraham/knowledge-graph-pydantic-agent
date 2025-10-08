#!/usr/bin/env bash
# ===============================================
# Phase 5 Tool Installation Script
# Installs all required tools for deployment
# ===============================================

set -euo pipefail

echo "=== Installing Phase 5 Required Tools ==="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS"
    exit 1
fi

# Update package manager
echo "Updating package manager..."
if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
    sudo apt-get update
elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]]; then
    sudo yum update -y
elif [[ "$OS" == "fedora" ]]; then
    sudo dnf update -y
fi

# Install jq (JSON processor)
echo ""
echo "Installing jq..."
if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
    sudo apt-get install -y jq
elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]] || [[ "$OS" == "fedora" ]]; then
    sudo yum install -y jq || sudo dnf install -y jq
fi

# Install Docker
echo ""
echo "Installing Docker..."
if ! command -v docker &> /dev/null; then
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        # Official Docker installation
        sudo apt-get install -y ca-certificates curl gnupg
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg

        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

        # Add current user to docker group
        sudo usermod -aG docker $USER

    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]]; then
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
    fi
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose (standalone - backup if plugin not available)
echo ""
echo "Installing Docker Compose standalone..."
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_VERSION="2.24.0"
    sudo curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

# Install Trivy (vulnerability scanner)
echo ""
echo "Installing Trivy..."
if ! command -v trivy &> /dev/null; then
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
        echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
        sudo apt-get update
        sudo apt-get install -y trivy
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]]; then
        TRIVY_VERSION="0.48.3"
        wget https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz
        tar zxvf trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz
        sudo mv trivy /usr/local/bin/
        rm trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz
    fi
    echo "✅ Trivy installed"
else
    echo "✅ Trivy already installed"
fi

# Install Syft (SBOM generator)
echo ""
echo "Installing Syft..."
if ! command -v syft &> /dev/null; then
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sudo sh -s -- -b /usr/local/bin
    echo "✅ Syft installed"
else
    echo "✅ Syft already installed"
fi

# Install Cosign (image signing)
echo ""
echo "Installing Cosign..."
if ! command -v cosign &> /dev/null; then
    COSIGN_VERSION="2.2.2"
    wget "https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-linux-amd64"
    sudo mv cosign-linux-amd64 /usr/local/bin/cosign
    sudo chmod +x /usr/local/bin/cosign
    echo "✅ Cosign installed"
else
    echo "✅ Cosign already installed"
fi

echo ""
echo "========================================="
echo "✅ All tools installed successfully!"
echo "========================================="
echo ""
echo "⚠️  IMPORTANT: You may need to log out and back in for Docker group membership to take effect"
echo ""
echo "Verify installation:"
echo "  docker --version"
echo "  docker-compose --version"
echo "  jq --version"
echo "  trivy --version"
echo "  syft --version"
echo "  cosign version"
