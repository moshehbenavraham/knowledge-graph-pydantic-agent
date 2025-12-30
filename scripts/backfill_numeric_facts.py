#!/usr/bin/env python3
"""Backfill numeric facts on existing Neo4j episodes.

This script parses episode text (fact field) to extract numeric values
(currency amounts, percentages) and stores them in the Episode.numeric_facts
property for range-based queries.

Usage:
    python scripts/backfill_numeric_facts.py --dry-run
    python scripts/backfill_numeric_facts.py --batch-size 500
    python scripts/backfill_numeric_facts.py --verbose

Options:
    --batch-size    Number of episodes to process per batch (default: 500)
    --dry-run       Preview changes without applying them
    --skip          Number of episodes to skip (for resumption)
    --verbose       Enable verbose logging
    --verify        Run verification queries after backfill

Example:
    # Preview what would be updated
    python scripts/backfill_numeric_facts.py --dry-run --verbose

    # Run full backfill with verification
    python scripts/backfill_numeric_facts.py --verify
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

from src.agentic_rag.graph.numeric_parser import (  # noqa: E402
    extract_numeric_facts_json,
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


class NumericFactsBackfill:
    """
    Handles backfilling numeric facts on existing episodes.

    This class provides idempotent updates - running multiple times
    will overwrite existing numeric_facts with fresh extractions.
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
        self.total_facts_extracted = 0
        self.errors = 0

    async def get_total_episode_count(self) -> int:
        """Get total count of episodes in the graph."""
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run("MATCH (e:Episode) RETURN count(e) as count")
            record = await result.single()
            return record["count"] if record else 0

    async def get_episodes_batch(self, skip: int = 0) -> list[dict[str, Any]]:
        """
        Fetch a batch of episodes for processing.

        Args:
            skip: Number of episodes to skip (for pagination)

        Returns:
            List of episode records with id and fact text
        """
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (ep:Episode)
                WHERE ep.fact IS NOT NULL AND ep.fact <> ''
                RETURN ep.id as id, ep.fact as fact, ep.numeric_facts as existing_facts
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
                        "fact": record["fact"],
                        "existing_facts": record["existing_facts"],
                    }
                )

            return episodes

    async def update_episode_numeric_facts(
        self,
        episode_id: str,
        numeric_facts: list[dict[str, Any]],
    ) -> bool:
        """
        Update an episode with extracted numeric facts.

        Args:
            episode_id: Episode node ID
            numeric_facts: List of numeric fact dictionaries

        Returns:
            True if updated, False if skipped
        """
        if self.dry_run:
            logger.info(
                "DRY RUN: Would update episode",
                episode_id=episode_id,
                facts_count=len(numeric_facts),
                facts_preview=numeric_facts[:2] if numeric_facts else [],
            )
            return True

        async with self.connection_manager.get_neo4j_session() as session:
            await session.run(
                """
                MATCH (ep:Episode {id: $episode_id})
                SET ep.numeric_facts = $numeric_facts,
                    ep.numeric_facts_updated = datetime()
                """,
                episode_id=episode_id,
                numeric_facts=numeric_facts,
            )

        return True

    async def process_episodes(self, skip: int = 0) -> None:
        """
        Process all episodes to extract and store numeric facts.

        Args:
            skip: Number of episodes to skip initially
        """
        total_episodes = await self.get_total_episode_count()
        logger.info(
            "Starting numeric facts backfill",
            total_episodes=total_episodes,
            batch_size=self.batch_size,
            dry_run=self.dry_run,
            skip=skip,
        )

        current_skip = skip
        batch_num = 0

        while True:
            batch_num += 1
            episodes = await retry_with_backoff(self.get_episodes_batch, current_skip)

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
                fact_text = episode.get("fact") or ""

                # Skip if no fact text
                if not fact_text.strip():
                    self.episodes_skipped += 1
                    continue

                # Extract numeric facts from episode text
                numeric_facts = extract_numeric_facts_json(fact_text)

                if not numeric_facts:
                    self.episodes_skipped += 1
                    if self.verbose:
                        logger.debug(
                            "No numeric facts found in episode",
                            episode_id=episode["id"],
                            fact_preview=fact_text[:100],
                        )
                    continue

                try:
                    updated = await retry_with_backoff(
                        self.update_episode_numeric_facts,
                        episode["id"],
                        numeric_facts,
                    )
                    if updated:
                        self.episodes_updated += 1
                        self.total_facts_extracted += len(numeric_facts)

                        if self.verbose:
                            logger.debug(
                                "Episode updated with numeric facts",
                                episode_id=episode["id"],
                                facts_count=len(numeric_facts),
                            )
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
                total_facts=self.total_facts_extracted,
                errors=self.errors,
            )

    def print_summary(self) -> None:
        """Print final summary statistics."""
        print("\n" + "=" * 60)
        print("NUMERIC FACTS BACKFILL SUMMARY")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("-" * 60)
        print("Episodes:")
        print(f"  Processed:  {self.episodes_processed:,}")
        print(f"  Updated:    {self.episodes_updated:,}")
        print(f"  Skipped:    {self.episodes_skipped:,}")
        print("-" * 60)
        print("Numeric Facts:")
        print(f"  Total Extracted:  {self.total_facts_extracted:,}")
        if self.episodes_updated > 0:
            avg_facts = self.total_facts_extracted / self.episodes_updated
            print(f"  Avg per Episode:  {avg_facts:.2f}")
        print("-" * 60)
        print(f"Errors:       {self.errors}")
        print("=" * 60 + "\n")


