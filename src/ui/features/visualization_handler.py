"""
Visualization handler for Graph Explorer dashboard.

Provides graph data fetching, pyvis network rendering, and filter application.
This handler bridges between the UI layer and graph query modules, providing
a simplified interface for the Streamlit page.

Key capabilities:
- Entity search with type filtering
- Subgraph fetching around entities
- pyvis network generation with custom styling
- Entity detail fetching for sidebar
- Progressive neighbor expansion
- Export to HTML/PNG
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

import structlog
from pyvis.network import Network

from src.agentic_rag.graph.visualization_queries import (
    DEFAULT_MAX_NODES,
    DEFAULT_STRENGTH_THRESHOLD,
    EntitySearchResult,
    SubgraphEdge,
    SubgraphNode,
    SubgraphResult,
    expand_entity_neighbors,
    fetch_entity_subgraph,
    fetch_temporal_facts,
    search_entities,
)
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.ui.components.entity_detail import (
    EntityDetail,
    EntityFact,
    EntityRelationship,
)

if TYPE_CHECKING:
    from src.ui.components.graph_filters import GraphFilterState

logger = structlog.get_logger(__name__)


# Entity type color palette (consistent with dashboard_utils.py)
ENTITY_TYPE_COLORS = {
    "person": "#4C8EDA",
    "company": "#FF6B6B",
    "organization": "#57C7E3",
    "location": "#FFC454",
    "event": "#F16667",
    "technology": "#8DCC93",
    "product": "#A78BFA",
    "concept": "#D9A5B3",
    "financial_metric": "#F0B95A",
}
DEFAULT_ENTITY_COLOR = "#A5ABB6"

# Edge styling
DEFAULT_EDGE_COLOR = "rgba(125, 125, 125, 0.3)"
HIGHLIGHTED_EDGE_COLOR = "rgba(125, 125, 125, 0.7)"

# Network visualization defaults
DEFAULT_GRAPH_HEIGHT = "600px"
DEFAULT_GRAPH_WIDTH = "100%"
DEFAULT_BG_COLOR = "#F8F9FA"
DEFAULT_FONT_COLOR = "#2C3E50"


@dataclass
class VisualizationState:
    """
    State container for visualization data.

    Attributes:
        nodes: Current nodes in the graph
        edges: Current edges in the graph
        selected_entity_id: Currently selected entity ID
        center_entity_id: Center of current subgraph
        search_results: Latest search results
        query_time_ms: Last query execution time
    """

    nodes: list[SubgraphNode] = field(default_factory=list)
    edges: list[SubgraphEdge] = field(default_factory=list)
    selected_entity_id: str | None = None
    center_entity_id: str | None = None
    search_results: list[EntitySearchResult] = field(default_factory=list)
    query_time_ms: float = 0.0

    def get_node_ids(self) -> list[str]:
        """Get list of current node IDs."""
        return [n.id for n in self.nodes]

    def clear(self) -> None:
        """Clear all visualization data."""
        self.nodes = []
        self.edges = []
        self.selected_entity_id = None
        self.center_entity_id = None
        self.search_results = []
        self.query_time_ms = 0.0


class VisualizationHandler:
    """
    Handler for graph visualization operations.

    Manages graph data fetching, pyvis rendering, and state management
    for the Graph Explorer dashboard.
    """

    def __init__(self, connection_manager: ConnectionManager | None = None):
        """
        Initialize visualization handler.

        Args:
            connection_manager: Database connection manager (creates if None)
        """
        self._connection_manager = connection_manager
        self._state = VisualizationState()
        self._initialized = False

        logger.info(
            "VisualizationHandler created",
            has_connection_manager=connection_manager is not None,
        )

    async def initialize(self) -> None:
        """Initialize handler with connection manager."""
        if self._initialized:
            return

        if self._connection_manager is None:
            self._connection_manager = ConnectionManager()
            await self._connection_manager.initialize()

        self._initialized = True
        logger.info("VisualizationHandler initialized")

    @property
    def connection_manager(self) -> ConnectionManager:
        """Get connection manager, raising if not initialized."""
        if self._connection_manager is None:
            raise RuntimeError("VisualizationHandler not initialized. Call initialize() first.")
        return self._connection_manager

    @property
    def state(self) -> VisualizationState:
        """Get current visualization state."""
        return self._state

    async def search_entities(
        self,
        search_term: str | None = None,
        entity_types: list[str] | None = None,
        limit: int = 50,
    ) -> list[EntitySearchResult]:
        """
        Search for entities matching criteria.

        Args:
            search_term: Optional name search pattern
            entity_types: Optional entity type filter
            limit: Maximum results

        Returns:
            List of matching entities
        """
        logger.info(
            "VisualizationHandler.search_entities called",
            search_term=search_term,
            entity_types=entity_types,
            limit=limit,
        )

        results = await search_entities(
            self.connection_manager,
            search_term=search_term,
            entity_types=entity_types,
            limit=limit,
        )

        self._state.search_results = results

        logger.info(
            "VisualizationHandler.search_entities completed",
            results_count=len(results),
        )

        return results

    async def load_entity_subgraph(
        self,
        entity_id: str,
        max_depth: int = 1,
        relationship_types: list[str] | None = None,
        min_strength: float = DEFAULT_STRENGTH_THRESHOLD,
        max_nodes: int = DEFAULT_MAX_NODES,
    ) -> SubgraphResult:
        """
        Load subgraph centered on an entity.

        Args:
            entity_id: Central entity ID
            max_depth: Maximum relationship depth
            relationship_types: Optional relationship type filter
            min_strength: Minimum relationship strength
            max_nodes: Maximum nodes to load

        Returns:
            SubgraphResult with nodes and edges
        """
        start_time = datetime.now()

        logger.info(
            "VisualizationHandler.load_entity_subgraph called",
            entity_id=entity_id,
            max_depth=max_depth,
            relationship_types=relationship_types,
            min_strength=min_strength,
            max_nodes=max_nodes,
        )

        result = await fetch_entity_subgraph(
            self.connection_manager,
            entity_id=entity_id,
            max_depth=max_depth,
            relationship_types=relationship_types,
            min_strength=min_strength,
            max_nodes=max_nodes,
        )

        # Update state
        self._state.nodes = result.nodes
        self._state.edges = result.edges
        self._state.center_entity_id = entity_id
        self._state.query_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "VisualizationHandler.load_entity_subgraph completed",
            nodes_count=len(result.nodes),
            edges_count=len(result.edges),
            query_time_ms=self._state.query_time_ms,
        )

        return result

    async def expand_neighbors(
        self,
        entity_id: str,
        max_neighbors: int = 20,
        min_strength: float = DEFAULT_STRENGTH_THRESHOLD,
    ) -> tuple[list[SubgraphNode], list[SubgraphEdge]]:
        """
        Expand neighbors for an entity, adding to current graph.

        Args:
            entity_id: Entity to expand from
            max_neighbors: Maximum new neighbors
            min_strength: Minimum relationship strength

        Returns:
            Tuple of (new_nodes, new_edges)
        """
        logger.info(
            "VisualizationHandler.expand_neighbors called",
            entity_id=entity_id,
            existing_nodes=len(self._state.nodes),
            max_neighbors=max_neighbors,
        )

        existing_ids = self._state.get_node_ids()

        new_nodes, new_edges = await expand_entity_neighbors(
            self.connection_manager,
            entity_id=entity_id,
            existing_ids=existing_ids,
            max_neighbors=max_neighbors,
            min_strength=min_strength,
        )

        # Add to state
        self._state.nodes.extend(new_nodes)
        self._state.edges.extend(new_edges)

        logger.info(
            "VisualizationHandler.expand_neighbors completed",
            new_nodes=len(new_nodes),
            new_edges=len(new_edges),
            total_nodes=len(self._state.nodes),
        )

        return new_nodes, new_edges

    async def get_entity_detail(
        self,
        entity_id: str,
        include_facts: bool = True,
    ) -> EntityDetail | None:
        """
        Get detailed information for an entity.

        Args:
            entity_id: Entity to get details for
            include_facts: Whether to fetch temporal facts

        Returns:
            EntityDetail or None if not found
        """
        logger.info(
            "VisualizationHandler.get_entity_detail called",
            entity_id=entity_id,
            include_facts=include_facts,
        )

        # Find entity in current nodes
        entity_node = None
        for node in self._state.nodes:
            if node.id == entity_id:
                entity_node = node
                break

        if entity_node is None:
            logger.warning("Entity not found in current graph", entity_id=entity_id)
            return None

        # Find relationships for this entity
        relationships: list[EntityRelationship] = []
        for edge in self._state.edges:
            if edge.source_id == entity_id:
                # Find target node
                target = next((n for n in self._state.nodes if n.id == edge.target_id), None)
                if target:
                    relationships.append(
                        EntityRelationship(
                            target_id=target.id,
                            target_name=target.name,
                            target_type=target.type,
                            relationship_type=edge.relationship_type,
                            subtype=edge.subtype,
                            strength=edge.strength,
                        )
                    )
            elif edge.target_id == entity_id:
                # Find source node
                source = next((n for n in self._state.nodes if n.id == edge.source_id), None)
                if source:
                    relationships.append(
                        EntityRelationship(
                            target_id=source.id,
                            target_name=source.name,
                            target_type=source.type,
                            relationship_type=edge.relationship_type,
                            subtype=edge.subtype,
                            strength=edge.strength,
                        )
                    )

        # Fetch temporal facts if requested
        facts: list[EntityFact] = []
        if include_facts:
            temporal_facts = await fetch_temporal_facts(
                self.connection_manager,
                entity_id=entity_id,
            )
            for tf in temporal_facts:
                facts.append(
                    EntityFact(
                        description=tf.description,
                        valid_from=tf.valid_from,
                        valid_to=tf.valid_to,
                        source=tf.source_document,
                    )
                )

        # Extract source documents from properties
        source_docs: list[str] = []
        doc_refs = entity_node.properties.get("document_refs", [])
        if isinstance(doc_refs, list):
            for ref in doc_refs:
                if isinstance(ref, dict) and "filename" in ref:
                    source_docs.append(ref["filename"])
                elif isinstance(ref, str):
                    source_docs.append(ref)

        entity_detail = EntityDetail(
            id=entity_node.id,
            name=entity_node.name,
            type=entity_node.type,
            canonical_name=entity_node.properties.get("canonical_name"),
            relationship_count=entity_node.relationship_count,
            relationships=relationships,
            facts=facts,
            properties=entity_node.properties,
            source_documents=source_docs,
        )

        self._state.selected_entity_id = entity_id

        logger.info(
            "VisualizationHandler.get_entity_detail completed",
            entity_name=entity_node.name,
            relationships_count=len(relationships),
            facts_count=len(facts),
        )

        return entity_detail

    def render_graph(
        self,
        height: str = DEFAULT_GRAPH_HEIGHT,
        width: str = DEFAULT_GRAPH_WIDTH,
        layout: str = "force_directed",
        highlight_entity_id: str | None = None,
    ) -> Network:
        """
        Render current graph state as pyvis Network.

        Args:
            height: Graph height (CSS format)
            width: Graph width (CSS format)
            layout: Layout algorithm (force_directed, hierarchical, circular)
            highlight_entity_id: Entity to highlight (selected node)

        Returns:
            Configured pyvis Network object
        """
        logger.info(
            "VisualizationHandler.render_graph called",
            nodes_count=len(self._state.nodes),
            edges_count=len(self._state.edges),
            layout=layout,
            highlight_entity_id=highlight_entity_id,
        )

        # Create network with settings
        net = Network(
            height=height,
            width=width,
            bgcolor=DEFAULT_BG_COLOR,
            font_color=DEFAULT_FONT_COLOR,
            notebook=False,
            cdn_resources="remote",
        )

        # Configure physics based on layout
        if layout == "force_directed":
            net.set_options(self._get_force_directed_options())
        elif layout == "hierarchical":
            net.set_options(self._get_hierarchical_options())
        else:
            net.toggle_physics(True)

        # Add nodes
        for node in self._state.nodes:
            color = ENTITY_TYPE_COLORS.get(node.type.lower(), DEFAULT_ENTITY_COLOR)

            # Scale node size based on relationship count
            size = max(15, min(50, 15 + node.relationship_count * 2))

            # Highlight selected node
            border_width = 4 if node.id == highlight_entity_id else 2

            # Tooltip
            title = (
                f"{node.name}\n"
                f"Type: {node.type.replace('_', ' ').title()}\n"
                f"Connections: {node.relationship_count}"
            )

            net.add_node(
                node.id,
                label=node.name[:20] if len(node.name) > 20 else node.name,
                title=title,
                color=color,
                size=size,
                borderWidth=border_width,
                borderWidthSelected=4,
                font={"size": 12, "color": DEFAULT_FONT_COLOR},
            )

        # Add edges
        added_node_ids = {n.id for n in self._state.nodes}
        for edge in self._state.edges:
            if edge.source_id in added_node_ids and edge.target_id in added_node_ids:
                # Style edge based on strength
                edge_width = max(1, min(5, edge.strength * 5))

                # Tooltip
                title = f"Relationship: {edge.subtype.replace('_', ' ').title()}\nStrength: {edge.strength:.0%}"

                net.add_edge(
                    edge.source_id,
                    edge.target_id,
                    title=title,
                    color=DEFAULT_EDGE_COLOR,
                    width=edge_width,
                )

        logger.info(
            "VisualizationHandler.render_graph completed",
            nodes_added=len(self._state.nodes),
            edges_added=len(
                [
                    e
                    for e in self._state.edges
                    if e.source_id in added_node_ids and e.target_id in added_node_ids
                ]
            ),
        )

        return net

    def render_graph_from_filters(
        self,
        filters: GraphFilterState,
        height: str = DEFAULT_GRAPH_HEIGHT,
        width: str = DEFAULT_GRAPH_WIDTH,
    ) -> Network:
        """
        Render graph with filter state applied.

        Args:
            filters: Current filter state
            height: Graph height
            width: Graph width

        Returns:
            Filtered pyvis Network
        """
        logger.info(
            "VisualizationHandler.render_graph_from_filters called",
            filter_summary=filters.to_dict(),
        )

        # Filter nodes by entity type if specified
        filtered_nodes = self._state.nodes
        if filters.entity_types:
            type_set = {t.lower() for t in filters.entity_types}
            filtered_nodes = [n for n in filtered_nodes if n.type.lower() in type_set]

        # Filter edges by relationship type and strength
        filtered_edges = self._state.edges
        if filters.relationship_types:
            rel_set = {r.lower() for r in filters.relationship_types}
            filtered_edges = [e for e in filtered_edges if e.subtype.lower() in rel_set]

        # Filter by strength threshold
        filtered_edges = [e for e in filtered_edges if e.strength >= filters.min_strength]

        # Create temporary state for rendering
        original_nodes = self._state.nodes
        original_edges = self._state.edges

        self._state.nodes = filtered_nodes[: filters.max_nodes]
        self._state.edges = filtered_edges

        net = self.render_graph(
            height=height,
            width=width,
            highlight_entity_id=self._state.selected_entity_id,
        )

        # Restore original state
        self._state.nodes = original_nodes
        self._state.edges = original_edges

        return net

    def export_to_html(self, filename: str = "graph.html") -> str:
        """
        Export current graph to HTML file.

        Args:
            filename: Output filename

        Returns:
            Path to exported file
        """
        logger.info("VisualizationHandler.export_to_html called", filename=filename)

        net = self.render_graph()
        net.save_graph(filename)

        logger.info("Graph exported to HTML", filename=filename)
        return filename

    def get_graph_html(self, height: str = DEFAULT_GRAPH_HEIGHT) -> str:
        """
        Get graph as HTML string for embedding.

        Args:
            height: Graph height

        Returns:
            HTML string
        """
        net = self.render_graph(height=height)

        # Generate HTML without saving to file
        html: str = net.generate_html()
        return html

    def clear_state(self) -> None:
        """Clear all visualization state."""
        self._state.clear()
        logger.info("VisualizationHandler state cleared")

    def _get_force_directed_options(self) -> str:
        """Get pyvis options for force-directed layout."""
        return """
        {
            "physics": {
                "enabled": true,
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 200,
                    "springConstant": 0.08,
                    "damping": 0.4,
                    "avoidOverlap": 0.5
                },
                "maxVelocity": 50,
                "minVelocity": 0.1,
                "solver": "forceAtlas2Based",
                "timestep": 0.35,
                "stabilization": {
                    "enabled": true,
                    "iterations": 100,
                    "updateInterval": 25
                }
            },
            "interaction": {
                "dragNodes": true,
                "dragView": true,
                "zoomView": true,
                "hover": true,
                "navigationButtons": true,
                "keyboard": {
                    "enabled": true
                }
            },
            "nodes": {
                "borderWidth": 2,
                "borderWidthSelected": 4,
                "font": {
                    "size": 14,
                    "face": "arial"
                }
            },
            "edges": {
                "color": {
                    "color": "rgba(125, 125, 125, 0.3)",
                    "highlight": "rgba(125, 125, 125, 0.7)",
                    "hover": "rgba(125, 125, 125, 0.5)"
                },
                "smooth": {
                    "enabled": true,
                    "type": "continuous"
                }
            }
        }
        """

    def _get_hierarchical_options(self) -> str:
        """Get pyvis options for hierarchical layout."""
        return """
        {
            "layout": {
                "hierarchical": {
                    "enabled": true,
                    "direction": "UD",
                    "sortMethod": "directed"
                }
            },
            "physics": {
                "enabled": false
            },
            "interaction": {
                "dragNodes": true,
                "dragView": true,
                "zoomView": true,
                "hover": true,
                "navigationButtons": true
            }
        }
        """


async def get_visualization_handler() -> VisualizationHandler:
    """
    Get initialized visualization handler singleton.

    Returns:
        Initialized VisualizationHandler instance
    """
    # Use module-level singleton
    global _visualization_handler

    if "_visualization_handler" not in globals() or _visualization_handler is None:
        _visualization_handler = VisualizationHandler()
        await _visualization_handler.initialize()

    return _visualization_handler


# Module-level singleton
_visualization_handler: VisualizationHandler | None = None
