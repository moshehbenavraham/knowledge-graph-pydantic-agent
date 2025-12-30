# ADR-004: Graph Visualization Design

**Status**: Accepted
**Date**: 2025-12-30
**Phase**: 03 - Production Readiness & User Experience
**Session**: 04 - Graph Visualization Dashboard

---

## Context

The Agentic GraphRAG System stores rich entity and relationship data in Neo4j, but users had no way to explore this knowledge graph visually. The chat interface could answer questions about entities, but understanding the broader structure of relationships required Cypher queries.

We needed an interactive visualization that:
1. Let users explore entities and relationships visually
2. Supported filtering by entity type, relationship type, and strength
3. Provided detailed information for selected entities
4. Worked within Streamlit's constraints
5. Handled graphs with hundreds of nodes performantly

## Decision

We implemented a **Graph Explorer dashboard** using pyvis for network rendering with a custom handler architecture:

### 1. VisualizationHandler (`src/ui/features/visualization_handler.py`)

Central controller for graph operations:
- Entity search with type filtering
- Subgraph loading centered on selected entity
- Progressive neighbor expansion
- Entity detail fetching
- pyvis network rendering
- Export to HTML

State management via `VisualizationState` dataclass:
- Current nodes and edges
- Selected/center entity IDs
- Search results
- Query timing

### 2. pyvis Network Rendering

Chose pyvis over alternatives because:
- Pure Python (no JavaScript build step)
- vis.js foundation (proven force-directed layout)
- HTML output embeddable in Streamlit
- Interactive out-of-the-box

Styling decisions:
- Entity types distinguished by color palette
- Node size scaled by relationship count
- Edge width reflects relationship strength
- Force-directed layout with physics stabilization
- Optional hierarchical layout

### 3. Graph Query Functions (`src/agentic_rag/graph/visualization_queries.py`)

Optimized Cypher queries for visualization:
- `search_entities()` - Name/type search with pagination
- `fetch_entity_subgraph()` - N-hop subgraph with strength filtering
- `expand_entity_neighbors()` - Incremental expansion
- `fetch_temporal_facts()` - Facts for entity detail

Performance optimizations:
- `max_nodes` limit to prevent browser overload
- `min_strength` threshold to filter weak relationships
- Efficient Cypher patterns avoiding cartesian products

### 4. Filter Components (`src/ui/components/graph_filters.py`)

Interactive filtering via sidebar:
- Entity type multi-select
- Relationship type multi-select
- Strength threshold slider
- Temporal range filter
- Node limit slider
- Search text input

`GraphFilterState` dataclass tracks all filter values.

### 5. Entity Detail Panel (`src/ui/components/entity_detail.py`)

Right sidebar showing selected entity:
- Basic info (name, type, relationship count)
- Connected relationships with strength
- Temporal facts (valid_from/valid_to)
- Source documents
- Actions (expand neighbors, center graph)

## Consequences

### Positive

- **Visual exploration**: Users can discover relationships interactively
- **Filtered views**: Complex graphs become manageable
- **Performance**: Subgraph approach handles large graphs
- **Integration**: Same data as chat, different view
- **Export**: HTML output shareable without system access

### Negative

- **Browser limits**: Very large graphs (1000+ nodes) still slow
- **Streamlit constraints**: Full re-render on filter changes
- **JavaScript dependency**: pyvis generates client-side JS
- **Layout variability**: Force-directed layout not deterministic

### Trade-offs

We chose entity-centric subgraphs over full-graph view because:
1. Full graph would overwhelm browser and user
2. Focused exploration more useful than overview
3. Progressive expansion enables discovery

We chose pyvis over alternatives:
- D3.js: More powerful but requires JavaScript expertise
- networkx + matplotlib: Static images, not interactive
- Streamlit-agraph: Less mature, fewer features
- Gephi: External tool, not embedded

## Implementation

**Key Files**:
- `src/ui/features/visualization_handler.py` - Main handler
- `src/agentic_rag/graph/visualization_queries.py` - Cypher queries
- `src/ui/components/graph_filters.py` - Filter components
- `src/ui/components/entity_detail.py` - Detail panel
- `src/ui/pages/graph_explorer.py` - Streamlit page

**Usage Example**:
```python
from src.ui.features.visualization_handler import get_visualization_handler

# Initialize handler
handler = await get_visualization_handler()

# Search for entities
results = await handler.search_entities(
    search_term="Intel",
    entity_types=["company", "organization"],
)

# Load subgraph
subgraph = await handler.load_entity_subgraph(
    entity_id=results[0].id,
    max_depth=2,
    min_strength=0.3,
)

# Render network
net = handler.render_graph(
    height="600px",
    highlight_entity_id=results[0].id,
)
```

**Entity Color Palette**:
| Entity Type | Color |
|-------------|-------|
| person | #4C8EDA |
| company | #FF6B6B |
| organization | #57C7E3 |
| location | #FFC454 |
| technology | #8DCC93 |
| product | #A78BFA |
| financial_metric | #F0B95A |

## Related Decisions

- ADR-003: UI Component Library provides entity_detail and graph_filters
- Multi-Hop Query Engine (Phase 02) powers relationship traversal
- Type Hierarchy enables hierarchical entity type filtering

---

**Last Updated**: 2025-12-30
