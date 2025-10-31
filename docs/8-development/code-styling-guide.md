# Code Styling Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-31
**Status:** Active

## Overview

This guide defines the coding standards and style conventions for the Luminari Agent project. Following these guidelines ensures code consistency, maintainability, and quality across the codebase.

**Philosophy:** Write code that is clear, maintainable, and secure. Favor explicitness over cleverness, and always prioritize readability.

## Table of Contents

1. [Core Standards](#core-standards)
2. [Code Formatting](#code-formatting)
3. [Type Hints](#type-hints)
4. [Docstrings](#docstrings)
5. [Import Organization](#import-organization)
6. [Naming Conventions](#naming-conventions)
7. [Async Patterns](#async-patterns)
8. [Error Handling](#error-handling)
9. [Security Guidelines](#security-guidelines)
10. [Testing Standards](#testing-standards)
11. [Configuration Management](#configuration-management)
12. [Common Patterns](#common-patterns)
13. [Anti-patterns to Avoid](#anti-patterns-to-avoid)
14. [Tools & Automation](#tools--automation)

## Core Standards

### Python Version
- **Minimum:** Python 3.11
- **Target:** Python 3.11, 3.12
- Use modern Python features (match statements, union types with `|`, etc.)

### Line Length
- **Maximum:** 100 characters
- Enforced by Black formatter
- Exception: URLs and long strings that cannot be broken

### Character Encoding
- **ONLY UTF-8 ASCII with LF line endings**
- **NO emojis, NO unicode special characters, NO Windows CRLF**
- Valid characters: ASCII 0x20-0x7E plus tab (0x09), LF (0x0A)
- Pre-commit hook enforces this rule

### File Organization
```
src/
  module_name/
    __init__.py       # Public API exports
    core.py           # Core functionality
    models.py         # Pydantic models
    utils.py          # Helper functions
    types.py          # Type definitions
tests/
  test_module_name/
    test_core.py      # Unit tests
    test_integration.py  # Integration tests
```

## Code Formatting

### Black Formatter

**Configuration** (pyproject.toml):
```toml
[tool.black]
line-length = 100
target-version = ['py311', 'py312']
```

**Rules:**
- Automatic formatting on save (via pre-commit)
- Double quotes for strings
- Trailing commas in multi-line structures
- Parentheses for line breaks in complex expressions

**Example:**
```python
# Good
result = some_function(
    parameter1="value1",
    parameter2="value2",
    parameter3="value3",
)

# Bad (manual line breaks without Black)
result = some_function(parameter1="value1",
    parameter2="value2", parameter3="value3")
```

### Ruff Linter

**Configuration** (pyproject.toml):
```toml
[tool.ruff]
line-length = 100
target-version = "py311"
fix = true
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "UP", # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # function calls in argument defaults
    "B905",  # zip() without strict parameter
]
```

**Auto-fixes:**
- Import sorting
- Unused imports removal
- Modernize Python syntax
- Common bug patterns

## Type Hints

### Requirements

**MANDATORY for all:**
- Public function signatures
- Class attributes
- Function return types

**Example:**
```python
from typing import Any
from collections.abc import Awaitable

# Good - Complete type hints
async def process_document(
    document_id: str,
    content: str,
    metadata: dict[str, Any],
    user_id: str | None = None
) -> dict[str, Any]:
    """Process a document with full type hints."""
    pass

# Bad - Missing type hints
async def process_document(document_id, content, metadata, user_id=None):
    pass
```

### Modern Type Syntax (Python 3.11+)

```python
# Use | for unions (not Union)
def get_value(key: str) -> str | None:
    pass

# Use built-in generics (not typing.List, Dict)
def process_items(items: list[str]) -> dict[str, int]:
    pass

# Use collections.abc for protocols
from collections.abc import Callable, Awaitable

def register_callback(
    callback: Callable[[str], Awaitable[None]]
) -> None:
    pass
```

### Optional vs | None

```python
# Preferred (explicit)
def get_user(user_id: str) -> User | None:
    pass

# Avoid (less explicit)
from typing import Optional
def get_user(user_id: str) -> Optional[User]:
    pass
```

### Type Aliases

```python
# For complex types, create aliases
from typing import TypeAlias

UserId: TypeAlias = str
Metadata: TypeAlias = dict[str, Any]
SearchResult: TypeAlias = dict[str, Any]

def search_documents(
    query: str,
    user_id: UserId,
    metadata_filter: Metadata | None = None
) -> list[SearchResult]:
    pass
```

## Docstrings

### Google Style Format

**REQUIRED for:**
- All public functions and methods
- All classes
- All modules

**Minimum coverage:** 75% (enforced by interrogate)

### Module Docstrings

```python
"""
Module Name - Brief Description
================================

Longer description explaining the module's purpose, main classes,
and key functionality.

Example:
    from src.module import ClassName

    obj = ClassName()
    result = obj.method()
"""
```

### Function Docstrings

```python
async def retrieve_documents(
    ctx: RunContext[UnifiedAgentDeps],
    query: str,
    max_results: int = 10,
    metadata_filter: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Retrieve relevant documents using vector similarity search.

    Performs semantic search over the document collection using embeddings
    and returns the most relevant results based on cosine similarity.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        max_results: Maximum number of results to return (default: 10)
        metadata_filter: Optional metadata filters as key-value pairs

    Returns:
        Dictionary containing:
            - documents: List of matching documents with content and metadata
            - count: Number of results returned
            - query: Original query text

    Raises:
        ValueError: If max_results is less than 1
        ConnectionError: If Supabase connection fails

    Example:
        result = await retrieve_documents(
            ctx,
            query="machine learning",
            max_results=5
        )
        print(f"Found {result['count']} documents")
    """
    pass
```

### Class Docstrings

```python
@dataclass
class UnifiedAgentDeps:
    """
    Dependency injection container for the unified agent.

    Provides all required clients, configuration, and context for agent
    operations. Use this class to centralize dependencies and avoid global
    state.

    Attributes:
        supabase: Supabase client for database operations
        embedding_client: OpenAI client for embeddings
        http_client: Async HTTP client for web requests
        brave_api_key: Optional API key for Brave search
        memories: User context from mem0
        session_id: Current session identifier

    Example:
        deps = UnifiedAgentDeps(
            supabase=get_supabase_client(),
            embedding_client=get_embedding_client(),
            http_client=AsyncClient()
        )
    """
    pass
```

## Import Organization

### Order (Enforced by Ruff)

```python
# 1. Standard library
import asyncio
import logging
from dataclasses import dataclass
from typing import Any

# 2. Third-party packages
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from supabase.client import Client

# 3. Local imports (absolute)
from src.config.agent import agent_config
from src.clients.llm import get_model
from src.tools import web_search_tool
```

### Import Styles

```python
# Preferred - Explicit imports
from src.config.settings import get_settings
from src.agentic_rag.search.hybrid_search import hybrid_search

# Avoid - Star imports (except in __init__.py)
from src.tools import *  # Bad

# Group related imports
from src.tools import (
    execute_safe_code_tool,
    execute_sql_query_tool,
    get_document_content_tool,
    image_analysis_tool,
)
```

### Lazy Imports for Heavy Dependencies

```python
# Good - Lazy import for optional/heavy dependency
def use_embeddings():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return model

# Bad - Top-level import of heavy optional dependency
from sentence_transformers import SentenceTransformer  # Loads 3GB PyTorch
```

## Naming Conventions

### General Rules

```python
# Classes: PascalCase
class UnifiedAgent:
    pass

class SearchResult:
    pass

# Functions/methods: snake_case
def process_document():
    pass

async def retrieve_documents():
    pass

# Variables: snake_case
user_name = "John"
max_results = 10
is_authenticated = True

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
API_VERSION = "v1"

# Private attributes: _leading_underscore
class MyClass:
    def __init__(self):
        self._internal_state = {}
        self.__really_private = []  # Name mangling

# Type aliases: PascalCase
UserId = str
SearchResults = list[dict[str, Any]]
```

### Specific Conventions

```python
# Tools: verb_noun_tool
async def retrieve_documents_tool():
    pass

async def execute_sql_query_tool():
    pass

# Handlers: noun_handler
class StreamingHandler:
    pass

class MemoryHandler:
    pass

# Configs: noun_config
agent_config = AgentConfig()
api_config = APIConfig()

# Models: noun (descriptive)
class User(BaseModel):
    pass

class Document(BaseModel):
    pass

# Exceptions: Error suffix
class ConfigurationError(Exception):
    pass

class AuthenticationError(Exception):
    pass
```

## Async Patterns

### Always Use Async for I/O

```python
# Good - Async for database operations
async def get_document(doc_id: str) -> Document | None:
    result = await supabase.table("documents").select("*").eq("id", doc_id).execute()
    return result.data[0] if result.data else None

# Bad - Blocking I/O
def get_document(doc_id: str) -> Document | None:
    result = supabase.table("documents").select("*").eq("id", doc_id).execute()
    return result.data[0] if result.data else None
```

### Parallel Execution

```python
# Good - Parallel async operations
async def hybrid_search(query: str) -> list[Document]:
    vector_task = asyncio.create_task(vector_search(query))
    graph_task = asyncio.create_task(graph_search(query))

    vector_results, graph_results = await asyncio.gather(
        vector_task,
        graph_task,
        return_exceptions=True
    )
    return merge_results(vector_results, graph_results)

# Bad - Sequential async (loses performance)
async def hybrid_search(query: str) -> list[Document]:
    vector_results = await vector_search(query)
    graph_results = await graph_search(query)
    return merge_results(vector_results, graph_results)
```

### Context Managers

```python
# Good - Async context manager
async def fetch_data():
    async with AsyncClient() as client:
        response = await client.get("https://api.example.com")
        return response.json()

# For cleanup
async def process_with_cleanup():
    try:
        resource = await acquire_resource()
        return await process(resource)
    finally:
        await cleanup_resource(resource)
```

### Asyncio Best Practices

```python
# Create tasks for concurrent operations
tasks = [
    asyncio.create_task(operation1()),
    asyncio.create_task(operation2()),
    asyncio.create_task(operation3()),
]
results = await asyncio.gather(*tasks, return_exceptions=True)

# Handle exceptions properly
for result in results:
    if isinstance(result, Exception):
        logger.error(f"Task failed: {result}")
    else:
        process_result(result)
```

## Error Handling

### Comprehensive Error Handling

```python
# Good - Specific exceptions with context
async def process_document(doc_id: str) -> dict[str, Any]:
    """Process document with comprehensive error handling."""
    try:
        document = await fetch_document(doc_id)
        if not document:
            raise ValueError(f"Document not found: {doc_id}")

        content = await extract_content(document)
        return {"status": "success", "content": content}

    except ValueError as e:
        logger.error(f"Invalid document: {e}")
        raise

    except ConnectionError as e:
        logger.error(f"Database connection failed: {e}")
        return {"status": "error", "message": "Database unavailable"}

    except Exception as e:
        logger.exception(f"Unexpected error processing document {doc_id}")
        raise RuntimeError(f"Processing failed: {e}") from e
```

### Validation

```python
# Good - Early validation
def search_documents(query: str, max_results: int = 10) -> list[Document]:
    """Search with input validation."""
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if max_results < 1:
        raise ValueError(f"max_results must be >= 1, got {max_results}")

    if max_results > 100:
        logger.warning(f"Large max_results value: {max_results}, capping at 100")
        max_results = 100

    return _perform_search(query, max_results)
```

### Logging Best Practices

```python
import structlog

logger = structlog.get_logger(__name__)

# Good - Structured logging with context
async def process_item(item_id: str) -> None:
    logger.info("Processing item", item_id=item_id)

    try:
        result = await process(item_id)
        logger.info("Item processed", item_id=item_id, result_size=len(result))
    except Exception as e:
        logger.exception(
            "Processing failed",
            item_id=item_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise

# Bad - Unstructured logging
logger.info(f"Processing item {item_id}")
```

## Security Guidelines

### Never Use os.getenv() Directly

```python
# Good - Use centralized configuration
from src.config import get_settings

settings = get_settings()
api_key = settings.openai_api_key

# Bad - Direct environment access
import os
api_key = os.getenv("OPENAI_API_KEY")
```

### SQL Injection Prevention

```python
# Good - Parameterized queries via Supabase RPC
async def query_data(table: str, condition: str) -> list[dict]:
    """Execute query using Supabase RPC (parameterized)."""
    result = await supabase.rpc(
        "execute_safe_query",
        {"query_table": table, "condition": condition}
    )
    return result.data

# Bad - String concatenation
query = f"SELECT * FROM {table} WHERE {condition}"  # SQL injection risk!
```

### Code Execution Safety

```python
# Good - RestrictedPython sandbox
from RestrictedPython import compile_restricted

def execute_safe_code(code: str) -> Any:
    """Execute code in restricted environment."""
    byte_code = compile_restricted(
        code,
        filename="<user_code>",
        mode="exec"
    )

    safe_globals = {
        "__builtins__": safe_builtins,
        "math": math,  # Whitelisted modules only
    }

    exec(byte_code, safe_globals)
    return safe_globals.get("result")

# Bad - Direct exec
exec(user_code)  # Arbitrary code execution!
```

### Hash Functions

```python
# Good - Specify security context
import hashlib

# For non-security purposes (checksums, cache keys)
hash_value = hashlib.md5(data, usedforsecurity=False).hexdigest()

# For security purposes (passwords, tokens)
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
```

### Input Validation

```python
# Good - Comprehensive validation
from pydantic import BaseModel, Field, validator

class SearchRequest(BaseModel):
    """Validated search request."""
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(default=10, ge=1, le=100)
    filters: dict[str, str] = Field(default_factory=dict)

    @validator("query")
    def validate_query(cls, v):
        """Ensure query is safe."""
        if any(char in v for char in ["<", ">", "&"]):
            raise ValueError("Query contains invalid characters")
        return v.strip()
```

## Testing Standards

### Test Coverage

- **Minimum:** 75% (enforced by pytest-cov)
- **Target:** 85%+
- Focus on critical paths and edge cases

### Test Structure

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestUnifiedAgent:
    """Test suite for unified agent functionality."""

    @pytest.fixture
    def mock_deps(self):
        """Create mock dependencies."""
        return UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=AsyncMock(),
            http_client=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_search_success(self, mock_deps):
        """Test successful document search."""
        # Arrange
        mock_deps.supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[{"id": "1", "content": "test"}])
        )

        # Act
        result = await search_documents(mock_deps, "test query")

        # Assert
        assert result["count"] == 1
        assert result["documents"][0]["id"] == "1"
        mock_deps.supabase.table.assert_called_once_with("documents")

    @pytest.mark.asyncio
    async def test_search_empty_query(self, mock_deps):
        """Test search with empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await search_documents(mock_deps, "")

    @pytest.mark.asyncio
    async def test_search_connection_error(self, mock_deps):
        """Test search handles connection errors gracefully."""
        # Arrange
        mock_deps.supabase.table.side_effect = ConnectionError("DB unavailable")

        # Act
        result = await search_documents(mock_deps, "test")

        # Assert
        assert result["status"] == "error"
        assert "unavailable" in result["message"].lower()
```

### Test Naming

```python
# Pattern: test_<component>_<scenario>_<expected_result>

def test_agent_search_valid_query_returns_results():
    pass

def test_agent_search_empty_query_raises_error():
    pass

def test_agent_search_db_error_returns_error_dict():
    pass
```

### Integration Tests

```python
@pytest.mark.integration
class TestAgentIntegration:
    """Integration tests requiring real services."""

    @pytest.fixture(scope="module")
    async def live_deps(self):
        """Real dependencies for integration testing."""
        return await create_real_dependencies()

    @pytest.mark.asyncio
    async def test_end_to_end_search(self, live_deps):
        """Test complete search flow with real database."""
        result = await agent.run(
            "Find documents about machine learning",
            deps=live_deps
        )
        assert result.data
        assert "machine learning" in result.data.lower()
```

## Configuration Management

### Use Centralized Settings

```python
# src/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Centralized configuration with validation."""

    # LLM Configuration
    llm_provider: str = Field(default="openai")
    openai_api_key: str = Field(default="")

    # Database Configuration
    supabase_url: str = Field(default="")
    supabase_key: str = Field(default="")

    # Feature Flags
    enable_graph_search: bool = Field(default=True)
    enable_web_search: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Usage
from src.config import get_settings

settings = get_settings()
model = get_model(settings.llm_provider)
```

### Configuration Facades

```python
# src/config/agent.py - Agent-specific config facade
from src.config.settings import get_settings

class AgentConfig:
    """Facade for agent configuration."""

    def __init__(self):
        self._settings = get_settings()

    @property
    def model_name(self) -> str:
        return self._settings.llm_provider

    @property
    def max_tokens(self) -> int:
        return self._settings.max_tokens

agent_config = AgentConfig()
```

## Common Patterns

### Dependency Injection

```python
# Good - Dependencies passed explicitly
@dataclass
class UnifiedAgentDeps:
    supabase: Client
    embedding_client: AsyncOpenAI
    http_client: AsyncClient

async def process_query(
    ctx: RunContext[UnifiedAgentDeps],
    query: str
) -> dict:
    deps = ctx.deps
    result = await deps.supabase.table("documents").select("*").execute()
    return result.data

# Bad - Global state
_supabase_client = None  # Global variable

def process_query(query: str) -> dict:
    result = _supabase_client.table("documents").select("*").execute()
    return result.data
```

### Factory Pattern for Clients

```python
# Good - Factory functions
def create_supabase_client() -> Client:
    """Create configured Supabase client."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)

def create_embedding_client() -> AsyncOpenAI:
    """Create embedding client based on provider."""
    settings = get_settings()
    if settings.llm_provider == "openai":
        return AsyncOpenAI(api_key=settings.openai_api_key)
    elif settings.llm_provider == "ollama":
        return AsyncOpenAI(base_url="http://localhost:11434")
    raise ValueError(f"Unknown provider: {settings.llm_provider}")
```

### Tool Registration

```python
# Good - Clean tool registration
from pydantic_ai import RunContext

async def search_tool(
    ctx: RunContext[UnifiedAgentDeps],
    query: str
) -> dict[str, Any]:
    """Search documents using RAG."""
    deps = ctx.deps
    # Implementation
    return result

# Register with agent
super_agent.tool(search_tool)

# Bad - Anonymous or inline tools
super_agent.tool(lambda ctx, q: search(ctx.deps.supabase, q))
```

### Result Dictionaries

```python
# Good - Structured result dictionaries
def process_document(doc_id: str) -> dict[str, Any]:
    """Process document and return structured result."""
    try:
        content = extract_content(doc_id)
        return {
            "status": "success",
            "document_id": doc_id,
            "content": content,
            "metadata": get_metadata(doc_id),
            "processed_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "document_id": doc_id,
            "error": str(e),
            "error_type": type(e).__name__,
        }

# Even better - Use Pydantic models
class ProcessResult(BaseModel):
    status: str
    document_id: str
    content: str | None = None
    error: str | None = None
```

## Anti-patterns to Avoid

### Global State

```python
# Bad - Global mutable state
_cache = {}
def get_value(key: str) -> Any:
    return _cache.get(key)

# Good - Pass state explicitly or use proper caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_value(key: str) -> Any:
    return fetch_from_db(key)
```

### Multiple Agent Implementations

```python
# Bad - Multiple agent files
src/agent/simple_agent.py
src/agent/advanced_agent.py
src/agent/rag_agent.py

# Good - One unified agent
src/agent/unified_agent.py  # Single source of truth
```

### Direct Environment Access

```python
# Bad
import os
api_key = os.getenv("API_KEY")

# Good
from src.config import get_settings
settings = get_settings()
api_key = settings.api_key
```

### Bare Except Clauses

```python
# Bad - Catches everything including KeyboardInterrupt
try:
    process_data()
except:
    pass

# Good - Specific exception handling
try:
    process_data()
except ValueError as e:
    logger.error(f"Invalid data: {e}")
    raise
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### String Concatenation for SQL/Paths

```python
# Bad - SQL injection vulnerability
query = f"SELECT * FROM {table} WHERE id = {user_id}"

# Good - Parameterized queries
query = supabase.table(table).select("*").eq("id", user_id)

# Bad - Path concatenation
file_path = base_dir + "/" + user_file

# Good - Use pathlib
from pathlib import Path
file_path = Path(base_dir) / user_file
```

## Tools & Automation

### Pre-commit Hooks

Installed hooks (enforced on every commit):
- **Black**: Auto-formatting
- **Ruff**: Linting and auto-fixes
- **MyPy**: Type checking (manual stage)
- **Bandit**: Security scanning
- **Interrogate**: Docstring coverage
- **Constitution Validator**: Project-specific compliance

Install with:
```bash
pre-commit install
```

### Manual Checks

```bash
# Format code
make format              # Black + Ruff

# Run linters
make lint                # Ruff + Black (check only)

# Type checking
mypy src/                # Manual type check

# Security
make security            # Bandit + Safety + pip-audit

# All checks
make check               # lint + test + security
```

### Test Execution

```bash
# Quick test run
pytest tests/ -v

# With coverage
make test-coverage       # Minimum 75% required

# Specific test file
pytest tests/test_unified_agent.py -v

# Specific test pattern
pytest -k "test_search" -v

# Stop on first failure
pytest -x

# Parallel execution (faster)
pytest -n auto
```

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes

# 3. Run checks locally
make format              # Auto-format
make lint                # Check style
pytest tests/            # Run tests

# 4. Commit (pre-commit runs automatically)
git add .
git commit -m "feat: add new feature"

# 5. Push
git push origin feature/my-feature
```

## Additional Resources

- **Project Documentation:** `/docs/`
- **CLAUDE.md:** Comprehensive project overview and guidelines
- **Testing Guide:** `/docs/8-development/testing-guide.md`
- **Architecture:** `/docs/3-architecture/`
- **Configuration:** `/docs/4-configuration/`

## Version History

| Version | Date       | Changes                                    |
|---------|------------|--------------------------------------------|
| 1.0.0   | 2025-10-31 | Initial code styling guide                 |

## Maintenance

This guide should be reviewed and updated:
- When adding new tools or frameworks
- When coding patterns emerge across the codebase
- During quarterly documentation reviews
- When Python version requirements change

**Owner:** Development Team
**Review Cycle:** Quarterly
