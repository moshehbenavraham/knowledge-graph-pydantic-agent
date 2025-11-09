#!/bin/bash
# Generate Coolify Environment Variables Template
# Creates a .env file ready for Coolify deployment

set -e

echo "======================================"
echo "Coolify Environment Generator"
echo "======================================"
echo ""
echo "This script will help you generate environment variables for Coolify deployment."
echo ""

# Output file
OUTPUT_FILE=".env.coolify"

# Check if file exists
if [ -f "$OUTPUT_FILE" ]; then
    echo "Warning: $OUTPUT_FILE already exists."
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Generate AUTH_COOKIE_KEY
echo "Generating AUTH_COOKIE_KEY..."
AUTH_COOKIE_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Generate OAUTH_ENCRYPTION_KEY (for future OAuth support)
echo "Generating OAUTH_ENCRYPTION_KEY..."
OAUTH_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create template
cat > "$OUTPUT_FILE" << 'EOF'
# ===== CORE DATABASE CONFIGURATION =====

# Supabase (PostgreSQL with pgvector)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Database URL (MUST use Session Pooler for Coolify compatibility)
DATABASE_URL=postgresql://postgres.xxxxx:your_password@aws-region.pooler.supabase.com:5432/postgres

# Neo4j Aura (Knowledge Graph)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_QUERY_API_URL=https://xxxxx.databases.neo4j.io/db/neo4j/query/v2
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j
NEO4J_ENCRYPTED=true

# ===== LLM CONFIGURATION =====

# Provider (openai, anthropic, ollama, openrouter)
LLM_PROVIDER=openai
LLM_API_KEY=sk-your_openai_api_key
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-your_openai_api_key
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# ===== AUTHENTICATION (REQUIRED FOR PRODUCTION) =====

USE_DATABASE_AUTH=true
EOF

# Add generated keys
echo "AUTH_COOKIE_KEY=$AUTH_COOKIE_KEY" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << 'EOF'

# Cookie Settings (adjust domain for your Coolify deployment)
AUTH_COOKIE_NAME=base_agent_auth
AUTH_COOKIE_EXPIRY_DAYS=30
AUTH_COOKIE_DOMAIN=your-app.yourdomain.com
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_HTTPONLY=true

# Session Settings
SESSION_IDLE_TIMEOUT_MINUTES=30
SESSION_ABSOLUTE_TIMEOUT_HOURS=24

# Password Reset (optional but recommended)
PASSWORD_RESET_URL=https://your-app.yourdomain.com/reset-password
EMAIL_ENABLED=false
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=noreply@baseagent.local

# ===== OAUTH AUTHENTICATION (OPTIONAL) =====

OAUTH_ENABLED=false
EOF

echo "OAUTH_ENCRYPTION_KEY=$OAUTH_ENCRYPTION_KEY" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" << 'EOF'

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://your-app.yourdomain.com

# GitHub OAuth
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=https://your-app.yourdomain.com

# ===== FEATURE FLAGS =====

ENABLE_RAG=true
ENABLE_AGENTIC_RAG=true
ENABLE_GRAPH_SEARCH=true
ENABLE_WEB_SEARCH=true
ENABLE_IMAGE_ANALYSIS=true
ENABLE_LONG_TERM_MEMORY=true
ENABLE_METRICS=true

# ===== WEB SEARCH (OPTIONAL) =====

JINA_API_KEY=
BRAVE_API_KEY=

# ===== LOGGING & MONITORING =====

LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_STRUCTURED_LOGGING=true

# ===== PERFORMANCE TUNING =====

# Connection Pooling
PG_POOL_MIN_SIZE=5
PG_POOL_MAX_SIZE=20
PG_POOL_TIMEOUT=10.0

# Neo4j Connection Pooling
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT=30.0

# Search Configuration
VECTOR_SEARCH_LIMIT=10
GRAPH_SEARCH_LIMIT=10
HYBRID_SEARCH_ALPHA=0.7

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# ===== UI CONFIGURATION =====

UI_MODE=advanced
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# ===== API CONFIGURATION (IF DEPLOYING API SERVICE) =====

API_HOST=0.0.0.0
API_PORT=8058
API_WORKERS=4
API_RELOAD=false
EOF

echo ""
echo "======================================"
echo "✓ Environment file generated: $OUTPUT_FILE"
echo "======================================"
echo ""
echo "IMPORTANT: Generated secure keys:"
echo "  - AUTH_COOKIE_KEY: $AUTH_COOKIE_KEY"
echo "  - OAUTH_ENCRYPTION_KEY: $OAUTH_ENCRYPTION_KEY"
echo ""
echo "Next steps:"
echo "1. Edit $OUTPUT_FILE and fill in your actual values:"
echo "   - Supabase credentials"
echo "   - Neo4j Aura credentials"
echo "   - LLM API keys"
echo "   - Update domain names"
echo "2. Run: ./scripts/coolify-pre-deploy-check.sh"
echo "3. Copy contents to Coolify Environment Variables (Bulk Edit)"
echo ""
echo "SECURITY NOTE: Keep this file secure and never commit to Git!"
echo ""
