#!/bin/bash
#
# health_check.sh - Comprehensive system health verification
#
# Usage: ./health_check.sh [--json] [--quick]
#
# Checks:
#   - Python environment
#   - Configuration validity
#   - Database connections
#   - API endpoints (if running)
#   - Disk space and memory
#

set -euo pipefail

# Colors
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

JSON_OUTPUT=false
QUICK_MODE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--json] [--quick]"
            echo ""
            echo "Options:"
            echo "  --json   Output results as JSON"
            echo "  --quick  Skip slow checks (database, API)"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Results storage
declare -A RESULTS
OVERALL_STATUS="healthy"

check_pass() {
    local name="$1"
    local detail="${2:-}"
    RESULTS[$name]="pass"
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${GREEN}[PASS]${NC} $name"
        if [ -n "$detail" ]; then
            echo "       $detail"
        fi
    fi
}

check_warn() {
    local name="$1"
    local detail="${2:-}"
    RESULTS[$name]="warn"
    if [ "$OVERALL_STATUS" = "healthy" ]; then
        OVERALL_STATUS="degraded"
    fi
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${YELLOW}[WARN]${NC} $name"
        if [ -n "$detail" ]; then
            echo "       $detail"
        fi
    fi
}

check_fail() {
    local name="$1"
    local detail="${2:-}"
    RESULTS[$name]="fail"
    OVERALL_STATUS="unhealthy"
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${RED}[FAIL]${NC} $name"
        if [ -n "$detail" ]; then
            echo "       $detail"
        fi
    fi
}

if [ "$JSON_OUTPUT" = false ]; then
    echo "=================================="
    echo "Health Check - Agentic RAG"
    echo "=================================="
    echo ""
fi

# Load environment
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# === Python Environment ===
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "${BLUE}=== Python Environment ===${NC}"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
    check_pass "Python version" "Python $PYTHON_VERSION (>= 3.11 required)"
else
    check_fail "Python version" "Python $PYTHON_VERSION (>= 3.11 required)"
fi

# Check virtual environment
if [ -n "${VIRTUAL_ENV:-}" ]; then
    check_pass "Virtual environment" "Active: $VIRTUAL_ENV"
elif [ -d "${PROJECT_ROOT}/.venv" ]; then
    check_warn "Virtual environment" "Found but not activated"
else
    check_warn "Virtual environment" "Not found"
fi

# Check key packages
for pkg in streamlit pydantic-ai supabase; do
    if pip show "$pkg" &>/dev/null; then
        VERSION=$(pip show "$pkg" 2>/dev/null | grep "Version:" | cut -d" " -f2)
        check_pass "Package: $pkg" "Version: $VERSION"
    else
        check_fail "Package: $pkg" "Not installed"
    fi
done

if [ "$JSON_OUTPUT" = false ]; then
    echo ""
fi

# === Configuration ===
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "${BLUE}=== Configuration ===${NC}"
fi

# Check .env file
if [ -f "${PROJECT_ROOT}/.env" ]; then
    check_pass ".env file" "Found"
else
    check_fail ".env file" "Not found - copy from .env.example"
fi

# Check required variables
for var in LLM_API_KEY DATABASE_URL SUPABASE_URL; do
    if [ -n "${!var:-}" ]; then
        # Mask the value for display
        check_pass "Config: $var" "Set (masked)"
    else
        check_warn "Config: $var" "Not set"
    fi
done

# Validate config loading
if python3 -c "from src.config import get_settings; get_settings()" 2>/dev/null; then
    check_pass "Config validation" "Settings load successfully"
else
    check_fail "Config validation" "Settings failed to load"
fi

if [ "$JSON_OUTPUT" = false ]; then
    echo ""
fi

# === Database Connections (skip in quick mode) ===
if [ "$QUICK_MODE" = false ]; then
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${BLUE}=== Database Connections ===${NC}"
    fi

    # PostgreSQL
    if [ -n "${DATABASE_URL:-}" ]; then
        if python3 -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('${DATABASE_URL}', timeout=10)
    await conn.execute('SELECT 1')
    await conn.close()
