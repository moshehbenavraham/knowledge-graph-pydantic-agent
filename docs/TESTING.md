# Testing Guide

This document provides comprehensive guidance for testing the Base Agent platform, including setup, execution, and best practices.

## Table of Contents

- [Overview](#overview)
- [Test Environment Setup](#test-environment-setup)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Coverage Requirements](#coverage-requirements)
- [Writing Tests](#writing-tests)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)

## Overview

The Base Agent platform uses a comprehensive testing strategy that includes:

- **Unit Tests**: Testing individual components in isolation
- **Integration Tests**: Testing component interactions
- **End-to-End Tests**: Testing complete user workflows
- **Performance Tests**: Testing system performance under load
- **Security Tests**: Testing security measures and vulnerabilities

### Current Test Status

- **Total Tests**: 164 tests
- **Passing Tests**: 76 (46%)
- **Test Coverage**: 33%
- **Target Coverage**: 75%

## Test Environment Setup

### Prerequisites

1. **Python Environment**: Python 3.12+ with virtual environment
2. **Dependencies**: All project dependencies installed
3. **Environment Variables**: Test-specific configuration

### Installation

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install test dependencies (if separate)
pip install pytest pytest-cov pytest-asyncio pytest-mock
```

### Environment Configuration

The testing framework uses a dedicated test environment configuration:

#### `.env.test` File

```bash
# Supabase Configuration (test values)
SUPABASE_URL=https://test.supabase.co
SUPABASE_KEY=test_key_for_testing_only
SUPABASE_SERVICE_KEY=test_service_key_for_testing_only

# OpenAI Configuration (test values)
OPENAI_API_KEY=test_openai_key
LLM_API_KEY=test_llm_key
LLM_BASE_URL=https://api.openai.com/v1

# Other test configurations
LOG_LEVEL=DEBUG
ENVIRONMENT=test
MEM0_API_KEY=test_mem0_key
BRAVE_SEARCH_API_KEY=test_brave_key
SEARXNG_URL=http://localhost:8080
DATABASE_URL=postgresql://test:test@localhost:5432/test_db
```

#### Automatic Environment Loading

The test environment is automatically configured through `tests/conftest.py`:

```python
# Environment variables are loaded automatically
# No manual setup required for individual tests
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_clients.py

# Run specific test class
python -m pytest tests/test_clients.py::TestGetLlmClient

# Run specific test method
python -m pytest tests/test_clients.py::TestGetLlmClient::test_get_llm_client
```

### Coverage Testing

```bash
# Run tests with coverage
python -m pytest --cov=src --cov-report=term-missing

# Generate HTML coverage report
python -m pytest --cov=src --cov-report=html

# Coverage with specific threshold
python -m pytest --cov=src --cov-fail-under=75
```

### Test Categories

```bash
# Run only unit tests
python -m pytest tests/test_*.py

# Run integration tests
python -m pytest tests/test_integration.py

# Run end-to-end tests
python -m pytest tests/test_e2e.py

# Exclude specific test categories
python -m pytest --ignore=tests/rag_pipeline/
```

### Performance Testing

```bash
# Run performance tests
python -m pytest tests/test_integration.py::TestPerformanceIntegration -v

# Run with timing information
python -m pytest --durations=10

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation:

#### Client Tests (`tests/test_clients.py`)
- **LLM Client**: Tests OpenAI client configuration and initialization
- **Supabase Client**: Tests database client setup and connection
- **Memory Client**: Tests Mem0 client configuration for different providers

```bash
# Run client tests
python -m pytest tests/test_clients.py -v
```

#### Tool Tests
- **Code Execution** (`tests/test_code_execution.py`): Tests safe Python code execution
- **Image Analysis** (`tests/test_image_analysis.py`): Tests image processing capabilities
- **Web Search** (`tests/test_web_search.py`): Tests Brave Search and SearXNG integration
- **SQL Query** (`tests/test_sql_query.py`): Tests database query execution
- **RAG Tools** (`tests/test_rag.py`): Tests document retrieval and embedding

```bash
# Run all tool tests
python -m pytest tests/test_*_*.py -v
```

### Integration Tests (`tests/test_integration.py`)

Integration tests verify component interactions:

- **RAG Pipeline Integration**: Document retrieval and processing workflows
- **Database Operations**: SQL execution and data handling
- **Tool Integration**: Multi-tool workflows and error propagation
- **Memory System**: Memory persistence and vector store integration
- **Performance Integration**: Concurrent operations and resource management
- **Error Recovery**: Failover scenarios and system resilience
- **Security Integration**: SQL injection prevention and data sanitization

### End-to-End Tests (`tests/test_e2e.py`)

E2E tests simulate complete user workflows:

- **Research Workflows**: Complete information gathering and analysis
- **UI Functionality**: Streamlit interface testing
- **Error Handling**: System-wide error scenarios
- **Edge Cases**: Boundary conditions and unusual inputs
- **Performance Workflows**: High-load and memory-intensive operations

### Agent Tests (`tests/test_agent.py`)

Comprehensive agent functionality testing:

- **Agent Initialization**: Model configuration and setup
- **System Prompts**: Prompt formatting and memory integration
- **Tool Integration**: Individual tool execution within agent context
- **Error Handling**: Agent-level error scenarios
- **Multi-Provider Support**: Different LLM provider configurations
- **Memory Integration**: Memory-aware agent operations

## Coverage Requirements

### Current Coverage Status

```
Name                                        Coverage
-------------------------------------------------------------------------
src/clients/                               95%+ (High Priority - Core)
src/tools/                                 90%+ (High Priority - Core)
src/agent/                                 100% (Critical - Core)
src/utils/monitoring.py                    51% (Needs Improvement)
src/ui/                                    33-54% (Needs Improvement)
src/rag_pipeline/                          0-9% (Needs Major Work)
-------------------------------------------------------------------------
TOTAL                                      33% (Target: 75%)
```

### Coverage Goals

- **Critical Components**: 95%+ coverage
  - Agent core functionality
  - Client connections
  - Tool implementations
- **Important Components**: 80%+ coverage
  - Utilities and monitoring
  - UI components
  - Error handling
- **Supporting Components**: 60%+ coverage
  - RAG pipeline
  - Configuration management

### Measuring Coverage

```bash
# Detailed coverage report
python -m pytest --cov=src --cov-report=term-missing --cov-report=html

# Coverage by module
python -m pytest --cov=src/clients --cov-report=term-missing

# Fail if coverage below threshold
python -m pytest --cov=src --cov-fail-under=75

## Writing Tests

### Test Structure

Follow this structure for new tests:

```python
import pytest
from unittest.mock import MagicMock, patch
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

### Testing Best Practices

#### 1. **Isolation and Mocking**

```python
# Mock external dependencies
@patch("src.clients.database.create_client")
def test_database_function(mock_create_client):
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    # Test implementation
```

#### 2. **Async Testing**

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality."""
    result = await async_function()
    assert result is not None
```

#### 3. **Parameterized Tests**

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

#### 4. **Fixtures for Common Setup**

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

### Test Categories to Implement

#### High Priority
1. **Error Handling Tests**: Comprehensive error scenario coverage
2. **Edge Case Tests**: Boundary conditions and unusual inputs
3. **Performance Tests**: Response time and resource usage validation
4. **Security Tests**: Input validation and injection prevention

#### Medium Priority
1. **Configuration Tests**: Different environment configurations
2. **Concurrency Tests**: Multi-user and parallel operation testing
3. **Data Validation Tests**: Input/output format verification

## Troubleshooting

### Common Test Issues

#### 1. **Import Errors**

```bash
# Error: ModuleNotFoundError
# Solution: Check PYTHONPATH and relative imports
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

#### 2. **Environment Variable Issues**

```bash
# Error: Missing environment variables
# Solution: Ensure .env.test is loaded
python -c "import os; print(os.getenv('SUPABASE_URL'))"
```

#### 3. **Async Test Issues**

```python
# Error: RuntimeWarning: coroutine was never awaited
# Solution: Use proper async/await syntax
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()  # Don't forget await
```

#### 4. **Mock Configuration Issues**

```python
# Error: Mock not being called as expected
# Solution: Verify mock path and setup
@patch("src.module.function")  # Use full import path
def test_function(mock_func):
    mock_func.return_value = "expected"
    # Test implementation
```

### Debugging Tests

```bash
# Run with debugging output
python -m pytest -v -s --tb=long

# Run single test with debugging
python -m pytest tests/test_file.py::test_function -v -s

# Use pdb for interactive debugging
python -m pytest --pdb tests/test_file.py::test_function
```

### Performance Debugging

```bash
# Profile test execution
python -m pytest --profile

# Memory usage profiling
python -m pytest --memray tests/test_file.py

## CI/CD Integration

### GitHub Actions Configuration

Example workflow for automated testing:

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
    strategy:
      matrix:
        python-version: [3.12]

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
      run: |
        python -m pytest --cov=src --cov-report=xml --cov-fail-under=75

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

Configure pre-commit hooks for automatic testing:

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

#### `scripts/test.sh`

```bash
#!/bin/bash
set -e

echo "Running Base Agent Test Suite..."

# Activate virtual environment
source venv/bin/activate

# Run linting
echo "Running code quality checks..."
black --check src/ tests/
ruff check src/ tests/

# Run tests with coverage
echo "Running tests with coverage..."
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=75

echo "All tests passed!"
```

#### `scripts/test-quick.sh`

```bash
#!/bin/bash
# Quick test run for development

source venv/bin/activate
python -m pytest tests/test_clients.py tests/test_code_execution.py -v
```

### Docker Testing

```dockerfile
# Dockerfile.test
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-m", "pytest", "--cov=src", "--cov-report=term-missing"]
```

```bash
# Run tests in Docker
docker build -f Dockerfile.test -t base-agent-test .
docker run --rm base-agent-test
```

## Test Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review failing tests and update mocks
2. **Monthly**: Update test dependencies and check for deprecations
3. **Quarterly**: Review test coverage and add missing tests
4. **Release**: Full test suite execution and performance validation

### Test Data Management

- **Mock Data**: Keep mock data in `tests/fixtures/`
- **Test Databases**: Use isolated test databases
- **Cleanup**: Ensure tests clean up after themselves

### Documentation Updates

- Update this document when adding new test categories
- Document new testing patterns and best practices
- Maintain examples for common testing scenarios

---

## Quick Reference

### Essential Commands

```bash
# Basic test run
python -m pytest

# With coverage
python -m pytest --cov=src --cov-report=term-missing

# Specific test file
python -m pytest tests/test_clients.py -v

# Failed tests only
python -m pytest --lf

# Stop on first failure
python -m pytest -x
```

### Test Status Summary

- ✅ **Working**: Clients, Tools, Code Execution, Image Analysis, Web Search, SQL Query
- 🔄 **In Progress**: Agent configuration, Memory integration, RAG pipeline
- ❌ **Needs Work**: UI tests, E2E workflows, Performance tests

For the latest test status, run: `python -m pytest --tb=no -q`
```
```
```
