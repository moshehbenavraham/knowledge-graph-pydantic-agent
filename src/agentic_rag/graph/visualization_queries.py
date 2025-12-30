"""
Visualization-specific Neo4j queries for the Graph Explorer dashboard.

This module provides optimized Cypher queries for:
- Entity search with name matching and type filtering
- Subgraph fetching with relationship expansion
- Temporal facts retrieval for entity details
- Relationship filtering by type and strength

All queries are parameterized to prevent injection attacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

from src.agentic_rag.graph.type_hierarchy import get_type_hierarchy

if TYPE_CHECKING:
    from src.agentic_rag.storage.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)

# Default limits for visualization performance
DEFAULT_ENTITY_LIMIT = 50
DEFAULT_RELATIONSHIP_LIMIT = 100
DEFAULT_MAX_NODES = 100
DEFAULT_STRENGTH_THRESHOLD = 0.3


@dataclass
class EntitySearchResult:
    """
    Result from entity search query.

    Attributes:
        id: Entity unique identifier
        name: Entity name
        type: Entity type (e.g., company, person)
        relationship_count: Number of connected relationships
        canonical_name: Canonical form of entity name
        properties: Additional entity properties
    """

    id: str
    name: str
    type: str
    relationship_count: int = 0
    canonical_name: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "relationship_count": self.relationship_count,
            "canonical_name": self.canonical_name,
            "properties": self.properties,
        }


@dataclass
class SubgraphNode:
    """
    Node in a visualization subgraph.

    Attributes:
        id: Node unique identifier
        name: Display name
        type: Entity type for styling
        relationship_count: Connection count for sizing
        properties: Additional properties for tooltips
    """

    id: str
    name: str
    type: str
    relationship_count: int = 0
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for pyvis."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "relationship_count": self.relationship_count,
            "properties": self.properties,
        }


@dataclass
class SubgraphEdge:
    """
    Edge in a visualization subgraph.

    Attributes:
        source_id: Source node ID
        target_id: Target node ID
        relationship_type: Type of relationship
        subtype: Relationship subtype (e.g., acquired, employs)
        strength: Relationship strength for edge styling
        properties: Additional properties for tooltips
    """

    source_id: str
    target_id: str
    relationship_type: str
    subtype: str
    strength: float = 0.5
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for pyvis."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "subtype": self.subtype,
            "strength": self.strength,
            "properties": self.properties,
        }


@dataclass
class TemporalFact:
    """
    Temporal fact associated with an entity.

    Attributes:
        description: Fact description
        valid_from: Start of validity period
        valid_to: End of validity period (None if current)
        created_at: When the fact was recorded
        source_document: Document that mentioned this fact
    """

    description: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    created_at: datetime | None = None
    source_document: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "description": self.description,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source_document": self.source_document,
        }


@dataclass
class SubgraphResult:
    """
    Complete subgraph result for visualization.

    Attributes:
        nodes: List of nodes in the subgraph
        edges: List of edges connecting nodes
        center_entity_id: ID of the central entity (if any)
        query_time_ms: Query execution time
    """

    nodes: list[SubgraphNode] = field(default_factory=list)
    edges: list[SubgraphEdge] = field(default_factory=list)
    center_entity_id: str | None = None
    query_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for handler."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "center_entity_id": self.center_entity_id,
            "query_time_ms": self.query_time_ms,
        }


def build_entity_search_query(
    search_term: str | None = None,
    entity_types: list[str] | None = None,
    limit: int = DEFAULT_ENTITY_LIMIT,
) -> tuple[str, dict[str, Any]]:
    """
    Build Cypher query for entity search with optional filters.

    Args:
        search_term: Optional name search pattern (case-insensitive)
        entity_types: Optional list of entity types to filter
        limit: Maximum entities to return

    Returns:
        Tuple of (cypher_query, parameters)
    """
    params: dict[str, Any] = {"limit": limit}

    # Start building query
    match_clause = "MATCH (e:Entity)"
    where_clauses: list[str] = []

    # Add search term filter
    if search_term:
        params["search_term"] = search_term.lower()
        where_clauses.append("toLower(e.name) CONTAINS $search_term")

    # Add type filter with hierarchy expansion
    if entity_types:
        hierarchy = get_type_hierarchy()
        expanded_types: list[str] = []
        for entity_type in entity_types:
            expanded_types.extend(hierarchy.expand_type_filter(entity_type.lower()))
        params["entity_types"] = list(set(expanded_types))
        where_clauses.append("toLower(e.type) IN $entity_types")

    # Build WHERE clause
    where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
    {match_clause}
    WHERE {where_str}
    WITH e, COUNT {{ (e)-[]-() }} as rel_count
    RETURN
        e.id as id,
        e.name as name,
        e.type as type,
        rel_count as relationship_count,
        e.canonical_name as canonical_name,
        properties(e) as properties
    ORDER BY rel_count DESC, e.name ASC
    LIMIT $limit
    """

    logger.debug(
        "build_entity_search_query",
        has_search_term=search_term is not None,
        entity_types=entity_types,
        limit=limit,
    )

    return query.strip(), params


