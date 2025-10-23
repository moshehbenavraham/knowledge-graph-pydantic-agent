"""
Neo4j initialization with Graphiti integration and custom indexes.
"""

import asyncio
import logging
from typing import Any

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)


class Neo4jInitializer:
    """Initialize Neo4j with Graphiti and custom indexes."""

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: AsyncGraphDatabase.driver | None = None

    async def initialize(self):
        """Initialize Neo4j with all required constraints and indexes."""
        # Create driver
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

        try:
            # Initialize Graphiti (creates base constraints/indexes)
            await self._init_graphiti()

            # Add custom indexes
            await self._create_custom_indexes()

            # Create initial data structures
            await self._create_initial_structures()

            # Verify setup
            await self._verify_setup()

            logger.info("Neo4j initialization completed successfully")

        finally:
            if self.driver:
                await self.driver.close()

    async def _init_graphiti(self):
        """Initialize Graphiti which creates base structures."""
        async with self.driver.session() as session:
            # Create Graphiti base constraints
            constraints = [
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT episode_id IF NOT EXISTS FOR (ep:Episode) REQUIRE ep.id IS UNIQUE",
                "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (ev:Event) REQUIRE ev.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    await session.run(constraint)
                    logger.info(
                        f"Created constraint: {constraint.split('CONSTRAINT')[1].split('IF')[0].strip()}"
                    )
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Constraint creation warning: {e}")

        logger.info("Graphiti base structures initialized successfully")

    async def _create_custom_indexes(self):
        """Create custom indexes beyond Graphiti defaults."""
        custom_indexes = [
            # Performance indexes
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_importance IF NOT EXISTS FOR (e:Entity) ON (e.importance_score)",
            "CREATE INDEX entity_mentions IF NOT EXISTS FOR (e:Entity) ON (e.mention_count)",
            "CREATE INDEX episode_timestamp IF NOT EXISTS FOR (ep:Episode) ON (ep.timestamp)",
            "CREATE INDEX episode_confidence IF NOT EXISTS FOR (ep:Episode) ON (ep.confidence)",
            "CREATE INDEX event_date IF NOT EXISTS FOR (ev:Event) ON (ev.date)",
            "CREATE INDEX event_impact IF NOT EXISTS FOR (ev:Event) ON (ev.impact_score)",
            # Composite indexes
            "CREATE INDEX entity_type_importance IF NOT EXISTS FOR (e:Entity) ON (e.type, e.importance_score)",
            "CREATE INDEX episode_type_timestamp IF NOT EXISTS FOR (ep:Episode) ON (ep.fact_type, ep.timestamp)",
            # Relationship indexes
            "CREATE INDEX rel_confidence IF NOT EXISTS FOR ()-[r:RELATED_TO]-() ON (r.confidence)",
            "CREATE INDEX rel_current IF NOT EXISTS FOR ()-[r:RELATED_TO]-() ON (r.is_current)",
        ]

        async with self.driver.session() as session:
            for index_query in custom_indexes:
                try:
                    await session.run(index_query)
                    index_name = index_query.split("INDEX")[1].split("IF")[0].strip()
                    logger.info(f"Created index: {index_name}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Index creation warning: {e}")

            # Create full-text search indexes (different syntax)
            fulltext_indexes = [
                ("entity_search", "Entity", ["name", "canonical_name"]),
                ("episode_search", "Episode", ["fact"]),
                ("concept_search", "Concept", ["name", "definition"]),
            ]

            for index_name, label, properties in fulltext_indexes:
                try:
                    props_str = ", ".join([f"n.{prop}" for prop in properties])
                    await session.run(
                        f"""
                        CREATE FULLTEXT INDEX {index_name} IF NOT EXISTS
                        FOR (n:{label})
                        ON EACH [{props_str}]
                    """
                    )
                    logger.info(f"Created fulltext index: {index_name}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Fulltext index creation warning: {e}")

    async def _create_initial_structures(self):
        """Create initial graph structures."""
        async with self.driver.session() as session:
            # Create root concepts for categorization
            root_concepts = [
                ("technology", "Root concept for technology-related entities"),
                ("business", "Root concept for business-related entities"),
                ("person", "Root concept for people"),
                ("location", "Root concept for locations"),
                ("event", "Root concept for events"),
                ("product", "Root concept for products"),
            ]

            for name, definition in root_concepts:
                await session.run(
                    """
                    MERGE (c:Concept {id: $id})
                    SET c.name = $name,
                        c.definition = $definition,
                        c.category = 'root',
                        c.created_at = datetime()
                """,
                    id=f"concept_root_{name}",
                    name=name,
                    definition=definition,
                )

            logger.info("Created root concept nodes")

    async def _verify_setup(self):
        """Verify the Neo4j setup is correct."""
        async with self.driver.session() as session:
            # Check constraints
            result = await session.run("SHOW CONSTRAINTS")
            constraints = await result.values()
            logger.info(f"Created {len(constraints)} constraints")

            # Check indexes
            result = await session.run("SHOW INDEXES")
            indexes = await result.values()
            logger.info(f"Created {len(indexes)} indexes")

            # Check node labels
            result = await session.run("CALL db.labels()")
            labels = [record[0] for record in await result.values()]
            expected_labels = {"Entity", "Episode", "Concept", "Event"}

            if expected_labels.issubset(set(labels)):
                logger.info("All expected node labels present")
            else:
                missing = expected_labels - set(labels)
                if missing:
                    logger.warning(f"Missing labels: {missing}")

            # Test query performance
            test_queries = [
                ("MATCH (e:Entity) RETURN e LIMIT 1", "Entity query"),
                ("MATCH (ep:Episode) RETURN ep LIMIT 1", "Episode query"),
                ("MATCH (e:Entity)-[r:RELATED_TO]->() RETURN r LIMIT 1", "Relationship query"),
            ]

            for query, name in test_queries:
                start = asyncio.get_event_loop().time()
                await session.run(query)
                elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000
                logger.info(f"{name} executed in {elapsed_ms:.2f}ms")

    async def clear_all_data(self):
        """Clear all data from Neo4j (useful for testing)."""
        async with self.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
            logger.info("Cleared all data from Neo4j")

    async def get_statistics(self) -> dict[str, Any]:
        """Get database statistics."""
        async with self.driver.session() as session:
            stats = {}

            # Count nodes by label
            labels = ["Entity", "Episode", "Concept", "Event"]
            for label in labels:
                result = await session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                record = await result.single()
                stats[f"{label.lower()}_count"] = record["count"] if record else 0

            # Count relationships
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            stats["relationship_count"] = record["count"] if record else 0

            # Database size
            result = await session.run("CALL dbms.database.info() YIELD name, currentStatus")
            records = await result.values()
            if records:
                stats["database_status"] = records[0][1]

            return stats


async def initialize_neo4j(uri: str, user: str, password: str):
    """Initialize Neo4j database."""
    initializer = Neo4jInitializer(uri, user, password)
    await initializer.initialize()


if __name__ == "__main__":
    from dotenv import load_dotenv

    from src.config import get_settings

    load_dotenv()

    settings = get_settings()
    neo4j_uri = settings.neo4j_uri
    neo4j_user = settings.neo4j_user
    neo4j_password = settings.neo4j_password

    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        raise ValueError(
            "NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD environment variables must be set"
        )

    asyncio.run(initialize_neo4j(neo4j_uri, neo4j_user, neo4j_password))
