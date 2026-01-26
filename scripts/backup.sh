#!/bin/bash
# Database Backup Script for Knowledge Graph Pydantic Agent
# Supports PostgreSQL (Supabase) and Neo4j Aura exports
# Usage: ./scripts/backup.sh [--postgres-only|--neo4j-only] [--upload]

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

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

# Parse arguments
POSTGRES_ONLY=false
NEO4J_ONLY=false
UPLOAD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --postgres-only)
            POSTGRES_ONLY=true
            shift
            ;;
        --neo4j-only)
            NEO4J_ONLY=true
            shift
            ;;
        --upload)
            UPLOAD=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --postgres-only  Only backup PostgreSQL (Supabase)"
            echo "  --neo4j-only     Only backup Neo4j (export entities/relationships)"
            echo "  --upload         Upload to cloud storage (requires R2/S3 config)"
            echo "  --help           Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  DATABASE_URL           PostgreSQL connection string"
            echo "  NEO4J_URI              Neo4j connection URI"
            echo "  NEO4J_USER             Neo4j username"
            echo "  NEO4J_PASSWORD         Neo4j password"
            echo "  BACKUP_DIR             Backup directory (default: ./backups)"
            echo "  BACKUP_RETENTION_DAYS  Days to keep backups (default: 7)"
            echo "  R2_ENDPOINT            Cloudflare R2 endpoint (optional)"
            echo "  R2_ACCESS_KEY_ID       R2 access key (optional)"
            echo "  R2_SECRET_ACCESS_KEY   R2 secret key (optional)"
            echo "  R2_BUCKET              R2 bucket name (optional)"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Load environment variables from .env if present
if [[ -f .env ]]; then
    log_info "Loading environment from .env file"
    set -a
    source .env
    set +a
fi

# PostgreSQL Backup (Supabase)
backup_postgres() {
    log_info "Starting PostgreSQL backup..."

    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_error "DATABASE_URL not set. Skipping PostgreSQL backup."
        return 1
    fi

    local backup_file="$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"

    # Check if pg_dump is available
    if ! command -v pg_dump &> /dev/null; then
        log_warn "pg_dump not found. Installing postgresql-client..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y postgresql-client
        elif command -v brew &> /dev/null; then
            brew install postgresql
        else
            log_error "Cannot install postgresql-client. Please install manually."
            return 1
        fi
    fi

    # Export specific tables (documents, analytics, auth)
    log_info "Exporting PostgreSQL tables to $backup_file"

    pg_dump "$DATABASE_URL" \
        --no-owner \
        --no-privileges \
        --clean \
        --if-exists \
        --format=plain \
        --table='public.documents' \
        --table='public.document_metadata' \
        --table='public.document_rows' \
        --table='public.search_analytics' \
        --table='public.tool_usage_analytics' \
        --table='public.agent_interactions' \
        --table='public.auth_users' \
        --table='public.auth_sessions' \
        2>/dev/null | gzip > "$backup_file"

    if [[ -f "$backup_file" ]]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "PostgreSQL backup complete: $backup_file ($size)"
        return 0
    else
        log_error "PostgreSQL backup failed"
        return 1
    fi
}

