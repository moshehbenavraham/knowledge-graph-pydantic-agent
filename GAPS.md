# Gap Analysis

## 1. Graphiti Usage Is Stubbed
- Evidence: Graphiti listed as optional dependency yet `GraphitiClient` wraps Neo4j directly and API routes return TODO payloads.【F:pyproject.toml†L78-L87】【F:src/agentic_rag/storage/graphiti_client.py†L15-L190】【F:src/api/endpoints/search.py†L161-L230】
- Impact: Target stack requires Graphiti ingest/search semantics (entity models, retrievers). Current implementation cannot leverage Graphiti features or guarantee schema compatibility.
- Remediation Steps:
  1. Replace custom `GraphitiClient` with official `graphiti_core` ingest/search classes (e.g., `GraphitiClient`, `KnowledgeStore`). Wire initialization inside dependency bootstrap and ingestion pipeline.【F:src/agentic_rag/ingestion/pipeline.py†L83-L166】
  2. Implement Graphiti ingest flow (episodes, facts, embeddings) using Graphiti-provided functions to ensure entity IDs align with Graphiti schema.
  3. Update `/api/v1/search/entities` and `/relationships` to call Graphiti retrievers (Cypher queries via Graphiti) and return real data.
- Estimate: 40–60 engineer hours.
- Risk: **Medium** – requires reworking ingestion/storage layers and validating data migrations.

## 2. FastAPI Dependency Initialization Fails
- Evidence: `init_dependencies` calls `PostgresStore()` and `Neo4jStore()` without required connection manager, causing runtime `TypeError` on startup.【F:src/api/dependencies.py†L33-L138】【F:src/agentic_rag/storage/postgres_store.py†L16-L24】【F:src/agentic_rag/storage/neo4j_store.py†L16-L23】
- Impact: API cannot boot, blocking all endpoints and automated testing.
- Remediation Steps:
  1. Inject `ConnectionManager` instance into `PostgresStore`/`Neo4jStore` constructors inside `init_dependencies` and ensure `ConnectionManager.initialize()` runs during startup.【F:src/agentic_rag/storage/connection_manager.py†L89-L200】
  2. Add startup smoke test (pytest) to catch missing constructor arguments.
- Estimate: 6–8 hours.
- Risk: **High** – production availability issue.

## 3. No First-party Postgres Deployment
- Evidence: Compose defines app, Neo4j, Redis, SearxNG; Postgres expected via external Supabase URL, yet migrations assume local control.【F:docker-compose.yml†L4-L158】【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L1-L200】
- Impact: Hard to reproduce target stack locally; analytics/graph sync functions rely on Postgres features (pgvector, extensions) not provisioned.
- Remediation Steps:
  1. Add Postgres + pgvector service to Compose with initialization scripts executing migrations.
  2. Provide Docker health checks and Makefile targets for migration/apply.
- Estimate: 10–14 hours.
- Risk: **Medium** – environment parity issue.

## 4. Graph Search Endpoints Unimplemented
- Evidence: `/api/v1/search/entities` and `/relationships` return static placeholders.【F:src/api/endpoints/search.py†L161-L223】
- Impact: Graph-only retrieval scenario from target stack is missing; unified agent cannot surface graph insights.
- Remediation Steps:
  1. Implement entity lookup via Graphiti/Neo4j (MATCH queries returning properties, relationships, episodes).
  2. Implement path-finding between entities with configurable depth/filters.
  3. Extend `GraphSearch` tests to cover new flows.【F:tests/agentic_rag/search/test_graph_search_comprehensive.py†L237-L287】
- Estimate: 16–24 hours.
- Risk: **Medium** – functionality gap.

## 5. Reindex & Graph Cleanup Workflows Missing
- Evidence: Document reindex endpoint has TODO, delete/stats endpoints skip graph operations.【F:src/api/endpoints/documents.py†L236-L395】
- Impact: Graph/Postgres consistency can drift; no automated re-embedding or graph purge support.
- Remediation Steps:
  1. Implement reindex routine invoking chunk regeneration, re-embedding, re-extraction, and Postgres update.【F:src/agentic_rag/ingestion/pipeline.py†L200-L384】
  2. Extend delete/stats to call Graphiti removal & counting helpers once Graphiti integration completed.
- Estimate: 20–30 hours.
- Risk: **Medium** – data consistency/maintenance issue.

## 6. Observability Integration Incomplete for API
- Evidence: Monitoring Compose stack exists but API lacks OTEL initialization (FastAPIInstrumentor optional import) and there is no automated metrics endpoint bridging to Prometheus other than manual `/metrics` route.【F:src/api/main.py†L39-L71】【F:docker-compose.monitoring.yml†L4-L165】
- Impact: Observability part of target stack (Jaeger/Prometheus) not fully wired into service runtime.
- Remediation Steps:
  1. Ensure OTEL instrumentation is enabled via settings toggle and document environment variables required for collectors.
  2. Add Prometheus FastAPI instrumentation (middleware/exposer) or integrate `prometheus_fastapi_instrumentator`.
- Estimate: 8–12 hours.
- Risk: **Low** – enhancements but valuable for enterprise readiness.