asyncio.run(test())
" 2>/dev/null; then
            check_pass "PostgreSQL connection" "Connected successfully"
        else
            check_fail "PostgreSQL connection" "Connection failed"
        fi
    else
        check_warn "PostgreSQL connection" "DATABASE_URL not set"
    fi

    # Neo4j
    if [ -n "${NEO4J_URI:-}" ]; then
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
            check_pass "Neo4j connection" "Connected successfully"
        else
            check_fail "Neo4j connection" "Connection failed"
        fi
    else
        check_warn "Neo4j connection" "NEO4J_URI not set"
    fi

    if [ "$JSON_OUTPUT" = false ]; then
        echo ""
    fi
fi

# === API Endpoints ===
if [ "$QUICK_MODE" = false ]; then
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${BLUE}=== API Endpoints ===${NC}"
    fi

    # Check if API is running
    API_PORT="${API_PORT:-8058}"
    if curl -s "http://localhost:${API_PORT}/health" &>/dev/null; then
        check_pass "API server" "Running on port $API_PORT"

        # Check detailed health
        HEALTH_STATUS=$(curl -s "http://localhost:${API_PORT}/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
        if [ "$HEALTH_STATUS" = "healthy" ]; then
            check_pass "API health" "Status: $HEALTH_STATUS"
        else
            check_warn "API health" "Status: $HEALTH_STATUS"
        fi
    else
        check_warn "API server" "Not running (port $API_PORT)"
    fi

    # Check if UI is running
    UI_PORT="${STREAMLIT_SERVER_PORT:-8502}"
    if curl -s "http://localhost:${UI_PORT}/_stcore/health" &>/dev/null; then
        check_pass "Streamlit UI" "Running on port $UI_PORT"
    else
        check_warn "Streamlit UI" "Not running (port $UI_PORT)"
    fi

    if [ "$JSON_OUTPUT" = false ]; then
        echo ""
    fi
fi

# === System Resources ===
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "${BLUE}=== System Resources ===${NC}"
fi

# Disk space
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 80 ]; then
    check_pass "Disk space" "${DISK_USAGE}% used"
elif [ "$DISK_USAGE" -lt 90 ]; then
    check_warn "Disk space" "${DISK_USAGE}% used (low)"
else
    check_fail "Disk space" "${DISK_USAGE}% used (critical)"
fi

# Memory (if /proc/meminfo available)
if [ -f /proc/meminfo ]; then
    TOTAL_MEM=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    AVAIL_MEM=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
    MEM_PERCENT=$((100 - (AVAIL_MEM * 100 / TOTAL_MEM)))

    if [ "$MEM_PERCENT" -lt 80 ]; then
        check_pass "Memory" "${MEM_PERCENT}% used"
    elif [ "$MEM_PERCENT" -lt 90 ]; then
        check_warn "Memory" "${MEM_PERCENT}% used (high)"
    else
        check_fail "Memory" "${MEM_PERCENT}% used (critical)"
    fi
else
    check_warn "Memory" "Unable to check (no /proc/meminfo)"
fi

if [ "$JSON_OUTPUT" = false ]; then
    echo ""
fi

# === Summary ===
if [ "$JSON_OUTPUT" = true ]; then
    # Output JSON
    echo "{"
    echo "  \"status\": \"$OVERALL_STATUS\","
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"checks\": {"
    FIRST=true
    for key in "${!RESULTS[@]}"; do
        if [ "$FIRST" = true ]; then
            FIRST=false
        else
            echo ","
        fi
        printf "    \"%s\": \"%s\"" "$key" "${RESULTS[$key]}"
    done
    echo ""
    echo "  }"
    echo "}"
else
    echo "=================================="
    if [ "$OVERALL_STATUS" = "healthy" ]; then
        echo -e "${GREEN}Overall Status: HEALTHY${NC}"
    elif [ "$OVERALL_STATUS" = "degraded" ]; then
        echo -e "${YELLOW}Overall Status: DEGRADED${NC}"
    else
        echo -e "${RED}Overall Status: UNHEALTHY${NC}"
    fi
    echo "=================================="
fi

# Exit code based on status
case "$OVERALL_STATUS" in
    healthy) exit 0 ;;
    degraded) exit 0 ;;
    *) exit 1 ;;
esac
