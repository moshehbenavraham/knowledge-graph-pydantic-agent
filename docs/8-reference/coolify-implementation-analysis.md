# Coolify Implementation Analysis

## Document Information

- **Author**: System Analysis
- **Date**: 2025-12-22
- **Scope**: Full-depth analysis of Coolify integration in Knowledge Graph Pydantic Agent (KGPA)
- **Verification Status**: Double-checked against codebase

---

## 1. What is Coolify?

Coolify is an open-source, self-hostable alternative to platforms like Heroku, Netlify, and Vercel. It provides:

- **Self-hosted PaaS**: Deploy applications on your own servers
- **Docker-based deployments**: Build and run containers automatically
- **Git integration**: Auto-deploy from GitHub/GitLab on push
- **SSL/HTTPS**: Automatic Let's Encrypt certificates
- **Zero-downtime deployments**: Health check-based rollouts
- **API access**: Programmatic deployment control

**Official Site**: https://coolify.io

---

## 2. Implementation Overview

Knowledge Graph Pydantic Agent (KGPA) uses Coolify as its **primary production deployment platform**. The integration is comprehensive, including:

| Component | Purpose |
|-----------|---------|
| API Deployment Script | Fully automated deployment via Coolify API |
| Docker Compose Configuration | Coolify-optimized container definition |
| Environment Generator | Secure credential generation for Coolify |
| Pre-deployment Validator | Verification of all prerequisites |
| Makefile Targets | Developer-friendly command interface |
| Documentation | Quick-start and full deployment guides |

---

## 3. File Inventory

### Scripts (3 files)

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/coolify-deploy.sh` | 445 | Main API deployment automation |
| `scripts/generate-coolify-env.sh` | 197 | Environment variable template generator |
| `scripts/coolify-pre-deploy-check.sh` | 269 | Pre-deployment validation checklist |

### Docker Configuration (1 file)

| File | Lines | Purpose |
|------|-------|---------|
| `docker/docker-compose.coolify.yml` | 181 | Coolify-specific Docker Compose |

### Documentation (2 files)

| File | Lines | Purpose |
|------|-------|---------|
| `docs/2-getting-started/coolify-deployment.md` | 258 | Quick-start guide |
| `docs/6-deployment/coolify-deploy-full.md` | 1044 | Comprehensive deployment guide |

### Configuration References

| File | Coolify-Related Content |
|------|------------------------|
| `.env.example` | Lines 63-68: COOLIFY_API_TOKEN, COOLIFY_API_URL, GITHUB_REPO, GITHUB_BRANCH, APP_NAME |
| `Makefile` | Lines 162-200: 9 Coolify-related make targets |
| `docker/Dockerfile.production` | 112 lines: Multi-stage build used by Coolify |

---

## 4. Deployment Architecture

```
                    +------------------+
                    |   Coolify Server |
                    |  (Self-hosted)   |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+         +---------v---------+
    |  GitHub Private   |         |   Coolify API     |
    |    Repository     |         |   (REST/JSON)     |
    +-------------------+         +-------------------+
              |                             |
              |    coolify-deploy.sh        |
              +-----------------------------+
                             |
              +--------------v--------------+
              |     Docker Build Stage      |
              |  Dockerfile.production      |
              |  - builder (dependencies)   |
              |  - runtime (Streamlit UI)   |
              |  - api (FastAPI optional)   |
              +--------------+--------------+
                             |
              +--------------v--------------+
              |    Running Container        |
              |  kgpa-coolify               |
              |  - Port 8502 (Streamlit)    |
              |  - Port 8058 (API optional) |
              +--------------+--------------+
                             |
         +-------------------+-------------------+
         |                                       |
+--------v--------+                    +---------v--------+
|  Supabase       |                    |  Neo4j Aura      |
|  (PostgreSQL +  |                    |  (Knowledge      |
|   pgvector)     |                    |   Graph)         |
+-----------------+                    +------------------+
```

**Key Architecture Decisions**:

1. **External Managed Databases**: Uses Supabase and Neo4j Aura (not self-hosted in Coolify)
2. **Single Container**: One app container with optional API sidecar
3. **Multi-stage Docker Build**: Optimized for size and security
4. **Non-root User**: Container runs as `appuser` (UID 1001)

---

## 5. Deployment Script Analysis (`coolify-deploy.sh`)

### Script Workflow (6 Steps)

```
Step 1: Discover Coolify Instance Details
    - Fetch teams (GET /teams)
    - Fetch servers (GET /servers)
    - Fetch GitHub Apps (GET /github-apps)
    - Fetch projects (GET /projects)

Step 2: Create Application Resource
    - POST /applications/public (or /applications/private-github-app)
    - Configure build pack, ports, repository

