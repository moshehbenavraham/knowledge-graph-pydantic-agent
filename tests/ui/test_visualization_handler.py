"""
Unit tests for VisualizationHandler.

Tests graph data fetching, pyvis rendering, and state management.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agentic_rag.graph.visualization_queries import (
    EntitySearchResult,
    SubgraphEdge,
    SubgraphNode,
    SubgraphResult,
)
from src.ui.components.graph_filters import GraphFilterState
from src.ui.features.visualization_handler import (
    ENTITY_TYPE_COLORS,
    VisualizationHandler,
    VisualizationState,
)


class TestVisualizationState:
    """Tests for VisualizationState dataclass."""

    def test_state_initialization(self) -> None:
        """Test VisualizationState default initialization."""
        state = VisualizationState()

        assert state.nodes == []
        assert state.edges == []
        assert state.selected_entity_id is None
        assert state.center_entity_id is None
        assert state.search_results == []
        assert state.query_time_ms == 0.0

    def test_get_node_ids(self) -> None:
        """Test get_node_ids returns list of node IDs."""
        state = VisualizationState()
        state.nodes = [
            SubgraphNode(id="n1", name="Node 1", type="company"),
            SubgraphNode(id="n2", name="Node 2", type="person"),
        ]

        ids = state.get_node_ids()

        assert ids == ["n1", "n2"]

    def test_clear_state(self) -> None:
        """Test clear resets all state."""
        state = VisualizationState()
        state.nodes = [SubgraphNode(id="n1", name="Node", type="company")]
        state.edges = [
            SubgraphEdge(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="test",
                strength=0.5,
            )
        ]
        state.selected_entity_id = "n1"

        state.clear()

        assert state.nodes == []
        assert state.edges == []
        assert state.selected_entity_id is None


class TestVisualizationHandler:
    """Tests for VisualizationHandler class."""

    def test_handler_initialization(self) -> None:
        """Test handler initialization without connection manager."""
        handler = VisualizationHandler()

        assert handler._connection_manager is None
        assert handler._initialized is False
        assert handler.state is not None

    def test_handler_with_connection_manager(self) -> None:
        """Test handler initialization with connection manager."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        assert handler._connection_manager == mock_cm

    @pytest.mark.asyncio
    async def test_handler_initialize(self) -> None:
        """Test handler initialize method."""
        with patch("src.ui.features.visualization_handler.ConnectionManager") as mock_cm_class:
            mock_cm = MagicMock()
            mock_cm_class.create = AsyncMock(return_value=mock_cm)

            handler = VisualizationHandler()
            await handler.initialize()

            assert handler._initialized is True
            mock_cm_class.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_handler_initialize_with_existing_cm(self) -> None:
        """Test handler initialize with existing connection manager."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)
        await handler.initialize()

        assert handler._initialized is True
        assert handler._connection_manager == mock_cm

    def test_connection_manager_property_raises_if_not_initialized(self) -> None:
        """Test connection_manager property raises if not initialized."""
        handler = VisualizationHandler()

        with pytest.raises(RuntimeError, match="not initialized"):
            _ = handler.connection_manager

    def test_connection_manager_property_returns_cm(self) -> None:
        """Test connection_manager property returns connection manager."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        assert handler.connection_manager == mock_cm


class TestVisualizationHandlerSearchEntities:
    """Tests for VisualizationHandler.search_entities method."""

    @pytest.mark.asyncio
    async def test_search_entities_updates_state(self) -> None:
        """Test search_entities updates handler state."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        mock_results = [
            EntitySearchResult(id="e1", name="Entity 1", type="company", relationship_count=5),
        ]

        with patch(
            "src.ui.features.visualization_handler.search_entities",
            new=AsyncMock(return_value=mock_results),
        ):
            results = await handler.search_entities(search_term="test")

            assert len(results) == 1
            assert handler.state.search_results == mock_results

    @pytest.mark.asyncio
    async def test_search_entities_with_filters(self) -> None:
        """Test search_entities with entity type filters."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        with patch(
            "src.ui.features.visualization_handler.search_entities",
            new=AsyncMock(return_value=[]),
        ) as mock_search:
            await handler.search_entities(
                search_term="Intel",
                entity_types=["company"],
                limit=25,
            )

            mock_search.assert_called_once()


class TestVisualizationHandlerLoadSubgraph:
    """Tests for VisualizationHandler.load_entity_subgraph method."""

    @pytest.mark.asyncio
    async def test_load_subgraph_updates_state(self) -> None:
        """Test load_entity_subgraph updates handler state."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        mock_result = SubgraphResult(
            nodes=[SubgraphNode(id="n1", name="Node", type="company")],
            edges=[],
            center_entity_id="n1",
        )

        with patch(
            "src.ui.features.visualization_handler.fetch_entity_subgraph",
            new=AsyncMock(return_value=mock_result),
        ):
            result = await handler.load_entity_subgraph(entity_id="n1")

            assert result.center_entity_id == "n1"
            assert len(handler.state.nodes) == 1
            assert handler.state.center_entity_id == "n1"


class TestVisualizationHandlerExpandNeighbors:
    """Tests for VisualizationHandler.expand_neighbors method."""

    @pytest.mark.asyncio
    async def test_expand_neighbors_adds_to_state(self) -> None:
        """Test expand_neighbors adds new nodes and edges."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        # Set initial state
        handler._state.nodes = [SubgraphNode(id="n1", name="Center", type="company")]
        handler._state.edges = []

        new_nodes = [SubgraphNode(id="n2", name="Neighbor", type="person")]
        new_edges = [
            SubgraphEdge(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="employs",
                strength=0.8,
            )
        ]

        with patch(
            "src.ui.features.visualization_handler.expand_entity_neighbors",
            new=AsyncMock(return_value=(new_nodes, new_edges)),
        ):
            nodes, edges = await handler.expand_neighbors(entity_id="n1")

            assert len(nodes) == 1
            assert len(edges) == 1
            assert len(handler.state.nodes) == 2
            assert len(handler.state.edges) == 1


