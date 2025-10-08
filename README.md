# Base Agent

Base Agent is a unified AI assistant built on [Pydantic-AI](https://github.com/pydantic/pydantic-ai)
that combines retrieval augmented generation, knowledge graph search, long-term memory, and
extensible tooling. The project ships with a Streamlit UI, a FastAPI service, and supporting
pipelines for ingestion and evaluation so the same agent logic can run in multiple contexts.

## Highlights
- Single asynchronous agent (`src/agent/unified_agent.py`) with intent-aware tool orchestration
- Agentic RAG stack with Supabase pgvector, Graphiti-powered Neo4j knowledge graph, and configurable hybrid routing
- Streamlit UI with simple/standard/advanced modes, FastAPI endpoints, and CLI utilities
- Centralised configuration via `.env` + Pydantic settings, supporting OpenAI, Anthropic, Ollama, and OpenRouter
- Observability built in: caching, structured logging, Prometheus metrics, and optional monitoring stack

## Architecture Overview
- **Agent layer:** Pydantic-AI agent exposing async tools for RAG, SQL, web search, code execution, and image analysis.
- **Retrieval layer:** `src/agentic_rag` and `src/rag_pipeline` provide ingestion, semantic chunking, embeddings, and hybrid search.
- **Persistence:** Supabase (PostgreSQL + pgvector) stores documents, embeddings, and mem0 memory; Neo4j + Graphiti handle the knowledge graph.
- **Interfaces:** Streamlit UI (`src/ui/streamlit_app.py`), FastAPI service (`src/api/main.py`), and CLI helpers in `examples/`.
- **Configuration:** `src/config/` modules source environment variables defined in `.env` (see `.env.example` for the full catalogue).

## Prerequisites
- Python 3.11 or newer
- Supabase project with the `pgvector` extension (or compatible Postgres instance)
- API access for your preferred LLM and embedding providers
- Optional: Neo4j 5.x for graph search, Brave Search or SearXNG for web search, Redis for caching
- Optional: Deno for the Model Context Protocol (MCP) code execution server

## Quick Start
1. **Clone and install**
   ```bash
   git clone <repository-url>
   cd base_agent
   make setup
   ```
2. **Create your environment configuration**
   ```bash
   cp .env.example .env
   # update .env with Supabase, LLM, embedding, and optional provider credentials
   ```
3. **Bootstrap data stores**
   - Run the SQL scripts under `sql/` in your Supabase instance (order: `documents.sql`, `document_metadata.sql`, `document_rows.sql`, `execute_sql_rpc.sql`, and `agentic_rag/schema.sql` if using the agentic pipeline).
   - Provision a Neo4j database if graph search is enabled, then initialise it with `python -m src.agentic_rag.storage.neo4j_store init`.
4. **Run the agent**
   ```bash
   make run-ui            # Streamlit UI on http://localhost:8501
   ```

### Run the Unified Agent in Other Modes
- **Streamlit UI variants**
  ```bash
  make run-ui-simple      # UI_MODE=simple
  make run-ui             # UI_MODE=standard (default)
  make run-ui-advanced    # UI_MODE=advanced
  make dev MODE=standard  # Streamlit with auto-reload
  ```
- **FastAPI service**
  ```bash
  make run-api            # Starts FastAPI on http://localhost:8058
  ```
- **Document processing**
  ```bash
  make run-rag                 # Local file and Google Drive watcher pipeline
  ```
- **Example script**
  ```bash
  python examples/unified_agent_demo.py
  ```

## Configuration
Environment variables are grouped in `.env.example`. Key sections include:
- **Supabase / Postgres:** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- **Neo4j:** `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `ENABLE_AGENTIC_RAG`
- **LLM & embeddings:** `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`
- **Web search:** `JINA_API_KEY`, `BRAVE_API_KEY`, `SEARXNG_BASE_URL`, `WEB_SEARCH_PROVIDER`
- **Feature toggles:** `ENABLE_RAG`, `ENABLE_GRAPH_SEARCH`, `ENABLE_CODE_EXECUTION`, `ENABLE_LONG_TERM_MEMORY`
- **UI & API:** `UI_MODE`, `API_HOST`, `API_PORT`, `CORS_ORIGINS`
- **Observability:** `ENABLE_METRICS`, `ENABLE_REDIS_CACHE`, `JAEGER_HOST`, `PROMETHEUS_PORT`

Settings are loaded through Pydantic models in `src/config/`, so updates to `.env` are automatically reflected across modules.

## Data Stores & Ingestion
- **Supabase (pgvector):** primary store for documents, embeddings, and SQL-backed tools. The SQL scripts in `sql/` create the required tables, functions, and agentic RAG schema.
- **Neo4j + Graphiti:** used for entity and relationship storage. Run `python -m src.agentic_rag.storage.neo4j_store init` after configuring environment variables.
- **mem0:** provides persistent and session memory, configured via `src/clients/memory.py`.
- **Optional caching:** enable Redis with `ENABLE_REDIS_CACHE=true` to speed up repeated queries.
- **Ingestion pipeline:** `src/rag_pipeline/pipeline.py` handles scheduled ingestion and watching; the agentic pipeline (`DocumentIngestionPipeline` in `src/agentic_rag/ingestion/pipeline.py`) uses Graphiti for entity/relationship extraction and can be invoked from custom scripts for semantic chunking + knowledge extraction (see `docs/DB_AND_RAG.md` for examples).

## Tools & Capabilities
- `smart_search` – intent-aware routing that combines vector, graph, and hybrid search strategies.
- `retrieve_relevant_documents`, `list_documents`, `get_document_content` – document exploration via Supabase.
- `execute_sql_query` – secure read-only SQL access to structured data.
- `execute_safe_code` – sandboxed Python execution.
- `web_search` – integrates Jina.ai, Brave Search, and SearXNG with automatic provider selection.
- `image_analysis` – forwards images to the configured multimodal model.
- Memory hooks – mem0-backed session and long-term memory surfaced in responses.
- Knowledge extraction – Graphiti-driven entity, relationship, and fact extraction powering the knowledge graph.

## Development Workflow
```bash
make setup           # Install editable package + pre-commit hooks
make check           # Ruff, mypy, pytest
make format          # Auto-format with Black and Ruff
make lint            # Formatting + lint verification
make test            # Run pytest suite
make test-coverage   # Pytest with coverage + htmlcov/
make security        # Bandit, Safety, pip-audit
make clean           # Remove Python build artifacts
```

- Additional commands include `make db-setup`, `make load-test`, and Docker targets (`make docker-build`, `make docker-run`, `make docker-stop`).
- CI expectations: run `make check` locally before opening a PR; coverage threshold is 75% (enforced in `pyproject.toml`).

## Project Layout
```
base_agent/
├── src/
│   ├── agent/                # Unified agent implementation
│   ├── agentic_rag/          # Agentic RAG pipelines, search, storage
│   ├── api/                  # FastAPI application
│   ├── clients/              # LLM, embedding, database, memory clients
│   ├── rag_pipeline/         # Classic ingestion pipeline
│   ├── tools/                # Tool definitions used by the agent
│   ├── ui/                   # Streamlit UI and feature handlers
│   └── utils/                # Caching, monitoring, rate limiting
├── tests/                    # pytest suites (mirrors runtime modules)
├── docs/                     # Architecture, configuration, installation guides
├── docs_sphinx/              # Sphinx documentation project
├── sql/                      # Supabase schema and functions
├── docker/                   # Containerisation assets
├── supabase/                 # Supabase CLI configuration
├── examples/                 # Sample scripts (e.g. unified_agent_demo.py)
└── scripts/, api_collections/, migrations/ and more supporting assets
```

## Observability & Operations
- Structured logging via `structlog` with JSON output (`LOG_FORMAT=json`).
- Prometheus metrics (`/metrics`) for API usage, latency, cache hits, and LLM utilisation.
- Optional monitoring stack (Prometheus, Grafana, Jaeger) via `docker-compose.monitoring.yml` and `make monitoring-*` targets.
- Rate limiting, caching, and circuit breaker helpers live in `src/utils/`.

## Testing & Quality Assurance
- Unit and integration tests use `pytest` with async fixtures; run `make test` or `pytest -k <pattern>`.
- Coverage reports are generated with `make test-coverage` and stored in `htmlcov/`.
- Pre-commit hooks enforce formatting (`Black`) and linting (`Ruff`). Remember to run `pre-commit run --all-files` if hooks are not installed.

## Documentation & Support
- Primary references live in `docs/`: `ARCHITECTURE.md`, `INSTALL.md`, `CONFIGURATION.md`, `USAGE.md`, `DB_AND_RAG.md`, and more.
- Additional design history is captured under `docs/projects_ongoing/`.
- Change history is tracked in `CHANGELOG.md`.
- For quick troubleshooting, consult `docs/TROUBLESHOOTING.md`.

## Contributing
1. Fork the repository and create a feature branch (`git checkout -b feat/<topic>`).
2. Run `make setup` to install dev dependencies and hooks.
3. Implement changes, update or add tests, and run `make check`.
4. Use Conventional Commit messages (e.g. `feat: add hybrid search metrics`).
5. Open a pull request describing the purpose, testing evidence, and follow-up items.

## License

Distributed under the MIT License. See `LICENSE` for details.

## Support & Contact
- Issues and feature requests: GitHub Issues
- Discussions and design feedback: GitHub Discussions
- Configuration questions: start with `docs/CONFIGURATION.md` before reaching out
