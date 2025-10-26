# AGENTIC_CODER_GUIDE.md

**Last Updated:** 2025-10-08
**Agentic RAG Status:** Phase 3 (Agent Intelligence) - FULLY OPERATIONAL ✅

This file provides guidance to Agentic Coding Agents (such as Claude Code) when working with code in this repository.

## Project Overview

**Luminari Agent** is a unified AI assistant with Agentic RAG (Retrieval Augmented Generation) capabilities, combining vector search (PostgreSQL/Supabase + pgvector), knowledge graph (Neo4j + Graphiti), and intelligent routing. Built with Pydantic AI, it provides comprehensive tooling for document retrieval, web search, image analysis, SQL queries, and code execution.

**Phase 3 Completion Status (2025-10-08):**
- ✅ All critical ingestion pipeline issues resolved
- ✅ Graph search fully operational with proper API contracts
- ✅ Storage layers (PostgreSQL + Neo4j) working correctly
- ✅ Configuration system properly integrated across all components
- ✅ Ready for Phase 4 (API & Performance Optimization)

**Critical Architecture Principles**:
- **ONE unified agent** (`src/agent/unified_agent.py`) - NO multiple agent implementations
- **Centralized configuration** (`src/config/settings.py`) - NEVER use `os.getenv()` directly
- **Async-first** - All I/O operations use async/await patterns

## Common Development Commands

### Setup & Dependencies
```bash
make setup                # Install dependencies and pre-commit hooks
cp .env.example .env      # Configure environment (REQUIRED before running)
```

### Running the Application
```bash
# UI modes (Streamlit on port 8501)
make run-ui               # Standard mode (streaming + tools) - DEFAULT
make run-ui-simple        # Simple mode (fast, no persistence)
make run-ui-advanced      # Advanced mode (all features)

# API server (FastAPI on port 8058)
make run-api              # Start FastAPI server

# RAG pipeline
make run-rag              # Run document processing
make dev                  # Development mode with auto-reload
```

### Code Quality & Testing
```bash
make format               # Format code with Black + Ruff
make lint                 # Run Ruff linting
make test                 # Run test suite (pytest)
make test-coverage        # Run tests with coverage report (minimum 75% required)
make security             # Run security scans (Bandit, Safety, pip-audit)
make check                # Run all checks (lint + test + security)
```

### Running Single Tests
```bash
pytest tests/test_unified_agent.py -v                  # Test unified agent
pytest tests/test_phase2_search.py -k hybrid           # Test specific search strategy
pytest -k "test_rag" -v                                # Run all RAG-related tests
pytest tests/test_agent.py::test_specific_function -v  # Run specific test
pytest --lf                                            # Re-run last failed tests
pytest tests/ -v --tb=short                            # Detailed failure info
pytest tests/ -x                                       # Stop on first failure
```

### Database Operations
```bash
make neo4j-init          # Initialize Neo4j knowledge graph
make ingest              # Ingest documents into Agentic RAG
make ingest-clean        # Clean ingest (reset existing data)
```

### Docker Development
```bash
make docker-build        # Build Docker images
make docker-run          # Run full stack with Docker Compose
make docker-stop         # Stop all containers
make docker-test         # Run tests in containers
```

## High-Level Architecture

### 1. Configuration System (Critical!)

**NEVER use `os.getenv()` directly** - always use the centralized configuration:

```python
from src.config import get_settings
from src.config.agent import agent_config
from src.config.api import api_config

settings = get_settings()  # Main settings instance
llm_provider = settings.llm_provider
```

**Configuration hierarchy**:
- `src/config/settings.py` - Main Pydantic Settings (single source of truth)
- `src/config/agent.py` - Agent-specific facade
- `src/config/api.py` - API-specific facade
- `src/config/clients.py` - Client configuration facade

All settings load from `.env` with automatic validation and type conversion.

### 2. The Unified Agent System

**Only ONE agent exists**: `src/agent/unified_agent.py`

Key components:
- **UnifiedAgentDeps**: Dependency injection container for all agent needs
- **UNIFIED_SYSTEM_PROMPT**: Core instruction set for agent behavior
- **super_agent**: Main Pydantic AI agent instance with all tools

**DO NOT create separate agent files** - extend the unified agent instead.

Usage:
```python
from src.agent import super_agent, UnifiedAgentDeps, run_unified_agent
```

