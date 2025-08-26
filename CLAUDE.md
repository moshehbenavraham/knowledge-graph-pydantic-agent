# CLAUDE.md

> **🤖 For Cursor AI quick reference, see [.cursorrules](./.cursorrules)**

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## WHEN WRITING DOCUMENTATION ONLY USE UTF-8 LR ASCII CHARACTERS, AVOID ALL PROBLEMATIC CHARACTERS!!!!!!!!

## Common Development Commands

### Setup and Installation
```bash
# Install dependencies with development extras
make setup

# Alternative: Install specific extras
python -m pip install -e .[dev]
python -m pip install -e .[rag]
python -m pip install -e .[security]
```

### Running the Application
```bash
# Start the main Streamlit UI
make run-ui

# Start in development mode with auto-reload
make dev

# Run the RAG pipeline for document processing
make run-rag

# Run the Agentic RAG API server
python -m src.api.main

# Run the Agentic RAG CLI
python -m src.agentic_rag.agent.agent chat "Your question"
```

### Code Quality and Testing
```bash
# Run all checks (linting, tests, security)
make check

# Format code with Black and Ruff
make format

# Run linting checks
make lint

# Run tests
make test

# Run tests with coverage report
make test-coverage

# Run security scans
make security

# Run specific test file
pytest tests/test_agent.py -v

# Run tests matching a pattern
pytest -k "test_rag" -v
```

### Database Operations
```bash
# Initialize Neo4j knowledge graph
python -m src.agentic_rag.storage.neo4j_store init

# Ingest documents for Agentic RAG
python -m src.agentic_rag.ingestion.pipeline ingest path/to/documents

# Clean ingested data and re-ingest
python -m src.agentic_rag.ingestion.pipeline --clean
```

### Docker Operations
```bash
make docker-build
make docker-run
make docker-stop
```

## High-Level Architecture

### System Design
The base_agent implements a multi-tiered AI assistant with **Agentic RAG** combining vector search (PostgreSQL/Supabase) and knowledge graph (Neo4j/Graphiti) capabilities.

### Key Components

#### 1. Agent Layer (src/agentic_rag/agent/)
- **agent.py**: Main Pydantic AI agent with tool definitions and context management
- **prompts.py**: System prompts controlling agent behavior
- **intent_analyzer.py**: Intent analysis system with 8 intent types
- **response_generator.py**: Response generation with citations and confidence scoring
- **router.py**: Query routing and strategy selection
- **tools.py**: Advanced search tools (smart_search, hybrid_search, etc.)
- **config.py**: Agent configuration and dependencies

#### 2. Storage Architecture
- **PostgreSQL/Supabase**: Document content, chunks, embeddings, and metadata
- **Neo4j**: Entity relationships, temporal facts (references back to PostgreSQL chunks)
- **mem0**: Long-term conversation memory with PostgreSQL backend

#### 3. Search Strategies
- **Vector Search**: Semantic similarity via pgvector (sub-200ms)
- **Graph Search**: Entity/relationship traversal via Neo4j (sub-500ms)
- **Hybrid Search**: Parallel execution with intelligent result merging

#### 4. Tool System
**Core Tools (src/tools/)**:
- **rag.py**: Document retrieval and RAG operations
- **web_search.py**: Brave API or SearXNG integration
- **image_analysis.py**: Vision model capabilities
- **code_execution.py**: Sandboxed Python execution
- **sql_query.py**: Read-only database queries

**Agentic RAG Tools (src/agentic_rag/agent/tools.py)**:
- **smart_search**: Intent-based automatic strategy selection
- **vector_search**: Semantic similarity search
- **graph_search**: Knowledge graph traversal
- **hybrid_search**: Combined vector and graph search
- **comprehensive_search**: Multi-strategy parallel execution
- **iterative_search**: Multi-step refinement for complex queries
- **get_entity_relationships**: Deep entity exploration
- **get_entity_timeline**: Temporal information retrieval