Step 3: Configure Application Settings
    - PATCH /applications/{uuid}
    - Set domain, build target, dockerfile location
    - Configure health checks
    - Set resource limits (8GB RAM, 4 CPU)

Step 4: Configure Environment Variables
    - POST /applications/{uuid}/envs/bulk
    - Read from local .env file
    - Exclude COOLIFY_* variables

Step 5: Trigger Deployment
    - GET /applications/{uuid}/start?force=false&instant_deploy=true
    - Monitor build progress (30s intervals, 15min timeout)

Step 6: Post-Deployment Instructions
    - Display verification URLs
    - Provide admin user creation command
```

### API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/teams` | List Coolify teams |
| GET | `/servers` | List available servers |
| GET | `/github-apps` | List GitHub App integrations |
| GET | `/projects` | List projects/environments |
| POST | `/applications/public` | Create app from public repo |
| POST | `/applications/private-github-app` | Create app from private repo |
| PATCH | `/applications/{uuid}` | Update application settings |
| POST | `/applications/{uuid}/envs/bulk` | Bulk set environment variables |
| GET | `/applications/{uuid}/start` | Trigger deployment |
| GET | `/applications/{uuid}` | Check application status |

### Required Environment Variables

```bash
COOLIFY_API_TOKEN    # Required: API token with write/deploy/read permissions
COOLIFY_API_URL      # Required: Base URL (e.g., https://coolify.domain.com/api/v1)
GITHUB_REPO          # Optional: Repository URL (default: moshehbenavraham/knowledge-graph-pydantic-agent)
GITHUB_BRANCH        # Optional: Branch to deploy (default: main)
APP_NAME             # Optional: Application name (default: kgpa-ui)
APP_DOMAIN           # Optional: Domain name (default: kgpa.aiwithapex.com)
```

---

## 6. Environment Generator Analysis (`generate-coolify-env.sh`)

### Generated Security Keys

```bash
# Auto-generated with Python
AUTH_COOKIE_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
OAUTH_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### Output File Structure (`.env.coolify`)

```
=== CORE DATABASE CONFIGURATION ===
- SUPABASE_URL, SUPABASE_SERVICE_KEY, DATABASE_URL
- NEO4J_URI, NEO4J_QUERY_API_URL, NEO4J_USER, NEO4J_PASSWORD

=== LLM CONFIGURATION ===
- LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
- EMBEDDING_PROVIDER, EMBEDDING_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSION

=== AUTHENTICATION ===
- USE_DATABASE_AUTH, AUTH_COOKIE_KEY, AUTH_COOKIE_NAME, AUTH_COOKIE_EXPIRY_DAYS
- AUTH_COOKIE_DOMAIN, AUTH_COOKIE_SECURE, AUTH_COOKIE_HTTPONLY
- SESSION_IDLE_TIMEOUT_MINUTES, SESSION_ABSOLUTE_TIMEOUT_HOURS

=== PASSWORD RESET ===
- PASSWORD_RESET_URL, EMAIL_ENABLED, EMAIL_PROVIDER, SMTP_*

=== OAUTH (OPTIONAL) ===
- OAUTH_ENABLED, OAUTH_ENCRYPTION_KEY
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
- GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_REDIRECT_URI

=== FEATURE FLAGS ===
- ENABLE_RAG, ENABLE_AGENTIC_RAG, ENABLE_GRAPH_SEARCH
- ENABLE_WEB_SEARCH, ENABLE_IMAGE_ANALYSIS, ENABLE_LONG_TERM_MEMORY, ENABLE_METRICS

=== WEB SEARCH ===
- JINA_API_KEY, BRAVE_API_KEY

=== LOGGING & MONITORING ===
- LOG_LEVEL, LOG_FORMAT, ENABLE_STRUCTURED_LOGGING

=== PERFORMANCE TUNING ===
- PG_POOL_MIN_SIZE, PG_POOL_MAX_SIZE, PG_POOL_TIMEOUT
- NEO4J_MAX_CONNECTION_POOL_SIZE, NEO4J_CONNECTION_TIMEOUT
- VECTOR_SEARCH_LIMIT, GRAPH_SEARCH_LIMIT, HYBRID_SEARCH_ALPHA
- RATE_LIMIT_ENABLED, RATE_LIMIT_PER_MINUTE

=== UI CONFIGURATION ===
- UI_MODE, STREAMLIT_SERVER_PORT, STREAMLIT_SERVER_ADDRESS
- STREAMLIT_SERVER_HEADLESS, STREAMLIT_BROWSER_GATHER_USAGE_STATS