### 3. Dual Storage Strategy (Agentic RAG)

The system implements an **Agentic RAG** architecture combining two databases:

**PostgreSQL/Supabase** (content storage):
- Full document content with embeddings
- Vector similarity search via pgvector (1536d for OpenAI, 768d for Ollama)
- Tables: `documents`, `document_metadata`, `document_rows`
- Single source of truth for all content (99.6% of storage)

**Neo4j** (knowledge graph):
- Entity extraction and relationships (via Graphiti)
- Temporal facts with timestamps
- NO content duplication - only references PostgreSQL chunks via IDs
- Cypher queries for relationship discovery
- 0.4% storage overhead

### 4. Search Strategy Flow

1. **IntentAnalyzer** analyzes query → determines intent (VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, TEMPORAL, ENTITY_FOCUSED)
2. **smart_search** tool routes to optimal strategy:
   - `retrieve_documents` → Vector search (semantic similarity)
   - Graph search → Entity/relationship queries
   - `comprehensive_search` → Parallel execution + intelligent merging
3. Results ranked and returned to agent

**Intent Analysis Patterns**:
- Relationship keywords: "related", "connected", "works with", "owns", etc.
- Temporal markers: "when", "timeline", "history", "recently", dates
- Entity indicators: Proper nouns, capitalized terms
- Semantic keywords: "about", "explain", "understand", "what is"

**Hybrid Search Merging**:
- Runs vector + graph search in parallel
- Graph entities boost related vector results
- Normalized scoring across both sources
- Deduplication based on content similarity

### Search Strategies
- **Vector Search**: Semantic similarity using pgvector (sub-200ms)
- **Graph Search**: Entity/relationship traversal in Neo4j (sub-500ms)
- **Hybrid Search**: Parallel execution with intelligent result merging
- **Smart Search**: Automatic strategy selection based on query intent

### 5. Tool System

All tools are in `src/tools/` and follow async patterns:

- **RAG tools** (`rag.py`): `retrieve_documents`, `list_all_documents`, `get_full_document`
- **Web search** (`web_search.py`): `search_web` - Multi-provider support (Jina > Brave > SearXNG)
- **SQL queries** (`sql_query.py`): `execute_sql` - Read-only queries via Supabase RPC
- **Image analysis** (`image_analysis.py`): `analyze_image` - Vision model integration
- **Code execution** (`code_execution.py`): `execute_python_code` - RestrictedPython sandbox

**Tool Development Rules**:
- Must be async functions
- Use dependency injection (UnifiedAgentDeps)
- Comprehensive error handling with informative messages
- Security validation for all inputs (especially SQL/code)
- Clear docstrings with usage examples

### 6. UI System Architecture

**Single modular UI** in `src/ui/streamlit_app.py` with three modes:

- **Simple** (`UI_MODE=simple`): Basic chat, no streaming
- **Standard** (`UI_MODE=standard`): Streaming + tool visibility (default)
- **Advanced** (`UI_MODE=advanced`): Memory + MCP servers + metrics

**Feature handlers** in `src/ui/features/`:
- `base_handler.py` - Core chat functionality
- `streaming_handler.py` - Real-time streaming
- `memory_handler.py` - mem0 integration
- `mcp_handler.py` - MCP server support

**Add new features** by creating handlers, not new UI files.

### Key Components

#### Unified Super Agent (`src/agent/unified_agent.py`) ⭐ THE ONLY AGENT
- **The One Agent to Rule Them All** - Combines ALL capabilities
- Intelligent intent-based search routing using IntentAnalyzer (`src/agentic_rag/search/intent_analyzer.py`)
- Tools: smart_search, retrieve_documents, search_web, execute_sql, analyze_image, execute_python_code
- Advanced features: comprehensive_search, iterative_search, memory integration
- Web search with multiple providers (Jina, Brave, SearXNG)
- Usage: `from src.agent import super_agent, UnifiedAgentDeps, run_unified_agent`

#### Storage Layer
- `src/agentic_rag/storage/postgres_store.py`: Vector operations and content storage
- `src/agentic_rag/storage/neo4j_store.py`: Knowledge graph operations
- Connection pooling with circuit breakers for reliability

