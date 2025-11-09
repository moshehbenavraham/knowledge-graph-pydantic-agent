#!/bin/bash
# Coolify Pre-Deployment Checklist Script
# Verifies all prerequisites are met before deploying to Coolify

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
ERRORS=0
WARNINGS=0

echo "======================================"
echo "Coolify Pre-Deployment Checklist"
echo "======================================"
echo ""

# Function to print status
print_status() {
    local status=$1
    local message=$2

    if [ "$status" = "ok" ]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [ "$status" = "warn" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
        ((WARNINGS++))
    else
        echo -e "${RED}✗${NC} $message"
        ((ERRORS++))
    fi
}

# Check 1: Verify .env file exists and has required variables
echo "1. Checking environment configuration..."
if [ ! -f .env ]; then
    print_status "error" ".env file not found"
else
    print_status "ok" ".env file exists"

    # Check required variables
    REQUIRED_VARS=(
        "SUPABASE_URL"
        "SUPABASE_SERVICE_KEY"
        "DATABASE_URL"
        "NEO4J_URI"
        "NEO4J_USER"
        "NEO4J_PASSWORD"
        "LLM_PROVIDER"
        "LLM_API_KEY"
        "AUTH_COOKIE_KEY"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if ! grep -q "^${var}=" .env || grep -q "^${var}=$" .env || grep -q "^${var}=your_" .env; then
            print_status "error" "Missing or invalid: $var"
        else
            print_status "ok" "Configured: $var"
        fi
    done
fi
echo ""

# Check 2: Verify Docker files exist
echo "2. Checking Docker configuration..."
if [ -f docker/Dockerfile.production ]; then
    print_status "ok" "Production Dockerfile exists"
else
    print_status "error" "docker/Dockerfile.production not found"
fi

if [ -f docker/docker-compose.coolify.yml ]; then
    print_status "ok" "Coolify docker-compose.yml exists"
else
    print_status "error" "docker/docker-compose.coolify.yml not found"
fi
echo ""

# Check 3: Verify Neo4j connection (if credentials provided)
echo "3. Checking Neo4j Aura connection..."
if [ -f .env ] && grep -q "^NEO4J_URI=neo4j+s://" .env; then
    source .env
    if command -v python3 &> /dev/null; then
        python3 -c "
from neo4j import GraphDatabase
import sys
try:
    driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', '$NEO4J_PASSWORD'))
    driver.verify_connectivity()
    print('Neo4j connection successful')
    driver.close()
    sys.exit(0)
except Exception as e:
    print(f'Neo4j connection failed: {e}')
    sys.exit(1)
" && print_status "ok" "Neo4j Aura connection successful" || print_status "error" "Neo4j Aura connection failed"
    else
        print_status "warn" "Python3 not found, skipping Neo4j connection test"
    fi
else
    print_status "warn" "Neo4j URI not configured or not using encrypted connection"
fi
echo ""

# Check 4: Verify Supabase connection
echo "4. Checking Supabase connection..."
if [ -f .env ] && grep -q "^DATABASE_URL=" .env; then
    source .env
    if command -v psql &> /dev/null; then
        psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null && \
            print_status "ok" "Supabase connection successful" || \
            print_status "error" "Supabase connection failed"
    else
        print_status "warn" "psql not found, skipping Supabase connection test"
    fi
else
    print_status "warn" "DATABASE_URL not configured"
fi
echo ""

# Check 5: Verify SQL migrations exist
echo "5. Checking database migrations..."
MIGRATIONS=(
    "src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql"
    "src/agentic_rag/storage/migrations/sql/002_document_rows_table.sql"
    "src/agentic_rag/storage/migrations/sql/003_execute_sql_rpc.sql"
    "src/agentic_rag/storage/migrations/sql/004_analytics_schema.sql"
    "src/agentic_rag/storage/migrations/sql/005_auth_tables.sql"
)

for migration in "${MIGRATIONS[@]}"; do
    if [ -f "$migration" ]; then
        print_status "ok" "Migration exists: $(basename $migration)"
    else
        print_status "error" "Missing migration: $migration"
    fi
done
echo ""

# Check 6: Verify authentication configuration
echo "6. Checking authentication configuration..."
if [ -f .env ]; then
    source .env

    if [ -z "$AUTH_COOKIE_KEY" ]; then
        print_status "error" "AUTH_COOKIE_KEY not set"
        echo "   Generate with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    else
        key_length=${#AUTH_COOKIE_KEY}
        if [ $key_length -lt 32 ]; then
            print_status "warn" "AUTH_COOKIE_KEY is too short (${key_length} chars, recommend 32+)"
        else
            print_status "ok" "AUTH_COOKIE_KEY configured"
        fi
    fi

    if [ "$USE_DATABASE_AUTH" = "true" ]; then
        print_status "ok" "Database authentication enabled (production mode)"
    else
        print_status "warn" "Database authentication disabled (using YAML mode)"
    fi
fi
echo ""

# Check 7: Verify config files exist
echo "7. Checking configuration files..."
if [ -d config ]; then
    print_status "ok" "config/ directory exists"

    if [ -f config/auth_config.yaml ]; then
        print_status "ok" "auth_config.yaml exists"
    else
        print_status "warn" "auth_config.yaml not found (only needed for YAML auth mode)"
    fi
else
    print_status "error" "config/ directory not found"
fi
echo ""

# Check 8: Verify LLM provider configuration
echo "8. Checking LLM provider configuration..."
if [ -f .env ]; then
    source .env

    case "$LLM_PROVIDER" in
        "openai")
            if [ -z "$LLM_API_KEY" ] || [[ "$LLM_API_KEY" == "your_"* ]]; then
                print_status "error" "OpenAI API key not configured"
            else
                print_status "ok" "OpenAI configured"
            fi
            ;;
        "anthropic")
            if [ -z "$LLM_API_KEY" ] || [[ "$LLM_API_KEY" == "your_"* ]]; then
                print_status "error" "Anthropic API key not configured"
            else
                print_status "ok" "Anthropic configured"
            fi
            ;;
        "ollama")
            print_status "ok" "Ollama configured (ensure Ollama server is accessible)"
            ;;
        *)
            print_status "error" "Unknown LLM_PROVIDER: $LLM_PROVIDER"
            ;;
    esac