def build_subgraph_query(
    entity_id: str,
    max_depth: int = 1,
    relationship_types: list[str] | None = None,
    min_strength: float = DEFAULT_STRENGTH_THRESHOLD,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> tuple[str, dict[str, Any]]:
    """
    Build Cypher query for fetching entity subgraph.

    Args:
        entity_id: Central entity ID
        max_depth: Maximum relationship depth (1-3)
        relationship_types: Optional relationship type filter
        min_strength: Minimum relationship strength threshold
        max_nodes: Maximum nodes to return

    Returns:
        Tuple of (cypher_query, parameters)
    """
    max_depth = max(1, min(3, max_depth))

    params: dict[str, Any] = {
        "entity_id": entity_id,
        "min_strength": min_strength,
        "max_nodes": max_nodes,
    }

    # Build relationship filter
    rel_filter = ""
    if relationship_types:
        params["rel_types"] = [rt.lower() for rt in relationship_types]
        rel_filter = "AND toLower(r.subtype) IN $rel_types"

    query = f"""
    MATCH (center:Entity {{id: $entity_id}})
    OPTIONAL MATCH path = (center)-[r:RELATED_TO*1..{max_depth}]-(neighbor:Entity)
    WHERE ALL(rel IN relationships(path) WHERE rel.strength >= $min_strength {rel_filter})
    WITH center, path, neighbor,
         CASE WHEN path IS NULL THEN [] ELSE relationships(path) END as rels
    UNWIND (CASE WHEN path IS NULL THEN [center] ELSE nodes(path) END) as node
    WITH DISTINCT node, center
    WITH node, COUNT {{ (node)-[]-() }} as rel_count
    ORDER BY rel_count DESC
    LIMIT $max_nodes
    WITH collect({{
        id: node.id,
        name: node.name,
        type: node.type,
        relationship_count: rel_count,
        properties: properties(node)
    }}) as nodes

    MATCH (n1:Entity)-[r:RELATED_TO]->(n2:Entity)
    WHERE n1.id IN [node IN nodes | node.id]
      AND n2.id IN [node IN nodes | node.id]
      AND r.strength >= $min_strength
    WITH nodes, collect({{
        source_id: n1.id,
        target_id: n2.id,
        relationship_type: type(r),
        subtype: r.subtype,
        strength: r.strength,
        properties: properties(r)
    }}) as edges

    RETURN nodes, edges
    """

    logger.debug(
        "build_subgraph_query",
        entity_id=entity_id,
        max_depth=max_depth,
        relationship_types=relationship_types,
        min_strength=min_strength,
        max_nodes=max_nodes,
    )

    return query.strip(), params


def build_temporal_facts_query(
    entity_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 50,
) -> tuple[str, dict[str, Any]]:
    """
    Build Cypher query for entity temporal facts.

    Args:
        entity_id: Entity ID to get facts for
        start_date: Optional start of date range filter
        end_date: Optional end of date range filter
        limit: Maximum facts to return

    Returns:
        Tuple of (cypher_query, parameters)
    """
    params: dict[str, Any] = {
        "entity_id": entity_id,
        "limit": limit,
    }

    # Build date range filter
    date_filter = ""
    if start_date:
        params["start_date"] = start_date.isoformat()
        date_filter += " AND (f.valid_from IS NULL OR f.valid_from >= datetime($start_date))"
    if end_date:
        params["end_date"] = end_date.isoformat()
        date_filter += " AND (f.valid_to IS NULL OR f.valid_to <= datetime($end_date))"

    query = f"""
    MATCH (e:Entity {{id: $entity_id}})-[r]-(f:Entity)
    WHERE type(r) IN ['RELATED_TO', 'MENTIONS', 'HAS_RELATIONSHIP']
    {date_filter}
    WITH e, f, r,
         coalesce(f.name, f.canonical_name, 'Related entity') as description,
         coalesce(f.first_seen, r.created_at) as valid_from,
         f.last_seen as valid_to,
         coalesce(f.first_seen, r.created_at) as created_at
    RETURN
        description,
        valid_from,
        valid_to,
        created_at,
        null as source_document
    ORDER BY created_at DESC
    LIMIT $limit
    """

    logger.debug(
        "build_temporal_facts_query",
        entity_id=entity_id,
        has_start_date=start_date is not None,
        has_end_date=end_date is not None,
        limit=limit,
    )

    return query.strip(), params


def build_expand_neighbors_query(
    entity_id: str,
    existing_ids: list[str],
    max_neighbors: int = 20,
    min_strength: float = DEFAULT_STRENGTH_THRESHOLD,
) -> tuple[str, dict[str, Any]]:
    """
    Build Cypher query to expand neighbors for an entity.

    This query returns neighbors that are not already in the graph,
    enabling progressive graph expansion.

    Args:
        entity_id: Entity to expand from
        existing_ids: IDs already in the graph (to exclude)
        max_neighbors: Maximum new neighbors to add
        min_strength: Minimum relationship strength

    Returns:
        Tuple of (cypher_query, parameters)
    """
    params: dict[str, Any] = {
        "entity_id": entity_id,
        "existing_ids": existing_ids,
        "max_neighbors": max_neighbors,
        "min_strength": min_strength,
    }

    query = """
    MATCH (center:Entity {id: $entity_id})-[r:RELATED_TO]-(neighbor:Entity)
    WHERE neighbor.id NOT IN $existing_ids
      AND r.strength >= $min_strength
    WITH neighbor, r, COUNT { (neighbor)-[]-() } as rel_count
    ORDER BY r.strength DESC, rel_count DESC
    LIMIT $max_neighbors
    RETURN
        neighbor.id as id,
        neighbor.name as name,
        neighbor.type as type,
        rel_count as relationship_count,
        properties(neighbor) as properties,
        {
            source_id: $entity_id,
            target_id: neighbor.id,
            relationship_type: type(r),
            subtype: r.subtype,
            strength: r.strength,
            properties: properties(r)
        } as edge
    """

    logger.debug(
        "build_expand_neighbors_query",
        entity_id=entity_id,
        existing_count=len(existing_ids),
        max_neighbors=max_neighbors,
    )

    return query.strip(), params


def build_entity_relationships_query(
    entity_id: str,
    relationship_types: list[str] | None = None,
    min_strength: float = DEFAULT_STRENGTH_THRESHOLD,
    limit: int = DEFAULT_RELATIONSHIP_LIMIT,
) -> tuple[str, dict[str, Any]]:
    """
    Build Cypher query for entity relationships.

    Args:
        entity_id: Entity to get relationships for
        relationship_types: Optional filter for relationship types
        min_strength: Minimum relationship strength
        limit: Maximum relationships to return

    Returns:
        Tuple of (cypher_query, parameters)
    """
    params: dict[str, Any] = {
        "entity_id": entity_id,
        "min_strength": min_strength,
        "limit": limit,
    }

    # Build relationship type filter
    type_filter = ""
    if relationship_types:
        params["rel_types"] = [rt.lower() for rt in relationship_types]
        type_filter = "AND toLower(r.subtype) IN $rel_types"

    query = f"""
    MATCH (e:Entity {{id: $entity_id}})-[r:RELATED_TO]-(other:Entity)
    WHERE r.strength >= $min_strength {type_filter}
    WITH e, r, other, COUNT {{ (other)-[]-() }} as other_rel_count
    RETURN
        other.id as target_id,
        other.name as target_name,
        other.type as target_type,
        other_rel_count as target_relationship_count,
        type(r) as relationship_type,
        r.subtype as subtype,
        r.strength as strength,
        properties(r) as properties
    ORDER BY r.strength DESC
    LIMIT $limit
    """

    logger.debug(
        "build_entity_relationships_query",
        entity_id=entity_id,
        relationship_types=relationship_types,
        min_strength=min_strength,
        limit=limit,
    )

    return query.strip(), params


async def search_entities(
    connection_manager: ConnectionManager,
    search_term: str | None = None,
    entity_types: list[str] | None = None,
    limit: int = DEFAULT_ENTITY_LIMIT,
) -> list[EntitySearchResult]:
    """
    Search for entities matching criteria.

    Args:
        connection_manager: Database connection manager
        search_term: Optional name search pattern
        entity_types: Optional entity type filter
        limit: Maximum results

    Returns:
        List of matching EntitySearchResult objects
    """
    start_time = datetime.now()

    logger.info(
        "search_entities called",
        search_term=search_term,
        entity_types=entity_types,
        limit=limit,
    )

    query, params = build_entity_search_query(search_term, entity_types, limit)

    try:
        async with connection_manager.get_neo4j_session() as session:
            result = await session.run(query, params)
            records = await result.data()

        entities = []
        for record in records:
            entities.append(
                EntitySearchResult(
                    id=record.get("id", ""),
                    name=record.get("name", ""),
                    type=record.get("type", ""),
                    relationship_count=record.get("relationship_count", 0),
                    canonical_name=record.get("canonical_name"),
                    properties=record.get("properties", {}),
                )
            )

        query_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "search_entities completed",
            results_found=len(entities),
            query_time_ms=query_time,
        )

        return entities

    except Exception as e:
        logger.exception("search_entities failed", error=str(e))
        return []


