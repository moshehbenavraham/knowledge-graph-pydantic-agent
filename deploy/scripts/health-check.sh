#!/usr/bin/env bash
# ===============================================
# Health Check Script
# Luminari Agent - Agentic RAG Platform
# ===============================================

set -euo pipefail

ENVIRONMENT="${1:-staging}"
MAX_RETRIES=30
RETRY_INTERVAL=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Health check configuration per environment
case $ENVIRONMENT in
    dev)
        UI_URL="http://localhost:8501/_stcore/health"
        API_URL="http://localhost:8058/health"
        ;;
    staging)
        UI_URL="http://localhost:8501/_stcore/health"
        API_URL="http://localhost:8058/health"
        ;;
    production)
        UI_URL="${PROD_UI_URL:-http://localhost:8501}/_stcore/health"
        API_URL="${PROD_API_URL:-http://localhost:8058}/health"
        ;;
    *)
        log_error "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Function to check a single endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local retries=0

    log_info "Checking $name at $url..."

    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -f -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|204"; then
            log_info "✓ $name is healthy"
            return 0
        fi

        retries=$((retries + 1))
        if [ $retries -lt $MAX_RETRIES ]; then
            log_warn "$name not ready, retrying in ${RETRY_INTERVAL}s... ($retries/$MAX_RETRIES)"
            sleep $RETRY_INTERVAL
        fi
    done

    log_error "✗ $name health check failed after $MAX_RETRIES attempts"
    return 1
}

# Function to check container health
check_container_health() {
    local container_name=$1

    log_info "Checking container: $container_name"

    if ! docker ps | grep -q "$container_name"; then
        log_error "✗ Container $container_name is not running"
        return 1
    fi

    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")

    if [[ "$health_status" == "healthy" ]] || [[ "$health_status" == "none" ]]; then
        log_info "✓ Container $container_name is healthy"
        return 0
    else
        log_error "✗ Container $container_name health status: $health_status"
        return 1
    fi
}

# Main health check sequence
log_info "========================================="
log_info "Starting health checks for $ENVIRONMENT"
log_info "========================================="

FAILED=0

# Check UI endpoint
if ! check_endpoint "UI" "$UI_URL"; then
    FAILED=$((FAILED + 1))
fi

# Check API endpoint
if ! check_endpoint "API" "$API_URL"; then
    FAILED=$((FAILED + 1))
fi

# Check critical containers
CONTAINERS=(
    "base-agent-${ENVIRONMENT}"
    "base-agent-api-${ENVIRONMENT}"
    "neo4j-${ENVIRONMENT}"
    "redis-${ENVIRONMENT}"
)

for container in "${CONTAINERS[@]}"; do
    if ! check_container_health "$container"; then
        FAILED=$((FAILED + 1))
    fi
done

# Additional service checks for staging/production
if [[ "$ENVIRONMENT" != "dev" ]]; then
    log_info "Checking observability stack..."

    # Check Prometheus
    PROMETHEUS_URL="http://localhost:9090/-/healthy"
    if ! check_endpoint "Prometheus" "$PROMETHEUS_URL"; then
        log_warn "Prometheus health check failed (non-critical)"
    fi

    # Check Grafana
    GRAFANA_URL="http://localhost:3000/api/health"
    if ! check_endpoint "Grafana" "$GRAFANA_URL"; then
        log_warn "Grafana health check failed (non-critical)"
    fi
fi

# Functional tests
log_info "Running functional tests..."

# Test API status endpoint
API_STATUS_URL="${API_URL/health/api/v1/status}"
if curl -f -s "$API_STATUS_URL" | grep -q "status"; then
    log_info "✓ API status endpoint is functional"
else
    log_warn "API status endpoint check failed (non-critical)"
fi

# Final result
log_info "========================================="
if [ $FAILED -eq 0 ]; then
    log_info "All health checks passed! ✓"
    log_info "========================================="
    exit 0
else
    log_error "$FAILED health check(s) failed"
    log_error "========================================="
    exit 1
fi