#### Ingestion Pipeline
- `src/agentic_rag/ingestion/pipeline.py`: Document processing orchestrator
- Semantic chunking with configurable size (default 1000 chars)
- Knowledge extraction using Graphiti for entities and relationships
- Documents go through: Chunking → Embedding generation → Knowledge extraction → Dual storage

## Important Configuration

### Environment Variables
Always check `.env.example` for required settings. **Copy `.env.example` to `.env` before running**:

- `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`: Required for database
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Required for knowledge graph
- `LLM_API_KEY` and `EMBEDDING_API_KEY`: Required for AI operations
- Web Search (configure one or more):
  - `JINA_API_KEY`: Jina.ai for clean web content extraction
  - `BRAVE_API_KEY`: Brave Search API
  - `SEARXNG_BASE_URL`: Self-hosted SearXNG instance
  - `WEB_SEARCH_PROVIDER`: Force specific provider (jina/brave/searxng)

**Never commit `.env` or generated credentials** - add new secrets to documentation in `docs/CONFIGURATION.md` instead.

### Database Setup
1. PostgreSQL/Supabase: Run SQL scripts in order: `documents.sql` → `document_metadata.sql` → `document_rows.sql` → `execute_sql_rpc.sql` → `agentic_rag/schema.sql`
2. Enable pgvector extension in Supabase dashboard
3. Neo4j: Use `make neo4j-init` or Docker deployment

### Database Schema

**PostgreSQL Tables (Supabase)**:
```sql
documents(id, content, metadata, embedding vector(1536))
document_metadata(id, document_id, key, value)
document_rows(id, document_id, row_data jsonb)
```

**Neo4j Graph Structure**:
```cypher
(Entity)-[:RELATIONSHIP]->(Entity)
(Fact {description, valid_from, valid_to, created_at})
```

**Important**: When using Ollama embeddings, change `vector(1536)` → `vector(768)` in all SQL scripts.

### Code Standards
- **Python version**: 3.11+ required
- **Line length**: 100 characters (Black formatter)
- **Type hints**: Required for all function signatures
- **Docstrings**: Google style for all public functions/classes
- **Imports**: Organized by Ruff (stdlib → third-party → local)
- **Async patterns**: Use `async`/`await` for all I/O operations
- **Test coverage**: 75% minimum (enforced by pytest-cov)
- **Naming conventions**: snake_case for modules/functions, PascalCase for classes
- **File size**: Never create files longer than 500 lines (refactor into modules)
- **Security**: Always use parameterized SQL queries
- **Testing**: Write tests for new features (expected use, edge cases, failure cases)

**Pre-commit hooks enforce**:
- Black formatting
- Ruff linting
- MyPy type checking (where configured)
- No trailing whitespace
- YAML/TOML validation

## Common Development Patterns

### Adding a New Tool
```python
# src/tools/my_new_tool.py
from pydantic_ai import RunContext
from src.agent.unified_agent import UnifiedAgentDeps

async def my_tool(
    ctx: RunContext[UnifiedAgentDeps],
    parameter: str
) -> dict:
    """
    Clear description of what this tool does.

    Args:
        ctx: Agent runtime context
        parameter: Description

    Returns:
        Result dictionary
    """
    deps = ctx.deps
    # Implementation with proper error handling
    return {"result": "value"}

# Then add to src/agent/unified_agent.py:
super_agent.tool(my_tool)
```

### Adding Configuration Values
```python
# src/config/settings.py
class Settings(BaseSettings):
    my_new_setting: str = Field(
        default="default_value",
        description="Clear description"
    )
```

Then update `.env.example` with the new variable.

### Running Agentic RAG Ingestion
```bash
# Documents go through:
# 1. Chunking (semantic or simple)
# 2. Embedding generation
# 3. Knowledge extraction (entities + relationships)
# 4. Dual storage (PostgreSQL content + Neo4j graph)

python -m src.agentic_rag.ingestion.pipeline ingest path/to/docs
```

## Performance Optimization

### LLM Model Selection
```python
# Choose model by task complexity
simple_tasks = "gpt-4o-mini"      # Fast, cheap
complex_tasks = "gpt-4o"          # Slower, more capable
local_fallback = "llama3.1"       # No API costs
```

### Caching Strategy
- **Embeddings**: Cache frequently used query embeddings
- **Search Results**: 1-hour TTL for web search results
- **Document Metadata**: Cache file schemas and metadata
- **Redis integration**: Optional for query result caching
- **LRU cache**: For frequent function calls