fi
echo ""

# Check 9: Verify embedding configuration
echo "9. Checking embedding configuration..."
if [ -f .env ]; then
    source .env

    if [ "$EMBEDDING_PROVIDER" = "openai" ]; then
        if [ "$EMBEDDING_DIMENSION" != "1536" ]; then
            print_status "warn" "EMBEDDING_DIMENSION should be 1536 for OpenAI"
        else
            print_status "ok" "OpenAI embedding dimension correct"
        fi
    elif [ "$EMBEDDING_PROVIDER" = "ollama" ]; then
        if [ "$EMBEDDING_DIMENSION" != "768" ]; then
            print_status "warn" "EMBEDDING_DIMENSION should be 768 for Ollama"
        else
            print_status "ok" "Ollama embedding dimension correct"
        fi
    fi
fi
echo ""

# Check 10: Verify feature flags for production
echo "10. Checking feature flags..."
if [ -f .env ]; then
    source .env

    if [ "$ENABLE_CODE_EXECUTION" = "true" ]; then
        print_status "warn" "Code execution enabled (consider disabling for production)"
    else
        print_status "ok" "Code execution disabled"
    fi

    if [ "$RATE_LIMIT_ENABLED" = "true" ]; then
        print_status "ok" "Rate limiting enabled"
    else
        print_status "warn" "Rate limiting disabled (recommend enabling for production)"
    fi
fi
echo ""

# Summary
echo "======================================"
echo "Summary"
echo "======================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Ready to deploy to Coolify.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ ${WARNINGS} warning(s) found. Review before deploying.${NC}"
    exit 0
else
    echo -e "${RED}✗ ${ERRORS} error(s) and ${WARNINGS} warning(s) found.${NC}"
    echo "Please fix errors before deploying to Coolify."
    exit 1
fi