#### 5. Ingestion Pipeline (src/agentic_rag/ingestion/)
- **pipeline.py**: Main orchestrator for document processing
- **chunker.py**: Semantic chunking with LLM-based intelligent splitting
- **embedder.py**: Multi-model embedding generation with caching
- **extractor.py**: Knowledge extraction (entities, relationships, facts) via Graphiti
- **Dual Storage**: Content in PostgreSQL, knowledge graph in Neo4j

#### 6. API Layer
- **FastAPI Backend**: REST endpoints with streaming support (src/api/main.py)
- **Streamlit UI**: Interactive web interface (src/ui/streamlit_app.py)
- **CLI Interface**: Command-line chat with tool visibility (src/agentic_rag/agent/agent.py)

#### 7. Search Architecture (src/agentic_rag/search/)
- **strategies.py**: Search strategy definitions and routing logic
- **vector.py**: Vector search implementation with pgvector
- **graph.py**: Knowledge graph search with Neo4j
- **hybrid.py**: Hybrid search combining vector and graph
- **weighted.py**: Intelligent result merging and ranking
- **base.py**: Base search interface and abstractions

#### 8. Storage Layer (src/agentic_rag/storage/)
- **postgres_store.py**: PostgreSQL operations for content and embeddings
- **neo4j_store.py**: Neo4j operations for knowledge graph
- **models.py**: Data models and schemas
- **utils.py**: Storage utilities and helpers
- **schema.sql**: Enhanced database schema definitions

## Configuration Requirements

### Environment Variables
Create `.env` file with:
- **SUPABASE_URL** and **SUPABASE_SERVICE_KEY**: Required for PostgreSQL/vector storage
- **NEO4J_URI**, **NEO4J_USER**, **NEO4J_PASSWORD**: Required for knowledge graph
- **LLM_PROVIDER**, **LLM_API_KEY**, **LLM_CHOICE**: Language model configuration
- **EMBEDDING_PROVIDER**, **EMBEDDING_API_KEY**: Embedding model configuration

### Database Setup
1. Enable pgvector extension in Supabase
2. Run SQL scripts in order:
   - sql/documents.sql
   - sql/document_metadata.sql
   - sql/document_rows.sql
   - sql/execute_sql_rpc.sql
   - sql/agentic_rag/schema.sql (if using Agentic RAG)
3. Initialize Neo4j (local Docker or cloud instance)

## Development Notes

### Code Style
- Line length: 100 characters
- Python 3.11+ with type hints
- Black formatting, Ruff linting
- MyPy for type checking
- Pre-commit hooks enforced

### Testing Requirements
- Minimum 75% code coverage
- Pytest with async support
- Tests mirror source structure
- Unit and integration tests included

### Security Considerations
- RestrictedPython for code execution
- Parameterized SQL queries only
- Read-only database operations
- API keys in environment variables

### Performance Targets
- Vector search: <200ms response
- Graph search: <500ms response
- Hybrid search optimized for parallel execution
- Caching enabled for frequently accessed data

## MCP Server Tools

### VisionCraft MCP Server
- **Tool Name**: `mcp__visioncraft__vision-query`
- **Purpose**: Query the VisionCraft knowledge base for AI-related information
- **Location**: `mcp-servers/visioncraft/index.js`
- **Usage**: Available as a tool for querying AI topics, concepts, and technical information
- **Example**: Use for researching AI algorithms, model architectures, training techniques, etc.

### Context7 MCP Server
- **Tool Name**: `mcp__context7__resolve-library-id` and `mcp__context7__get-library-docs`
- **Purpose**: Retrieve up-to-date documentation and code examples for any library
- **Configuration**: Configured in `.mcp.json` with API credentials
- **Usage**:
  - First use `resolve-library-id` to get the Context7-compatible library ID
  - Then use `get-library-docs` with the resolved ID to fetch documentation
- **Example**: Use for getting latest documentation on frameworks like Next.js, Supabase, MongoDB, etc.
