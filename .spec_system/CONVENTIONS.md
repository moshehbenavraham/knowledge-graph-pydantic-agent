# CONVENTIONS.md

> Project-specific coding standards for the Agentic GraphRAG System.
> All contributors (human and AI) must follow these conventions.

---

## Guiding Principles

1. **Optimize for readability** over cleverness
2. **ONE unified agent** - extend, never create multiple implementations
3. **Centralized configuration** - never bypass the settings system
4. **Async everywhere** - all I/O operations must be async
5. **Type everything** - MyPy strict mode is enforced
6. **Test thoroughly** - 75% coverage minimum, behavior over implementation

---

## Critical Project Rules

### Configuration (NEVER bypass)

**ALWAYS** use centralized configuration:

```python
# CORRECT
from src.config import get_settings
settings = get_settings()
api_key = settings.llm_api_key

# WRONG - NEVER do this
import os
api_key = os.getenv("LLM_API_KEY")  # FORBIDDEN
```

Configuration hierarchy:
- `src/config/settings.py` - Single source of truth (Pydantic Settings)
- `src/config/agent.py` - Agent-specific facade
- `src/config/api.py` - API-specific facade
- `src/config/clients.py` - Client configuration facade

### Agent Architecture (ONE agent only)

**Only ONE agent exists**: `src/agent/unified_agent.py`

```python
# CORRECT - Add new capability as a tool
@super_agent.tool
async def my_new_capability(
    ctx: RunContext[UnifiedAgentDeps],
    param: str
) -> dict[str, Any]:
    """Tool docstring."""
    return {"result": "value"}

# WRONG - NEVER create separate agents
class MyNewAgent(Agent):  # FORBIDDEN
    pass
```

### Tool Development Pattern

All tools must follow this pattern:

```python
from pydantic_ai import RunContext
from src.agent.unified_agent import UnifiedAgentDeps
from typing import Any
import structlog

logger = structlog.get_logger(__name__)

async def my_tool(
    ctx: RunContext[UnifiedAgentDeps],
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Short description of what this tool does.

    Use for:
    - Specific use case 1
    - Specific use case 2

    Args:
        ctx: Agent runtime context with dependencies
        query: Description of the query parameter
        limit: Maximum number of results

    Returns:
        Dictionary with result data and metadata
    """
    logger.info("my_tool called", query_length=len(query), limit=limit)

    try:
        deps = ctx.deps
        # Implementation using deps.supabase, deps.embedding_client, etc.
        result = await some_async_operation()

        logger.info("my_tool completed", result_count=len(result))
        return {"status": "success", "data": result}

    except Exception as e:
        logger.exception("my_tool failed", query=query, error=str(e))
        return {"status": "error", "error": str(e)}
```

Key requirements:
- Must be async functions
- Use `RunContext[UnifiedAgentDeps]` for dependency injection
- Comprehensive error handling with informative messages
- Security validation for all inputs (especially SQL/code)
- Structured logging with context parameters

### UI Development Pattern

Add features via handlers in `src/ui/features/`, not new UI files:

```python
from .base_handler import BaseHandler
from typing import Any
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

class MyFeatureHandler(BaseHandler):
    def _setup_hook(self) -> None:
        """Initialize feature-specific resources."""
        self.my_resource = create_resource()

    async def run_agent(
        self,
        user_input: str,
        message_history: list[ModelRequest | ModelResponse],
        http_client: AsyncClient,
        **kwargs: Any,
    ) -> dict[str, Any]:
        agent_deps = self.get_agent_deps(http_client, **kwargs)
        # Implementation
        return {"response": result}
```

Handler types:
- `base_handler.py` - Core chat functionality
- `streaming_handler.py` - Real-time streaming
- `memory_handler.py` - mem0 integration
- `mcp_handler.py` - MCP server support
- `upload_handler.py` - File upload processing

---

## Code Style Standards

### Formatting