async def verify_numeric_facts(connection_manager: ConnectionManager) -> None:
    """
    Verify numeric facts were populated correctly.

    Args:
        connection_manager: Neo4j connection manager
    """
    print("\nVERIFICATION QUERIES:")
    print("-" * 40)

    async with connection_manager.get_neo4j_session() as session:
        # Count episodes with numeric facts
        result = await session.run(
            """
            MATCH (e:Episode)
            RETURN
                count(e) as total,
                count(e.numeric_facts) as with_facts
            """
        )
        record = await result.single()
        if record:
            print(f"Episodes total: {record['total']:,}")
            print(f"  with numeric_facts: {record['with_facts']:,}")

        # Count by fact type
        result = await session.run(
            """
            MATCH (e:Episode)
            WHERE e.numeric_facts IS NOT NULL
            UNWIND e.numeric_facts as fact
            RETURN fact.fact_type as fact_type, count(*) as count
            ORDER BY count DESC
            """
        )
        print("\nFacts by type:")
        async for record in result:
            print(f"  {record['fact_type']}: {record['count']:,}")

        # Sample high-value facts
        result = await session.run(
            """
            MATCH (e:Episode)
            WHERE e.numeric_facts IS NOT NULL
            UNWIND e.numeric_facts as fact
            WHERE fact.fact_type = 'currency' AND fact.value > 1000000000
            RETURN e.fact as episode_fact, fact.original_text as original, fact.value as value
            ORDER BY fact.value DESC
            LIMIT 5
            """
        )
        print("\nTop 5 currency facts (>$1B):")
        async for record in result:
            value_b = record["value"] / 1e9
            print(f"  ${value_b:.2f}B - '{record['original']}'")


async def main() -> None:
    """Main entry point for the backfill script."""
    parser = argparse.ArgumentParser(
        description="Backfill numeric facts on Neo4j episodes",
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
        "Numeric facts backfill starting",
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        skip=args.skip,
    )

    start_time = datetime.now()

    try:
        # Initialize connection
        connection_manager = ConnectionManager()

        backfill = NumericFactsBackfill(
            connection_manager=connection_manager,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        # Process episodes
        await backfill.process_episodes(skip=args.skip)

        # Print summary
        backfill.print_summary()

        # Verification
        if args.verify and not args.dry_run:
            await verify_numeric_facts(connection_manager)

        # Cleanup
        await connection_manager.close()

    except Exception as e:
        logger.exception("Backfill failed", error=str(e))
        sys.exit(1)

    elapsed = datetime.now() - start_time
    logger.info(
        "Numeric facts backfill complete",
        elapsed_seconds=elapsed.total_seconds(),
    )


if __name__ == "__main__":
    asyncio.run(main())
