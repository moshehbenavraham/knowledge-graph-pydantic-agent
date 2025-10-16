# Changelog

All notable changes to the Base Agent project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Previous changelogs**: See `/docs/changelogs_previous/` for historical changes (v0.1.0 - v0.9.0)

---

## [1.0.2] - 2025-10-16

### Changed
- **Interactive Knowledge Graph Visualization** - Replaced static Plotly graph with interactive pyvis network
  - Draggable nodes: Click and drag individual nodes to reposition them for better relationship visualization
  - Pan and zoom: Click-drag background to pan, scroll to zoom in/out
  - Physics simulation: ForceAtlas2 algorithm (same as Neo4j Enterprise) with natural node repulsion and spring forces
  - Multiple layout options: Force-directed (default), hierarchical, and circular layouts via dropdown selector
  - Navigation controls: Built-in pan/zoom buttons in bottom-right corner
  - Enhanced tooltips: Hover over nodes to see entity details (name, type, connections) in clean multi-line format
  - Neo4j-inspired styling: 8 distinct entity type colors, node size based on connection count (15-50px)
  - Full-width display: Knowledge graph now spans entire dashboard width for better visibility (was half-width)
  - Edge validation: Only displays edges between visible nodes, preventing graph rendering errors
  - Performance: Increased max entities from 100 to 200 with optimized physics stabilization

### Added
- New dependency: `pyvis>=0.3.2` for interactive network visualization
- Helper function: `create_pyvis_graph()` in `src/ui/features/dashboard_utils.py` (180 lines)
  - Configurable physics engines for different layout algorithms
  - Comprehensive node/edge styling with entity type-based color mapping
  - Defensive edge validation to prevent assertion errors
  - Debug logging for skipped edges (nodes not in top N entities)

### Fixed
- **Knowledge Graph Edge Errors** - Fixed AssertionError when relationships referenced entities outside top N
  - Added node ID tracking set to validate edge endpoints before adding to graph
  - Edges to non-existent nodes are now safely skipped with debug logging
  - Prevents crashes when Neo4j relationships span beyond displayed entity limit
- **HTML Encoding in Tooltips** - Fixed display of raw HTML tags in node hover tooltips
  - Changed from HTML format (`<b>`, `<br>`, `<i>`) to plain text with newlines (`\n`)
  - Tooltips now render as clean multi-line text instead of showing encoded characters

### Technical Details
- **Physics Configuration**:
  - Gravitational constant: -50 (nodes repel each other)
  - Spring length: 200px (natural spacing between connected nodes)
  - Damping: 0.4 (smooth, realistic motion)
  - Stabilization: 100 iterations for optimal initial layout
- **Interaction Features**: Drag nodes, drag canvas, zoom (scroll), hover tooltips, keyboard navigation
- **Rendering**: HTML generated via pyvis, embedded in Streamlit via `components.html()`
- **Temporary Files**: Proper cleanup with context managers and Path.unlink()

---

## [1.0.1] - 2025-10-15

### Added
- **GraphRAG Analytics Dashboard** - Comprehensive visualization and monitoring interface for the Agentic RAG system
  - Real-time search analytics with metrics cards (total searches, avg latency, top strategy, graph boost rate)
  - Search strategy distribution bar chart showing usage patterns across vector, graph, and hybrid searches
  - Query intent distribution pie chart displaying intent analysis breakdown (VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, TEMPORAL, ENTITY_FOCUSED)
  - Interactive knowledge graph visualization using NetworkX and Plotly with spring layout algorithm
  - Entity explorer with top 20 entities table (sortable by relationships, chunks, creation date)
  - Entity timeline viewer showing first_seen, last_updated, mention_count, and chunk references
  - Performance metrics section with query latency breakdown and database health indicators
  - 30-second caching for expensive Neo4j queries to optimize dashboard performance
  - Manual refresh button to clear cache and fetch latest data
  - Graceful degradation when databases are unavailable or empty
- Dashboard feature handlers in modular architecture:
  - `src/ui/features/dashboard_handler.py` (380 lines) - Metrics collection and data fetching
  - `src/ui/features/dashboard_utils.py` (330 lines) - Cypher query generation and data formatting