# Neo4j Backup (Entity/Relationship export)
backup_neo4j() {
    log_info "Starting Neo4j knowledge graph export..."

    if [[ -z "${NEO4J_URI:-}" ]] || [[ -z "${NEO4J_USER:-}" ]] || [[ -z "${NEO4J_PASSWORD:-}" ]]; then
        log_error "Neo4j credentials not set. Skipping Neo4j backup."
        return 1
    fi

    local backup_file="$BACKUP_DIR/neo4j_${TIMESTAMP}.cypher.gz"

    # Check if cypher-shell is available, otherwise use Python script
    if command -v cypher-shell &> /dev/null; then
        log_info "Exporting Neo4j data via cypher-shell to $backup_file"

        # Export all nodes and relationships
        cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
            --format plain <<EOF | gzip > "$backup_file"
// Export all Entity nodes
CALL apoc.export.cypher.query(
    "MATCH (n:Entity) RETURN n",
    null,
    {format: 'cypher-shell', stream: true}
) YIELD cypherStatements
RETURN cypherStatements;

// Export all relationships
CALL apoc.export.cypher.query(
    "MATCH ()-[r]->() RETURN r",
    null,
    {format: 'cypher-shell', stream: true}
) YIELD cypherStatements
RETURN cypherStatements;
EOF
    else
        log_info "cypher-shell not available. Using Python export..."

        # Use Python script for Neo4j export
        python3 << 'PYTHON_SCRIPT'
import os
import gzip
import json
from datetime import datetime

try:
    from neo4j import GraphDatabase
except ImportError:
    print("neo4j driver not installed. Run: pip install neo4j")
    exit(1)

uri = os.environ.get("NEO4J_URI")
user = os.environ.get("NEO4J_USER")
password = os.environ.get("NEO4J_PASSWORD")
backup_dir = os.environ.get("BACKUP_DIR", "./backups")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

driver = GraphDatabase.driver(uri, auth=(user, password))

with driver.session() as session:
    # Export entities
    entities = session.run("""
        MATCH (e:Entity)
        RETURN e.name AS name, e.entity_type AS type,
               e.description AS description, e.document_refs AS refs,
               e.mention_count AS mentions, e.created_at AS created
    """).data()

    # Export relationships
    relationships = session.run("""
        MATCH (s:Entity)-[r]->(t:Entity)
        RETURN s.name AS source, type(r) AS relationship,
               t.name AS target, properties(r) AS props
    """).data()

driver.close()

export_data = {
    "exported_at": timestamp,
    "entity_count": len(entities),
    "relationship_count": len(relationships),
    "entities": entities,
    "relationships": relationships
}

backup_file = f"{backup_dir}/neo4j_{timestamp}.json.gz"
with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
    json.dump(export_data, f, indent=2, default=str)

print(f"Neo4j export complete: {backup_file}")
print(f"  Entities: {len(entities)}")
print(f"  Relationships: {len(relationships)}")
PYTHON_SCRIPT
    fi

    log_info "Neo4j backup complete"
    return 0
}

# Upload to cloud storage (Cloudflare R2 or S3-compatible)
upload_to_cloud() {
    if [[ -z "${R2_ENDPOINT:-}" ]] || [[ -z "${R2_ACCESS_KEY_ID:-}" ]] || [[ -z "${R2_SECRET_ACCESS_KEY:-}" ]]; then
        log_warn "Cloud storage not configured. Skipping upload."
        return 0
    fi

    log_info "Uploading backups to cloud storage..."

    # Install AWS CLI if needed
    if ! command -v aws &> /dev/null; then
        log_warn "AWS CLI not found. Please install for cloud upload support."
        return 1
    fi

    local bucket="${R2_BUCKET:-kgpa-backups}"

    # Configure AWS CLI for R2
    export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"

    # Upload today's backups
    for file in "$BACKUP_DIR"/*_${TIMESTAMP}*; do
        if [[ -f "$file" ]]; then
            local filename=$(basename "$file")
            log_info "Uploading $filename to s3://$bucket/"
            aws s3 cp "$file" "s3://$bucket/$filename" \
                --endpoint-url "$R2_ENDPOINT" \
                --only-show-errors
        fi
    done

    log_info "Cloud upload complete"
}

# Clean old backups
cleanup_old_backups() {
    log_info "Cleaning backups older than $RETENTION_DAYS days..."

    find "$BACKUP_DIR" -type f -name "*.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

    local remaining=$(find "$BACKUP_DIR" -type f -name "*.gz" | wc -l)
    log_info "Remaining backup files: $remaining"
}

# Main execution
main() {
    log_info "========================================"
    log_info "Knowledge Graph Pydantic Agent Database Backup"
    log_info "Timestamp: $TIMESTAMP"
    log_info "Backup directory: $BACKUP_DIR"
    log_info "========================================"

    local success=true

    # Run backups based on flags
    if [[ "$NEO4J_ONLY" == "false" ]]; then
        backup_postgres || success=false
    fi

    if [[ "$POSTGRES_ONLY" == "false" ]]; then
        backup_neo4j || success=false
    fi

    # Upload if requested
    if [[ "$UPLOAD" == "true" ]]; then
        upload_to_cloud
    fi

    # Cleanup old backups
    cleanup_old_backups

    log_info "========================================"
    if [[ "$success" == "true" ]]; then
        log_info "Backup completed successfully"
    else
        log_warn "Backup completed with some failures"
    fi
    log_info "========================================"

    # List backup files
    log_info "Backup files:"
    ls -lh "$BACKUP_DIR"/*.gz 2>/dev/null || log_warn "No backup files found"
}

main "$@"
