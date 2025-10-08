"""
Neo4j store operations for lightweight entity and relationship management.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class Neo4jStore:
    """Neo4j operations for entity and relationship management without content duplication."""

    def __init__(self, connection_manager):
        """Initialize with connection manager."""
        self.connection_manager = connection_manager

    async def add_entities(self, entities: list[dict[str, Any]], source_chunk_id: str) -> list[str]:
        """Add entities to Neo4j (only names and types, no content)."""
        entity_ids = []

        async with self.connection_manager.get_neo4j_session() as session:
            for entity in entities:
                entity_id = f"entity_{uuid4()}"

                # Create or merge entity
                result = await session.run(
                    """
                    MERGE (e:Entity {name: $name, type: $type})
                    ON CREATE SET
                        e.id = $entity_id,
                        e.canonical_name = $name,
                        e.first_seen = datetime(),
                        e.last_updated = datetime(),
                        e.mention_count = 1,
                        e.relationship_count = 0,
                        e.importance_score = 0.5,
                        e.chunk_refs = [$chunk_id],
                        e.document_refs = []
                    ON MATCH SET
                        e.last_updated = datetime(),
                        e.mention_count = e.mention_count + 1,
                        e.chunk_refs = CASE
                            WHEN $chunk_id IN e.chunk_refs THEN e.chunk_refs
                            ELSE e.chunk_refs + $chunk_id
                        END
                    RETURN e.id as entity_id
                """,
                    name=entity["name"],
                    type=entity["type"],
                    entity_id=entity_id,
                    chunk_id=source_chunk_id,
                )

                record = await result.single()
                entity_ids.append(record["entity_id"])

                logger.debug(f"Added/updated entity: {entity['name']} ({entity['type']})")

        logger.info(f"Added {len(entity_ids)} entities from chunk {source_chunk_id}")
        return entity_ids

    async def add_relationships(
        self, relationships: list[dict[str, Any]], source_chunk_id: str
    ) -> int:
        """Add relationships between entities."""
        relationship_count = 0

        async with self.connection_manager.get_neo4j_session() as session:
            for rel in relationships:
                # Create relationship
                result = await session.run(
                    """
                    MATCH (e1:Entity {id: $entity1_id})
                    MATCH (e2:Entity {id: $entity2_id})
                    MERGE (e1)-[r:RELATED_TO {
                        type: $rel_type,
                        subtype: $rel_subtype
                    }]-(e2)
                    ON CREATE SET
                        r.id = $rel_id,
                        r.confidence = $confidence,
                        r.strength = $strength,
                        r.valid_from = datetime(),
                        r.is_current = true,
                        r.source_chunks = [$chunk_id],
                        r.extraction_method = 'llm',
                        r.last_verified = datetime()
                    ON MATCH SET
                        r.confidence = CASE
                            WHEN r.confidence < $confidence THEN $confidence
                            ELSE r.confidence
                        END,
                        r.source_chunks = CASE
                            WHEN $chunk_id IN r.source_chunks THEN r.source_chunks
                            ELSE r.source_chunks + $chunk_id
                        END,
                        r.last_verified = datetime()
                    RETURN r.id as rel_id
                """,
                    entity1_id=rel["entity1_id"],
                    entity2_id=rel["entity2_id"],
                    rel_type=rel.get("type", "RELATED_TO"),
                    rel_subtype=rel.get("subtype", "general"),
                    rel_id=f"rel_{uuid4()}",
                    confidence=rel.get("confidence", 0.8),
                    strength=rel.get("strength", 0.5),
                    chunk_id=source_chunk_id,
                )

                if await result.single():
                    relationship_count += 1

                # Update entity relationship counts
                await session.run(
                    """
                    MATCH (e:Entity)
                    WHERE e.id IN [$entity1_id, $entity2_id]
                    SET e.relationship_count = size((e)-[:RELATED_TO]-())
                """,
                    entity1_id=rel["entity1_id"],
                    entity2_id=rel["entity2_id"],
                )

        logger.info(f"Added {relationship_count} relationships from chunk {source_chunk_id}")
        return relationship_count

    async def add_episodes(
        self, facts: list[str], entity_ids: list[str], source_chunk_id: str, source_document_id: str
    ) -> list[str]:
        """Add temporal facts/episodes (brief summaries, not full content)."""
        episode_ids = []

        async with self.connection_manager.get_neo4j_session() as session:
            for fact in facts:
                # Ensure fact is brief (max 500 chars)
                if len(fact) > 500:
                    fact = fact[:497] + "..."

                episode_id = f"episode_{uuid4()}"

                # Create episode
                result = await session.run(
                    """
                    CREATE (ep:Episode {
                        id: $episode_id,
                        fact: $fact,
                        timestamp: datetime(),
                        source_chunk: $chunk_id,
                        source_document: $document_id,
                        confidence: 0.8,
                        entities: $entity_ids,
                        fact_type: 'extracted',
                        temporal_type: 'point'
                    })
                    RETURN ep.id as episode_id
                """,
                    episode_id=episode_id,
                    fact=fact,
                    chunk_id=source_chunk_id,
                    document_id=source_document_id,
                    entity_ids=entity_ids,
                )

                record = await result.single()
                if record:
                    episode_ids.append(record["episode_id"])

                    # Link episode to entities
                    await session.run(
                        """
                        MATCH (ep:Episode {id: $episode_id})
                        MATCH (e:Entity)
                        WHERE e.id IN $entity_ids
                        CREATE (e)-[:MENTIONED_IN]->(ep)
                    """,
                        episode_id=episode_id,
                        entity_ids=entity_ids,
                    )

        logger.info(f"Added {len(episode_ids)} episodes from chunk {source_chunk_id}")
        return episode_ids

    async def execute_query(
        self, cypher: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute a custom Cypher query and return results.

        Args:
            cypher: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run(cypher, **(parameters or {}))

            records = []
            async for record in result:
                # Convert record to dict
                records.append(dict(record))

            return records

    async def search_entities(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for entities by name or type."""
        async with self.connection_manager.get_neo4j_session() as session:
            # Try exact match first
            result = await session.run(
                """
                MATCH (e:Entity)
                WHERE toLower(e.name) CONTAINS toLower($query)
                   OR toLower(e.type) = toLower($query)
                RETURN e
                ORDER BY e.importance_score DESC, e.mention_count DESC
                LIMIT $limit
            """,
                query=query,
                limit=limit,
            )

            entities = []
            async for record in result:
                entity = dict(record["e"])
                entities.append(entity)

            # If no results, try fuzzy search
            if not entities:
                result = await session.run(
                    """
                    CALL db.index.fulltext.queryNodes('entity_search', $query)
                    YIELD node, score
                    RETURN node as e, score
                    ORDER BY score DESC
                    LIMIT $limit
                """,
                    query=query,
                    limit=limit,
                )

                async for record in result:
                    entity = dict(record["e"])
                    entity["search_score"] = record["score"]
                    entities.append(entity)

            return entities

    async def get_entity_relationships(self, entity_id: str, depth: int = 1) -> dict[str, Any]:
        """Get relationships for an entity up to specified depth."""
        async with self.connection_manager.get_neo4j_session() as session:
            # Get entity and its relationships
            result = await session.run(
                """
                MATCH path = (e:Entity {id: $entity_id})-[r:RELATED_TO*1..$depth]-(related)
                RETURN
                    e,
                    collect(DISTINCT r) as relationships,
                    collect(DISTINCT related) as related_entities
            """,
                entity_id=entity_id,
                depth=min(depth, 3),
            )  # Cap depth at 3

            record = await result.single()
            if not record:
                return None

            return {
                "entity": dict(record["e"]),
                "relationships": [dict(r) for r in record["relationships"]],
                "related_entities": [dict(e) for e in record["related_entities"]],
            }

    async def search_episodes(
        self,
        query: str,
        entity_ids: list[str] | None = None,
        time_range: tuple[datetime, datetime] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for episodes/facts."""
        async with self.connection_manager.get_neo4j_session() as session:
            # Build query based on parameters
            where_clauses = []
            params = {"query": query, "limit": limit}

            if entity_ids:
                where_clauses.append("ANY(e_id IN ep.entities WHERE e_id IN $entity_ids)")
                params["entity_ids"] = entity_ids

            if time_range:
                where_clauses.append("ep.timestamp >= $start_time AND ep.timestamp <= $end_time")
                params["start_time"] = time_range[0]
                params["end_time"] = time_range[1]

            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Search episodes
            result = await session.run(
                f"""
                CALL db.index.fulltext.queryNodes('episode_search', $query)
                YIELD node, score
                WITH node as ep, score
                WHERE {where_clause}
                RETURN ep, score
                ORDER BY score DESC, ep.timestamp DESC
                LIMIT $limit
            """,
                **params,
            )

            episodes = []
            async for record in result:
                episode = dict(record["ep"])
                episode["search_score"] = record["score"]
                episodes.append(episode)

            return episodes

    async def get_entity_timeline(self, entity_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get timeline of episodes for an entity."""
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {id: $entity_id})-[:MENTIONED_IN]->(ep:Episode)
                RETURN ep
                ORDER BY ep.timestamp DESC
                LIMIT $limit
            """,
                entity_id=entity_id,
                limit=limit,
            )

            timeline = []
            async for record in result:
                timeline.append(dict(record["ep"]))

            return timeline

    async def update_entity_importance(self, entity_id: str):
        """Update entity importance score based on mentions and relationships."""
        async with self.connection_manager.get_neo4j_session() as session:
            await session.run(
                """
                MATCH (e:Entity {id: $entity_id})
                WITH e,
                     size((e)-[:RELATED_TO]-()) as rel_count,
                     size((e)-[:MENTIONED_IN]->()) as mention_count
                SET e.importance_score =
                    CASE
                        WHEN rel_count + mention_count = 0 THEN 0.1
                        ELSE (rel_count * 0.3 + mention_count * 0.7) /
                             (rel_count + mention_count + 10.0)
                    END,
                    e.relationship_count = rel_count,
                    e.mention_count = mention_count
            """,
                entity_id=entity_id,
            )

    async def find_paths(
        self, entity1_id: str, entity2_id: str, max_depth: int = 3
    ) -> list[dict[str, Any]]:
        """Find paths between two entities."""
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run(
                f"""
                MATCH path = shortestPath(
                    (e1:Entity {{id: $entity1_id}})-[*..{max_depth}]-(e2:Entity {{id: $entity2_id}})
                )
                RETURN path
                LIMIT 5
            """,
                entity1_id=entity1_id,
                entity2_id=entity2_id,
            )

            paths = []
            async for record in result:
                path = record["path"]
                paths.append(
                    {
                        "nodes": [dict(node) for node in path.nodes],
                        "relationships": [dict(rel) for rel in path.relationships],
                        "length": len(path.relationships),
                    }
                )

            return paths

    async def get_graph_statistics(self) -> dict[str, Any]:
        """Get graph database statistics."""
        async with self.connection_manager.get_neo4j_session() as session:
            stats = {}

            # Count nodes by label
            for label in ["Entity", "Episode", "Concept", "Event"]:
                result = await session.run(
                    f"""
                    MATCH (n:{label})
                    RETURN count(n) as count
                """
                )
                record = await result.single()
                stats[f"{label.lower()}_count"] = record["count"] if record else 0

            # Count relationships
            result = await session.run(
                """
                MATCH ()-[r:RELATED_TO]->()
                RETURN count(r) as count
            """
            )
            record = await result.single()
            stats["relationship_count"] = record["count"] if record else 0

            # Get top entities
            result = await session.run(
                """
                MATCH (e:Entity)
                RETURN e.name as name, e.type as type, e.importance_score as score
                ORDER BY e.importance_score DESC
                LIMIT 10
            """
            )

            top_entities = []
            async for record in result:
                top_entities.append(
                    {"name": record["name"], "type": record["type"], "score": record["score"]}
                )
            stats["top_entities"] = top_entities

            # Graph density
            if stats["entity_count"] > 0:
                max_relationships = stats["entity_count"] * (stats["entity_count"] - 1) / 2
                stats["graph_density"] = (
                    stats["relationship_count"] / max_relationships if max_relationships > 0 else 0
                )
            else:
                stats["graph_density"] = 0

            return stats

    async def cleanup_orphaned_entities(self):
        """Remove entities with no relationships or mentions."""
        async with self.connection_manager.get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (e:Entity)
                WHERE NOT EXISTS((e)-[:RELATED_TO]-())
                  AND NOT EXISTS((e)-[:MENTIONED_IN]->())
                  AND e.mention_count = 0
                DELETE e
                RETURN count(e) as deleted_count
            """
            )

            record = await result.single()
            if record and record["deleted_count"] > 0:
                logger.info(f"Cleaned up {record['deleted_count']} orphaned entities")
