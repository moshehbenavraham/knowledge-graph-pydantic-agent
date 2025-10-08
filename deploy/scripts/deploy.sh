#!/usr/bin/env bash
# ===============================================
# Deployment Script with Health Checks
# Base Agent - Agentic RAG Platform
# ===============================================

set -euo pipefail

# Configuration
ENVIRONMENT="${1:-staging}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="/tmp/deploy-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Validation
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    echo "Usage: $0 <dev|staging|production>"
    exit 1
fi

log_info "Starting deployment to $ENVIRONMENT environment"
log_info "Log file: $LOG_FILE"

# Pre-deployment checks
log_info "Running pre-deployment checks..."

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running"
    exit 1
fi
log_info "✓ Docker is running"

# Check required environment variables
REQUIRED_VARS=(
    "SUPABASE_URL"
    "SUPABASE_SERVICE_KEY"
    "NEO4J_PASSWORD"
    "LLM_API_KEY"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        log_error "Required environment variable $var is not set"
        exit 1
    fi
done
log_info "✓ All required environment variables are set"

# Load environment-specific configuration
ENV_FILE="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
if [[ -f "$ENV_FILE" ]]; then
    log_info "Loading environment from $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
fi

# Set compose file based on environment
COMPOSE_FILE="${PROJECT_ROOT}/docker/docker-compose.${ENVIRONMENT}.yml"
if [[ ! -f "$COMPOSE_FILE" ]]; then
    log_error "Compose file not found: $COMPOSE_FILE"
    exit 1
fi
log_info "✓ Using compose file: $COMPOSE_FILE"

# Production safety check
if [[ "$ENVIRONMENT" == "production" ]]; then
    log_warn "=== PRODUCTION DEPLOYMENT WARNING ==="
    log_warn "You are about to deploy to PRODUCTION"
    log_warn "Current image tag: ${IMAGE_TAG:-latest}"
    read -p "Are you sure you want to continue? (type 'yes' to proceed): " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_error "Deployment cancelled by user"
        exit 1
    fi
fi

# Backup current state
log_info "Backing up current deployment state..."
BACKUP_DIR="${PROJECT_ROOT}/deploy/backups/${ENVIRONMENT}"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="${BACKUP_DIR}/backup-$(date +%Y%m%d-%H%M%S).tar.gz"

if docker ps -a | grep -q "base-agent-${ENVIRONMENT}"; then
    docker-compose -f "$COMPOSE_FILE" config > "${BACKUP_DIR}/docker-compose-backup.yml"
    log_info "✓ Configuration backed up to $BACKUP_DIR"
fi

# Pull latest images
log_info "Pulling latest images..."
if ! docker-compose -f "$COMPOSE_FILE" pull; then
    log_error "Failed to pull images"
    exit 1
fi
log_info "✓ Images pulled successfully"

# Stop existing services gracefully
if docker ps | grep -q "base-agent-${ENVIRONMENT}"; then
    log_info "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" down --timeout 30
    log_info "✓ Services stopped"
fi

# Start new deployment
log_info "Starting new deployment..."
if ! docker-compose -f "$COMPOSE_FILE" up -d; then
    log_error "Failed to start services"
    log_error "Attempting rollback..."
    bash "${SCRIPT_DIR}/rollback.sh" "$ENVIRONMENT"
    exit 1
fi
log_info "✓ Services started"

# Wait for services to be ready
log_info "Waiting for services to be ready..."
sleep 10

# Health checks
log_info "Running health checks..."
if ! bash "${SCRIPT_DIR}/health-check.sh" "$ENVIRONMENT"; then
    log_error "Health checks failed"
    log_error "Attempting rollback..."
    bash "${SCRIPT_DIR}/rollback.sh" "$ENVIRONMENT"
    exit 1
fi
log_info "✓ All health checks passed"

# Post-deployment validation
log_info "Running post-deployment validation..."

# Check container status
CONTAINERS=$(docker-compose -f "$COMPOSE_FILE" ps -q)
UNHEALTHY=0
for container in $CONTAINERS; do
    status=$(docker inspect --format='{{.State.Status}}' "$container")
    if [[ "$status" != "running" ]]; then
        log_error "Container $container is not running (status: $status)"
        UNHEALTHY=$((UNHEALTHY + 1))
    fi
done

if [[ $UNHEALTHY -gt 0 ]]; then
    log_error "$UNHEALTHY containers are not healthy"
    exit 1
fi
log_info "✓ All containers are running"

# Tag deployment for rollback reference
CURRENT_TAG=$(docker-compose -f "$COMPOSE_FILE" images -q app | head -1)
echo "$CURRENT_TAG" > "${BACKUP_DIR}/current-deployment.txt"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${BACKUP_DIR}/current-deployment.txt"

log_info "========================================="
log_info "Deployment to $ENVIRONMENT completed successfully!"
log_info "========================================="
log_info "Access points:"
case $ENVIRONMENT in
    dev)
        log_info "  - UI: http://localhost:8501"
        log_info "  - API: http://localhost:8058"
        ;;
    staging)
        log_info "  - UI: http://staging.example.com:8501"
        log_info "  - API: http://staging.example.com:8058"
        log_info "  - Grafana: http://staging.example.com:3000"
        ;;
    production)
        log_info "  - UI: https://app.example.com"
        log_info "  - API: https://api.example.com"
        log_info "  - Grafana: https://grafana.example.com"
        ;;
esac

log_info "Deployment log: $LOG_FILE"
log_info "Backup location: $BACKUP_DIR"

exit 0
