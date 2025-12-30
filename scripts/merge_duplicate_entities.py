#!/usr/bin/env python3
"""Entity deduplication merge script with dry-run, interactive, and batch modes.

This script identifies duplicate entities in the Neo4j knowledge graph and
provides options to merge them while preserving all relationships.

Usage:
    # Dry run - show what would be merged
    python scripts/merge_duplicate_entities.py --dry-run

    # Interactive mode - confirm each merge
    python scripts/merge_duplicate_entities.py --interactive

    # Batch mode - merge all with progress reporting
    python scripts/merge_duplicate_entities.py --batch

    # Custom fuzzy threshold
    python scripts/merge_duplicate_entities.py --threshold 85 --batch

    # Limit number of merges
    python scripts/merge_duplicate_entities.py --batch --limit 100
"""

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import structlog

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase

from src.agentic_rag.entity_resolution.deduplication import (
    DEFAULT_FUZZY_THRESHOLD,
    DuplicateGroup,
    Entity,
    find_duplicates,
)
from src.agentic_rag.entity_resolution.merge_history import (
    MergedEntity,
    MergeHistory,
    MergeOperation,
    MergeStatus,
)
from src.config import get_settings

logger = structlog.get_logger(__name__)


async def get_relationship_count(driver: Any, entity_id: str) -> int:
    """Get the number of relationships for an entity.

    Args:
        driver: Neo4j async driver
        entity_id: UUID of the entity

    Returns:
        Count of relationships (both directions)
    """
    query = """
    MATCH (e:Entity {uuid: $entity_id})-[r]-()
    RETURN count(r) AS count
    """
    async with driver.session() as session:
        result = await session.run(query, entity_id=entity_id)
        record = await result.single()
        return int(record["count"]) if record else 0


async def transfer_relationships(
    driver: Any,
    source_id: str,
    target_id: str,
) -> int:
    """Transfer all relationships from source entity to target entity.

    Handles both incoming and outgoing relationships. Skips self-loops
    that would be created by merging.

    Args:
        driver: Neo4j async driver
        source_id: UUID of the entity to merge from
        target_id: UUID of the entity to merge into

    Returns:
        Number of relationships transferred
    """
    logger.debug(
        "Transferring relationships",
        source_id=source_id,
        target_id=target_id,
    )

    transferred = 0

    async with driver.session() as session:
        # Transfer outgoing relationships
        outgoing_query = """
        MATCH (source:Entity {uuid: $source_id})-[r]->(other)
        WHERE other.uuid <> $target_id
        WITH source, r, other, type(r) AS rel_type, properties(r) AS props
        MATCH (target:Entity {uuid: $target_id})
        CALL apoc.create.relationship(target, rel_type, props, other) YIELD rel
        DELETE r
        RETURN count(rel) AS count
        """

        try:
            result = await session.run(outgoing_query, source_id=source_id, target_id=target_id)
            record = await result.single()
            if record:
                transferred += int(record["count"])
        except Exception as e:
            # Fall back to manual transfer if APOC not available
            logger.debug("APOC not available, using manual transfer", error=str(e))
            transferred += await _manual_transfer_outgoing(session, source_id, target_id)

        # Transfer incoming relationships
        incoming_query = """
        MATCH (other)-[r]->(source:Entity {uuid: $source_id})
        WHERE other.uuid <> $target_id
        WITH source, r, other, type(r) AS rel_type, properties(r) AS props
        MATCH (target:Entity {uuid: $target_id})
        CALL apoc.create.relationship(other, rel_type, props, target) YIELD rel
        DELETE r
        RETURN count(rel) AS count
        """

        try:
            result = await session.run(incoming_query, source_id=source_id, target_id=target_id)
            record = await result.single()
            if record:
                transferred += int(record["count"])
        except Exception:
            transferred += await _manual_transfer_incoming(session, source_id, target_id)

    logger.debug("Relationships transferred", count=transferred)
    return transferred