| Setting | Value |
|---------|-------|
| Line length | 100 characters |
| Formatter | Black |
| Python version | 3.11+ required |
| Import sorting | Ruff (isort rules) |

### Type Hints (Required)

```python
# CORRECT - Full type hints
def process_query(
    query: str,
    limit: int = 10,
    options: dict[str, Any] | None = None,
) -> list[SearchResult]:
    ...

async def fetch_data(url: str) -> dict[str, Any]:
    ...

# WRONG - Missing type hints
def process_query(query, limit=10):  # FAILS MyPy
    ...
```

MyPy strict mode is enforced:
- `disallow_untyped_defs = true`
- `check_untyped_defs = true`
- `strict_optional = true`

### Docstrings (Google Style)

75% coverage minimum enforced by `interrogate`.

```python
def calculate_similarity(
    embedding_a: list[float],
    embedding_b: list[float],
    normalize: bool = True,
) -> float:
    """
    Calculate cosine similarity between two embeddings.

    Uses normalized dot product for efficient comparison.

    Args:
        embedding_a: First embedding vector (1536 dimensions for OpenAI)
        embedding_b: Second embedding vector (same dimensions)
        normalize: Whether to normalize vectors before comparison

    Returns:
        Similarity score between -1 and 1 (1 = identical)

    Raises:
        ValueError: If embedding dimensions don't match

    Example:
        >>> similarity = calculate_similarity([0.1, 0.2], [0.1, 0.3])
        >>> print(f"Similarity: {similarity:.2f}")
    """
```

---

## Naming Conventions

### Python Naming

| Element | Convention | Example |
|---------|------------|---------|
| Variables | snake_case | `user_query`, `max_results` |
| Functions | snake_case | `get_settings()`, `retrieve_documents()` |
| Classes | PascalCase | `UnifiedAgentDeps`, `HybridSearch` |
| Constants | UPPER_SNAKE | `DEFAULT_LIMIT`, `MAX_RETRIES` |
| Private | _prefix | `_connection_manager`, `_setup_hook()` |
| Type aliases | PascalCase | `SearchResult`, `ChunkData` |

### Descriptive Names

```python
# CORRECT - Descriptive
def get_user_by_email(email: str) -> dict[str, Any] | None:
    ...

is_authenticated = check_session_valid(token)
has_graph_enabled = settings.enable_graph

# WRONG - Ambiguous
def get_user(e):  # What is 'e'?
    ...

auth = check(tok)  # Unclear
```

### Boolean Naming

Booleans should read as questions:

```python
# CORRECT
is_active = True
has_permission = check_role(user)
should_retry = attempt < max_retries
can_execute = validate_code(script)
enable_caching = True

# WRONG
active = True  # Not a question
permission = check_role(user)  # Noun, not boolean
```

---

## Async Patterns

### All I/O Must Be Async

```python
# CORRECT
async def fetch_documents(query: str) -> list[Document]:
    result = await supabase.from_("documents").select("*").execute()
    return result.data

async def search_with_timeout(query: str) -> SearchResult:
    async with asyncio.timeout(5.0):
        return await hybrid_search.search(query)

# WRONG - Blocking I/O
def fetch_documents(query: str) -> list[Document]:  # Not async!
    result = requests.get(url)  # Blocks event loop
    return result.json()
```

### Context Managers

```python
# CORRECT - Use async with for resources
async with super_agent.iter(user_input, deps=deps) as run:
    async for node in run:
        # Process streaming nodes

async with httpx.AsyncClient() as client:
    response = await client.get(url)

# WRONG - Deprecated patterns
run_mcp_servers()  # Deprecated, use async with agent:
```

### Parallel Execution

```python
# CORRECT - Parallel when independent
results = await asyncio.gather(
    vector_search(query),
    graph_search(query),
    return_exceptions=True,
)

# Handle exceptions from gather
for result in results:
    if isinstance(result, Exception):
        logger.error("Search failed", error=str(result))
```

