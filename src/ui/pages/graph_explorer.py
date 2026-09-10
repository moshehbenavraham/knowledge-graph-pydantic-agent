"""
Graph Explorer page for interactive knowledge graph visualization.

This page provides:
- Entity search with type filtering
- Interactive graph visualization using pyvis
- Entity detail sidebar on node selection
- Filter controls (type, strength, temporal)
- Expand neighbors and export functionality

The page integrates with the VisualizationHandler for data operations
and uses Streamlit components for the UI.
"""

from __future__ import annotations

import asyncio
import tempfile
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
import structlog

from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.ui.components.entity_detail import (
    render_empty_selection_state,
    render_entity_detail_panel,
)
from src.ui.components.graph_filters import (
    GraphFilterState,
    initialize_filter_state,
    render_filter_sidebar,
    render_filter_summary,
    render_reset_button,
)
from src.ui.features.visualization_handler import VisualizationHandler

logger = structlog.get_logger(__name__)

# Page configuration
PAGE_TITLE = "Graph Explorer"
PAGE_ICON = "network"
GRAPH_HEIGHT = 600
GRAPH_WIDTH_PERCENT = 100

# Session state keys
STATE_HANDLER = "graph_explorer_handler"
STATE_INITIALIZED = "graph_explorer_initialized"
STATE_SELECTED_ENTITY = "graph_explorer_selected_entity"
STATE_GRAPH_HTML = "graph_explorer_graph_html"
STATE_SEARCH_RESULTS = "graph_explorer_search_results"
STATE_ENTITY_DETAIL = "graph_explorer_entity_detail"
STATE_LOADING = "graph_explorer_loading"


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get existing event loop or create a new one."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def run_async(coro: Any) -> Any:
    """Run async coroutine in sync context."""
    loop = get_or_create_event_loop()
    return loop.run_until_complete(coro)


async def initialize_handler() -> VisualizationHandler:
    """Initialize visualization handler with connection manager."""
    connection_manager = ConnectionManager()
    await connection_manager.initialize()
    handler = VisualizationHandler(connection_manager)
    await handler.initialize()
    return handler


def get_handler() -> VisualizationHandler:
    """Get or create visualization handler from session state."""
    if STATE_HANDLER not in st.session_state:
        with st.spinner("Initializing Graph Explorer..."):
            handler = run_async(initialize_handler())
            st.session_state[STATE_HANDLER] = handler
            st.session_state[STATE_INITIALIZED] = True
    result: VisualizationHandler = st.session_state[STATE_HANDLER]
    return result