async def _manual_transfer_outgoing(session: Any, source_id: str, target_id: str) -> int:
    """Manually transfer outgoing relationships without APOC.

    Args:
        session: Neo4j session
        source_id: Source entity UUID
        target_id: Target entity UUID

    Returns:
        Number of relationships transferred
    """
    # Get outgoing relationships
    query = """
    MATCH (source:Entity {uuid: $source_id})-[r]->(other)
    WHERE other.uuid <> $target_id
    RETURN type(r) AS rel_type, properties(r) AS props, other.uuid AS other_id
    """
    result = await session.run(query, source_id=source_id, target_id=target_id)
    records = [record async for record in result]

    transferred = 0
    for record in records:
        rel_type = record["rel_type"]
        props = dict(record["props"]) if record["props"] else {}
        other_id = record["other_id"]

        # Create new relationship
        create_query = f"""
        MATCH (target:Entity {{uuid: $target_id}}), (other:Entity {{uuid: $other_id}})
        CREATE (target)-[r:{rel_type} $props]->(other)
        RETURN r
        """
        await session.run(create_query, target_id=target_id, other_id=other_id, props=props)
        transferred += 1

    # Delete old relationships
    delete_query = """
    MATCH (source:Entity {uuid: $source_id})-[r]->()
    DELETE r
    """
    await session.run(delete_query, source_id=source_id)

    return transferred


async def _manual_transfer_incoming(session: Any, source_id: str, target_id: str) -> int:
    """Manually transfer incoming relationships without APOC.

    Args:
        session: Neo4j session
        source_id: Source entity UUID
        target_id: Target entity UUID

    Returns:
        Number of relationships transferred
    """
    # Get incoming relationships
    query = """
    MATCH (other)-[r]->(source:Entity {uuid: $source_id})
    WHERE other.uuid <> $target_id
    RETURN type(r) AS rel_type, properties(r) AS props, other.uuid AS other_id
    """
    result = await session.run(query, source_id=source_id, target_id=target_id)
    records = [record async for record in result]

    transferred = 0
    for record in records:
        rel_type = record["rel_type"]
        props = dict(record["props"]) if record["props"] else {}
        other_id = record["other_id"]

        # Create new relationship
        create_query = f"""
        MATCH (other:Entity {{uuid: $other_id}}), (target:Entity {{uuid: $target_id}})
        CREATE (other)-[r:{rel_type} $props]->(target)
        RETURN r
        """
        await session.run(create_query, target_id=target_id, other_id=other_id, props=props)
        transferred += 1

    # Delete old relationships
    delete_query = """
    MATCH ()-[r]->(source:Entity {uuid: $source_id})
    DELETE r
    """
    await session.run(delete_query, source_id=source_id)

    return transferred


