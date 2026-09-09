"""
Entity detail sidebar component for Graph Explorer.

Displays detailed information about a selected entity:
- Basic properties (name, type, canonical name)
- Relationship summary (connected entities count by type)
- Temporal facts timeline
- Related documents

This component integrates with the visualization handler
to fetch and display entity details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import streamlit as st
import structlog

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)


@dataclass
class EntityRelationship:
    """
    Summary of a relationship to another entity.

    Attributes:
        target_id: ID of the connected entity
        target_name: Name of the connected entity
        target_type: Type of the connected entity
        relationship_type: Type of relationship
        subtype: Relationship subtype
        strength: Relationship strength
    """

    target_id: str
    target_name: str
    target_type: str
    relationship_type: str
    subtype: str
    strength: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "relationship_type": self.relationship_type,
            "subtype": self.subtype,
            "strength": self.strength,
        }


@dataclass
class EntityFact:
    """
    Temporal fact about an entity.

    Attributes:
        description: Fact description
        valid_from: Start of validity
        valid_to: End of validity
        source: Source document
    """

    description: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "source": self.source,
        }


@dataclass
class EntityDetail:
    """
    Complete entity details for display.

    Attributes:
        id: Entity unique identifier
        name: Entity display name
        type: Entity type
        canonical_name: Canonical form of name
        relationship_count: Total number of relationships
        relationships: List of related entities
        facts: List of temporal facts
        properties: Additional properties
        source_documents: Documents mentioning this entity
    """

    id: str
    name: str
    type: str
    canonical_name: str | None = None
    relationship_count: int = 0
    relationships: list[EntityRelationship] = field(default_factory=list)
    facts: list[EntityFact] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    source_documents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "canonical_name": self.canonical_name,
            "relationship_count": self.relationship_count,
            "relationships": [r.to_dict() for r in self.relationships],
            "facts": [f.to_dict() for f in self.facts],
            "properties": self.properties,
            "source_documents": self.source_documents,
        }


# Entity type color mapping (consistent with pyvis)
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


def get_entity_color(entity_type: str) -> str:
    """
    Get color for entity type.

    Args:
        entity_type: Entity type string

    Returns:
        Hex color code
    """
    return ENTITY_TYPE_COLORS.get(entity_type.lower(), DEFAULT_ENTITY_COLOR)


def render_entity_header(entity: EntityDetail) -> None:
    """
    Render entity header with name, type badge, and basic info.

    Args:
        entity: Entity details to display
    """
    # Entity name as header
    st.subheader(entity.name)

    # Type badge with color
    color = get_entity_color(entity.type)
    type_label = entity.type.replace("_", " ").title()
    st.markdown(
        f'<span style="background-color: {color}; color: white; '
        f'padding: 2px 8px; border-radius: 4px; font-size: 12px;">'
        f"{type_label}</span>",
        unsafe_allow_html=True,
    )

    # Canonical name if different
    if entity.canonical_name and entity.canonical_name != entity.name:
        st.caption(f"Canonical: {entity.canonical_name}")

    # Relationship count
    st.metric("Connections", entity.relationship_count)


def render_entity_properties(entity: EntityDetail) -> None:
    """
    Render entity properties in an expandable section.

    Args:
        entity: Entity details to display
    """
    # Filter out internal properties
    display_props = {
        k: v
        for k, v in entity.properties.items()
        if not k.startswith("_") and k not in ("id", "name", "type", "canonical_name")
    }

    if not display_props:
        st.info("No additional properties")
        return

    with st.expander("Properties", expanded=False):
        for key, value in display_props.items():
            # Format key for display
            display_key = key.replace("_", " ").title()

            # Format value based on type
            if isinstance(value, list):
                if len(value) > 5:
                    display_value = f"{len(value)} items"
                else:
                    display_value = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                display_value = f"{len(value)} fields"
            elif isinstance(value, bool):
                display_value = "Yes" if value else "No"
            elif isinstance(value, float):
                display_value = f"{value:.2f}"
            else:
                display_value = str(value)

            st.text(f"{display_key}: {display_value}")


def render_relationships_summary(
    relationships: list[EntityRelationship],
    on_entity_click: Callable[[str], None] | None = None,
) -> None:
    """
    Render relationships summary grouped by type.

    Args:
        relationships: List of entity relationships
        on_entity_click: Optional callback when entity is clicked
    """
    if not relationships:
        st.info("No relationships found")
        return

    # Group by relationship type
    by_type: dict[str, list[EntityRelationship]] = {}
    for rel in relationships:
        subtype = rel.subtype or rel.relationship_type
        if subtype not in by_type:
            by_type[subtype] = []
        by_type[subtype].append(rel)

    # Render each type group
    for rel_type, rels in sorted(by_type.items(), key=lambda x: -len(x[1])):
        type_label = rel_type.replace("_", " ").title()
        with st.expander(f"{type_label} ({len(rels)})", expanded=len(rels) <= 5):
            for rel in sorted(rels, key=lambda r: -r.strength):
                col1, col2 = st.columns([3, 1])

                with col1:
                    # Entity name as clickable button
                    if on_entity_click:
                        if st.button(
                            rel.target_name,
                            key=f"rel_{rel.target_id}",
                            help=f"View {rel.target_name}",
                        ):
                            on_entity_click(rel.target_id)
                    else:
                        entity_color = get_entity_color(rel.target_type)
                        st.markdown(
                            f'<span style="color: {entity_color};">'
                            f"{rel.target_name}</span> "
                            f'<span style="color: #888; font-size: 11px;">'
                            f"({rel.target_type})</span>",
                            unsafe_allow_html=True,
                        )

                with col2:
                    # Strength indicator
                    strength_pct = int(rel.strength * 100)
                    st.caption(f"{strength_pct}%")


def render_temporal_facts(facts: list[EntityFact]) -> None:
    """
    Render temporal facts as a timeline.

    Args:
        facts: List of temporal facts
    """
    if not facts:
        st.info("No temporal facts found")
        return

    # Sort by date (most recent first)
    sorted_facts = sorted(
        facts,
        key=lambda f: f.valid_from or datetime.min,
        reverse=True,
    )

    for fact in sorted_facts:
        # Date range
        date_str = ""
        if fact.valid_from:
            date_str = fact.valid_from.strftime("%Y-%m-%d")
            if fact.valid_to:
                date_str += f" to {fact.valid_to.strftime('%Y-%m-%d')}"
            else:
                date_str += " - present"

        # Render as a card-like element
        with st.container():
            if date_str:
                st.caption(date_str)
            st.write(fact.description)
            if fact.source:
                st.caption(f"Source: {fact.source}")
            st.divider()


def render_source_documents(documents: list[str]) -> None:
    """
    Render list of source documents.

    Args:
        documents: List of document names/paths
    """
    if not documents:
        st.info("No source documents")
        return

    with st.expander(f"Source Documents ({len(documents)})", expanded=False):
        for doc in documents:
            st.text(f"- {doc}")


def render_entity_actions(
    entity: EntityDetail,
    on_expand: Callable[[str], None] | None = None,
    on_focus: Callable[[str], None] | None = None,
) -> None:
    """
    Render action buttons for the entity.

    Args:
        entity: Entity details
        on_expand: Callback to expand entity neighbors
        on_focus: Callback to focus/center on entity
    """
    col1, col2 = st.columns(2)

    with col1:
        if on_expand:
            if st.button(
                "Expand Neighbors",
                key=f"expand_{entity.id}",
                use_container_width=True,
                help="Load connected entities",
            ):
                on_expand(entity.id)

    with col2:
        if on_focus:
            if st.button(
                "Center View",
                key=f"focus_{entity.id}",
                use_container_width=True,
                help="Center graph on this entity",
            ):
                on_focus(entity.id)


def render_entity_detail_panel(
    entity: EntityDetail | None,
    on_entity_click: Callable[[str], None] | None = None,
    on_expand: Callable[[str], None] | None = None,
    on_focus: Callable[[str], None] | None = None,
    show_facts: bool = True,
    show_documents: bool = True,
) -> None:
    """
    Render complete entity detail panel.

    Args:
        entity: Entity details to display (None shows placeholder)
        on_entity_click: Callback when related entity is clicked
        on_expand: Callback to expand entity neighbors
        on_focus: Callback to focus on entity
        show_facts: Whether to show temporal facts section
        show_documents: Whether to show source documents section
    """
    logger.debug(
        "render_entity_detail_panel called",
        has_entity=entity is not None,
        entity_id=entity.id if entity else None,
    )

    if entity is None:
        st.info("Select an entity from the graph to view details")
        return

    # Header with name and type
    render_entity_header(entity)

    st.divider()

    # Action buttons
    if on_expand or on_focus:
        render_entity_actions(entity, on_expand, on_focus)
        st.divider()

    # Properties section
    st.subheader("Properties")
    render_entity_properties(entity)

    # Relationships section
    st.subheader("Relationships")
    render_relationships_summary(entity.relationships, on_entity_click)

    # Temporal facts section (optional)
    if show_facts:
        st.subheader("Timeline")
        render_temporal_facts(entity.facts)

    # Source documents section (optional)
    if show_documents and entity.source_documents:
        st.subheader("Sources")
        render_source_documents(entity.source_documents)


def render_empty_selection_state() -> None:
    """Render placeholder when no entity is selected."""
    st.markdown("""
        ### Entity Details

        Click on a node in the graph to view its details.

        **Tip:** Use the search box to find specific entities.
        """)


def render_loading_state() -> None:
    """Render loading indicator for entity details."""
    with st.spinner("Loading entity details..."):
        st.empty()


def entity_from_dict(data: dict[str, Any]) -> EntityDetail:
    """
    Create EntityDetail from dictionary data.

    Args:
        data: Dictionary with entity data

    Returns:
        EntityDetail object
    """
    relationships = []
    for rel_data in data.get("relationships", []):
        relationships.append(
            EntityRelationship(
                target_id=rel_data.get("target_id", ""),
                target_name=rel_data.get("target_name", ""),
                target_type=rel_data.get("target_type", ""),
                relationship_type=rel_data.get("relationship_type", ""),
                subtype=rel_data.get("subtype", ""),
                strength=float(rel_data.get("strength", 0.5)),
            )
        )

    facts = []
    for fact_data in data.get("facts", []):
        valid_from = fact_data.get("valid_from")
        valid_to = fact_data.get("valid_to")

        facts.append(
            EntityFact(
                description=fact_data.get("description", ""),
                valid_from=(
                    datetime.fromisoformat(valid_from) if isinstance(valid_from, str) else None
                ),
                valid_to=(datetime.fromisoformat(valid_to) if isinstance(valid_to, str) else None),
                source=fact_data.get("source"),
            )
        )

    return EntityDetail(
        id=data.get("id", ""),
        name=data.get("name", ""),
        type=data.get("type", ""),
        canonical_name=data.get("canonical_name"),
        relationship_count=data.get("relationship_count", 0),
        relationships=relationships,
        facts=facts,
        properties=data.get("properties", {}),
        source_documents=data.get("source_documents", []),
    )
