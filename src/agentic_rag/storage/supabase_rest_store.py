"""
Supabase REST API store for document and chunk storage.

This is an alternative to PostgresStore for environments where
direct PostgreSQL connection is blocked (e.g., restrictive firewalls).
Uses Supabase's REST API instead of asyncpg.
"""

import json
import logging
from typing import Any
from uuid import UUID

from supabase import Client, create_client

logger = logging.getLogger(__name__)


class SupabaseRestStore:
    """
    Document and chunk storage using Supabase REST API.

    This class mirrors PostgresStore interface but uses REST instead of SQL.
    """

    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize Supabase REST client.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key
        """
        self.client: Client = create_client(supabase_url, supabase_key)
        logger.info(f"Initialized SupabaseRestStore for {supabase_url}")

    async def store_document(
        self, title: str, source: str, content: str, metadata: dict[str, Any] | None = None
    ) -> UUID:
        """
        Store a document and return its ID.

        Args:
            title: Document title
            source: Document source/filename
            content: Full document content
            metadata: Optional metadata dict

        Returns:
            UUID of created document
        """
        doc_data = {
            "title": title,
            "source": source,
            "content": content,
            "metadata": metadata or {},
        }

        try:
            result = self.client.table("documents").insert(doc_data).execute()

            if result.data and len(result.data) > 0:
                doc_id = UUID(result.data[0]["id"])
                logger.info(f"Stored document {doc_id}: {title}")
                return doc_id
            raise ValueError("No document ID returned from insert")

        except Exception as e:
            logger.error(f"Failed to store document '{title}': {e}")
            raise

    async def store_chunks(self, document_id: UUID, chunks: list[dict[str, Any]]) -> list[UUID]:
        """
        Store multiple chunks and return their IDs.

        Args:
            document_id: Parent document UUID
            chunks: List of chunk dictionaries with content, embeddings, etc.

        Returns:
            List of chunk UUIDs
        """
        chunk_ids = []

        try:
            # Prepare chunk records
            chunk_records = []
            for i, chunk in enumerate(chunks):
                chunk_record = {
                    "document_id": str(document_id),
                    "content": chunk["content"],
                    "chunk_index": i,
                    "start_char": chunk.get("start_char", i * 1000),
                    "end_char": chunk.get("end_char", (i + 1) * 1000),
                    "metadata": chunk.get("metadata", {}),
                    "token_count": chunk.get("token_count"),
                }

                # Add embeddings if present
                if chunk.get("embedding_1536"):
                    chunk_record["embedding_1536"] = chunk["embedding_1536"]
                if chunk.get("embedding_768"):
                    chunk_record["embedding_768"] = chunk["embedding_768"]

                chunk_records.append(chunk_record)

            # Batch insert chunks
            result = self.client.table("chunks").insert(chunk_records).execute()

            if result.data:
                chunk_ids = [UUID(row["id"]) for row in result.data]
                logger.info(f"Stored {len(chunk_ids)} chunks for document {document_id}")
            else:
                raise ValueError("No chunk IDs returned from insert")

        except Exception as e:
            logger.error(f"Failed to store chunks for document {document_id}: {e}")
            raise

        return chunk_ids

    async def update_chunk_metadata(self, chunk_id: UUID, metadata_update: dict[str, Any]):
        """
        Update chunk metadata with entity references.

        Args:
            chunk_id: Chunk UUID
            metadata_update: Metadata fields to update
        """
        try:
            # Get existing chunk
            result = (
                self.client.table("chunks").select("metadata").eq("id", str(chunk_id)).execute()
            )

            if not result.data or len(result.data) == 0:
                logger.warning(f"Chunk {chunk_id} not found for metadata update")
                return

            # Merge metadata
            existing_meta = result.data[0].get("metadata", {})
            if isinstance(existing_meta, str):
                existing_meta = json.loads(existing_meta)

            existing_meta.update(metadata_update)

            # Update chunk
            update_data = {"metadata": existing_meta}

            # Handle entity_refs separately if present
            if "entity_refs" in metadata_update:
                update_data["entity_refs"] = metadata_update["entity_refs"]

            self.client.table("chunks").update(update_data).eq("id", str(chunk_id)).execute()

            logger.debug(f"Updated metadata for chunk {chunk_id}")

        except Exception as e:
            logger.error(f"Failed to update metadata for chunk {chunk_id}: {e}")
            raise

    async def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 10,
        threshold: float = 0.7,
        embedding_column: str = "embedding_1536",
    ) -> list[dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.

        Note: This uses Supabase's RPC function for vector search.
        The schema must have a match_chunks() or similar function.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum results to return
            threshold: Similarity threshold
            embedding_column: Which embedding column to use

        Returns:
            List of similar chunks with similarity scores
        """
        try:
            # Use Supabase RPC for vector search
            # This requires the match_chunks() function in schema
            result = self.client.rpc(
                "match_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": limit,
                },
            ).execute()

            if result.data:
                logger.info(f"Found {len(result.data)} similar chunks")
                return result.data
            return []

        except Exception as e:
            logger.warning(f"Vector search failed (may not be implemented): {e}")
            # Fallback: return empty results
            return []

    async def get_document(self, document_id: UUID) -> dict[str, Any] | None:
        """
        Get document by ID.

        Args:
            document_id: Document UUID

        Returns:
            Document data or None if not found
        """
        try:
            result = self.client.table("documents").select("*").eq("id", str(document_id)).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None

    async def get_chunks(self, document_id: UUID) -> list[dict[str, Any]]:
        """
        Get all chunks for a document.

        Args:
            document_id: Document UUID

        Returns:
            List of chunk data
        """
        try:
            result = (
                self.client.table("chunks")
                .select("*")
                .eq("document_id", str(document_id))
                .order("chunk_index")
                .execute()
            )

            if result.data:
                return result.data
            return []

        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {e}")
            return []

    async def delete_document(self, document_id: UUID) -> bool:
        """
        Delete document and its chunks.

        Args:
            document_id: Document UUID

        Returns:
            True if successful
        """
        try:
            # Delete chunks first (foreign key constraint)
            self.client.table("chunks").delete().eq("document_id", str(document_id)).execute()

            # Delete document
            self.client.table("documents").delete().eq("id", str(document_id)).execute()

            logger.info(f"Deleted document {document_id} and its chunks")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
