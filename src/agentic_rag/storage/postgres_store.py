"""
PostgreSQL store operations for content storage and vector search.
"""

import json
import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class PostgresStore:
    """PostgreSQL operations for document and chunk storage."""

    def __init__(self, connection_manager):
        """Initialize with connection manager."""
        self.connection_manager = connection_manager

    async def store_document(
        self, title: str, source: str, content: str, metadata: dict[str, Any] | None = None
    ) -> UUID:
        """Store a document and return its ID."""
        async with self.connection_manager.get_pg_connection() as conn:
            doc_id = await conn.fetchval(
                """
                INSERT INTO documents (title, source, content, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """,
                title,
                source,
                content,
                json.dumps(metadata or {}),
            )

            logger.info(f"Stored document {doc_id}: {title}")
            return doc_id

    async def store_chunks(self, document_id: UUID, chunks: list[dict[str, Any]]) -> list[UUID]:
        """Store multiple chunks and return their IDs."""
        chunk_ids = []

        async with self.connection_manager.get_pg_connection() as conn:
            # Prepare batch insert data
            insert_data = []
            for i, chunk in enumerate(chunks):
                # Convert embeddings to PostgreSQL vector format
                emb_1536 = chunk.get("embedding_1536")
                emb_768 = chunk.get("embedding_768")
                # PostgreSQL vector expects string format like '[1.0, 2.0, 3.0]'
                emb_1536_str = f"[{','.join(map(str, emb_1536))}]" if emb_1536 else None
                emb_768_str = f"[{','.join(map(str, emb_768))}]" if emb_768 else None

                insert_data.append(
                    (
                        document_id,
                        chunk["content"],
                        emb_1536_str,
                        emb_768_str,
                        i,  # chunk_index
                        chunk.get("start_char", i * 1000),
                        chunk.get("end_char", (i + 1) * 1000),
                        json.dumps(chunk.get("metadata", {})),
                        chunk.get("token_count"),
                    )
                )

            # Batch insert chunks using executemany
            chunk_ids = []
            for chunk_data in insert_data:
                row = await conn.fetchrow(
                    """
                    INSERT INTO chunks (
                        document_id, content, embedding_1536, embedding_768,
                        chunk_index, start_char, end_char, metadata, token_count
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                    """,
                    *chunk_data,
                )
                chunk_ids.append(row["id"])

            logger.info(f"Stored {len(chunk_ids)} chunks for document {document_id}")

        return chunk_ids

    async def update_chunk_metadata(self, chunk_id: UUID, metadata_update: dict[str, Any]):
        """Update chunk metadata with entity references."""
        async with self.connection_manager.get_pg_connection() as conn:
            # Get existing metadata
            existing = await conn.fetchval("SELECT metadata FROM chunks WHERE id = $1", chunk_id)

            if existing:
                existing_meta = json.loads(existing) if isinstance(existing, str) else existing
            else:
                existing_meta = {}

            # Merge metadata
            existing_meta.update(metadata_update)

            # Update entity_refs if provided
            if "entity_refs" in metadata_update:
                await conn.execute(
                    """
                    UPDATE chunks
                    SET metadata = $1,
                        entity_refs = $2
                    WHERE id = $3
                """,
                    json.dumps(existing_meta),
                    metadata_update["entity_refs"],
                    chunk_id,
                )
            else:
                await conn.execute(
                    """
                    UPDATE chunks
                    SET metadata = $1
                    WHERE id = $2
                """,
                    json.dumps(existing_meta),
                    chunk_id,
                )

    async def search_similar(
        self, embedding: list[float], limit: int = 10, similarity_threshold: float = 0.7
    ) -> list[dict[str, Any]]:
        """Search for similar chunks using vector similarity."""
        async with self.connection_manager.get_pg_connection() as conn:
            # Determine embedding dimension
            embedding_dim = len(embedding)
            embedding_column = "embedding_1536" if embedding_dim == 1536 else "embedding_768"

            # embedding_column is validated above to be either 'embedding_1536' or 'embedding_768'
            results = await conn.fetch(
                f"""
                SELECT
                    c.id,
                    c.document_id,
                    c.content,
                    c.metadata,
                    c.chunk_index,
                    d.title,
                    d.source,
                    1 - (c.{embedding_column} <=> $1::vector) as similarity
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.{embedding_column} IS NOT NULL
                    AND d.is_deleted = FALSE
                    AND 1 - (c.{embedding_column} <=> $1::vector) >= $2
                ORDER BY c.{embedding_column} <=> $1::vector
                LIMIT $3
            """,  # nosec B608
                embedding,
                similarity_threshold,
                limit,
            )

            return [dict(row) for row in results]

    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        entity_ids: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search with vector + text + entity boosting."""
        async with self.connection_manager.get_pg_connection() as conn:
            # Determine embedding dimension
            embedding_dim = len(query_embedding)
            embedding_column = "embedding_1536" if embedding_dim == 1536 else "embedding_768"

            # embedding_column is validated above to be either 'embedding_1536' or 'embedding_768'
            # Call the hybrid search function
            results = await conn.fetch(
                f"""
                SELECT * FROM hybrid_search_enhanced(
                    $1::{embedding_column},
                    NULL,  -- embedding_768 (if using 1536)
                    $2,    -- query_text
                    $3,    -- entity_ids
                    $4,    -- match_count
                    TRUE,  -- use_cache
                    0.7    -- similarity_threshold
                )
            """,  # nosec B608
                query_embedding,
                query_text,
                entity_ids,
                limit,
            )

            return [dict(row) for row in results]

    async def get_chunks_by_ids(self, chunk_ids: list[UUID]) -> list[dict[str, Any]]:
        """Get chunks by their IDs."""
        async with self.connection_manager.get_pg_connection() as conn:
            results = await conn.fetch(
                """
                SELECT
                    c.*,
                    d.title as document_title,
                    d.source as document_source
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.id = ANY($1)
                ORDER BY c.document_id, c.chunk_index
            """,
                chunk_ids,
            )

            return [dict(row) for row in results]

    async def get_document(self, document_id: UUID) -> dict[str, Any] | None:
        """Get a document by ID."""
        async with self.connection_manager.get_pg_connection() as conn:
            result = await conn.fetchrow(
                """
                SELECT * FROM documents
                WHERE id = $1 AND is_deleted = FALSE
            """,
                document_id,
            )

            return dict(result) if result else None

    async def delete_document(self, document_id: UUID, hard_delete: bool = False):
        """Delete a document (soft delete by default)."""
        async with self.connection_manager.get_pg_connection() as conn:
            if hard_delete:
                # Add to sync queue for Neo4j cleanup
                await conn.execute(
                    """
                    INSERT INTO graph_sync_queue (document_id, operation, payload)
                    VALUES ($1, 'delete', '{"hard_delete": true}'::jsonb)
                """,
                    document_id,
                )

                # Hard delete
                await conn.execute(
                    """
                    DELETE FROM documents WHERE id = $1
                """,
                    document_id,
                )

                logger.info(f"Hard deleted document {document_id}")
            else:
                # Soft delete
                await conn.execute(
                    """
                    UPDATE documents
                    SET is_deleted = TRUE, deleted_at = NOW()
                    WHERE id = $1
                """,
                    document_id,
                )

                logger.info(f"Soft deleted document {document_id}")

    async def create_session(
        self, user_id: str | None = None, metadata: dict[str, Any] | None = None
    ) -> UUID:
        """Create a new chat session."""
        async with self.connection_manager.get_pg_connection() as conn:
            session_id = await conn.fetchval(
                """
                INSERT INTO sessions (user_id, metadata)
                VALUES ($1, $2)
                RETURNING id
            """,
                user_id,
                json.dumps(metadata or {}),
            )

            return session_id

    async def add_message(
        self, session_id: UUID, role: str, content: str, metadata: dict[str, Any] | None = None
    ):
        """Add a message to a session."""
        async with self.connection_manager.get_pg_connection() as conn:
            await conn.execute(
                """
                INSERT INTO messages (session_id, role, content, metadata)
                VALUES ($1, $2, $3, $4)
            """,
                session_id,
                role,
                content,
                json.dumps(metadata or {}),
            )

    async def get_session_messages(self, session_id: UUID, limit: int = 50) -> list[dict[str, Any]]:
        """Get messages from a session."""
        async with self.connection_manager.get_pg_connection() as conn:
            results = await conn.fetch(
                """
                SELECT * FROM messages
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """,
                session_id,
                limit,
            )

            return [dict(row) for row in reversed(results)]

    async def add_to_sync_queue(
        self,
        document_id: UUID | None = None,
        chunk_id: UUID | None = None,
        operation: str = "create",
        payload: dict[str, Any] | None = None,
    ):
        """Add an item to the graph sync queue."""
        async with self.connection_manager.get_pg_connection() as conn:
            await conn.execute(
                """
                INSERT INTO graph_sync_queue (document_id, chunk_id, operation, payload)
                VALUES ($1, $2, $3, $4)
            """,
                document_id,
                chunk_id,
                operation,
                json.dumps(payload or {}),
            )

    async def get_pending_sync_items(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get pending items from sync queue."""
        async with self.connection_manager.get_pg_connection() as conn:
            results = await conn.fetch(
                """
                SELECT * FROM graph_sync_queue
                WHERE status = 'pending'
                    AND retry_count < max_retries
                ORDER BY created_at
                LIMIT $1
            """,
                limit,
            )

            return [dict(row) for row in results]

    async def update_sync_item_status(
        self, sync_id: UUID, status: str, error_message: str | None = None
    ):
        """Update sync queue item status."""
        async with self.connection_manager.get_pg_connection() as conn:
            if status == "failed":
                await conn.execute(
                    """
                    UPDATE graph_sync_queue
                    SET status = $1,
                        retry_count = retry_count + 1,
                        error_message = $2,
                        processed_at = NOW()
                    WHERE id = $3
                """,
                    status,
                    error_message,
                    sync_id,
                )
            else:
                await conn.execute(
                    """
                    UPDATE graph_sync_queue
                    SET status = $1,
                        processed_at = NOW()
                    WHERE id = $2
                """,
                    status,
                    sync_id,
                )

    async def clean_expired_cache(self):
        """Clean expired search cache entries."""
        async with self.connection_manager.get_pg_connection() as conn:
            deleted = await conn.fetchval(
                """
                DELETE FROM search_cache
                WHERE expires_at < NOW()
                RETURNING COUNT(*)
            """
            )

            if deleted:
                logger.info(f"Cleaned {deleted} expired cache entries")

    async def list_documents(
        self,
        limit: int = 20,
        offset: int = 0,
        source_filter: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        """
        List documents with pagination and filtering.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip (for pagination)
            source_filter: Optional source filter (exact match or pattern)
            sort_by: Field to sort by (created_at, title, updated_at)
            sort_order: Sort order (asc or desc)

        Returns:
            List of document dictionaries with metadata

        Example:
            documents = await store.list_documents(
                limit=20,
                offset=0,
                source_filter="%.pdf",
                sort_by="created_at",
                sort_order="desc"
            )
        """
        async with self.connection_manager.get_pg_connection() as conn:
            # Validate sort parameters
            valid_sort_fields = {"created_at", "title", "updated_at"}
            if sort_by not in valid_sort_fields:
                sort_by = "created_at"

            valid_sort_orders = {"asc", "desc"}
            if sort_order.lower() not in valid_sort_orders:
                sort_order = "desc"

            # Build dynamic ORDER BY clause
            order_clause = f"d.{sort_by} {sort_order.upper()}"

            # sort_by and sort_order are validated against whitelists above
            query = f"""
                SELECT
                    d.id,
                    d.title,
                    d.source,
                    d.created_at,
                    d.updated_at,
                    d.metadata,
                    COUNT(c.id) as chunk_count
                FROM documents d
                LEFT JOIN chunks c ON c.document_id = d.id
                WHERE d.is_deleted = FALSE
                    AND ($3::text IS NULL OR d.source LIKE $3)
                GROUP BY d.id, d.title, d.source, d.created_at, d.updated_at, d.metadata
                ORDER BY {order_clause}
                LIMIT $1 OFFSET $2
            """  # nosec B608

            rows = await conn.fetch(query, limit, offset, source_filter)
            return [dict(row) for row in rows]

    async def count_documents(self, source_filter: str | None = None) -> int:
        """
        Count total documents with optional filtering.

        Args:
            source_filter: Optional source filter (exact match or pattern)

        Returns:
            Total count of matching documents
        """
        async with self.connection_manager.get_pg_connection() as conn:
            query = """
                SELECT COUNT(*) as total
                FROM documents
                WHERE is_deleted = FALSE
                    AND ($1::text IS NULL OR source LIKE $1)
            """

            row = await conn.fetchrow(query, source_filter)
            return row["total"] if row else 0

    async def get_document_chunks(
        self, document_id: UUID, include_embeddings: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get all chunks for a document.

        Args:
            document_id: Document UUID
            include_embeddings: Whether to include embedding vectors

        Returns:
            List of chunk dictionaries
        """
        async with self.connection_manager.get_pg_connection() as conn:
            if include_embeddings:
                query = """
                    SELECT
                        id, document_id, content,
                        embedding_1536, embedding_768,
                        chunk_index, metadata, token_count,
                        start_char, end_char, entity_refs,
                        created_at
                    FROM chunks
                    WHERE document_id = $1
                    ORDER BY chunk_index ASC
                """
            else:
                query = """
                    SELECT
                        id, document_id, content, chunk_index,
                        metadata, token_count,
                        start_char, end_char, entity_refs,
                        created_at
                    FROM chunks
                    WHERE document_id = $1
                    ORDER BY chunk_index ASC
                """

            rows = await conn.fetch(query, document_id)
            return [dict(row) for row in rows]

    async def update_document(self, document_id: UUID, updates: dict[str, Any]) -> bool:
        """
        Update document metadata.

        Args:
            document_id: Document UUID
            updates: Dictionary of fields to update (title, metadata)

        Returns:
            True if updated, False if not found
        """
        async with self.connection_manager.get_pg_connection() as conn:
            # Build dynamic UPDATE query based on provided fields
            allowed_fields = {"title", "metadata"}
            update_fields = {k: v for k, v in updates.items() if k in allowed_fields}

            if not update_fields:
                logger.warning(f"No valid fields to update for document {document_id}")
                return False

            set_clauses = []
            values = [document_id]
            param_idx = 2

            for field, value in update_fields.items():
                if field == "metadata":
                    # Handle metadata as JSONB
                    set_clauses.append(f"{field} = ${param_idx}::jsonb")
                    values.append(json.dumps(value))
                else:
                    set_clauses.append(f"{field} = ${param_idx}")
                    values.append(value)
                param_idx += 1

            # Always update the updated_at timestamp
            set_clauses.append("updated_at = NOW()")

            # set_clauses built from allowed_fields whitelist above
            query = f"""
                UPDATE documents
                SET {', '.join(set_clauses)}
                WHERE id = $1 AND is_deleted = FALSE
                RETURNING id
            """  # nosec B608

            result = await conn.fetchrow(query, *values)
            success = result is not None

            if success:
                logger.info(f"Updated document {document_id}: {list(update_fields.keys())}")
            else:
                logger.warning(f"Document {document_id} not found for update")

            return success

    async def count_chunks(self, document_id: UUID) -> int:
        """
        Count chunks for a document.

        Args:
            document_id: Document UUID

        Returns:
            Number of chunks
        """
        async with self.connection_manager.get_pg_connection() as conn:
            query = """
                SELECT COUNT(*) as total
                FROM chunks
                WHERE document_id = $1
            """

            row = await conn.fetchrow(query, document_id)
            return row["total"] if row else 0

    async def get_statistics(self) -> dict[str, Any]:
        """Get database statistics."""
        async with self.connection_manager.get_pg_connection() as conn:
            stats = {}

            # Document stats
            stats["total_documents"] = await conn.fetchval(
                """
                SELECT COUNT(*) FROM documents WHERE is_deleted = FALSE
            """
            )

            # Chunk stats
            chunk_stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_chunks,
                    COUNT(DISTINCT document_id) as documents_with_chunks,
                    COUNT(embedding_1536) as chunks_with_1536_embeddings,
                    COUNT(embedding_768) as chunks_with_768_embeddings,
                    AVG(token_count) as avg_token_count
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.is_deleted = FALSE
            """
            )
            stats.update(dict(chunk_stats))

            # Session stats
            session_stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(DISTINCT s.id) as total_sessions,
                    COUNT(m.id) as total_messages
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id
            """
            )
            stats.update(dict(session_stats))

            # Sync queue stats
            sync_stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_syncs,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_syncs,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_syncs
                FROM graph_sync_queue
            """
            )
            stats.update(dict(sync_stats))

            # Cache stats
            cache_stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as cached_searches,
                    AVG(hit_count) as avg_cache_hits,
                    MAX(hit_count) as max_cache_hits
                FROM search_cache
                WHERE expires_at > NOW()
            """
            )
            stats.update(dict(cache_stats))

            return stats
