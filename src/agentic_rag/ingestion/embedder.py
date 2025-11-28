"""
Embedding generation with caching and batch processing.

Supports multiple embedding models and provides efficient batch processing
with automatic retry logic and caching.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from typing import Any, cast

import openai
import structlog

from src.agentic_rag.config import get_config

logger = logging.getLogger(__name__)
structlog_logger = structlog.get_logger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""

    provider: str = "openai"
    model: str = "text-embedding-3-small"
    dimension: int = 1536
    batch_size: int = 100
    enable_cache: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0


def get_embedding_config() -> dict[str, Any]:
    """Get embedding configuration from global settings."""
    structlog_logger.info("get_embedding_config called")
    config = get_config().embedding
    perf_config = get_config().performance

    result = {
        "provider": config.provider,
        "model": config.model,
        "dimension": config.dimension,
        "batch_size": config.batch_size,
        "enable_cache": perf_config.enable_caching,
        "max_retries": 3,
        "retry_delay": 1.0,
    }

    structlog_logger.info(
        "get_embedding_config completed",
        provider=result["provider"],
        model=result["model"],
        dimension=result["dimension"],
    )
    return result


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""

    def __init__(self, max_size: int = 1000):
        """
        Initialize embedding cache.

        Args:
            max_size: Maximum number of cached embeddings
        """
        structlog_logger.info("EmbeddingCache initializing", max_size=max_size)
        self.max_size = max_size
        self._cache: dict[str, list[float]] = {}
        self._access_order: list[str] = []
        structlog_logger.info("EmbeddingCache initialized")

    def get(self, text: str) -> list[float] | None:
        """
        Get embedding from cache.

        Args:
            text: Text to get embedding for

        Returns:
            Cached embedding or None
        """
        key = self._hash_text(text)
        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            structlog_logger.debug("EmbeddingCache.get - cache hit", text_preview=text[:50])
            return self._cache[key]
        structlog_logger.debug("EmbeddingCache.get - cache miss", text_preview=text[:50])
        return None

    def set(self, text: str, embedding: list[float]) -> None:
        """
        Store embedding in cache.

        Args:
            text: Text that was embedded
            embedding: Embedding vector
        """
        key = self._hash_text(text)

        # Check if already in cache
        if key in self._cache:
            self._access_order.remove(key)
        elif len(self._cache) >= self.max_size:
            # Evict least recently used
            lru_key = self._access_order.pop(0)
            del self._cache[lru_key]
            structlog_logger.debug("EmbeddingCache.set - evicted LRU entry")

        self._cache[key] = embedding
        self._access_order.append(key)
        structlog_logger.debug("EmbeddingCache.set - cached embedding", cache_size=len(self._cache))

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._access_order.clear()

    @staticmethod
    def _hash_text(text: str) -> str:
        """
        Generate hash key for text.

        Args:
            text: Text to hash

        Returns:
            Hash string
        """
        return hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()


class EmbeddingGenerator:
    """
    Multi-model embedding generation with caching and batch processing.

    Supports OpenAI, Nomic, Ollama, and other providers with automatic
    fallback and retry logic.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize embedding generator.

        Args:
            config: Embedding configuration dictionary or EmbeddingConfig object
        """
        structlog_logger.info("EmbeddingGenerator initializing")
        self.config = config or get_embedding_config()
        self.cache = EmbeddingCache() if self._get_config_value("enable_cache", True) else None
        self._client: openai.AsyncOpenAI | None = None
        self._stats: dict[str, Any] = {
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls": 0,
            "total_embeddings": 0,
        }
        structlog_logger.info(
            "EmbeddingGenerator initialized",
            provider=self._get_config_value("provider"),
            model=self._get_config_value("model"),
            cache_enabled=self.cache is not None,
        )

    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """Get config value supporting both dict and dataclass."""
        if isinstance(self.config, dict):
            return self.config.get(key, default)
        return getattr(self.config, key, default)

    @property
    def client(self) -> openai.AsyncOpenAI:
        """Lazy load embedding client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> openai.AsyncOpenAI:
        """Create embedding client based on provider."""
        structlog_logger.info("_create_client called", provider=self._get_config_value("provider"))
        config = get_config()

        if self._get_config_value("provider") == "openai":
            structlog_logger.info("_create_client - creating OpenAI client")
            return openai.AsyncOpenAI(
                api_key=config.embedding.api_key, base_url=config.embedding.base_url
            )

        if self._get_config_value("provider") == "ollama":
            # Ollama uses OpenAI-compatible API
            # Default Ollama base URL is http://localhost:11434/v1
            base_url = config.embedding.base_url or "http://localhost:11434/v1"
            # Ollama doesn't require a real API key
            api_key = config.embedding.api_key or "ollama"
            structlog_logger.info("_create_client - creating Ollama client", base_url=base_url)
            return openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

        if self._get_config_value("provider") == "nomic":
            # Nomic implementation
            raise NotImplementedError("Nomic provider not yet implemented")

        raise ValueError(f"Unknown embedding provider: {self._get_config_value('provider')}")

    async def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """
        Generate embeddings for text.

        Args:
            text: Single text or list of texts to embed

        Returns:
            Single embedding or list of embeddings
        """
        if isinstance(text, str):
            is_single = True
            texts: list[str] = [text]
        else:
            is_single = False
            texts = text

        structlog_logger.info("embed called", num_texts=len(texts), is_single=is_single)

        embeddings = await self.embed_batch(texts)

        structlog_logger.info("embed completed", num_embeddings=len(embeddings))
        return embeddings[0] if is_single else embeddings

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        structlog_logger.info("embed_batch called", num_texts=len(texts))

        if not texts:
            structlog_logger.info("embed_batch - empty texts, returning empty list")
            return []

        embeddings = []
        uncached_texts = []
        uncached_indices = []

        # Check cache first
        for i, text in enumerate(texts):
            if self.cache:
                cached = self.cache.get(text)
                if cached:
                    embeddings.append(cached)
                    self._stats["cache_hits"] += 1
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
                    self._stats["cache_misses"] += 1
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        structlog_logger.info(
            "embed_batch - cache check complete",
            cache_hits=len(embeddings),
            cache_misses=len(uncached_texts),
        )

        # Generate embeddings for uncached texts
        if uncached_texts:
            new_embeddings = await self._generate_embeddings(uncached_texts)

            # Cache new embeddings
            if self.cache:
                for text, embedding in zip(uncached_texts, new_embeddings, strict=False):
                    self.cache.set(text, embedding)

            # Merge with cached embeddings in correct order
            if self.cache and embeddings:
                result: list[list[float] | None] = [None] * len(texts)
                cached_idx = 0
                uncached_idx = 0

                for i in range(len(texts)):
                    if i in uncached_indices:
                        result[i] = new_embeddings[uncached_idx]
                        uncached_idx += 1
                    else:
                        result[i] = embeddings[cached_idx]
                        cached_idx += 1

                # Filter out any None values (should not happen, but for type safety)
                embeddings = [e for e in result if e is not None]
            else:
                embeddings = new_embeddings

        self._stats["total_embeddings"] += len(texts)

        structlog_logger.info("embed_batch completed", num_embeddings=len(embeddings))
        return embeddings

    async def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using the configured provider.

        Args:
            texts: Texts to embed

        Returns:
            List of embeddings
        """
        structlog_logger.info("_generate_embeddings called", num_texts=len(texts))

        embeddings = []

        # Process in batches
        batch_size = self._get_config_value("batch_size")
        num_batches = (len(texts) + batch_size - 1) // batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_num = i // batch_size + 1
            structlog_logger.info(
                "_generate_embeddings - processing batch",
                batch_num=batch_num,
                total_batches=num_batches,
                batch_size=len(batch),
            )
            batch_embeddings = await self._generate_batch_with_retry(batch)
            embeddings.extend(batch_embeddings)

        structlog_logger.info("_generate_embeddings completed", num_embeddings=len(embeddings))
        return embeddings

    async def _generate_batch_with_retry(self, batch: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch with retry logic.

        Args:
            batch: Batch of texts

        Returns:
            List of embeddings
        """
        structlog_logger.info("_generate_batch_with_retry called", batch_size=len(batch))

        for attempt in range(self._get_config_value("max_retries")):
            try:
                if self._get_config_value("provider") == "openai":
                    result = await self._generate_openai_embeddings(batch)
                    structlog_logger.info(
                        "_generate_batch_with_retry completed", attempt=attempt + 1
                    )
                    return result
                raise NotImplementedError(
                    f"Provider {self._get_config_value('provider')} not implemented"
                )

            except Exception as e:
                logger.warning(f"Embedding generation attempt {attempt + 1} failed: {e}")
                structlog_logger.warning(
                    "_generate_batch_with_retry - attempt failed",
                    attempt=attempt + 1,
                    error=str(e),
                )

                if attempt < self._get_config_value("max_retries") - 1:
                    await asyncio.sleep(self._get_config_value("retry_delay") * (2**attempt))
                else:
                    raise

        return []

    async def _generate_openai_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using OpenAI API.

        Args:
            texts: Texts to embed

        Returns:
            List of embeddings
        """
        structlog_logger.info(
            "_generate_openai_embeddings called",
            num_texts=len(texts),
            model=self._get_config_value("model"),
        )

        self._stats["api_calls"] += 1

        response = await self.client.embeddings.create(
            model=self._get_config_value("model"), input=texts
        )

        result = [data.embedding for data in response.data]
        structlog_logger.info("_generate_openai_embeddings completed", num_embeddings=len(result))
        return result

    async def embed_chunks(self, chunks: list[Any]) -> list[Any]:
        """
        Embed document chunks in place.

        Args:
            chunks: List of DocumentChunk objects

        Returns:
            Chunks with embeddings added
        """
        structlog_logger.info("embed_chunks called", num_chunks=len(chunks))

        # Extract texts
        texts = [chunk.content for chunk in chunks]

        # Generate embeddings
        embeddings = await self.embed_batch(texts)

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            chunk.embedding = embedding

        structlog_logger.info("embed_chunks completed", num_chunks_embedded=len(chunks))
        return chunks

    def get_stats(self) -> dict[str, Any]:
        """
        Get embedding generation statistics.

        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()

        if self._stats["cache_hits"] + self._stats["cache_misses"] > 0:
            stats["cache_hit_rate"] = self._stats["cache_hits"] / (
                self._stats["cache_hits"] + self._stats["cache_misses"]
            )
        else:
            stats["cache_hit_rate"] = 0.0

        return stats

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Embedding cache cleared")


