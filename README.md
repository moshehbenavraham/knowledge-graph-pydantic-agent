# Base Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Pydantic AI](https://img.shields.io/badge/Pydantic-AI-blue)](https://ai.pydantic.dev/)

**Version 1.2.3** | **API Version 0.8.0** | **Package:** `luminari-ai-agent`

Base Agent is a unified AI assistant built on [Pydantic-AI](https://github.com/pydantic/pydantic-ai)
that combines retrieval augmented generation, knowledge graph search, long-term memory, and
extensible tooling. The project ships with a Streamlit UI, a production-ready FastAPI service with
streaming support, and supporting pipelines for ingestion and evaluation so the same agent logic
can run in multiple contexts.

## Table of Contents
- [Highlights](#highlights)
- [What's New in v1.2.3](#whats-new-in-v123)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Data Stores & Ingestion](#data-stores--ingestion)
- [Tools & Capabilities](#tools--capabilities)
- [Development Workflow](#development-workflow)
- [Project Layout](#project-layout)
- [Observability & Operations](#observability--operations)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Documentation & Support](#documentation--support)
- [Key Dependencies](#key-dependencies)
- [Contributing](#contributing)
- [License](#license)
- [Support & Contact](#support--contact)

## System Architecture

**This is an Agentic Graph RAG system** - NOT just vector search. The system requires BOTH components:

1. **PostgreSQL/Supabase** - Vector embeddings and document storage
2. **Neo4j Aura** - Knowledge graph (entities, relationships, temporal facts)

The graph component is **REQUIRED**, not optional. Without it, you lose:
- Entity extraction and relationship discovery
- Temporal reasoning and fact timelines
- Graph-based search strategies
- Hybrid search that combines vector + graph

## Highlights
- **Single unified agent** (`src/agent/unified_agent.py`) with intent-aware tool orchestration - one agent to rule them all
- **Agentic Graph RAG stack** with Supabase pgvector + Graphiti-powered Neo4j knowledge graph + intelligent hybrid routing (BOTH databases required)
- **Production-ready FastAPI** with versioned routes (`/api/v1`), SSE/WebSocket streaming, circuit breakers, and comprehensive middleware
- **Flexible Streamlit UI** with runtime-configurable modes (simple/standard/advanced) and CLI utilities
- **📊 GraphRAG Analytics Dashboard** - Real-time visualization of search patterns, knowledge graph structure, entity relationships, and system performance
- **📈 Persistent Analytics System (v1.1.0)** - Foundational observability infrastructure with PostgreSQL-backed event logging, performance tracking, and dashboard-ready queries
- **🔍 Comprehensive Application Logging (v1.2.2)** - Structured debug logging across entire UI and agent pipeline with immediate visibility into operations, performance, and errors (NEW!)
- **Type-safe centralized configuration** via Pydantic settings with full validation, supporting OpenAI, Anthropic, Ollama, and OpenRouter
- **Full observability stack**: Redis caching, structured logging (structlog), Prometheus metrics, OpenTelemetry tracing, and monitoring (Grafana + Jaeger)
- **mem0-powered memory**: Long-term and session memory for contextual conversations
- **Enterprise resilience**: Circuit breakers, retry logic with exponential backoff, rate limiting, and graceful degradation

## What's New in v1.2.3

Version 1.2.3 delivers **critical stability fixes and enhanced learning visibility** with comprehensive bug fixes for connection pooling, circuit breakers, and tool result display.

🔧 **Critical Stability Improvements**
- **Fixed PostgreSQL pool race condition**: Async lock ensures atomic singleton creation, preventing multiple uninitialized instances
- **Fixed circuit breaker logic**: Corrected inverted states (CLOSED=healthy, OPEN=broken) following standard patterns - Neo4j searches now work correctly
- **Fixed broken singleton recovery**: Failed initialization now retries instead of permanently breaking the connection manager
- **Fixed analytics logger initialization**: RAG tools now use singleton pattern, properly initializing analytics on first use
- **Eliminated deprecation warnings**: Updated Supabase client configuration and Pydantic AI model names

📚 **Enhanced Learning Experience**
- **Tool Return Visibility**: NEW! See what each tool actually returned in collapsible expanders
  - Displays after streaming completes with tool name in title
  - Smart truncation for long results (>2000 chars with preview)
  - Perfect for learning: inspect RAG chunks, graph relationships, web search results
  - Example: 12 tool returns visible in logs after running all tools
- **Improved error handling**: Empty tool arguments display "No arguments" instead of parse warnings

**What Was Fixed**:
- Race condition in connection manager singleton (async lock added)
- Circuit breaker states inverted (9 locations updated)
- Analytics logger bypassed in direct instantiation (now uses singleton)
- Supabase timeout/verify deprecation warnings (httpx client configured)
- Tool returns not visible in UI (post-stream extraction added)
- Image analysis deprecation (OpenAIModel → OpenAIChatModel)
- JSON parsing warnings for empty tool args (early validation)

**Impact**: System now stable, resilient, and provides excellent visibility into tool operations for learning and debugging.

See `docs/a-changelogs/current.md` for detailed technical notes.

---

## What's New in v1.1.0

Version 1.1.0 introduced **foundational observability infrastructure** for comprehensive system monitoring and analytics.

📈 **Persistent Analytics System** (Core Infrastructure)
- **Always-on event logging** to PostgreSQL with async, non-blocking architecture (<5ms overhead)
- **5 analytics tables** with monthly partitioning: search operations, tool usage, agent interactions, ingestion metrics, system health
- **Batched writes** (100 events or 5 seconds) with automatic retry and error handling
- **Materialized views** for dashboard-ready queries with pre-computed aggregations
- **Automatic initialization** with connection manager - zero configuration needed
- **Comprehensive monitoring**: latency tracking, cache hit rates, graph boost detection, error tracking
- **Maintenance functions** for partition management and view refreshes
- **Production-ready**: 30+ unit tests, complete documentation, graceful degradation

**Key Features**:
- Search analytics with intent detection and strategy usage
- Tool execution metrics with error tracking
- User-agent interaction logging with feedback
- Document ingestion performance tracking
- System health snapshots (database, cache, application metrics)

See `docs/analytics_system.md` for complete documentation.

**Previous Major Release: v0.9.0** - Unified agent architecture, centralized configuration, modular UI
See `CHANGELOG.md` for complete release history.

## 📊 Implementation Status (2025-10-14)

**Agentic Graph RAG System: 92% Complete**

✅ **Fully Operational Components**:
- PostgreSQL/Supabase vector storage with dual embeddings (1536d + 768d)
- Neo4j Aura knowledge graph with entity/fact storage
- Entity extraction (LLM-powered) - extracting 50-100+ entities per document
- Fact extraction (temporal reasoning) - 40-70+ facts per document
- Document ingestion pipeline with full async support
- Hybrid search combining vector + graph strategies
- Intent analysis with 5-strategy routing
- Circuit breakers, retry logic, and error handling

🟢 **In Progress**:
- Full ingestion of 21 test documents (~5/21 completed as of 19:32)
- 481+ entities extracted and stored in Neo4j
- 278+ facts (episodes) with temporal markers stored
- Integration testing with real ingested data

🟡 **Known Issues**:
- Relationship storage: Minor `'entity1_id'` KeyError (doesn't block ingestion)
- Test coverage: 18.45% (target: 75%)

**Next Steps**:
1. Complete full ingestion verification (entities, relationships, facts)
2. E2E testing with hybrid search on real data
3. Increase test coverage to 40%+
4. Production deployment validation

See `docs/projects_ongoing/AGENTIC_GRAPH_RAG_PLAN.md` for detailed progress tracking.

## Architecture Overview
- **Agent layer:** Single Pydantic-AI agent (`src/agent/unified_agent.py`) exposing async tools for RAG, SQL, web search, code execution, and image analysis
- **Retrieval layer:** `src/agentic_rag/` provides intent-aware routing (`search/`), semantic chunking (`ingestion/`), Graphiti knowledge extraction, and hybrid search; analytics system (`analytics/`) logs all operations for observability; legacy `src/rag_pipeline/` handles scheduled ingestion
- **Persistence:** Supabase (PostgreSQL + pgvector) stores documents, embeddings, analytics events, and mem0 memory; Neo4j + Graphiti manage the temporal knowledge graph
- **Interfaces:** Unified Streamlit UI (`src/ui/streamlit_app.py`) with modular feature handlers (`ui/features/`), FastAPI service (`src/api/main.py`) with endpoint routers (`api/endpoints/`), and CLI helpers in `examples/`
- **Configuration:** Type-safe Pydantic settings in `src/config/` with module-specific facades (agent, API, clients, UI) - all sourcing from `.env` (see `.env.example`)

## Prerequisites

### ⚠️ Deployment Options

**Choose your installation path based on needed features:**

| Feature | Lightweight | Full RAG |
|---------|-------------|----------|
| **Install command** | `pip install -e .[dev]` | `pip install -e .[dev,rag]` |
| **Disk space** | ~500MB | ~5.5GB |
| **Install time** | ~5 min | ~15 min |
| **RAM needed** | 2-4GB | 8GB+ |
| | |
| Vector search | ✅ | ✅ |
| OpenAI embeddings (API) | ✅ | ✅ |
| Web search | ✅ | ✅ |
| Image analysis | ✅ | ✅ |
| Code execution | ✅ | ✅ |
| Conversation memory | ✅ | ✅ |
| | |
| **Knowledge graph** | ❌ | ✅ |
| **Local embeddings** | ❌ | ✅ |
| **Entity extraction** | ❌ | ✅ |
| **Temporal reasoning** | ❌ | ✅ |
| **Document parsing** | ❌ | ✅ |

**💡 Recommendation:** Start with **Lightweight** to test the system, upgrade to **Full RAG** later if you need knowledge graph features.

**⚠️ Note:** Full RAG downloads 3.7GB of CUDA libraries (mostly unused on CPU) due to PyTorch including GPU support by default.

### Required
- **Python 3.11+** (tested with 3.11 and 3.12)
- **Supabase project** with `pgvector` extension enabled (or compatible PostgreSQL 14+ instance)
- **API access** for at least one LLM provider:
  - OpenAI (recommended for best performance)
  - Anthropic Claude
  - Ollama (local models)
  - OpenRouter (multi-model access)

### Optional (Recommended)
- **Neo4j 5.x** for knowledge graph search and entity relationships
- **Redis** for query result caching and performance optimization
- **Web search provider:**
  - Jina.ai API key (cleanest results)
  - Brave Search API key
  - Self-hosted SearXNG instance
- **Deno** for Model Context Protocol (MCP) server support

### Development Tools
- **Docker** for containerization and monitoring stack
- **Git** for version control
- **Make** for development workflow automation

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
   - Run the single migration file `src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql` in your Supabase SQL Editor (creates all tables, indexes, and functions in one step)
   - Provision a Neo4j database if graph search is enabled, then initialise it with `make neo4j-init` or `python -m src.agentic_rag.storage.migrations.neo4j_init`
4. **Run the agent**
   ```bash
   make run-ui            # Streamlit UI on http://localhost:8501
   ```

### Run the Unified Agent in Other Modes
- **Streamlit UI variants** (all use the same unified UI with different runtime modes)
  ```bash
  make run-ui-simple      # UI_MODE=simple (fast, no persistence)
  make run-ui             # UI_MODE=standard (default - streaming + tools)
  make run-ui-advanced    # UI_MODE=advanced (all features: memory, MCP, metrics)
  ```
- **FastAPI service**
  ```bash
  make run-api            # Starts FastAPI on http://localhost:8058
  ```
- **Document processing pipelines**
  ```bash
  make run-rag            # Classic RAG pipeline (local file and Google Drive watcher)
  make run-agentic-rag    # Agentic RAG pipeline (semantic chunking + knowledge extraction)
  ```
- **Example scripts**
  ```bash
  python examples/unified_agent_demo.py   # Interactive agent demonstration
  ```

## Configuration
All configuration is managed through type-safe Pydantic models in `src/config/` that load from `.env`. Environment variables are organized into logical groups in `.env.example`:

### Core Services
- **Supabase / Postgres:** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- **Neo4j:** `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- **Redis (optional):** `REDIS_URL`, `REDIS_PASSWORD`, `ENABLE_REDIS_CACHE`

### AI Models
- **LLM:** `LLM_PROVIDER` (openai/anthropic/ollama/openrouter), `LLM_MODEL`, `LLM_API_KEY`, `LLM_TEMPERATURE`
- **Embeddings:** `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`
- **Vision:** `VISION_LLM_CHOICE` for image analysis

### Feature Toggles
- `ENABLE_RAG`, `ENABLE_AGENTIC_RAG`, `ENABLE_GRAPH_SEARCH`
- `ENABLE_CODE_EXECUTION`, `ENABLE_WEB_SEARCH`, `ENABLE_IMAGE_ANALYSIS`
- `ENABLE_LONG_TERM_MEMORY` (mem0 integration)

### Search & Retrieval
- **Web search:** `JINA_API_KEY`, `BRAVE_API_KEY`, `SEARXNG_BASE_URL`, `WEB_SEARCH_PROVIDER`
- **Search settings:** `DEFAULT_SEARCH_LIMIT`, `VECTOR_SEARCH_THRESHOLD`, `ENABLE_SEARCH_CACHE`
- **Chunking:** `CHUNK_SIZE`, `CHUNK_OVERLAP`, `USE_SEMANTIC_CHUNKING`

### Application Settings
- **UI:** `UI_MODE` (simple/standard/advanced)
- **API:** `API_HOST`, `API_PORT`, `CORS_ORIGINS`
- **Observability:** `ENABLE_METRICS`, `PROMETHEUS_PORT`, `ENABLE_TRACING`, `JAEGER_ENDPOINT`
- **Performance:** `MAX_CONCURRENT_REQUESTS`, `REQUEST_TIMEOUT`, `RATE_LIMIT_PER_MINUTE`

**Important:** Updates to `.env` are automatically validated and reflected across all modules through the centralized Pydantic configuration system in `src/config/`.

### Complete Configuration Reference

All 68 configuration fields with types, defaults, and validation rules:

#### Application Environment (3 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `APP_ENV` | `development\|testing\|production` | `development` | Enum | Application environment |
| `LOG_LEVEL` | `str` | `INFO` | - | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `DEBUG` | `bool` | `false` | - | Debug mode flag |

#### Database Configuration - PostgreSQL/Supabase (3 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `DATABASE_URL` | `str` | `None` | Required in production | PostgreSQL database URL |
| `SUPABASE_URL` | `str` | `None` | Required if no DATABASE_URL | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | `str` | `None` | - | Supabase service role key |

#### Database Configuration - Neo4j (5 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `NEO4J_URI` | `str` | `bolt://localhost:7687` | - | Neo4j connection URI |
| `NEO4J_USER` | `str` | `neo4j` | - | Neo4j username |
| `NEO4J_PASSWORD` | `str` | `""` | Required in production if graph enabled | Neo4j password |
| `NEO4J_DATABASE` | `str` | `neo4j` | - | Neo4j database name |
| `NEO4J_ENCRYPTED` | `bool` | `true` | - | Use encrypted connection |

#### Database Configuration - Redis (2 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `REDIS_URL` | `str` | `None` | Required if cache enabled | Redis connection URL |
| `ENABLE_REDIS_CACHE` | `bool` | `false` | - | Enable Redis caching |

#### Connection Pool Settings - PostgreSQL (5 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `PG_POOL_MIN` | `int` | `5` | ≥ 1 | Minimum pool size |
| `PG_POOL_MAX` | `int` | `20` | ≥ 1, > PG_POOL_MIN | Maximum pool size |
| `PG_MAX_QUERIES` | `int` | `50000` | ≥ 100 | Max queries before connection reset |
| `PG_MAX_INACTIVE_LIFETIME` | `int` | `300` | ≥ 10 | Max inactive connection lifetime (seconds) |
| `PG_COMMAND_TIMEOUT` | `int` | `60` | ≥ 5 | Command timeout (seconds) |

#### Connection Pool Settings - Neo4j (3 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `NEO4J_POOL_SIZE` | `int` | `50` | ≥ 1 | Connection pool size |
| `NEO4J_CONNECTION_TIMEOUT` | `float` | `30.0` | > 0 | Connection timeout (seconds) |
| `NEO4J_MAX_RETRY_TIME` | `int` | `30` | ≥ 1 | Maximum retry time (seconds) |

#### Connection Pool Settings - Redis (2 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `REDIS_POOL_SIZE` | `int` | `10` | ≥ 1 | Connection pool size |
| `REDIS_SOCKET_TIMEOUT` | `int` | `5` | ≥ 1 | Socket timeout (seconds) |

#### Embedding Configuration (7 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `EMBEDDING_PROVIDER` | `openai\|nomic\|ollama\|cohere` | `openai` | Enum | Embedding model provider |
| `EMBEDDING_BASE_URL` | `str` | `https://api.openai.com/v1` | - | Embedding API base URL |
| `EMBEDDING_API_KEY` | `str` | `""` | Required in production | Embedding API key |
| `EMBEDDING_MODEL` | `str` | `text-embedding-3-small` | - | Embedding model name |
| `EMBEDDING_MODEL_CHOICE` | `str` | `None` | - | Alternative model (legacy) |
| `EMBEDDING_DIMENSION` | `int` | `1536` | > 0 | Vector dimension (1536 for OpenAI, 768 for Ollama) |
| `EMBEDDING_BATCH_SIZE` | `int` | `100` | 1-2048 | Embedding batch size |

#### LLM Configuration (8 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `LLM_PROVIDER` | `openai\|anthropic\|ollama\|openrouter` | `openai` | Enum | LLM provider |
| `LLM_BASE_URL` | `str` | `https://api.openai.com/v1` | - | LLM API base URL |
| `LLM_API_KEY` | `str` | `""` | Required in production | LLM API key |
| `LLM_MODEL` | `str` | `gpt-4o-mini` | - | LLM model name |
| `LLM_CHOICE` | `str` | `None` | - | Alternative model (legacy) |
| `EXTRACTION_MODEL` | `str` | `gpt-4o-mini` | - | Model for knowledge extraction |
| `LLM_TEMPERATURE` | `float` | `0.7` | 0.0-2.0 | Temperature setting |
| `LLM_MAX_TOKENS` | `int` | `2000` | 1-128000 | Maximum tokens for response |

#### Performance Settings (7 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `VECTOR_SEARCH_TIMEOUT` | `float` | `2.0` | > 0 | Vector search timeout (seconds) |
| `GRAPH_SEARCH_TIMEOUT` | `float` | `3.0` | > 0 | Graph search timeout (seconds) |
| `ENABLE_CACHING` | `bool` | `true` | - | Enable caching |
| `EMBEDDING_CACHE_SIZE` | `int` | `1000` | ≥ 0 | Embedding cache size |
| `EMBEDDING_CACHE_TTL` | `int` | `3600` | ≥ 0 | Embedding cache TTL (seconds) |
| `GRAPH_CACHE_SIZE` | `int` | `500` | ≥ 0 | Graph cache size |
| `GRAPH_CACHE_TTL` | `int` | `1800` | ≥ 0 | Graph cache TTL (seconds) |

#### Feature Flags (4 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `ENABLE_GRAPH` | `bool` | `true` | - | Enable graph database features |
| `ENABLE_PARALLEL_SEARCH` | `bool` | `true` | - | Enable parallel search execution |
| `ENABLE_TRACING` | `bool` | `false` | - | Enable OpenTelemetry tracing |
| `HOT_RELOAD` | `bool` | `false` | - | Enable hot reload for development |

#### Ingestion Settings (6 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `CHUNK_SIZE` | `int` | `1000` | 100-10000 | Document chunk size |
| `CHUNK_OVERLAP` | `int` | `200` | ≥ 0, < CHUNK_SIZE | Chunk overlap size |
| `MAX_ENTITIES_PER_CHUNK` | `int` | `10` | 1-100 | Maximum entities per chunk |
| `MAX_FACT_LENGTH` | `int` | `500` | 50-2000 | Maximum fact length |
| `USE_SEMANTIC_CHUNKING` | `bool` | `true` | - | Use semantic chunking |
| `GRAPH_BATCH_SIZE` | `int` | `10` | 1-100 | Graph operation batch size |

#### API Configuration (3 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `API_HOST` | `str` | `0.0.0.0` | - | API server host |
| `API_PORT` | `int` | `8058` | 1-65535 | API server port |
| `CORS_ORIGINS` | `str` | `http://localhost:3000` | - | CORS allowed origins (comma-separated) |

#### UI Configuration (1 field)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `UI_MODE` | `simple\|standard\|advanced` | `standard` | Enum | UI display mode |

#### Web Search Configuration (4 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `WEB_SEARCH_PROVIDER` | `jina\|brave\|searxng` | `None` | Enum | Preferred web search provider |
| `JINA_API_KEY` | `str` | `None` | - | Jina.ai API key |
| `BRAVE_API_KEY` | `str` | `None` | - | Brave Search API key |
| `SEARXNG_BASE_URL` | `str` | `None` | - | SearXNG instance URL |

#### Circuit Breaker Settings (3 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `int` | `5` | ≥ 1 | Failures before circuit opens |
| `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `int` | `60` | ≥ 10 | Recovery timeout (seconds) |
| `CIRCUIT_BREAKER_HALF_OPEN_REQUESTS` | `int` | `3` | ≥ 1 | Requests allowed in half-open state |

#### Tracing Configuration (2 fields)

| Variable | Type | Default | Validation | Description |
|----------|------|---------|------------|-------------|
| `JAEGER_HOST` | `str` | `localhost` | - | Jaeger agent host |
| `JAEGER_PORT` | `int` | `6831` | - | Jaeger agent port |

**Total: 68 configuration fields** organized in 17 categories. See `.env.example` for complete examples.

## Data Stores & Ingestion

### Storage Architecture
- **Supabase (PostgreSQL + pgvector):** Primary store for full document content, embeddings (1536d for OpenAI, 768d for Ollama), and SQL-backed tools. Initialize with single migration file: `src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql`
  - **Dual backend support:** Direct PostgreSQL (primary, optimal performance) with automatic fallback to REST API (when ports 5432/6543 blocked by firewalls/VPNs)
  - PostgreSQL via asyncpg with connection pooling: `src/agentic_rag/storage/postgres_store.py`
  - REST API via HTTPS (port 443): `src/agentic_rag/storage/supabase_rest_store.py` (automatic fallback)
- **Neo4j + Graphiti:** Temporal knowledge graph storing entities, relationships, and facts with timestamps. Initialize with `make neo4j-init` or `python -m src.agentic_rag.storage.migrations.neo4j_init`
- **mem0:** Session and long-term memory for conversational context, configured via `src/clients/memory.py`
- **Redis (optional):** Query result caching with configurable TTL - enable with `ENABLE_REDIS_CACHE=true`

### Ingestion Pipelines
Two complementary pipelines are available:

1. **Classic RAG Pipeline** (`src/rag_pipeline/pipeline.py`)
   - Scheduled file watching and ingestion
   - Google Drive integration
   - Simple chunking with embeddings
   - Run with `make run-rag`

2. **Agentic RAG Pipeline** (`src/agentic_rag/ingestion/pipeline.py`)
   - Semantic chunking with LLM-powered boundary detection
   - Graphiti-driven entity and relationship extraction
   - Dual storage (PostgreSQL content + Neo4j graph)
   - **Intelligent storage backend selection:** Tries PostgreSQL first, auto-falls back to REST API if connection blocked
   - Run with `make ingest` or `python -m src.agentic_rag.ingestion ingest [--rest-api]`

**Ingestion Commands:**
```bash
make ingest                                        # Default: Auto-fallback (tries PostgreSQL → REST API)
python -m src.agentic_rag.ingestion ingest        # Same as above
python -m src.agentic_rag.ingestion ingest --rest-api  # Force REST API mode
```

See `docs/DB_AND_RAG.md` and `docs/TROUBLESHOOTING.md` for detailed ingestion examples, storage backend selection, and network troubleshooting.

## Tools & Capabilities

The unified agent (`src/agent/unified_agent.py`) provides 12 comprehensive tools through async functions decorated with `@super_agent.tool`:

### Search & Retrieval
- **`smart_search(query, limit)`** – Primary search tool with intent-aware routing (5 strategies: VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, TEMPORAL, ENTITY_FOCUSED) that automatically selects optimal approach. Returns rich results with chunks, entities, and facts.
- **`query_knowledge_graph(entity_name, query_type, limit)`** – Direct knowledge graph queries for entity exploration, relationship discovery, and temporal facts. Query types: entity_facts, entity_relationships, temporal_facts.
- **`retrieve_documents(query, limit)`** – Simple vector similarity search via Supabase pgvector for straightforward content retrieval.
- **`comprehensive_search(query, use_vector, use_graph, max_results)`** – Parallel multi-strategy search that executes all search types and intelligently combines results.
- **`iterative_search(query, max_iterations)`** – Multi-step iterative search for complex queries requiring refinement and exploration.
- **`list_all_documents()`** – Browse available documents with metadata including document IDs, file paths, types, and schema information.
- **`get_full_document(document_id)`** – Retrieve complete document content by ID with all chunks combined.

### Data Access & Analysis
- **`execute_sql(sql_query)`** – Secure read-only SQL execution via Supabase RPC with query validation. Use for data analysis and aggregations.
- **`query_tabular_data(sql_query)`** – Execute SQL queries on uploaded CSV/Excel datasets stored in document_rows table. Includes detailed usage patterns.

### External Integration
- **`search_web(query)`** – Multi-provider web search (Jina.ai → Brave Search → SearXNG) with automatic failover for current information.
- **`analyze_image(document_id, analysis_query)`** – Vision model integration for image understanding, OCR, object detection, and scene analysis.

### Code Execution
- **`execute_python_code(code)`** – Sandboxed Python execution using RestrictedPython with whitelisted modules for calculations and data transformation.

### Memory & Context
- **mem0 integration** – Automatic session and long-term memory with semantic search over past conversations
- **Knowledge extraction** – Graphiti-powered entity, relationship, and temporal fact extraction feeding the knowledge graph

All tools include comprehensive error handling, input validation, and structured logging for production use. See `src/agent/unified_agent.py` for detailed tool signatures and docstrings.

## UI Features

### Interactive Streamlit Dashboard

The Streamlit UI (`src/ui/streamlit_app.py`) provides two main interfaces accessible via sidebar navigation:

#### 💬 Chat Interface
- Runtime-configurable modes: Simple, Standard, Advanced
- Real-time streaming responses with tool visibility
- File upload support (documents, images, tabular data)
- Conversation export (JSON format)
- mem0 memory integration (Advanced mode)

#### 📊 GraphRAG Analytics Dashboard (Available in Standard/Advanced modes)

Real-time visualization and analytics for your Agentic RAG system:

**Search Analytics**
- Total searches, average latency, top strategy metrics
- Search strategy distribution charts (VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, etc.)
- Graph boost rate tracking

**Intent Analysis**
- Query intent distribution pie charts
- Strategy usage visualizations
- Real-time updates from IntentAnalyzer

**Knowledge Graph Visualization**
- **Interactive network graph with pyvis** - Neo4j Enterprise-style visualization
- **Draggable nodes** - Click and drag individual nodes to reposition and explore relationships
- **Pan and zoom** - Click-drag background to pan, scroll to zoom in/out
- **Physics simulation** - ForceAtlas2 algorithm with natural node repulsion and spring forces
- **Multiple layouts** - Force-directed (default), hierarchical, and circular via dropdown
- **Color-coded entities** - 8 distinct colors by type (person, company, organization, location, event, technology, product, concept)
- **Dynamic node sizing** - Node size scales with connection count (15-50px range)
- **Adjustable entity limit** - 10-200 entities with optimized rendering
- **Rich tooltips** - Hover to see entity name, type, connections, and interaction hints
- **Navigation controls** - Built-in pan/zoom buttons and keyboard navigation

**Entity Explorer**
- Top 20 most connected entities in sortable table
- Entity timeline viewer showing temporal facts
- Click-through navigation for detailed entity information

**Performance Metrics**
- Query latency breakdown (Vector, Graph, Total)
- Cache hit rate and database connection pool stats
- Detailed PostgreSQL and Neo4j metrics
- Real-time monitoring with 30-second cache refresh

**Access:** Navigate to "📊 Dashboard" in the sidebar after starting the UI:
```bash
make run-ui              # Standard mode (recommended)
make run-ui-advanced     # Advanced mode with all features
```

## API Reference

The FastAPI service (`src/api/main.py`) exposes 24+ production endpoints across multiple routers. API documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running the API server.

### Core Endpoints

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/` | API information and documentation links | - | JSON with API metadata and endpoint listing |
| GET | `/api/v1/status` | System status and component health | - | StatusResponse with database/cache health |
| GET | `/metrics` | Prometheus metrics exposition | - | Prometheus format metrics |
| DELETE | `/api/v1/cache` | Clear cache entries (supports patterns) | `?pattern=*` | Success message |

### Chat Endpoints (`/api/v1/chat`)

| Method | Path | Purpose | Request Body | Response |
|--------|------|---------|--------------|----------|
| POST | `/api/v1/chat` | Synchronous chat with caching | `ChatRequest` | `ChatResponse` with sources and metrics |
| POST | `/api/v1/chat/stream` | Server-Sent Events streaming chat | `ChatRequest` | SSE stream of response chunks |
| WebSocket | `/api/v1/chat/ws` | Bidirectional WebSocket chat | JSON messages | Real-time streaming responses |
| POST | `/api/v1/chat/feedback` | Submit user feedback on response | `FeedbackRequest` | `FeedbackResponse` with feedback ID |
| GET | `/api/v1/chat/sessions/{session_id}/history` | Get session conversation history | `?limit=50` | List of messages with metadata |

**ChatRequest Schema:**
```json
{
  "message": "Your question here",
  "session_id": "optional-session-id",
  "search_strategy": "adaptive",
  "include_sources": true,
  "stream": false,
  "max_tokens": 2000,
  "temperature": 0.7
}
```

### Search Endpoints (`/api/v1/search`)

| Method | Path | Purpose | Query Parameters | Response |
|--------|------|---------|------------------|----------|
| POST | `/api/v1/search` | Unified search (vector/hybrid/adaptive) | - | `SearchResponse` with results and entities |
| GET | `/api/v1/search/suggest` | Query autocomplete/suggestions | `?query=prefix&limit=5` | List of suggestions |
| GET | `/api/v1/search/entities/{entity_name}` | Get entity information from graph | - | Entity properties and relationships |
| GET | `/api/v1/search/relationships` | Find relationship paths between entities | `?entity1=X&entity2=Y&max_depth=3` | Relationship path data |

**SearchRequest Schema:**
```json
{
  "query": "search query text",
  "search_type": "adaptive",
  "limit": 10,
  "threshold": 0.7,
  "filters": {}
}
```

### Document Endpoints (`/api/v1/documents`)

| Method | Path | Purpose | Parameters | Response |
|--------|------|---------|------------|----------|
| POST | `/api/v1/documents` | Ingest new document with knowledge extraction | `IngestRequest` body | `IngestResponse` with document_id and stats |
| GET | `/api/v1/documents` | List documents with pagination | `?page=1&page_size=20&source_filter=` | `DocumentListResponse` with pagination |
| GET | `/api/v1/documents/{document_id}` | Get full document content | `?include_chunks=false` | `DocumentContent` with metadata |
| DELETE | `/api/v1/documents/{document_id}` | Delete document and associated data | - | Status confirmation |
| PATCH | `/api/v1/documents/{document_id}` | Update document metadata | `title` and/or `metadata` in body | Updated document info |
| POST | `/api/v1/documents/{document_id}/reindex` | Regenerate embeddings and knowledge | - | Reindex status |
| GET | `/api/v1/documents/{document_id}/stats` | Get document statistics | - | Chunk, entity, and relationship counts |

**IngestRequest Schema:**
```json
{
  "content": "document text content",
  "title": "Document Title",
  "source": "file_path_or_url",
  "metadata": {}
}
```

### Analytics Endpoints (`/api/v1/analytics`)

| Method | Path | Purpose | Query Parameters | Response |
|--------|------|---------|------------------|----------|
| GET | `/api/v1/analytics/search-metrics` | Search performance metrics | `?window=7d` (24h/7d/30d) | Aggregated search statistics |
| GET | `/api/v1/analytics/intent-distribution` | Query intent distribution | `?window=7d` | Intent percentages |
| GET | `/api/v1/analytics/performance-metrics` | Latency and cache statistics | `?window=7d` | Performance breakdown |
| GET | `/api/v1/analytics/time-series` | Time-series trending data | `?window=7d&metric=searches` | Time-stamped data points |
| GET | `/api/v1/analytics/tool-usage` | Tool execution metrics | `?window=7d` | Per-tool usage stats |
| GET | `/api/v1/analytics/agent-interactions` | User-agent interaction metrics | `?window=7d` | Interaction statistics |
| GET | `/api/v1/analytics/health` | Analytics service health check | - | Service health status |

### Example API Usage

```bash
# Synchronous chat request
curl -X POST http://localhost:8058/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is OpenAI?", "include_sources": true}'

# Streaming chat with SSE
curl -N http://localhost:8058/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain RAG systems", "stream": true}'

# Hybrid search
curl -X POST http://localhost:8058/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI funding trends", "search_type": "hybrid", "limit": 10}'

# Ingest document
curl -X POST http://localhost:8058/api/v1/documents \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Document text here...",
    "title": "My Document",
    "source": "/path/to/doc.txt"
  }'

# Get search analytics
curl http://localhost:8058/api/v1/analytics/search-metrics?window=24h

# Check system status
curl http://localhost:8058/api/v1/status

# Get Prometheus metrics
curl http://localhost:8058/metrics
```

### Authentication & Security

- **Current version**: No authentication required (development mode)
- **Production**: Add authentication middleware (JWT/API keys) before deployment
- **Rate limiting**: 60 requests/minute per IP (configurable in middleware)
- **CORS**: Configured via `CORS_ORIGINS` environment variable
- **Security headers**: Automatic security headers added by middleware

See `docs/operations/API_RUNBOOK.md` for detailed operational procedures, troubleshooting, and production deployment guidelines.

## Development Workflow

### Core Development
```bash
make setup           # Install editable package + pre-commit hooks
make check           # Run all checks: Ruff, mypy, pytest
make format          # Auto-format with Black and Ruff
make lint            # Verify formatting and linting
make test            # Run pytest suite
make test-coverage   # Pytest with coverage report (htmlcov/)
make security        # Security audit: Bandit, Safety, pip-audit
make clean           # Remove Python build artifacts
```

### Database Operations
```bash
make db-setup        # Initialize database schema
make db-migrate      # Run Alembic migrations
make db-rollback     # Rollback last migration
make db-history      # Show migration history
make db-revision     # Create new migration
make neo4j-init      # Initialize Neo4j knowledge graph
make ingest          # Ingest documents into Agentic RAG
make ingest-clean    # Clean ingest (reset existing data)
```

### Performance & Testing
```bash
make load-test           # Run Locust load tests (with UI)
make load-test-headless  # Headless load testing
make stress-test         # High-load stress testing
make profile             # Profile API performance
make profile-memory      # Memory profiling
```

### Docker & Monitoring
```bash
make docker-build    # Build Docker image
make docker-run      # Run containerized application
make docker-stop     # Stop Docker containers
make monitoring-up   # Start Prometheus + Grafana + Jaeger
make monitoring-down # Stop monitoring stack
make monitoring-logs # View monitoring logs
```

### Redis Operations
```bash
make redis-cli       # Open Redis CLI
make redis-flush     # Flush Redis cache
```

### CI/CD Best Practices
- **Pre-commit hooks:** Automatically run Black, Ruff, and validation on commit
- **Before PR:** Run `make check` locally to ensure all tests and linting pass
- **Coverage requirement:** 75% minimum (enforced in `pyproject.toml`)
- **Commit style:** Use Conventional Commits (e.g., `feat:`, `fix:`, `docs:`)

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
├── docker/                   # Containerisation assets
├── supabase/                 # Supabase CLI configuration
├── examples/                 # Sample scripts (e.g. unified_agent_demo.py)
└── scripts/, api_collections/, migrations/ and more supporting assets
```

## Observability & Operations
- **Application Logging (v1.2.2)**: Comprehensive structured logging via `structlog` across entire UI and agent pipeline with real-time execution tracking, event counters, and debug filtering. See `CLAUDE.md` section "Application Logging & Debugging" for complete guide.
  - Handler initialization and lifecycle tracking
  - Session management (mode switches, feature toggles, page navigation)
  - Agent execution flow (input → handler → agent → tools → response)
  - Streaming events (chunk counts, tool calls, memory operations)
  - Error context with state snapshots
  - Usage: `make run-ui | grep "keyword"` or `LOG_LEVEL=DEBUG make run-ui`
- **Analytics System (v1.1.0)**: Persistent event logging to PostgreSQL with search metrics, tool usage, agent interactions, and system health tracking. Dashboard-ready materialized views for performance analysis.
- **Metrics & Monitoring**: Prometheus metrics (`/metrics`) for API usage, latency, cache hits, and LLM utilisation.
- **Tracing**: Optional OpenTelemetry tracing with Jaeger integration (`ENABLE_TRACING=true`).
- **Monitoring Stack**: Optional Prometheus + Grafana + Jaeger via `docker-compose.monitoring.yml` and `make monitoring-*` targets.
- **Resilience**: Rate limiting, caching, circuit breaker helpers in `src/utils/`.

## Testing & Quality Assurance

### Test Suite Overview
The project includes comprehensive testing at multiple levels:

**Unit Tests** (`tests/unit/`)
- Core functionality tests with mocked dependencies
- Run with `make test` or `pytest tests/unit/ -v`
- Coverage target: >75%

**Integration Tests** (`tests/integration/`) ✨ **NEW in Phase 4.5**
- 50+ tests against live databases (PostgreSQL, Neo4j)
- Full API workflow validation
- Storage layer CRUD operations
- Search strategy performance tests
- Run with `pytest tests/integration/ -v`
- Requires test database configuration

**Load Tests** (`tests/load/`) ✨ **NEW in Phase 4.5**
- Locust-based performance testing
- SLO validation (Chat P50<500ms, P95<1500ms, Search P50<200ms)
- Automated performance analysis and reporting
- Run with `make load-test` or `locust -f tests/load/locustfile.py`

### Running Tests
```bash
# Unit tests (fast, no dependencies)
make test
pytest tests/unit/ -v

# Integration tests (requires test databases)
pytest tests/integration/ -v

# Phase 1 infrastructure tests (requires real PostgreSQL + Neo4j)
unset TESTING  # Use real environment, not test mocks
pytest tests/test_phase1_infrastructure.py -v --no-cov

# Load tests (requires running API)
make load-test             # Interactive web UI
make load-test-headless    # Headless mode with reports

# All checks (lint + test + security)
make check
```

### Event Loop Configuration (Async Tests)
**Important**: Tests with async database operations require module-scoped event loops to avoid "Task attached to a different loop" errors. This is configured in `pyproject.toml`:

```toml
asyncio_default_fixture_loop_scope = "module"
```

Tests that use asyncpg pools must use `@pytest.mark.asyncio(loop_scope="module")` on test classes. See `docs/TESTING_GUIDE.md` for details

# Coverage report
make test-coverage         # Generates htmlcov/ directory
```

### Quality Enforcement
- Pre-commit hooks enforce formatting (`Black`) and linting (`Ruff`)
- Minimum test coverage: 75% (enforced by `pytest-cov`)
- Type checking with `mypy` (where configured)
- Security scanning with `bandit` and `safety`

### Continuous Integration
Integration and load tests can be added to CI pipelines. See `docs/operations/API_RUNBOOK.md` for recommended CI configuration.

## Documentation & Support

### Comprehensive Documentation
The `docs/` directory contains detailed guides for all aspects of the project:

- **Getting Started:** `INSTALL.md`, `CONFIGURATION.md`, `USAGE.md`
- **Architecture:** `ARCHITECTURE.md`, `DB_AND_RAG.md`, `architecture_diagrams.md`
- **Development:** `EXAMPLES.md`, `TESTING.md`, `TOOL_USAGE_PATTERNS.md`, `AGENTIC_CODER_GUIDE.md`
- **Operations:** `DEPLOYMENT.md`, `PERFORMANCE.md`, `TROUBLESHOOTING.md`, `operations/API_RUNBOOK.md` ✨ **NEW**
- **Agentic RAG:** `AGENTIC_RAG_INTRO.md` - comprehensive guide to the knowledge graph system
- **Product:** `PRD.md` - product requirements and roadmap
- **History:** `CHANGELOG.md` - version history and release notes
- **Design Notes:** `docs/projects_ongoing/` - ongoing design decisions and experiments

### Quick Links
- **Troubleshooting:** `docs/TROUBLESHOOTING.md`
- **API Documentation:** Auto-generated Sphinx docs in `docs_sphinx/`
- **Configuration Reference:** Complete `.env.example` with all variables documented

## Key Dependencies

### Core Framework
- **[Pydantic AI](https://ai.pydantic.dev/)** ≥0.1.2 - Agent framework with type-safe tooling
- **[Pydantic](https://docs.pydantic.dev/)** ≥2.5.0 - Data validation and settings management
- **[Streamlit](https://streamlit.io/)** ≥1.44.0 - Interactive web UI

### AI & ML
- **[OpenAI](https://github.com/openai/openai-python)** ≥1.75.0 - OpenAI API client
- **[Anthropic](https://github.com/anthropics/anthropic-sdk-python)** ≥0.49.0 - Claude API client
- **[mem0ai](https://mem0.ai/)** ≥0.0.10 - Long-term memory management
- **[sentence-transformers](https://www.sbert.net/)** ≥3.3.1 - Local embeddings (optional)

### Data & Storage
- **[Supabase](https://supabase.com/)** ≥2.3.0 - PostgreSQL client with pgvector support
- **[Neo4j](https://neo4j.com/)** ≥5.28.0 - Graph database driver
- **[graphiti-core](https://github.com/getzep/graphiti)** ≥0.1.0 - Knowledge graph extraction
- **[Redis](https://redis.io/)** ≥5.0.0 - Caching layer
- **[asyncpg](https://github.com/MagicStack/asyncpg)** ≥0.28.0 - Async PostgreSQL driver

### API & Web
- **[FastAPI](https://fastapi.tiangolo.com/)** ≥0.104.0 - REST API framework
- **[httpx](https://www.python-httpx.org/)** ≥0.28.0 - Async HTTP client
- **[Uvicorn](https://www.uvicorn.org/)** ≥0.24.0 - ASGI server

### Observability
- **[structlog](https://www.structlog.org/)** ≥24.0.0 - Structured logging
- **[prometheus-client](https://github.com/prometheus/client_python)** ≥0.19.0 - Metrics collection
- **[opentelemetry](https://opentelemetry.io/)** - Distributed tracing

### Development
- **[pytest](https://pytest.org/)** ≥7.4.0 - Testing framework
- **[Black](https://black.readthedocs.io/)** ≥24.0.0 - Code formatter
- **[Ruff](https://docs.astral.sh/ruff/)** ≥0.8.0 - Fast Python linter
- **[mypy](https://mypy-lang.org/)** ≥1.8.0 - Static type checker

See `pyproject.toml` for the complete dependency list.

## Contributing

We welcome contributions! Here's how to get started:

1. **Fork and clone** the repository
   ```bash
   git clone https://github.com/yourusername/base_agent.git
   cd base_agent
   ```

2. **Create a feature branch** using Conventional Commits naming
   ```bash
   git checkout -b feat/your-feature-name
   # or: fix/bug-description, docs/update-readme, etc.
   ```

3. **Set up development environment**
   ```bash
   make setup          # Install dependencies and pre-commit hooks
   cp .env.example .env  # Configure environment
   ```

4. **Implement your changes**
   - Write clear, documented code following project style
   - Add or update tests for new functionality
   - Run `make check` to verify all tests and linting pass
   - Ensure coverage remains above 75%

5. **Commit using Conventional Commits**
   ```bash
   git commit -m "feat: add hybrid search caching"
   git commit -m "fix: resolve Neo4j connection timeout"
   git commit -m "docs: update configuration examples"
   ```

6. **Open a pull request**
   - Describe the purpose and motivation
   - Include testing evidence (screenshots, test output)
   - List any follow-up items or breaking changes
   - Reference related issues

### Contribution Guidelines
- **Code style:** Black (100 chars), Ruff linting, type hints required
- **Testing:** Add tests for new features, maintain 75%+ coverage
- **Documentation:** Update relevant docs in `docs/` and docstrings
- **Commits:** Use [Conventional Commits](https://www.conventionalcommits.org/)
- **Pre-commit:** Hooks will auto-format and validate before commit

## License

Distributed under the MIT License. See `LICENSE` for details.

## Support & Contact

### Getting Help
- **Documentation:** Start with `docs/CONFIGURATION.md` and `docs/TROUBLESHOOTING.md`
- **Issues:** Report bugs and request features via GitHub Issues
- **Discussions:** Ask questions and share ideas in GitHub Discussions
- **Examples:** Check `examples/` directory for usage patterns

### Community
- **Contributing:** See the Contributing section above
- **Code of Conduct:** Be respectful and constructive
- **Security:** Report security vulnerabilities privately via GitHub Security Advisories

---

**Built with ❤️ using [Pydantic AI](https://ai.pydantic.dev/)** | **Version 0.9.0** | **License: MIT**
