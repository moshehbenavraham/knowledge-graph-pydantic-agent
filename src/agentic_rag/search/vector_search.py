"""
Vector similarity search using pgvector.

High-performance vector search with caching and metadata filtering.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

import structlog

from src.agentic_rag.config import get_config
from src.agentic_rag.ingestion.embedder import EmbeddingGenerator
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.agentic_rag.storage.postgres_store import PostgresStore

logger = logging.getLogger(__name__)
structlog_logger = structlog.get_logger(__name__)


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

    def get(
        self, key: str
    ) -> list[ChunkResult] | None:  # Constitution exception: CONST-V-001 - Simple cache accessor
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

    def set(
        self, key: str, results: list[ChunkResult]
    ) -> None:  # Constitution exception: CONST-V-001 - Simple cache accessor
        """
        Cache results.

        Args:
            key: Cache key
            results: Results to cache
        """
        self._cache[key] = (datetime.now(), results)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()

    @staticmethod
    def generate_key(query_embedding: list[float], filters: dict[str, Any] | None = None) -> str:
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

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize vector search.

        Args:
            connection_manager: Initialized database connection manager (required)

        Raises:
            ValueError: If connection_manager is None
        """
        if connection_manager is None:
            raise ValueError(
                "VectorSearch requires an initialized ConnectionManager. "
                "Use get_connection_manager() to get a properly initialized instance."
            )

        self.config = get_config()
        self.connection_manager = connection_manager
        self.pg_store = PostgresStore(self.connection_manager)
        self.embedder = EmbeddingGenerator()

        # Initialize cache if enabled
        self.cache: SearchCache | None
        if self.config.performance.enable_caching:
            self.cache = SearchCache(ttl_seconds=self.config.performance.embedding_cache_ttl)
        else:
            self.cache = None

        self._stats: dict[str, Any] = {
            "searches": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_latency": 0,
        }

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

        structlog_logger.info(
            "Vector search starting",
            query_preview=query[:80],
            query_truncated=len(query) > 80,
            limit=limit,
            similarity_threshold=similarity_threshold,
            has_filters=bool(filters),
        )

        # Generate query embedding
        embed_start = datetime.now()
        raw_embedding = await self.embedder.embed(query)
        # Single text input returns single embedding (list[float]), not batch
        query_embedding: list[float] = cast("list[float]", raw_embedding)
        embed_time = (datetime.now() - embed_start).total_seconds()
        structlog_logger.info(
            "Embedding generated",
            embedding_dim=len(query_embedding),
            embed_time_s=round(embed_time, 3),
        )

        # Check cache
        if self.cache:
            cache_key = SearchCache.generate_key(query_embedding, filters)
            cached = self.cache.get(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                latency = (datetime.now() - start_time).total_seconds()
                structlog_logger.info(
                    "Cache hit - returning cached results",
                    cached_results=len(cached[:limit]),
                    total_latency_s=round(latency, 3),
                )
                return cached[:limit]
            self._stats["cache_misses"] += 1
            structlog_logger.info("Cache miss - executing database search")

        # Perform search
        search_start = datetime.now()
        results = await self._search_vectors(
            query_embedding, limit * 2, filters, similarity_threshold  # Get more for filtering
        )
        search_time = (datetime.now() - search_start).total_seconds()

        # Cache results
        if self.cache and results:
            self.cache.set(cache_key, results)
            structlog_logger.info("Results cached for future queries")

        # Update stats
        latency = (datetime.now() - start_time).total_seconds()
        self._stats["total_latency"] += latency

        # Log result details
        if results:
            avg_similarity = sum(r.similarity for r in results) / len(results)
            top_similarity = results[0].similarity if results else 0
            structlog_logger.info(
                "Vector search completed",
                total_results=len(results),
                search_time_s=round(search_time, 3),
                top_similarity=round(top_similarity, 3),
                avg_similarity=round(avg_similarity, 3),
                returning=len(results[:limit]),
                total_latency_s=round(latency, 3),
            )
        else:
            structlog_logger.info(
                "Vector search completed - no results",
                similarity_threshold=similarity_threshold,
                total_latency_s=round(latency, 3),
            )

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
        embedding_dim = len(query_embedding)
        structlog_logger.debug(
            "Executing pgvector query",
            embedding_column=f"embedding_{embedding_dim}",
            limit=limit,
            similarity_threshold=similarity_threshold,
            has_filters=bool(filters),
        )

        async with self.connection_manager.get_pg_connection() as conn:
            # Build query based on embedding dimension
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
        structlog_logger.info("search_similar_chunks called", chunk_id=str(chunk_id), limit=limit)

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
                structlog_logger.info(
                    "search_similar_chunks - chunk not found", chunk_id=str(chunk_id)
                )
                return []

            # Use whichever embedding is available
            embedding = row["embedding_1536"] or row["embedding_768"]
            if not embedding:
                structlog_logger.info(
                    "search_similar_chunks - no embedding found", chunk_id=str(chunk_id)
                )
                return []

            # Search for similar chunks
            results = await self._search_vectors(
                embedding,
                limit + 1,  # +1 to exclude self
                None,
                0.7,  # Higher threshold for similarity search
            )

            structlog_logger.info("search_similar_chunks completed", num_results=len(results))
            return results

    async def get_chunks_by_ids(self, chunk_ids: list[UUID]) -> list[ChunkResult]:
        """
        Retrieve specific chunks by IDs.

        Args:
            chunk_ids: List of chunk IDs

        Returns:
            List of chunk results
        """
        structlog_logger.info("get_chunks_by_ids called", num_chunk_ids=len(chunk_ids))

        if not chunk_ids:
            structlog_logger.info("get_chunks_by_ids - empty chunk_ids list")
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

            structlog_logger.info("get_chunks_by_ids completed", num_results=len(results))
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

        structlog_logger.debug(
            "get_stats called",
            searches=stats.get("searches", 0),
            avg_latency=round(stats.get("avg_latency", 0), 3),
            cache_hit_rate=round(stats.get("cache_hit_rate", 0), 3),
        )
        return stats

    def clear_cache(self) -> None:
        """Clear the search cache."""
        if self.cache:
            self.cache.clear()
            structlog_logger.info("Search cache cleared")
