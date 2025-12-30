#!/usr/bin/env python3
"""Backfill temporal metadata on existing Neo4j episodes and entities.

This script populates fiscal quarter, year, and document date properties
on Episode nodes by parsing their source document filenames. It also
calculates entity temporal spans (first/last document dates).

Usage:
    python scripts/backfill_temporal_metadata.py --dry-run
    python scripts/backfill_temporal_metadata.py --batch-size 500
    python scripts/backfill_temporal_metadata.py --entities-only

Options:
    --batch-size    Number of episodes to process per batch (default: 500)
    --dry-run       Preview changes without applying them
    --skip          Number of episodes to skip (for resumption)
    --verbose       Enable verbose logging
    --episodes-only Process only episodes, skip entity spans
    --entities-only Process only entity spans, skip episodes
"""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

import structlog

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agentic_rag.graph.temporal_parser import (  # noqa: E402
    extract_temporal_properties,
)
from src.agentic_rag.storage.connection_manager import ConnectionManager  # noqa: E402

logger = structlog.get_logger(__name__)


# Configuration constants
DEFAULT_BATCH_SIZE = 500
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

# Type variable for retry function
T = TypeVar("T")


async def retry_with_backoff(
    coro_func: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF_SECONDS,
    **kwargs: Any,
) -> T:
    """Execute a coroutine with exponential backoff retry logic.

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
    last_exception: Exception | None = None
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

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("Unexpected retry loop exit")


class TemporalMetadataBackfill:
    """
    Handles backfilling temporal metadata on episodes and entity temporal spans.

    This class provides idempotent updates - running multiple times
    will not create duplicates or corrupt data.
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        batch_size: int = DEFAULT_BATCH_SIZE,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        """
        Initialize the backfill handler.

        Args:
            connection_manager: Neo4j connection manager
            batch_size: Number of episodes to process per batch
            dry_run: If True, only preview changes without applying
            verbose: Enable verbose logging
        """
        self.connection_manager = connection_manager
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.verbose = verbose

        # Statistics
        self.episodes_processed = 0
        self.episodes_updated = 0
        self.episodes_skipped = 0
        self.entities_processed = 0
        self.entities_updated = 0
        self.errors = 0

    async def get_total_episode_count(self) -> int:
        """Get total count of episodes in the graph."""
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run("MATCH (e:Episode) RETURN count(e) as count")
            record = await result.single()
            return record["count"] if record else 0

    async def get_episodes_without_temporal(self, skip: int = 0) -> list[dict[str, Any]]:
        """
        Fetch a batch of episodes that need temporal metadata.

        Args:
            skip: Number of episodes to skip (for pagination)

        Returns:
            List of episode records with id and source_document
        """
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (ep:Episode)
                WHERE ep.fiscal_quarter IS NULL OR ep.fiscal_year IS NULL
                RETURN ep.id as id, ep.source_document as source_document
                ORDER BY ep.id
                SKIP $skip
                LIMIT $limit
                """,
                skip=skip,
                limit=self.batch_size,
            )

            episodes = []
            async for record in result:
                episodes.append(
                    {
                        "id": record["id"],
                        "source_document": record["source_document"],
                    }
                )

            return episodes

    async def get_all_episodes_batch(self, skip: int = 0) -> list[dict[str, Any]]:
        """
        Fetch a batch of all episodes (for idempotent updates).

        Args:
            skip: Number of episodes to skip (for pagination)

        Returns:
            List of episode records
        """
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (ep:Episode)
                RETURN ep.id as id, ep.source_document as source_document,
                       ep.fiscal_quarter as fiscal_quarter
                ORDER BY ep.id
                SKIP $skip
                LIMIT $limit
                """,
                skip=skip,
                limit=self.batch_size,
            )

            episodes = []
            async for record in result:
                episodes.append(
                    {
                        "id": record["id"],
                        "source_document": record["source_document"],
                        "fiscal_quarter": record["fiscal_quarter"],
                    }
                )

            return episodes

    async def update_episode_temporal(
        self,
        episode_id: str,
        temporal_props: dict[str, str | int | None],
    ) -> bool:
        """
        Update an episode with temporal properties.

        Args:
            episode_id: Episode node ID
            temporal_props: Temporal properties to set

        Returns:
            True if updated, False if skipped
        """
        if self.dry_run:
            logger.info(
                "DRY RUN: Would update episode",
                episode_id=episode_id,
                props=temporal_props,
            )
            return True

        async with self.connection_manager.get_neo4j_session() as session:
            await session.run(
                """
                MATCH (ep:Episode {id: $episode_id})
                SET ep.fiscal_quarter = $fiscal_quarter,
                    ep.fiscal_year = $fiscal_year,
                    ep.document_date = $document_date,
                    ep.company = $company
                """,
                episode_id=episode_id,
                fiscal_quarter=temporal_props["fiscal_quarter"],
                fiscal_year=temporal_props["fiscal_year"],
                document_date=temporal_props["document_date"],
                company=temporal_props["company"],
            )

        return True

    async def process_episodes(self, skip: int = 0) -> None:
        """
        Process all episodes to add temporal metadata.

        Args:
            skip: Number of episodes to skip initially
        """
        total_episodes = await self.get_total_episode_count()
        logger.info(
            "Starting episode temporal backfill",
            total_episodes=total_episodes,
            batch_size=self.batch_size,
            dry_run=self.dry_run,
            skip=skip,
        )

        current_skip = skip
        batch_num = 0

        while True:
            batch_num += 1
            episodes = await retry_with_backoff(self.get_all_episodes_batch, current_skip)

            if not episodes:
                logger.info("No more episodes to process")
                break

            logger.info(
                "Processing batch",
                batch=batch_num,
                episodes_in_batch=len(episodes),
                processed_so_far=self.episodes_processed,
            )

            for episode in episodes:
                self.episodes_processed += 1
                source_doc = episode.get("source_document") or ""

                # Extract temporal properties from source document filename
                # The source_document may be a full path or just a filename
                filename = Path(source_doc).name if source_doc else ""
                temporal_props = extract_temporal_properties(filename)

                if temporal_props["fiscal_quarter"] is None:
                    self.episodes_skipped += 1
                    if self.verbose:
                        logger.debug(
                            "Skipping episode - no temporal data extractable",
                            episode_id=episode["id"],
                            source_document=source_doc,
                        )
                    continue

                # Check if already has correct temporal data (idempotency)
                if (
                    episode.get("fiscal_quarter") == temporal_props["fiscal_quarter"]
                    and not self.dry_run
                ):
                    self.episodes_skipped += 1
                    continue

                try:
                    updated = await retry_with_backoff(
                        self.update_episode_temporal,
                        episode["id"],
                        temporal_props,
                    )
                    if updated:
                        self.episodes_updated += 1
                except Exception as e:
                    self.errors += 1
                    logger.error(
                        "Failed to update episode",
                        episode_id=episode["id"],
                        error=str(e),
                    )

            current_skip += self.batch_size

            # Progress log every batch
            progress = (self.episodes_processed / total_episodes * 100) if total_episodes > 0 else 0
            logger.info(
                "Batch complete",
                batch=batch_num,
                progress_pct=f"{progress:.1f}%",
                updated=self.episodes_updated,
                skipped=self.episodes_skipped,
                errors=self.errors,
            )

    async def calculate_entity_temporal_spans(self) -> None:
        """
        Calculate and update first/last document dates for all entities.

        This examines the episodes each entity is mentioned in and
        determines the earliest and latest document dates.
        """
        logger.info("Calculating entity temporal spans")

        async with self.connection_manager.get_neo4j_session() as session:
            # Get all entities with their episode document dates
            result = await session.run(
                """
                MATCH (e:Entity)-[:MENTIONED_IN]->(ep:Episode)
                WHERE ep.document_date IS NOT NULL
                WITH e, collect(DISTINCT ep.document_date) as dates
                RETURN e.id as entity_id,
                       e.name as entity_name,
                       dates
                """
            )

            entities_to_update = []
            async for record in result:
                dates = record["dates"]
                if not dates:
                    continue

                # Sort dates to find min/max
                sorted_dates = sorted(dates)
                first_date = sorted_dates[0]
                last_date = sorted_dates[-1]

                entities_to_update.append(
                    {
                        "entity_id": record["entity_id"],
                        "entity_name": record["entity_name"],
                        "first_document_date": first_date,
                        "last_document_date": last_date,
                        "date_count": len(dates),
                    }
                )

            logger.info(
                "Found entities with temporal data",
                count=len(entities_to_update),
            )

            # Update entities
            for entity in entities_to_update:
                self.entities_processed += 1

                if self.dry_run:
                    logger.info(
                        "DRY RUN: Would update entity temporal span",
                        entity_name=entity["entity_name"],
                        first_date=entity["first_document_date"],
                        last_date=entity["last_document_date"],
                    )
                    self.entities_updated += 1
                    continue

                try:
                    await session.run(
                        """
                        MATCH (e:Entity {id: $entity_id})
                        SET e.first_document_date = $first_date,
                            e.last_document_date = $last_date,
                            e.temporal_span_quarters = $date_count
                        """,
                        entity_id=entity["entity_id"],
                        first_date=entity["first_document_date"],
                        last_date=entity["last_document_date"],
                        date_count=entity["date_count"],
                    )
                    self.entities_updated += 1
                except Exception as e:
                    self.errors += 1
                    logger.error(
                        "Failed to update entity temporal span",
                        entity_id=entity["entity_id"],
                        error=str(e),
                    )

    def print_summary(self) -> None:
        """Print final summary statistics."""
        print("\n" + "=" * 60)
        print("TEMPORAL METADATA BACKFILL SUMMARY")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("-" * 60)
        print("Episodes:")
        print(f"  Processed:  {self.episodes_processed:,}")
        print(f"  Updated:    {self.episodes_updated:,}")
        print(f"  Skipped:    {self.episodes_skipped:,}")
        print("-" * 60)
        print("Entities:")
        print(f"  Processed:  {self.entities_processed:,}")
        print(f"  Updated:    {self.entities_updated:,}")
        print("-" * 60)
        print(f"Errors:       {self.errors}")
        print("=" * 60 + "\n")


