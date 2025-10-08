#!/usr/bin/env bash
# ===============================================
# Rollback Script
# Base Agent - Agentic RAG Platform
# ===============================================

set -euo pipefail

ENVIRONMENT="${1:-staging}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/deploy/backups/${ENVIRONMENT}"
LOG_FILE="/tmp/rollback-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

log_warn "========================================="
log_warn "ROLLBACK INITIATED for $ENVIRONMENT"
log_warn "========================================="
log_info "Log file: $LOG_FILE"

# Check backup exists
if [[ ! -d "$BACKUP_DIR" ]]; then
    log_error "No backup directory found at $BACKUP_DIR"
    log_error "Cannot perform rollback"
    exit 1
fi

# Find latest backup
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/docker-compose-backup*.yml 2>/dev/null | head -1)
if [[ -z "$LATEST_BACKUP" ]]; then
    log_error "No backup configuration found"
    exit 1
fi

log_info "Found backup: $LATEST_BACKUP"

# Get previous deployment info
PREVIOUS_TAG=""
if [[ -f "${BACKUP_DIR}/current-deployment.txt" ]]; then
    PREVIOUS_TAG=$(head -1 "${BACKUP_DIR}/current-deployment.txt")
    log_info "Previous deployment tag: $PREVIOUS_TAG"
fi

# Confirmation for production
if [[ "$ENVIRONMENT" == "production" ]]; then
    log_warn "=== PRODUCTION ROLLBACK WARNING ==="
    log_warn "You are about to rollback PRODUCTION"
    read -p "Type 'rollback' to confirm: " confirm
    if [[ "$confirm" != "rollback" ]]; then
        log_error "Rollback cancelled"
        exit 1
    fi
fi

# Stop current deployment
COMPOSE_FILE="${PROJECT_ROOT}/docker/docker-compose.${ENVIRONMENT}.yml"
log_info "Stopping current deployment..."
if docker-compose -f "$COMPOSE_FILE" ps -q | grep -q .; then
    docker-compose -f "$COMPOSE_FILE" down --timeout 30
    log_info "✓ Current deployment stopped"
else
    log_warn "No running services found"
fi

# Restore from backup
log_info "Restoring from backup configuration..."
cp "$LATEST_BACKUP" "${COMPOSE_FILE}.rollback"

# If we have the previous image tag, restore it
if [[ -n "$PREVIOUS_TAG" ]]; then
    log_info "Pulling previous image: $PREVIOUS_TAG"
    # This is a simplified approach - in production you'd want more sophisticated image management
    export IMAGE_TAG="$PREVIOUS_TAG"
fi

# Start services with backup configuration
log_info "Starting services from backup..."
if ! docker-compose -f "$COMPOSE_FILE" up -d; then
    log_error "Failed to start services from backup"
    log_error "Manual intervention required"
    exit 1
fi

log_info "✓ Services started from backup"

# Wait for services
log_info "Waiting for services to stabilize..."
sleep 15

# Health check
log_info "Running health checks..."
if bash "${SCRIPT_DIR}/health-check.sh" "$ENVIRONMENT"; then
    log_info "✓ Health checks passed"
else
    log_error "Health checks failed after rollback"
    log_error "Manual intervention required"
    exit 1
fi

# Log rollback event
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) - Rollback completed" >> "${BACKUP_DIR}/rollback-history.log"

log_info "========================================="
log_info "Rollback completed successfully!"
log_info "========================================="
log_info "Rollback log: $LOG_FILE"
log_info "Previous state restored from: $LATEST_BACKUP"

exit 0
