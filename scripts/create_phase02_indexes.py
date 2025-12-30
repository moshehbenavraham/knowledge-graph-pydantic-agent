#!/usr/bin/env python3
"""
Neo4j index creation script for Phase 02 query optimization.

Creates indexes optimized for multi-hop, temporal, and comparison query patterns.
All indexes are idempotent (CREATE INDEX IF NOT EXISTS).

Usage:
    python scripts/create_phase02_indexes.py [--dry-run] [--verify]

Options:
    --dry-run   Print Cypher statements without executing
    --verify    Verify indexes after creation
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ClientError

from src.config import get_settings

logger = structlog.get_logger(__name__)


# Index definitions for Phase 02 query patterns
PHASE02_INDEXES = [
    # Entity indexes for fast lookups
    {
        "name": "entity_name_idx",
        "statement": "CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name)",
        "description": "Entity name lookup index",
    },
    {
        "name": "entity_type_idx",
        "statement": "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
        "description": "Entity type filter index",
    },
    {
        "name": "entity_name_type_idx",
        "statement": (
            "CREATE INDEX entity_name_type_idx IF NOT EXISTS "
            "FOR (e:Entity) ON (e.name, e.entity_type)"
        ),
        "description": "Composite entity name+type index",
    },
    # Temporal indexes for trend queries
    {
        "name": "fact_valid_from_idx",
        "statement": "CREATE INDEX fact_valid_from_idx IF NOT EXISTS FOR (f:Fact) ON (f.valid_from)",
        "description": "Fact temporal start index",
    },
    {
        "name": "fact_valid_to_idx",
        "statement": "CREATE INDEX fact_valid_to_idx IF NOT EXISTS FOR (f:Fact) ON (f.valid_to)",
        "description": "Fact temporal end index",
    },
    {
        "name": "fact_created_at_idx",
        "statement": "CREATE INDEX fact_created_at_idx IF NOT EXISTS FOR (f:Fact) ON (f.created_at)",
        "description": "Fact creation timestamp index",
    },
    # Relationship indexes for multi-hop traversal
    {
        "name": "rel_strength_idx",
        "statement": (
            "CREATE INDEX rel_strength_idx IF NOT EXISTS "
            "FOR ()-[r:RELATES_TO]-() ON (r.strength)"
        ),
        "description": "Relationship strength index for path filtering",
    },
    {
        "name": "rel_type_idx",
        "statement": (
            "CREATE INDEX rel_type_idx IF NOT EXISTS "
            "FOR ()-[r:RELATES_TO]-() ON (r.relationship_type)"
        ),
        "description": "Relationship type index",
    },
    # Numeric fact indexes for comparison queries
    {
        "name": "numeric_fact_value_idx",
        "statement": (
            "CREATE INDEX numeric_fact_value_idx IF NOT EXISTS " "FOR (f:NumericFact) ON (f.value)"
        ),
        "description": "Numeric fact value index for comparisons",
    },
    {
        "name": "numeric_fact_metric_idx",
        "statement": (
            "CREATE INDEX numeric_fact_metric_idx IF NOT EXISTS "
            "FOR (f:NumericFact) ON (f.metric_name)"
        ),
        "description": "Numeric fact metric name index",
    },
    {
        "name": "numeric_fact_entity_idx",
        "statement": (
            "CREATE INDEX numeric_fact_entity_idx IF NOT EXISTS "
            "FOR (f:NumericFact) ON (f.entity_name)"
        ),
        "description": "Numeric fact entity lookup index",
    },
    # Full-text search index for entity names
    {
        "name": "entity_fulltext_idx",
        "statement": (
            "CREATE FULLTEXT INDEX entity_fulltext_idx IF NOT EXISTS "
            "FOR (e:Entity) ON EACH [e.name, e.description]"
        ),
        "description": "Full-text search on entity names and descriptions",
    },
    # Document reference indexes
    {
        "name": "entity_doc_refs_idx",
        "statement": (
            "CREATE INDEX entity_doc_refs_idx IF NOT EXISTS " "FOR (e:Entity) ON (e.document_refs)"
        ),
        "description": "Entity document references index",
    },
]


async def create_indexes(
    driver: AsyncGraphDatabase,
    dry_run: bool = False,
) -> dict[str, bool]:
    """
    Create all Phase 02 indexes.

    Args:
        driver: Neo4j async driver
        dry_run: If True, only print statements without executing

    Returns:
        Dictionary of index name to success status
    """
    results: dict[str, bool] = {}

    async with driver.session() as session:
        for index in PHASE02_INDEXES:
            name = index["name"]
            statement = index["statement"]
            description = index["description"]

            if dry_run:
                logger.info(
                    "DRY RUN - Would create index",
                    index_name=name,
                    description=description,
                    statement=statement,
                )
                results[name] = True
                continue

            try:
                await session.run(statement)
                logger.info(
                    "Index created successfully",
                    index_name=name,
                    description=description,
                )
                results[name] = True
            except ClientError as e:
                if "already exists" in str(e).lower():
                    logger.info(
                        "Index already exists",
                        index_name=name,
                    )
                    results[name] = True
                else:
                    logger.error(
                        "Failed to create index",
                        index_name=name,
                        error=str(e),
                    )
                    results[name] = False

    return results


async def verify_indexes(driver: AsyncGraphDatabase) -> dict[str, bool]:
    """
    Verify all Phase 02 indexes exist.

    Args:
        driver: Neo4j async driver

    Returns:
        Dictionary of index name to existence status
    """
    results: dict[str, bool] = {}

    async with driver.session() as session:
        # Query all indexes
        result = await session.run("SHOW INDEXES")
        records = [record async for record in result]
        existing_indexes = {record["name"] for record in records}

        for index in PHASE02_INDEXES:
            name = index["name"]
            exists = name in existing_indexes
            results[name] = exists

            if exists:
                logger.info("Index verified", index_name=name)
            else:
                logger.warning("Index missing", index_name=name)

    return results


async def show_index_stats(driver: AsyncGraphDatabase) -> None:
    """
    Display index statistics.

    Args:
        driver: Neo4j async driver
    """
    async with driver.session() as session:
        result = await session.run(
            """
            SHOW INDEXES
            YIELD name, type, state, populationPercent
            WHERE name STARTS WITH 'entity_' OR name STARTS WITH 'fact_'
               OR name STARTS WITH 'rel_' OR name STARTS WITH 'numeric_'
            RETURN name, type, state, populationPercent
            ORDER BY name
            """
        )
        records = [record async for record in result]

        if records:
            print("\nPhase 02 Index Statistics:")
            print("-" * 60)
            print(f"{'Name':<30} {'Type':<12} {'State':<10} {'Population'}")
            print("-" * 60)
            for record in records:
                print(
                    f"{record['name']:<30} "
                    f"{record['type']:<12} "
                    f"{record['state']:<10} "
                    f"{record['populationPercent']:.1f}%"
                )
        else:
            print("\nNo Phase 02 indexes found.")


async def main(dry_run: bool = False, verify: bool = False) -> int:
    """
    Main entry point.

    Args:
        dry_run: Print statements without executing
        verify: Verify indexes after creation

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    settings = get_settings()

    logger.info(
        "Starting Phase 02 index creation",
        neo4j_uri=settings.neo4j_uri,
        dry_run=dry_run,
        verify=verify,
    )

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    try:
        # Verify connectivity
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS test")
            await result.single()
        logger.info("Neo4j connection verified")

        # Create indexes
        results = await create_indexes(driver, dry_run=dry_run)

        # Count results
        success_count = sum(1 for v in results.values() if v)
        fail_count = sum(1 for v in results.values() if not v)

        logger.info(
            "Index creation complete",
            total=len(results),
            success=success_count,
            failed=fail_count,
        )

        # Verify if requested
        if verify and not dry_run:
            logger.info("Verifying indexes...")
            verify_results = await verify_indexes(driver)
            verified_count = sum(1 for v in verify_results.values() if v)
            logger.info(
                "Verification complete",
                verified=verified_count,
                total=len(verify_results),
            )
            await show_index_stats(driver)

        return 0 if fail_count == 0 else 1

    except Exception as e:
        logger.exception("Index creation failed", error=str(e))
        return 1

    finally:
        await driver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create Neo4j indexes for Phase 02 query optimization"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print Cypher statements without executing",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify indexes after creation",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(dry_run=args.dry_run, verify=args.verify))
    sys.exit(exit_code)