=== API CONFIGURATION ===
- API_HOST, API_PORT, API_WORKERS, API_RELOAD
```

---

## 7. Pre-Deployment Validator Analysis (`coolify-pre-deploy-check.sh`)

### Validation Checks (10 Categories)

| Check | Validation |
|-------|------------|
| 1. Environment Configuration | .env file exists, required variables set |
| 2. Docker Configuration | Dockerfile.production and docker-compose.coolify.yml exist |
| 3. Neo4j Connection | Live connection test via Python driver |
| 4. Supabase Connection | Live connection test via psql |
| 5. SQL Migrations | All 5 required migration files exist |
| 6. Authentication | AUTH_COOKIE_KEY set and >= 32 chars |
| 7. Config Files | config/ directory and auth_config.yaml exist |
| 8. LLM Provider | API key configured for selected provider |
| 9. Embedding Config | Dimension matches provider (1536/768) |
| 10. Feature Flags | Security recommendations (code execution, rate limiting) |

### Required Variables Checked

```bash
SUPABASE_URL
SUPABASE_SERVICE_KEY
DATABASE_URL
NEO4J_URI
NEO4J_USER
NEO4J_PASSWORD
LLM_PROVIDER
LLM_API_KEY
AUTH_COOKIE_KEY
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed OR only warnings |
| 1 | Errors found (deployment blocked) |

---

## 8. Docker Compose Configuration (`docker-compose.coolify.yml`)

### Service Definition

```yaml
services:
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile.production
      target: runtime
    container_name: kgpa-coolify
    ports:
      - "8502:8502"
```

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8192M
    reservations:
      cpus: '2.0'
      memory: 4096M
```

### Health Check

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8502/_stcore/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Environment Variables

The compose file passes through **50+ environment variables** covering:
- Database connections (Supabase, Neo4j)
- LLM and embedding configuration
- Authentication settings
- Feature flags
- Performance tuning
- Logging configuration

### Volumes

```yaml
volumes:
  app_data:    # /app/data (persistent storage)
  app_logs:    # /app/logs (log files)
```

---

## 9. Makefile Targets

| Target | Command | Purpose |
|--------|---------|---------|
| `coolify-check` | Run pre-deployment checks | Validates prerequisites |
| `coolify-env` | Generate environment template | Creates `.env.coolify` |
| `coolify-build` | Build production image | Local Docker build test |
| `coolify-test-build` | Test build with run command | Build and print run command |
| `coolify-compose-up` | Start services locally | Docker Compose up |
| `coolify-compose-down` | Stop services | Docker Compose down |
| `coolify-compose-logs` | View logs | Docker Compose logs -f |
| `coolify-deploy-api` | Automated deployment | Run coolify-deploy.sh |

### Usage Examples

```bash
# Full deployment workflow
make coolify-env           # Generate .env.coolify
vi .env.coolify            # Edit with real values
make coolify-check         # Verify prerequisites
make coolify-test-build    # Test Docker build locally
make coolify-deploy-api    # Deploy via Coolify API

# Local testing
make coolify-compose-up    # Start locally
make coolify-compose-logs  # View logs
make coolify-compose-down  # Stop
```

---

## 10. Dockerfile.production Analysis

### Build Stages

| Stage | Base Image | Purpose |
|-------|------------|---------|
| `builder` | python:3.11-slim | Install dependencies with uv |
| `runtime` | python:3.11-slim | Minimal Streamlit runtime |
| `api` | runtime | FastAPI server (optional) |

### Security Features

1. **Non-root user**: `appuser` (UID 1001)
2. **Minimal packages**: Only runtime dependencies in final image
3. **No shell access**: User has `/sbin/nologin`
4. **Read-only code**: Application code owned by appuser

### Exposed Ports

| Port | Service |
|------|---------|
| 8502 | Streamlit UI |
| 8058 | FastAPI API |
| 8002 | Prometheus metrics |

### Key Environment Variables

```dockerfile
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    STREAMLIT_SERVER_PORT=8502 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true
```

---

## 11. Integration with External Services

### Supabase (PostgreSQL + pgvector)

- **Connection**: DATABASE_URL with Session Pooler (required for Coolify)
- **Tables**: documents, auth_users, analytics, etc.
- **Migrations**: 5-8 SQL files applied via SQL Editor

### Neo4j Aura (Knowledge Graph)

- **Connection**: NEO4J_URI with `neo4j+s://` (encrypted)
- **Schema**: Entity/Episode constraints and indexes
- **Graphiti**: Entity extraction and relationship storage

### GitHub Integration

- **Public repos**: `/applications/public` endpoint
- **Private repos**: Requires GitHub App in Coolify
- **Auto-deploy**: Triggered on push (optional)

