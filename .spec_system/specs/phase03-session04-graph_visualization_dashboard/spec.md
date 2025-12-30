# Session Specification

**Session ID**: `phase03-session04-graph_visualization_dashboard`
**Phase**: 03 - Production Readiness & User Experience
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session delivers an interactive graph visualization dashboard that enables users to visually explore the knowledge graph. Users will be able to search for entities, view their relationships, filter by type and temporal range, and navigate through the graph interactively.

The visualization dashboard is the culmination of the Phase 01-02 knowledge graph improvements and Phase 03 UI/UX work. It provides a visual interface to the multi-hop queries, temporal facts, relationship scoring, and entity type hierarchy built in previous phases. This session transforms the knowledge graph from a backend query engine into a user-facing exploration tool.

The implementation follows the established handler pattern from Session 03, integrating with the existing Streamlit UI architecture. The graph visualization uses pyvis for interactive network rendering, which generates HTML that embeds seamlessly in Streamlit via `st.components.v1.html`.

---

## 2. Objectives

1. Enable users to search and discover entities in the knowledge graph via a search interface with type filtering
2. Render an interactive network graph showing entities as nodes and relationships as edges with strength-based styling
3. Display entity details (properties, relationships, temporal facts) in a detail panel when a node is selected
4. Provide filtering controls for relationship types, strength thresholds, and temporal date ranges
5. Support graph navigation including zoom, pan, expand neighbors, and export to PNG/SVG

---

## 3. Prerequisites

### Required Sessions
- [x] `phase03-session01-error_handling_and_resilience` - Error handling infrastructure for graceful failures
- [x] `phase03-session02-performance_monitoring_and_profiling` - Performance monitoring for large graph queries
- [x] `phase03-session03-ui_ux_enhancements` - UI component library (buttons, modals, layouts)
- [x] `phase01-session05-relationship_scoring` - Relationship strength for edge styling
- [x] `phase01-session06-type_hierarchy_and_testing` - Entity type hierarchy for filtering

### Required Tools/Knowledge
- pyvis library for network visualization
- Neo4j Cypher query patterns for entity/relationship retrieval
- Streamlit components for embedding HTML content
- Existing handler pattern from `src/ui/features/`

### Environment Requirements
- Neo4j Aura connection configured (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
- pyvis installed (`pip install pyvis`)
- Streamlit running in Advanced mode for full feature access

---

## 4. Scope

### In Scope (MVP)
- Entity search component with name query and type filter dropdown
- Interactive graph visualization using pyvis (nodes, edges, styling)
- Entity detail sidebar showing properties, relationships, and temporal facts
- Relationship filter: type selection (multi-select), strength threshold slider
- Temporal filter: date range picker for filtering facts by valid_from/valid_to
- Graph navigation: zoom, pan, expand neighbors (click to load connected nodes)
- Export functionality: save current graph view as PNG or SVG
- Integration with existing ConnectionManager and graph query utilities
- Performance optimization for graphs up to 100 nodes

### Out of Scope (Deferred)
- Graph editing (create/update/delete entities) - *Reason: Read-only exploration for MVP*
- Export to external graph formats (GraphML, GEXF) - *Reason: Basic image export sufficient for MVP*
- Collaborative annotation features - *Reason: Multi-user features require authentication enhancements*
- 3D visualization - *Reason: 2D sufficient for MVP, 3D adds complexity*
- Real-time graph updates during ingestion - *Reason: Static snapshot adequate for exploration*

---

## 5. Technical Approach

### Architecture

The visualization dashboard follows a layered architecture:

1. **UI Layer** (`src/ui/pages/graph_explorer.py`): Streamlit page with search, filters, and graph display
2. **Handler Layer** (`src/ui/features/visualization_handler.py`): Graph data fetching and pyvis rendering logic
3. **Query Layer**: Reuses existing `src/agentic_rag/graph/` modules for Neo4j queries
4. **Data Layer**: ConnectionManager for Neo4j connections

```
[Streamlit Page] -> [VisualizationHandler] -> [Graph Query Modules] -> [Neo4j]
                           |
                    [pyvis Network] -> [HTML embed in Streamlit]
```

### Design Patterns
- **Handler Pattern**: VisualizationHandler extends the UI handler pattern for graph operations
- **Facade Pattern**: Handler provides simplified interface to complex graph query operations
- **Observer Pattern**: Filter changes trigger graph re-rendering via Streamlit session state

### Technology Stack
- Python 3.11+
- Streamlit 1.44+ (st.components.v1.html for pyvis embedding)
- pyvis 0.3.2+ (interactive network visualization)
- Neo4j Python driver (existing via ConnectionManager)
- structlog for logging

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/ui/pages/graph_explorer.py` | Streamlit page for graph visualization | ~250 |
| `src/ui/features/visualization_handler.py` | Handler for graph queries and pyvis rendering | ~300 |
| `src/ui/components/graph_filters.py` | Reusable filter components (type, strength, temporal) | ~150 |
| `src/ui/components/entity_detail.py` | Entity detail sidebar component | ~120 |
| `src/agentic_rag/graph/visualization_queries.py` | Neo4j queries optimized for visualization | ~180 |
| `tests/ui/test_visualization_handler.py` | Unit tests for visualization handler | ~200 |
| `tests/ui/test_graph_filters.py` | Unit tests for filter components | ~100 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/ui/streamlit_app.py` | Add Graph Explorer to navigation sidebar | ~15 |
| `src/ui/features/__init__.py` | Export VisualizationHandler | ~2 |
| `src/agentic_rag/graph/__init__.py` | Export visualization query functions | ~5 |
| `pyproject.toml` | Add pyvis dependency | ~1 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] Entity search returns matching entities with type filtering
- [ ] Graph visualization renders entities as nodes and relationships as edges
- [ ] Clicking a node displays entity details in sidebar
- [ ] Relationship type filter limits visible edges to selected types
- [ ] Strength threshold slider filters edges below threshold
- [ ] Temporal filter limits facts to specified date range
- [ ] Expand neighbors button loads connected entities for selected node
- [ ] Export button saves current graph view as PNG or SVG