class MultiDimensionEmbedder:
    """
    Generate embeddings in multiple dimensions for flexibility.

    Supports generating both 1536-dim and 768-dim embeddings
    for different use cases.
    """

    def __init__(self) -> None:
        """Initialize multi-dimension embedder."""
        structlog_logger.info("MultiDimensionEmbedder initializing")
        config = get_config()

        # Primary embedder (1536-dim)
        self.primary_config = {
            "provider": config.embedding.provider,
            "model": config.embedding.model,
            "dimension": 1536,
            "batch_size": config.embedding.batch_size,
            "enable_cache": config.performance.enable_caching,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        self.primary_embedder = EmbeddingGenerator(self.primary_config)

        # Secondary embedder (768-dim) if needed
        self.secondary_embedder = None
        if config.embedding.dimension == 768:
            self.secondary_config = {
                "provider": "nomic",
                "model": "nomic-embed-text",
                "dimension": 768,
                "batch_size": config.embedding.batch_size,
                "enable_cache": config.performance.enable_caching,
                "max_retries": 3,
                "retry_delay": 1.0,
            }
            # Only initialize if Nomic is available
            try:
                self.secondary_embedder = EmbeddingGenerator(self.secondary_config)
                structlog_logger.info("MultiDimensionEmbedder - secondary embedder initialized")
            except Exception:
                logger.info("Secondary embedder (768-dim) not available")
                structlog_logger.info("MultiDimensionEmbedder - secondary embedder not available")

        structlog_logger.info("MultiDimensionEmbedder initialized")

    async def embed_multi(
        self, text: str | list[str]
    ) -> dict[str, list[float] | list[list[float]] | None]:
        """
        Generate embeddings in multiple dimensions.

        Args:
            text: Text(s) to embed

        Returns:
            Dictionary with embeddings of different dimensions
        """
        is_single = isinstance(text, str)
        num_texts = 1 if is_single else len(text)
        structlog_logger.info("embed_multi called", num_texts=num_texts)

        result: dict[str, list[float] | list[list[float]] | None] = {}

        # Primary embedding
        result["embedding_1536"] = await self.primary_embedder.embed(text)

        # Secondary embedding if available
        if self.secondary_embedder:
            try:
                result["embedding_768"] = await self.secondary_embedder.embed(text)
            except Exception as e:
                logger.warning(f"Secondary embedding failed: {e}")
                structlog_logger.warning("embed_multi - secondary embedding failed", error=str(e))
                result["embedding_768"] = None
        else:
            result["embedding_768"] = None

        structlog_logger.info("embed_multi completed")
        return result


async def generate_embeddings(texts: list[str], client: Any) -> list[list[float]]:
    """
    Simple wrapper function for generating embeddings (for backward compatibility).

    Args:
        texts: List of texts to embed
        client: OpenAI client (or any embedding client)

    Returns:
        List of embedding vectors
    """
    structlog_logger.info("generate_embeddings called", num_texts=len(texts))

    # Use the client if it's already an EmbeddingGenerator
    if hasattr(client, "embed_batch"):
        result = await client.embed_batch(texts)
        structlog_logger.info("generate_embeddings completed", num_embeddings=len(result))
        return cast("list[list[float]]", result)

    # Otherwise, create a new generator with default config
    generator = EmbeddingGenerator()
    result = await generator.embed_batch(texts)
    structlog_logger.info("generate_embeddings completed", num_embeddings=len(result))
    return result
