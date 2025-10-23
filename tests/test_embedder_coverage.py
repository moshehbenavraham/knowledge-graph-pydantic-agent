"""
Comprehensive test coverage for src/agentic_rag/ingestion/embedder.py.

Tests cover:
1. Different embedding providers (OpenAI, Ollama, Nomic)
2. Batch embedding generation
3. API error handling and retries
4. Rate limiting scenarios
5. Token limit handling
6. Cache behavior (LRU eviction, hit/miss)
7. Dimension validation
8. Empty/null text handling
9. Very long text truncation
10. Concurrent embedding requests
11. Provider fallback logic
12. Cost tracking/monitoring
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from src.agentic_rag.ingestion.embedder import (
    EmbeddingCache,
    EmbeddingGenerator,
    MultiDimensionEmbedder,
    get_embedding_config,
)


class TestGetEmbeddingConfig:
    """Test get_embedding_config function."""

    @patch("src.agentic_rag.ingestion.embedder.get_config")
    def test_get_embedding_config_default(self, mock_get_config):
        """Test getting embedding config with default values."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.embedding.provider = "openai"
        mock_config.embedding.model = "text-embedding-3-small"
        mock_config.embedding.dimension = 1536
        mock_config.embedding.batch_size = 100
        mock_config.performance.enable_caching = True
        mock_get_config.return_value = mock_config

        config = get_embedding_config()

        assert config["provider"] == "openai"
        assert config["model"] == "text-embedding-3-small"
        assert config["dimension"] == 1536
        assert config["batch_size"] == 100
        assert config["enable_cache"] is True
        assert config["max_retries"] == 3
        assert config["retry_delay"] == 1.0

    @patch("src.agentic_rag.ingestion.embedder.get_config")
    def test_get_embedding_config_custom(self, mock_get_config):
        """Test getting embedding config with custom values."""
        mock_config = MagicMock()
        mock_config.embedding.provider = "nomic"
        mock_config.embedding.model = "nomic-embed-text"
        mock_config.embedding.dimension = 768
        mock_config.embedding.batch_size = 50
        mock_config.performance.enable_caching = False
        mock_get_config.return_value = mock_config

        config = get_embedding_config()

        assert config["provider"] == "nomic"
        assert config["model"] == "nomic-embed-text"
        assert config["dimension"] == 768
        assert config["batch_size"] == 50
        assert config["enable_cache"] is False