---

## Logging Standards

### Use structlog With Context

```python
import structlog

logger = structlog.get_logger(__name__)

# CORRECT - Structured context parameters
logger.info(
    "Document retrieval completed",
    query_length=len(query),
    chunks_returned=len(result.chunks),
    strategy_used=result.search_strategy.value,
    query_time_ms=result.query_time * 1000,
)

logger.exception(
    "Smart search failed",
    query=user_query,
    error=str(e),
    error_type=type(e).__name__,
)

# WRONG - Unstructured string formatting
logger.info(f"Found {len(results)} results for query: {query}")  # Hard to parse
```

### Log Levels

| Level | Use For |
|-------|---------|
| `debug` | Detailed internal state, loop iterations |
| `info` | Key operations, state changes, completions |
| `warning` | Recoverable issues, deprecated usage |
| `error` | Failures that don't crash the app |
| `exception` | Errors with stack traces |

### Visual Separation for Major Operations

```python
logger.info("=" * 80)
logger.info("Handler initialization starting", handler_class=self.__class__.__name__)
# ... operation ...
logger.info("Handler initialization COMPLETE")
```

---

## Error Handling

### Comprehensive Try/Except

```python
async def retrieve_documents(query: str) -> str:
    logger.info("retrieve_documents called", query_length=len(query))

    try:
        hybrid_search = await get_hybrid_search()
        result = await hybrid_search.search(query=query)

        logger.info(
            "Document retrieval completed",
            chunks_returned=len(result.chunks),
        )
        return format_results(result)

    except asyncio.TimeoutError:
        logger.warning("Search timed out", query=query)
        return "Search timed out. Please try a shorter query."

    except ConnectionError as e:
        logger.error("Database connection failed", error=str(e))
        return f"Database unavailable: {e}"

    except Exception as e:
        logger.exception("Document retrieval failed", query=query, error=str(e))
        return f"Error retrieving documents: {e}"
```

### Security-Sensitive Error Handling

```python
# Don't expose internal details in user-facing errors
try:
    user = authenticate(username, password)
except InvalidCredentialsError:
    # CORRECT - Generic message
    return "Invalid username or password"
    # WRONG - Reveals which field was wrong
    # return "Password incorrect for user admin"
```

---

## Testing Standards

### Test Structure

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing."""
    client = MagicMock()
    client.rpc.return_value.execute = MagicMock(
        return_value=MagicMock(data=[{"content": "test"}])
    )
    return client

class TestSmartSearch:
    """Test suite for smart search functionality."""

    @pytest.mark.asyncio
    async def test_returns_results_for_valid_query(self, mock_supabase):
        """Test that valid queries return expected results."""
        with patch("src.tools.rag.get_hybrid_search") as mock_search:
            mock_search.return_value.search = AsyncMock(
                return_value=create_mock_result()
            )

            result = await smart_search_tool("machine learning")

            assert result["status"] == "success"
            assert len(result["chunks"]) > 0

    @pytest.mark.asyncio
    async def test_handles_empty_query_gracefully(self):
        """Test that empty queries don't crash."""
        result = await smart_search_tool("")
        assert "error" in result or result["chunks"] == []
```

### Test Naming

Test names describe scenario and expectation:

```python
# CORRECT
def test_returns_none_when_user_not_found():
def test_raises_validation_error_for_invalid_email():
def test_creates_session_on_successful_login():

# WRONG
def test_user():  # What about the user?
def test_login_works():  # What does "works" mean?
```

### Coverage Requirements

- Minimum: 75% (enforced by pytest-cov)
- Test suite: ~3,788 tests, ~7-10 minutes execution
- Run with: `make test` or `make test-parallel`

---

## Security Standards

### Bandit Scanning

Bandit runs on pre-commit. When suppressing warnings:

```python
# CORRECT - Justify the suppression
api_host: str = Field(
    default="0.0.0.0",  # nosec B104 - Binding to all interfaces required for container deployment
    description="API server host",
)

