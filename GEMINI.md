# AI Assistant Onboarding Guide

Welcome to the Luminari AI Agent project! This comprehensive guide provides everything an AI coding agent needs to understand, contribute to, and work effectively with this production-ready AI assistant system.

## 📖 Table of Contents

- [Quick Start](#quick-start)
- [Project Overview](#project-overview)
- [Architecture Deep Dive](#architecture-deep-dive)
- [Environment Setup](#environment-setup)
- [Core Components](#core-components)
- [Database Schema](#database-schema)
- [Development Workflow](#development-workflow)
- [Testing Strategy](#testing-strategy)
- [Code Style Guidelines](#code-style-guidelines)
- [Performance Considerations](#performance-considerations)
- [Security Requirements](#security-requirements)
- [Domain Knowledge](#domain-knowledge)
- [Common Patterns](#common-patterns)
- [Troubleshooting Guide](#troubleshooting-guide)
- [API Reference](#api-reference)
- [Quick Commands](#quick-commands)

---

## 🚀 Quick Start

### Essential Commands
```bash
# Setup development environment
make setup
cp .env.example .env  # Configure your environment

# Run the application
make run-ui          # Starts Streamlit UI on port 8501
make run-rag         # Runs RAG pipeline
make dev             # Development mode with auto-reload

# Development workflow
make format          # Format code with Black + Ruff
make lint           # Run linting checks
make test           # Run test suite
make test-coverage  # Run tests with coverage report
```

### Critical Environment Variables
```bash
# Supabase (Primary Database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key

# LLM Configuration
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_key
LLM_CHOICE=gpt-4o-mini

# Embedding Configuration
EMBEDDING_API_KEY=your_embedding_key
EMBEDDING_MODEL_CHOICE=text-embedding-3-small
```

---

## 🏗 Project Overview

### System Architecture
This is a production-ready AI agent built with:
- **Framework**: Pydantic AI 0.0.53+ with async support
- **Vector Database**: Supabase with pgvector extension
- **Memory**: mem0ai with PostgreSQL backend
- **UI**: Streamlit 1.44.1
- **Security**: RestrictedPython for safe code execution

### Key Capabilities
- **Document Retrieval (RAG)**: Vector similarity search with 4-document context window
- **Long-term Memory**: Persistent conversation memory
- **Web Search**: Internet search via Brave API or SearXNG
- **Image Analysis**: Vision model integration
- **Code Execution**: Sandboxed Python execution
- **SQL Queries**: Read-only database queries with validation

### Design Patterns Used
1. **Dependency Injection**: [`AgentDeps`](src/agent/agent.py:40) provides all external dependencies
2. **Tool Pattern**: Each capability is a separate tool with clear interfaces
3. **Factory Pattern**: [`get_model()`](src/agent/agent.py:31) creates LLM instances
4. **Client Pattern**: Separate clients for different services
5. **Pipeline Pattern**: RAG processing pipeline with stages

---

## 🏗 Architecture Deep Dive

### Component Interaction Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │ ←→ │  Pydantic Agent │ ←→ │     Tools       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                       ┌────────▼────────┐    ┌────────▼────────┐
                       │  AgentDeps      │    │  RAG Pipeline   │
                       │  - Supabase     │    │  - Text Proc.   │
                       │  - Embedding    │    │  - Embeddings   │
                       │  - HTTP Client  │    │  - Vector Store │
                       └─────────────────┘    └─────────────────┘
```

### Directory Structure
```
src/
├── agent/              # Core agent logic
│   ├── agent.py        # Main Pydantic AI agent with tool definitions
│   ├── base.py         # Base agent configuration
│   └── prompt.py       # System prompt configuration
├── clients/            # External service clients
│   ├── database.py     # Database connection management
│   ├── llm.py         # LLM client factory
│   └── memory.py      # Long-term memory client
├── tools/             # Agent tool implementations
│   ├── rag.py         # Document retrieval and RAG tools
│   ├── web_search.py  # Web search via Brave/SearXNG
│   ├── image_analysis.py # Vision model tools
│   ├── code_execution.py # Safe Python execution
│   └── sql_query.py   # Database query tools
├── rag_pipeline/      # Document processing pipeline
│   ├── common/        # Shared utilities
│   └── sources/       # Data source integrations
└── ui/               # User interfaces
    └── streamlit_app.py # Main Streamlit application
```

---

## ⚙️ Environment Setup

### Prerequisites
- **Python**: 3.11+ (required for modern async features)
- **Supabase**: Account with pgvector extension enabled
- **Docker**: For containerized deployment (optional)

### Detailed Configuration

#### 1. Supabase Setup
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Run the SQL files in order:
-- sql/documents.sql        # Main vector document storage
-- sql/document_metadata.sql # Document metadata table
-- sql/document_rows.sql     # Tabular data as JSONB
-- sql/execute_sql_rpc.sql   # Secure SQL execution function
```

#### 2. LLM Provider Configuration
```bash
# OpenAI (Primary)
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
LLM_CHOICE=gpt-4o-mini

# Ollama (Local fallback)
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_CHOICE=llama3.1

# OpenRouter (Alternative)
LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-your-key
```

#### 3. Embedding Configuration
```bash
# OpenAI Embeddings (1536 dimensions)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL_CHOICE=text-embedding-3-small

# Ollama Embeddings (768 dimensions - requires schema change)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL_CHOICE=nomic-embed-text
```

### Common Setup Issues
- **pgvector dimension mismatch**: Ensure [`embedding vector(1536)`](sql/documents.sql:9) matches your model
- **Supabase RLS**: Disable Row Level Security for development
- **API rate limits**: Configure fallback providers appropriately

---

## 🔧 Core Components

### 1. Pydantic AI Agent
**Location**: [`src/agent/agent.py`](src/agent/agent.py)

The main agent orchestrates all interactions:
```python
# Agent initialization with dependencies
agent = Agent(
    get_model(),
    system_prompt=AGENT_SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=2
)

# Key features:
# - Automatic tool calling based on context
# - Memory integration via system prompt injection
# - Retry logic for failed LLM calls
# - Multi-provider support with fallbacks
```

**Key Methods**:
- [`@agent.tool`](src/agent/agent.py:68): Decorator to register agent tools
- [`@agent.system_prompt`](src/agent/agent.py:64): Dynamic prompt injection
- [`RunContext[AgentDeps]`](src/agent/agent.py:69): Dependency injection pattern

### 2. RAG Pipeline
**Location**: [`src/rag_pipeline/`](src/rag_pipeline/)

Multi-stage document processing:
```python
# Pipeline stages:
1. Document ingestion (local files, Google Drive)
2. Text extraction and chunking
3. Embedding generation
4. Vector storage in Supabase
5. Similarity search with metadata filtering
```

**Critical Components**:
- [`text_processor.py`](src/rag_pipeline/common/text_processor.py): Chunking strategies
- [`db_handler.py`](src/rag_pipeline/common/db_handler.py): Vector operations
- [`match_documents()`](sql/documents.sql:13): PostgreSQL similarity function

### 3. Tool System
**Location**: [`src/tools/`](src/tools/)

Each tool follows the same pattern:
```python
# Tool interface pattern
async def tool_function(
    ctx: RunContext[AgentDeps],
    param1: str,
    param2: int = None
) -> str:
    """
    Tool description for LLM.

    Args:
        param1: Required parameter description
        param2: Optional parameter with default

    Returns:
        Formatted string response
    """
    # Implementation with error handling
    try:
        result = await external_service_call()
        return formatted_result
    except Exception as e:
        return f"Error: {str(e)}"
```

### 4. Memory System
**Integration**: mem0ai + PostgreSQL

Memory is injected into every conversation:
```python
@agent.system_prompt
def add_memories(ctx: RunContext[str]) -> str:
    return f"\nUser Memories:\n{ctx.deps.memories}"
```

---

## 🗄 Database Schema

### Core Tables

#### 1. Documents Table
```sql
CREATE TABLE documents (
  id bigserial primary key,
  content text,                    -- Document chunk content
  metadata jsonb,                  -- File metadata and source info
  embedding vector(1536)           -- OpenAI embedding vector
);
```

**Usage Pattern**:
```python
# Similarity search
result = supabase.rpc('match_documents', {
    'query_embedding': embedding_vector,
    'match_count': 4,
    'filter': {'file_type': 'pdf'}
})
```

#### 2. Document Metadata Table
```sql
CREATE TABLE document_metadata (
  id text primary key,
  title text,
  schema jsonb,    -- For CSV/Excel column schemas
  url text         -- Source URL or file path
);
```

#### 3. Document Rows Table
```sql
CREATE TABLE document_rows (
  id bigserial primary key,
  dataset_id text,          -- References document_metadata.id
  row_data jsonb           -- Structured data from CSV/Excel
);
```

**SQL Query Pattern**:
```sql
SELECT
    row_data->>'category' as category,
    AVG((row_data->>'revenue')::numeric) as avg_revenue
FROM document_rows
WHERE dataset_id = 'known_file_id'
GROUP BY row_data->>'category';
```

### Vector Search Optimization
- **Index**: `USING ivfflat (embedding vector_cosine_ops)`
- **Similarity Function**: `1 - (embedding <=> query_embedding)`
- **Performance**: Sub-500ms for most queries with proper indexing

---

## 🔄 Development Workflow

### Git Workflow
```bash
# Feature development
git checkout -b feature/new-tool
# Make changes
git add .
git commit -m "feat(tools): add new analysis tool"
git push origin feature/new-tool
# Create pull request
```

### Code Quality Checks
```bash
# Pre-commit hooks (automatic)
pre-commit install

# Manual checks
make lint          # Ruff + Black + MyPy
make test          # Full test suite
make security-check # Bandit security scan
```

### Release Process
1. Update version in [`pyproject.toml`](pyproject.toml:2)
2. Update [`CHANGELOG.md`](CHANGELOG.md)
3. Create release branch: `release/v1.x.x`
4. Merge to main after testing
5. Tag release: `git tag v1.x.x`

### Docker Development
```bash
make docker-build     # Build containers
make docker-run       # Run full stack
make docker-test      # Run tests in containers
```

---

## 🧪 Testing Strategy

### Test Structure
```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_agent.py           # Agent core functionality
├── test_clients.py         # Client integrations
├── test_*.py              # Tool-specific tests
└── rag_pipeline/          # RAG pipeline tests
```

### Test Categories
1. **Unit Tests** (70%): Individual functions and classes
2. **Integration Tests** (20%): Component interactions
3. **End-to-End Tests** (10%): Full workflows

### Key Testing Patterns
```python
# Async test with mocks
@pytest.mark.asyncio
async def test_rag_retrieval(mock_supabase_client, mock_async_openai):
    # Setup mocks
    mock_supabase_client.rpc.return_value.execute.return_value.data = mock_documents

    # Test the function
    result = await retrieve_relevant_documents_tool(
        mock_supabase_client,
        mock_async_openai,
        "test query"
    )

    # Assertions
    assert "Document ID:" in result
    assert mock_supabase_client.rpc.called
```

### Coverage Requirements
- **Minimum**: 75% (enforced by pytest-cov)
- **Target**: 90%+ for critical paths
- **Exclusions**: UI components, external API error paths

---

## 📝 Code Style Guidelines

### Python Style
- **Formatter**: Black (line length: 100)
- **Linter**: Ruff with strict settings
- **Type Checker**: MyPy with strict mode

### Key Conventions
```python
# Function naming: snake_case
async def retrieve_documents_tool() -> str:
    pass

# Class naming: PascalCase
class AgentDeps:
    pass

# Constants: UPPER_SNAKE_CASE
AGENT_SYSTEM_PROMPT = "..."

# Type hints: Always required
from typing import List, Dict, Optional

def process_data(items: List[str]) -> Dict[str, Any]:
    pass
```

### Error Handling Pattern
```python
# Consistent error handling across tools
try:
    result = await external_service()
    return format_success(result)
except SpecificError as e:
    logger.error(f"Service error: {e}")
    return f"Service unavailable: {str(e)}"
except Exception as e:
    logger.exception("Unexpected error")
    return f"Error: {str(e)}"
```

### Documentation Standards
- **Docstrings**: Required for all public functions
- **Type Hints**: Required for function signatures
- **Comments**: Explain complex business logic, not obvious code

---

## ⚡ Performance Considerations

### LLM Optimization
```python
# Model selection by complexity
simple_tasks = "gpt-4o-mini"      # Fast, cheap
complex_tasks = "gpt-4o"          # Slower, more capable
local_fallback = "llama3.1"       # No API costs
```

### Database Performance
```python
# Vector search optimization
- Use appropriate match_count (4 is optimal for context)
- Filter by metadata before similarity search
- Index embedding columns properly

# Query patterns
Good: SELECT specific columns with WHERE clauses
Bad:  SELECT * without filters
```

### Caching Strategy
- **Embeddings**: Cache frequently used query embeddings
- **Search Results**: 1-hour TTL for web search results
- **Document Metadata**: Cache file schemas and metadata

### Memory Management
```python
# Large document handling
def process_large_document(content: str) -> str:
    # Limit content size to prevent memory issues
    return content[:20000]  # 20K character limit

# Async operations
async def batch_process(items: List[str]) -> List[str]:
    # Process in batches to avoid overwhelming APIs
    batch_size = 10
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        batch_results = await asyncio.gather(*[process_item(item) for item in batch])
        results.extend(batch_results)
    return results
```

---

## 🔒 Security Requirements

### Input Validation
```python
# SQL injection prevention
def validate_sql_query(query: str) -> bool:
    """Validate SQL query is read-only and safe."""
    forbidden = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER']
    query_upper = query.upper()
    return not any(word in query_upper for word in forbidden)

# Code execution safety
def execute_safe_code(code: str) -> str:
    """Execute Python code in restricted environment."""
    # Uses RestrictedPython for sandboxing
    return restricted_exec(code)
```

### API Security
- **Authentication**: JWT tokens with refresh mechanism
- **Rate Limiting**: Per-user and per-endpoint limits
- **CORS**: Restrictive origin policies
- **HTTPS**: Enforce TLS 1.3 for all connections

### Data Protection
```python
# Sensitive data handling
def sanitize_logs(data: dict) -> dict:
    """Remove sensitive information from logs."""
    sanitized = data.copy()
    for key in ['api_key', 'password', 'token']:
        if key in sanitized:
            sanitized[key] = '***REDACTED***'
    return sanitized
```

### Environment Security
```bash
# Production environment variables
export LLM_API_KEY="$(vault kv get -field=api_key secret/llm)"
export SUPABASE_SERVICE_KEY="$(vault kv get -field=service_key secret/supabase)"

# Development - use .env files (never commit)
cp .env.example .env
# Edit .env with your keys
```

---

## 🧠 Domain Knowledge

### AI Agent Patterns

#### 1. Tool Selection Strategy
The agent uses function calling to automatically select appropriate tools:
```python
# The LLM decides which tools to use based on:
- System prompt instructions
- Tool docstrings
- User query context
- Available parameters
```

#### 2. RAG Best Practices
```python
# Chunking strategy
chunk_size = 1000      # Optimal for most documents
chunk_overlap = 200    # Preserve context across chunks

# Retrieval strategy
match_count = 4        # Balance between context and noise
similarity_threshold = 0.7  # Filter irrelevant results
```

#### 3. Memory Integration
```python
# Memory is injected via system prompt
@agent.system_prompt
def add_memories(ctx: RunContext[str]) -> str:
    # This makes the agent "remember" previous conversations
    return f"\nUser Memories:\n{ctx.deps.memories}"
```

### Embedding Models
```python
# OpenAI text-embedding-3-small
- Dimensions: 1536
- Cost: $0.02/1M tokens
- Performance: Excellent for most use cases

# Ollama nomic-embed-text
- Dimensions: 768
- Cost: Free (local)
- Performance: Good for privacy-focused deployments
```

### LLM Provider Strategies
1. **Primary**: OpenAI GPT-4o-mini (fast, cost-effective)
2. **Fallback**: OpenRouter (access to multiple models)
3. **Local**: Ollama (privacy, no API costs)

---

## 🔧 Common Patterns

### Adding a New Tool
```python
# 1. Create tool implementation in src/tools/
async def my_new_tool_implementation(param1: str) -> str:
    """Implementation logic here."""
    pass

# 2. Register tool in agent.py
@agent.tool
async def my_new_tool(ctx: RunContext[AgentDeps], param1: str) -> str:
    """
    Tool description for the LLM.

    Args:
        param1: Parameter description

    Returns:
        Tool result description
    """
    return await my_new_tool_implementation(param1)

# 3. Import in agent.py
from tools.my_tool import my_new_tool_implementation

# 4. Add tests
@pytest.mark.asyncio
async def test_my_new_tool():
    result = await my_new_tool_implementation("test")
    assert result is not None
```

### RAG Document Processing
```python
# 1. Document ingestion
document = load_document(file_path)

# 2. Text extraction
text = extract_text(document)

# 3. Chunking
chunks = split_text_into_chunks(text, chunk_size=1000, overlap=200)

# 4. Embedding generation
embeddings = []
for chunk in chunks:
    embedding = await get_embedding(chunk.content, embedding_client)
    embeddings.append(embedding)

# 5. Vector storage
for chunk, embedding in zip(chunks, embeddings):
    supabase.table('documents').insert({
        'content': chunk.content,
        'metadata': chunk.metadata,
        'embedding': embedding
    }).execute()
```

### Memory Usage Pattern
```python
# The agent automatically uses memory through system prompt injection
# No explicit memory calls needed in most cases

# For explicit memory management:
from mem0 import Memory

memory = Memory.from_config(config)
memory.add("User prefers technical explanations", user_id="user123")
memories = memory.get_all(user_id="user123")
```

---

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### 1. Vector Dimension Mismatch
**Error**: `dimension of vector does not match`
```sql
-- Check your current schema
\d documents

-- If using Ollama embeddings, update schema
ALTER TABLE documents ALTER COLUMN embedding TYPE vector(768);
ALTER FUNCTION match_documents(vector(768), int, jsonb) ...
```

#### 2. LLM Connection Issues
**Error**: `Connection timeout` or `API key invalid`
```python
# Debug connection
import os
print(f"LLM_BASE_URL: {os.getenv('LLM_BASE_URL')}")
print(f"LLM_API_KEY: {os.getenv('LLM_API_KEY')[:10]}...")

# Test connection manually
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=os.getenv('LLM_API_KEY'))
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "test"}]
)
```

#### 3. Supabase RPC Errors
**Error**: `function match_documents does not exist`
```sql
-- Ensure you've run the SQL setup files
-- Check function exists
SELECT proname FROM pg_proc WHERE proname = 'match_documents';

-- Recreate if missing
-- Run sql/documents.sql again
```

#### 4. Tool Not Being Called
**Issue**: Agent doesn't use your tool
```python
# Check tool docstring is clear and specific
@agent.tool
async def my_tool(ctx: RunContext[AgentDeps], query: str) -> str:
    """
    CLEAR description of when to use this tool.
    Be specific about the use case.

    Args:
        query: What kind of input this expects

    Returns:
        What format the output will be
    """
    pass
```

#### 5. Memory Not Working
**Issue**: Agent doesn't remember previous conversations
```python
# Check memory integration in system prompt
@agent.system_prompt
def add_memories(ctx: RunContext[str]) -> str:
    print(f"Memories: {ctx.deps.memories}")  # Debug output
    return f"\nUser Memories:\n{ctx.deps.memories}"
```

### Debugging Techniques

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or in environment
LOG_LEVEL=DEBUG
```

#### Test Individual Components
```python
# Test RAG retrieval
result = await retrieve_relevant_documents_tool(
    supabase_client,
    embedding_client,
    "test query"
)
print(f"RAG result: {result}")

# Test web search
result = await web_search_tool(
    "test query",
    http_client,
    brave_api_key,
    searxng_url
)
print(f"Search result: {result}")
```

#### Monitor API Usage
```python
# Add API call logging
import time

def log_api_call(func):
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__}: {elapsed:.2f}s")
        return result
    return wrapper
```

---

## 📚 API Reference

### Agent Methods
```python
# Main agent interaction
response = await agent.run(
    user_prompt="Your question here",
    deps=AgentDeps(...)
)

# Streaming response
async for chunk in agent.run_stream(user_prompt, deps=deps):
    print(chunk.content)
```

### Tool Functions
```python
# RAG tools
await retrieve_relevant_documents(ctx, user_query: str) -> str
await list_documents(ctx) -> List[str]
await get_document_content(ctx, document_id: str) -> str

# Search tools
await web_search(ctx, query: str) -> str

# Analysis tools
await image_analysis(ctx, document_id: str, query: str) -> str
await execute_code(ctx, code: str) -> str

# Data tools
await execute_sql_query(ctx, sql_query: str) -> str
```

### Client Factories
```python
# LLM client
from src.clients.llm import get_llm_client
embedding_client = get_llm_client()

# Database client
from supabase import create_client
supabase = create_client(url, service_key)
```

---

## ⚡ Quick Commands

### Development
```bash
# Setup and configuration
make setup                    # Complete environment setup
cp .env.example .env         # Copy environment template
make install-dev             # Install development dependencies

# Code quality
make format                  # Format with Black + Ruff
make lint                   # Run all linters
make test                   # Run test suite
make test-coverage          # Tests with coverage report

# Running services
make run-ui                 # Streamlit UI (port 8501)
make run-rag               # RAG pipeline processor
make dev                   # Development mode with auto-reload
```

### Docker
```bash
make docker-build          # Build Docker images
make docker-run           # Run full stack with Docker Compose
make docker-stop          # Stop all containers
make docker-test          # Run tests in containers
```

### Database
```bash
make db-setup             # Instructions for Supabase setup
make db-migrate           # Database migration info
```

### Utilities
```bash
make clean                # Remove Python cache files
pre-commit run --all-files # Run pre-commit hooks manually
```

### Environment Variables Quick Reference
```bash
# Core settings
SUPABASE_URL=                # Supabase project URL
SUPABASE_SERVICE_KEY=        # Service role key
LLM_API_KEY=                # OpenAI/provider API key
EMBEDDING_API_KEY=          # Embedding model API key

# Optional settings
BRAVE_API_KEY=              # Web search API key
SEARXNG_BASE_URL=           # Self-hosted search URL
GOOGLE_DRIVE_FOLDER_ID=     # Google Drive integration
ENABLE_CODE_EXECUTION=      # Enable/disable code execution
```

---

## 🎯 Summary

This AI agent is a sophisticated system that combines:
- **Multi-modal AI** with document understanding, web search, and code execution
- **Production-ready architecture** with proper testing, security, and deployment
- **Flexible configuration** supporting multiple LLM providers and data sources
- **Comprehensive tooling** for development, testing, and monitoring

### Next Steps for New Contributors
1. **Setup**: Follow the [Environment Setup](#environment-setup) section
2. **Understand**: Read the [Core Components](#core-components) section
3. **Practice**: Try adding a new tool following [Common Patterns](#common-patterns)
4. **Test**: Write tests following the [Testing Strategy](#testing-strategy)
5. **Deploy**: Use Docker or direct deployment methods

### Key Success Factors
- **Configuration Management**: Proper environment setup is critical
- **Error Handling**: All tools must handle failures gracefully
- **Testing**: Comprehensive test coverage ensures reliability
- **Documentation**: Clear docstrings help the LLM use tools correctly
- **Performance**: Consider API costs and response times in design decisions

This system is designed to be both powerful and maintainable. Focus on understanding the patterns rather than memorizing details, and you'll be productive quickly.

---

*Last updated: 2024-08-24*
*Version: 1.0*