- Dashboard configuration in `src/config/ui.py` with DashboardConfig dataclass
- Page navigation system in Streamlit UI (Chat / Dashboard)
- Comprehensive test suite: `tests/ui/test_dashboard.py` (470 lines, 20+ tests)
- New dependencies: `plotly>=5.18.0`, `networkx>=3.2.1`
- Documentation: `docs/DASHBOARD_QUICKSTART.md` - User-friendly quick start guide

### Fixed
- **Neo4j Schema Compatibility** - Updated all Cypher queries to match actual database schema
  - Changed property names: `uuid` → `id`, `entity_type` → `type`, `created_at` → `first_seen`
  - Updated entity summary retrieval to use `canonical_name` property
  - Fixed chunk count queries to use `size(e.chunk_refs)` instead of relationship traversal
  - Fixed relationship queries to use correct property names and `properties(r)` for metadata
- **Neo4j 5+ Syntax Compliance** - Migrated from deprecated `size()` function to modern `COUNT {}` syntax
  - Updated all relationship counting queries: `size((e)-[]->())` → `COUNT { (e)-[]->(other) }`
  - Ensures compatibility with Neo4j 5.x and later versions
  - Eliminates syntax error warnings from Neo4j server
- **NetworkX Graph Rendering** - Resolved "None cannot be a node" error
  - Added entity ID validation to filter out None values before graph creation
  - Implemented `valid_entities` filtering in dashboard visualization
  - Updated entity count displays to reflect filtered entities
- **Plotly Visualization Compatibility** - Fixed deprecated colorbar configuration
  - Migrated `titleside` parameter to nested `title=dict(text=..., side=...)` format
  - Ensures compatibility with Plotly 5.18.0+
- **Streamlit Component Parameters** - Corrected parameter usage for Streamlit widgets
  - `st.plotly_chart()` uses `use_container_width=True` (not `width`)
  - `st.dataframe()` uses `width="stretch"` (new parameter)
  - Eliminates deprecation warnings in Streamlit output

### Changed
- Dashboard only available in Standard and Advanced UI modes (not Simple mode)
- Entity timeline view simplified to show entity metadata instead of temporal facts (Facts node type not yet in schema)
- Graph visualization limited to 100 entities maximum for performance optimization

### Technical Details
- **Architecture**: Modular feature handler pattern following existing codebase conventions
- **Performance**: 30-second TTL cache for Neo4j queries, lazy loading of graph data
- **Error Handling**: Comprehensive try-catch blocks with graceful degradation
- **Testing**: 20+ unit and integration tests covering all dashboard functionality
- **Code Quality**: All changes pass ruff linting, black formatting, and type checks

### Documentation
- Added `docs/DASHBOARD_QUICKSTART.md` with usage instructions and troubleshooting
- Updated `docs/projects_ongoing/graphrag-dashboard.md` with completion status
- Created `docs/projects_ongoing/graphrag-dashboard-COMPLETE.md` with implementation summary
- Added `docs/projects_ongoing/graphrag-dashboard-BUGS-FIXED.md` documenting critical bug fixes

---

## [1.0.0] - 2025-10-14

### Release
- **Production-Ready Agentic Graph RAG System** - Complete implementation with dual-database architecture
- PostgreSQL/Supabase vector storage with pgvector for embeddings
- Neo4j Aura knowledge graph with Graphiti integration
- Hybrid search with intelligent intent analysis and routing
- Comprehensive tooling: web search, image analysis, SQL queries, code execution
- Three UI modes: Simple, Standard (default), Advanced
- Full test coverage (75%+) with integration and end-to-end tests
- Production deployment guides and monitoring setup

---

## Previous Versions

See `/docs/changelogs_previous/` for historical changes from v0.1.0 through v0.9.0.

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version (X.0.0) for incompatible API changes
- **MINOR** version (0.X.0) for new functionality in a backward compatible manner
- **PATCH** version (0.0.X) for backward compatible bug fixes

## Changelog Sections

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** in case of vulnerabilities
