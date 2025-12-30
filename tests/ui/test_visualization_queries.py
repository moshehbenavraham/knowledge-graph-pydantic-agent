"""
Unit tests for visualization queries module.

Tests query building and execution functions for the Graph Explorer.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agentic_rag.graph.visualization_queries import (
    DEFAULT_ENTITY_LIMIT,
    DEFAULT_MAX_NODES,
    DEFAULT_STRENGTH_THRESHOLD,
    EntitySearchResult,
    SubgraphEdge,
    SubgraphNode,
    SubgraphResult,
    TemporalFact,
    build_entity_relationships_query,
    build_entity_search_query,
    build_expand_neighbors_query,
    build_subgraph_query,
    build_temporal_facts_query,
)


class TestEntitySearchResult:
    """Tests for EntitySearchResult dataclass."""

    def test_entity_search_result_creation(self) -> None:
        """Test creating EntitySearchResult with all fields."""
        result = EntitySearchResult(
            id="entity-123",
            name="Test Entity",
            type="company",
            relationship_count=5,
            canonical_name="Test Entity Inc",
            properties={"key": "value"},
        )

        assert result.id == "entity-123"
        assert result.name == "Test Entity"
        assert result.type == "company"
        assert result.relationship_count == 5
        assert result.canonical_name == "Test Entity Inc"
        assert result.properties == {"key": "value"}

    def test_entity_search_result_to_dict(self) -> None:
        """Test EntitySearchResult.to_dict() method."""
        result = EntitySearchResult(
            id="entity-123",
            name="Test Entity",
            type="company",
            relationship_count=5,
        )

        as_dict = result.to_dict()

        assert as_dict["id"] == "entity-123"
        assert as_dict["name"] == "Test Entity"
        assert as_dict["type"] == "company"
        assert as_dict["relationship_count"] == 5

    def test_entity_search_result_defaults(self) -> None:
        """Test EntitySearchResult default values."""
        result = EntitySearchResult(
            id="entity-123",
            name="Test",
            type="person",
        )

        assert result.relationship_count == 0
        assert result.canonical_name is None
        assert result.properties == {}


class TestSubgraphNode:
    """Tests for SubgraphNode dataclass."""

    def test_subgraph_node_creation(self) -> None:
        """Test creating SubgraphNode."""
        node = SubgraphNode(
            id="node-1",
            name="Node Name",
            type="organization",
            relationship_count=10,
            properties={"source": "doc1"},
        )

        assert node.id == "node-1"
        assert node.name == "Node Name"
        assert node.type == "organization"
        assert node.relationship_count == 10

    def test_subgraph_node_to_dict(self) -> None:
        """Test SubgraphNode.to_dict() method."""
        node = SubgraphNode(
            id="node-1",
            name="Node",
            type="person",
        )

        as_dict = node.to_dict()

        assert "id" in as_dict
        assert "name" in as_dict
        assert "type" in as_dict
        assert "relationship_count" in as_dict


class TestSubgraphEdge:
    """Tests for SubgraphEdge dataclass."""

    def test_subgraph_edge_creation(self) -> None:
        """Test creating SubgraphEdge."""
        edge = SubgraphEdge(
            source_id="node-1",
            target_id="node-2",
            relationship_type="RELATED_TO",
            subtype="acquired",
            strength=0.85,
        )

        assert edge.source_id == "node-1"
        assert edge.target_id == "node-2"
        assert edge.relationship_type == "RELATED_TO"
        assert edge.subtype == "acquired"
        assert edge.strength == 0.85

    def test_subgraph_edge_to_dict(self) -> None:
        """Test SubgraphEdge.to_dict() method."""
        edge = SubgraphEdge(
            source_id="a",
            target_id="b",
            relationship_type="RELATED_TO",
            subtype="mentions",
            strength=0.5,
        )

        as_dict = edge.to_dict()

        assert as_dict["source_id"] == "a"
        assert as_dict["target_id"] == "b"
        assert as_dict["strength"] == 0.5


class TestSubgraphResult:
    """Tests for SubgraphResult dataclass."""

    def test_subgraph_result_creation(self) -> None:
        """Test creating SubgraphResult."""
        nodes = [
            SubgraphNode(id="n1", name="Node 1", type="company"),
            SubgraphNode(id="n2", name="Node 2", type="person"),
        ]
        edges = [
            SubgraphEdge(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="employs",
                strength=0.8,
            )
        ]

        result = SubgraphResult(
            nodes=nodes,
            edges=edges,
            center_entity_id="n1",
            query_time_ms=150.5,
        )

        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.center_entity_id == "n1"
        assert result.query_time_ms == 150.5

    def test_subgraph_result_to_dict(self) -> None:
        """Test SubgraphResult.to_dict() method."""
        result = SubgraphResult(
            nodes=[SubgraphNode(id="n1", name="Node", type="company")],
            edges=[],
        )

        as_dict = result.to_dict()

        assert "nodes" in as_dict
        assert "edges" in as_dict
        assert len(as_dict["nodes"]) == 1


class TestTemporalFact:
    """Tests for TemporalFact dataclass."""

    def test_temporal_fact_creation(self) -> None:
        """Test creating TemporalFact."""
        now = datetime.now()
        fact = TemporalFact(
            description="Company was acquired",
            valid_from=now,
            valid_to=None,
            created_at=now,
            source_document="doc.pdf",
        )

        assert fact.description == "Company was acquired"
        assert fact.valid_from == now
        assert fact.valid_to is None
        assert fact.source_document == "doc.pdf"

    def test_temporal_fact_to_dict(self) -> None:
        """Test TemporalFact.to_dict() method."""
        now = datetime.now()
        fact = TemporalFact(
            description="Test fact",
            valid_from=now,
        )

        as_dict = fact.to_dict()

        assert as_dict["description"] == "Test fact"
        assert "valid_from" in as_dict
        assert as_dict["valid_from"] is not None


class TestBuildEntitySearchQuery:
    """Tests for build_entity_search_query function."""

    def test_basic_query_no_filters(self) -> None:
        """Test query with no filters."""
        query, params = build_entity_search_query()

        assert "MATCH (e:Entity)" in query
        assert "RETURN" in query
        assert "ORDER BY" in query
        assert params["limit"] == DEFAULT_ENTITY_LIMIT

    def test_query_with_search_term(self) -> None:
        """Test query with search term filter."""
        query, params = build_entity_search_query(search_term="Intel")

        assert "toLower(e.name) CONTAINS" in query
        assert params["search_term"] == "intel"

    def test_query_with_entity_types(self) -> None:
        """Test query with entity type filter."""
        query, params = build_entity_search_query(entity_types=["company", "organization"])

        assert "toLower(e.type) IN" in query
        assert "entity_types" in params

    def test_query_with_custom_limit(self) -> None:
        """Test query with custom limit."""
        _query, params = build_entity_search_query(limit=25)

        assert params["limit"] == 25


class TestBuildSubgraphQuery:
    """Tests for build_subgraph_query function."""

    def test_basic_subgraph_query(self) -> None:
        """Test basic subgraph query."""
        _query, params = build_subgraph_query(entity_id="entity-123")

        assert params["entity_id"] == "entity-123"
        assert params["min_strength"] == DEFAULT_STRENGTH_THRESHOLD
        assert params["max_nodes"] == DEFAULT_MAX_NODES

    def test_subgraph_query_with_depth(self) -> None:
        """Test subgraph query with custom depth."""
        query, _params = build_subgraph_query(entity_id="e1", max_depth=2)

        assert "*1..2" in query

    def test_subgraph_query_with_relationship_types(self) -> None:
        """Test subgraph query with relationship type filter."""
        _query, params = build_subgraph_query(
            entity_id="e1",
            relationship_types=["acquired", "partnered"],
        )

        assert "rel_types" in params
        assert "acquired" in params["rel_types"]

    def test_subgraph_query_max_depth_capped(self) -> None:
        """Test that max_depth is capped at 3."""
        query, _params = build_subgraph_query(entity_id="e1", max_depth=10)

        # Max depth should be capped at 3
        assert "*1..3" in query


class TestBuildTemporalFactsQuery:
    """Tests for build_temporal_facts_query function."""

    def test_basic_temporal_query(self) -> None:
        """Test basic temporal facts query."""
        query, params = build_temporal_facts_query(entity_id="entity-123")

        assert params["entity_id"] == "entity-123"
        assert "RETURN" in query
        assert "ORDER BY" in query

    def test_temporal_query_with_date_range(self) -> None:
        """Test temporal facts query with date range."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)

        _query, params = build_temporal_facts_query(
            entity_id="e1",
            start_date=start,
            end_date=end,
        )

        assert "start_date" in params
        assert "end_date" in params

    def test_temporal_query_with_limit(self) -> None:
        """Test temporal facts query with custom limit."""
        _query, params = build_temporal_facts_query(entity_id="e1", limit=100)

        assert params["limit"] == 100