---

## 12. Health Monitoring

### Health Check Endpoint

```
GET /_stcore/health
Response: {"status": "ok"}
```

### Coolify Monitoring Features

1. **Build logs**: Real-time during deployment
2. **Container logs**: Application stdout/stderr
3. **Health status**: Green/Red indicators
4. **Resource usage**: CPU/Memory metrics
5. **Deployment history**: Rollback capability

### Recommended Monitoring

- **Production**: Coolify dashboard for basics
- **Advanced**: External Prometheus + Grafana
- **Logs**: Structured JSON with structlog

---

## 13. Security Considerations

### Secrets Management

| Variable | Storage |
|----------|---------|
| API keys | Coolify "Secret" marking (lock icon) |
| Database passwords | Never in Git, only in Coolify env |
| Cookie keys | Auto-generated, stored in Coolify |

### Authentication Flow

1. Coolify provides HTTPS (Let's Encrypt)
2. Cookie-based auth with `AUTH_COOKIE_SECURE=true`
3. Database auth mode (not YAML) for production
4. Session management with idle/absolute timeouts

### Network Security

- **Ingress**: Only 8502 exposed via Coolify proxy
- **Databases**: External managed services (Supabase, Neo4j Aura)
- **Rate limiting**: Enabled by default (`RATE_LIMIT_ENABLED=true`)

---

## 14. Deployment Workflow Summary

### Prerequisites

1. Coolify server with Docker
2. Supabase project with migrations applied
3. Neo4j Aura instance with schema initialized
4. LLM API keys (OpenAI/Anthropic)

### Deployment Steps

```
1. make coolify-env                    # Generate .env.coolify
2. Edit .env.coolify                   # Add credentials
3. Apply Supabase migrations           # SQL Editor
4. Initialize Neo4j schema             # Cypher console
5. make coolify-check                  # Validate prerequisites
6. make coolify-deploy-api             # Deploy to Coolify
7. Create admin user via Coolify terminal
8. Verify at https://your-domain.com
```

### Post-Deployment

```bash
# In Coolify terminal
python -m src.auth.db_cli create \
  --username admin \
  --email admin@example.com \
  --name "Admin User" \
  --password "SecurePassword123!" \
  --role admin
```

---

## 15. Known Limitations

1. **Single Instance**: Horizontal scaling requires sticky sessions
2. **Database Migrations**: Manual via Supabase SQL Editor
3. **Neo4j Backup**: Via Aura Console only (not API)
4. **Embedding Size**: ~3.7GB if using local sentence-transformers
5. **Build Time**: 5-8 minutes for full RAG dependencies

---

## 16. Files Cross-Reference

### File Dependencies

```
coolify-deploy.sh
    ├── Reads: .env
    ├── Uses: Coolify API endpoints
    └── Configures: docker/Dockerfile.production

generate-coolify-env.sh
    ├── Generates: .env.coolify
    ├── Uses: Python (secrets, cryptography.fernet)
    └── Template for: docker-compose.coolify.yml

coolify-pre-deploy-check.sh
    ├── Reads: .env
    ├── Checks: docker/Dockerfile.production
    ├── Checks: docker/docker-compose.coolify.yml
    ├── Checks: src/agentic_rag/storage/migrations/sql/*.sql
    └── Tests: Neo4j, Supabase connections

docker-compose.coolify.yml
    ├── Uses: docker/Dockerfile.production
    ├── Reads: Environment variables
    └── Exposes: Port 8502

Dockerfile.production
    ├── Copies: src/, config/, Makefile, pyproject.toml
    ├── Installs: .[rag,auth,security]
    └── Runs: streamlit run src/ui/streamlit_app.py
```

---

## 17. Verification Checklist

This analysis verified:

- [x] All Coolify-related files identified (9 files)
- [x] Deployment script API endpoints documented
- [x] Environment variables catalogued (50+)
- [x] Docker configuration analyzed
- [x] Makefile targets enumerated (9 targets)
- [x] Pre-deployment checks documented (10 categories)
- [x] Security considerations reviewed
- [x] Integration with external services mapped
- [x] File dependencies cross-referenced
- [x] Double-checked against grep/glob results

---

## 18. Appendix: Quick Command Reference

```bash
# Environment
make coolify-env           # Generate .env.coolify with secure keys

# Validation
make coolify-check         # Run all pre-deployment checks

# Building
make coolify-build         # Build production image
make coolify-test-build    # Build and show run command

# Local Testing
make coolify-compose-up    # Start with docker-compose
make coolify-compose-logs  # View logs
make coolify-compose-down  # Stop services

# Deployment
make coolify-deploy-api    # Automated API deployment
```