### Testing Requirements
- [ ] Unit tests for VisualizationHandler (mocked Neo4j)
- [ ] Unit tests for filter components
- [ ] Unit tests for visualization query functions
- [ ] Integration test: search -> visualization -> detail view flow
- [ ] Performance test: 100-node graph renders in < 3 seconds

### Quality Gates
- [ ] All files ASCII-encoded (0-127 characters only)
- [ ] Unix LF line endings
- [ ] Code follows project conventions (CONVENTIONS.md)
- [ ] Black formatting passes
- [ ] Ruff linting passes
- [ ] MyPy type checking passes
- [ ] Bandit security scan passes
- [ ] 75%+ test coverage on new code

---

## 8. Implementation Notes

### Key Considerations
- pyvis generates HTML with JavaScript; use `st.components.v1.html()` to embed
- Graph rendering is client-side; keep node count reasonable (100 max default)
- Use session state to persist filter selections across reruns
- Implement loading indicators for graph queries (can take 1-2 seconds)

### Potential Challenges
- **Large Graph Performance**: Implement pagination/limiting for initial query; expand on demand
- **pyvis HTML Height**: Dynamically calculate height based on container; default 600px
- **Neo4j Connection Stability**: Use existing error handling from Session 01; retry on transient failures
- **Node Selection Events**: pyvis click events require JavaScript callback; use streamlit-pyvis or custom approach

### Relevant Considerations
<!-- From CONSIDERATIONS.md -->
- **[External Dependencies]** Neo4j Aura connection stability: Implement robust error handling with retries and user-friendly error messages when graph database is unavailable
- **[Architecture]** Handler-based UI: Create visualization_handler.py following existing handler patterns, not a new UI architecture
- **[Architecture]** Unified agent principle: Integrate with existing graph query modules, don't duplicate query logic
- **[What Worked]** Structured logging with structlog: Log all graph operations with query parameters and timing

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No unicode characters, emojis, or special symbols.

---

## 9. Testing Strategy

### Unit Tests
- VisualizationHandler.fetch_entity_subgraph() returns expected node/edge structure
- VisualizationHandler.render_graph() generates valid pyvis HTML
- Filter components correctly format Cypher WHERE clauses
- Entity detail component renders all property types

### Integration Tests
- End-to-end: search query -> Neo4j -> visualization -> detail panel
- Filter changes trigger graph re-query and re-render
- Expand neighbors appends nodes without duplicates

### Manual Testing
- Visual inspection: nodes positioned reasonably, edges visible
- Interaction: zoom with scroll, pan with drag, click to select
- Export: PNG/SVG downloads correctly with graph content
- Responsive: visualization resizes with browser window

### Edge Cases
- Empty search results: display "No entities found" message
- Entity with no relationships: render single node, detail shows "No relationships"
- Very long entity names: truncate in node label, show full in detail
- Entities with many relationships (50+): limit initial edges, show "Load more" option
- Invalid date range: validate temporal filter, show error for end < start

---

## 10. Dependencies

### External Libraries
- pyvis: 0.3.2+ (network visualization)
- streamlit: 1.44+ (already installed)
- neo4j: 5.0+ (already installed via ConnectionManager)

### Other Sessions
- **Depends on**:
  - phase03-session01 (error handling)
  - phase03-session02 (performance monitoring)
  - phase03-session03 (UI components)
  - phase01-session05 (relationship scoring)
  - phase01-session06 (type hierarchy)
- **Depended by**:
  - phase03-session05 (documentation must document this feature)

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
