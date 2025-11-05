# Enterprise Trial Checklist

| Area | Item | Status | Evidence |
| --- | --- | --- | --- |
| Infrastructure | pgvector-enabled Postgres provisioned and migrations applied | ☐ | `001_enhanced_schema.sql` requires manual execution.【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L1-L200】 |
| Infrastructure | Neo4j initialized with Graphiti constraints | ☐ | Run `make neo4j-init` prior to trial.【F:Makefile†L147-L149】【F:src/agentic_rag/storage/migrations/neo4j_init.py†L17-L124】 |
| Application | FastAPI dependency bootstrap fixed (`PostgresStore`/`Neo4jStore` constructors wired) | ☐ | Current implementation fails at startup.【F:src/api/dependencies.py†L33-L138】 |
| Application | Graph search endpoints return real data (no TODO stubs) | ☐ | `/api/v1/search/entities` & `/relationships` placeholders must be replaced.【F:src/api/endpoints/search.py†L161-L223】 |
| Application | Document reindex/delete/stats maintain Neo4j/Postgres parity | ☐ | TODO markers remain in endpoints.【F:src/api/endpoints/documents.py†L236-L395】 |
| Security | AuthN/AuthZ strategy implemented (API key/OAuth) | ☐ | No auth middleware currently configured.【F:src/api/main.py†L105-L135】 |
| Security | Secrets supplied via secure channel (not plaintext Compose) | ☐ | Compose exposes sensitive env vars; integrate secrets manager.【F:docker-compose.yml†L10-L48】 |
| Observability | OTEL tracing + Prometheus metrics verified end-to-end | ☐ | Instrumentation optional; verify collectors receive spans/metrics.【F:src/api/main.py†L39-L110】【F:docker-compose.monitoring.yml†L4-L165】 |
| Quality | Full test suite/linters pass in CI (`make check`) | ☐ | Pytest, mypy, ruff defined in Makefile.【F:Makefile†L6-L34】 |
| Quality | Benchmark plan executed and baseline metrics recorded | ☐ | Follow `BENCHMARK_PLAN.md` to capture latency/recall baselines.【F:BENCHMARK_PLAN.md†L1-L60】 |
| Documentation | Runbook/operations docs reviewed with SRE | ☐ | `RUNBOOK.md` covers setup and health checks.【F:RUNBOOK.md†L1-L120】 |
