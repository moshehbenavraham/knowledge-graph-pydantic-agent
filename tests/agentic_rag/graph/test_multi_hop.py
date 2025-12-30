"""
Unit tests for multi-hop query engine.

Tests cover:
- Pydantic models and dataclasses (T019)
- MultiHopQueryBuilder Cypher generation (T020)
- PathResultParser and strength calculation (T021)
- Integration tests with mocked Neo4j (T022)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agentic_rag.graph.multi_hop import (
    MultiHopQuery,
    MultiHopQueryBuilder,
    PathNode,
    PathResult,
    PathResultParser,
    PathStep,
    execute_multi_hop,
    explore_entity_neighborhood,
    find_paths_between,
)

# =============================================================================
# T019: Unit tests for Pydantic models and dataclasses
# =============================================================================


class TestPathNode:
    """Tests for PathNode dataclass."""

    def test_create_path_node_basic(self) -> None:
        """Test basic PathNode creation."""
        node = PathNode(id="n1", name="Intel", type="company")
        assert node.id == "n1"
        assert node.name == "Intel"
        assert node.type == "company"
        assert node.properties == {}

    def test_create_path_node_with_properties(self) -> None:
        """Test PathNode creation with properties."""
        props = {"importance_score": 0.9, "mention_count": 100}
        node = PathNode(id="n1", name="Intel", type="company", properties=props)
        assert node.properties == props

    def test_path_node_to_dict(self) -> None:
        """Test PathNode serialization."""
        node = PathNode(id="n1", name="Intel", type="company", properties={"score": 0.5})
        result = node.to_dict()
        assert result == {
            "id": "n1",
            "name": "Intel",
            "type": "company",
            "properties": {"score": 0.5},
        }


class TestPathStep:
    """Tests for PathStep dataclass."""

    def test_create_path_step_basic(self) -> None:
        """Test basic PathStep creation."""
        step = PathStep(
            source_id="n1",
            target_id="n2",
            relationship_type="RELATED_TO",
            subtype="acquired",
            strength=0.8,
        )
        assert step.source_id == "n1"
        assert step.target_id == "n2"
        assert step.relationship_type == "RELATED_TO"
        assert step.subtype == "acquired"
        assert step.strength == 0.8
        assert step.properties == {}

    def test_path_step_to_dict(self) -> None:
        """Test PathStep serialization."""
        step = PathStep(
            source_id="n1",
            target_id="n2",
            relationship_type="RELATED_TO",
            subtype="employs",
            strength=0.6,
            properties={"confidence": 0.9},
        )
        result = step.to_dict()
        assert result["source_id"] == "n1"
        assert result["target_id"] == "n2"
        assert result["strength"] == 0.6


class TestPathResult:
    """Tests for PathResult dataclass."""

    def test_create_empty_path_result(self) -> None:
        """Test empty PathResult creation."""
        result = PathResult()
        assert result.nodes == []
        assert result.steps == []
        assert result.cumulative_strength == 0.0
        assert result.hop_count == 0
        assert result.source_documents == []

    def test_create_path_result_with_data(self) -> None:
        """Test PathResult creation with nodes and steps."""
        nodes = [
            PathNode(id="n1", name="Intel", type="company"),
            PathNode(id="n2", name="Mobileye", type="company"),
        ]
        steps = [
            PathStep(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="acquired",
                strength=0.9,
            )
        ]
        result = PathResult(
            nodes=nodes,
            steps=steps,
            cumulative_strength=0.9,
            hop_count=1,
            source_documents=["doc1.pdf"],
        )
        assert len(result.nodes) == 2
        assert len(result.steps) == 1
        assert result.cumulative_strength == 0.9
        assert result.hop_count == 1

    def test_path_result_get_path_summary_empty(self) -> None:
        """Test path summary for empty result."""
        result = PathResult()
        assert result.get_path_summary() == ""

    def test_path_result_get_path_summary_single_node(self) -> None:
        """Test path summary with single node."""
        result = PathResult(nodes=[PathNode(id="n1", name="Intel", type="company")])
        assert result.get_path_summary() == "Intel"

    def test_path_result_get_path_summary_full_path(self) -> None:
        """Test path summary with full path."""
        nodes = [
            PathNode(id="n1", name="Intel", type="company"),
            PathNode(id="n2", name="Mobileye", type="company"),
            PathNode(id="n3", name="AutonomousCar", type="product"),
        ]
        steps = [
            PathStep(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="acquired",
                strength=0.9,
            ),
            PathStep(
                source_id="n2",
                target_id="n3",
                relationship_type="RELATED_TO",
                subtype="produces",
                strength=0.8,
            ),
        ]
        result = PathResult(nodes=nodes, steps=steps)
        summary = result.get_path_summary()
        assert "Intel" in summary
        assert "acquired" in summary
        assert "Mobileye" in summary
        assert "produces" in summary
        assert "AutonomousCar" in summary

    def test_path_result_to_dict(self) -> None:
        """Test PathResult serialization."""
        result = PathResult(
            nodes=[PathNode(id="n1", name="Intel", type="company")],
            steps=[],
            cumulative_strength=1.0,
            hop_count=0,
        )
        data = result.to_dict()
        assert "nodes" in data
        assert "steps" in data
        assert data["cumulative_strength"] == 1.0


class TestMultiHopQuery:
    """Tests for MultiHopQuery Pydantic model."""

    def test_create_basic_query(self) -> None:
        """Test basic query creation."""
        query = MultiHopQuery(start_entity="Intel")
        assert query.start_entity == "Intel"
        assert query.end_entity is None
        assert query.min_hops == 1
        assert query.max_hops == 3
        assert query.min_strength == 0.3
        assert query.limit == 50

    def test_create_query_with_all_params(self) -> None:
        """Test query creation with all parameters."""
        query = MultiHopQuery(
            start_entity="Intel",
            end_entity="AMD",
            min_hops=1,
            max_hops=2,
            relationship_types=["acquired", "partnered"],
            exclude_relationship_types=["competed_with"],
            min_strength=0.5,
            entity_type_filter="organization",
            limit=20,
        )
        assert query.start_entity == "Intel"
        assert query.end_entity == "AMD"
        assert query.max_hops == 2
        assert query.min_strength == 0.5
        assert query.relationship_types == ["acquired", "partnered"]
        assert query.entity_type_filter == "organization"

    def test_query_validates_empty_start_entity(self) -> None:
        """Test that empty start_entity is rejected."""
        with pytest.raises(ValueError):
            MultiHopQuery(start_entity="")

    def test_query_validates_max_hops_range(self) -> None:
        """Test that max_hops is capped at 3."""
        with pytest.raises(ValueError):
            MultiHopQuery(start_entity="Intel", max_hops=5)

    def test_query_validates_min_hops_not_greater_than_max(self) -> None:
        """Test that min_hops <= max_hops."""
        with pytest.raises(ValueError):
            MultiHopQuery(start_entity="Intel", min_hops=3, max_hops=1)

    def test_query_validates_min_strength_range(self) -> None:
        """Test that min_strength is in valid range."""
        with pytest.raises(ValueError):
            MultiHopQuery(start_entity="Intel", min_strength=1.5)

    def test_query_validates_limit_range(self) -> None:
        """Test that limit is in valid range."""
        with pytest.raises(ValueError):
            MultiHopQuery(start_entity="Intel", limit=200)


# =============================================================================
# T020: Unit tests for MultiHopQueryBuilder Cypher generation
# =============================================================================


class TestMultiHopQueryBuilder:
    """Tests for MultiHopQueryBuilder."""

    def test_builder_requires_start_entity(self) -> None:
        """Test that build() requires start_entity."""
        builder = MultiHopQueryBuilder()
        with pytest.raises(ValueError, match="start_entity is required"):
            builder.build()

    def test_builder_basic_query(self) -> None:
        """Test basic single-hop query generation."""
        builder = MultiHopQueryBuilder().start_from("Intel").with_hop_range(1, 1)
        cypher, params = builder.build()

        assert "$start_entity" in cypher
        assert params["start_entity"] == "Intel"
        assert "$min_strength" in cypher
        assert "*1..1" in cypher

    def test_builder_with_end_entity(self) -> None:
        """Test query with end entity specified."""
        builder = MultiHopQueryBuilder().start_from("Intel").end_at("AMD")
        cypher, params = builder.build()

        assert "$end_entity" in cypher
        assert params["end_entity"] == "AMD"

    def test_builder_variable_depth(self) -> None:
        """Test variable-depth query (1-3 hops)."""
        builder = MultiHopQueryBuilder().start_from("Intel").with_hop_range(1, 3)
        cypher, _params = builder.build()

        assert "*1..3" in cypher

    def test_builder_from_query_model(self) -> None:
        """Test builder configuration from MultiHopQuery model."""
        query = MultiHopQuery(
            start_entity="Intel",
            end_entity="Mobileye",
            max_hops=2,
            min_strength=0.5,
        )
        builder = MultiHopQueryBuilder().from_query(query)
        cypher, params = builder.build()

        assert params["start_entity"] == "Intel"
        assert params["end_entity"] == "Mobileye"
        assert params["min_strength"] == 0.5
        assert "*1..2" in cypher

    def test_builder_strength_threshold_filtering(self) -> None:
        """Test strength threshold is included in query."""
        builder = MultiHopQueryBuilder().start_from("Intel").with_min_strength(0.7)
        cypher, params = builder.build()

        assert "r.strength >= $min_strength" in cypher
        assert params["min_strength"] == 0.7

    def test_builder_relationship_type_filtering(self) -> None:
        """Test relationship type filtering."""
        builder = (
            MultiHopQueryBuilder()
            .start_from("Intel")
            .with_relationship_types(["acquired", "partnered"])
        )
        cypher, params = builder.build()

        assert "$include_rel_types" in cypher
        assert params["include_rel_types"] == ["acquired", "partnered"]

    def test_builder_exclude_relationship_types(self) -> None:
        """Test excluding relationship types."""
        builder = (
            MultiHopQueryBuilder().start_from("Intel").exclude_relationship_types(["competed_with"])
        )
        cypher, _params = builder.build()

        assert "$exclude_rel_types" in cypher
        assert "NONE(r IN rels" in cypher

    def test_builder_entity_type_filtering(self) -> None:
        """Test entity type filtering with hierarchy expansion."""
        builder = MultiHopQueryBuilder().start_from("Intel").with_entity_type_filter("organization")
        cypher, params = builder.build()

        assert "$entity_types" in cypher
        assert "n.type" in cypher
        # Should include expanded types
        assert "organization" in params["entity_types"]
        assert "company" in params["entity_types"]

    def test_builder_limit(self) -> None:
        """Test result limit."""
        builder = MultiHopQueryBuilder().start_from("Intel").with_limit(10)
        cypher, params = builder.build()

        assert params["limit"] == 10
        assert "LIMIT $limit" in cypher

    def test_builder_returns_cumulative_strength(self) -> None:
        """Test that query calculates cumulative strength."""
        builder = MultiHopQueryBuilder().start_from("Intel")
        cypher, _ = builder.build()

        assert "cumulative_strength" in cypher
        assert "reduce" in cypher.lower()

    def test_builder_method_chaining(self) -> None:
        """Test fluent method chaining."""
        builder = (
            MultiHopQueryBuilder()
            .start_from("Intel")
            .end_at("AMD")
            .with_hop_range(1, 2)
            .with_min_strength(0.5)
            .with_relationship_types(["acquired"])
            .with_entity_type_filter("organization")
            .with_limit(25)
        )
        _cypher, params = builder.build()

        assert params["start_entity"] == "Intel"
        assert params["end_entity"] == "AMD"
        assert params["min_strength"] == 0.5
        assert params["limit"] == 25


# =============================================================================
# T021: Unit tests for PathResultParser and strength calculation
# =============================================================================


class TestPathResultParser:
    """Tests for PathResultParser."""

    def test_calculate_path_strength_empty(self) -> None:
        """Test strength calculation with empty steps."""
        strength = PathResultParser.calculate_path_strength([])
        assert strength == 0.0

    def test_calculate_path_strength_single_step(self) -> None:
        """Test strength calculation with single step."""
        steps = [
            PathStep(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="acquired",
                strength=0.8,
            )
        ]
        strength = PathResultParser.calculate_path_strength(steps)
        assert strength == 0.8

    def test_calculate_path_strength_multiple_steps(self) -> None:
        """Test strength calculation with multiple steps (product)."""
        steps = [
            PathStep(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="acquired",
                strength=0.8,
            ),
            PathStep(
                source_id="n2",
                target_id="n3",
                relationship_type="RELATED_TO",
                subtype="produces",
                strength=0.5,
            ),
        ]
        strength = PathResultParser.calculate_path_strength(steps)
        assert abs(strength - 0.4) < 0.001  # 0.8 * 0.5 = 0.4

    def test_parse_record_empty(self) -> None:
        """Test parsing empty record."""
        record: dict[str, Any] = {"nodes": [], "relationships": [], "hop_count": 0}
        result = PathResultParser.parse_record(record)
        assert result.nodes == []
        assert result.steps == []

    def test_parse_record_with_data(self) -> None:
        """Test parsing record with data."""
        record = {
            "nodes": [
                {"id": "n1", "name": "Intel", "type": "company", "properties": {}},
                {"id": "n2", "name": "Mobileye", "type": "company", "properties": {}},
            ],
            "relationships": [
                {
                    "source_id": "n1",
                    "target_id": "n2",
                    "relationship_type": "RELATED_TO",
                    "subtype": "acquired",
                    "strength": 0.9,
                    "properties": {},
                }
            ],
            "cumulative_strength": 0.9,
            "hop_count": 1,
        }
        result = PathResultParser.parse_record(record)

        assert len(result.nodes) == 2
        assert result.nodes[0].name == "Intel"
        assert result.nodes[1].name == "Mobileye"
        assert len(result.steps) == 1
        assert result.steps[0].subtype == "acquired"
        assert result.cumulative_strength == 0.9
        assert result.hop_count == 1

    def test_parse_record_calculates_strength_if_missing(self) -> None:
        """Test that strength is calculated if not in record."""
        record = {
            "nodes": [
                {"id": "n1", "name": "Intel", "type": "company", "properties": {}},
                {"id": "n2", "name": "Mobileye", "type": "company", "properties": {}},
            ],
            "relationships": [
                {
                    "source_id": "n1",
                    "target_id": "n2",
                    "relationship_type": "RELATED_TO",
                    "subtype": "acquired",
                    "strength": 0.8,
                    "properties": {},
                }
            ],
            "hop_count": 1,
            # No cumulative_strength provided
        }
        result = PathResultParser.parse_record(record)
        assert result.cumulative_strength == 0.8

    def test_parse_records_sorts_by_strength(self) -> None:
        """Test that multiple records are sorted by strength descending."""
        records = [
            {
                "nodes": [{"id": "n1", "name": "A", "type": "x", "properties": {}}],
                "relationships": [],
                "cumulative_strength": 0.5,
                "hop_count": 0,
            },
            {
                "nodes": [{"id": "n2", "name": "B", "type": "x", "properties": {}}],
                "relationships": [],
                "cumulative_strength": 0.9,
                "hop_count": 0,
            },
            {
                "nodes": [{"id": "n3", "name": "C", "type": "x", "properties": {}}],
                "relationships": [],
                "cumulative_strength": 0.7,
                "hop_count": 0,
            },
        ]
        results = PathResultParser.parse_records(records)

        assert results[0].cumulative_strength == 0.9
        assert results[1].cumulative_strength == 0.7
        assert results[2].cumulative_strength == 0.5

    def test_extract_source_documents(self) -> None:
        """Test document reference extraction from nodes."""
        nodes = [
            PathNode(
                id="n1",
                name="Intel",
                type="company",
                properties={
                    "document_refs": [
                        {"filename": "doc1.pdf"},
                        {"filename": "doc2.pdf"},
                    ]
                },
            ),
            PathNode(
                id="n2",
                name="Mobileye",
                type="company",
                properties={"document_refs": [{"filename": "doc2.pdf"}]},
            ),
        ]
        docs = PathResultParser._extract_source_documents(nodes)
        assert len(docs) == 2
        assert "doc1.pdf" in docs
        assert "doc2.pdf" in docs


# =============================================================================
# T022: Integration tests with mocked Neo4j
# =============================================================================


class TestExecuteMultiHop:
    """Integration tests for execute_multi_hop with mocked Neo4j."""

    @pytest.fixture
    def mock_connection_manager(self) -> MagicMock:
        """Create mock connection manager."""
        manager = MagicMock()
        session = AsyncMock()
        manager.get_neo4j_session.return_value.__aenter__ = AsyncMock(return_value=session)
        manager.get_neo4j_session.return_value.__aexit__ = AsyncMock(return_value=None)
        return manager

    @pytest.mark.asyncio
    async def test_execute_requires_connection_manager(self) -> None:
        """Test that execute requires connection manager."""
        query = MultiHopQuery(start_entity="Intel")
        with pytest.raises(ValueError, match="connection_manager is required"):
            await execute_multi_hop(None, query)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_execute_returns_empty_on_no_results(
        self, mock_connection_manager: MagicMock
    ) -> None:
        """Test that empty results are handled gracefully."""
        # Setup mock to return empty result
        mock_result = AsyncMock()
        mock_result.__aiter__ = lambda self: iter([])

        session = AsyncMock()
        session.run.return_value = mock_result

        mock_connection_manager.get_neo4j_session.return_value.__aenter__ = AsyncMock(
            return_value=session
        )

        query = MultiHopQuery(start_entity="NonExistentEntity")
        results = await execute_multi_hop(mock_connection_manager, query, use_cache=False)

        assert results == []

    @pytest.mark.asyncio
    async def test_execute_parses_results(self, mock_connection_manager: MagicMock) -> None:
        """Test that results are properly parsed."""
        # Setup mock to return a path result - use dict directly since dict(dict) works
        mock_record = {
            "nodes": [
                {"id": "n1", "name": "Intel", "type": "company", "properties": {}},
                {"id": "n2", "name": "Mobileye", "type": "company", "properties": {}},
            ],
            "relationships": [
                {
                    "source_id": "n1",
                    "target_id": "n2",
                    "relationship_type": "RELATED_TO",
                    "subtype": "acquired",
                    "strength": 0.9,
                    "properties": {},
                }
            ],
            "cumulative_strength": 0.9,
            "hop_count": 1,
        }

        # Create proper async iterator that yields dicts
        class MockAsyncIterator:
            def __init__(self, items: list[Any]) -> None:
                self.items = items
                self.index = 0

            def __aiter__(self) -> MockAsyncIterator:
                return self

            async def __anext__(self) -> Any:
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_result = MockAsyncIterator([mock_record])

        session = AsyncMock()
        session.run.return_value = mock_result

        mock_connection_manager.get_neo4j_session.return_value.__aenter__ = AsyncMock(
            return_value=session
        )

        query = MultiHopQuery(start_entity="Intel")
        results = await execute_multi_hop(mock_connection_manager, query, use_cache=False)

        assert len(results) == 1
        assert results[0].nodes[0].name == "Intel"
        assert results[0].nodes[1].name == "Mobileye"
        assert results[0].steps[0].subtype == "acquired"

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self, mock_connection_manager: MagicMock) -> None:
        """Test that exceptions are handled gracefully."""
        mock_connection_manager.get_neo4j_session.return_value.__aenter__.side_effect = Exception(
            "Connection failed"
        )

        query = MultiHopQuery(start_entity="Intel")
        results = await execute_multi_hop(mock_connection_manager, query, use_cache=False)

        assert results == []


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture
    def mock_connection_manager(self) -> MagicMock:
        """Create mock connection manager."""
        manager = MagicMock()
        return manager

    @pytest.mark.asyncio
    async def test_find_paths_between_creates_correct_query(
        self, mock_connection_manager: MagicMock
    ) -> None:
        """Test find_paths_between creates query with both entities."""
        with patch(
            "src.agentic_rag.graph.multi_hop.execute_multi_hop", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = []

            await find_paths_between(
                mock_connection_manager,
                start_entity="Intel",
                end_entity="AMD",
                max_hops=2,
            )

            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            query = call_args[0][1]
            assert query.start_entity == "Intel"
            assert query.end_entity == "AMD"
            assert query.max_hops == 2

    @pytest.mark.asyncio
    async def test_explore_neighborhood_creates_correct_query(
        self, mock_connection_manager: MagicMock
    ) -> None:
        """Test explore_entity_neighborhood creates query without end entity."""
        with patch(
            "src.agentic_rag.graph.multi_hop.execute_multi_hop", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = []

            await explore_entity_neighborhood(
                mock_connection_manager,
                entity="Intel",
                hops=2,
                entity_type="organization",
            )

            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            query = call_args[0][1]
            assert query.start_entity == "Intel"
            assert query.end_entity is None
            assert query.max_hops == 2
            assert query.entity_type_filter == "organization"


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_path_with_zero_strength_edge(self) -> None:
        """Test path with zero strength edge."""
        steps = [
            PathStep(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="weak",
                strength=0.0,
            ),
            PathStep(
                source_id="n2",
                target_id="n3",
                relationship_type="RELATED_TO",
                subtype="strong",
                strength=0.9,
            ),
        ]
        strength = PathResultParser.calculate_path_strength(steps)
        assert strength == 0.0  # Product with zero is zero

    def test_query_with_special_characters_in_entity(self) -> None:
        """Test query with special characters in entity name."""
        query = MultiHopQuery(start_entity="Intel (Corporation)")
        assert query.start_entity == "Intel (Corporation)"

    def test_builder_hop_range_validation(self) -> None:
        """Test hop range validation in builder."""
        builder = MultiHopQueryBuilder().start_from("Intel").with_hop_range(5, 10)
        # Should be capped to 1-3
        cypher, _ = builder.build()
        assert "*3..3" in cypher

    def test_builder_limit_validation(self) -> None:
        """Test limit validation in builder."""
        builder = MultiHopQueryBuilder().start_from("Intel").with_limit(500)
        _, params = builder.build()
        # Should be capped to 100
        assert params["limit"] == 100

    def test_path_result_with_circular_reference(self) -> None:
        """Test path with circular reference (A -> B -> A)."""
        nodes = [
            PathNode(id="n1", name="A", type="entity"),
            PathNode(id="n2", name="B", type="entity"),
            PathNode(id="n1", name="A", type="entity"),  # Back to A
        ]
        steps = [
            PathStep(
                source_id="n1", target_id="n2", relationship_type="R", subtype="x", strength=0.5
            ),
            PathStep(
                source_id="n2", target_id="n1", relationship_type="R", subtype="y", strength=0.5
            ),
        ]
        result = PathResult(nodes=nodes, steps=steps, cumulative_strength=0.25, hop_count=2)
        summary = result.get_path_summary()
        assert "A" in summary
        assert "B" in summary

    def test_parse_record_with_missing_fields(self) -> None:
        """Test parsing record with missing optional fields."""
        record: dict[str, Any] = {
            "nodes": [{"id": "n1", "name": "Intel", "type": "company"}],
            "relationships": [],
            # Missing cumulative_strength, hop_count
        }
        result = PathResultParser.parse_record(record)
        assert result.nodes[0].name == "Intel"
        assert result.cumulative_strength == 0.0  # Calculated from empty steps


# =============================================================================
# Performance / Boundary Tests
# =============================================================================


class TestPerformanceBoundaries:
    """Tests for performance-related boundaries."""

    def test_query_limit_respects_maximum(self) -> None:
        """Test that query limit is capped at 100."""
        query = MultiHopQuery(start_entity="Intel", limit=100)
        assert query.limit == 100

    def test_query_hop_depth_respects_maximum(self) -> None:
        """Test that hop depth is capped at 3."""
        query = MultiHopQuery(start_entity="Intel", max_hops=3)
        assert query.max_hops == 3

    def test_parse_many_records(self) -> None:
        """Test parsing many records (50+)."""
        records = []
        for i in range(55):
            records.append(
                {
                    "nodes": [{"id": f"n{i}", "name": f"Entity{i}", "type": "x", "properties": {}}],
                    "relationships": [],
                    "cumulative_strength": i / 100.0,
                    "hop_count": 0,
                }
            )

        results = PathResultParser.parse_records(records)
        assert len(results) == 55
        # Should be sorted by strength descending
        assert results[0].cumulative_strength > results[-1].cumulative_strength
