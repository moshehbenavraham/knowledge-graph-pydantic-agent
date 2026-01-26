# Knowledge Graph Pydantic Agent Testing Guide

Comprehensive testing documentation for the Knowledge Graph Pydantic Agent platform.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Test Execution](#test-execution)
- [Manual UI Testing](#manual-ui-testing)
- [Writing Tests](#writing-tests)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)

---

## Quick Start

### Manual Testing (3 Minutes)

```bash
# Start the UI
make run-ui-simple

# Open browser: http://localhost:8501

# Test these queries:
1. "What documents do you have?" → Tests document listing
2. "How much did OpenAI raise in their latest funding round?" → Tests RAG retrieval
3. "What's the latest news about AI?" → Tests web search
4. "How many documents are in the database?" → Tests SQL queries
```

### Automated Testing (Quick Check)

```bash
# Activate environment
source .venv/bin/activate

# Run all tests (1,113 tests, ~7-10 minutes)
make test

# Run with coverage (~10-15 minutes)
make test-coverage

# Run specific test file
pytest tests/test_clients.py -v
```

**System Configuration:**
- URL: http://localhost:8501
- Mode: Simple UI (basic chat, no streaming)
- Documents: Example documents in `docs/x-examples/`
- **Total Tests**: 1,113 tests
- **Test Coverage Target**: 75% minimum
- **Execution Time**: 7-10 minutes (full suite), 10-15 minutes (with coverage)

---

## Test Execution

### Environment Setup

```bash
# Install dependencies
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-mock
```

### Environment Configuration

Tests automatically use mock configurations via `tests/conftest.py`. No `.env.test` file needed.

### Basic Commands

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=term-missing --cov-report=html

# Specific test file
pytest tests/test_clients.py -v

# Specific test class
pytest tests/test_clients.py::TestGetLlmClient

# Specific test method
pytest tests/test_clients.py::TestGetLlmClient::test_get_llm_client

# Stop on first failure
pytest -x

# Re-run last failed
pytest --lf

# Show print statements
pytest -s
```

### Test Categories

```bash
# Unit tests
pytest tests/test_*.py

# Integration tests
pytest tests/integration/

# Exclude specific tests
pytest --ignore=tests/rag_pipeline/
```

### Timeout Configuration

The test suite is substantial. **Always use adequate timeouts** when running in CI/CD or scripts:

```bash
# Recommended for scripts
timeout 1800 pytest  # 30 minutes

# CI/CD job configuration
timeout-minutes: 25  # GitHub Actions
```

### Async Test Configuration

If you encounter `RuntimeError: Task attached to a different loop`:

**1. pyproject.toml:**
```toml
[tool.pytest.ini_options]
asyncio_default_fixture_loop_scope = "module"
asyncio_mode = "auto"
```

**2. Test files with async operations:**
```python
@pytest.mark.asyncio(loop_scope="module")
class TestDatabaseOperations:
    async def test_something(self):
        # Your test
```

**3. conftest.py:**
```python
@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
```

---

## Manual UI Testing

### Test Checklist

#### Phase 1: Basic Functionality

**Simple Chat:**
```
Query: "Hello! Can you introduce yourself?"
Expected: Agent greeting and capabilities explanation
```

**Basic Knowledge:**
```
Query: "What's the capital of France?"
Expected: "Paris"
```

**Math:**
```
Query: "What is 157 * 234?"
Expected: 36,738
```

#### Phase 2: Document Retrieval & RAG

**List Documents:**
```
Query: "What documents do you have available?"
Tool: list_all_documents
Expected: List of documents with IDs and metadata
```

**Simple Retrieval:**
```
Query: "How much did OpenAI raise in their latest funding round?"
Tool: smart_search or retrieve_documents
Expected: Information from ingested documents
```

**Multi-Document Synthesis:**
```
Query: "Compare OpenAI's strategy with Apple's approach to AI development"
Tool: smart_search or comprehensive_search
Expected: Synthesis from multiple documents
```

#### Phase 3: Web Search

```
Query: "What are the latest news about OpenAI?"
Tool: search_web
Expected: Recent web results
Provider: Jina.ai, Brave Search, or SearXNG (configured via WEB_SEARCH_PROVIDER)
```

#### Phase 4: SQL Queries

```
Query: "How many documents are in the database?"
Tool: execute_sql or query_tabular_data
Expected: Document count from database
```

**Security Test:**
```
Query: "DROP TABLE documents"
Expected: REJECTED - read-only queries only
```

#### Phase 5: Memory & Context

```
Query 1: "My favorite color is blue"
Query 2: "What's my favorite color?"
Expected: Remembers from conversation context
```

#### Phase 6: Tool Combinations

```
Query: "What do my documents say about Apple's AI struggles, and what's Apple announcing today?"
Expected: retrieve_documents (historical) + web_search (current)
```

### 10-Minute Test Session

```
1. "Hello, what can you help me with?"
2. "What documents do you have?"
3. "How much did OpenAI raise in their latest funding round?"
4. "How many documents are in the database?"
5. "What's the latest news about OpenAI today?"
6. "Compare what my documents say about Apple with current news"
7. "Summarize our conversation"
```

### Success Criteria

- [ ] UI loads without errors
- [ ] Agent responds to simple queries
- [ ] Can list and retrieve documents
- [ ] Web search returns current results
- [ ] SQL queries execute safely (read-only)
- [ ] Multiple tools can be used in one query
- [ ] Graceful error handling
- [ ] Reasonable response times (< 10s)

---

## Writing Tests

### Test Structure Template

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.module_to_test import function_to_test

class TestModuleName:
    """Test class for ModuleName functionality."""

    def setup_method(self):
        """Setup run before each test method."""
        self.mock_data = {"key": "value"}

    @patch("module_to_test.external_dependency")
    def test_function_success(self, mock_dependency):
        """Test successful function execution."""
        # Arrange
        mock_dependency.return_value = "expected_result"

        # Act
        result = function_to_test("input")

        # Assert
        assert result == "expected_result"
        mock_dependency.assert_called_once_with("input")

    def test_function_error_handling(self):
        """Test function error handling."""
        with pytest.raises(ValueError, match="Expected error message"):
            function_to_test(invalid_input)
```

### Essential Patterns

#### 1. Configuration Mocking

**Always use `get_settings()`, never `os.getenv()`:**

```python
@patch("module.get_settings")
def test_function(self, mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.database_url = "postgresql://test"
    mock_settings.llm_provider = "openai"
    mock_get_settings.return_value = mock_settings
```

#### 2. Async Testing

**Use AsyncMock for async functions:**

```python
@pytest.mark.asyncio
@patch("module.async_function", new=AsyncMock(return_value=True))
async def test_async_function(mock_func):
    result = await mock_func()
    assert result is True
```

#### 3. Async Context Managers

```python
mock_resource = AsyncMock()
mock_context = AsyncMock()
mock_context.__aenter__ = AsyncMock(return_value=mock_resource)
mock_context.__aexit__ = AsyncMock(return_value=None)
mock_pool.acquire = MagicMock(return_value=mock_context)
```

#### 4. Parameterized Tests

```python
@pytest.mark.parametrize("input_value,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_multiple_inputs(input_value, expected):
    result = function_to_test(input_value)
    assert result == expected
```

#### 5. Fixtures for Common Setup

```python
@pytest.fixture
def mock_agent_deps():
    """Fixture providing mock AgentDeps."""
    return MagicMock(
        supabase=MagicMock(),
        embedding_client=MagicMock(),
        memories=MagicMock()
    )

def test_with_fixture(mock_agent_deps):
    result = function_using_deps(mock_agent_deps)
    assert result is not None
```

---

## Common Patterns

### Architecture Migration

#### Configuration: os.getenv() → get_settings()

**Old (Deprecated):**
```python
@patch("module.os.getenv")
def test_function(self, mock_getenv):
    mock_getenv.side_effect = lambda key, default=None: {...}.get(key, default)
```

**New (Required):**
```python
@patch("module.get_settings")
def test_function(self, mock_get_settings):
    mock_settings = MagicMock()
    mock_settings.attribute = "value"
    mock_get_settings.return_value = mock_settings
```

#### Singleton Facades: No Caching in __init__

**Wrong:**
```python
class APIConfig:
    def __init__(self):
        self._settings = get_settings()  # Cached once!

    @property
    def port(self):
        return self._settings.api_port  # Stale after reload
```

**Correct:**
```python
class APIConfig:
    @property
    def port(self):
        return get_settings().api_port  # Fresh every time
```

### FastAPI Testing

**Use dependency overrides, not patch():**

```python
@pytest.fixture
def app(mock_postgres_store):
    app = FastAPI()
    app.include_router(router)

    async def get_mock_postgres_store():
        return mock_postgres_store

    app.dependency_overrides[get_postgres_store] = get_mock_postgres_store
    return app

def test_endpoint(app, client):
    response = client.get("/api/v1/foo")
    assert response.status_code == 200
```

### Mock Configuration

#### Patch Location

**Patch where imported/used, not where defined:**

```python
# src/auth/db.py defines list_users()
# src/auth/streamlit_auth.py imports: from src.auth.db import list_users

# Wrong
@patch("src.auth.streamlit_auth.list_users")

# Correct
@patch("src.auth.db.list_users")
```

#### Mock Attributes

**Set attributes explicitly, don't rely on auto-generation:**

```python
# Wrong
mock_result = MagicMock()
# mock_result.confidence is a Mock object!

# Correct
mock_result = MagicMock()
mock_result.confidence = 0.9
mock_result.chunks = []
mock_result.sources = ["source1", "source2"]
```

#### Entity Mock Format

```python
# Wrong
entities = [MagicMock(name=f"Entity{i}") for i in range(10)]
# entities[0].name is a Mock object!

# Correct
entities = []
for i in range(10):
    entity = MagicMock()
    entity.name = f"Entity{i}"  # Set as attribute
    entities.append(entity)
```

### Data Types

#### UUID Types

```python
from uuid import uuid4

# Wrong
chunk = ChunkResult(
    chunk_id="chunk-1",  # String!
    document_id="doc-1",
)

# Correct
chunk = ChunkResult(
    chunk_id=uuid4(),
    document_id=uuid4(),
)
```

#### Enum Values

```python
# API receives lowercase strings
{"strategy": "vector"}

# Convert to enum
strategy = SearchStrategy(request.strategy)  # SearchStrategy.VECTOR_ONLY

# Enum value
strategy.value  # "vector_only"
```

### Error Handling

**Tools return error strings, not exceptions:**

```python
# Wrong
with pytest.raises(Exception, match="Connection failed"):
    await execute_sql_query_tool(...)

# Correct
result = await execute_sql_query_tool(...)
assert "Error executing SQL query" in result
assert "Connection failed" in result
```

### Critical Gotchas

**1. AsyncMock for Async Functions**
```python
# Wrong - causes "can't be used in await"
@patch("module.async_func", return_value=True)

# Right
@patch("module.async_func", new=AsyncMock(return_value=True))
```

**2. FastAPI Dependencies**
```python
# Wrong - doesn't work
with patch("endpoints.get_db", return_value=mock_db):
    response = client.get("/api/v1/foo")

# Right - use dependency_overrides
app.dependency_overrides[get_db] = lambda: mock_db
response = client.get("/api/v1/foo")
```

**3. Mock Attribute Truthiness**
```python
# Wrong - MagicMock creates attributes (always truthy)
if getattr(mock_commit, "is_merge", False):
    # Always True!

# Right - delete or set explicitly
del mock_commit.is_merge
# or
mock_commit.is_merge = False
```

---

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

**Environment Variables:**
```bash
python -c "import os; print(os.getenv('SUPABASE_URL'))"
```

**Async Test Errors:**
```python
# Don't forget await
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
```

**Mock Not Called:**
```python
# Use full import path
@patch("src.module.function")  # Correct
def test_function(mock_func):
    mock_func.return_value = "expected"
```

### Debugging

```bash
# Verbose output
pytest -v -s --tb=long

# Single test with debugging
pytest tests/test_file.py::test_function -v -s

# Interactive debugging
pytest --pdb tests/test_file.py::test_function

# Profile execution
pytest --profile

# Show slowest tests
pytest --durations=10
```

### Test Failures

1. Read error message carefully
2. Verify mock setup matches implementation
3. Check for async/sync mismatches
4. Confirm patch location (where used, not defined)
5. Review recent code changes

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 25  # Full suite takes ~15 min + buffer
    strategy:
      matrix:
        python-version: [3.11, 3.12]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run tests with coverage
      timeout-minutes: 20
      run: |
        timeout 1200 pytest --cov=src --cov-report=xml --cov-fail-under=75

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: python -m pytest
        language: system
        pass_filenames: false
        always_run: true
```

### Test Automation Scripts

**scripts/test.sh:**
```bash
#!/bin/bash
set -e

source .venv/bin/activate

# Linting
black --check src/ tests/
ruff check src/ tests/

# Tests with coverage
pytest --cov=src --cov-report=term-missing --cov-fail-under=75

echo "All tests passed!"
```

**scripts/test-quick.sh:**
```bash
#!/bin/bash
source .venv/bin/activate
pytest tests/test_clients.py tests/test_code_execution.py -v
```

---

## Coverage Requirements

**Target**: 75% minimum (enforced by pytest-cov)

**Priority Levels:**
- **Critical (95%+)**: Agent core, clients, tools
- **Important (80%+)**: Utilities, UI, error handling
- **Supporting (60%+)**: RAG pipeline, configuration

**Measuring Coverage:**
```bash
# Detailed report
pytest --cov=src --cov-report=term-missing --cov-report=html

# By module
pytest --cov=src/clients --cov-report=term-missing

# Enforce threshold
pytest --cov=src --cov-fail-under=75
```

---

## Test Maintenance

### Regular Tasks

- **Weekly**: Review failing tests, update mocks
- **Monthly**: Update dependencies, check for deprecations
- **Quarterly**: Review coverage, add missing tests
- **Release**: Full suite execution, performance validation

### Best Practices

**When Writing New Tests:**
- Use `get_settings()` mocking, never `os.getenv()`
- Use `AsyncMock` for all async functions
- Set all mock attributes explicitly
- Test both success and error paths

**When Refactoring Code:**
- Update enum values across tests
- Check dataclass vs dict access patterns
- Verify async/await consistency
- Update import paths
- Test configuration reload scenarios

**When Adding Features:**
- Use dependency injection
- Create fixtures for tests
- Return error strings from tools (not exceptions)
- Use proper UUID types
- Document expected data formats

---

## Quick Reference

### Essential Commands

```bash
# Basic test run
pytest

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific test
pytest tests/test_clients.py -v

# Failed tests only
pytest --lf

# Stop on first failure
pytest -x
```

### UI Testing Modes

```bash
make run-ui-simple    # No streaming, basic chat only
make run-ui-standard  # Streaming + tool visibility
make run-ui-advanced  # Full features (Memory + MCP)
make run-api          # REST API (port 8058)
```

### Test Status

- **Working**: Clients, Tools, Code Execution, Image Analysis, Web Search, SQL Query
- **In Progress**: Agent configuration, Memory integration, RAG pipeline
- **Needs Work**: UI tests, E2E workflows, Performance tests

For latest status: `pytest --tb=no -q`

---

**Good luck testing!**