# WRONG - Suppression without justification
password = "hardcoded"  # nosec  # Why is this OK?
```

### SQL Injection Prevention

```python
# CORRECT - Parameterized via Supabase
response = (
    client.table("documents")
    .select("*")
    .eq("id", document_id)  # Parameterized
    .execute()
)

# CORRECT - Using RPC for complex queries
result = client.rpc("search_documents", {"query_embedding": embedding})

# WRONG - String interpolation
query = f"SELECT * FROM documents WHERE id = '{document_id}'"  # VULNERABLE
```

### Input Validation

```python
# Validate inputs at system boundaries
def execute_sql(sql_query: str) -> str:
    # Strip trailing semicolons (Supabase RPC requirement)
    sql_query = sql_query.rstrip(";")

    # Validate read-only
    if not sql_query.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed"

    # Execute via safe RPC
    return client.rpc("execute_readonly_query", {"query": sql_query})
```

---

## Git and Version Control

### Commit Messages

Imperative mood, conventional commits format:

```
feat: add OAuth 2.0 authentication for Google and GitHub
fix: resolve session timeout race condition in streaming handler
docs: update deployment guide for Coolify
refactor: extract hybrid search logic to dedicated module
test: add coverage for password reset flow
chore: update dependencies to fix security vulnerabilities
```

### Attribution Rules (CRITICAL)

**NEVER attribute commits to Claude, Anthropic, or AI**:

```bash
# CORRECT
git commit -m "Add user authentication system"

# WRONG - FORBIDDEN
git commit -m "Add user authentication

Co-Authored-By: Claude <noreply@anthropic.com>  # NEVER
Generated with Claude Code  # NEVER
"
```

### Branch Naming

```
feat/user-authentication
fix/session-timeout
docs/deployment-guide
refactor/search-module
test/oauth-coverage
```

---

## Pre-commit Hooks

The following hooks run automatically:

| Hook | Purpose |
|------|---------|
| black | Code formatting (100 char lines) |
| ruff | Linting + import sorting |
| mypy | Strict type checking |
| bandit | Security scanning |
| pip-audit | Dependency vulnerability scanning |
| interrogate | Docstring coverage (75% min) |
| check-yaml/json/toml | Config file validation |
| trailing-whitespace | Whitespace cleanup |
| mixed-line-ending | LF only (Unix) |

Install: `make pre-commit-install`
Run manually: `make pre-commit-run`

---

## Database Patterns

### Supabase Client Usage

```python
from src.clients.database import get_supabase_client

client = get_supabase_client()

# Query pattern
response = (
    client.table("documents")
    .select("id, title, content")
    .eq("source", source_filter)
    .order("created_at", desc=True)
    .limit(10)
    .execute()
)

if not response.data:
    return []

return response.data
```

### Vector Dimensions

| Provider | Dimensions |
|----------|------------|
| OpenAI (text-embedding-3-small) | 1536 |
| Ollama (nomic-embed-text) | 768 |

Ensure SQL schema matches: `embedding vector(1536)` or `vector(768)`

---

## Project-Specific Patterns

### Global Singleton Initialization

```python
# Pattern for expensive resources
_connection_manager: ConnectionManager | None = None
_current_loop: asyncio.AbstractEventLoop | None = None

async def get_connection_manager() -> ConnectionManager:
    global _connection_manager, _current_loop

    # Handle event loop changes (Streamlit can switch loops)
    current_loop = asyncio.get_running_loop()
    if _current_loop is not current_loop:
        _connection_manager = None
        _current_loop = current_loop

    if _connection_manager is None:
        _connection_manager = await ConnectionManager.create()

    return _connection_manager
```

### Analytics Logging

```python
from src.agentic_rag.analytics import SearchAnalyticsEvent, get_analytics_logger

