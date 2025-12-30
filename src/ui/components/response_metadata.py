"""
Response metadata display components.

Provides query intent badges, source counts, latency display,
and tool execution timeline for transparency and user trust.
"""

from dataclasses import dataclass, field
from typing import Any

import streamlit as st
import structlog

from src.ui.components.progress_indicators import ToolExecutionState

logger = structlog.get_logger(__name__)


@dataclass
class ResponseMetadata:
    """
    Metadata about a query response for display.

    Attributes:
        detected_intent: Detected search intent type
        strategy_used: Search strategy that was applied
        source_count: Number of sources/chunks returned
        total_latency_ms: Total response time in milliseconds
        vector_latency_ms: Vector search time (if applicable)
        graph_latency_ms: Graph search time (if applicable)
        cache_hit: Whether results came from cache
        tools_called: List of tools that were executed
        tool_states: Detailed tool execution states
        entities_found: Number of entities found
        relationships_found: Number of relationships found
    """

    detected_intent: str | None = None
    strategy_used: str | None = None
    source_count: int = 0
    total_latency_ms: float = 0.0
    vector_latency_ms: float = 0.0
    graph_latency_ms: float = 0.0
    cache_hit: bool = False
    tools_called: list[str] = field(default_factory=list)
    tool_states: list[ToolExecutionState] = field(default_factory=list)
    entities_found: int = 0
    relationships_found: int = 0


# Intent type display configuration
INTENT_DISPLAY: dict[str, dict[str, str]] = {
    "VECTOR_HEAVY": {
        "label": "Content Search",
        "description": "Semantic search through document content",
        "color": "blue",
    },
    "GRAPH_HEAVY": {
        "label": "Graph Search",
        "description": "Entity and relationship discovery",
        "color": "green",
    },
    "HYBRID": {
        "label": "Hybrid Search",
        "description": "Combined content and graph analysis",
        "color": "purple",
    },
    "TEMPORAL": {
        "label": "Timeline Search",
        "description": "Time-based information retrieval",
        "color": "orange",
    },
    "ENTITY_FOCUSED": {
        "label": "Entity Search",
        "description": "Focused entity information lookup",
        "color": "teal",
    },
    "MULTI_HOP": {
        "label": "Path Discovery",
        "description": "Multi-hop connection traversal",
        "color": "red",
    },
    "TEMPORAL_TREND": {
        "label": "Trend Analysis",
        "description": "Time-series trend identification",
        "color": "gold",
    },
    "COMPARISON": {
        "label": "Comparison",
        "description": "Cross-entity comparison analysis",
        "color": "violet",
    },
}


def get_intent_display(intent: str) -> dict[str, str]:
    """
    Get display configuration for an intent type.

    Args:
        intent: Intent type string

    Returns:
        Display configuration dict with label, description, color
    """
    intent_upper = intent.upper() if intent else ""
    return INTENT_DISPLAY.get(
        intent_upper,
        {
            "label": intent or "Unknown",
            "description": "Query processing",
            "color": "gray",
        },
    )


def render_intent_badge(
    intent: str,
    show_description: bool = False,
) -> None:
    """
    Render a query intent badge.

    Displays the detected intent type with appropriate styling.

    Args:
        intent: Detected intent type
        show_description: Whether to show intent description
    """
    if not intent:
        return

    display = get_intent_display(intent)

    # Render badge as markdown with background style simulation
    badge_text = f"**[{display['label']}]**"
    st.markdown(badge_text)

    if show_description:
        st.caption(display["description"])


def render_source_count(
    count: int,
    label: str = "sources",
) -> None:
    """
    Render source count indicator.

    Args:
        count: Number of sources
        label: Label text (e.g., 'sources', 'documents', 'chunks')
    """
    if count == 0:
        st.caption(f"No {label} found")
    elif count == 1:
        st.caption(f"1 {label[:-1] if label.endswith('s') else label}")
    else:
        st.caption(f"{count} {label}")


def render_latency_display(
    total_ms: float,
    vector_ms: float | None = None,
    graph_ms: float | None = None,
    show_breakdown: bool = False,
) -> None:
    """
    Render latency metrics display.

    Args:
        total_ms: Total latency in milliseconds
        vector_ms: Vector search latency (optional)
        graph_ms: Graph search latency (optional)
        show_breakdown: Whether to show detailed breakdown
    """
    # Format total latency
    if total_ms < 1000:
        total_str = f"{total_ms:.0f}ms"
    else:
        total_str = f"{total_ms / 1000:.2f}s"

    st.caption(f"Response time: {total_str}")

    if show_breakdown and (vector_ms or graph_ms):
        breakdown_parts = []
        if vector_ms:
            breakdown_parts.append(f"Vector: {vector_ms:.0f}ms")
        if graph_ms:
            breakdown_parts.append(f"Graph: {graph_ms:.0f}ms")

        if breakdown_parts:
            st.caption(" | ".join(breakdown_parts))


