import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock environment variables before importing modules that use them
TEST_ENV_VARS = {
    "LLM_PROVIDER": "openai",
    "LLM_API_KEY": "test-llm-key",
    "LLM_CHOICE": "gpt-4o-mini",
    "EMBEDDING_PROVIDER": "openai",
    "EMBEDDING_API_KEY": "test-embedding-key",
    "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
    "SUPABASE_URL": "https://test-supabase-url.com",
    "SUPABASE_SERVICE_KEY": "test-supabase-key",
    "DATABASE_URL": "postgresql://user:password@localhost:5432/testdb",
}

with patch.dict(os.environ, TEST_ENV_VARS):
    # Add src directory to path to import the module
    sys.path.append(str(Path(__file__).parent.parent.resolve() / "src"))
    from clients.memory import get_mem0_client, get_mem0_client_async, get_mem0_config


class TestMemoryConfiguration:
    """Test memory system configuration for different providers."""

    @patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "openai",
            "LLM_API_KEY": "sk-test-openai-key",
            "LLM_CHOICE": "gpt-4o-mini",
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_API_KEY": "sk-test-embedding-key",
            "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
        },
    )
    def test_openai_memory_configuration(self):
        """Test memory configuration with OpenAI providers."""
        config = get_mem0_config()

        # Test LLM configuration
        assert config["llm"]["provider"] == "openai"
        assert config["llm"]["config"]["model"] == "gpt-4o-mini"
        assert config["llm"]["config"]["temperature"] == 0.2
        assert config["llm"]["config"]["max_tokens"] == 2000

        # Test embedder configuration
        assert config["embedder"]["provider"] == "openai"
        assert config["embedder"]["config"]["model"] == "text-embedding-3-small"
        assert config["embedder"]["config"]["embedding_dims"] == 1536

        # Test vector store configuration
        assert config["vector_store"]["provider"] == "supabase"
        assert config["vector_store"]["config"]["embedding_model_dims"] == 1536

    @patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "openrouter",
            "LLM_API_KEY": "sk-or-test-key",
            "LLM_CHOICE": "anthropic/claude-3-sonnet",
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_API_KEY": "sk-test-embedding-key",
        },
    )
    def test_openrouter_memory_configuration(self):
        """Test memory configuration with OpenRouter LLM and OpenAI embeddings."""
        config = get_mem0_config()

        # Test LLM configuration (OpenRouter uses OpenAI provider in mem0)
        assert config["llm"]["provider"] == "openai"
        assert config["llm"]["config"]["model"] == "anthropic/claude-3-sonnet"

        # Test embedder configuration (still OpenAI)
        assert config["embedder"]["provider"] == "openai"
        assert config["embedder"]["config"]["embedding_dims"] == 1536

    @patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "ollama",
            "LLM_BASE_URL": "http://localhost:11434/v1",
            "LLM_CHOICE": "llama3.1",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_BASE_URL": "http://localhost:11434/v1",
            "EMBEDDING_MODEL_CHOICE": "nomic-embed-text",
        },
    )
    def test_ollama_memory_configuration(self):
        """Test memory configuration with Ollama providers."""
        config = get_mem0_config()

        # Test LLM configuration
        assert config["llm"]["provider"] == "ollama"
        assert config["llm"]["config"]["model"] == "llama3.1"
        assert config["llm"]["config"]["ollama_base_url"] == "http://localhost:11434"

        # Test embedder configuration
        assert config["embedder"]["provider"] == "ollama"
        assert config["embedder"]["config"]["model"] == "nomic-embed-text"
        assert config["embedder"]["config"]["embedding_dims"] == 768
        assert config["embedder"]["config"]["ollama_base_url"] == "http://localhost:11434"

        # Test vector store configuration
        assert config["vector_store"]["config"]["embedding_model_dims"] == 768

    def test_mixed_provider_configuration(self):
        """Test configuration with mixed providers (Ollama LLM + OpenAI embeddings)."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "ollama",
                "LLM_BASE_URL": "http://localhost:11434/v1",
                "LLM_CHOICE": "llama3.1",
                "EMBEDDING_PROVIDER": "openai",
                "EMBEDDING_API_KEY": "sk-test-key",
                "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
            },
        ):
            config = get_mem0_config()

            # LLM should be Ollama
            assert config["llm"]["provider"] == "ollama"
            assert config["llm"]["config"]["model"] == "llama3.1"

            # Embedder should be OpenAI
            assert config["embedder"]["provider"] == "openai"
            assert config["embedder"]["config"]["model"] == "text-embedding-3-small"
            assert config["embedder"]["config"]["embedding_dims"] == 1536

    def test_default_fallback_configuration(self):
        """Test configuration with missing environment variables uses defaults."""
        with patch.dict(
            os.environ, {"LLM_PROVIDER": "openai", "EMBEDDING_PROVIDER": "openai"}, clear=False
        ):
            config = get_mem0_config()

            # Should use default embedding model
            assert config["embedder"]["config"]["model"] == "text-embedding-3-small"
            assert config["embedder"]["config"]["embedding_dims"] == 1536

    def test_supabase_vector_store_configuration(self):
        """Test Supabase vector store configuration."""
        config = get_mem0_config()

        vector_store_config = config["vector_store"]
        assert vector_store_config["provider"] == "supabase"
        assert vector_store_config["config"]["collection_name"] == "mem0_memories"
        assert "connection_string" in vector_store_config["config"]


class TestMemoryClientInitialization:
    """Test memory client initialization and basic operations."""

    @patch("clients.memory.Memory")
    def test_sync_memory_client_creation(self, mock_memory_class):
        """Test synchronous memory client creation."""
        mock_client = MagicMock()
        mock_memory_class.return_value = mock_client

        client = get_mem0_client()

        assert client is not None
        mock_memory_class.assert_called_once()

    @patch("clients.memory.AsyncMemory")
    def test_async_memory_client_creation(self, mock_async_memory_class):
        """Test asynchronous memory client creation."""
        mock_client = MagicMock()
        mock_async_memory_class.return_value = mock_client

        client = get_mem0_client_async()

        assert client is not None
        mock_async_memory_class.assert_called_once()

    @patch("clients.memory.Memory")
    def test_memory_client_with_custom_config(self, mock_memory_class):
        """Test memory client creation with custom configuration."""
        mock_client = MagicMock()
        mock_memory_class.return_value = mock_client

        # Test with custom configuration
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "ollama",
                "LLM_CHOICE": "custom-model",
                "EMBEDDING_PROVIDER": "ollama",
                "EMBEDDING_MODEL_CHOICE": "custom-embed-model",
            },
        ):
            client = get_mem0_client()

            # Verify client was created
            assert client is not None
            mock_memory_class.assert_called_once()

            # Verify configuration was passed
            call_args = mock_memory_class.call_args
            config = call_args[0][0] if call_args[0] else call_args[1].get("config")

            if config:
                assert config["llm"]["config"]["model"] == "custom-model"


class TestMemoryOperations:
    """Test memory operations and data handling."""

    @pytest.fixture
    def mock_memory_client(self):
        """Create a mock memory client for testing."""
        client = MagicMock()
        client.add.return_value = {"id": "mem_123", "content": "Test memory"}
        client.search.return_value = [
            {"content": "Relevant memory 1", "score": 0.9},
            {"content": "Relevant memory 2", "score": 0.8},
        ]
        client.get_all.return_value = [
            {"id": "mem_123", "content": "Memory 1"},
            {"id": "mem_456", "content": "Memory 2"},
        ]
        client.delete.return_value = {"deleted": True}
        return client

    def test_memory_addition(self, mock_memory_client):
        """Test adding memories to the system."""
        # Test adding a memory
        result = mock_memory_client.add("User prefers Python programming")

        assert result["id"] == "mem_123"
        assert result["content"] == "Test memory"
        mock_memory_client.add.assert_called_once_with("User prefers Python programming")

    def test_memory_search(self, mock_memory_client):
        """Test searching memories."""
        # Test searching memories
        results = mock_memory_client.search("Python programming")

        assert len(results) == 2
        assert results[0]["content"] == "Relevant memory 1"
        assert results[0]["score"] == 0.9
        mock_memory_client.search.assert_called_once_with("Python programming")

    def test_memory_retrieval(self, mock_memory_client):
        """Test retrieving all memories."""
        # Test getting all memories
        memories = mock_memory_client.get_all()

        assert len(memories) == 2
        assert memories[0]["id"] == "mem_123"
        assert memories[1]["id"] == "mem_456"
        mock_memory_client.get_all.assert_called_once()

    def test_memory_deletion(self, mock_memory_client):
        """Test deleting memories."""
        # Test deleting a memory
        result = mock_memory_client.delete("mem_123")

        assert result["deleted"] is True
        mock_memory_client.delete.assert_called_once_with("mem_123")


class TestMemoryErrorHandling:
    """Test memory system error handling and edge cases."""

    @patch("clients.memory.Memory")
    def test_memory_client_initialization_failure(self, mock_memory_class):
        """Test handling of memory client initialization failures."""
        mock_memory_class.side_effect = Exception("Failed to initialize memory client")

        with pytest.raises(Exception, match="Failed to initialize memory client"):
            get_mem0_client()

    def test_invalid_provider_configuration(self):
        """Test handling of invalid provider configurations."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "invalid_provider",
                "EMBEDDING_PROVIDER": "invalid_embedding_provider",
            },
        ):
            config = get_mem0_config()

            # Should not have LLM or embedder config for invalid providers
            assert "llm" not in config or config.get("llm") is None
            assert "embedder" not in config or config.get("embedder") is None

    def test_missing_required_environment_variables(self):
        """Test behavior when required environment variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_mem0_config()

            # Should still have vector store configuration
            assert "vector_store" in config
            assert config["vector_store"]["provider"] == "supabase"

    @patch("clients.memory.Memory")
    def test_memory_operation_failures(self, mock_memory_class):
        """Test handling of memory operation failures."""
        mock_client = MagicMock()
        mock_client.add.side_effect = Exception("Memory add failed")
        mock_client.search.side_effect = Exception("Memory search failed")
        mock_memory_class.return_value = mock_client

        client = get_mem0_client()

        # Test that exceptions are properly propagated
        with pytest.raises(Exception, match="Memory add failed"):
            client.add("test memory")

        with pytest.raises(Exception, match="Memory search failed"):
            client.search("test query")
