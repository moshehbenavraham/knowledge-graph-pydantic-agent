"""
ULTRA Comprehensive tests for embedding generation.

Target coverage: 23% → 95%+

Tests all embedding providers, caching, batching, retry logic,
error handling, statistics, and multi-dimension embeddings.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agentic_rag.ingestion.embedder import (
    EmbeddingCache,
    EmbeddingGenerator,
    MultiDimensionEmbedder,
    generate_embeddings,
)


class TestEmbeddingCache:
    """Test EmbeddingCache LRU cache implementation."""

    def test_cache_init(self):
        """Test cache initialization."""
        cache = EmbeddingCache(max_size=100)

        assert cache.max_size == 100
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0

    def test_cache_get_miss(self):
        """Test getting non-existent item."""
        cache = EmbeddingCache()

        result = cache.get("nonexistent text")

        assert result is None

    def test_cache_set_and_get(self):
        """Test setting and getting item."""
        cache = EmbeddingCache()
        embedding = [0.1, 0.2, 0.3]

        cache.set("test text", embedding)
        result = cache.get("test text")

        assert result == embedding

    def test_cache_lru_eviction(self):
        """Test LRU eviction when max size exceeded."""
        cache = EmbeddingCache(max_size=2)

        cache.set("text1", [0.1])
        cache.set("text2", [0.2])
        cache.set("text3", [0.3])  # Should evict text1

        assert cache.get("text1") is None
        assert cache.get("text2") is not None
        assert cache.get("text3") is not None

    def test_cache_access_updates_order(self):
        """Test that accessing item updates LRU order."""
        cache = EmbeddingCache(max_size=2)

        cache.set("text1", [0.1])
        cache.set("text2", [0.2])
        cache.get("text1")  # Access text1, making it most recent
        cache.set("text3", [0.3])  # Should evict text2, not text1

        assert cache.get("text1") is not None
        assert cache.get("text2") is None
        assert cache.get("text3") is not None

    def test_cache_set_existing_updates_order(self):
        """Test that setting existing item updates order."""
        cache = EmbeddingCache(max_size=2)

        cache.set("text1", [0.1])
        cache.set("text2", [0.2])
        cache.set("text1", [0.1, 0.2])  # Update text1
        cache.set("text3", [0.3])  # Should evict text2

        assert cache.get("text1") is not None
        assert cache.get("text2") is None

    def test_cache_clear(self):
        """Test clearing cache."""
        cache = EmbeddingCache()

        cache.set("text1", [0.1])
        cache.set("text2", [0.2])
        cache.clear()

        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
        assert cache.get("text1") is None

    def test_hash_text(self):
        """Test text hashing."""
        hash1 = EmbeddingCache._hash_text("same text")
        hash2 = EmbeddingCache._hash_text("same text")
        hash3 = EmbeddingCache._hash_text("different text")

        assert hash1 == hash2
        assert hash1 != hash3


class TestEmbeddingGeneratorInit:
    """Test EmbeddingGenerator initialization."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        with patch("src.agentic_rag.ingestion.embedder.get_embedding_config") as mock_config:
            mock_config.return_value = {
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

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        custom_config = {
            "provider": "openai",
            "model": "custom-model",
            "dimension": 768,
            "batch_size": 50,
            "enable_cache": False,
            "max_retries": 5,
            "retry_delay": 2.0,
        }

        generator = EmbeddingGenerator(config=custom_config)

        assert generator.config["model"] == "custom-model"
        assert generator.config["dimension"] == 768
        assert generator.cache is None

    def test_init_stats_tracking(self):
        """Test that stats are initialized."""
        generator = EmbeddingGenerator()

        assert generator._stats["cache_hits"] == 0
        assert generator._stats["cache_misses"] == 0
        assert generator._stats["api_calls"] == 0
        assert generator._stats["total_embeddings"] == 0


class TestClientCreation:
    """Test embedding client creation."""

    def test_client_lazy_loading(self):
        """Test that client is lazy loaded."""
        generator = EmbeddingGenerator()

        assert generator._client is None
        _ = generator.client  # Access property
        assert generator._client is not None

    @patch("src.agentic_rag.ingestion.embedder.openai.AsyncOpenAI")
    @patch("src.agentic_rag.ingestion.embedder.get_config")
    def test_create_openai_client(self, mock_get_config, mock_openai):
        """Test OpenAI client creation."""
        mock_config = MagicMock()
        mock_config.embedding.api_key = "test-key"
        mock_config.embedding.base_url = "https://api.openai.com/v1"
        mock_get_config.return_value = mock_config

        config = {"provider": "openai"}
        generator = EmbeddingGenerator(config=config)

        _ = generator.client

        mock_openai.assert_called_once()

    @patch("src.agentic_rag.ingestion.embedder.openai.AsyncOpenAI")
    @patch("src.agentic_rag.ingestion.embedder.get_config")
    def test_create_ollama_client(self, mock_get_config, mock_openai):
        """Test Ollama client creation."""
        mock_config = MagicMock()
        mock_config.embedding.api_key = None
        mock_config.embedding.base_url = "http://localhost:11434/v1"
        mock_get_config.return_value = mock_config

        config = {"provider": "ollama"}
        generator = EmbeddingGenerator(config=config)

        _ = generator.client

        mock_openai.assert_called_once()

    def test_create_nomic_client_not_implemented(self):
        """Test that Nomic raises NotImplementedError."""
        config = {"provider": "nomic"}
        generator = EmbeddingGenerator(config=config)

        with pytest.raises(NotImplementedError):
            _ = generator.client

    def test_create_unknown_provider(self):
        """Test that unknown provider raises error."""
        config = {"provider": "unknown_provider"}
        generator = EmbeddingGenerator(config=config)

        with pytest.raises(ValueError, match="Unknown embedding provider"):
            _ = generator.client


class TestEmbedMethod:
    """Test single/batch embed methods."""

    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """Test embedding single text."""
        generator = EmbeddingGenerator()

        with patch.object(generator, "embed_batch", return_value=[[0.1, 0.2, 0.3]]) as mock_batch:
            result = await generator.embed("test text")

            mock_batch.assert_called_once_with(["test text"])
            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_list_of_texts(self):
        """Test embedding list of texts."""
        generator = EmbeddingGenerator()

        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        with patch.object(generator, "embed_batch", return_value=embeddings) as mock_batch:
            result = await generator.embed(["text1", "text2"])

            mock_batch.assert_called_once_with(["text1", "text2"])
            assert result == embeddings


class TestEmbedBatch:
    """Test batch embedding."""

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self):
        """Test embedding empty list."""
        generator = EmbeddingGenerator()

        result = await generator.embed_batch([])

        assert result == []

    @pytest.mark.asyncio
    async def test_embed_batch_all_cached(self):
        """Test batch with all items cached."""
        generator = EmbeddingGenerator()
        generator.cache.set("text1", [0.1, 0.2])
        generator.cache.set("text2", [0.3, 0.4])

        result = await generator.embed_batch(["text1", "text2"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        assert generator._stats["cache_hits"] == 2
        assert generator._stats["cache_misses"] == 0

    @pytest.mark.asyncio
    async def test_embed_batch_none_cached(self):
        """Test batch with no items cached."""
        generator = EmbeddingGenerator()

        with patch.object(generator, "_generate_embeddings", return_value=[[0.1, 0.2], [0.3, 0.4]]):
            result = await generator.embed_batch(["text1", "text2"])

            assert len(result) == 2
            assert generator._stats["cache_misses"] == 2

    @pytest.mark.asyncio
    async def test_embed_batch_partial_cached(self):
        """Test batch with some items cached."""
        generator = EmbeddingGenerator()
        generator.cache.set("text1", [0.1, 0.2])

        with patch.object(generator, "_generate_embeddings", return_value=[[0.3, 0.4]]):
            result = await generator.embed_batch(["text1", "text2"])

            assert result[0] == [0.1, 0.2]
            assert result[1] == [0.3, 0.4]
            assert generator._stats["cache_hits"] == 1
            assert generator._stats["cache_misses"] == 1

    @pytest.mark.asyncio
    async def test_embed_batch_caches_new_embeddings(self):
        """Test that new embeddings are cached."""
        generator = EmbeddingGenerator()

        with patch.object(generator, "_generate_embeddings", return_value=[[0.1, 0.2]]):
            await generator.embed_batch(["text1"])

            cached = generator.cache.get("text1")
            assert cached == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_embed_batch_no_cache_mode(self):
        """Test batch embedding without cache."""
        config = {
            "enable_cache": False,
            "provider": "openai",
            "batch_size": 100,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "_generate_embeddings", return_value=[[0.1]]):
            result = await generator.embed_batch(["text1"])

            assert result == [[0.1]]


class TestGenerateEmbeddings:
    """Test embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_embeddings_single_batch(self):
        """Test generating embeddings in single batch."""
        config = {"batch_size": 100, "provider": "openai", "max_retries": 3, "retry_delay": 1.0}
        generator = EmbeddingGenerator(config=config)

        with patch.object(
            generator, "_generate_batch_with_retry", return_value=[[0.1], [0.2]]
        ) as mock_batch:
            result = await generator._generate_embeddings(["text1", "text2"])

            mock_batch.assert_called_once()
            assert result == [[0.1], [0.2]]

    @pytest.mark.asyncio
    async def test_generate_embeddings_multiple_batches(self):
        """Test generating embeddings across multiple batches."""
        config = {"batch_size": 2, "provider": "openai", "max_retries": 3, "retry_delay": 1.0}
        generator = EmbeddingGenerator(config=config)

        side_effects = [[[0.1], [0.2]], [[0.3]]]
        with patch.object(
            generator, "_generate_batch_with_retry", side_effect=side_effects
        ) as mock_batch:
            result = await generator._generate_embeddings(["text1", "text2", "text3"])

            assert mock_batch.call_count == 2
            assert result == [[0.1], [0.2], [0.3]]


class TestGenerateBatchWithRetry:
    """Test batch generation with retry logic."""

    @pytest.mark.asyncio
    async def test_generate_batch_success_first_try(self):
        """Test successful generation on first try."""
        config = {"provider": "openai", "max_retries": 3, "retry_delay": 1.0}
        generator = EmbeddingGenerator(config=config)

        with patch.object(
            generator, "_generate_openai_embeddings", return_value=[[0.1]]
        ) as mock_openai:
            result = await generator._generate_batch_with_retry(["text1"])

            mock_openai.assert_called_once()
            assert result == [[0.1]]

    @pytest.mark.asyncio
    async def test_generate_batch_retry_then_success(self):
        """Test retry logic with eventual success."""
        config = {"provider": "openai", "max_retries": 3, "retry_delay": 0.01}
        generator = EmbeddingGenerator(config=config)

        with patch.object(
            generator,
            "_generate_openai_embeddings",
            side_effect=[Exception("Error"), Exception("Error"), [[0.1]]],
        ) as mock_openai:
            result = await generator._generate_batch_with_retry(["text1"])

            assert mock_openai.call_count == 3
            assert result == [[0.1]]

    @pytest.mark.asyncio
    async def test_generate_batch_all_retries_fail(self):
        """Test all retries fail."""
        config = {"provider": "openai", "max_retries": 3, "retry_delay": 0.01}
        generator = EmbeddingGenerator(config=config)

        with patch.object(
            generator, "_generate_openai_embeddings", side_effect=Exception("Persistent error")
        ):
            with pytest.raises(Exception, match="Persistent error"):
                await generator._generate_batch_with_retry(["text1"])

    @pytest.mark.asyncio
    async def test_generate_batch_exponential_backoff(self):
        """Test exponential backoff between retries."""
        config = {"provider": "openai", "max_retries": 3, "retry_delay": 0.1}
        generator = EmbeddingGenerator(config=config)

        with patch.object(generator, "_generate_openai_embeddings", side_effect=Exception("Error")):
            with patch("asyncio.sleep") as mock_sleep:
                with pytest.raises(Exception):
                    await generator._generate_batch_with_retry(["text1"])

                # Should sleep with exponential backoff: 0.1, 0.2
                assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_batch_unknown_provider(self):
        """Test error with unknown provider."""
        config = {"provider": "unknown", "max_retries": 3, "retry_delay": 1.0}
        generator = EmbeddingGenerator(config=config)

        with pytest.raises(NotImplementedError):
            await generator._generate_batch_with_retry(["text1"])


class TestGenerateOpenAIEmbeddings:
    """Test OpenAI embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_openai_embeddings(self):
        """Test OpenAI embedding generation."""
        generator = EmbeddingGenerator()

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_data1 = MagicMock()
        mock_data1.embedding = [0.1, 0.2, 0.3]
        mock_data2 = MagicMock()
        mock_data2.embedding = [0.4, 0.5, 0.6]
        mock_response.data = [mock_data1, mock_data2]
        mock_client.embeddings.create.return_value = mock_response

        generator._client = mock_client

        result = await generator._generate_openai_embeddings(["text1", "text2"])

        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        assert generator._stats["api_calls"] == 1


class TestEmbedChunks:
    """Test embedding document chunks."""

    @pytest.mark.asyncio
    async def test_embed_chunks(self):
        """Test embedding document chunks."""
        generator = EmbeddingGenerator()

        # Create mock chunks
        chunk1 = MagicMock()
        chunk1.content = "content 1"
        chunk2 = MagicMock()
        chunk2.content = "content 2"

        with patch.object(generator, "embed_batch", return_value=[[0.1], [0.2]]):
            result = await generator.embed_chunks([chunk1, chunk2])

            assert chunk1.embedding == [0.1]
            assert chunk2.embedding == [0.2]
            assert result == [chunk1, chunk2]

    @pytest.mark.asyncio
    async def test_embed_chunks_empty_list(self):
        """Test embedding empty chunk list."""
        generator = EmbeddingGenerator()

        result = await generator.embed_chunks([])

        assert result == []


class TestStatistics:
    """Test statistics tracking."""

    def test_get_stats_initial(self):
        """Test getting initial statistics."""
        generator = EmbeddingGenerator()

        stats = generator.get_stats()

        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["api_calls"] == 0
        assert stats["total_embeddings"] == 0
        assert stats["cache_hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_stats_after_operations(self):
        """Test statistics after operations."""
        generator = EmbeddingGenerator()

        # Cache some embeddings
        generator.cache.set("text1", [0.1])
        generator.cache.set("text2", [0.2])

        # Perform operations
        with patch.object(generator, "_generate_embeddings", return_value=[[0.3]]):
            await generator.embed_batch(["text1", "text2", "text3"])

        stats = generator.get_stats()

        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        assert stats["total_embeddings"] == 3
        assert stats["cache_hit_rate"] == 2 / 3

    def test_clear_cache(self):
        """Test clearing cache."""
        generator = EmbeddingGenerator()
        generator.cache.set("text1", [0.1])

        generator.clear_cache()

        assert generator.cache.get("text1") is None


class TestMultiDimensionEmbedder:
    """Test MultiDimensionEmbedder."""

    @patch("src.agentic_rag.ingestion.embedder.get_config")
    def test_multi_dimension_init(self, mock_get_config):
        """Test initialization."""
        mock_config = MagicMock()
        mock_config.embedding.provider = "openai"
        mock_config.embedding.model = "text-embedding-3-small"
        mock_config.embedding.dimension = 1536
        mock_config.embedding.batch_size = 100
        mock_config.performance.enable_caching = True
        mock_get_config.return_value = mock_config

        embedder = MultiDimensionEmbedder()

        assert embedder.primary_embedder is not None
        assert embedder.secondary_embedder is None

    @pytest.mark.asyncio
    @patch("src.agentic_rag.ingestion.embedder.get_config")
    async def test_embed_multi_primary_only(self, mock_get_config):
        """Test multi-dimension embedding with primary only."""
        mock_config = MagicMock()
        mock_config.embedding.provider = "openai"
        mock_config.embedding.model = "test-model"
        mock_config.embedding.dimension = 1536
        mock_config.embedding.batch_size = 100
        mock_config.performance.enable_caching = True
        mock_get_config.return_value = mock_config

        embedder = MultiDimensionEmbedder()

        with patch.object(embedder.primary_embedder, "embed", return_value=[0.1, 0.2, 0.3]):
            result = await embedder.embed_multi("test text")

            assert "embedding_1536" in result
            assert result["embedding_1536"] == [0.1, 0.2, 0.3]
            assert result["embedding_768"] is None


class TestBackwardCompatibility:
    """Test backward compatibility functions."""

    @pytest.mark.asyncio
    async def test_generate_embeddings_with_generator(self):
        """Test generate_embeddings with EmbeddingGenerator."""
        generator = EmbeddingGenerator()

        with patch.object(generator, "embed_batch", return_value=[[0.1]]):
            result = await generate_embeddings(["text1"], generator)

            assert result == [[0.1]]

    @pytest.mark.asyncio
    async def test_generate_embeddings_with_client(self):
        """Test generate_embeddings with generic client."""
        mock_client = MagicMock()
        mock_client.embed_batch = AsyncMock(return_value=[[0.1]])

        with patch("src.agentic_rag.ingestion.embedder.EmbeddingGenerator") as mock_gen_class:
            mock_gen = MagicMock()
            mock_gen.embed_batch = AsyncMock(return_value=[[0.1]])
            mock_gen_class.return_value = mock_gen

            result = await generate_embeddings(["text1"], mock_client)

            assert result == [[0.1]]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
