# Coolify Deployment Guide

## Overview

This guide covers deploying Knowledge Graph Pydantic Agent (KGPA) to Coolify using external managed database services (Neo4j Aura + Supabase). This approach provides:

- **Simplified infrastructure**: No need to manage database containers in Coolify
- **Managed backups**: Both Neo4j Aura and Supabase provide automatic backups
- **Better performance**: Dedicated database infrastructure optimized by providers
- **Cost-effective**: Free tiers available for both services during development
- **Production-ready**: Enterprise-grade databases with monitoring and scaling

### Architecture

```
Coolify Server
 KGPA Container (Streamlit UI on 8501)
    Connects to -> Supabase PostgreSQL (vector embeddings + user data)
    Connects to -> Neo4j Aura (knowledge graph)
 Optional: FastAPI Container (API on 8058)
```

**External Services Required**:
- **Supabase**: PostgreSQL with pgvector extension (document storage, vectors, auth)
- **Neo4j Aura**: Managed graph database (knowledge graph, entities, relationships)

---

## Prerequisites

### 1. Coolify Server
- Coolify installed and accessible
- Minimum 8GB RAM allocated for the application
- Docker support enabled
- Public domain or subdomain configured (for HTTPS)

### 2. Neo4j Aura Account
- Sign up at https://neo4j.com/cloud/aura/
- Create a free instance (or paid if production):
  - Instance name: `kgpa-graph`
  - Region: Choose closest to your Coolify server
  - Database version: 5.13 or later
- **Save credentials immediately** (only shown once):
  - Connection URI: `neo4j+s://xxxxx.databases.neo4j.io`
  - Username: `neo4j`
  - Password: `[generated-password]`
  - Query API URL: `https://xxxxx.databases.neo4j.io/db/neo4j/query/v2`

### 3. Supabase Account
- Sign up at https://supabase.com
- Create a new project:
  - Project name: `kgpa`
  - Database password: **Strong password** (save securely)
  - Region: Choose closest to your Coolify server
- Navigate to Project Settings -> Database
- **Save connection details**:
  - Project URL: `https://xxxxx.supabase.co`
  - Service Role Key: Settings -> API -> `service_role` secret
  - Database URL (Session Pooler): Settings -> Database -> Connection Pooling
    - **Use Session mode** for compatibility with WSL2/Coolify
    - Format: `postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-[REGION].pooler.supabase.com:5432/postgres`

### 4. LLM Provider API Keys
- **OpenAI** (recommended): https://platform.openai.com/api-keys
  - Used for: LLM, embeddings, vision (OCR)
  - Model: `gpt-4o-mini` (default)
  - Embedding: `text-embedding-3-small` (1536 dimensions)
- **Anthropic** (alternative): https://console.anthropic.com/
  - Model: `claude-3-5-sonnet-20241022`
- **Ollama** (self-hosted): Configure endpoint if running locally

### 5. Optional Service API Keys
- **Jina AI**: https://jina.ai/ (web search)
- **Brave Search**: https://brave.com/search/api/ (web search fallback)

---

## Pre-Deployment Steps

### Step 1: Apply Supabase Database Migrations

**Connect to Supabase SQL Editor** (Dashboard -> SQL Editor):

Run each migration in order:

**1. Enable pgvector extension**:
```sql
-- 001_vector_extension.sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**2. Create documents tables**:
```sql
-- 002_documents_table.sql
-- Copy contents from: sql/002_documents_table.sql
-- Creates: documents, document_metadata, document_rows tables
```

**3. Create search functions**:
```sql
-- 003_search_functions.sql
-- Copy contents from: sql/003_search_functions.sql
-- Creates: execute_readonly_sql RPC function
```

**4. Create analytics tables** (v1.1.0+):
```sql
-- 004_analytics_schema.sql
-- Copy contents from: src/agentic_rag/storage/migrations/sql/004_analytics_schema.sql
-- Creates: search_analytics, tool_usage_analytics, agent_interactions, system_metrics tables
```

**5. Create authentication tables** (v1.5.0+ - REQUIRED for production):
```sql
-- 005_auth_tables.sql
-- Copy contents from: src/agentic_rag/storage/migrations/sql/005_auth_tables.sql
-- Creates: auth_users, auth_sessions, auth_password_reset_tokens, auth_roles, auth_user_roles
```

**6. Add email verification** (v1.6.0+):
```sql
-- 006_email_verification.sql
-- Copy contents from: src/agentic_rag/storage/migrations/sql/006_email_verification.sql
```

**7. Add 2FA and password history** (v1.7.0+):
```sql
-- 007_2fa_and_password_history.sql
-- Copy contents from: src/agentic_rag/storage/migrations/sql/007_2fa_and_password_history.sql
```

**8. Add OAuth tables** (v1.8.0+):
```sql
-- 008_oauth_accounts.sql
-- Copy contents from: src/agentic_rag/storage/migrations/sql/008_oauth_accounts.sql
-- Creates: auth_oauth_accounts table for Google/GitHub OAuth
```

**Verify migrations**:
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Should see: documents, document_metadata, document_rows,
-- search_analytics, auth_users, auth_sessions, etc.
```

### Step 2: Initialize Neo4j Graph Schema

**Using Neo4j Browser** (Aura Console -> Open):

```cypher
// Create Graphiti schema
CREATE CONSTRAINT entity_uuid IF NOT EXISTS FOR (e:Entity) REQUIRE e.uuid IS UNIQUE;
CREATE CONSTRAINT episode_uuid IF NOT EXISTS FOR (e:Episode) REQUIRE e.uuid IS UNIQUE;
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX episode_created_at IF NOT EXISTS FOR (e:Episode) ON (e.created_at);
```

**Verify**:
```cypher
SHOW CONSTRAINTS;
SHOW INDEXES;
```

### Step 3: Generate Authentication Cookie Key

**On your local machine**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Save the output** - this is your `AUTH_COOKIE_KEY` (keep it secret).

### Step 4: Create Initial Admin User

**After first deployment**, you'll create the admin user via CLI (see Post-Deployment section).

For now, prepare:
- Admin username
- Admin email
- Admin password (strong, 12+ characters)

### Step 5: Prepare Environment Variables

