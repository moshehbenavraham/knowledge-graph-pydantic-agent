#!/usr/bin/env python3
"""
Backfill relationship strength scores on existing Neo4j relationships.

This script recalculates and updates the strength property on all existing
relationships in the Neo4j knowledge graph using the evidence-based scoring
function. It considers chunk count, relationship type priority, and entity
importance scores.

Usage:
    python scripts/backfill_relationship_scores.py --batch-size 500 --dry-run
    python scripts/backfill_relationship_scores.py --batch-size 500

Options:
    --batch-size    Number of relationships to process per batch (default: 500)
    --dry-run       Preview changes without applying them
    --skip          Number of relationships to skip (for resumption)
    --verbose       Enable verbose logging
    --stats-only    Only show current statistics, don't update anything
"""

import argparse
import asyncio
import sys
from pathlib import Path

import structlog
from neo4j import AsyncGraphDatabase

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agentic_rag.graph.relationship_scoring import (  # noqa: E402
    ScoringConfig,
    calculate_relationship_strength,
)
from src.config import get_settings  # noqa: E402

logger = structlog.get_logger(__name__)


# Configuration constants
DEFAULT_BATCH_SIZE = 500
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


class RelationshipScoreBackfill:
    """
    Handles backfilling relationship strength scores.

    Processes relationships in batches, calculating dynamic strength scores
    based on chunk count, relationship type, and entity importance.
    """

    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the backfill handler.

        Args:
            batch_size: Number of relationships per batch
            dry_run: If True, preview changes without applying
            verbose: Enable detailed logging
        """
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.verbose = verbose
        self.config = ScoringConfig()
        self.driver = None

        # Statistics
        self.stats = {
            "total_relationships": 0,
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "score_distribution": {
                "0.0-0.2": 0,
                "0.2-0.4": 0,
                "0.4-0.6": 0,
                "0.6-0.8": 0,
                "0.8-1.0": 0,
            },
        }

    async def initialize(self) -> None:
        """Initialize Neo4j connection."""
        settings = get_settings()
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("Neo4j connection initialized")

    async def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")

    async def get_total_count(self) -> int:
        """Get total number of relationships to process."""
        async with self.driver.session() as session:
            result = await session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
            record = await result.single()
            return record["count"] if record else 0

    async def get_current_stats(self) -> dict:
        """Get current relationship statistics."""
        async with self.driver.session() as session:
            # Overall count
            result = await session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
            record = await result.single()
            total = record["count"] if record else 0

            # Strength distribution
            result = await session.run(
                """
                MATCH ()-[r:RELATED_TO]->()
                RETURN
                    count(CASE WHEN r.strength >= 0.0 AND r.strength < 0.2 THEN 1 END) as low,
                    count(CASE WHEN r.strength >= 0.2 AND r.strength < 0.4 THEN 1 END) as med_low,
                    count(CASE WHEN r.strength >= 0.4 AND r.strength < 0.6 THEN 1 END) as medium,
                    count(CASE WHEN r.strength >= 0.6 AND r.strength < 0.8 THEN 1 END) as med_high,
                    count(CASE WHEN r.strength >= 0.8 AND r.strength <= 1.0 THEN 1 END) as high,
                    avg(r.strength) as avg_strength,
                    min(r.strength) as min_strength,
                    max(r.strength) as max_strength
                """
            )
            record = await result.single()

            # Type distribution
            type_result = await session.run(
                """
                MATCH ()-[r:RELATED_TO]->()
                RETURN r.type as type, count(*) as count, avg(r.strength) as avg_strength
                ORDER BY count DESC
                """
            )
            types = []
            async for rec in type_result:
                types.append(
                    {
                        "type": rec["type"],
                        "count": rec["count"],
                        "avg_strength": rec["avg_strength"],
                    }
                )

            return {
                "total": total,
                "strength_distribution": {
                    "0.0-0.2": record["low"],
                    "0.2-0.4": record["med_low"],
                    "0.4-0.6": record["medium"],
                    "0.6-0.8": record["med_high"],
                    "0.8-1.0": record["high"],
                },
                "avg_strength": record["avg_strength"],
                "min_strength": record["min_strength"],
                "max_strength": record["max_strength"],
                "types": types,
            }

    async def fetch_batch(self, skip: int) -> list[dict]:
        """
        Fetch a batch of relationships with their entity data.

        Args:
            skip: Number of relationships to skip

        Returns:
            List of relationship data dictionaries
        """
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e1:Entity)-[r:RELATED_TO]->(e2:Entity)
                RETURN
                    elementId(r) as rel_id,
                    r.type as rel_type,
                    r.strength as current_strength,
                    r.source_chunks as source_chunks,
                    e1.name as entity1_name,
                    e1.importance_score as entity1_importance,
                    e2.name as entity2_name,
                    e2.importance_score as entity2_importance
                ORDER BY rel_id
                SKIP $skip
                LIMIT $limit
                """,
                skip=skip,
                limit=self.batch_size,
            )

            relationships = []
            async for record in result:
                relationships.append(
                    {
                        "rel_id": record["rel_id"],
                        "rel_type": record["rel_type"],
                        "current_strength": record["current_strength"],
                        "source_chunks": record["source_chunks"] or [],
                        "entity1_name": record["entity1_name"],
                        "entity1_importance": record["entity1_importance"],
                        "entity2_name": record["entity2_name"],
                        "entity2_importance": record["entity2_importance"],
                    }
                )

            return relationships

    def calculate_new_strength(self, rel_data: dict) -> float:
        """
        Calculate new strength score for a relationship.

        Args:
            rel_data: Relationship data dictionary

        Returns:
            Calculated strength score (0.0-1.0)
        """
        chunk_count = len(rel_data["source_chunks"])
        return calculate_relationship_strength(
            chunk_count=chunk_count,
            relationship_type=rel_data["rel_type"],
            entity1_importance=rel_data["entity1_importance"],
            entity2_importance=rel_data["entity2_importance"],
            config=self.config,
        )

    def _update_score_distribution(self, strength: float) -> None:
        """Update score distribution statistics."""
        if strength < 0.2:
            self.stats["score_distribution"]["0.0-0.2"] += 1
        elif strength < 0.4:
            self.stats["score_distribution"]["0.2-0.4"] += 1
        elif strength < 0.6:
            self.stats["score_distribution"]["0.4-0.6"] += 1
        elif strength < 0.8:
            self.stats["score_distribution"]["0.6-0.8"] += 1
        else:
            self.stats["score_distribution"]["0.8-1.0"] += 1

    async def update_batch(self, relationships: list[dict]) -> int:
        """
        Update strength scores for a batch of relationships.

        Args:
            relationships: List of relationship data with new scores

        Returns:
            Number of relationships updated
        """
        if self.dry_run:
            return len(relationships)

        async with self.driver.session() as session:
            # Use UNWIND for batch update efficiency
            updates = [
                {"rel_id": r["rel_id"], "new_strength": r["new_strength"]} for r in relationships
            ]

            result = await session.run(
                """
                UNWIND $updates as update
                MATCH ()-[r:RELATED_TO]->()
                WHERE elementId(r) = update.rel_id
                SET r.strength = update.new_strength,
                    r.strength_updated_at = datetime()
                RETURN count(r) as updated
                """,
                updates=updates,
            )
            record = await result.single()
            return record["updated"] if record else 0

    async def run(self, skip: int = 0) -> dict:
        """
        Run the backfill process.

        Args:
            skip: Number of relationships to skip

        Returns:
            Statistics dictionary
        """
        logger.info("=" * 80)
        logger.info("RELATIONSHIP SCORE BACKFILL STARTING")
        logger.info("=" * 80)

        await self.initialize()

        try:
            self.stats["total_relationships"] = await self.get_total_count()
            logger.info(
                "Total relationships to process",
                total=self.stats["total_relationships"],
                batch_size=self.batch_size,
                dry_run=self.dry_run,
            )

            if self.stats["total_relationships"] == 0:
                logger.info("No relationships found to process")
                return self.stats

            current_skip = skip
            batch_num = 0

            while True:
                batch_num += 1

                # Fetch batch with retry
                relationships = await retry_with_backoff(self.fetch_batch, current_skip)

                if not relationships:
                    logger.info("No more relationships to process")
                    break

                logger.info(
                    f"Processing batch {batch_num}",
                    batch_size=len(relationships),
                    skip=current_skip,
                )

                # Calculate new scores
                updates_to_apply = []
                for rel in relationships:
                    self.stats["processed"] += 1

                    try:
                        new_strength = self.calculate_new_strength(rel)
                        old_strength = rel["current_strength"] or 0.5

                        # Track score change
                        if abs(new_strength - old_strength) > 0.001:
                            rel["new_strength"] = new_strength
                            updates_to_apply.append(rel)
                            self._update_score_distribution(new_strength)

                            if self.verbose:
                                logger.debug(
                                    "Score updated",
                                    entity1=rel["entity1_name"][:30],
                                    entity2=rel["entity2_name"][:30],
                                    rel_type=rel["rel_type"],
                                    old_strength=f"{old_strength:.3f}",
                                    new_strength=f"{new_strength:.3f}",
                                    chunk_count=len(rel["source_chunks"]),
                                )
                        else:
                            self.stats["skipped"] += 1

                    except Exception as e:
                        self.stats["errors"] += 1
                        logger.error(
                            "Error calculating score",
                            rel_id=rel["rel_id"],
                            error=str(e),
                        )

                # Apply updates with retry
                if updates_to_apply:
                    try:
                        updated = await retry_with_backoff(self.update_batch, updates_to_apply)
                        self.stats["updated"] += updated
                        logger.info(
                            f"Batch {batch_num} complete",
                            updated=updated,
                            total_updated=self.stats["updated"],
                            progress=f"{self.stats['processed']}/{self.stats['total_relationships']}",
                        )
                    except Exception as e:
                        self.stats["errors"] += len(updates_to_apply)
                        logger.error(f"Batch update failed: {e}")
                else:
                    logger.info(f"Batch {batch_num}: no updates needed")

                current_skip += len(relationships)

                # Progress update every 5 batches
                if batch_num % 5 == 0:
                    progress_pct = (
                        self.stats["processed"] / self.stats["total_relationships"]
                    ) * 100
                    logger.info(
                        f"Progress: {progress_pct:.1f}%",
                        processed=self.stats["processed"],
                        updated=self.stats["updated"],
                        errors=self.stats["errors"],
                    )

        finally:
            await self.close()

        # Final summary
        logger.info("=" * 80)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 80)
        logger.info(
            "Final statistics",
            total=self.stats["total_relationships"],
            processed=self.stats["processed"],
            updated=self.stats["updated"],
            skipped=self.stats["skipped"],
            errors=self.stats["errors"],
            dry_run=self.dry_run,
        )
        logger.info(
            "Score distribution",
            distribution=self.stats["score_distribution"],
        )

        return self.stats


