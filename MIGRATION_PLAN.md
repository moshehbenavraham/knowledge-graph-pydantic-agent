# Migration Plan to Target Stack

## Phase 1 – MVP Alignment (Weeks 1–3)
1. **Fix dependency bootstrap** – Inject `ConnectionManager` into `PostgresStore`/`Neo4jStore` constructors and ensure initialization during FastAPI startup.【F:src/api/dependencies.py†L33-L138】【F:src/agentic_rag/storage/postgres_store.py†L16-L24】
2. **Provision local Postgres** – Add pgvector-enabled Postgres service to Compose and automate execution of `001_enhanced_schema.sql` migrations.【F:docker-compose.yml†L4-L158】【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L1-L200】
3. **Enable ingestion pipeline reuse** – Create shared pipeline dependency that calls `await pipeline.initialize()` once per lifecycle before ingestion endpoint uses it.【F:src/agentic_rag/ingestion/pipeline.py†L83-L166】【F:src/api/endpoints/documents.py†L56-L90】
4. **Implement Graph entity/relationship endpoints** using direct Neo4j Cypher queries while Graphiti integration is staged.【F:src/api/endpoints/search.py†L161-L223】【F:src/agentic_rag/storage/neo4j_store.py†L25-L166】

## Phase 2 – Hardening & Observability (Weeks 4–6)
1. **Replace custom Graphiti wrapper** with official `graphiti_core` ingestion/search flows; update ingestion pipeline and search helpers accordingly.【F:src/agentic_rag/storage/graphiti_client.py†L15-L190】【F:src/agentic_rag/search/graph_search.py†L147-L233】
2. **Complete graph maintenance** – Implement reindex/delete/stats operations to maintain Neo4j/Postgres parity and flush `graph_sync_queue` workers.【F:src/api/endpoints/documents.py†L236-L395】【F:src/agentic_rag/storage/postgres_store.py†L370-L436】
3. **Instrument tracing/metrics** – Enable `FastAPIInstrumentor`, configure OTLP exporters, and expose standardized Prometheus metrics for request latency and errors.【F:src/api/main.py†L39-L147】【F:docker-compose.monitoring.yml†L4-L165】
4. **Add auth middleware** – Introduce API key or JWT/OAuth using configuration scaffolding in `src/config/settings.py` to protect critical routes.【F:src/config/settings.py†L79-L200】

## Phase 3 – Enterprise Readiness (Weeks 7–10)
1. **Multi-tenant controls** – Implement Supabase/Postgres schema or row-level isolation, extend settings to map tenants, and enforce in `PostgresStore`/`GraphSearch` queries.【F:src/agentic_rag/storage/postgres_store.py†L451-L754】【F:src/config/settings.py†L93-L200】
2. **CDC/Sync Services** – Build background worker (Celery/Async task) processing `graph_sync_queue` to guarantee idempotent Neo4j updates and retries.【F:src/agentic_rag/storage/postgres_store.py†L370-L436】
3. **Benchmark harness** – Automate ingestion of synthetic corpora and run latency/recall measurements to validate SLA (see `BENCHMARK_PLAN.md`).
4. **Security & Compliance** – Integrate secrets manager, add audit logging, run CI security scans (Bandit/Safety/pip-audit) as gates and document CVE exceptions.【F:Makefile†L35-L40】【F:pyproject.toml†L54-L117】
