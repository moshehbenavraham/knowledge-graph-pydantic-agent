# Import the functions to test
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).parent.parent.resolve() / "src"))
from clients.database import get_supabase_client
from clients.llm import get_llm_client
from clients.memory import get_mem0_client


class TestGetLlmClient:
    @patch("clients.llm.AsyncOpenAI")
    @patch("clients.llm.os.getenv")
    def test_get_llm_client(self, mock_getenv, mock_async_openai):
        # Configure mock environment variables
        def getenv_side_effect(key, default=None):
            env_vars = {
                "LLM_BASE_URL": "https://test-api.openai.com/v1",
                "LLM_API_KEY": "test-api-key",
            }
            return env_vars.get(key, default)

        mock_getenv.side_effect = getenv_side_effect

        # Create mock instances
        mock_embedding_client = MagicMock()

        # Configure mocks to return our mock instances
        mock_async_openai.return_value = mock_embedding_client

        # Call the function
        embedding_client = get_llm_client()

        # Assert the function returns the expected values
        assert embedding_client == mock_embedding_client

        # Assert AsyncOpenAI was called with the correct parameters
        mock_async_openai.assert_called_once_with(
            base_url="https://test-api.openai.com/v1", api_key="test-api-key"
        )


class TestGetSupabaseClient:
    @patch("clients.database.create_client")
    @patch("clients.database.os.getenv")
    def test_get_supabase_client(self, mock_getenv, mock_create_client):
        # Configure mock environment variables
        def getenv_side_effect(key, default=None):
            env_vars = {
                "SUPABASE_URL": "https://test-supabase-url.com",
                "SUPABASE_SERVICE_KEY": "test-supabase-key",
            }
            return env_vars.get(key, default)

        mock_getenv.side_effect = getenv_side_effect

        # Create mock instances
        mock_supabase_client = MagicMock()

        # Configure mocks to return our mock instances
        mock_create_client.return_value = mock_supabase_client

        # Call the function
        supabase = get_supabase_client()

        # Assert the function returns the expected values
        assert supabase == mock_supabase_client

        # Assert create_client was called with the correct parameters
        mock_create_client.assert_called_once_with(
            "https://test-supabase-url.com", "test-supabase-key"
        )


