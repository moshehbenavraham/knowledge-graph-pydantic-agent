"""
Vector similarity search using pgvector.

High-performance vector search with caching and metadata filtering.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from src.agentic_rag.config import get_config
from src.agentic_rag.ingestion.embedder import EmbeddingGenerator
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.agentic_rag.storage.postgres_store import PostgresStore

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    """Result from vector search."""

    chunk_id: UUID
    content: str
    similarity: float
    document_id: UUID
    document_title: str
    document_source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Get the score (alias for similarity)."""
        return self.similarity

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": str(self.chunk_id),
            "content": self.content,
            "similarity": self.similarity,
            "document_id": str(self.document_id),
            "document_title": self.document_title,
            "document_source": self.document_source,
            "metadata": self.metadata,
            "entities": self.entities,
        }


class SearchCache:
    """Simple TTL cache for search results."""

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize search cache.

        Args:
            ttl_seconds: Time to live in seconds
        """
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: dict[str, tuple[datetime, list[ChunkResult]]] = {}

    def get(self, key: str) -> list[ChunkResult] | None:
        """
        Get cached results.

        Args:
            key: Cache key

        Returns:
            Cached results or None
        """
        if key in self._cache:
            timestamp, results = self._cache[key]
            if datetime.now() - timestamp < self.ttl:
                return results
            del self._cache[key]
        return None

    def set(self, key: str, results: list[ChunkResult]):
        """
        Cache results.

        Args:
            key: Cache key
            results: Results to cache
        """
        self._cache[key] = (datetime.now(), results)

    def clear(self):
        """Clear the cache."""
        self._cache.clear()

    @staticmethod
    def generate_key(query_embedding: list[float], filters: dict | None = None) -> str:
        """
        Generate cache key from query and filters.

        Args:
            query_embedding: Query embedding vector
            filters: Search filters

        Returns:
            Cache key
        """
        # Create a string representation
        key_parts = [
            str(query_embedding[:10]),  # Use first 10 dimensions
            json.dumps(filters or {}, sort_keys=True),
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()


class VectorSearch:
    """
    High-performance vector similarity search using pgvector.

    Performance targets:
    - <200ms for 10k chunks
    - <100ms with caching
    """

    def __init__(self, connection_manager: ConnectionManager | None = None):
        """
        Initialize vector search.

        Args:
            connection_manager: Database connection manager
        """
        self.config = get_config()
        self.connection_manager = connection_manager or ConnectionManager()
        self.pg_store = PostgresStore(self.connection_manager)
        self.embedder = EmbeddingGenerator()

        # Initialize cache if enabled
        if self.config.performance.enable_caching:
            self.cache = SearchCache(ttl_seconds=self.config.performance.embedding_cache_ttl)
        else:
            self.cache = None

        self._stats = {"searches": 0, "cache_hits": 0, "cache_misses": 0, "total_latency": 0}

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        similarity_threshold: float = 0.0,
    ) -> list[ChunkResult]:
        """
        Search for similar chunks using vector similarity.

        Args:
            query: Search query text
            limit: Maximum number of results
            filters: Optional metadata filters
            similarity_threshold: Minimum similarity score

        Returns:
            List of chunk results
        """
        start_time = datetime.now()
        self._stats["searches"] += 1

        # Generate query embedding
        query_embedding = await self.embedder.embed(query)

        # Check cache
        if self.cache:
            cache_key = SearchCache.generate_key(query_embedding, filters)
            cached = self.cache.get(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached[:limit]
            self._stats["cache_misses"] += 1

        # Perform search
        results = await self._search_vectors(
            query_embedding, limit * 2, filters, similarity_threshold  # Get more for filtering
        )

        # Cache results
        if self.cache and results:
            self.cache.set(cache_key, results)

        # Update stats
        latency = (datetime.now() - start_time).total_seconds()
        self._stats["total_latency"] += latency

        logger.info(f"Vector search completed in {latency:.3f}s, found {len(results)} results")

        return results[:limit]

    async def _search_vectors(
        self,
        query_embedding: list[float],
        limit: int,
        filters: dict[str, Any] | None,
        similarity_threshold: float,
    ) -> list[ChunkResult]:
        """
        Execute vector search query.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum results
            filters: Metadata filters
            similarity_threshold: Minimum similarity

        Returns:
            List of chunk results
        """
        async with self.connection_manager.get_pg_connection() as conn:
            # Build query based on embedding dimension
            embedding_dim = len(query_embedding)
            embedding_column = f"embedding_{embedding_dim}"

            # Optimized query with IVFFlat index
            # embedding_column is validated to be 'embedding_768' or 'embedding_1536'
            query = f"""
            SELECT
                c.id as chunk_id,
                c.content,
                1 - (c.{embedding_column} <=> $1::vector) as similarity,
                c.document_id,
                c.metadata,
                c.entity_refs,
                d.title as document_title,
                d.source as document_source,
                d.metadata as document_metadata
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.{embedding_column} IS NOT NULL
                AND (1 - (c.{embedding_column} <=> $1::vector)) >= $2
                AND ($3::jsonb IS NULL OR c.metadata @> $3::jsonb)
            ORDER BY c.{embedding_column} <=> $1::vector
            LIMIT $4
            """  # nosec B608

            # Convert embedding to PostgreSQL vector format
            # asyncpg needs vector as string format: "[1.0,2.0,3.0]"
            if isinstance(query_embedding, str):
                # Already in string format (from DB)
                embedding_str = query_embedding
            else:
                # Convert list to string format
                embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            # Execute query
            rows = await conn.fetch(
                query,
                embedding_str,
                similarity_threshold,
                json.dumps(filters) if filters else None,
                limit,
            )

            # Convert to ChunkResult objects
            results = []
            for row in rows:
                chunk_metadata = (
                    json.loads(row["metadata"])
                    if isinstance(row["metadata"], str)
                    else row["metadata"]
                )

                results.append(
                    ChunkResult(
                        chunk_id=row["chunk_id"],
                        content=row["content"],
                        similarity=row["similarity"],
                        document_id=row["document_id"],
                        document_title=row["document_title"],
                        document_source=row["document_source"],
                        metadata=chunk_metadata,
                        entities=row["entity_refs"] or [],
                    )
                )

            return results

    async def search_similar_chunks(self, chunk_id: UUID, limit: int = 5) -> list[ChunkResult]:
        """
        Find chunks similar to a given chunk.

        Args:
            chunk_id: Reference chunk ID
            limit: Maximum number of results

        Returns:
            List of similar chunks
        """
        # Get the reference chunk's embedding
        async with self.connection_manager.get_pg_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT content, embedding_1536, embedding_768
                FROM chunks
                WHERE id = $1
                """,
                chunk_id,
            )

            if not row:
                return []

            # Use whichever embedding is available
            embedding = row["embedding_1536"] or row["embedding_768"]
            if not embedding:
                return []

            # Search for similar chunks
            return await self._search_vectors(
                embedding,
                limit + 1,  # +1 to exclude self
                None,
                0.7,  # Higher threshold for similarity search
            )

    async def get_chunks_by_ids(self, chunk_ids: list[UUID]) -> list[ChunkResult]:
        """
        Retrieve specific chunks by IDs.

        Args:
            chunk_ids: List of chunk IDs

        Returns:
            List of chunk results
        """
        if not chunk_ids:
            return []

        async with self.connection_manager.get_pg_connection() as conn:
            query = """
            SELECT
                c.id as chunk_id,
                c.content,
                c.document_id,
                c.metadata,
                c.entity_refs,
                d.title as document_title,
                d.source as document_source,
                d.metadata as document_metadata
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.id = ANY($1::uuid[])
            """

            rows = await conn.fetch(query, chunk_ids)

            results = []
            for row in rows:
                chunk_metadata = (
                    json.loads(row["metadata"])
                    if isinstance(row["metadata"], str)
                    else row["metadata"]
                )

                results.append(
                    ChunkResult(
                        chunk_id=row["chunk_id"],
                        content=row["content"],
                        similarity=1.0,  # Direct retrieval, max similarity
                        document_id=row["document_id"],
                        document_title=row["document_title"],
                        document_source=row["document_source"],
                        metadata=chunk_metadata,
                        entities=row["entity_refs"] or [],
                    )
                )

            return results

    def get_stats(self) -> dict[str, Any]:
        """
        Get search statistics.

        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()

        if stats["searches"] > 0:
            stats["avg_latency"] = stats["total_latency"] / stats["searches"]

            if stats["cache_hits"] + stats["cache_misses"] > 0:
                stats["cache_hit_rate"] = stats["cache_hits"] / (
                    stats["cache_hits"] + stats["cache_misses"]
                )
            else:
                stats["cache_hit_rate"] = 0.0

        return stats

    def clear_cache(self):
        """Clear the search cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Search cache cleared")
