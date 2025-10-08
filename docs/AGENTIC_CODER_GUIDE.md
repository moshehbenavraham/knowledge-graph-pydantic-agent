# AGENTIC_CODER_GUIDE.md

This file provides guidance to Agentic Coding Agents (such as Claude Code) when working with code in this repository.

## Common Development Commands

### Setup & Dependencies
```bash
make setup                # Install dependencies and pre-commit hooks
make install-dev          # Install development dependencies
```

### Running the Application
```bash
make run-ui               # Start Streamlit UI in standard mode (http://localhost:8501)
make run-ui-simple        # Start UI in simple mode (fast, no persistence)
make run-ui-advanced      # Start UI in advanced mode (all features)
make run-ui MODE=simple   # Start UI with custom mode
make run-api              # Start FastAPI server (http://localhost:8058)
make run-agentic-rag      # Run Agentic RAG CLI
make dev                  # Development mode with auto-reload
make dev MODE=advanced    # Development mode with specific UI mode
```

### Code Quality & Testing
```bash
make format               # Format code with Black + Ruff
make lint                 # Run Ruff linting
make test                 # Run test suite  
make test-coverage        # Run tests with coverage report (must maintain 75%+)
make security             # Run security scans (Bandit, Safety, pip-audit)
make check                # Run all checks (lint, test, security)
```

### Running Single Tests
```bash
pytest tests/test_agent.py::test_specific_function -v  # Run specific test
pytest -k "test_pattern" -v                            # Run tests matching pattern
pytest --lf                                            # Re-run last failed tests
```

### Database Operations
```bash
make neo4j-init          # Initialize Neo4j knowledge graph
make ingest              # Run document ingestion pipeline
make ingest-clean        # Clean and re-ingest documents
```

### Docker Development
```bash
make docker-build        # Build Docker images
make docker-run          # Run full stack with Docker Compose
make docker-stop         # Stop all containers
make docker-test         # Run tests in containers
```

## High-Level Architecture

### Dual Storage Strategy
The system implements an **Agentic RAG** architecture combining two databases:

- **PostgreSQL/Supabase**: Primary content storage
  - Full document content and chunks with vector embeddings (pgvector)
  - Uses either OpenAI text-embedding-3-small (1536d) or Ollama nomic-embed-text (768d)
  - Single source of truth for all content (99.6% of storage)
  
- **Neo4j/Graphiti**: Knowledge graph index (0.4% storage overhead)
  - Stores only extracted entities, relationships, and facts
  - No content duplication - references PostgreSQL chunks via IDs
  - Enables relationship queries and temporal analysis

### Agent Intelligence Layer
The system uses a unified Pydantic AI agent with sophisticated query routing:

1. **Intent Analysis**: Uses IntentAnalyzer to classify queries into 5 intent types (VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, TEMPORAL, ENTITY_FOCUSED)
2. **Strategy Selection**: Routes to optimal search approach based on intent with confidence scoring
3. **Tool Orchestration**: Coordinates parallel execution of search strategies
4. **Response Generation**: Synthesizes results with citations and confidence scores

### Search Strategies
- **Vector Search**: Semantic similarity using pgvector (sub-200ms)
- **Graph Search**: Entity/relationship traversal in Neo4j (sub-500ms)  
- **Hybrid Search**: Parallel execution with intelligent result merging
- **Smart Search**: Automatic strategy selection based on query intent

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

## Important Configuration

### Environment Variables
Always check `.env.example` for required settings:
- `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`: Required for database
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Required for knowledge graph
- `LLM_API_KEY` and `EMBEDDING_API_KEY`: Required for AI operations
- Web Search (configure one or more):
  - `JINA_API_KEY`: Jina.ai for clean web content extraction
  - `BRAVE_API_KEY`: Brave Search API
  - `SEARXNG_BASE_URL`: Self-hosted SearXNG instance
  - `WEB_SEARCH_PROVIDER`: Force specific provider (jina/brave/searxng)

### Database Setup
1. PostgreSQL/Supabase: Run SQL scripts in order from `sql/` directory
2. Neo4j: Use `make neo4j-init` or Docker deployment
3. Enable pgvector extension in Supabase dashboard

### Code Standards
- Python 3.11+ with type hints
- Line length: 100 characters
- Use existing patterns for error handling and logging
- Maintain 75% test coverage minimum
- Always use parameterized SQL queries
- Never create files longer than 500 lines (refactor into modules)
- Write tests for new features: expected use, edge cases, failure cases

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

## Common Troubleshooting

### Vector Dimension Mismatch
```sql
-- If using Ollama embeddings (768d), update schema:
ALTER TABLE documents ALTER COLUMN embedding TYPE vector(768);
```

### LLM Connection Issues
```python
# Debug connection
import os
print(f"LLM_BASE_URL: {os.getenv('LLM_BASE_URL')}")
print(f"LLM_API_KEY: {os.getenv('LLM_API_KEY')[:10]}...")
```

### Supabase RPC Errors
```sql
-- Check if function exists
SELECT proname FROM pg_proc WHERE proname = 'match_documents';
-- If missing, re-run sql/documents.sql
```