class TestGetMem0Client:
    @patch("clients.memory.Memory")
    @patch("clients.memory.os")
    def test_get_mem0_client_with_openai(self, mock_os, mock_memory):
        # Configure mock environment variables
        mock_os.getenv.side_effect = lambda key, default=None: {
            "LLM_PROVIDER": "openai",
            "LLM_API_KEY": "test-llm-api-key",
            "LLM_CHOICE": "gpt-4",
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_API_KEY": "test-embedding-api-key",
            "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
            "DATABASE_URL": "postgresql://user:password@localhost:5432/testdb",
        }.get(key, default)

        # Mock environment dictionary with MagicMock
        mock_os.environ = MagicMock()
        mock_os.environ.get.return_value = ""

        # Create mock Memory instance
        mock_memory_instance = MagicMock()
        mock_memory.from_config.return_value = mock_memory_instance

        # Call the function
        result = get_mem0_client()

        # Assert the function returns the expected Memory instance
        assert result == mock_memory_instance

        # Assert Memory.from_config was called with the correct configuration
        expected_config = {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4",
                    "temperature": 0.2,
                    "max_tokens": 2000,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {"model": "text-embedding-3-small", "embedding_dims": 1536},
            },
            "vector_store": {
                "provider": "supabase",
                "config": {
                    "connection_string": "",
                    "collection_name": "mem0_memories",
                    "embedding_model_dims": 1536,
                },
            },
        }

        # Check that Memory.from_config was called with the expected config
        mock_memory.from_config.assert_called_once()
        actual_config = mock_memory.from_config.call_args[0][0]
        assert actual_config == expected_config

        # Assert environment variables were set correctly
        mock_os.environ.__setitem__.assert_any_call("OPENAI_API_KEY", "test-llm-api-key")

    @patch("clients.memory.Memory")
    @patch("clients.memory.os")
    def test_get_mem0_client_with_ollama(self, mock_os, mock_memory):
        # Configure mock environment variables
        mock_os.getenv.side_effect = lambda key, default=None: {
            "LLM_PROVIDER": "ollama",
            "LLM_API_KEY": "",
            "LLM_CHOICE": "llama3",
            "LLM_BASE_URL": "http://localhost:11434/v1",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_API_KEY": "",
            "EMBEDDING_MODEL_CHOICE": "nomic-embed-text",
            "EMBEDDING_BASE_URL": "http://localhost:11434/v1",
            "DATABASE_URL": "postgresql://user:password@localhost:5432/testdb",
        }.get(key, default)

        # Mock environment dictionary with MagicMock
        mock_os.environ = MagicMock()
        mock_os.environ.get.return_value = ""

        # Create mock Memory instance
        mock_memory_instance = MagicMock()
        mock_memory.from_config.return_value = mock_memory_instance

        # Call the function
        result = get_mem0_client()

        # Assert the function returns the expected Memory instance
        assert result == mock_memory_instance

        # Assert Memory.from_config was called with the correct configuration
        expected_config = {
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": "llama3",
                    "temperature": 0.2,
                    "max_tokens": 2000,
                    "ollama_base_url": "http://localhost:11434",
                },
            },
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": "nomic-embed-text",
                    "embedding_dims": 768,
                    "ollama_base_url": "http://localhost:11434",
                },
            },
            "vector_store": {
                "provider": "supabase",
                "config": {
                    "connection_string": "",
                    "collection_name": "mem0_memories",
                    "embedding_model_dims": 768,
                },
            },
        }

        # Check that Memory.from_config was called with the expected config
        mock_memory.from_config.assert_called_once()
        actual_config = mock_memory.from_config.call_args[0][0]
        assert actual_config == expected_config

    @patch("clients.memory.Memory")
    @patch("clients.memory.os")
    def test_get_mem0_client_with_openrouter(self, mock_os, mock_memory):
        # Configure mock environment variables
        mock_os.getenv.side_effect = lambda key, default=None: {
            "LLM_PROVIDER": "openrouter",
            "LLM_API_KEY": "test-openrouter-key",
            "LLM_CHOICE": "anthropic/claude-3-opus",
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_API_KEY": "test-embedding-api-key",
            "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
            "DATABASE_URL": "postgresql://user:password@localhost:5432/testdb",
        }.get(key, default)

        # Mock environment dictionary with MagicMock
        mock_os.environ = MagicMock()
        mock_os.environ.get.return_value = ""

        # Create mock Memory instance
        mock_memory_instance = MagicMock()
        mock_memory.from_config.return_value = mock_memory_instance

        # Call the function
        result = get_mem0_client()

        # Assert the function returns the expected Memory instance
        assert result == mock_memory_instance

        # Assert Memory.from_config was called with the correct configuration
        expected_config = {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "anthropic/claude-3-opus",
                    "temperature": 0.2,
                    "max_tokens": 2000,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {"model": "text-embedding-3-small", "embedding_dims": 1536},
            },
            "vector_store": {
                "provider": "supabase",
                "config": {
                    "connection_string": "",
                    "collection_name": "mem0_memories",
                    "embedding_model_dims": 1536,
                },
            },
        }

        # Check that Memory.from_config was called with the expected config
        mock_memory.from_config.assert_called_once()
        actual_config = mock_memory.from_config.call_args[0][0]
        assert actual_config == expected_config

        # Assert environment variables were set correctly
        mock_os.environ.__setitem__.assert_any_call("OPENAI_API_KEY", "test-embedding-api-key")
        mock_os.environ.__setitem__.assert_any_call("OPENROUTER_API_KEY", "test-openrouter-key")
