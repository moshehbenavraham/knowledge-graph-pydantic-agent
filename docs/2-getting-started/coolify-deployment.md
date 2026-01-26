# Coolify Deployment - Quick Start Guide

This is a quick reference guide for deploying Knowledge Graph Pydantic Agent (KGPA) to Coolify. For the complete guide with troubleshooting, see [coolify-deploy-full.md](../6-deployment/coolify-deploy-full.md).

## Prerequisites

Before you start, ensure you have:

1. **Coolify server** set up and accessible
2. **Neo4j Aura** account with database instance created
3. **Supabase** project created
4. **LLM API keys** (OpenAI, Anthropic, or Ollama endpoint)

## Quick Start (5 Steps)

### Step 1: Generate Environment Variables

```bash
# Generate Coolify environment template with secure keys
make coolify-env
```

This creates `.env.coolify` with:
- Auto-generated `AUTH_COOKIE_KEY`
- Auto-generated `OAUTH_ENCRYPTION_KEY`
- Template for all required variables

### Step 2: Configure Environment

Edit `.env.coolify` and fill in:

```bash
# Core Database (REQUIRED)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
DATABASE_URL=postgresql://postgres.xxxxx:password@aws-region.pooler.supabase.com:5432/postgres

# Neo4j Aura (REQUIRED)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# LLM Provider (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=sk-your_openai_api_key

# Domain (UPDATE for your deployment)
AUTH_COOKIE_DOMAIN=your-app.yourdomain.com
PASSWORD_RESET_URL=https://your-app.yourdomain.com/reset-password
```

### Step 3: Apply Database Migrations

**Supabase SQL Editor** (run in order):

All migration files are in: `src/agentic_rag/storage/migrations/sql/`

```sql
-- 1. Enhanced schema (includes pgvector extension and documents tables)
-- Run: 001_enhanced_schema.sql

-- 2. Document rows table
-- Run: 002_document_rows_table.sql

-- 3. Execute SQL RPC function
-- Run: 003_execute_sql_rpc.sql

-- 4. Analytics schema
-- Run: 004_analytics_schema.sql

-- 5. Auth tables (REQUIRED for production)
-- Run: 005_auth_tables.sql

-- 6-8. Optional: Email verification, 2FA, OAuth
-- Run: 006_email_verification.sql, 007_2fa_and_password_history.sql, 008_oauth_analytics.sql
```

**Neo4j Browser** (Aura Console → Open):
```cypher
CREATE CONSTRAINT entity_uuid IF NOT EXISTS FOR (e:Entity) REQUIRE e.uuid IS UNIQUE;
CREATE CONSTRAINT episode_uuid IF NOT EXISTS FOR (e:Episode) REQUIRE e.uuid IS UNIQUE;
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX episode_created_at IF NOT EXISTS FOR (e:Episode) ON (e.created_at);
```

### Step 4: Run Pre-Deployment Checks

```bash
# Verify all prerequisites
make coolify-check
```

Fix any errors before proceeding.

### Step 5: Deploy to Coolify

1. **Create Resource**: Coolify Dashboard → New → Resource → Docker Compose

2. **Configure**:
   - **Name**: `kgpa-ui`
   - **Domain**: `kgpa.yourdomain.com`
   - **Build Pack**: Dockerfile
   - **Dockerfile**: `docker/Dockerfile.production`
   - **Build Context**: `.` (root)
   - **Build Target**: `runtime`

3. **Environment Variables**: Copy contents of `.env.coolify` to Coolify → Bulk Edit

4. **Resource Limits**:
   - Memory: 8192 MB (8GB)
   - CPU: 4.0 cores
   - Reservation: 4096 MB / 2.0 cores

5. **Deploy**: Click Deploy button

## Post-Deployment

### Create Admin User

Access Coolify Terminal and run:

```bash
python -m src.auth.db_cli create \
  --username admin \
  --email admin@yourdomain.com \
  --name "Admin User" \
  --password "YourStrongPassword123!" \
  --role admin
```

### Verify Deployment

1. Access your domain: `https://kgpa.yourdomain.com`
2. Login with admin credentials
3. Test core features:
   - Upload a document
   - Ask a question
   - Check search works

## Makefile Commands

```bash
# Generate environment template
make coolify-env

# Run pre-deployment checks
make coolify-check

# Build Docker image locally (test)
make coolify-build

# Test build and get run command
make coolify-test-build

# Start locally using Coolify docker-compose
make coolify-compose-up

# View logs
make coolify-compose-logs

# Stop services
make coolify-compose-down
```

## File Reference

| File | Purpose |
|------|---------|
| `docker/Dockerfile.production` | Multi-stage production Dockerfile |
| `docker/docker-compose.coolify.yml` | Coolify-specific compose file |
| `.env.example` | Environment variable reference |
| `scripts/generate-coolify-env.sh` | Environment generator |
| `scripts/coolify-pre-deploy-check.sh` | Pre-deployment validator |
| `src/agentic_rag/storage/migrations/sql/*.sql` | Database migration scripts |

## Common Issues

### Build Fails

**Symptom**: Docker build fails in Coolify

**Fix**:
1. Test build locally: `make coolify-test-build`
2. Check logs for missing dependencies
3. Verify build context is set to `.` (root)
4. Ensure build target is `runtime`

### Health Check Failing

**Symptom**: Coolify shows "Unhealthy"

**Fix**:
1. Check environment variables are set correctly
2. Verify database connections (Neo4j + Supabase)
3. Increase health check start period to 60s
4. Check logs for errors

### Authentication Not Working

**Symptom**: Login page loads but credentials don't work

**Fix**:
1. Verify `USE_DATABASE_AUTH=true`
2. Check `AUTH_COOKIE_DOMAIN` matches your domain
3. Ensure `AUTH_COOKIE_KEY` is set (32+ chars)
4. Create admin user using CLI (see above)
5. Try incognito window (clears cookies)

### Database Connection Failed

**Symptom**: Cannot connect to PostgreSQL/Neo4j

**Fix**:
1. **PostgreSQL**: Must use Session Pooler URL (not direct)
   - Format: `postgresql://postgres.xxxxx:pass@aws-region.pooler.supabase.com:5432/postgres`
2. **Neo4j**: Must use encrypted connection (`neo4j+s://`)
3. Run `make coolify-check` to test connections
4. Verify firewall/IP allowlist settings

## Resource Requirements

### Minimum (Development)
- **RAM**: 4GB
- **CPU**: 2 cores
- **Disk**: 5GB

### Recommended (Production)
- **RAM**: 8GB
- **CPU**: 4 cores
- **Disk**: 10GB

### External Services (Free Tier)
- **Supabase**: 500MB database, 1GB storage
- **Neo4j Aura**: 50k nodes, 175k relationships
- **OpenAI**: Pay-as-you-go (gpt-4o-mini: $0.15/1M tokens)

## Next Steps

1. **Configure OAuth** (optional): See `docs/deployment/oauth_setup_guide.md`
2. **Enable Email** (optional): Configure SMTP for password reset
3. **Add Documents**: Upload via UI or API
4. **Monitor**: Check Coolify logs for errors
5. **Backup**: Configure Supabase + Neo4j backups

## Support

For detailed troubleshooting, see:
- Full guide: [coolify-deploy-full.md](../6-deployment/coolify-deploy-full.md)
- General deployment: [general.md](../6-deployment/general.md)
- Operations: See docs/7-operations/go-live-checklist.md

For issues, check Coolify logs:
```bash
# In Coolify UI: Logs tab
# Or via terminal:
docker logs <container-name>
```