async def verify_temporal_data(connection_manager: ConnectionManager) -> None:
    """
    Verify temporal data was populated correctly.

    Args:
        connection_manager: Neo4j connection manager
    """
    print("\nVERIFICATION QUERIES:")
    print("-" * 40)

    async with connection_manager.get_neo4j_session() as session:
        # Count episodes with temporal data
        result = await session.run(
            """
            MATCH (e:Episode)
            RETURN
                count(e) as total,
                count(e.fiscal_quarter) as with_quarter,
                count(e.fiscal_year) as with_year,
                count(e.document_date) as with_date
            """
        )
        record = await result.single()
        if record:
            print(f"Episodes total: {record['total']:,}")
            print(f"  with fiscal_quarter: {record['with_quarter']:,}")
            print(f"  with fiscal_year: {record['with_year']:,}")
            print(f"  with document_date: {record['with_date']:,}")

        # Count by quarter
        result = await session.run(
            """
            MATCH (e:Episode)
            WHERE e.fiscal_quarter IS NOT NULL
            RETURN e.fiscal_quarter as quarter, count(e) as count
            ORDER BY quarter
            """
        )
        print("\nEpisodes by quarter:")
        async for record in result:
            print(f"  {record['quarter']}: {record['count']:,}")

        # Count entities with temporal spans
        result = await session.run(
            """
            MATCH (e:Entity)
            WHERE e.first_document_date IS NOT NULL
            RETURN count(e) as count
            """
        )
        record = await result.single()
        if record:
            print(f"\nEntities with temporal spans: {record['count']:,}")