class TestBuildExpandNeighborsQuery:
    """Tests for build_expand_neighbors_query function."""

    def test_expand_neighbors_query(self) -> None:
        """Test expand neighbors query."""
        query, params = build_expand_neighbors_query(
            entity_id="center-1",
            existing_ids=["n1", "n2", "n3"],
            max_neighbors=15,
        )

        assert params["entity_id"] == "center-1"
        assert params["existing_ids"] == ["n1", "n2", "n3"]
        assert params["max_neighbors"] == 15
        assert "NOT IN" in query

    def test_expand_neighbors_with_strength(self) -> None:
        """Test expand neighbors with minimum strength."""
        _query, params = build_expand_neighbors_query(
            entity_id="e1",
            existing_ids=[],
            min_strength=0.7,
        )

        assert params["min_strength"] == 0.7


class TestBuildEntityRelationshipsQuery:
    """Tests for build_entity_relationships_query function."""

    def test_basic_relationships_query(self) -> None:
        """Test basic entity relationships query."""
        query, params = build_entity_relationships_query(entity_id="entity-123")

        assert params["entity_id"] == "entity-123"
        assert "MATCH" in query
        assert "RELATED_TO" in query

    def test_relationships_query_with_types(self) -> None:
        """Test relationships query with type filter."""
        _query, params = build_entity_relationships_query(
            entity_id="e1",
            relationship_types=["acquired"],
        )

        assert "rel_types" in params
        assert "acquired" in params["rel_types"]

    def test_relationships_query_with_strength(self) -> None:
        """Test relationships query with strength threshold."""
        _query, params = build_entity_relationships_query(
            entity_id="e1",
            min_strength=0.8,
        )

        assert params["min_strength"] == 0.8


