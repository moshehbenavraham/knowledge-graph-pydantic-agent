"""
Initialize Neo4j database with required schema for Graphiti.

Creates:
- Constraints for Entity and Episode uniqueness
- Indexes for performance
- Verifies connectivity

Usage:
    python scripts/init_neo4j.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agentic_rag.storage.connection_manager import ConnectionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def init_neo4j():
    """Initialize Neo4j with required schema."""
    logger.info("Initializing Neo4j database schema...")

    # Create connection manager
    conn_mgr = ConnectionManager()

    try:
        # Initialize connections
        logger.info("→ Connecting to Neo4j...")
        await conn_mgr.initialize()
        logger.info("✅ Connected to Neo4j")

        async with conn_mgr.get_neo4j_session() as session:
            # Create constraints
            logger.info("→ Creating constraints...")

            # Entity ID uniqueness constraint
            try:
                await session.run(
                    """
                    CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
                    FOR (e:Entity)
                    REQUIRE e.id IS UNIQUE
                    """
                )
                logger.info("✅ Created Entity.id UNIQUE constraint")
            except Exception as e:
                logger.warning(f"Entity.id constraint might already exist: {e}")

            # Episode ID uniqueness constraint
            try:
                await session.run(
                    """
                    CREATE CONSTRAINT episode_id_unique IF NOT EXISTS
                    FOR (ep:Episode)
                    REQUIRE ep.id IS UNIQUE
                    """
                )
                logger.info("✅ Created Episode.id UNIQUE constraint")
            except Exception as e:
                logger.warning(f"Episode.id constraint might already exist: {e}")

            # Create indexes
            logger.info("→ Creating indexes...")

            # Entity name index (for search)
            try:
                await session.run(
                    """
                    CREATE INDEX entity_name_idx IF NOT EXISTS
                    FOR (e:Entity)
                    ON (e.name)
                    """
                )
                logger.info("✅ Created Entity.name index")
            except Exception as e:
                logger.warning(f"Entity.name index might already exist: {e}")

            # Entity type index (for filtering)
            try:
                await session.run(
                    """
                    CREATE INDEX entity_type_idx IF NOT EXISTS
                    FOR (e:Entity)
                    ON (e.type)
                    """
                )
                logger.info("✅ Created Entity.type index")
            except Exception as e:
                logger.warning(f"Entity.type index might already exist: {e}")

            # Episode timestamp index (for temporal queries)
            try:
                await session.run(
                    """
                    CREATE INDEX episode_timestamp_idx IF NOT EXISTS
                    FOR (ep:Episode)
                    ON (ep.timestamp)
                    """
                )
                logger.info("✅ Created Episode.timestamp index")
            except Exception as e:
                logger.warning(f"Episode.timestamp index might already exist: {e}")

            # Episode source_id index (for chunk references)
            try:
                await session.run(
                    """
                    CREATE INDEX episode_source_idx IF NOT EXISTS
                    FOR (ep:Episode)
                    ON (ep.source_id)
                    """
                )
                logger.info("✅ Created Episode.source_id index")
            except Exception as e:
                logger.warning(f"Episode.source_id index might already exist: {e}")

            # Verify schema
            logger.info("→ Verifying schema...")

            # Count existing nodes
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            node_count = record["count"] if record else 0

            # Count existing relationships
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            rel_count = record["count"] if record else 0

            logger.info(f"✅ Schema verified: {node_count} nodes, {rel_count} relationships")

            # List all constraints
            result = await session.run("SHOW CONSTRAINTS")
            constraints = [record async for record in result]
            logger.info(f"✅ {len(constraints)} constraints active")

            # List all indexes
            result = await session.run("SHOW INDEXES")
            indexes = [record async for record in result]
            logger.info(f"✅ {len(indexes)} indexes active")

        logger.info("\n" + "=" * 70)
        logger.info("✅ Neo4j initialization complete!")
        logger.info("=" * 70)
        logger.info("Ready for document ingestion with knowledge graph extraction.")

    except Exception as e:
        logger.error(f"❌ Neo4j initialization failed: {e}")
        logger.exception("Full error:")
        sys.exit(1)

    finally:
        await conn_mgr.close()


if __name__ == "__main__":
    try:
        asyncio.run(init_neo4j())
    except KeyboardInterrupt:
        logger.info("\n❌ Initialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Initialization failed: {e}")
        sys.exit(1)
