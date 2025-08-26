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