# Non-blocking analytics (don't fail operations if analytics fails)
try:
    analytics_logger = get_analytics_logger()
    event = SearchAnalyticsEvent(
        query_text=query,
        strategy_used=strategy.value,
        total_latency_ms=latency_ms,
    )
    await analytics_logger.log_search(event)
except Exception as e:
    logger.warning(f"Failed to log analytics: {e}")
    # Continue - analytics failure shouldn't break the app
```

---

## When In Doubt

1. Check `CLAUDE.md` for project-specific guidance
2. Look at existing similar code in the codebase
3. Ask - leave it better than you found it
4. Ship, learn, iterate

---

## Infrastructure Configuration

| Component | Provider | Status | Details |
|-----------|----------|--------|---------|
| CDN/DNS | Cloudflare | configured | Domain management via Cloudflare |
| Hosting | Coolify/Docker | configured | docker-compose.coolify.yml, 8GB VPS |
| Database | PostgreSQL | configured | Supabase (managed), daily backups included |
| Knowledge Graph | Neo4j Aura | configured | Managed service, automatic daily backups |
| Cache | In-memory/Redis | configured | Optional Redis, in-memory fallback |
| Health | FastAPI | configured | /health/*, Kubernetes probes |
| Security | Middleware | configured | RateLimitMiddleware (60/min), SecurityHeadersMiddleware |
| Backup | Custom script | configured | scripts/backup.sh, 7-day retention, R2 optional |
| Deploy | GitHub Actions | configured | release.yml (tag-based), GHCR container registry |

### Infrastructure Bundles (4/4 Configured)

| Bundle | Components | Verification |
|--------|------------|--------------|
| Health | /health endpoint, /health/detailed, readiness/liveness/startup probes | `curl /health` returns 200 + JSON |
| Security | Rate limiting (60 req/min), security headers, CORS | Rapid requests get 429 |
| Backup | PostgreSQL dump, Neo4j export, cloud upload (R2) | `make backup` creates ./backups/*.gz |
| Deploy | Release workflow, container build, GHCR push | Tags (v*) trigger release.yml |

### Backup Strategy

**Managed Services (Automatic)**:
- Supabase: Daily backups, PITR on Pro plan
- Neo4j Aura: Automatic daily backups, 7-day retention

**Custom Backups (On-Demand)**:
- Script: `scripts/backup.sh`
- Commands: `make backup`, `make backup-postgres`, `make backup-neo4j`, `make backup-upload`
- Retention: 7 days local (configurable via BACKUP_RETENTION_DAYS)
- Cloud storage: Cloudflare R2 (optional, configure R2_* env vars)

---

## CI/CD Configuration

| Bundle | Status | Workflow |
|--------|--------|----------|
| Code Quality | configured | .github/workflows/ci.yml |
| Build & Test | configured | .github/workflows/ci.yml |
| Security | configured | .github/workflows/ci.yml, .github/workflows/security-supply-chain.yml |
| Integration | configured | .github/workflows/ci.yml (tests), .github/workflows/performance.yml |
| Operations | configured | .github/workflows/release.yml, .github/dependabot.yml |

### Workflow Files

| Workflow | Purpose | Triggers |
|----------|---------|----------|
| ci.yml | Lint, format, type check, tests, coverage | push, pull_request |
| security-supply-chain.yml | Gitleaks, Trivy, pip-audit, SBOM | push, pull_request, schedule |
| docs-validation.yml | Link validation, markdown syntax | push (docs), schedule |
| performance.yml | Load, stress, spike, endurance tests | schedule, manual |
| release.yml | Package build, container build, GitHub release | tags (v*), manual |

### Dependabot

Configured for:
- **pip**: Weekly Python dependency updates (grouped by dev/security)
- **github-actions**: Weekly action updates
- **docker**: Weekly Docker base image updates

---

*Last updated: 2025-12-30 | Agentic GraphRAG System v1.8.0*