async def merge_entity(
    driver: Any,
    canonical: Entity,
    duplicate: Entity,
) -> tuple[bool, int]:
    """Merge a duplicate entity into the canonical entity.

    Transfers all relationships and deletes the duplicate node.
    Updates mention_count on canonical.

    Args:
        driver: Neo4j async driver
        canonical: Target entity (kept)
        duplicate: Source entity (merged and deleted)

    Returns:
        Tuple of (success, relationships_transferred)
    """
    logger.info(
        "Merging entity",
        duplicate=duplicate.name,
        canonical=canonical.name,
    )

    try:
        # Transfer relationships
        transferred = await transfer_relationships(driver, duplicate.entity_id, canonical.entity_id)

        # Merge document_refs
        merged_refs = list(canonical.document_refs) + list(duplicate.document_refs)
        # Deduplicate refs by filename
        seen_filenames: set[str] = set()
        unique_refs: list[dict[str, Any]] = []
        for ref in merged_refs:
            if isinstance(ref, dict):
                filename = ref.get("filename", "")
                if filename not in seen_filenames:
                    seen_filenames.add(filename)
                    unique_refs.append(ref)

        # Update canonical and delete duplicate
        async with driver.session() as session:
            query = """
            MATCH (canonical:Entity {uuid: $canonical_id})
            SET canonical.mention_count = canonical.mention_count + $added_mentions,
                canonical.document_refs = $merged_refs,
                canonical.merged_at = $merged_at
            WITH canonical
            MATCH (duplicate:Entity {uuid: $duplicate_id})
            DELETE duplicate
            RETURN canonical.uuid AS id
            """
            result = await session.run(
                query,
                canonical_id=canonical.entity_id,
                duplicate_id=duplicate.entity_id,
                added_mentions=duplicate.mention_count,
                merged_refs=unique_refs,
                merged_at=datetime.now(UTC).isoformat(),
            )
            record = await result.single()

            if record:
                logger.info(
                    "Entity merged successfully",
                    canonical=canonical.name,
                    duplicate=duplicate.name,
                    relationships_transferred=transferred,
                )
                return True, transferred

        return False, 0

    except Exception as e:
        logger.exception(
            "Failed to merge entity",
            duplicate=duplicate.name,
            canonical=canonical.name,
            error=str(e),
        )
        return False, 0


async def process_group(
    driver: Any,
    history: MergeHistory,
    group: DuplicateGroup,
    dry_run: bool = False,
    interactive: bool = False,
) -> tuple[int, int]:
    """Process a single duplicate group.

    Args:
        driver: Neo4j async driver
        history: MergeHistory instance for logging
        group: DuplicateGroup to process
        dry_run: If True, only report what would be done
        interactive: If True, prompt for confirmation

    Returns:
        Tuple of (merges_completed, total_relationships_transferred)
    """
    canonical = group.canonical
    merges = 0
    total_transferred = 0

    click.echo(f"\n{'=' * 60}")
    click.echo(f"Canonical: {canonical.name} (mentions: {canonical.mention_count})")
    click.echo(f"Match type: {group.match_type.value}")
    click.echo(f"Similarity: {group.similarity_score:.2f}")
    click.echo(f"Duplicates to merge: {len(group.duplicates)}")

    for dup in group.duplicates:
        rel_count = await get_relationship_count(driver, dup.entity_id)
        click.echo(f"  - {dup.name} (mentions: {dup.mention_count}, rels: {rel_count})")

    if dry_run:
        click.echo("[DRY RUN] Would merge the above entities")
        return len(group.duplicates), 0

    if interactive:
        if not click.confirm("Proceed with merge?", default=True):
            click.echo("Skipped")
            return 0, 0

    # Process each duplicate
    for duplicate in group.duplicates:
        merge_id = str(uuid.uuid4())

        # Get relationship count for logging
        rel_count = await get_relationship_count(driver, duplicate.entity_id)

        # Create merge operation record
        operation = MergeOperation(
            merge_id=merge_id,
            status=MergeStatus.PENDING,
            match_type=group.match_type,
            similarity_score=group.similarity_score,
            canonical_id=canonical.entity_id,
            canonical_name=canonical.name,
            merged_entities=[
                MergedEntity(
                    entity_id=duplicate.entity_id,
                    name=duplicate.name,
                    entity_type=duplicate.entity_type,
                    mention_count=duplicate.mention_count,
                    document_refs=duplicate.document_refs,
                    relationship_count=rel_count,
                )
            ],
        )

        # Log pending merge
        try:
            await history.log_merge(operation)
        except Exception as e:
            logger.warning("Failed to log merge operation", error=str(e))

        # Execute merge
        success, transferred = await merge_entity(driver, canonical, duplicate)

        if success:
            merges += 1
            total_transferred += transferred
            await history.update_status(
                merge_id,
                MergeStatus.COMPLETED,
                f"Transferred {transferred} relationships",
            )
        else:
            await history.update_status(merge_id, MergeStatus.FAILED, "Merge operation failed")

    return merges, total_transferred