async def main() -> None:
    """Main entry point for the backfill script."""
    parser = argparse.ArgumentParser(
        description="Backfill temporal metadata on Neo4j episodes and entities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Episodes per batch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Number of episodes to skip (for resumption)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--episodes-only",
        action="store_true",
        help="Process only episodes, skip entity temporal spans",
    )
    parser.add_argument(
        "--entities-only",
        action="store_true",
        help="Process only entity temporal spans, skip episodes",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run verification queries after backfill",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = "DEBUG" if args.verbose else "INFO"
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, log_level.upper(), structlog.INFO)
        ),
    )

    logger.info(
        "Temporal metadata backfill starting",
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        skip=args.skip,
        episodes_only=args.episodes_only,
        entities_only=args.entities_only,
    )

    start_time = datetime.now()

    try:
        # Initialize connection
        connection_manager = await ConnectionManager.create()

        backfill = TemporalMetadataBackfill(
            connection_manager=connection_manager,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        # Process episodes
        if not args.entities_only:
            await backfill.process_episodes(skip=args.skip)

        # Calculate entity temporal spans
        if not args.episodes_only:
            await backfill.calculate_entity_temporal_spans()

        # Print summary
        backfill.print_summary()

        # Verification
        if args.verify and not args.dry_run:
            await verify_temporal_data(connection_manager)

        # Cleanup
        await connection_manager.close()

    except Exception as e:
        logger.exception("Backfill failed", error=str(e))
        sys.exit(1)

    elapsed = datetime.now() - start_time
    logger.info(
        "Temporal metadata backfill complete",
        elapsed_seconds=elapsed.total_seconds(),
    )


if __name__ == "__main__":
    asyncio.run(main())
