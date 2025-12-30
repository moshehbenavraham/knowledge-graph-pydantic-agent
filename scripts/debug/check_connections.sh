#!/bin/bash
#
# check_connections.sh - Test connectivity to all external services
#
# Usage: ./check_connections.sh [--verbose]
#
# Tests:
#   - PostgreSQL (Supabase)
#   - Neo4j (Aura)
#   - OpenAI API
#   - Optional services
#

set -euo pipefail

# Colors (only if terminal supports it)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

VERBOSE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Usage: $0 [--verbose]"
            exit 1
            ;;
    esac
done

# Load environment
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/.env"
    set +a
fi

log_info() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo "     $1"
    fi
}

echo "=================================="
echo "Connection Check - Agentic RAG"
echo "=================================="
echo ""

FAILED=0

# Check PostgreSQL/Supabase
echo "Checking PostgreSQL (Supabase)..."
if [ -n "${DATABASE_URL:-}" ]; then
    # Extract host from DATABASE_URL
    DB_HOST=$(echo "$DATABASE_URL" | sed -E 's/.*@([^:\/]+).*/\1/')
    if command -v nc &> /dev/null; then
        if nc -z -w 5 "$DB_HOST" 5432 2>/dev/null; then
            log_info "PostgreSQL port reachable at $DB_HOST:5432"
        elif nc -z -w 5 "$DB_HOST" 6543 2>/dev/null; then
            log_info "PostgreSQL pooler reachable at $DB_HOST:6543"
        else
            log_error "PostgreSQL not reachable at $DB_HOST"
            FAILED=$((FAILED + 1))
        fi
    else
        log_warn "nc not installed, skipping port check"
    fi

    # Test actual connection via Python
    if python3 -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('${DATABASE_URL}', timeout=10)
    await conn.execute('SELECT 1')
    await conn.close()
asyncio.run(test())
" 2>/dev/null; then
        log_info "PostgreSQL connection successful"
    else
        log_error "PostgreSQL connection failed"
        FAILED=$((FAILED + 1))
    fi
else
    log_warn "DATABASE_URL not set, skipping PostgreSQL check"
fi

echo ""

# Check Neo4j
echo "Checking Neo4j (Aura)..."
if [ -n "${NEO4J_URI:-}" ]; then
    # Extract host from NEO4J_URI
    NEO4J_HOST=$(echo "$NEO4J_URI" | sed -E 's/.*\/\/([^:\/]+).*/\1/')
    log_verbose "Neo4j host: $NEO4J_HOST"

    # Test connection via Python
    if python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver(
    '${NEO4J_URI}',
    auth=('${NEO4J_USER:-neo4j}', '${NEO4J_PASSWORD:-}')
)
with driver.session() as session:
    session.run('RETURN 1')
driver.close()
" 2>/dev/null; then
        log_info "Neo4j connection successful"
    else
        log_error "Neo4j connection failed"
        log_verbose "Check if instance is paused at https://neo4j.com/cloud/aura-free"
        FAILED=$((FAILED + 1))
    fi
else
    log_warn "NEO4J_URI not set, skipping Neo4j check"
fi

echo ""

# Check OpenAI API
echo "Checking OpenAI API..."
if [ -n "${LLM_API_KEY:-}" ]; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer ${LLM_API_KEY}" \
        "https://api.openai.com/v1/models" 2>/dev/null || echo "000")

    if [ "$HTTP_STATUS" = "200" ]; then
        log_info "OpenAI API accessible"
    elif [ "$HTTP_STATUS" = "401" ]; then
        log_error "OpenAI API key invalid"
        FAILED=$((FAILED + 1))
    else
        log_error "OpenAI API unreachable (HTTP $HTTP_STATUS)"
        FAILED=$((FAILED + 1))
    fi
else
    log_warn "LLM_API_KEY not set, skipping OpenAI check"
fi

echo ""

# Check Supabase REST API
echo "Checking Supabase REST API..."
if [ -n "${SUPABASE_URL:-}" ]; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "apikey: ${SUPABASE_SERVICE_KEY:-}" \
        "${SUPABASE_URL}/rest/v1/" 2>/dev/null || echo "000")

    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "401" ]; then
        log_info "Supabase REST API reachable"
    else
        log_error "Supabase REST API unreachable (HTTP $HTTP_STATUS)"
        FAILED=$((FAILED + 1))
    fi
else
    log_warn "SUPABASE_URL not set, skipping Supabase REST check"
fi

echo ""

# Summary
echo "=================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All connection checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED connection check(s) failed${NC}"
    exit 1
fi