Create a `.env` file locally with all required variables (you'll paste this into Coolify):

```bash
# === CORE DATABASE CONFIGURATION ===

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

# === LLM CONFIGURATION ===

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

# === AUTHENTICATION (REQUIRED FOR PRODUCTION) ===

USE_DATABASE_AUTH=true
AUTH_COOKIE_KEY=your_generated_32_char_key_from_step_3

# Cookie Settings (adjust domain for your Coolify deployment)
AUTH_COOKIE_NAME=kgpa_auth
AUTH_COOKIE_EXPIRY_DAYS=30
AUTH_COOKIE_DOMAIN=your-app.yourdomain.com
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_HTTPONLY=true

# Session Settings
SESSION_IDLE_TIMEOUT_MINUTES=30
SESSION_ABSOLUTE_TIMEOUT_HOURS=24

# Password Reset (optional but recommended)
PASSWORD_RESET_URL=https://your-app.yourdomain.com/reset-password
EMAIL_ENABLED=false  # Set to true if configuring email
EMAIL_PROVIDER=smtp  # smtp, sendgrid, mailgun
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=noreply@kgpa.local

# === FEATURE FLAGS ===

ENABLE_RAG=true
ENABLE_AGENTIC_RAG=true
ENABLE_GRAPH_SEARCH=true
ENABLE_WEB_SEARCH=true
ENABLE_IMAGE_ANALYSIS=true
ENABLE_LONG_TERM_MEMORY=true
ENABLE_METRICS=true

# === WEB SEARCH (OPTIONAL) ===

JINA_API_KEY=your_jina_api_key_optional
BRAVE_API_KEY=your_brave_api_key_optional

# === LOGGING & MONITORING ===

LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_STRUCTURED_LOGGING=true

# === PERFORMANCE TUNING ===

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

# === UI CONFIGURATION ===

UI_MODE=advanced  # simple, standard, advanced
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# === API CONFIGURATION (IF DEPLOYING API SERVICE) ===

API_HOST=0.0.0.0
API_PORT=8058
API_WORKERS=4
API_RELOAD=false
```

**Save this file** - you'll copy/paste it into Coolify.

---

## Coolify Deployment Process

### Step 1: Create New Resource in Coolify

1. Log into your Coolify dashboard
2. Click **+ New** -> **Resource** -> **Docker Compose**
3. Select your server and destination

### Step 2: Configure Resource

**General Settings**:
- **Name**: `kgpa-ui`
- **Description**: `Knowledge Graph Pydantic Agent - Agentic RAG System (Streamlit UI)`
- **Domain**: Configure your domain (e.g., `kgpa.yourdomain.com`)
  - Enable HTTPS (Let's Encrypt automatic)
  - Enable Force HTTPS redirect

**Build Configuration**:
- **Build Pack**: Dockerfile
- **Dockerfile Location**: `docker/Dockerfile.production`
- **Build Context**: `.` (project root)
- **Docker Build Target**: `runtime` (for UI service)
- **Docker Build Arguments**: Leave empty (uses ENV vars)

**Port Configuration**:
- **Public Port**: `8501` (mapped to container 8501)
- **Protocol**: HTTP
- Click **+ Add Port** if deploying API:
  - Public: `8058` -> Container: `8058` (API service)

**Health Check**:
- **Enable Health Check**:
- **Health Check Method**: HTTP
- **Health Check Path**: `/_stcore/health`
- **Health Check Port**: `8501`
- **Health Check Interval**: `30s`
- **Health Check Timeout**: `10s`
- **Health Check Start Period**: `40s`
- **Health Check Retries**: `3`

**Resource Limits**:
- **Memory Limit**: `8192 MB` (8GB minimum for full RAG)
- **CPU Limit**: `4.0` (4 cores recommended)
- **Memory Reservation**: `4096 MB` (4GB)

### Step 3: Configure Environment Variables

Click **Environment Variables** tab -> **Bulk Edit** -> Paste your `.env` contents from Step 5.

**Critical variables to verify**:
- `DATABASE_URL` - Must use **Session Pooler** URL
- `NEO4J_URI` - Must use `neo4j+s://` (encrypted)
- `AUTH_COOKIE_KEY` - Must be set and unique
- `AUTH_COOKIE_DOMAIN` - Must match your Coolify domain
- `LLM_API_KEY` - Must be valid

**Security best practice**: Mark sensitive variables as "Secret" (lock icon):
- `SUPABASE_SERVICE_KEY`
- `NEO4J_PASSWORD`
- `LLM_API_KEY`
- `AUTH_COOKIE_KEY`
- `SMTP_PASSWORD`
- All other `*_API_KEY` variables

### Step 4: Configure Persistent Storage (Optional)

If you want to persist logs or uploaded files:

Click **Persistent Storage** tab -> **+ Add Volume**:
- **Name**: `kgpa-logs`
- **Mount Path**: `/app/logs`
- **Size**: `5GB`

Add another volume for uploaded files:
- **Name**: `kgpa-data`
- **Mount Path**: `/app/data`
- **Size**: `10GB`

### Step 5: Deploy

1. Click **Deploy** button (top right)
2. Monitor build logs in real-time
3. **Expected build time**: 5-8 minutes
   - Stage 1: Installing dependencies (~5 minutes for RAG extra)
   - Stage 2: Copying files and setting up runtime (~30 seconds)
4. **Expected startup time**: 40 seconds
   - Streamlit initialization
   - Database connection pooling
   - Health check warmup

### Step 6: Verify Deployment

**Check build logs**:
```
Successfully built <image-id>
Successfully tagged <image-name>
Container started: kgpa-ui
```

**Check health status**:
- Coolify UI should show **Healthy** (green indicator)
- If unhealthy, check logs for errors

**Access application**:
- Navigate to your configured domain: `https://kgpa.yourdomain.com`
- You should see the KGPA login page

---

## Post-Deployment

### Step 1: Create Initial Admin User

**Using Coolify shell access**:

1. In Coolify UI, click **Terminal** (console icon)
2. Run the user creation command:

```bash
python -m src.auth.db_cli create \
  --username admin \
  --email admin@yourdomain.com \
  --name "Admin User" \
  --password "YourStrongPassword123!" \
  --role admin
```

**Expected output**:
```
User 'admin' created successfully!
User ID: <uuid>
Email: admin@yourdomain.com
Role: admin
```

### Step 2: Test Authentication

1. Navigate to your domain
2. Enter admin credentials
3. Click **Login**
4. Should redirect to main chat interface

**If login fails**:
- Check Coolify logs: `grep "Authentication"`
- Verify `AUTH_COOKIE_DOMAIN` matches your actual domain
- Check `USE_DATABASE_AUTH=true` is set
- Verify database migrations ran successfully

### Step 3: Verify Database Connectivity

**Test PostgreSQL/Supabase**:
1. In chat interface, try a SQL query:
   - Message: "Show me all tables in the database"
   - Tool should call `sql_query` and return table list
2. Expected: Should see `documents`, `auth_users`, `search_analytics`, etc.

**Test Neo4j**:
1. In chat interface, ask a knowledge graph question:
   - Message: "What entities are in the knowledge graph?"
   - Should trigger graph search
2. Expected: May be empty initially (until you ingest documents)

### Step 4: Initialize Knowledge Graph

**Run initial graph initialization** (if not done in pre-deployment):

```bash
# In Coolify terminal
make neo4j-init
```

**Expected output**:
```
Connecting to Neo4j...
Creating Graphiti schema...
Constraints created: 2
Indexes created: 2
Neo4j initialization complete!
```

### Step 5: Test Core Features

**Test RAG (if you have documents)**:
1. Upload a document via UI (Upload button in sidebar)
2. Ask a question about the document
3. Should retrieve relevant chunks and answer

**Test Web Search** (if enabled):
1. Ask: "What's the latest news about AI?"
2. Should call web search tool (Jina or Brave)
3. Returns recent results

**Test Image Analysis** (if enabled):
1. Upload an image
2. Ask: "What's in this image?"
3. Should use vision model (gpt-4o-mini)

**Test Memory** (if enabled):
1. Say: "Remember my favorite color is blue"
2. New session: Ask "What's my favorite color?"
3. Should recall from long-term memory

### Step 6: Configure Monitoring (Optional)

**Prometheus Metrics**:
1. Add another port in Coolify: `8000` -> `8000`
2. Access metrics: `https://kgpa.yourdomain.com:8000/metrics`
3. Use with Grafana or other monitoring tools

**Structured Logging**:
- Logs are JSON formatted (LOG_FORMAT=json)
- View in Coolify: **Logs** tab
- Filter by level: `grep '"level":"error"'`
- Filter by component: `grep '"handler":"StreamingHandler"'`

### Step 7: Configure Backups

**Supabase backups** (automatic):
- Free tier: Daily backups (7 day retention)
- Pro tier: Point-in-time recovery
- Settings -> Database -> Backups

**Neo4j Aura backups** (automatic):
- Free tier: Daily backups (7 day retention)
- Professional: Configurable schedule
- Aura Console -> Backups

**Application data backups** (if using persistent volumes):
```bash
# In Coolify, schedule backup task
docker run --rm \
  -v kgpa-data:/data \
  -v /backup:/backup \
  alpine tar czf /backup/kgpa-data-$(date +%Y%m%d).tar.gz /data
```

---

## Troubleshooting

### Deployment Fails to Start

**Symptom**: Container exits immediately after starting

**Check logs** (Coolify -> Logs):
```bash
# Look for these errors:
grep -i "error\|failed\|exception"
```

**Common causes**:

1. **Missing environment variables**:
   ```
   Error: LLM_API_KEY is required when LLM_PROVIDER=openai
   ```
   **Fix**: Add missing variable in Coolify Environment Variables

2. **Invalid DATABASE_URL**:
   ```
   Error: Could not connect to PostgreSQL
   ```
   **Fix**:
   - Verify URL uses Session Pooler (not Transaction)
   - Check password has no special chars needing escaping
   - Test connection from Coolify terminal: `psql $DATABASE_URL -c "\dt"`

3. **Neo4j connection failed**:
   ```
   Error: Failed to connect to Neo4j
   ```
   **Fix**:
   - Verify `NEO4J_URI` uses `neo4j+s://` (not `neo4j://`)
   - Check Neo4j Aura instance is running
   - Verify credentials are correct
   - Test: `python -c "from neo4j import GraphDatabase; GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', '$NEO4J_PASSWORD')).verify_connectivity()"`

### Health Check Failing

**Symptom**: Coolify shows "Unhealthy" status

**Check health endpoint directly**:
```bash
# In Coolify terminal
curl http://localhost:8501/_stcore/health
```

**Expected response**:
```json
{
  "status": "ok"
}
```

**If returns error**:
- Check Streamlit is running: `ps aux | grep streamlit`
- Check port 8501 is listening: `netstat -tlnp | grep 8501`
- Increase start period if app needs longer warmup: `60s` instead of `40s`

### Authentication Not Working

**Symptom**: Login page loads but credentials don't work

**Verify database authentication setup**:
```bash
# In Coolify terminal
python -m src.auth.db_cli list
```

**Should show**:
```
Users in database:
- admin (admin@yourdomain.com) [Role: admin]
```

**If no users**:
- Create admin user (see Post-Deployment Step 1)

**If user exists but login fails**:
- Check cookie domain matches: `echo $AUTH_COOKIE_DOMAIN`
- Verify cookie key is set: `echo $AUTH_COOKIE_KEY | wc -c` (should be 32+)
- Check browser console for cookie errors
- Try incognito/private window (clears old cookies)

### RAG Search Returns No Results

**Symptom**: Queries work but no documents found

**Check document count**:
```bash
# In Coolify terminal
psql $DATABASE_URL -c "SELECT COUNT(*) FROM documents;"
```

**If count is 0**:
- No documents ingested yet
- Upload documents via UI or run ingestion pipeline
- See: `make ingest` (if you have local documents to upload)

**If documents exist but search fails**:
- Check embeddings are generated: `SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL;`
- Verify embedding dimension matches: `SELECT vector_dims(embedding) FROM documents LIMIT 1;`
  - Should be `1536` for OpenAI, `768` for Ollama
- If dimension mismatch, re-generate embeddings with correct provider

### Graph Search Returns No Results

**Symptom**: Vector search works but graph search empty

**Check Neo4j has data**:
```bash
# In Coolify terminal (or Neo4j Browser)
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', '$NEO4J_PASSWORD'))
with driver.session() as session:
    result = session.run('MATCH (n) RETURN count(n) AS count')
    print(f'Nodes: {result.single()[\"count\"]}')
"
```

**If node count is 0**:
- No knowledge extracted yet
- Documents need to be processed through Graphiti
- May take time after ingestion (async process)

### High Memory Usage

**Symptom**: Container using >8GB RAM, getting OOM killed

**Check current usage**:
```bash
# In Coolify terminal
free -h
ps aux --sort=-%mem | head -n 10
```

**Common causes**:
1. **sentence-transformers loaded**: Embeddings use PyTorch (~3.7GB)
   - **Fix**: Use OpenAI embeddings instead of local models
   - Set: `EMBEDDING_PROVIDER=openai`

2. **Large document uploads**: Processing multiple large files
   - **Fix**: Implement upload size limits
   - Set: `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200` (MB)

3. **Memory leaks in long-running sessions**:
   - **Fix**: Restart container periodically
   - Coolify: Set auto-restart schedule

**Optimize memory**:
- Reduce connection pool sizes:
  - `PG_POOL_MAX_SIZE=10` (from 20)
  - `NEO4J_MAX_CONNECTION_POOL_SIZE=25` (from 50)
- Disable unused features:
  - `ENABLE_LONG_TERM_MEMORY=false` (if not using mem0)
  - `ENABLE_WEB_SEARCH=false` (if not needed)

### Slow Response Times

**Symptom**: Queries take >10 seconds to respond

**Check component latency**:
```bash
# In Coolify logs, filter for performance metrics
grep "latency_ms" | tail -n 20
```

**Common causes**:
1. **Database connection latency**: Choose Supabase/Neo4j regions close to Coolify server
2. **LLM provider latency**: OpenAI/Anthropic response times vary by region
3. **Large result sets**: Reduce search limits
   - `VECTOR_SEARCH_LIMIT=5` (from 10)
   - `GRAPH_SEARCH_LIMIT=5` (from 10)

**Enable caching** (if not using Redis):
- Add Redis service in Coolify
- Set: `REDIS_URL=redis://redis:6379/0`
- Enables query caching for repeated searches

### OAuth Login Not Working

**Symptom**: OAuth buttons show but login fails

**Prerequisites**:
- `OAUTH_ENABLED=true`
- `USE_DATABASE_AUTH=true`
- Valid OAuth credentials from Google/GitHub

**Check OAuth configuration**:
```bash
# In Coolify terminal
echo "Google: $GOOGLE_CLIENT_ID"
echo "GitHub: $GITHUB_CLIENT_ID"
echo "Redirect: $GOOGLE_REDIRECT_URI"
echo "Encryption: $OAUTH_ENCRYPTION_KEY"
```

**Common issues**:
1. **Redirect URI mismatch**:
   - Must match exactly in OAuth app settings
   - Coolify: `https://kgpa.yourdomain.com` (no trailing slash)
   - Update in Google Cloud Console or GitHub Settings

2. **Encryption key not set**:
   ```bash
   # Generate new key
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   # Add to Coolify: OAUTH_ENCRYPTION_KEY=<generated-key>
   ```

3. **OAuth app not verified** (Google):
   - Development mode: Adds warning screen
   - Production: Submit app for verification

---

## Maintenance

### Updating the Application

**To deploy new version**:
1. Update your Git repository with changes
2. In Coolify UI, click **Redeploy**
3. Coolify will pull latest code and rebuild
4. Zero-downtime deployment (health checks ensure readiness)

**Manual image update**:
```bash
# If using external registry
docker pull yourregistry/knowledge-graph-pydantic-agent:latest
# Coolify will detect and offer to redeploy
```

### Database Migrations

**When new migrations are added**:
1. Check repository for new SQL files in `src/agentic_rag/storage/migrations/sql/`
2. Apply manually in Supabase SQL Editor (in order)
3. Redeploy application (no downtime - migrations are backwards compatible)

**Example workflow**:
```bash
# New migration: 009_new_feature.sql
# 1. Copy contents
# 2. Supabase SQL Editor -> Paste -> Run
# 3. Verify: SELECT * FROM new_table;
# 4. Coolify -> Redeploy
```

### Viewing Logs

**Real-time logs** (Coolify UI):
- Click **Logs** tab
- Auto-refreshes every 5 seconds

**Filtered logs**:
```bash
# In Coolify terminal
# Errors only
docker logs kgpa-ui 2>&1 | grep '"level":"error"'

# Specific component
docker logs kgpa-ui 2>&1 | grep 'StreamingHandler'

# Last 100 lines
docker logs --tail 100 kgpa-ui

# Follow logs live
docker logs -f kgpa-ui
```

**Export logs**:
```bash
# Save last 24 hours to file
docker logs --since 24h kgpa-ui > /tmp/kgpa-logs.txt
```

### Scaling

**Vertical scaling** (more resources):
- Coolify -> Resource Settings -> Edit Resource Limits
- Increase Memory Limit: `16384 MB` (16GB)
- Increase CPU Limit: `8.0` (8 cores)
- **Restart required**: Click Redeploy

**Horizontal scaling** (multiple instances):
- Coolify supports load balancing across multiple containers
- Configure in: Advanced -> Scale
- Set replicas: `2` or `3`
- **Note**: Ensure session stickiness for authentication cookies

**Database scaling**:
- **Supabase**: Upgrade to Pro tier for better performance
- **Neo4j Aura**: Upgrade instance size in Aura Console

### Rollback

**To previous version**:
1. Coolify UI -> Deployments tab
2. Find previous successful deployment
3. Click **Redeploy** on that version
4. Confirms rollback -> Deploys old version

**Manual rollback**:
```bash
# If using Git tags
git checkout v1.7.0
git push --force
# Coolify auto-detects and offers redeploy
```

### Backup and Restore

**Database backups** (automatic):
- Supabase: Settings -> Database -> Backups -> Restore
- Neo4j: Aura Console -> Backups -> Create snapshot

**Manual database backup**:
```bash
# PostgreSQL/Supabase
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql

# Neo4j (via Aura Console only for managed instances)
```

**Application data backup** (if using persistent volumes):
```bash
# In Coolify terminal
tar czf /tmp/kgpa-backup.tar.gz /app/data /app/logs

# Download from Coolify UI: Files tab
```

**Restore process**:
1. Stop application: Coolify -> Stop
2. Restore database: Supabase/Neo4j console
3. Restore volumes: `tar xzf backup.tar.gz -C /`
4. Start application: Coolify -> Start

---

## Security Best Practices

### 1. Environment Variables
- Mark all secrets as "Secret" in Coolify (lock icon)
- Never commit `.env` to Git
- Rotate keys periodically (quarterly):
  - `AUTH_COOKIE_KEY`
  - `LLM_API_KEY`
  - Database passwords

### 2. Authentication
- Use strong admin password (12+ characters, mixed case, numbers, symbols)
- Enable 2FA for admin accounts (if implemented)
- Set session timeout: `SESSION_IDLE_TIMEOUT_MINUTES=30`
- Enable password reset email flow for production

### 3. HTTPS
- Always enable HTTPS in Coolify (Let's Encrypt)
- Force HTTPS redirect:
- Set secure cookie flags:
  - `AUTH_COOKIE_SECURE=true`
  - `AUTH_COOKIE_HTTPONLY=true`

### 4. Database Security
- Use Supabase Row Level Security (RLS) policies
- Restrict Supabase service key access
- Use Neo4j RBAC (create read-only user for application if possible)
- Regular backups (daily minimum)

### 5. Rate Limiting
- Enable in production: `RATE_LIMIT_ENABLED=true`
- Adjust per use case: `RATE_LIMIT_PER_MINUTE=60`
- Monitor for abuse in logs

### 6. Monitoring
- Enable metrics: `ENABLE_METRICS=true`
- Set up alerting for:
  - Health check failures
  - High error rates
  - Memory/CPU spikes
- Review logs weekly for anomalies

---

## Cost Optimization

### Free Tier Limits

**Supabase Free Tier**:
- 500 MB database storage
- 1 GB file storage
- 2 GB bandwidth/month
- 50,000 monthly active users
- **Sufficient for**: Development, small projects (<100 documents)

**Neo4j Aura Free Tier**:
- 50,000 nodes + 175,000 relationships
- Shared infrastructure
- **Sufficient for**: Development, moderate knowledge graphs (<1000 entities)

**When to upgrade**:
- Supabase: >500 MB documents -> Pro ($25/month)
- Neo4j: >50k nodes -> Professional ($65/month)

### Optimizing Costs

1. **Use OpenAI gpt-4o-mini** (not gpt-4):
   - 15x cheaper ($0.15/1M vs $2.50/1M input tokens)
   - Sufficient for most RAG use cases

2. **Cache responses** (if using Redis):
   - Reduces duplicate LLM calls
   - Saves API costs

3. **Limit search results**:
   - `VECTOR_SEARCH_LIMIT=5` (fewer embeddings to generate)
   - `GRAPH_SEARCH_LIMIT=5` (fewer Cypher queries)

4. **Disable unused features**:
   - `ENABLE_WEB_SEARCH=false` (if not needed)
   - `ENABLE_IMAGE_ANALYSIS=false` (uses vision model)
   - `ENABLE_LONG_TERM_MEMORY=false` (if not using mem0)

5. **Coolify resource allocation**:
   - Start with 4GB RAM if not using local embeddings
   - Scale up only if needed
   - Monitor actual usage: Coolify -> Metrics

---

## Production Checklist

Before going live, verify:

- [ ] All database migrations applied (8 SQL files)
- [ ] Neo4j graph schema initialized
- [ ] Admin user created and tested
- [ ] `AUTH_COOKIE_KEY` generated and set (32+ chars)
- [ ] `AUTH_COOKIE_DOMAIN` matches actual domain
- [ ] `AUTH_COOKIE_SECURE=true` (HTTPS enforced)
- [ ] `USE_DATABASE_AUTH=true` (not YAML mode)
- [ ] HTTPS enabled in Coolify (Let's Encrypt)
- [ ] Health checks passing (green status)
- [ ] All core features tested:
  - [ ] Login/logout
  - [ ] RAG search (upload document + query)
  - [ ] Graph search (entity queries)
  - [ ] Web search (if enabled)
  - [ ] Image analysis (if enabled)
- [ ] Email configured (if using password reset)
- [ ] OAuth configured (if using Google/GitHub login)
- [ ] Backups configured (Supabase + Neo4j)
- [ ] Monitoring/alerting set up
- [ ] Logs reviewed (no errors)
- [ ] Resource limits appropriate (8GB+ RAM)
- [ ] Rate limiting enabled (`RATE_LIMIT_ENABLED=true`)
- [ ] Secrets marked as "Secret" in Coolify
- [ ] `.env` file NOT committed to Git
- [ ] Documentation updated with production URLs

---

## Additional Resources

### Documentation
- **KGPA Docs**: `/docs/` directory in repository
- **Supabase Docs**: https://supabase.com/docs
- **Neo4j Aura Docs**: https://neo4j.com/docs/aura/
- **Coolify Docs**: https://coolify.io/docs

### Support
- **GitHub Issues**: Report bugs or request features
- **Logs**: Always include logs when reporting issues
- **Health Check**: Share health endpoint output for debugging

### Related Guides
- `docs/6-deployment/general.md` - General deployment concepts
- `docs/6-deployment/streamlit_ngrok_deploy.md` - Alternative ngrok deployment
- `docs/7-operations/go-live-checklist.md` - Production readiness
- `docs/7-operations/api-runbook.md` - API operations guide

---

## Next Steps

1. **Complete Pre-Deployment Steps** (database setup, credentials)
2. **Deploy to Coolify** (follow deployment process)
3. **Verify Post-Deployment** (create admin, test features)
4. **Configure Monitoring** (metrics, logs, alerts)
5. **Go Live** (production checklist)

Need help? Check troubleshooting section or review logs in Coolify UI.
