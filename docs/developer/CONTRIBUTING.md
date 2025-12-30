# Contributing Guidelines

Guidelines for contributing to the Agentic GraphRAG project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Commit Guidelines](#commit-guidelines)
- [Documentation](#documentation)

---

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on technical merit
- Acknowledge contributions

---

## Getting Started

1. Read the [Setup Guide](setup_guide.md) to configure your environment
2. Review [CONVENTIONS.md](../../.spec_system/CONVENTIONS.md) for architecture understanding
3. Check existing issues and PRs before starting work
4. Create an issue for significant changes before implementation

---

## Development Process

### 1. Issue First

For non-trivial changes:
1. Create an issue describing the change
2. Discuss approach with maintainers
3. Get approval before starting work

### 2. Branch Strategy

```bash
# Feature branches
git checkout -b feature/descriptive-name

# Bug fixes
git checkout -b fix/issue-number-description

# Documentation
git checkout -b docs/topic-name
```

### 3. Development Loop

```bash
# Make changes
# ...

# Format code
make format

# Run linter
make lint

# Run tests
make test

# Commit (hooks run automatically)
git commit -m "Type: Description"
```

---

## Code Standards

### Python Style

- **Line length**: 100 characters
- **Formatter**: Black (automatic via pre-commit)
- **Linter**: Ruff (automatic via pre-commit)
- **Type checker**: MyPy (strict mode)

### Type Hints

Required for all function signatures:

```python
# Good
async def search_documents(
    query: str,
    limit: int = 10,
    filters: dict[str, Any] | None = None,
) -> list[SearchResult]:
    ...

# Bad (missing types)
async def search_documents(query, limit=10, filters=None):
    ...
```

### Docstrings

Use Google style for all public functions:

```python
async def search_documents(
    query: str,
    limit: int = 10,
) -> list[SearchResult]:
    """
    Search documents using semantic similarity.

    Args:
        query: Search query text
        limit: Maximum results to return

    Returns:
        List of matching search results

    Raises:
        SearchError: If search fails
    """
    ...
```

### Async Patterns

Use `async`/`await` for all I/O operations:

```python
# Good
async def fetch_data() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# Bad (blocking I/O)
def fetch_data() -> dict:
    response = requests.get(url)
    return response.json()
```

### Error Handling

Use structured error handling:

```python
from src.agentic_rag.resilience import ErrorCategory, categorize_exception

try:
    result = await operation()
except Exception as e:
    category = categorize_exception(e)
    if category == ErrorCategory.TRANSIENT:
        # Retry or fallback
        pass
    else:
        raise
```

### Imports

Organize imports (handled by Ruff):

```python
# Standard library
import asyncio
from typing import Any

# Third-party
import structlog
from fastapi import APIRouter

# Local
from src.config import get_settings
from src.utils.cache import RedisCache
```

---

## Testing Requirements

### Coverage Minimum

- **Overall**: 75% minimum
- **New code**: Should not decrease coverage

### Test Structure

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_database():
    """Fixture for mocked database client."""
    mock = AsyncMock()
    mock.query.return_value = [{"id": 1}]
    return mock

@pytest.mark.asyncio
async def test_search_returns_results(mock_database):
    """Test that search returns expected results."""
    # Arrange
    query = "test query"

    # Act
    results = await search(query, db=mock_database)

    # Assert
    assert len(results) > 0
    mock_database.query.assert_called_once()
```

### Test Categories

1. **Unit tests**: Test individual functions
2. **Integration tests**: Test component interactions
3. **End-to-end tests**: Test full workflows

### Running Tests

```bash
# All tests
make test

# With coverage
make test-coverage

# Specific file
pytest tests/test_search.py -v

# Specific test
pytest tests/test_search.py::test_vector_search -v

# By marker
pytest -m "not slow" -v
```

---

## Pull Request Process

### 1. Before Creating PR

- [ ] All tests pass locally (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] Linter passes (`make lint`)
- [ ] Security checks pass (`make security`)
- [ ] Documentation updated if needed
- [ ] No unnecessary file changes

### 2. PR Title Format

```
type: Short description

Examples:
feat: Add multi-hop query support
fix: Resolve circuit breaker state inversion
docs: Update API endpoint documentation
refactor: Simplify search result merging
test: Add integration tests for ingestion
```

### 3. PR Description Template

```markdown
## Summary
Brief description of changes.

## Changes
- List of specific changes
- ...

## Testing
- How was this tested?
- Any manual testing steps?

## Related Issues
Closes #123
```

### 4. Review Process

1. CI checks must pass
2. At least one approval required
3. Address all review comments
4. Squash commits before merge

---

## Commit Guidelines

### Commit Message Format

```
type: Subject line (max 72 chars)

Body explaining what and why (not how).
Wrap at 72 characters.

References #issue-number
```

### Commit Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring |
| `test` | Adding tests |
| `chore` | Build, config changes |

### Good Commit Examples

```bash
# Feature
feat: Add temporal trend analysis to search

Implements time-series analysis for queries containing
temporal patterns. Uses sliding window aggregation
over entity mentions.

Closes #45

# Bug fix
fix: Resolve Neo4j circuit breaker state inversion

Circuit breaker was incorrectly blocking requests when
CLOSED (should be healthy). Updated 9 locations to
follow standard pattern.

Fixes #78
```

---

## Documentation

### When to Update Docs

- New features: Add usage examples
- API changes: Update endpoint docs
- Configuration changes: Update .env.example
- Architecture changes: Update CLAUDE.md

### Documentation Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Main architecture reference |
| `docs/api/` | API documentation |
| `docs/developer/` | Developer guides |
| `docs/troubleshooting/` | Problem solutions |
| `docs/adr/` | Architecture decisions |

### Documentation Style

- Use clear, concise language
- Include code examples
- Keep formatting consistent
- Use ASCII only (no emojis)

---

## Questions?

- Create a discussion for general questions
- Create an issue for bugs or feature requests
- Review existing documentation first

---

**Last Updated**: 2025-12-30