async def fetch_entity_subgraph(
    connection_manager: ConnectionManager,
    entity_id: str,
    max_depth: int = 1,
    relationship_types: list[str] | None = None,
    min_strength: float = DEFAULT_STRENGTH_THRESHOLD,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> SubgraphResult:
    """
    Fetch subgraph around an entity for visualization.

    Args:
        connection_manager: Database connection manager
        entity_id: Central entity ID
        max_depth: Maximum relationship depth
        relationship_types: Optional relationship type filter
        min_strength: Minimum relationship strength
        max_nodes: Maximum nodes to return

    Returns:
        SubgraphResult with nodes and edges
    """
    start_time = datetime.now()

    logger.info(
        "fetch_entity_subgraph called",
        entity_id=entity_id,
        max_depth=max_depth,
        relationship_types=relationship_types,
        min_strength=min_strength,
        max_nodes=max_nodes,
    )

    query, params = build_subgraph_query(
        entity_id, max_depth, relationship_types, min_strength, max_nodes
    )

    try:
        async with connection_manager.get_neo4j_session() as session:
            result = await session.run(query, params)
            record = await result.single()

        if not record:
            logger.warning("fetch_entity_subgraph returned no results", entity_id=entity_id)
            return SubgraphResult(center_entity_id=entity_id)

        # Parse nodes
        nodes = []
        for node_data in record.get("nodes", []):
            nodes.append(
                SubgraphNode(
                    id=node_data.get("id", ""),
                    name=node_data.get("name", ""),
                    type=node_data.get("type", ""),
                    relationship_count=node_data.get("relationship_count", 0),
                    properties=node_data.get("properties", {}),
                )
            )

        # Parse edges
        edges = []
        for edge_data in record.get("edges", []):
            edges.append(
                SubgraphEdge(
                    source_id=edge_data.get("source_id", ""),
                    target_id=edge_data.get("target_id", ""),
                    relationship_type=edge_data.get("relationship_type", "RELATED_TO"),
                    subtype=edge_data.get("subtype", "general"),
                    strength=float(edge_data.get("strength", 0.5)),
                    properties=edge_data.get("properties", {}),
                )
            )

        query_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "fetch_entity_subgraph completed",
            nodes_count=len(nodes),
            edges_count=len(edges),
            query_time_ms=query_time,
        )

        return SubgraphResult(
            nodes=nodes,
            edges=edges,
            center_entity_id=entity_id,
            query_time_ms=query_time,
        )

    except Exception as e:
        logger.exception("fetch_entity_subgraph failed", entity_id=entity_id, error=str(e))
        return SubgraphResult(center_entity_id=entity_id)