def render_response_metadata(
    metadata: ResponseMetadata,
    compact: bool = True,
    show_tools: bool = True,
) -> None:
    """
    Render complete response metadata display.

    Shows intent badge, source count, latency, and optionally
    tool execution information.

    Args:
        metadata: Response metadata to display
        compact: Use compact single-row layout
        show_tools: Whether to show tool information
    """
    if compact:
        # Compact layout: single row with key metrics
        cols = st.columns([2, 2, 2, 2])

        with cols[0]:
            if metadata.detected_intent:
                render_intent_badge(metadata.detected_intent)

        with cols[1]:
            render_source_count(metadata.source_count)

        with cols[2]:
            if metadata.total_latency_ms > 0:
                render_latency_display(metadata.total_latency_ms)

        with cols[3]:
            if metadata.cache_hit:
                st.caption("[Cached]")
            elif metadata.tools_called:
                st.caption(f"{len(metadata.tools_called)} tools")

    else:
        # Expanded layout: multiple rows with details
        st.markdown("---")
        st.markdown("**Response Details**")

        col1, col2 = st.columns(2)

        with col1:
            if metadata.detected_intent:
                render_intent_badge(metadata.detected_intent, show_description=True)

            render_source_count(metadata.source_count)

            if metadata.entities_found or metadata.relationships_found:
                entity_text = f"{metadata.entities_found} entities"
                rel_text = f"{metadata.relationships_found} relationships"
                st.caption(f"{entity_text}, {rel_text}")

        with col2:
            render_latency_display(
                metadata.total_latency_ms,
                metadata.vector_latency_ms,
                metadata.graph_latency_ms,
                show_breakdown=True,
            )

            if metadata.cache_hit:
                st.caption("[Results from cache]")

        # Tool execution details
        if show_tools and metadata.tool_states:
            st.markdown("**Tools Executed**")
            for state in metadata.tool_states:
                _render_tool_summary(state)


def _render_tool_summary(state: ToolExecutionState) -> None:
    """Render a brief tool execution summary."""
    from src.ui.components.progress_indicators import (
        STATUS_ICONS,
        get_tool_display_name,
    )

    display_name = get_tool_display_name(state.tool_name)
    icon = STATUS_ICONS.get(state.status, "[?]")

    col1, col2 = st.columns([4, 1])

    with col1:
        st.markdown(f"{icon} {display_name}")

    with col2:
        st.caption(state.elapsed_display)


def create_metadata_from_result(
    result: dict[str, Any],
    tool_states: list[ToolExecutionState] | None = None,
) -> ResponseMetadata:
    """
    Create ResponseMetadata from a search result dictionary.

    Args:
        result: Search result with metadata fields
        tool_states: Optional tool execution states

    Returns:
        ResponseMetadata populated from result
    """
    return ResponseMetadata(
        detected_intent=result.get("intent") or result.get("detected_intent"),
        strategy_used=result.get("strategy") or result.get("strategy_used"),
        source_count=result.get("chunk_count", 0)
        or len(result.get("chunks", []))
        or result.get("source_count", 0),
        total_latency_ms=result.get("total_latency_ms", 0)
        or result.get("latency_ms", 0)
        or result.get("query_time_ms", 0),
        vector_latency_ms=result.get("vector_latency_ms", 0),
        graph_latency_ms=result.get("graph_latency_ms", 0),
        cache_hit=result.get("cache_hit", False),
        tools_called=result.get("tools_called", []),
        tool_states=tool_states or [],
        entities_found=result.get("entities_found", 0),
        relationships_found=result.get("relationships_found", 0),
    )


def render_metadata_from_analytics(
    event_data: dict[str, Any],
) -> None:
    """
    Render metadata from an analytics event.

    Args:
        event_data: Analytics event data dictionary
    """
    metadata = ResponseMetadata(
        detected_intent=event_data.get("detected_intent"),
        strategy_used=event_data.get("strategy_used"),
        source_count=event_data.get("chunks_returned", 0),
        total_latency_ms=event_data.get("total_latency_ms", 0),
        vector_latency_ms=event_data.get("vector_latency_ms", 0),
        graph_latency_ms=event_data.get("graph_latency_ms", 0),
        cache_hit=event_data.get("cache_hit", False),
        entities_found=event_data.get("entities_found", 0),
        relationships_found=event_data.get("relationships_found", 0),
    )

    render_response_metadata(metadata, compact=True, show_tools=False)