def initialize_session_state() -> None:
    """Initialize page-specific session state."""
    defaults: dict[str, Any] = {
        STATE_SELECTED_ENTITY: None,
        STATE_GRAPH_HTML: None,
        STATE_SEARCH_RESULTS: [],
        STATE_ENTITY_DETAIL: None,
        STATE_LOADING: False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize filter state
    initialize_filter_state("graph_filter")


def search_entities(handler: VisualizationHandler, filters: GraphFilterState) -> None:
    """Execute entity search with current filters."""
    st.session_state[STATE_LOADING] = True

    try:
        results = run_async(
            handler.search_entities(
                search_term=filters.search_term or None,
                entity_types=filters.entity_types or None,
                limit=50,
            )
        )
        st.session_state[STATE_SEARCH_RESULTS] = results

        logger.info(
            "Entity search completed",
            results_count=len(results),
            search_term=filters.search_term,
            entity_types=filters.entity_types,
        )
    except Exception as e:
        logger.exception("Entity search failed", error=str(e))
        st.error(f"Search failed: {e}")
    finally:
        st.session_state[STATE_LOADING] = False


def load_entity_graph(
    handler: VisualizationHandler, entity_id: str, filters: GraphFilterState
) -> None:
    """Load subgraph centered on entity and render."""
    st.session_state[STATE_LOADING] = True

    try:
        # Fetch subgraph
        run_async(
            handler.load_entity_subgraph(
                entity_id=entity_id,
                max_depth=filters.max_depth,
                relationship_types=filters.relationship_types or None,
                min_strength=filters.min_strength,
                max_nodes=filters.max_nodes,
            )
        )

        # Render graph with filters
        net = handler.render_graph_from_filters(
            filters=filters,
            height=f"{GRAPH_HEIGHT}px",
        )

        # Get HTML
        html = net.generate_html()
        st.session_state[STATE_GRAPH_HTML] = html
        st.session_state[STATE_SELECTED_ENTITY] = entity_id

        logger.info(
            "Entity graph loaded",
            entity_id=entity_id,
            nodes_count=len(handler.state.nodes),
            edges_count=len(handler.state.edges),
        )
    except Exception as e:
        logger.exception("Failed to load entity graph", error=str(e))
        st.error(f"Failed to load graph: {e}")
    finally:
        st.session_state[STATE_LOADING] = False


def expand_entity_neighbors(
    handler: VisualizationHandler, entity_id: str, filters: GraphFilterState
) -> None:
    """Expand neighbors for an entity."""
    st.session_state[STATE_LOADING] = True

    try:
        run_async(
            handler.expand_neighbors(
                entity_id=entity_id,
                max_neighbors=20,
                min_strength=filters.min_strength,
            )
        )

        # Re-render graph
        net = handler.render_graph_from_filters(
            filters=filters,
            height=f"{GRAPH_HEIGHT}px",
        )
        html = net.generate_html()
        st.session_state[STATE_GRAPH_HTML] = html

        logger.info(
            "Neighbors expanded",
            entity_id=entity_id,
            total_nodes=len(handler.state.nodes),
        )
    except Exception as e:
        logger.exception("Failed to expand neighbors", error=str(e))
        st.error(f"Failed to expand: {e}")
    finally:
        st.session_state[STATE_LOADING] = False


def select_entity(handler: VisualizationHandler, entity_id: str) -> None:
    """Select entity and load its details."""
    try:
        detail = run_async(handler.get_entity_detail(entity_id))
        st.session_state[STATE_ENTITY_DETAIL] = detail
        st.session_state[STATE_SELECTED_ENTITY] = entity_id

        logger.info(
            "Entity selected",
            entity_id=entity_id,
            entity_name=detail.name if detail else None,
        )
    except Exception as e:
        logger.exception("Failed to get entity detail", error=str(e))


def export_graph(handler: VisualizationHandler, format_type: str = "html") -> str | None:
    """Export current graph to file."""
    try:
        if format_type == "html":
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                html = handler.get_graph_html()
                f.write(html)
                return f.name
        return None
    except Exception as e:
        logger.exception("Failed to export graph", error=str(e))
        st.error(f"Export failed: {e}")
        return None


def render_search_results(
    handler: VisualizationHandler, results: list[Any], filters: GraphFilterState
) -> None:
    """Render search results as clickable list."""
    if not results:
        st.info("No entities found. Try adjusting your search.")
        return

    st.caption(f"Found {len(results)} entities")

    for result in results[:20]:  # Limit display
        col1, col2 = st.columns([4, 1])
        with col1:
            type_label = result.type.replace("_", " ").title()
            if st.button(
                f"{result.name} ({type_label})",
                key=f"search_result_{result.id}",
                use_container_width=True,
            ):
                load_entity_graph(handler, result.id, filters)
                select_entity(handler, result.id)
                st.rerun()

        with col2:
            st.caption(f"{result.relationship_count} conn.")


def render_graph_view(handler: VisualizationHandler, filters: GraphFilterState) -> None:
    """Render the main graph visualization area."""
    # Graph toolbar
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    with col1:
        if st.button("Refresh Graph", use_container_width=True):
            if st.session_state[STATE_SELECTED_ENTITY]:
                load_entity_graph(handler, st.session_state[STATE_SELECTED_ENTITY], filters)
                st.rerun()

    with col2:
        selected_entity = st.session_state.get(STATE_ENTITY_DETAIL)
        if selected_entity and st.button("Expand Neighbors", use_container_width=True):
            expand_entity_neighbors(handler, selected_entity.id, filters)
            st.rerun()

    with col3:
        if st.button("Export HTML", use_container_width=True):
            filepath = export_graph(handler, "html")
            if filepath:
                st.success(f"Exported to {filepath}")

    with col4:
        if st.button("Clear", use_container_width=True):
            handler.clear_state()
            st.session_state[STATE_GRAPH_HTML] = None
            st.session_state[STATE_SELECTED_ENTITY] = None
            st.session_state[STATE_ENTITY_DETAIL] = None
            st.rerun()

    # Render graph or placeholder
    graph_html = st.session_state.get(STATE_GRAPH_HTML)

    if graph_html:
        # Show graph statistics
        if handler.state.nodes:
            stats_col1, stats_col2, stats_col3 = st.columns(3)
            with stats_col1:
                st.metric("Nodes", len(handler.state.nodes))
            with stats_col2:
                st.metric("Edges", len(handler.state.edges))
            with stats_col3:
                st.metric("Query Time", f"{handler.state.query_time_ms:.0f}ms")

        # Embed pyvis HTML
        components.html(graph_html, height=GRAPH_HEIGHT + 50, scrolling=True)

        # Filter summary
        render_filter_summary(filters)

    else:
        # Placeholder
        st.markdown("""
            ### Welcome to Graph Explorer

            Use the search box in the sidebar to find entities, then click on one
            to visualize its connections in the knowledge graph.

            **Features:**
            - Search entities by name or type
            - Filter by relationship strength and type
            - Expand neighbors to discover connections
            - View entity details in the sidebar
            - Export graph to HTML

            **Tips:**
            - Drag nodes to reposition them
            - Scroll to zoom in/out
            - Click a node to view its details
            """)


def _make_entity_click_handler(
    handler: VisualizationHandler,
) -> Any:
    """Create click handler for entity selection."""

    def on_click(eid: str) -> None:
        select_entity(handler, eid)
        st.rerun()

    return on_click


def _make_expand_handler(
    handler: VisualizationHandler,
    filters: GraphFilterState,
) -> Any:
    """Create expand handler for neighbor expansion."""

    def on_expand(eid: str) -> None:
        expand_entity_neighbors(handler, eid, filters)
        st.rerun()

    return on_expand


def render_entity_sidebar(handler: VisualizationHandler, filters: GraphFilterState) -> None:
    """Render entity detail sidebar."""
    entity_detail = st.session_state.get(STATE_ENTITY_DETAIL)

    if entity_detail:
        render_entity_detail_panel(
            entity=entity_detail,
            on_entity_click=_make_entity_click_handler(handler),
            on_expand=_make_expand_handler(handler, filters),
            show_facts=True,
            show_documents=True,
        )
    else:
        render_empty_selection_state()


def render_page() -> None:
    """Render the Graph Explorer page."""
    logger.info("Rendering Graph Explorer page")

    # Initialize session state
    initialize_session_state()

    # Get handler
    handler = get_handler()

    # Page layout: sidebar + main content + detail panel
    # Sidebar for filters
    with st.sidebar:
        st.header("Graph Explorer")

        # Search and filters
        filters = render_filter_sidebar(
            prefix="graph_filter",
            show_temporal=True,
            show_options=True,
        )

        # Search button
        if st.button("Search Entities", type="primary", use_container_width=True):
            search_entities(handler, filters)
            st.rerun()

        # Reset button
        if render_reset_button("graph_filter"):
            handler.clear_state()
            st.session_state[STATE_GRAPH_HTML] = None
            st.session_state[STATE_SEARCH_RESULTS] = []
            st.session_state[STATE_ENTITY_DETAIL] = None
            st.rerun()

        st.divider()

        # Search results
        results = st.session_state.get(STATE_SEARCH_RESULTS, [])
        if results:
            st.subheader("Search Results")
            render_search_results(handler, results, filters)

    # Main content area
    main_col, detail_col = st.columns([3, 1])

    with main_col:
        st.header(PAGE_TITLE)

        # Loading indicator
        if st.session_state.get(STATE_LOADING):
            st.spinner("Loading...")

        # Graph view
        render_graph_view(handler, filters)

    with detail_col:
        st.subheader("Entity Details")
        render_entity_sidebar(handler, filters)


# Entry point for Streamlit page
def main() -> None:
    """Main entry point for the page."""
    render_page()


if __name__ == "__main__":
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
    )
    main()
