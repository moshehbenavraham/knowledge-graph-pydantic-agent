"""
Graph filter components for the Graph Explorer dashboard.

Provides Streamlit UI components for filtering graph visualizations:
- Entity type filter (multi-select dropdown)
- Relationship strength threshold slider
- Temporal date range picker
- Relationship type filter

All components use Streamlit session state for persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import streamlit as st
import structlog

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)


# Available entity types for filtering
DEFAULT_ENTITY_TYPES = [
    "company",
    "person",
    "organization",
    "product",
    "technology",
    "location",
    "event",
    "concept",
    "financial_metric",
]

# Common relationship types
DEFAULT_RELATIONSHIP_TYPES = [
    "acquired",
    "employs",
    "invested_in",
    "partnered_with",
    "competitor_of",
    "subsidiary_of",
    "located_in",
    "produces",
    "mentions",
    "related_to",
]


@dataclass
class GraphFilterState:
    """
    State container for graph filter values.

    Attributes:
        search_term: Entity name search text
        entity_types: Selected entity types
        relationship_types: Selected relationship types
        min_strength: Minimum relationship strength threshold
        start_date: Start of temporal date range
        end_date: End of temporal date range
        max_nodes: Maximum nodes to display
        max_depth: Maximum relationship depth for expansion
    """

    search_term: str = ""
    entity_types: list[str] = field(default_factory=list)
    relationship_types: list[str] = field(default_factory=list)
    min_strength: float = 0.3
    start_date: date | None = None
    end_date: date | None = None
    max_nodes: int = 100
    max_depth: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "search_term": self.search_term,
            "entity_types": self.entity_types,
            "relationship_types": self.relationship_types,
            "min_strength": self.min_strength,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "max_nodes": self.max_nodes,
            "max_depth": self.max_depth,
        }

    @classmethod
    def from_session_state(cls, prefix: str = "graph_filter") -> GraphFilterState:
        """
        Create GraphFilterState from Streamlit session state.

        Args:
            prefix: Session state key prefix

        Returns:
            GraphFilterState with values from session state
        """
        return cls(
            search_term=st.session_state.get(f"{prefix}_search_term", ""),
            entity_types=st.session_state.get(f"{prefix}_entity_types", []),
            relationship_types=st.session_state.get(f"{prefix}_relationship_types", []),
            min_strength=st.session_state.get(f"{prefix}_min_strength", 0.3),
            start_date=st.session_state.get(f"{prefix}_start_date"),
            end_date=st.session_state.get(f"{prefix}_end_date"),
            max_nodes=st.session_state.get(f"{prefix}_max_nodes", 100),
            max_depth=st.session_state.get(f"{prefix}_max_depth", 1),
        )


def initialize_filter_state(prefix: str = "graph_filter") -> None:
    """
    Initialize session state for graph filters with defaults.

    Args:
        prefix: Session state key prefix
    """
    defaults = {
        f"{prefix}_search_term": "",
        f"{prefix}_entity_types": [],
        f"{prefix}_relationship_types": [],
        f"{prefix}_min_strength": 0.3,
        f"{prefix}_start_date": None,
        f"{prefix}_end_date": None,
        f"{prefix}_max_nodes": 100,
        f"{prefix}_max_depth": 1,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def render_entity_search(
    prefix: str = "graph_filter",
    on_change: Callable[[], None] | None = None,
) -> str:
    """
    Render entity search text input.

    Args:
        prefix: Session state key prefix
        on_change: Optional callback when value changes

    Returns:
        Current search term value
    """
    key = f"{prefix}_search_term"

    search_term = st.text_input(
        "Search Entities",
        value=st.session_state.get(key, ""),
        key=key,
        placeholder="Enter entity name...",
        help="Search for entities by name (case-insensitive)",
        on_change=on_change,
    )

    return str(search_term)


def render_entity_type_filter(
    prefix: str = "graph_filter",
    available_types: list[str] | None = None,
    on_change: Callable[[], None] | None = None,
) -> list[str]:
    """
    Render entity type multi-select filter.

    Args:
        prefix: Session state key prefix
        available_types: List of available entity types
        on_change: Optional callback when selection changes

    Returns:
        List of selected entity types
    """
    if available_types is None:
        available_types = DEFAULT_ENTITY_TYPES

    key = f"{prefix}_entity_types"

    # Format display labels
    type_labels = {t: t.replace("_", " ").title() for t in available_types}

    selected = st.multiselect(
        "Entity Types",
        options=available_types,
        default=st.session_state.get(key, []),
        key=key,
        format_func=lambda x: type_labels.get(x, x),
        help="Filter by entity type (empty = all types)",
        on_change=on_change,
    )

    return selected


def render_relationship_type_filter(
    prefix: str = "graph_filter",
    available_types: list[str] | None = None,
    on_change: Callable[[], None] | None = None,
) -> list[str]:
    """
    Render relationship type multi-select filter.

    Args:
        prefix: Session state key prefix
        available_types: List of available relationship types
        on_change: Optional callback when selection changes

    Returns:
        List of selected relationship types
    """
    if available_types is None:
        available_types = DEFAULT_RELATIONSHIP_TYPES

    key = f"{prefix}_relationship_types"

    # Format display labels
    type_labels = {t: t.replace("_", " ").title() for t in available_types}

    selected = st.multiselect(
        "Relationship Types",
        options=available_types,
        default=st.session_state.get(key, []),
        key=key,
        format_func=lambda x: type_labels.get(x, x),
        help="Filter by relationship type (empty = all types)",
        on_change=on_change,
    )

    return selected


def render_strength_threshold(
    prefix: str = "graph_filter",
    on_change: Callable[[], None] | None = None,
) -> float:
    """
    Render relationship strength threshold slider.

    Args:
        prefix: Session state key prefix
        on_change: Optional callback when value changes

    Returns:
        Selected minimum strength threshold (0.0-1.0)
    """
    key = f"{prefix}_min_strength"

    strength = st.slider(
        "Minimum Strength",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.get(key, 0.3),
        step=0.05,
        key=key,
        help="Filter relationships below this strength threshold",
        on_change=on_change,
    )

    return float(strength)


def render_temporal_filter(
    prefix: str = "graph_filter",
    on_change: Callable[[], None] | None = None,
) -> tuple[date | None, date | None]:
    """
    Render temporal date range filter.

    Args:
        prefix: Session state key prefix
        on_change: Optional callback when values change

    Returns:
        Tuple of (start_date, end_date), either can be None
    """
    start_key = f"{prefix}_start_date"
    end_key = f"{prefix}_end_date"

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "From Date",
            value=st.session_state.get(start_key),
            key=start_key,
            help="Filter facts valid from this date",
            on_change=on_change,
        )

    with col2:
        end_date = st.date_input(
            "To Date",
            value=st.session_state.get(end_key),
            key=end_key,
            help="Filter facts valid until this date",
            on_change=on_change,
        )

    # Validate date range
    if start_date and end_date and start_date > end_date:
        st.error("Start date must be before end date")
        return None, None

    return start_date, end_date


def render_graph_options(
    prefix: str = "graph_filter",
    on_change: Callable[[], None] | None = None,
) -> tuple[int, int]:
    """
    Render graph display options (max nodes, depth).

    Args:
        prefix: Session state key prefix
        on_change: Optional callback when values change

    Returns:
        Tuple of (max_nodes, max_depth)
    """
    nodes_key = f"{prefix}_max_nodes"
    depth_key = f"{prefix}_max_depth"

    col1, col2 = st.columns(2)

    with col1:
        max_nodes = st.slider(
            "Max Nodes",
            min_value=10,
            max_value=200,
            value=st.session_state.get(nodes_key, 100),
            step=10,
            key=nodes_key,
            help="Maximum number of nodes to display (affects performance)",
            on_change=on_change,
        )

    with col2:
        max_depth = st.slider(
            "Expansion Depth",
            min_value=1,
            max_value=3,
            value=st.session_state.get(depth_key, 1),
            step=1,
            key=depth_key,
            help="Maximum relationship depth for expansion",
            on_change=on_change,
        )

    return max_nodes, max_depth


def render_filter_sidebar(
    prefix: str = "graph_filter",
    on_change: Callable[[], None] | None = None,
    show_temporal: bool = True,
    show_options: bool = True,
) -> GraphFilterState:
    """
    Render complete filter sidebar with all components.

    Args:
        prefix: Session state key prefix
        on_change: Optional callback when any filter changes
        show_temporal: Whether to show temporal filter
        show_options: Whether to show graph options

    Returns:
        GraphFilterState with current filter values
    """
    # Initialize state if needed
    initialize_filter_state(prefix)

    logger.debug("render_filter_sidebar called", prefix=prefix)

    # Entity search
    st.subheader("Search")
    search_term = render_entity_search(prefix, on_change)

    # Entity type filter
    st.subheader("Entity Filters")
    entity_types = render_entity_type_filter(prefix, on_change=on_change)

    # Relationship filters
    st.subheader("Relationship Filters")
    relationship_types = render_relationship_type_filter(prefix, on_change=on_change)
    min_strength = render_strength_threshold(prefix, on_change)

    # Temporal filter (optional)
    start_date = None
    end_date = None
    if show_temporal:
        st.subheader("Temporal Filter")
        start_date, end_date = render_temporal_filter(prefix, on_change)

    # Graph options (optional)
    max_nodes = 100
    max_depth = 1
    if show_options:
        st.subheader("Display Options")
        max_nodes, max_depth = render_graph_options(prefix, on_change)

    # Build filter state
    filter_state = GraphFilterState(
        search_term=search_term,
        entity_types=entity_types,
        relationship_types=relationship_types,
        min_strength=min_strength,
        start_date=start_date,
        end_date=end_date,
        max_nodes=max_nodes,
        max_depth=max_depth,
    )

    logger.debug(
        "render_filter_sidebar completed",
        has_search=bool(search_term),
        entity_types_count=len(entity_types),
        relationship_types_count=len(relationship_types),
        min_strength=min_strength,
    )

    return filter_state


def render_filter_summary(filter_state: GraphFilterState) -> None:
    """
    Render a summary of active filters.

    Args:
        filter_state: Current filter state
    """
    active_filters: list[str] = []

    if filter_state.search_term:
        active_filters.append(f'Search: "{filter_state.search_term}"')

    if filter_state.entity_types:
        types_str = ", ".join(filter_state.entity_types[:3])
        if len(filter_state.entity_types) > 3:
            types_str += f" +{len(filter_state.entity_types) - 3} more"
        active_filters.append(f"Types: {types_str}")

    if filter_state.min_strength > 0.3:
        active_filters.append(f"Strength >= {filter_state.min_strength:.0%}")

    if filter_state.start_date or filter_state.end_date:
        date_range = ""
        if filter_state.start_date:
            date_range += filter_state.start_date.strftime("%Y-%m-%d")
        date_range += " to "
        if filter_state.end_date:
            date_range += filter_state.end_date.strftime("%Y-%m-%d")
        active_filters.append(f"Date: {date_range}")

    if active_filters:
        st.caption(f"Active filters: {' | '.join(active_filters)}")
    else:
        st.caption("No filters applied")


def render_reset_button(
    prefix: str = "graph_filter",
    on_reset: Callable[[], None] | None = None,
) -> bool:
    """
    Render filter reset button.

    Args:
        prefix: Session state key prefix
        on_reset: Optional callback when reset is clicked

    Returns:
        True if reset was clicked
    """
    if st.button("Reset Filters", key=f"{prefix}_reset", use_container_width=True):
        # Reset all filter values to defaults
        st.session_state[f"{prefix}_search_term"] = ""
        st.session_state[f"{prefix}_entity_types"] = []
        st.session_state[f"{prefix}_relationship_types"] = []
        st.session_state[f"{prefix}_min_strength"] = 0.3
        st.session_state[f"{prefix}_start_date"] = None
        st.session_state[f"{prefix}_end_date"] = None
        st.session_state[f"{prefix}_max_nodes"] = 100
        st.session_state[f"{prefix}_max_depth"] = 1

        if on_reset:
            on_reset()

        logger.info("Graph filters reset", prefix=prefix)
        return True

    return False


def convert_to_datetime(d: date | None) -> datetime | None:
    """
    Convert date to datetime for query compatibility.

    Args:
        d: Date object or None

    Returns:
        Datetime at start of day or None
    """
    if d is None:
        return None
    return datetime.combine(d, datetime.min.time())
