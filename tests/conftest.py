import os
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv

# Load test environment variables
load_dotenv(".env.test")


# Set required environment variables for tests if not already set
def setup_test_environment():
    """Ensure all required environment variables are set for testing."""
    required_vars = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_key_for_testing_only",
        "SUPABASE_SERVICE_KEY": "test_service_key_for_testing_only",
        "OPENAI_API_KEY": "test_openai_key",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test",
    }

    for var, default_value in required_vars.items():
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
