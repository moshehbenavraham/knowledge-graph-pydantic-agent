# Development Tooling Reference

The Agentic RAG codebase ships with a production-ready toolchain that covers code
quality, testing, security, performance analysis, and observability. This guide
captures the essentials that were previously tracked under
`docs/projects_ongoing/DEV_TOOLS.md` so everything relevant now lives in the
documentation root.

## Toolchain Snapshot (Updated 2024-12-26)

- **Core workflow**: `make dev-setup` installs Poetry (optional), pins pre-commit,
  and ensures all development dependencies are available.
- **Pre-commit hooks**: Managed via `pre-commit-config.yaml`; run with
  `make dev-check` or `pre-commit run --all-files`.
- **Git conventions**: Conventional Commits are enforced with Commitizen (`cz`)
  and pre-commit hooks.
- **CI coverage**: GitHub Actions workflows run quality, security, and
  performance suites (`.github/workflows/*`).

## Code Quality & Testing

| Category | Tools | Key Commands / Files |
|----------|-------|----------------------|
| Formatting & Linting | Black, Ruff, Docformatter | `make format`, `make lint`, `pyproject.toml` |
| Static Typing | MyPy | `make lint` (type step), `mypy.ini` |
| Unit & Async Tests | Pytest, pytest-asyncio, pytest-cov | `make test`, `make test-coverage`, `tests/` |
| Coverage Analysis | Coverage.py | `make test-coverage` (produces `htmlcov/`) |
| Security Scans | Bandit, Safety, pip-audit | `make security` |
| Multi-env Testing | tox (py311, py312, lint, security) | `make tox`, `tox.ini` |

## Operational Tooling

### Caching Layer
- Redis service defined in `docker-compose.yml` with supporting config in
  `redis.conf` (if present).
- Python integration in `src/utils/cache.py` with automatic in-memory fallback.
- Environment variables: `REDIS_URL`, `REDIS_PASSWORD`, `REDIS_MAX_CONNECTIONS`
  (see `docs/CONFIGURATION.md`).
- CLI helpers: `make redis-cli`, `make redis-flush`, `make redis-commander-up`
  (web UI at `http://localhost:8081` when running).

### Database Migrations
- Alembic configuration lives in `alembic.ini` and `migrations/`.
- Make targets: `make db-migrate`, `make db-rollback`, `make db-history`,
  `make db-revision`.
- Works with Supabase/PostgreSQL; see `docs/CONFIGURATION.md` and `docs/DB_AND_RAG.md`
  for connection details.

### Load & Benchmark Testing
- Locust suite under `tests/load/` with `locustfile.py`, `scenarios.py`,
  and result helpers.
- Commands: `make load-test`, `make load-test-headless`, `make stress-test`,
  plus composite `make full-test` (runs unit + load suites).
- Environment hints: `LOCUST_HOST`, `LOCUST_USERS`, `LOCUST_SPAWN_RATE`
  (documented in `.env.example`).

### Monitoring & Observability
- Prometheus, Grafana, Jaeger, and Redis Commander stack defined in
  `docker-compose.monitoring.yml`.
- Start/stop/log helpers: `make monitoring-up`, `make monitoring-down`,
  `make monitoring-logs`, `make full-monitoring`.
- FastAPI metrics emitting from `src/api/main.py`; OpenTelemetry tracing configured
  with Jaeger exporter.
- Default URLs when stack is running:
  - Prometheus: `http://localhost:9090`
  - Grafana: `http://localhost:3000` (admin/admin)
  - Jaeger: `http://localhost:16686`
  - Redis Commander: `http://localhost:8081` (admin/admin)

### Profiling & Performance Analysis
- `py-spy` driven profiles via `scripts/profile.py` with modes for API, UI, RAG,
  and tests.
- Make targets: `make profile-api`, `make profile-ui`, `make profile-rag`,
  `make profile-tests`, `make profile-memory`.
- Performance goals and tuning notes live in `docs/PERFORMANCE.md`.

## Developer Experience Enhancements

- **Poetry** (optional): Supported alongside pip; use
  `make poetry-install`, `make poetry-update`, `make poetry-lock`, or drop into a
  shell with `make poetry-shell`.
- **HTTPie CLI**: Quick API smoke testing via `make http-test`, `make http-chat`,
  `make http-search`; scripted examples in `tests/api_examples/httpie_examples.sh`.
- **API Collections**: Postman and Insomnia exports under `api_collections/` with
  Make targets `make api-test` and `make api-search`.
- **Docker Tooling**: Application and monitoring stacks run through the top-level
  `docker-compose*.yml` files; additional images built via `make docker-build`
  family targets.
- **Documentation toolchains**:
  - Sphinx project (`docs_sphinx/`) with `make docs-sphinx-build`,
    `make docs-sphinx-serve`.
  - MkDocs site configured by `mkdocs.yml` with `make docs-mkdocs-build`,
    `make docs-mkdocs-serve`.
  - Mermaid diagrams curated in `docs/architecture_diagrams.md`.

## Quick Command Reference

```bash
make dev-setup       # Install dev deps, Poetry, and pre-commit hooks
make dev-check       # Run linting, typing, tests, security in one pass
make dev-format      # Apply Black, Ruff, Docformatter
make dev-clean       # Remove caches, build artifacts, generated docs

make full-test       # Unit + coverage + load tests
make full-profile    # Generate flamegraphs for API/UI/RAG/test flows
make full-monitoring # Bring up full observability stack

make redis-commander-up   # Launch Redis management UI
make http-test            # HTTPie regression scenarios
make profile-api          # 30s API CPU profile (py-spy)
make tox                  # Matrix testing (py311/py312/lint/security)
```

## Success Metrics & Maintenance

- Target thresholds for latency, cache hit rates, and resource utilization are
  tracked in `docs/PERFORMANCE.md`; CI performance workflow located at
  `.github/workflows/performance.yml`.
- Daily/weekly maintenance expectations:
  - Monitor dashboards and alerts when monitoring stack is active.
  - Review load-test artifacts and profiling flamegraphs after major changes.
  - Update dependencies and rerun `make dev-check` on a weekly cadence.

## Related References

- Configuration details & environment variables: `docs/CONFIGURATION.md`,
  `.env.example`.
- Database schemas and RAG storage: `docs/DB_AND_RAG.md`, `sql/`.
- Troubleshooting and incident response: `docs/TROUBLESHOOTING.md`,
  `docs/operations/API_RUNBOOK.md`.
- Architecture diagrams & system overview: `docs/ARCHITECTURE.md`,
  `docs/architecture_diagrams.md`.

This document consolidates the development tooling notes that previously lived
under `docs/projects_ongoing/DEV_TOOLS.md`.
