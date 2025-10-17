"""
Knowledge graph search for facts and relationships.

Searches Neo4j for entities, relationships, and temporal facts without
retrieving full document content.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.agentic_rag.config import get_config
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.agentic_rag.storage.graphiti_client import GraphitiClient
from src.agentic_rag.storage.neo4j_store import Neo4jStore

logger = logging.getLogger(__name__)


@dataclass
class GraphFact:
    """A fact from the knowledge graph."""

    fact: str
    timestamp: datetime | None
    confidence: float
    source_chunk: str
    entities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fact": self.fact,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "confidence": self.confidence,
            "source_chunk": self.source_chunk,
            "entities": self.entities,
        }


@dataclass
class GraphEntity:
    """An entity from the knowledge graph."""

    id: str
    name: str
    type: str
    chunk_refs: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "chunk_refs": self.chunk_refs,
            "confidence": self.confidence,
        }


@dataclass
class GraphRelationship:
    """A relationship from the knowledge graph."""

    source: str
    target: str
    type: str
    confidence: float
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "confidence": self.confidence,
            "properties": self.properties,
        }


@dataclass
class GraphSearchResult:
    """Result from graph search."""

    facts: list[GraphFact] = field(default_factory=list)
    entities: list[GraphEntity] = field(default_factory=list)
    relationships: list[GraphRelationship] = field(default_factory=list)
    chunk_refs: list[str] = field(default_factory=list)
    query_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "facts": [f.to_dict() for f in self.facts],
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "chunk_refs": self.chunk_refs,
            "query_time": self.query_time,
        }


class GraphSearch:
    """
    Knowledge graph search for facts and relationships.

    Performance targets:
    - <500ms for complex traversals
    - <200ms for direct lookups
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize graph search.

        Args:
            connection_manager: Initialized database connection manager (required)

        Raises:
            ValueError: If connection_manager is None
        """
        if connection_manager is None:
            raise ValueError(
                "GraphSearch requires an initialized ConnectionManager. "
                "Use get_connection_manager() to get a properly initialized instance."
            )

        self.config = get_config()
        self.connection_manager = connection_manager
        self.neo4j_store = Neo4jStore(self.connection_manager)
        self.graphiti_client = GraphitiClient(self.neo4j_store)

        self._stats = {
            "searches": 0,
            "total_latency": 0,
            "facts_found": 0,
            "entities_found": 0,
            "relationships_found": 0,
        }

    async def search(self, query: str, limit: int = 20) -> GraphSearchResult:
        """
        Multi-strategy graph search.

        Searches for:
        1. Full-text search on facts
        2. Entity name matching
        3. Relationship traversal
        4. Temporal filtering

        Args:
            query: Search query
            limit: Maximum results per category

        Returns:
            Graph search result
        """
        start_time = datetime.now()
        self._stats["searches"] += 1

        # Execute parallel searches
        tasks = [
            self._search_facts(query, limit),
            self._search_entities(query, limit),
            self._search_relationships(query, limit),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results
        facts = results[0] if not isinstance(results[0], Exception) else []
        entities = results[1] if not isinstance(results[1], Exception) else []
        relationships = results[2] if not isinstance(results[2], Exception) else []

        # Extract unique chunk references
        chunk_refs = self._extract_chunk_refs(facts, entities, relationships)

        # Update statistics
        query_time = (datetime.now() - start_time).total_seconds()
        self._stats["total_latency"] += query_time
        self._stats["facts_found"] += len(facts)
        self._stats["entities_found"] += len(entities)
        self._stats["relationships_found"] += len(relationships)

        logger.info(
            f"Graph search completed in {query_time:.3f}s: "
            f"{len(facts)} facts, {len(entities)} entities, "
            f"{len(relationships)} relationships"
        )

        return GraphSearchResult(
            facts=facts,
            entities=entities,
            relationships=relationships,
            chunk_refs=chunk_refs,
            query_time=query_time,
        )

    async def _search_facts(self, query: str, limit: int) -> list[GraphFact]:
        """
        Search for facts using Graphiti.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of facts
        """
        try:
            # Use Graphiti's search method
            results = await self.graphiti_client.search(query, limit=limit)

            facts = []
            for result in results:
                # Parse Graphiti result format
                if "fact" in result or "content" in result:
                    fact_text = result.get("fact") or result.get("content", "")

                    facts.append(
                        GraphFact(
                            fact=fact_text[:500],  # Enforce limit
                            timestamp=result.get("timestamp"),
                            confidence=result.get("confidence", 0.8),
                            source_chunk=result.get("source_chunk", ""),
                            entities=result.get("entities", []),
                        )
                    )

            return facts

        except Exception as e:
            logger.warning(f"Fact search failed: {e}")
            return []

    async def _search_entities(self, query: str, limit: int) -> list[GraphEntity]:
        """
        Search for entities by name.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of entities
        """
        try:
            # Build Cypher query for entity search
            cypher = """
            MATCH (e:Entity)
            WHERE toLower(e.name) CONTAINS toLower($query)
            RETURN e.id as id,
                   e.name as name,
                   e.type as type,
                   e.chunk_refs as chunk_refs,
                   e.confidence as confidence
            ORDER BY e.confidence DESC
            LIMIT $limit
            """

            results = await self.neo4j_store.execute_query(cypher, {"query": query, "limit": limit})

            entities = []
            for record in results:
                entities.append(
                    GraphEntity(
                        id=record["id"],
                        name=record["name"],
                        type=record["type"],
                        chunk_refs=record.get("chunk_refs", []),
                        confidence=record.get("confidence", 1.0),
                    )
                )

            return entities

        except Exception as e:
            logger.warning(f"Entity search failed: {e}")
            return []

    async def _search_relationships(self, query: str, limit: int) -> list[GraphRelationship]:
        """
        Search for relationships.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of relationships
        """
        try:
            # First find relevant entities
            entities = await self._search_entities(query, 10)

            if not entities:
                return []

            entity_ids = [e.id for e in entities]

            # Find relationships involving these entities
            cypher = """
            MATCH (e1:Entity)-[r]->(e2:Entity)
            WHERE e1.id IN $entity_ids OR e2.id IN $entity_ids
            RETURN e1.name as source,
                   e2.name as target,
                   type(r) as type,
                   r.confidence as confidence,
                   properties(r) as properties
            ORDER BY r.confidence DESC
            LIMIT $limit
            """

            results = await self.neo4j_store.execute_query(
                cypher, {"entity_ids": entity_ids, "limit": limit}
            )

            relationships = []
            for record in results:
                relationships.append(
                    GraphRelationship(
                        source=record["source"],
                        target=record["target"],
                        type=record["type"],
                        confidence=record.get("confidence", 1.0),
                        properties=record.get("properties", {}),
                    )
                )

            return relationships

        except Exception as e:
            logger.warning(f"Relationship search failed: {e}")
            return []

    async def find_entity_timeline(self, entity_name: str, limit: int = 20) -> list[GraphFact]:
        """
        Get timeline of facts for an entity.

        Args:
            entity_name: Entity name
            limit: Maximum results

        Returns:
            List of facts in chronological order
        """
        try:
            # Find entity
            cypher = """
            MATCH (e:Entity {name: $name})
            RETURN e.id as entity_id
            LIMIT 1
            """

            result = await self.neo4j_store.execute_query(cypher, {"name": entity_name})

            if not result:
                return []

            entity_id = result[0]["entity_id"]

            # Get timeline from Neo4j
            facts = await self.neo4j_store.get_entity_timeline(entity_id, limit=limit)

            return [
                GraphFact(
                    fact=f["fact"][:500],
                    timestamp=f.get("timestamp"),
                    confidence=f.get("confidence", 0.8),
                    source_chunk=f.get("source_chunk", ""),
                    entities=[entity_name],
                )
                for f in facts
            ]

        except Exception as e:
            logger.warning(f"Timeline search failed: {e}")
            return []

    async def find_entity_relationships(self, entity_name: str, depth: int = 2) -> dict[str, Any]:
        """
        Find all relationships for an entity up to specified depth.

        Args:
            entity_name: Entity name
            depth: Traversal depth

        Returns:
            Dictionary with entities and relationships
        """
        try:
            cypher = """
            MATCH path = (e:Entity {name: $name})-[*1..$depth]-(related:Entity)
            WITH e, related, relationships(path) as rels
            RETURN DISTINCT
                related.name as entity_name,
                related.type as entity_type,
                [r in rels | {
                    type: type(r),
                    confidence: r.confidence,
                    properties: properties(r)
                }] as relationships
            LIMIT 50
            """

            results = await self.neo4j_store.execute_query(
                cypher, {"name": entity_name, "depth": depth}
            )

            return {
                "central_entity": entity_name,
                "related_entities": [
                    {
                        "name": r["entity_name"],
                        "type": r["entity_type"],
                        "relationships": r["relationships"],
                    }
                    for r in results
                ],
            }

        except Exception as e:
            logger.warning(f"Relationship traversal failed: {e}")
            return {"central_entity": entity_name, "related_entities": []}

    def _extract_chunk_refs(
        self,
        facts: list[GraphFact],
        entities: list[GraphEntity],
        relationships: list[GraphRelationship],
    ) -> list[str]:
        """
        Extract unique chunk references.

        Args:
            facts: List of facts
            entities: List of entities
            relationships: List of relationships

        Returns:
            List of unique chunk references
        """
        chunk_refs = set()

        # From facts
        for fact in facts:
            if fact.source_chunk:
                chunk_refs.add(fact.source_chunk)

        # From entities
        for entity in entities:
            chunk_refs.update(entity.chunk_refs)

        # From relationships
        for rel in relationships:
            if "source_chunk" in rel.properties:
                chunk_refs.add(rel.properties["source_chunk"])

        return list(chunk_refs)

    def get_stats(self) -> dict[str, Any]:
        """
        Get search statistics.

        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()

        if stats["searches"] > 0:
            stats["avg_latency"] = stats["total_latency"] / stats["searches"]
            stats["avg_facts_per_search"] = stats["facts_found"] / stats["searches"]
            stats["avg_entities_per_search"] = stats["entities_found"] / stats["searches"]
            stats["avg_relationships_per_search"] = stats["relationships_found"] / stats["searches"]

        return stats
