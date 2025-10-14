import asyncio
import os
from unittest.mock import MagicMock

import pytest


# Set required environment variables for tests
def setup_test_environment():
    """Ensure all required environment variables are set for testing."""
    test_env_vars = {
        # Supabase Configuration (test values)
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_key_for_testing_only",
        "SUPABASE_SERVICE_KEY": "test_service_key_for_testing_only",
        # Neo4j Configuration (test values)
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "test_password",
        "NEO4J_DATABASE": "test",
        # LLM Configuration (test values)
        "LLM_PROVIDER": "openai",
        "LLM_API_KEY": "test_openai_key",
        "LLM_CHOICE": "gpt-3.5-turbo",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        # Embedding Configuration (test values)
        "EMBEDDING_PROVIDER": "openai",
        "EMBEDDING_API_KEY": "test_openai_key",
        "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
        # Other test configurations
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test",
        "MEM0_API_KEY": "test_mem0_key",
        "BRAVE_API_KEY": "test_brave_key",
        "SEARXNG_BASE_URL": "http://localhost:8080",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        # Feature flags for testing
        "ENABLE_CODE_EXECUTION": "false",
        "ENABLE_WEB_SEARCH": "false",
        "ENABLE_IMAGE_ANALYSIS": "false",
        "ENABLE_LONG_TERM_MEMORY": "false",
        "ENABLE_RAG": "false",
        "ENABLE_AGENTIC_RAG": "false",
        "ENABLE_GRAPH_SEARCH": "false",
        # Test-specific settings
        "TESTING": "true",
        "TEST_MODE": "true",
    }

    for var, default_value in test_env_vars.items():
        if not os.getenv(var):
            os.environ[var] = default_value


# Setup test environment
setup_test_environment()

# Configure pytest-asyncio as the default async plugin
pytest_plugins = ["pytest_asyncio"]


# Mark all async tests with asyncio by default
def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as requiring asyncio")


# Configure pytest-asyncio to use module-scoped event loops
@pytest.fixture(scope="module")
def event_loop():
    """
    Create a module-scoped event loop for async tests.

    This ensures all tests in a module share the same event loop,
    avoiding "Event loop is closed" and "Task attached to different loop" errors.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Cleanup: close the loop after all tests in the module
    try:
        loop.close()
    except Exception as e:
        print(f"Warning: Error closing event loop: {e}")


@pytest.fixture(scope="module")
async def connection_manager_module(event_loop):
    """
    Module-scoped connection manager for tests.

    This creates a fresh connection manager for each test module,
    avoiding event loop conflicts between test files.
    """
    # Reset global singleton to ensure clean state
    import src.agentic_rag.storage.connection_manager as cm_module
    from src.agentic_rag.storage.connection_manager import ConnectionManager

    cm_module._connection_manager = None

    # Create and initialize connection manager in the current event loop
    manager = ConnectionManager()
    await manager.initialize()

    yield manager

    # Cleanup: close connections after all tests in the module
    try:
        await manager.close()
    except Exception as e:
        print(f"Warning: Error closing connection manager: {e}")

    # Reset global singleton again
    cm_module._connection_manager = None


@pytest.fixture
async def connection_manager(connection_manager_module):
    """
    Function-scoped connection manager fixture.

    Reuses the module-scoped connection manager but ensures
    it's in a good state for each test.
    """
    # Verify connection manager is in good state
    manager = connection_manager_module

    # Reset circuit breaker state before each test
    from src.agentic_rag.storage.connection_manager import ConnectionState

    manager.pg_state = ConnectionState.OPEN
    manager.neo4j_state = ConnectionState.OPEN
    manager.pg_failures = 0
    manager.neo4j_failures = 0

    yield manager

    # No cleanup needed here - handled by module fixture


@pytest.fixture(scope="session")
def test_database_url():
    """Provide test database URL."""
    return os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agentic_rag_test"
    )


@pytest.fixture
def mock_env_vars():
    """Fixture to provide common environment variable mocks"""
    return {
        "EMBEDDING_BASE_URL": "https://test-api.openai.com/v1",
        "EMBEDDING_API_KEY": "test-api-key",
        "SUPABASE_URL": "https://test-supabase-url.com",
        "SUPABASE_SERVICE_KEY": "test-supabase-key",
        "LLM_PROVIDER": "openai",
        "LLM_API_KEY": "test-llm-api-key",
        "LLM_CHOICE": "gpt-4",
        "EMBEDDING_PROVIDER": "openai",
        "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
        "DATABASE_URL": "postgresql://user:password@localhost:5432/testdb",
    }


@pytest.fixture
def mock_async_openai():
    """Fixture to provide a mock AsyncOpenAI client"""
    return MagicMock()


@pytest.fixture
def mock_supabase_client():
    """Fixture to provide a mock Supabase client"""
    return MagicMock()


@pytest.fixture
def mock_memory():
    """Fixture to provide a mock Memory instance"""
    memory = MagicMock()
    memory.from_config = MagicMock()
    return memory