class TestVisualizationHandlerGetEntityDetail:
    """Tests for VisualizationHandler.get_entity_detail method."""

    @pytest.mark.asyncio
    async def test_get_entity_detail_returns_detail(self) -> None:
        """Test get_entity_detail returns EntityDetail."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        # Set up state with entity
        handler._state.nodes = [
            SubgraphNode(
                id="n1",
                name="Test Entity",
                type="company",
                relationship_count=3,
                properties={"canonical_name": "Test Corp"},
            )
        ]
        handler._state.edges = [
            SubgraphEdge(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="owns",
                strength=0.9,
            )
        ]

        with patch(
            "src.ui.features.visualization_handler.fetch_temporal_facts",
            new=AsyncMock(return_value=[]),
        ):
            detail = await handler.get_entity_detail(entity_id="n1")

            assert detail is not None
            assert detail.name == "Test Entity"
            assert detail.type == "company"
            assert handler.state.selected_entity_id == "n1"

    @pytest.mark.asyncio
    async def test_get_entity_detail_not_found(self) -> None:
        """Test get_entity_detail returns None for missing entity."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        handler._state.nodes = []

        detail = await handler.get_entity_detail(entity_id="missing")

        assert detail is None


class TestVisualizationHandlerRenderGraph:
    """Tests for VisualizationHandler.render_graph method."""

    def test_render_graph_returns_network(self) -> None:
        """Test render_graph returns pyvis Network."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        handler._state.nodes = [
            SubgraphNode(id="n1", name="Node 1", type="company", relationship_count=5),
            SubgraphNode(id="n2", name="Node 2", type="person", relationship_count=3),
        ]
        handler._state.edges = [
            SubgraphEdge(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="employs",
                strength=0.8,
            )
        ]

        net = handler.render_graph()

        # Verify network was created with nodes and edges
        assert net is not None
        assert len(net.nodes) == 2
        assert len(net.edges) == 1

    def test_render_graph_with_highlight(self) -> None:
        """Test render_graph highlights selected entity."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        handler._state.nodes = [
            SubgraphNode(id="n1", name="Node 1", type="company"),
        ]

        net = handler.render_graph(highlight_entity_id="n1")

        assert net is not None

    def test_render_graph_empty_state(self) -> None:
        """Test render_graph with empty state."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        net = handler.render_graph()

        assert net is not None
        assert len(net.nodes) == 0


class TestVisualizationHandlerRenderFromFilters:
    """Tests for VisualizationHandler.render_graph_from_filters method."""

    def test_render_with_entity_type_filter(self) -> None:
        """Test render_graph_from_filters with entity type filter."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        handler._state.nodes = [
            SubgraphNode(id="n1", name="Company", type="company"),
            SubgraphNode(id="n2", name="Person", type="person"),
        ]
        handler._state.edges = []

        filters = GraphFilterState(
            entity_types=["company"],
            min_strength=0.3,
            max_nodes=100,
        )

        net = handler.render_graph_from_filters(filters)

        # Should only include company nodes
        assert len(net.nodes) == 1

    def test_render_with_strength_filter(self) -> None:
        """Test render_graph_from_filters with strength threshold."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        handler._state.nodes = [
            SubgraphNode(id="n1", name="Node 1", type="company"),
            SubgraphNode(id="n2", name="Node 2", type="company"),
        ]
        handler._state.edges = [
            SubgraphEdge(
                source_id="n1",
                target_id="n2",
                relationship_type="RELATED_TO",
                subtype="weak",
                strength=0.2,
            ),
        ]

        filters = GraphFilterState(min_strength=0.5)

        net = handler.render_graph_from_filters(filters)

        # Edge should be filtered out due to low strength
        assert len(net.edges) == 0


class TestVisualizationHandlerExport:
    """Tests for VisualizationHandler export methods."""

    def test_get_graph_html(self) -> None:
        """Test get_graph_html returns HTML string."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        handler._state.nodes = [
            SubgraphNode(id="n1", name="Node", type="company"),
        ]

        html = handler.get_graph_html()

        assert isinstance(html, str)
        assert "<html>" in html.lower() or "<!doctype" in html.lower()

    def test_clear_state(self) -> None:
        """Test clear_state resets handler state."""
        mock_cm = MagicMock()
        handler = VisualizationHandler(connection_manager=mock_cm)

        handler._state.nodes = [SubgraphNode(id="n1", name="Node", type="company")]
        handler._state.selected_entity_id = "n1"

        handler.clear_state()

        assert handler.state.nodes == []
        assert handler.state.selected_entity_id is None


class TestEntityTypeColors:
    """Tests for entity type color constants."""

    def test_common_types_have_colors(self) -> None:
        """Test that common entity types have assigned colors."""
        common_types = ["person", "company", "organization", "product", "technology"]

        for entity_type in common_types:
            assert entity_type in ENTITY_TYPE_COLORS
            assert ENTITY_TYPE_COLORS[entity_type].startswith("#")

    def test_colors_are_valid_hex(self) -> None:
        """Test that all colors are valid hex codes."""
        for color in ENTITY_TYPE_COLORS.values():
            assert color.startswith("#")
            assert len(color) == 7
