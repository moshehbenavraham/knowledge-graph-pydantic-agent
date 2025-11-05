# Runbook

## Local Development
1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -e .[dev,rag]
   ```
   *Reference:* editable install targets defined in `pyproject.toml` optional groups and Makefile `setup` task.【F:pyproject.toml†L54-L117】【F:Makefile†L2-L19】

2. **Environment variables** – copy `.env.example` (if available) or export required keys (LLM_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, NEO4J_PASSWORD, etc.) per `docker-compose.yml` definitions.【F:docker-compose.yml†L10-L48】

3. **Run FastAPI service**
   ```bash
   source .venv/bin/activate
   make run-api
   ```
   Uses `python -m src.api.main` via Makefile.【F:Makefile†L84-L86】

4. **Run Streamlit UI / Unified Agent**
   ```bash
   source .venv/bin/activate
   make run-ui
   ```
   Runs Streamlit with UI mode configurable via `UI_MODE` env var.【F:Makefile†L62-L76】

5. **Run ingestion pipeline CLI**
   ```bash
   source .venv/bin/activate
   make run-rag SOURCE=local
   ```
   Invokes `src.rag_pipeline.pipeline:main` for local or Google Drive watchers.【F:Makefile†L78-L80】【F:src/rag_pipeline/pipeline.py†L13-L55】

6. **Execute tests & linters**
   ```bash
   make test
   make lint
   make security
   ```
   Pytest, Ruff/Black/Mypy, and Bandit/Safety/pip-audit pipelines are scripted.【F:Makefile†L15-L40】

## Docker / Compose
1. **Build & run core stack**
   ```bash
   docker compose up --build
   ```
   or `make docker-run` to start services defined in `docker-compose.yml` (app, searxng, neo4j, redis).【F:docker-compose.yml†L4-L158】【F:Makefile†L129-L138】 Ensure external Postgres (Supabase) credentials are provided before boot.

2. **Monitoring stack**
   ```bash
   docker compose -f docker-compose.monitoring.yml up -d
   ```
   Launches Prometheus, Grafana, Jaeger, Redis exporter, Node exporter, Loki, Promtail, and Redis Commander.【F:docker-compose.monitoring.yml†L4-L165】【F:Makefile†L195-L200】

3. **Health checks** – Compose defines health probes for app (Streamlit), Neo4j, Redis, SearxNG. Confirm with `docker inspect` or rely on Compose auto-restart.【F:docker-compose.yml†L79-L149】

## Database Setup
- **Postgres**: Provide `DATABASE_URL` pointing to pgvector-enabled instance. Run SQL migrations manually (e.g., via `psql -f src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql`). No automated migration runner is bundled.
- **Neo4j**: After Neo4j container is up, execute initializer script to create constraints/indexes:
  ```bash
  source .venv/bin/activate
  python -m src.agentic_rag.storage.neo4j_store init
  ```
  (Makefile alias `make neo4j-init`.)【F:Makefile†L147-L149】【F:src/agentic_rag/storage/migrations/neo4j_init.py†L17-L170】

## Smoke Tests
1. **FastAPI**
   ```bash
   curl http://localhost:8000/health/
   curl http://localhost:8000/api/v1/status
   ```
   Verify JSON payloads indicating healthy components.【F:src/api/health_endpoints.py†L16-L60】【F:src/api/main.py†L176-L200】

2. **Chat endpoint**
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat \
     -H 'Content-Type: application/json' \
     -d '{"message": "Hello", "session_id": "demo"}'
   ```
   Expect `ChatResponse` with metrics.【F:src/api/endpoints/chat.py†L38-L123】

3. **Search endpoint**
   ```bash
   curl -X POST http://localhost:8000/api/v1/search \
     -H 'Content-Type: application/json' \
     -d '{"query": "test", "search_type": "hybrid"}'
   ```
   Returns `SearchResponse`; if no data ingested, expect empty list.【F:src/api/endpoints/search.py†L48-L120】

4. **Prometheus metrics**
   ```bash
   curl http://localhost:8000/metrics
   ```
   Confirms application metrics exporter is reachable.【F:src/api/main.py†L11-L147】

## Production Deployment Notes
- Configure secrets via managed vault or environment injection (Kubernetes Secrets) to avoid checking credentials into Compose files.【F:docker-compose.yml†L10-L48】
- Enable OpenTelemetry export by setting `ENABLE_TRACING`/collector endpoints before startup so `_setup_tracing` executes.【F:src/api/main.py†L69-L110】
- Run background ingestion as separate worker process (e.g., systemd service invoking `make run-rag`) to avoid blocking API threads.
- Monitor queue health by querying `graph_sync_queue` and analytics tables; consider scheduled job to flush expired cache entries via `PostgresStore.clean_expired_cache`.【F:src/agentic_rag/storage/postgres_store.py†L437-L450】