async def fetch_temporal_facts(
    connection_manager: ConnectionManager,
    entity_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 50,
) -> list[TemporalFact]:
    """
    Fetch temporal facts for an entity.

    Args:
        connection_manager: Database connection manager
        entity_id: Entity to get facts for
        start_date: Optional date range start
        end_date: Optional date range end
        limit: Maximum facts to return

    Returns:
        List of TemporalFact objects
    """
    start_time = datetime.now()

    logger.info(
        "fetch_temporal_facts called",
        entity_id=entity_id,
        has_date_range=start_date is not None or end_date is not None,
        limit=limit,
    )

    query, params = build_temporal_facts_query(entity_id, start_date, end_date, limit)

    try:
        async with connection_manager.get_neo4j_session() as session:
            result = await session.run(query, params)
            records = await result.data()

        facts = []
        for record in records:
            valid_from = record.get("valid_from")
            valid_to = record.get("valid_to")
            created_at = record.get("created_at")

            facts.append(
                TemporalFact(
                    description=record.get("description", ""),
                    valid_from=valid_from if isinstance(valid_from, datetime) else None,
                    valid_to=valid_to if isinstance(valid_to, datetime) else None,
                    created_at=created_at if isinstance(created_at, datetime) else None,
                    source_document=record.get("source_document"),
                )
            )

        query_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "fetch_temporal_facts completed",
            facts_count=len(facts),
            query_time_ms=query_time,
        )

        return facts

    except Exception as e:
        logger.exception("fetch_temporal_facts failed", entity_id=entity_id, error=str(e))
        return []


