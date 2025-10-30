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
    @patch("clients.llm.clients_config")
    def test_get_llm_client(self, mock_clients_config, mock_async_openai):
        # Configure mock clients_config
        mock_llm_provider = MagicMock()
        mock_llm_provider.value = "openai"
        mock_clients_config.llm_provider = mock_llm_provider
        mock_clients_config.llm_base_url = "https://test-api.openai.com/v1"
        mock_clients_config.llm_api_key = "test-api-key"
        mock_clients_config.llm_model = "gpt-4"

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
    @patch("clients.database.clients_config")
    def test_get_supabase_client(self, mock_clients_config, mock_create_client):
        # Configure mock clients_config
        mock_clients_config.supabase_url = "https://test-supabase-url.com"
        mock_clients_config.supabase_service_key = "test-supabase-key"

        # Create mock instances
        mock_supabase_client = MagicMock()

        # Configure mocks to return our mock instances
        mock_create_client.return_value = mock_supabase_client

        # Call the function
        supabase = get_supabase_client()

        # Assert the function returns the expected values
        assert supabase == mock_supabase_client

        # Assert create_client was called with the correct parameters (now includes ClientOptions)
        call_args = mock_create_client.call_args
        assert call_args[0][0] == "https://test-supabase-url.com"
        assert call_args[0][1] == "test-supabase-key"
        # ClientOptions passed as keyword argument
        assert "options" in call_args[1]


class TestGetMem0Client:
    @patch("clients.memory.Memory")
    @patch("clients.memory.get_mem0_config")
    def test_get_mem0_client_with_openai(self, mock_get_config, mock_memory):
        # Mock the config that get_mem0_config returns
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
        mock_get_config.return_value = expected_config

        # Create mock Memory instance
        mock_memory_instance = MagicMock()
        mock_memory.from_config.return_value = mock_memory_instance

        # Call the function
        result = get_mem0_client()

        # Assert the function returns the expected Memory instance
        assert result == mock_memory_instance

        # Assert Memory.from_config was called with the expected config
        mock_memory.from_config.assert_called_once_with(expected_config)

    @patch("clients.memory.Memory")
    @patch("clients.memory.get_mem0_config")
    def test_get_mem0_client_with_ollama(self, mock_get_config, mock_memory):
        # Mock the config that get_mem0_config returns
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
        mock_get_config.return_value = expected_config

        # Create mock Memory instance
        mock_memory_instance = MagicMock()
        mock_memory.from_config.return_value = mock_memory_instance

        # Call the function
        result = get_mem0_client()

        # Assert the function returns the expected Memory instance
        assert result == mock_memory_instance

        # Assert Memory.from_config was called with the expected config
        mock_memory.from_config.assert_called_once_with(expected_config)

    @patch("clients.memory.Memory")
    @patch("clients.memory.get_mem0_config")
    def test_get_mem0_client_with_openrouter(self, mock_get_config, mock_memory):
        # Mock the config that get_mem0_config returns
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
        mock_get_config.return_value = expected_config

        # Create mock Memory instance
        mock_memory_instance = MagicMock()
        mock_memory.from_config.return_value = mock_memory_instance

        # Call the function
        result = get_mem0_client()

        # Assert the function returns the expected Memory instance
        assert result == mock_memory_instance

        # Assert Memory.from_config was called with the expected config
        mock_memory.from_config.assert_called_once_with(expected_config)