async def show_stats_only():
    """Display current relationship statistics without updating."""
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    try:
        backfill = RelationshipScoreBackfill()
        backfill.driver = driver
        stats = await backfill.get_current_stats()

        print("\n" + "=" * 60)
        print("CURRENT RELATIONSHIP STATISTICS")
        print("=" * 60)
        print(f"\nTotal relationships: {stats['total']}")
        print(f"Average strength: {stats['avg_strength']:.4f}")
        print(f"Min strength: {stats['min_strength']:.4f}")
        print(f"Max strength: {stats['max_strength']:.4f}")

        print("\nStrength Distribution:")
        for range_name, count in stats["strength_distribution"].items():
            pct = (count / stats["total"] * 100) if stats["total"] > 0 else 0
            bar = "#" * int(pct / 2)
            print(f"  {range_name}: {count:6d} ({pct:5.1f}%) {bar}")

        print("\nRelationship Types:")
        for t in stats["types"][:10]:
            avg = t["avg_strength"] or 0
            print(f"  {t['type']:20s}: {t['count']:6d} (avg: {avg:.3f})")

        print("=" * 60 + "\n")

    finally:
        await driver.close()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Backfill relationship strength scores in Neo4j")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of relationships per batch (default: {DEFAULT_BATCH_SIZE})",
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
        help="Number of relationships to skip (for resumption)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show current statistics",
    )

    args = parser.parse_args()

    # Configure logging
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            10 if args.verbose else 20  # DEBUG or INFO
        ),
    )

    if args.stats_only:
        await show_stats_only()
        return

    backfill = RelationshipScoreBackfill(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    stats = await backfill.run(skip=args.skip)

    # Exit with error code if there were errors
    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