async def expand_entity_neighbors(
    connection_manager: ConnectionManager,
    entity_id: str,
    existing_ids: list[str],
    max_neighbors: int = 20,
    min_strength: float = DEFAULT_STRENGTH_THRESHOLD,
) -> tuple[list[SubgraphNode], list[SubgraphEdge]]:
    """
    Expand neighbors for an entity, excluding existing nodes.

    Args:
        connection_manager: Database connection manager
        entity_id: Entity to expand from
        existing_ids: IDs already in the graph
        max_neighbors: Maximum new neighbors
        min_strength: Minimum relationship strength

    Returns:
        Tuple of (new_nodes, new_edges)
    """
    start_time = datetime.now()

    logger.info(
        "expand_entity_neighbors called",
        entity_id=entity_id,
        existing_count=len(existing_ids),
        max_neighbors=max_neighbors,
    )

    query, params = build_expand_neighbors_query(
        entity_id, existing_ids, max_neighbors, min_strength
    )

    try:
        async with connection_manager.get_neo4j_session() as session:
            result = await session.run(query, params)
            records = await result.data()

        nodes = []
        edges = []

        for record in records:
            nodes.append(
                SubgraphNode(
                    id=record.get("id", ""),
                    name=record.get("name", ""),
                    type=record.get("type", ""),
                    relationship_count=record.get("relationship_count", 0),
                    properties=record.get("properties", {}),
                )
            )

            edge_data = record.get("edge", {})
            edges.append(
                SubgraphEdge(
                    source_id=edge_data.get("source_id", ""),
                    target_id=edge_data.get("target_id", ""),
                    relationship_type=edge_data.get("relationship_type", "RELATED_TO"),
                    subtype=edge_data.get("subtype", "general"),
                    strength=float(edge_data.get("strength", 0.5)),
                    properties=edge_data.get("properties", {}),
                )
            )

        query_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "expand_entity_neighbors completed",
            new_nodes=len(nodes),
            new_edges=len(edges),
            query_time_ms=query_time,
        )

        return nodes, edges

    except Exception as e:
        logger.exception("expand_entity_neighbors failed", entity_id=entity_id, error=str(e))
        return [], []