class TestSearchEntitiesFunction:
    """Tests for search_entities async function."""

    @pytest.mark.asyncio
    async def test_search_entities_returns_results(self) -> None:
        """Test search_entities returns EntitySearchResult list."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.data = AsyncMock(
            return_value=[
                {
                    "id": "e1",
                    "name": "Entity 1",
                    "type": "company",
                    "relationship_count": 5,
                    "canonical_name": None,
                    "properties": {},
                }
            ]
        )
        mock_session.run = AsyncMock(return_value=mock_result)

        mock_cm = MagicMock()
        mock_cm.get_neo4j_session = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()
            )
        )

        with patch("src.agentic_rag.graph.visualization_queries.search_entities") as mock_search:
            mock_search.return_value = [
                EntitySearchResult(id="e1", name="Entity 1", type="company", relationship_count=5)
            ]

            from src.agentic_rag.graph.visualization_queries import search_entities

            results = await search_entities(mock_cm, search_term="test")

            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_entities_handles_error(self) -> None:
        """Test search_entities handles errors gracefully."""
        mock_cm = MagicMock()
        mock_cm.get_neo4j_session = MagicMock(side_effect=Exception("Connection failed"))

        from src.agentic_rag.graph.visualization_queries import search_entities

        results = await search_entities(mock_cm, search_term="test")

        assert results == []


class TestFetchEntitySubgraph:
    """Tests for fetch_entity_subgraph async function."""

    @pytest.mark.asyncio
    async def test_fetch_subgraph_returns_result(self) -> None:
        """Test fetch_entity_subgraph returns SubgraphResult."""
        mock_cm = MagicMock()

        with patch(
            "src.agentic_rag.graph.visualization_queries.fetch_entity_subgraph"
        ) as mock_fetch:
            mock_fetch.return_value = SubgraphResult(
                nodes=[SubgraphNode(id="n1", name="Node", type="company")],
                edges=[],
                center_entity_id="n1",
            )

            from src.agentic_rag.graph.visualization_queries import fetch_entity_subgraph

            result = await fetch_entity_subgraph(mock_cm, entity_id="n1")

            assert isinstance(result, SubgraphResult)
            assert result.center_entity_id == "n1"

    @pytest.mark.asyncio
    async def test_fetch_subgraph_handles_empty(self) -> None:
        """Test fetch_entity_subgraph handles no results."""
        mock_cm = MagicMock()

        with patch(
            "src.agentic_rag.graph.visualization_queries.fetch_entity_subgraph"
        ) as mock_fetch:
            mock_fetch.return_value = SubgraphResult(center_entity_id="missing")

            from src.agentic_rag.graph.visualization_queries import fetch_entity_subgraph

            result = await fetch_entity_subgraph(mock_cm, entity_id="missing")

            assert result.nodes == []
            assert result.edges == []
