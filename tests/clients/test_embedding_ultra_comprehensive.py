"""Ultra comprehensive tests for embedding.py (target: 90%+ coverage)."""

from unittest.mock import patch


class TestGetEmbeddingClient:
    """Test get_embedding_client() function."""

    def test_get_embedding_client_success(self):
        from src.clients.embedding import get_embedding_client

        with patch("src.clients.embedding.clients_config") as mock_config:
            mock_config.embedding_provider.value = "openai"
            mock_config.embedding_model = "text-embedding-3-small"
            mock_config.embedding_base_url = "https://api.openai.com/v1"
            mock_config.embedding_api_key = "test-key"

            with patch("src.clients.embedding.AsyncOpenAI") as MockAsyncOpenAI:
                result = get_embedding_client()

                MockAsyncOpenAI.assert_called_once_with(
                    base_url="https://api.openai.com/v1", api_key="test-key"
                )
                assert result is not None

    def test_get_embedding_client_ollama(self):
        from src.clients.embedding import get_embedding_client

        with patch("src.clients.embedding.clients_config") as mock_config:
            mock_config.embedding_provider.value = "ollama"
            mock_config.embedding_model = "nomic-embed-text"
            mock_config.embedding_base_url = "http://localhost:11434/v1"
            mock_config.embedding_api_key = "ollama"

            with patch("src.clients.embedding.AsyncOpenAI") as MockAsyncOpenAI:
                result = get_embedding_client()

                MockAsyncOpenAI.assert_called_once_with(
                    base_url="http://localhost:11434/v1", api_key="ollama"
                )
                assert result is not None

    def test_get_embedding_client_custom_provider(self):
        from src.clients.embedding import get_embedding_client

        with patch("src.clients.embedding.clients_config") as mock_config:
            mock_config.embedding_provider.value = "custom"
            mock_config.embedding_model = "custom-model"
            mock_config.embedding_base_url = "https://custom.api/v1"
            mock_config.embedding_api_key = "custom-key"

            with patch("src.clients.embedding.AsyncOpenAI") as MockAsyncOpenAI:
                result = get_embedding_client()

                MockAsyncOpenAI.assert_called_once()
                assert result is not None

    def test_get_embedding_client_logs_info(self):
        from src.clients.embedding import get_embedding_client

        with patch("src.clients.embedding.clients_config") as mock_config:
            mock_config.embedding_provider.value = "openai"
            mock_config.embedding_model = "text-embedding-3-small"
            mock_config.embedding_base_url = "https://api.openai.com/v1"
            mock_config.embedding_api_key = "test-key"

            with patch("src.clients.embedding.AsyncOpenAI"):
                with patch("src.clients.embedding.logger") as mock_logger:
                    get_embedding_client()

                    mock_logger.info.assert_called_once()
                    call_args = mock_logger.info.call_args
                    assert "Creating embedding client" in call_args[0]

    def test_get_embedding_client_different_base_urls(self):
        from src.clients.embedding import get_embedding_client

        test_cases = [
            ("https://api.openai.com/v1", "openai-key"),
            ("http://localhost:11434/v1", "ollama"),
            ("https://api.custom.com/embeddings", "custom-key"),
        ]

        for base_url, api_key in test_cases:
            with patch("src.clients.embedding.clients_config") as mock_config:
                mock_config.embedding_provider.value = "test"
                mock_config.embedding_model = "test-model"
                mock_config.embedding_base_url = base_url
                mock_config.embedding_api_key = api_key

                with patch("src.clients.embedding.AsyncOpenAI") as MockAsyncOpenAI:
                    result = get_embedding_client()

                    MockAsyncOpenAI.assert_called_once_with(base_url=base_url, api_key=api_key)
                    assert result is not None
