#!/bin/bash
echo "=== Phase 5 Tool Requirements Check ==="
echo ""

# Function to check if command exists
check_tool() {
    if command -v "$1" &> /dev/null; then
        echo "✅ $1 ($(command -v $1))"
        return 0
    else
        echo "❌ $1 - NOT INSTALLED"
        return 1
    fi
}

MISSING=0

# Core tools
echo "Core Tools:"
check_tool "docker" || ((MISSING++))
check_tool "docker-compose" || ((MISSING++))
check_tool "git" || ((MISSING++))
check_tool "curl" || ((MISSING++))
check_tool "jq" || ((MISSING++))
echo ""

# Line ending tools
echo "Text Processing:"
check_tool "dos2unix" || ((MISSING++))
check_tool "sed" || ((MISSING++))
echo ""

# YAML validation
echo "Configuration Validation:"
check_tool "yamllint" || ((MISSING++))
echo ""

# Security & Supply Chain
echo "Security & Supply Chain:"
check_tool "trivy" || ((MISSING++))
check_tool "syft" || ((MISSING++))
check_tool "cosign" || ((MISSING++))
check_tool "grype" || echo "⚠️  grype (optional - alternative to trivy)"
echo ""

# Monitoring tools
echo "Monitoring (optional for local testing):"
check_tool "prometheus" || echo "⚠️  prometheus (runs in container)"
check_tool "grafana-cli" || echo "⚠️  grafana (runs in container)"
echo ""

echo "================================"
if [ $MISSING -eq 0 ]; then
    echo "✅ All required tools installed!"
else
    echo "❌ Missing $MISSING required tools"
fi