### Parallel Execution
- Hybrid search runs vector + graph in parallel
- Batch embedding generation
- Async HTTP clients for web search

### Monitoring
- Prometheus metrics on `/metrics` endpoint
- Structured logging with context
- Performance profiling: `make profile-api`

### Memory Management
```python
# Limit content size to prevent memory issues
def process_large_document(content: str) -> str:
    return content[:20000]  # 20K character limit
```

## Security Patterns

### Input Validation
```python
# SQL injection prevention
def validate_sql_query(query: str) -> bool:
    forbidden = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER']
    query_upper = query.upper()
    return not any(word in query_upper for word in forbidden)
```

### Sensitive Data Protection
```python
# Remove sensitive information from logs
def sanitize_logs(data: dict) -> dict:
    sanitized = data.copy()
    for key in ['api_key', 'password', 'token']:
        if key in sanitized:
            sanitized[key] = '***REDACTED***'
    return sanitized
```

### Security Considerations
- **SQL Injection Protection**: All queries use parameterized statements + Supabase RPC
- **Code Execution**: RestrictedPython sandbox with whitelisted modules only
- **API Keys**: Never commit - always use environment variables
- **Hash Functions**: Add `usedforsecurity=False` for non-security hashing
- **Logging**: Sanitize logs that may contain user prompts or retrieved documents

## Testing Strategy

**Test coverage minimum**: 75% (enforced by pytest-cov)

**Test categories**:
- `tests/test_*.py` - Unit tests
- `tests/test_integration.py` - Integration tests
- `tests/test_e2e.py` - End-to-end tests
- `tests/rag_pipeline/` - RAG-specific tests
- `tests/load/` - Performance tests (Locust)

**Mock patterns**:
```python
@pytest.fixture
def mock_supabase():
    # Mock Supabase client
    pass

@pytest.mark.asyncio
async def test_agent_function(mock_supabase):
    # Test with mocked dependencies
    pass
```

## Common Troubleshooting

### Import errors after changes
```bash
make clean
make setup
```

### Database connection issues
1. Verify `.env` has correct `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
2. Check pgvector extension enabled in Supabase
3. Run SQL scripts in order: `documents.sql` → `document_metadata.sql` → `document_rows.sql` → `execute_sql_rpc.sql` → `agentic_rag/schema.sql`

### Neo4j connection issues
1. Verify `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` in `.env`
2. Initialize graph: `make neo4j-init`

### Tests failing
```bash
pytest tests/ -v --tb=short  # Detailed failure info
pytest tests/ -x             # Stop on first failure
pytest tests/ --lf           # Re-run last failed tests
```

### Vector Dimension Mismatch
```sql
-- If using Ollama embeddings (768d), update schema:
ALTER TABLE documents ALTER COLUMN embedding TYPE vector(768);
```

### LLM Connection Issues
```python
# Debug connection - USE CENTRALIZED CONFIG, NOT os.getenv()
from src.config import get_settings
settings = get_settings()
print(f"LLM_BASE_URL: {settings.llm_base_url}")
print(f"LLM_PROVIDER: {settings.llm_provider}")
```

### Supabase RPC Errors
```sql
-- Check if function exists
SELECT proname FROM pg_proc WHERE proname = 'match_documents';
-- If missing, re-run src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql
```

## Key Files Reference

- `src/agent/unified_agent.py` - THE agent (100-300 lines)
- `src/config/settings.py` - All configuration
- `src/agentic_rag/search/intent_analyzer.py` - Query intent analysis
- `src/agentic_rag/search/hybrid_search.py` - Search orchestration
- `src/ui/streamlit_app.py` - Main UI entry point
- `Makefile` - All development commands (490 lines)
- `pyproject.toml` - Dependencies and tool config
- `CLAUDE.md` - Comprehensive project documentation for Claude Code
- `AGENTS.md` - Repository guidelines and conventions

## Version Information

- **Current Version**: 0.9.0
- **Python**: 3.11+
- **Key Dependencies**: pydantic-ai ≥0.1.2, streamlit ≥1.44.0, mem0ai ≥0.0.10
- **Last Major Update**: Unified agent system, centralized configuration, modular UI
