"""
Multi-hop query engine for knowledge graph path traversal.

This module provides relationship traversal across the knowledge graph,
enabling queries like "What products did companies acquired by Intel release?"
or "Which executives are connected through shared board memberships?"

Key components:
- PathNode, PathStep, PathResult: Dataclasses for path representation
- MultiHopQuery: Pydantic model for query parameters
- MultiHopQueryBuilder: Builder pattern for Cypher query construction
- PathResultParser: Parser for Neo4j path records

Performance targets:
- 1-hop queries: < 500ms
- 2-hop queries: < 1 second
- 3-hop queries: < 2 seconds
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from functools import reduce
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field, field_validator

from src.agentic_rag.cache import CacheType, generate_cache_key, get_query_cache
from src.agentic_rag.graph.type_hierarchy import get_type_hierarchy
from src.config import get_settings

if TYPE_CHECKING:
    from src.agentic_rag.storage.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)

# Query timeout from settings
MULTI_HOP_TIMEOUT_SECONDS = 5.0


# =============================================================================
# Dataclasses (T003-T005)
# =============================================================================


@dataclass
class PathNode:
    """
    Represents a single node in a path traversal result.

    Attributes:
        id: Unique node identifier
        name: Entity name
        type: Entity type (e.g., "company", "person", "product")
        properties: Additional node properties
    """

    id: str
    name: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "properties": self.properties,
        }


@dataclass
class PathStep:
    """
    Represents a relationship edge in a path traversal result.

    Attributes:
        source_id: ID of the source node
        target_id: ID of the target node
        relationship_type: Type of relationship (e.g., "RELATED_TO")
        subtype: Relationship subtype (e.g., "acquired", "employs")
        strength: Relationship strength score (0.0-1.0)
        properties: Additional relationship properties
    """

    source_id: str
    target_id: str
    relationship_type: str
    subtype: str
    strength: float
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "subtype": self.subtype,
            "strength": self.strength,
            "properties": self.properties,
        }


@dataclass
class PathResult:
    """
    Represents a complete path with nodes, steps, and ranking.

    The path is ordered from start to end, with nodes and steps alternating:
    node[0] -> step[0] -> node[1] -> step[1] -> node[2] ...

    Attributes:
        nodes: List of nodes in traversal order
        steps: List of relationship edges connecting nodes
        cumulative_strength: Product of all edge strengths (for ranking)
        hop_count: Number of hops (edges) in the path
        source_documents: Document references for provenance
    """

    nodes: list[PathNode] = field(default_factory=list)
    steps: list[PathStep] = field(default_factory=list)
    cumulative_strength: float = 0.0
    hop_count: int = 0
    source_documents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "steps": [s.to_dict() for s in self.steps],
            "cumulative_strength": self.cumulative_strength,
            "hop_count": self.hop_count,
            "source_documents": self.source_documents,
        }

    def get_path_summary(self) -> str:
        """
        Get a human-readable path summary.

        Returns:
            String like "Intel -> acquired -> Mobileye -> produces -> product_X"
        """
        if not self.nodes:
            return ""

        parts = []
        for i, node in enumerate(self.nodes):
            parts.append(node.name)
            if i < len(self.steps):
                step = self.steps[i]
                parts.append(f"--[{step.subtype}]-->")

        return " ".join(parts)


# =============================================================================
# Pydantic Model (T006)
# =============================================================================


class MultiHopQuery(BaseModel):
    """
    Query parameters for multi-hop graph traversal.

    Attributes:
        start_entity: Starting entity name or pattern
        end_entity: Optional ending entity name or pattern
        min_hops: Minimum path length (default 1)
        max_hops: Maximum path length (default 3, max 3)
        relationship_types: Optional list of relationship types to traverse
        exclude_relationship_types: Relationship types to exclude
        min_strength: Minimum relationship strength threshold (default 0.3)
        entity_type_filter: Filter nodes by entity type (uses hierarchy)
        limit: Maximum number of paths to return (default 50)
    """

    start_entity: str = Field(
        ...,
        min_length=1,
        description="Starting entity name or search pattern",
    )
    end_entity: str | None = Field(
        default=None,
        description="Optional ending entity name or pattern",
    )
    min_hops: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Minimum path length",
    )
    max_hops: int = Field(
        default=3,
        ge=1,
        le=3,
        description="Maximum path length (capped at 3 for performance)",
    )
    relationship_types: list[str] | None = Field(
        default=None,
        description="Relationship types to include (None = all)",
    )
    exclude_relationship_types: list[str] | None = Field(
        default=None,
        description="Relationship types to exclude",
    )
    min_strength: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum relationship strength threshold",
    )
    entity_type_filter: str | None = Field(
        default=None,
        description="Filter nodes by entity type (supports hierarchy)",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum paths to return",
    )

    @field_validator("max_hops")
    @classmethod
    def validate_max_hops(cls, v: int, info: Any) -> int:
        """Ensure max_hops >= min_hops."""
        min_hops = info.data.get("min_hops", 1)
        if v < min_hops:
            raise ValueError(f"max_hops ({v}) must be >= min_hops ({min_hops})")
        return v


# =============================================================================
# Query Builder (T008-T012)
# =============================================================================


class MultiHopQueryBuilder:
    """
    Builder pattern for constructing multi-hop Cypher queries.

    Builds parameterized Cypher queries with:
    - Variable-length path matching (1-3 hops)
    - Relationship type filtering
    - Strength threshold filtering
    - Entity type filtering with hierarchy expansion
    """

    def __init__(self) -> None:
        """Initialize the query builder."""
        self._start_entity: str | None = None
        self._end_entity: str | None = None
        self._min_hops: int = 1
        self._max_hops: int = 3
        self._relationship_types: list[str] | None = None
        self._exclude_relationship_types: list[str] | None = None
        self._min_strength: float = 0.3
        self._entity_type_filter: str | None = None
        self._limit: int = 50
        self._type_hierarchy = get_type_hierarchy()

    def start_from(self, entity: str) -> MultiHopQueryBuilder:
        """Set the starting entity."""
        self._start_entity = entity
        return self

    def end_at(self, entity: str | None) -> MultiHopQueryBuilder:
        """Set the optional ending entity."""
        self._end_entity = entity
        return self

    def with_hop_range(self, min_hops: int, max_hops: int) -> MultiHopQueryBuilder:
        """Set the hop range (1-3)."""
        self._min_hops = max(1, min(3, min_hops))
        self._max_hops = max(1, min(3, max_hops))
        self._min_hops = min(self._min_hops, self._max_hops)
        return self

    def with_relationship_types(self, types: list[str] | None) -> MultiHopQueryBuilder:
        """Set relationship types to include."""
        self._relationship_types = types
        return self

    def exclude_relationship_types(self, types: list[str] | None) -> MultiHopQueryBuilder:
        """Set relationship types to exclude."""
        self._exclude_relationship_types = types
        return self

    def with_min_strength(self, strength: float) -> MultiHopQueryBuilder:
        """Set minimum relationship strength threshold."""
        self._min_strength = max(0.0, min(1.0, strength))
        return self

    def with_entity_type_filter(self, entity_type: str | None) -> MultiHopQueryBuilder:
        """Set entity type filter (uses hierarchy expansion)."""
        self._entity_type_filter = entity_type
        return self

    def with_limit(self, limit: int) -> MultiHopQueryBuilder:
        """Set result limit."""
        self._limit = max(1, min(100, limit))
        return self

    def from_query(self, query: MultiHopQuery) -> MultiHopQueryBuilder:
        """Configure builder from MultiHopQuery model."""
        self._start_entity = query.start_entity
        self._end_entity = query.end_entity
        self._min_hops = query.min_hops
        self._max_hops = query.max_hops
        self._relationship_types = query.relationship_types
        self._exclude_relationship_types = query.exclude_relationship_types
        self._min_strength = query.min_strength
        self._entity_type_filter = query.entity_type_filter
        self._limit = query.limit
        return self

    def build(self) -> tuple[str, dict[str, Any]]:
        """
        Build the Cypher query and parameters.

        Returns:
            Tuple of (cypher_query_string, parameters_dict)

        Raises:
            ValueError: If start_entity is not set
        """
        if not self._start_entity:
            raise ValueError("start_entity is required")

        params: dict[str, Any] = {
            "start_entity": self._start_entity,
            "min_strength": self._min_strength,
            "limit": self._limit,
        }

        # Build MATCH clause with variable-length path
        if self._end_entity:
            params["end_entity"] = self._end_entity
            match_clause = self._build_match_with_end_entity()
        else:
            match_clause = self._build_match_open_ended()

        # Build WHERE clauses
        where_clauses = self._build_where_clauses(params)
        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Build RETURN clause with path data
        return_clause = self._build_return_clause()

        # Combine into full query
        query = f"""
        {match_clause}
        WHERE {where_str}
        {return_clause}
        ORDER BY cumulative_strength DESC
        LIMIT $limit
        """

        logger.debug(
            "MultiHopQueryBuilder.build",
            start_entity=self._start_entity,
            end_entity=self._end_entity,
            hop_range=f"{self._min_hops}-{self._max_hops}",
            min_strength=self._min_strength,
            entity_type_filter=self._entity_type_filter,
        )

        return query.strip(), params

    def _build_match_with_end_entity(self) -> str:
        """Build MATCH clause when end entity is specified."""
        return f"""
        MATCH path = (start:Entity)-[rels:RELATED_TO*{self._min_hops}..{self._max_hops}]-(end:Entity)
        WHERE toLower(start.name) CONTAINS toLower($start_entity)
          AND toLower(end.name) CONTAINS toLower($end_entity)
        WITH path, start, end, rels, nodes(path) as path_nodes
        """

    def _build_match_open_ended(self) -> str:
        """Build MATCH clause for open-ended traversal."""
        return f"""
        MATCH path = (start:Entity)-[rels:RELATED_TO*{self._min_hops}..{self._max_hops}]-(end:Entity)
        WHERE toLower(start.name) CONTAINS toLower($start_entity)
          AND start <> end
        WITH path, start, end, rels, nodes(path) as path_nodes
        """

    def _build_where_clauses(self, params: dict[str, Any]) -> list[str]:
        """Build WHERE clauses for filtering."""
        clauses = []

        # Strength threshold - all edges must meet minimum
        clauses.append("ALL(r IN rels WHERE r.strength >= $min_strength)")

        # Relationship type filtering
        if self._relationship_types:
            params["include_rel_types"] = [t.lower() for t in self._relationship_types]
            clauses.append("ALL(r IN rels WHERE toLower(r.subtype) IN $include_rel_types)")

        if self._exclude_relationship_types:
            params["exclude_rel_types"] = [t.lower() for t in self._exclude_relationship_types]
            clauses.append("NONE(r IN rels WHERE toLower(r.subtype) IN $exclude_rel_types)")

        # Entity type filtering with hierarchy expansion
        if self._entity_type_filter:
            expanded_types = self._type_hierarchy.expand_type_filter(self._entity_type_filter)
            params["entity_types"] = [t.lower() for t in expanded_types]
            clauses.append("ALL(n IN path_nodes WHERE toLower(n.type) IN $entity_types)")

        return clauses

    def _build_return_clause(self) -> str:
        """Build RETURN clause extracting path data."""
        return """
        WITH path, start, end, rels, path_nodes,
             reduce(strength = 1.0, r IN rels | strength * r.strength) as cumulative_strength
        RETURN
            [n IN path_nodes | {
                id: n.id,
                name: n.name,
                type: n.type,
                properties: properties(n)
            }] as nodes,
            [r IN rels | {
                source_id: startNode(r).id,
                target_id: endNode(r).id,
                relationship_type: type(r),
                subtype: r.subtype,
                strength: r.strength,
                properties: properties(r)
            }] as relationships,
            cumulative_strength,
            length(path) as hop_count
        """


# =============================================================================
# Path Result Parser (T013-T014)
# =============================================================================


class PathResultParser:
    """
    Parses Neo4j path records into PathResult objects.

    Handles conversion from raw Cypher results to typed dataclasses
    with proper strength calculation and ranking.
    """

    @staticmethod
    def parse_record(record: dict[str, Any]) -> PathResult:
        """
        Parse a single Neo4j record into a PathResult.

        Args:
            record: Dictionary from Neo4j query result

        Returns:
            PathResult with parsed nodes, steps, and calculated strength
        """
        # Parse nodes
        nodes = []
        for node_data in record.get("nodes", []):
            nodes.append(
                PathNode(
                    id=node_data.get("id", ""),
                    name=node_data.get("name", ""),
                    type=node_data.get("type", ""),
                    properties=node_data.get("properties", {}),
                )
            )

        # Parse relationships/steps
        steps = []
        for rel_data in record.get("relationships", []):
            steps.append(
                PathStep(
                    source_id=rel_data.get("source_id", ""),
                    target_id=rel_data.get("target_id", ""),
                    relationship_type=rel_data.get("relationship_type", "RELATED_TO"),
                    subtype=rel_data.get("subtype", "general"),
                    strength=float(rel_data.get("strength", 0.5)),
                    properties=rel_data.get("properties", {}),
                )
            )

        # Calculate cumulative strength (product of all edge strengths)
        cumulative_strength = record.get("cumulative_strength")
        if cumulative_strength is None:
            cumulative_strength = PathResultParser.calculate_path_strength(steps)

        # Extract source documents from node properties
        source_documents = PathResultParser._extract_source_documents(nodes)

        return PathResult(
            nodes=nodes,
            steps=steps,
            cumulative_strength=float(cumulative_strength),
            hop_count=len(steps),
            source_documents=source_documents,
        )

    @staticmethod
    def parse_records(records: list[dict[str, Any]]) -> list[PathResult]:
        """
        Parse multiple Neo4j records into PathResults.

        Args:
            records: List of dictionaries from Neo4j query results

        Returns:
            List of PathResults sorted by cumulative_strength descending
        """
        results = [PathResultParser.parse_record(r) for r in records]
        # Sort by cumulative strength (highest first)
        results.sort(key=lambda x: x.cumulative_strength, reverse=True)
        return results

    @staticmethod
    def calculate_path_strength(steps: list[PathStep]) -> float:
        """
        Calculate cumulative path strength as product of edge strengths.

        Args:
            steps: List of path steps

        Returns:
            Product of all step strengths (0.0 if empty)
        """
        if not steps:
            return 0.0

        return reduce(lambda acc, step: acc * step.strength, steps, 1.0)

    @staticmethod
    def _extract_source_documents(nodes: list[PathNode]) -> list[str]:
        """Extract unique source document references from path nodes."""
        documents: set[str] = set()

        for node in nodes:
            # Check document_refs property
            doc_refs = node.properties.get("document_refs", [])
            if isinstance(doc_refs, list):
                for ref in doc_refs:
                    if isinstance(ref, dict) and "filename" in ref:
                        documents.add(ref["filename"])
                    elif isinstance(ref, str):
                        documents.add(ref)

        return list(documents)


# =============================================================================
# Execute Function (T015)
# =============================================================================


async def execute_multi_hop(
    connection_manager: ConnectionManager,
    query: MultiHopQuery,
    use_cache: bool = True,
    timeout_seconds: float | None = None,
) -> list[PathResult]:
    """
    Execute a multi-hop traversal query against Neo4j.

    This is the main entry point for multi-hop queries. It builds the
    Cypher query, executes it against Neo4j, and parses the results.
    Results are cached for improved performance on repeated queries.

    Args:
        connection_manager: Initialized database connection manager
        query: MultiHopQuery parameters
        use_cache: Whether to use query result caching (default True)
        timeout_seconds: Query timeout (default from settings)

    Returns:
        List of PathResults sorted by cumulative strength (strongest first)

    Raises:
        ValueError: If connection_manager is None

    Example:
        >>> query = MultiHopQuery(
        ...     start_entity="Intel",
        ...     max_hops=2,
        ...     min_strength=0.5,
        ... )
        >>> results = await execute_multi_hop(connection_manager, query)
        >>> for path in results:
        ...     print(path.get_path_summary())
    """
    if connection_manager is None:
        raise ValueError("connection_manager is required")

    # Get timeout from settings if not specified
    if timeout_seconds is None:
        settings = get_settings()
        timeout_seconds = settings.query_timeout_seconds

    start_time = datetime.now()

    logger.info(
        "execute_multi_hop called",
        start_entity=query.start_entity,
        end_entity=query.end_entity,
        hop_range=f"{query.min_hops}-{query.max_hops}",
        min_strength=query.min_strength,
        entity_type_filter=query.entity_type_filter,
        limit=query.limit,
        use_cache=use_cache,
    )

    # Check cache first
    cache = get_query_cache()
    cache_key = generate_cache_key(
        query=query.start_entity,
        params={
            "end_entity": query.end_entity,
            "min_hops": query.min_hops,
            "max_hops": query.max_hops,
            "min_strength": query.min_strength,
            "entity_type_filter": query.entity_type_filter,
            "limit": query.limit,
        },
        prefix="multi_hop",
    )

    if use_cache:
        hit, cached_result = cache.get(CacheType.MULTI_HOP, cache_key)
        if hit:
            logger.info(
                "execute_multi_hop cache hit",
                start_entity=query.start_entity,
                cache_key=cache_key[:16],
            )
            return cached_result  # type: ignore[no-any-return]

    # Build query
    builder = MultiHopQueryBuilder().from_query(query)
    cypher, params = builder.build()

    logger.debug("execute_multi_hop cypher", cypher_preview=cypher[:200])

    # Execute query with timeout
    try:
        async with asyncio.timeout(timeout_seconds):
            async with connection_manager.get_neo4j_session() as session:
                result = await session.run(cypher, params)

                records = []
                async for record in result:
                    records.append(dict(record))

    except TimeoutError:
        logger.warning(
            "execute_multi_hop timeout",
            start_entity=query.start_entity,
            timeout_seconds=timeout_seconds,
        )
        return []

    except Exception as e:
        logger.exception(
            "execute_multi_hop failed",
            error=str(e),
            start_entity=query.start_entity,
        )
        return []

    # Parse results
    path_results = PathResultParser.parse_records(records)

    # Cache results
    if use_cache:
        cache.set(CacheType.MULTI_HOP, cache_key, path_results)

    query_time = (datetime.now() - start_time).total_seconds()

    logger.info(
        "execute_multi_hop completed",
        paths_found=len(path_results),
        query_time_ms=query_time * 1000,
        start_entity=query.start_entity,
        cached=use_cache,
    )

    return path_results


# =============================================================================
# Convenience Functions
# =============================================================================


async def find_paths_between(
    connection_manager: ConnectionManager,
    start_entity: str,
    end_entity: str,
    max_hops: int = 3,
    min_strength: float = 0.3,
    limit: int = 10,
) -> list[PathResult]:
    """
    Find paths between two specific entities.

    Convenience wrapper for common use case of finding connections
    between two known entities.

    Args:
        connection_manager: Database connection manager
        start_entity: Starting entity name
        end_entity: Ending entity name
        max_hops: Maximum path length (default 3)
        min_strength: Minimum relationship strength (default 0.3)
        limit: Maximum paths to return (default 10)

    Returns:
        List of PathResults connecting the entities
    """
    query = MultiHopQuery(
        start_entity=start_entity,
        end_entity=end_entity,
        max_hops=max_hops,
        min_strength=min_strength,
        limit=limit,
    )
    return await execute_multi_hop(connection_manager, query)


async def explore_entity_neighborhood(
    connection_manager: ConnectionManager,
    entity: str,
    hops: int = 2,
    min_strength: float = 0.3,
    entity_type: str | None = None,
    limit: int = 50,
) -> list[PathResult]:
    """
    Explore the neighborhood around an entity.

    Finds all reachable entities within the specified hop distance,
    optionally filtered by entity type.

    Args:
        connection_manager: Database connection manager
        entity: Central entity name
        hops: Maximum distance to explore (default 2)
        min_strength: Minimum relationship strength (default 0.3)
        entity_type: Optional entity type filter (uses hierarchy)
        limit: Maximum paths to return (default 50)

    Returns:
        List of PathResults from the central entity
    """
    query = MultiHopQuery(
        start_entity=entity,
        min_hops=1,
        max_hops=hops,
        min_strength=min_strength,
        entity_type_filter=entity_type,
        limit=limit,
    )
    return await execute_multi_hop(connection_manager, query)