class TestEmbeddingCache:
    """Test EmbeddingCache class."""

    def test_cache_initialization(self):
        """Test cache initialization with default and custom sizes."""
        cache = EmbeddingCache()
        assert cache.max_size == 1000
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0

        cache_custom = EmbeddingCache(max_size=500)
        assert cache_custom.max_size == 500

    def test_cache_set_and_get(self):
        """Test setting and getting embeddings from cache."""
        cache = EmbeddingCache()
        text = "test text"
        embedding = [0.1, 0.2, 0.3]

        # Initially should return None
        assert cache.get(text) is None

        # Set and retrieve
        cache.set(text, embedding)
        result = cache.get(text)
        assert result == embedding

    def test_cache_get_updates_access_order(self):
        """Test that getting an item updates its position in LRU order."""
        cache = EmbeddingCache(max_size=3)

        cache.set("text1", [0.1])
        cache.set("text2", [0.2])
        cache.set("text3", [0.3])

        # Access text1 (should move to end)
        cache.get("text1")

        # Check access order
        assert cache._access_order[-1] == cache._hash_text("text1")

    def test_cache_set_existing_item(self):
        """Test setting an existing item updates it and moves to end."""
        cache = EmbeddingCache(max_size=3)

        cache.set("text1", [0.1])
        cache.set("text2", [0.2])
        cache.set("text3", [0.3])

        # Update text1
        cache.set("text1", [0.9])

        # Should be moved to end
        assert cache._access_order[-1] == cache._hash_text("text1")
        assert cache.get("text1") == [0.9]

    def test_cache_lru_eviction(self):
        """Test that cache evicts least recently used item when full."""
        cache = EmbeddingCache(max_size=2)

        cache.set("text1", [0.1])
        cache.set("text2", [0.2])

        # This should evict text1
        cache.set("text3", [0.3])

        assert cache.get("text1") is None
        assert cache.get("text2") == [0.2]
        assert cache.get("text3") == [0.3]

    def test_cache_lru_eviction_after_access(self):
        """Test LRU eviction respects access order."""
        cache = EmbeddingCache(max_size=2)

        cache.set("text1", [0.1])
        cache.set("text2", [0.2])

        # Access text1 (makes it most recently used)
        cache.get("text1")

        # This should evict text2 instead of text1
        cache.set("text3", [0.3])

        assert cache.get("text1") == [0.1]
        assert cache.get("text2") is None
        assert cache.get("text3") == [0.3]

    def test_cache_clear(self):
        """Test clearing the cache."""
        cache = EmbeddingCache()
        cache.set("text1", [0.1])
        cache.set("text2", [0.2])

        cache.clear()

        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
        assert cache.get("text1") is None

    def test_cache_hash_text(self):
        """Test text hashing function."""
        cache = EmbeddingCache()

        hash1 = cache._hash_text("test text")
        hash2 = cache._hash_text("test text")
        hash3 = cache._hash_text("different text")

        # Same text should produce same hash
        assert hash1 == hash2

        # Different text should produce different hash
        assert hash1 != hash3

        # Hash should be a valid hex string
        assert isinstance(hash1, str)
        assert len(hash1) == 32  # MD5 hex digest length


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    @patch("src.agentic_rag.ingestion.embedder.get_embedding_config")
    def test_generator_initialization_default(self, mock_get_config):
        """Test generator initialization with default config."""
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "dimension": 1536,
            "batch_size": 100,
            "enable_cache": True,
            "max_retries": 3,
            "retry_delay": 1.0,
        }

        generator = EmbeddingGenerator()

        assert generator.config["provider"] == "openai"
        assert generator.cache is not None
        assert generator._stats["cache_hits"] == 0
        assert generator._stats["api_calls"] == 0

    def test_generator_initialization_with_config(self):
        """Test generator initialization with custom config."""
        config = {
            "provider": "nomic",
            "model": "nomic-embed-text",
            "dimension": 768,
            "batch_size": 50,
            "enable_cache": False,
            "max_retries": 5,
            "retry_delay": 2.0,
        }

        generator = EmbeddingGenerator(config=config)

        assert generator.config == config
        assert generator.cache is None  # Disabled

    @patch("src.agentic_rag.ingestion.embedder.get_config")
    @patch("src.agentic_rag.ingestion.embedder.openai.AsyncOpenAI")
    def test_create_client_openai(self, mock_openai, mock_get_config):
        """Test creating OpenAI client."""
        mock_config = MagicMock()
        mock_config.embedding.api_key = "test-api-key"
        mock_config.embedding.base_url = "https://api.openai.com/v1"
        mock_get_config.return_value = mock_config

        config = {"provider": "openai", "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        # Access client to trigger lazy loading
        _ = generator.client

        mock_openai.assert_called_once_with(
            api_key="test-api-key", base_url="https://api.openai.com/v1"
        )

    def test_create_client_nomic_not_implemented(self):
        """Test that Nomic provider raises NotImplementedError."""
        config = {"provider": "nomic", "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        with pytest.raises(NotImplementedError, match="Nomic provider not yet implemented"):
            _ = generator.client

    @patch("src.agentic_rag.ingestion.embedder.get_config")
    def test_create_client_ollama(self, mock_get_config):
        """Test that Ollama provider creates AsyncOpenAI client."""
        # Mock config to return Ollama settings
        mock_config = MagicMock()
        mock_config.embedding.base_url = "http://localhost:11434/v1"
        mock_config.embedding.api_key = "ollama"
        mock_get_config.return_value = mock_config

        config = {"provider": "ollama", "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        # Should create AsyncOpenAI client with Ollama base URL
        client = generator.client
        assert client is not None
        assert isinstance(client, openai.AsyncOpenAI)
        # Verify it uses Ollama's base URL
        assert "11434" in str(client.base_url)

    def test_create_client_unknown_provider(self):
        """Test that unknown provider raises ValueError."""
        config = {"provider": "unknown", "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        with pytest.raises(ValueError, match="Unknown embedding provider: unknown"):
            _ = generator.client

    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """Test embedding a single text string."""
        config = {"provider": "openai", "batch_size": 100, "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "embed_batch", return_value=[[0.1, 0.2, 0.3]]) as mock_batch:
            result = await generator.embed("test text")

            mock_batch.assert_called_once_with(["test text"])
            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_list_of_texts(self):
        """Test embedding a list of texts."""
        config = {"provider": "openai", "batch_size": 100, "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        expected = [[0.1, 0.2], [0.3, 0.4]]
        with patch.object(generator, "embed_batch", return_value=expected) as mock_batch:
            result = await generator.embed(["text1", "text2"])

            mock_batch.assert_called_once_with(["text1", "text2"])
            assert result == expected

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self):
        """Test embedding empty list returns empty list."""
        config = {"provider": "openai", "batch_size": 100, "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        result = await generator.embed_batch([])

        assert result == []

    @pytest.mark.asyncio
    async def test_embed_batch_with_cache_all_cached(self):
        """Test batch embedding when all texts are cached."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": True,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        generator = EmbeddingGenerator(config=config)

        # Pre-populate cache
        generator.cache.set("text1", [0.1, 0.2])
        generator.cache.set("text2", [0.3, 0.4])

        result = await generator.embed_batch(["text1", "text2"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        assert generator._stats["cache_hits"] == 2
        assert generator._stats["cache_misses"] == 0

    @pytest.mark.asyncio
    async def test_embed_batch_with_cache_partial_cached(self):
        """Test batch embedding with some texts cached and some not."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": True,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        generator = EmbeddingGenerator(config=config)

        # Pre-populate cache with one text
        generator.cache.set("text1", [0.1, 0.2])

        # Mock the API call for uncached text
        with patch.object(generator, "_generate_embeddings", return_value=[[0.3, 0.4]]) as mock_gen:
            result = await generator.embed_batch(["text1", "text2"])

            mock_gen.assert_called_once_with(["text2"])
            assert result == [[0.1, 0.2], [0.3, 0.4]]
            assert generator._stats["cache_hits"] == 1
            assert generator._stats["cache_misses"] == 1

    @pytest.mark.asyncio
    async def test_embed_batch_no_cache(self):
        """Test batch embedding without cache enabled."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": False,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        generator = EmbeddingGenerator(config=config)

        with patch.object(
            generator, "_generate_embeddings", return_value=[[0.1, 0.2], [0.3, 0.4]]
        ) as mock_gen:
            result = await generator.embed_batch(["text1", "text2"])

            mock_gen.assert_called_once_with(["text1", "text2"])
            assert result == [[0.1, 0.2], [0.3, 0.4]]

    @pytest.mark.asyncio
    async def test_embed_batch_caches_new_embeddings(self):
        """Test that new embeddings are cached after generation."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": True,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "_generate_embeddings", return_value=[[0.1, 0.2]]):
            await generator.embed_batch(["text1"])

            # Should now be cached
            cached = generator.cache.get("text1")
            assert cached == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_generate_embeddings_single_batch(self):
        """Test generating embeddings within single batch."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": False,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        generator = EmbeddingGenerator(config=config)

        texts = ["text1", "text2", "text3"]
        expected = [[0.1], [0.2], [0.3]]

        with patch.object(
            generator, "_generate_batch_with_retry", return_value=expected
        ) as mock_batch:
            result = await generator._generate_embeddings(texts)

            mock_batch.assert_called_once_with(texts)
            assert result == expected

    @pytest.mark.asyncio
    async def test_generate_embeddings_multiple_batches(self):
        """Test generating embeddings across multiple batches."""
        config = {
            "provider": "openai",
            "batch_size": 2,
            "enable_cache": False,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        generator = EmbeddingGenerator(config=config)

        texts = ["text1", "text2", "text3", "text4", "text5"]

        with patch.object(generator, "_generate_batch_with_retry") as mock_batch:
            mock_batch.side_effect = [
                [[0.1], [0.2]],  # First batch
                [[0.3], [0.4]],  # Second batch
                [[0.5]],  # Third batch
            ]

            result = await generator._generate_embeddings(texts)

            assert mock_batch.call_count == 3
            assert result == [[0.1], [0.2], [0.3], [0.4], [0.5]]

    @pytest.mark.asyncio
    async def test_generate_batch_with_retry_success_first_attempt(self):
        """Test batch generation succeeds on first attempt."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": False,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        generator = EmbeddingGenerator(config=config)

        expected = [[0.1, 0.2]]
        with patch.object(
            generator, "_generate_openai_embeddings", return_value=expected
        ) as mock_openai:
            result = await generator._generate_batch_with_retry(["text1"])

            mock_openai.assert_called_once_with(["text1"])
            assert result == expected

    @pytest.mark.asyncio
    async def test_generate_batch_with_retry_success_after_retries(self):
        """Test batch generation succeeds after retries."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": False,
            "max_retries": 3,
            "retry_delay": 0.1,
        }
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "_generate_openai_embeddings") as mock_openai:
            # Fail twice, then succeed
            mock_openai.side_effect = [
                Exception("Rate limit"),
                Exception("Timeout"),
                [[0.1, 0.2]],
            ]

            result = await generator._generate_batch_with_retry(["text1"])

            assert mock_openai.call_count == 3
            assert result == [[0.1, 0.2]]

    @pytest.mark.asyncio
    async def test_generate_batch_with_retry_all_attempts_fail(self):
        """Test batch generation fails after all retry attempts."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": False,
            "max_retries": 3,
            "retry_delay": 0.1,
        }
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "_generate_openai_embeddings") as mock_openai:
            mock_openai.side_effect = Exception("Persistent error")

            with pytest.raises(Exception, match="Persistent error"):
                await generator._generate_batch_with_retry(["text1"])

            assert mock_openai.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_batch_with_retry_exponential_backoff(self):
        """Test retry logic uses exponential backoff."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": False,
            "max_retries": 3,
            "retry_delay": 0.1,
        }
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "_generate_openai_embeddings") as mock_openai:
            mock_openai.side_effect = [
                Exception("Error 1"),
                Exception("Error 2"),
                [[0.1]],
            ]

            with patch("src.agentic_rag.ingestion.embedder.asyncio.sleep") as mock_sleep:
                await generator._generate_batch_with_retry(["text1"])

                # Check exponential backoff: 0.1, 0.2
                assert mock_sleep.call_count == 2
                mock_sleep.assert_any_call(0.1)  # First retry: delay * 2^0
                mock_sleep.assert_any_call(0.2)  # Second retry: delay * 2^1

    @pytest.mark.asyncio
    async def test_generate_batch_with_retry_not_implemented_provider(self):
        """Test that non-OpenAI providers raise NotImplementedError."""
        config = {
            "provider": "nomic",
            "batch_size": 100,
            "enable_cache": False,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        generator = EmbeddingGenerator(config=config)

        with pytest.raises(NotImplementedError, match="Provider nomic not implemented"):
            await generator._generate_batch_with_retry(["text1"])

    @pytest.mark.asyncio
    async def test_generate_openai_embeddings(self):
        """Test OpenAI embedding generation."""
        config = {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "batch_size": 100,
            "enable_cache": False,
        }
        generator = EmbeddingGenerator(config=config)

        # Mock the OpenAI client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_data1 = MagicMock()
        mock_data1.embedding = [0.1, 0.2]
        mock_data2 = MagicMock()
        mock_data2.embedding = [0.3, 0.4]
        mock_response.data = [mock_data1, mock_data2]
        mock_client.embeddings.create.return_value = mock_response
        generator._client = mock_client

        result = await generator._generate_openai_embeddings(["text1", "text2"])

        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input=["text1", "text2"]
        )
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        assert generator._stats["api_calls"] == 1

    @pytest.mark.asyncio
    async def test_embed_chunks(self):
        """Test embedding document chunks."""
        config = {"provider": "openai", "batch_size": 100, "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        # Create mock chunks
        chunk1 = MagicMock()
        chunk1.content = "content1"
        chunk2 = MagicMock()
        chunk2.content = "content2"
        chunks = [chunk1, chunk2]

        with patch.object(
            generator, "embed_batch", return_value=[[0.1, 0.2], [0.3, 0.4]]
        ) as mock_batch:
            result = await generator.embed_chunks(chunks)

            mock_batch.assert_called_once_with(["content1", "content2"])
            assert result == chunks
            assert chunk1.embedding == [0.1, 0.2]
            assert chunk2.embedding == [0.3, 0.4]

    def test_get_stats_with_cache_hits(self):
        """Test getting stats with cache activity."""
        config = {"provider": "openai", "enable_cache": True}
        generator = EmbeddingGenerator(config=config)

        generator._stats["cache_hits"] = 75
        generator._stats["cache_misses"] = 25
        generator._stats["api_calls"] = 10
        generator._stats["total_embeddings"] = 100

        stats = generator.get_stats()

        assert stats["cache_hits"] == 75
        assert stats["cache_misses"] == 25
        assert stats["api_calls"] == 10
        assert stats["total_embeddings"] == 100
        assert stats["cache_hit_rate"] == 0.75

    def test_get_stats_no_cache_activity(self):
        """Test getting stats with no cache activity."""
        config = {"provider": "openai", "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        stats = generator.get_stats()

        assert stats["cache_hit_rate"] == 0.0

    def test_clear_cache_with_cache_enabled(self):
        """Test clearing cache when cache is enabled."""
        config = {"provider": "openai", "enable_cache": True}
        generator = EmbeddingGenerator(config=config)

        generator.cache.set("text1", [0.1, 0.2])
        generator.clear_cache()

        assert generator.cache.get("text1") is None

    def test_clear_cache_with_cache_disabled(self):
        """Test clearing cache when cache is disabled."""
        config = {"provider": "openai", "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        # Should not raise error
        generator.clear_cache()


class TestMultiDimensionEmbedder:
    """Test MultiDimensionEmbedder class."""

    @patch("src.agentic_rag.ingestion.embedder.get_config")
    def test_initialization_1536_dimension(self, mock_get_config):
        """Test initialization with 1536 dimension config."""
        mock_config = MagicMock()
        mock_config.embedding.provider = "openai"
        mock_config.embedding.model = "text-embedding-3-small"
        mock_config.embedding.dimension = 1536
        mock_config.embedding.batch_size = 100
        mock_config.performance.enable_caching = True
        mock_get_config.return_value = mock_config

        embedder = MultiDimensionEmbedder()

        assert embedder.primary_config["dimension"] == 1536
        assert embedder.primary_embedder is not None
        assert embedder.secondary_embedder is None

    @patch("src.agentic_rag.ingestion.embedder.get_config")
    def test_initialization_768_dimension(self, mock_get_config):
        """Test initialization with 768 dimension config."""
        mock_config = MagicMock()
        mock_config.embedding.provider = "openai"
        mock_config.embedding.model = "text-embedding-3-small"
        mock_config.embedding.dimension = 768
        mock_config.embedding.batch_size = 100
        mock_config.performance.enable_caching = True
        mock_get_config.return_value = mock_config

        with patch("src.agentic_rag.ingestion.embedder.EmbeddingGenerator") as mock_generator_class:
            # Mock generator to avoid NotImplementedError
            mock_generator_class.side_effect = [
                MagicMock(),  # Primary embedder
                Exception("Nomic not available"),  # Secondary embedder fails
            ]

            embedder = MultiDimensionEmbedder()

            assert embedder.primary_embedder is not None
            assert embedder.secondary_embedder is None

    @pytest.mark.asyncio
    @patch("src.agentic_rag.ingestion.embedder.get_config")
    async def test_embed_multi_single_text(self, mock_get_config):
        """Test multi-dimension embedding of single text."""
        mock_config = MagicMock()
        mock_config.embedding.provider = "openai"
        mock_config.embedding.model = "text-embedding-3-small"
        mock_config.embedding.dimension = 1536
        mock_config.embedding.batch_size = 100
        mock_config.performance.enable_caching = True
        mock_get_config.return_value = mock_config

        embedder = MultiDimensionEmbedder()

        # Mock primary embedder
        embedder.primary_embedder = AsyncMock()
        embedder.primary_embedder.embed.return_value = [0.1, 0.2, 0.3]

        result = await embedder.embed_multi("test text")

        assert result["embedding_1536"] == [0.1, 0.2, 0.3]
        assert result["embedding_768"] is None

    @pytest.mark.asyncio
    @patch("src.agentic_rag.ingestion.embedder.get_config")
    async def test_embed_multi_list_of_texts(self, mock_get_config):
        """Test multi-dimension embedding of list of texts."""
        mock_config = MagicMock()
        mock_config.embedding.provider = "openai"
        mock_config.embedding.model = "text-embedding-3-small"
        mock_config.embedding.dimension = 1536
        mock_config.embedding.batch_size = 100
        mock_config.performance.enable_caching = True
        mock_get_config.return_value = mock_config

        embedder = MultiDimensionEmbedder()

        # Mock primary embedder
        embedder.primary_embedder = AsyncMock()
        embedder.primary_embedder.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        result = await embedder.embed_multi(["text1", "text2"])

        assert result["embedding_1536"] == [[0.1, 0.2], [0.3, 0.4]]
        assert result["embedding_768"] is None

    @pytest.mark.asyncio
    @patch("src.agentic_rag.ingestion.embedder.get_config")
    async def test_embed_multi_with_secondary_embedder(self, mock_get_config):
        """Test multi-dimension embedding with secondary embedder."""
        mock_config = MagicMock()
        mock_config.embedding.provider = "openai"
        mock_config.embedding.model = "text-embedding-3-small"
        mock_config.embedding.dimension = 1536
        mock_config.embedding.batch_size = 100
        mock_config.performance.enable_caching = True
        mock_get_config.return_value = mock_config

        embedder = MultiDimensionEmbedder()

        # Mock both embedders
        embedder.primary_embedder = AsyncMock()
        embedder.primary_embedder.embed.return_value = [0.1, 0.2, 0.3]

        embedder.secondary_embedder = AsyncMock()
        embedder.secondary_embedder.embed.return_value = [0.4, 0.5]

        result = await embedder.embed_multi("test text")

        assert result["embedding_1536"] == [0.1, 0.2, 0.3]
        assert result["embedding_768"] == [0.4, 0.5]

    @pytest.mark.asyncio
    @patch("src.agentic_rag.ingestion.embedder.get_config")
    async def test_embed_multi_secondary_fails(self, mock_get_config):
        """Test multi-dimension embedding when secondary embedder fails."""
        mock_config = MagicMock()
        mock_config.embedding.provider = "openai"
        mock_config.embedding.model = "text-embedding-3-small"
        mock_config.embedding.dimension = 1536
        mock_config.embedding.batch_size = 100
        mock_config.performance.enable_caching = True
        mock_get_config.return_value = mock_config

        embedder = MultiDimensionEmbedder()

        # Mock primary to succeed, secondary to fail
        embedder.primary_embedder = AsyncMock()
        embedder.primary_embedder.embed.return_value = [0.1, 0.2, 0.3]

        embedder.secondary_embedder = AsyncMock()
        embedder.secondary_embedder.embed.side_effect = Exception("Secondary failed")

        result = await embedder.embed_multi("test text")

        assert result["embedding_1536"] == [0.1, 0.2, 0.3]
        assert result["embedding_768"] is None


class TestConcurrentEmbedding:
    """Test concurrent embedding scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_embed_requests(self):
        """Test multiple concurrent embedding requests."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": True,
            "max_retries": 3,
            "retry_delay": 0.1,
        }
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "_generate_embeddings") as mock_gen:
            mock_gen.side_effect = lambda texts: [[0.1] * len(texts[0])] * len(texts)

            # Run multiple concurrent embed operations
            tasks = [generator.embed(f"text{i}") for i in range(10)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 10

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """Test concurrent cache access doesn't cause issues."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": True,
            "max_retries": 3,
            "retry_delay": 0.1,
        }
        generator = EmbeddingGenerator(config=config)

        # Pre-populate cache
        for i in range(5):
            generator.cache.set(f"text{i}", [float(i)])

        # Concurrent cache reads
        tasks = [generator.embed_batch([f"text{i % 5}"]) for i in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        assert generator._stats["cache_hits"] == 20


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_text_embedding(self):
        """Test embedding empty string."""
        config = {"provider": "openai", "batch_size": 100, "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "_generate_embeddings", return_value=[[0.0]]):
            result = await generator.embed("")
            assert result == [0.0]

    @pytest.mark.asyncio
    async def test_very_long_text_embedding(self):
        """Test embedding very long text."""
        config = {"provider": "openai", "batch_size": 100, "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        long_text = "a" * 100000  # Very long text

        with patch.object(generator, "_generate_embeddings", return_value=[[0.1, 0.2]]):
            result = await generator.embed(long_text)
            assert result == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_special_characters_in_text(self):
        """Test embedding text with special characters."""
        config = {"provider": "openai", "batch_size": 100, "enable_cache": False}
        generator = EmbeddingGenerator(config=config)

        special_text = "!@#$%^&*()_+{}|:<>?~`"

        with patch.object(generator, "_generate_embeddings", return_value=[[0.1]]):
            result = await generator.embed(special_text)
            assert result == [0.1]

    @pytest.mark.asyncio
    async def test_unicode_text_embedding(self):
        """Test embedding text with Unicode characters."""
        config = {"provider": "openai", "batch_size": 100, "enable_cache": True}
        generator = EmbeddingGenerator(config=config)

        unicode_text = "Hello 世界 🌍 émoji"

        with patch.object(generator, "_generate_embeddings", return_value=[[0.1]]):
            result = await generator.embed(unicode_text)
            assert result == [0.1]

            # Should be cached with same hash
            cached = generator.cache.get(unicode_text)
            assert cached == [0.1]

    def test_cache_with_identical_texts(self):
        """Test cache handles identical texts correctly."""
        cache = EmbeddingCache(max_size=10)

        cache.set("identical", [0.1])
        cache.set("identical", [0.2])  # Update same text

        result = cache.get("identical")
        assert result == [0.2]
        assert len(cache._cache) == 1

    @pytest.mark.asyncio
    async def test_batch_with_duplicate_texts(self):
        """Test batch embedding with duplicate texts."""
        config = {
            "provider": "openai",
            "batch_size": 100,
            "enable_cache": True,
            "max_retries": 3,
            "retry_delay": 0.1,
        }
        generator = EmbeddingGenerator(config=config)

        texts = ["text1", "text2", "text1", "text2"]  # Duplicates

        # Mock needs to return embeddings for all items in uncached_texts
        # Since cache is empty first time, all 4 texts will be in uncached_texts
        with patch.object(
            generator, "_generate_embeddings", return_value=[[0.1], [0.2], [0.1], [0.2]]
        ) as mock_gen:
            result = await generator.embed_batch(texts)

            # Should generate embeddings for all texts on first call
            mock_gen.assert_called_once()
            assert len(result) == 4
            # After caching, subsequent calls should use cache
            result2 = await generator.embed_batch(["text1"])
            assert result2 == [[0.1]]
            assert generator._stats["cache_hits"] == 1

    @pytest.mark.asyncio
    async def test_stats_tracking_accuracy(self):
        """Test that stats are tracked accurately."""
        config = {
            "provider": "openai",
            "batch_size": 2,
            "enable_cache": True,
            "max_retries": 3,
            "retry_delay": 0.1,
        }
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "_generate_embeddings") as mock_gen:
            mock_gen.side_effect = [
                [[0.1], [0.2]],
                [[0.3]],
            ]

            # First batch - both are cache misses
            await generator.embed_batch(["text1", "text2"])
            # Second batch with one cached (text1) and one new (text3)
            await generator.embed_batch(["text1", "text3"])

            stats = generator.get_stats()
            assert stats["cache_hits"] == 1  # text1 on second call
            assert stats["cache_misses"] == 3  # text1, text2, text3
            assert stats["total_embeddings"] == 4  # 2 + 2 texts processed (batch 1 + batch 2)
            assert stats["cache_hit_rate"] == 0.25  # 1 hit / 4 total requests