async def run_deduplication(
    dry_run: bool = True,
    interactive: bool = False,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run the entity deduplication process.

    Args:
        dry_run: If True, only report what would be done
        interactive: If True, prompt for confirmation on each merge
        threshold: Fuzzy matching threshold (0-100)
        limit: Maximum number of groups to process

    Returns:
        Dictionary with deduplication statistics
    """
    settings = get_settings()

    # Connect to Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    try:
        # Verify connection
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS test")
            await result.single()
            click.echo("Connected to Neo4j successfully")

        # Find duplicates
        click.echo(f"\nFinding duplicate entities (threshold: {threshold}%)...")
        groups = await find_duplicates(driver, threshold)

        if not groups:
            click.echo("No duplicate entities found!")
            return {"groups": 0, "merges": 0, "relationships": 0}

        click.echo(f"Found {len(groups)} duplicate groups")
        total_duplicates = sum(len(g.duplicates) for g in groups)
        click.echo(f"Total entities to merge: {total_duplicates}")

        # Apply limit if specified
        if limit and len(groups) > limit:
            click.echo(f"Limiting to first {limit} groups")
            groups = groups[:limit]

        # Initialize merge history
        history = MergeHistory(driver)

        # Process groups
        total_merges = 0
        total_relationships = 0

        mode = "DRY RUN" if dry_run else ("INTERACTIVE" if interactive else "BATCH")
        click.echo(f"\nProcessing in {mode} mode...")

        for i, group in enumerate(groups, 1):
            click.echo(f"\n[{i}/{len(groups)}]", nl=False)
            merges, rels = await process_group(driver, history, group, dry_run, interactive)
            total_merges += merges
            total_relationships += rels

        # Summary
        click.echo(f"\n{'=' * 60}")
        click.echo("SUMMARY")
        click.echo(f"{'=' * 60}")
        click.echo(f"Mode: {mode}")
        click.echo(f"Groups processed: {len(groups)}")
        click.echo(f"Entities merged: {total_merges}")
        click.echo(f"Relationships transferred: {total_relationships}")

        if dry_run:
            click.echo("\nRun with --batch or --interactive to execute merges")

        return {
            "groups": len(groups),
            "merges": total_merges,
            "relationships": total_relationships,
        }

    finally:
        await driver.close()


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be merged without making changes",
)
@click.option(
    "--interactive",
    is_flag=True,
    default=False,
    help="Prompt for confirmation on each merge group",
)
@click.option(
    "--batch",
    is_flag=True,
    default=False,
    help="Merge all duplicates without prompts",
)
@click.option(
    "--threshold",
    type=float,
    default=DEFAULT_FUZZY_THRESHOLD,
    help=f"Fuzzy matching threshold (default: {DEFAULT_FUZZY_THRESHOLD})",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of groups to process",
)
def main(
    dry_run: bool,
    interactive: bool,
    batch: bool,
    threshold: float,
    limit: int | None,
) -> None:
    """Merge duplicate entities in the Neo4j knowledge graph.

    By default, runs in dry-run mode showing what would be merged.
    """
    # Validate mode selection
    mode_count = sum([dry_run, interactive, batch])
    if mode_count == 0:
        dry_run = True  # Default to dry-run
    elif mode_count > 1:
        click.echo("Error: Only one of --dry-run, --interactive, or --batch allowed")
        sys.exit(1)

    click.echo("=" * 60)
    click.echo("Entity Deduplication Tool")
    click.echo("=" * 60)

    try:
        result = asyncio.run(
            run_deduplication(
                dry_run=dry_run,
                interactive=interactive and not dry_run,
                threshold=threshold,
                limit=limit,
            )
        )

        if result["merges"] > 0 or dry_run:
            sys.exit(0)
        else:
            click.echo("No merges performed")
            sys.exit(0)

    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Deduplication failed", error=str(e))
        click.echo(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
