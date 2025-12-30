#!/usr/bin/env python3
"""
Backfill document_refs property on existing Neo4j entities.

This script populates the document_refs property on entities that were
created before the document reference tracking feature was implemented.
It processes entities in batches to avoid timeouts and supports resumption.

Usage:
    python scripts/backfill_document_refs.py --batch-size 100 --dry-run
    python scripts/backfill_document_refs.py --batch-size 100

Options:
    --batch-size    Number of entities to process per batch (default: 100)
    --dry-run       Preview changes without applying them
    --resume-from   Entity ID to resume from (for interrupted runs)
    --verbose       Enable verbose logging
"""

import argparse
import asyncio
import sys
from pathlib import Path

import structlog

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agentic_rag.models.document_reference import (  # noqa: E402
    DocumentReference,
    extract_document_metadata,
)
from src.agentic_rag.storage.connection_manager import ConnectionManager  # noqa: E402

logger = structlog.get_logger(__name__)


# Configuration constants
DEFAULT_BATCH_SIZE = 100
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0


async def retry_with_backoff(
    coro_func,
    *args,
    max_retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF_SECONDS,
    **kwargs,
):
    """
    Execute a coroutine with exponential backoff retry logic.

    Args:
        coro_func: Async function to execute
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the coroutine

    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    backoff = initial_backoff

    for attempt in range(max_retries + 1):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    "Operation failed, retrying",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    backoff_seconds=backoff,
                    error=str(e),
                )
                await asyncio.sleep(backoff)
                backoff *= 2  # Exponential backoff
            else:
                logger.error(
                    "Operation failed after all retries",
                    attempts=max_retries + 1,
                    error=str(e),
                )

    raise last_exception  # type: ignore[misc]


class DocumentRefBackfill:
    """
    Handles backfilling document_refs on existing entities.

    Processes entities in batches, extracts document metadata from
    associated chunks, and updates the entity's document_refs property.
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        batch_size: int = DEFAULT_BATCH_SIZE,
        dry_run: bool = False,
    ) -> None:
        """
        Initialize the backfill processor.

        Args:
            connection_manager: Database connection manager
            batch_size: Number of entities to process per batch
            dry_run: If True, preview changes without applying
        """
        self.connection_manager = connection_manager
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.stats = {
            "total_entities": 0,
            "entities_processed": 0,
            "entities_updated": 0,
            "entities_skipped": 0,
            "errors": 0,
        }

    async def get_total_entity_count(self) -> int:
        """Get total number of entities in the graph."""
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
            record = await result.single()
            return record["count"] if record else 0

    async def get_entity_batch(
        self,
        offset: int,
        limit: int,
        resume_from: str | None = None,
    ) -> list[dict]:
        """
        Fetch a batch of entities to process.

        Args:
            offset: Number of entities to skip
            limit: Maximum entities to return
            resume_from: Optional entity ID to resume from

        Returns:
            List of entity dictionaries
        """
        async with self.connection_manager.get_neo4j_session() as session:
            if resume_from:
                query = """
                    MATCH (e:Entity)
                    WHERE e.id >= $resume_from
                    RETURN e.id as id, e.name as name, e.type as type,
                           e.chunk_refs as chunk_refs, e.document_refs as document_refs
                    ORDER BY e.id
                    LIMIT $limit
                """
                result = await session.run(query, resume_from=resume_from, limit=limit)
            else:
                query = """
                    MATCH (e:Entity)
                    RETURN e.id as id, e.name as name, e.type as type,
                           e.chunk_refs as chunk_refs, e.document_refs as document_refs
                    ORDER BY e.id
                    SKIP $offset
                    LIMIT $limit
                """
                result = await session.run(query, offset=offset, limit=limit)

            entities = []
            async for record in result:
                entities.append(dict(record))
            return entities

    async def get_chunk_metadata(self, chunk_ids: list[str]) -> list[dict]:
        """
        Fetch chunk metadata from PostgreSQL.

        Args:
            chunk_ids: List of chunk IDs to fetch

        Returns:
            List of chunk metadata dictionaries
        """
        if not chunk_ids:
            return []

        async with self.connection_manager.get_postgres_connection() as conn:
            # Query chunks table for metadata
            query = """
                SELECT c.id, c.metadata, d.title, d.source
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.id::text = ANY($1)
            """
            rows = await conn.fetch(query, chunk_ids)
            return [dict(row) for row in rows]

    async def _do_update_entity(
        self,
        entity_id: str,
        document_refs: list[dict],
    ) -> bool:
        """Internal method to perform the actual Neo4j update."""
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {id: $entity_id})
                SET e.document_refs = $document_refs
                RETURN e.id as id
                """,
                entity_id=entity_id,
                document_refs=document_refs,
            )
            record = await result.single()
            return record is not None

    async def update_entity_document_refs(
        self,
        entity_id: str,
        document_refs: list[dict],
    ) -> bool:
        """
        Update entity with document references (with retry logic).

        Args:
            entity_id: Entity ID to update
            document_refs: List of document reference dictionaries

        Returns:
            True if update succeeded
        """
        if self.dry_run:
            logger.info(
                "DRY RUN: Would update entity",
                entity_id=entity_id,
                document_refs_count=len(document_refs),
            )
            return True

        try:
            return await retry_with_backoff(
                self._do_update_entity,
                entity_id,
                document_refs,
            )
        except Exception as e:
            logger.error(
                "Failed to update entity after retries",
                entity_id=entity_id,
                error=str(e),
            )
            return False

    async def process_entity(self, entity: dict) -> bool:
        """
        Process a single entity to populate document_refs.

        Args:
            entity: Entity dictionary with id, chunk_refs, etc.

        Returns:
            True if entity was updated
        """
        entity_id = entity["id"]
        chunk_refs = entity.get("chunk_refs") or []
        existing_refs = entity.get("document_refs") or []

        # Skip if already has document refs (idempotency)
        if existing_refs and len(existing_refs) > 0:
            logger.debug("Entity already has document_refs, skipping", entity_id=entity_id)
            self.stats["entities_skipped"] += 1
            return False

        if not chunk_refs:
            logger.debug("Entity has no chunk_refs, skipping", entity_id=entity_id)
            self.stats["entities_skipped"] += 1
            return False

        # Get chunk metadata from PostgreSQL
        chunk_metadata = await self.get_chunk_metadata(chunk_refs)

        if not chunk_metadata:
            logger.warning(
                "No chunk metadata found",
                entity_id=entity_id,
                chunk_refs=chunk_refs,
            )
            self.stats["entities_skipped"] += 1
            return False

        # Extract document references from chunk metadata
        doc_refs_map: dict[str, DocumentReference] = {}
        for chunk in chunk_metadata:
            source = chunk.get("source", "")
            title = chunk.get("title", "")
            metadata = chunk.get("metadata", {})

            doc_ref = extract_document_metadata(source, title, metadata)

            # Aggregate by filename, incrementing mention_count
            if doc_ref.filename in doc_refs_map:
                existing = doc_refs_map[doc_ref.filename]
                doc_refs_map[doc_ref.filename] = DocumentReference(
                    filename=existing.filename,
                    company=existing.company or doc_ref.company,
                    quarter=existing.quarter or doc_ref.quarter,
                    year=existing.year or doc_ref.year,
                    mention_count=existing.mention_count + 1,
                )
            else:
                doc_refs_map[doc_ref.filename] = doc_ref

        # Convert to list of dicts for Neo4j
        document_refs = [ref.to_dict() for ref in doc_refs_map.values()]

        # Update entity
        success = await self.update_entity_document_refs(entity_id, document_refs)

        if success:
            self.stats["entities_updated"] += 1
            logger.debug(
                "Entity updated",
                entity_id=entity_id,
                document_refs_count=len(document_refs),
            )
        else:
            self.stats["errors"] += 1

        return success

    async def run(self, resume_from: str | None = None) -> dict:
        """
        Run the backfill process.

        Args:
            resume_from: Optional entity ID to resume from

        Returns:
            Statistics dictionary
        """
        logger.info("=" * 80)
        logger.info(
            "Starting document_refs backfill",
            batch_size=self.batch_size,
            dry_run=self.dry_run,
            resume_from=resume_from,
        )

        # Get total count
        self.stats["total_entities"] = await self.get_total_entity_count()
        logger.info("Total entities in graph", count=self.stats["total_entities"])

        offset = 0
        while True:
            # Fetch batch
            entities = await self.get_entity_batch(
                offset=offset,
                limit=self.batch_size,
                resume_from=resume_from if offset == 0 else None,
            )

            if not entities:
                break

            logger.info(
                "Processing batch",
                offset=offset,
                batch_size=len(entities),
                progress=f"{self.stats['entities_processed']}/{self.stats['total_entities']}",
            )

            # Process each entity in batch
            for entity in entities:
                try:
                    await self.process_entity(entity)
                    self.stats["entities_processed"] += 1
                except Exception as e:
                    logger.exception(
                        "Error processing entity",
                        entity_id=entity.get("id"),
                        error=str(e),
                    )
                    self.stats["errors"] += 1

            offset += len(entities)

            # Log progress
            if self.stats["entities_processed"] % 500 == 0:
                logger.info(
                    "Progress checkpoint",
                    processed=self.stats["entities_processed"],
                    updated=self.stats["entities_updated"],
                    skipped=self.stats["entities_skipped"],
                    errors=self.stats["errors"],
                )

        logger.info("=" * 80)
        logger.info(
            "Backfill complete",
            total_entities=self.stats["total_entities"],
            entities_processed=self.stats["entities_processed"],
            entities_updated=self.stats["entities_updated"],
            entities_skipped=self.stats["entities_skipped"],
            errors=self.stats["errors"],
        )

        return self.stats


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill document_refs property on Neo4j entities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of entities per batch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    parser.add_argument(
        "--resume-from",
        type=str,
        default=None,
        help="Entity ID to resume from (for interrupted runs)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


async def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Configure logging
    log_level = "DEBUG" if args.verbose else "INFO"
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, log_level, structlog.INFO)
        ),
    )

    logger.info(
        "Backfill script starting",
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        resume_from=args.resume_from,
    )

    # Initialize connection manager
    connection_manager = ConnectionManager()
    await connection_manager.initialize()

    try:
        # Run backfill
        backfill = DocumentRefBackfill(
            connection_manager=connection_manager,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
        stats = await backfill.run(resume_from=args.resume_from)

        # Return non-zero exit code if there were errors
        if stats["errors"] > 0:
            return 1
        return 0

    finally:
        await connection_manager.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
