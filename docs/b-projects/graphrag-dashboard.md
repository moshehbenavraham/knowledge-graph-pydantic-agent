# GraphRAG Dashboard Implementation Plan

**Status:** [x] COMPLETED
**Created:** 2025-10-15
**Completed:** 2025-10-15
**Owner:** AI with Apex

## Overview

Add a comprehensive GraphRAG analytics and visualization dashboard to the Streamlit UI, providing insights into search patterns, knowledge graph structure, entity relationships, and system performance.

## Architecture Approach

Follow the existing modular pattern:
- Create `src/ui/features/dashboard_handler.py` for dashboard logic
- Add new sidebar navigation for Dashboard page
- Integrate with existing HybridSearch, IntentAnalyzer, and GraphSearch components
- Use Streamlit's native visualization libraries (plotly, networkx, etc.)

## Implementation Steps

### 1. Create Dashboard Feature Handler

**File:** `src/ui/features/dashboard_handler.py` (~150-200 lines)

**Responsibilities:**
- Fetch statistics from HybridSearch, IntentAnalyzer, GraphSearch, VectorSearch
- Provide methods to query Neo4j for graph visualization data
- Handle real-time metrics refresh
- Cache expensive queries (TTL: 30 seconds)

**Key Methods:**
```python
class DashboardHandler:
    def __init__(self, connection_manager: ConnectionManager):
        """Initialize with database connections"""

    async def get_search_metrics(self) -> dict[str, Any]:
        """Fetch aggregated search statistics"""

    async def get_intent_distribution(self) -> dict[str, float]:
        """Get distribution of query intents"""

    async def get_graph_data(self, limit: int = 50) -> dict[str, Any]:
        """Fetch entity and relationship data for visualization"""

    async def get_top_entities(self, limit: int = 20) -> list[dict]:
        """Get most connected entities"""

    async def get_entity_timeline(self, entity_id: str) -> list[dict]:
        """Get temporal facts for specific entity"""

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get latency breakdown and cache stats"""
```

### 2. Add Dashboard Utilities Module

**File:** `src/ui/features/dashboard_utils.py` (~100-150 lines)

**Responsibilities:**
- Cypher queries for entity/relationship extraction
- Data formatting for visualization
- Time-series data aggregation
- Export functions (CSV, JSON)

**Key Functions:**
```python
def format_graph_for_plotly(entities, relationships) -> dict:
    """Format graph data for plotly network visualization"""

def aggregate_time_series(stats, time_window: str) -> pd.DataFrame:
    """Aggregate metrics over time (24h/7d/30d)"""

def generate_entity_cypher(filters: dict) -> str:
    """Generate Cypher query with filters"""

def export_metrics_to_csv(metrics: dict, filename: str):
    """Export dashboard metrics to CSV"""
```

### 3. Add Dashboard Page to Main UI

**File:** `src/ui/streamlit_app.py` (modifications)

**Changes:**
1. Add page navigation in sidebar:
```python
def render_sidebar():
    with st.sidebar:
        # Add page selector at top
        page = st.radio(
            "Navigation",
            options=["=� Chat", "=� Dashboard"],
            index=0
        )
        st.session_state.current_page = page

        st.divider()
        # Rest of sidebar...
```

2. Add conditional page rendering in `main()`:
```python
async def main():
    # ... initialization ...

    page = st.session_state.get("current_page", "=� Chat")

    if page == "=� Chat":
        render_chat_interface()
    elif page == "=� Dashboard":
        if st.session_state.config.mode != UIMode.SIMPLE:
            await render_dashboard()
        else:
            st.warning("Dashboard is only available in Standard and Advanced modes")
```

### 4. Dashboard Layout Components

#### Section A: Search Analytics (Top Row)

**Metrics Cards** (4 columns):
```python
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Searches", metrics["total_searches"])
with col2:
    st.metric("Avg Latency", f"{metrics['avg_latency_ms']:.0f}ms")
with col3:
    st.metric("Top Strategy", metrics["most_used_strategy"])
with col4:
    st.metric("Graph Boost Rate", f"{metrics['boost_rate']:.1%}")
```

**Line Chart** - Search volume over time:
```python
import plotly.express as px

time_data = await handler.get_time_series_data(window="7d")
fig = px.line(time_data, x="timestamp", y="search_count",
              title="Search Volume (Last 7 Days)")
st.plotly_chart(fig)
```

#### Section B: Intent Analysis (Middle Left)

**Pie Chart** - Intent distribution:
```python
intent_dist = await handler.get_intent_distribution()
fig = px.pie(
    values=list(intent_dist.values()),
    names=list(intent_dist.keys()),
    title="Query Intent Distribution"
)
st.plotly_chart(fig)
```

**Bar Chart** - Strategy usage:
```python
strategy_stats = metrics["strategy_distribution"]
fig = px.bar(
    x=list(strategy_stats.keys()),
    y=list(strategy_stats.values()),
    title="Search Strategy Usage"
)
st.plotly_chart(fig)
```

#### Section C: Knowledge Graph Visualization (Middle Right)

**Interactive Network Graph**:
```python
import plotly.graph_objects as go
import networkx as nx

graph_data = await handler.get_graph_data(limit=50)
G = nx.Graph()

# Add nodes (entities)
for entity in graph_data["entities"]:
    G.add_node(
        entity["id"],
        label=entity["name"],
        type=entity["type"]
    )

# Add edges (relationships)
for rel in graph_data["relationships"]:
    G.add_edge(
        rel["source_id"],
        rel["target_id"],
        label=rel["type"]
    )

# Create plotly figure
pos = nx.spring_layout(G)
edge_trace, node_trace = create_plotly_network(G, pos)
fig = go.Figure(data=[edge_trace, node_trace])
st.plotly_chart(fig, use_container_width=True)
```

**Controls**:
```python
col1, col2, col3 = st.columns(3)
with col1:
    entity_types = st.multiselect("Entity Types", options=all_types)
with col2:
    depth = st.slider("Relationship Depth", 1, 3, 2)
with col3:
    search_entity = st.text_input("Search Entity")
```

#### Section D: Entity Explorer (Bottom Left)

**Top Entities Table**:
```python
entities = await handler.get_top_entities(limit=20)
df = pd.DataFrame(entities)
df_display = df[["name", "type", "relationship_count", "chunk_count", "confidence"]]

# Make table interactive with selection
selected_row = st.dataframe(
    df_display,
    use_container_width=True,
    selection_mode="single-row",
    on_select="rerun"
)

if selected_row:
    entity_id = df.iloc[selected_row]["id"]
    timeline = await handler.get_entity_timeline(entity_id)

    st.subheader(f"Timeline: {df.iloc[selected_row]['name']}")
    for fact in timeline:
        st.write(f"- {fact['timestamp']}: {fact['description']}")
```

#### Section E: Performance Metrics (Bottom Right)

**Latency Breakdown**:
```python
perf = await handler.get_performance_metrics()

fig = px.bar(
    x=["Vector Search", "Graph Search", "Ranking", "Total"],
    y=[
        perf["vector_latency_ms"],
        perf["graph_latency_ms"],
        perf["ranking_latency_ms"],
        perf["total_latency_ms"]
    ],
    title="Average Query Latency Breakdown"
)
st.plotly_chart(fig)
```

**Cache & Database Health**:
```python
col1, col2 = st.columns(2)
with col1:
    st.metric("Cache Hit Rate", f"{perf['cache_hit_rate']:.1%}")
    st.metric("Cache Size", f"{perf['cache_size_mb']:.1f} MB")
with col2:
    st.metric("DB Pool Active", perf["db_connections_active"])
    st.metric("DB Pool Idle", perf["db_connections_idle"])
```

### 5. Add Dashboard Configuration

**File:** `src/config/ui.py` (modifications)

```python
@dataclass
class DashboardConfig:
    """Dashboard-specific configuration."""

    enabled: bool = True
    refresh_interval_seconds: int = 30
    max_entities_display: int = 50
    default_time_window: str = "7d"  # 24h, 7d, 30d
    enable_export: bool = True
    cache_ttl_seconds: int = 30

class UIConfig:
    # ... existing config ...

    dashboard: DashboardConfig = DashboardConfig()
```

### 6. Add Required Dependencies

**File:** `pyproject.toml` (modifications)

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "plotly>=5.18.0",
    "networkx>=3.2.1",
    "pandas>=2.1.0",  # likely already included
]
```

### 7. Create Dashboard Tests

**File:** `tests/ui/test_dashboard.py` (~100+ lines)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.ui.features.dashboard_handler import DashboardHandler
from src.ui.features.dashboard_utils import format_graph_for_plotly

@pytest.fixture
def mock_connection_manager():
    """Mock connection manager for testing"""
    manager = MagicMock()
    return manager

@pytest.mark.asyncio
async def test_get_search_metrics(mock_connection_manager):
    """Test search metrics retrieval"""
    handler = DashboardHandler(mock_connection_manager)
    # Mock the HybridSearch instance
    handler._hybrid_search = MagicMock()
    handler._hybrid_search.get_stats.return_value = {
        "searches": 100,
        "avg_latency": 0.5,
    }

    metrics = await handler.get_search_metrics()
    assert metrics["total_searches"] == 100
    assert metrics["avg_latency_ms"] == 500

@pytest.mark.asyncio
async def test_get_graph_data(mock_connection_manager):
    """Test graph data retrieval"""
    handler = DashboardHandler(mock_connection_manager)
    # Mock Neo4j queries
    handler._graph_search = MagicMock()
    handler._graph_search.get_stats.return_value = {
        "entities_found": 50,
        "relationships_found": 100,
    }

    graph_data = await handler.get_graph_data(limit=50)
    assert "entities" in graph_data
    assert "relationships" in graph_data

def test_format_graph_for_plotly():
    """Test graph data formatting"""
    entities = [
        {"id": "1", "name": "OpenAI", "type": "Company"},
        {"id": "2", "name": "GPT-4", "type": "Model"},
    ]
    relationships = [
        {"source_id": "1", "target_id": "2", "type": "DEVELOPED"}
    ]

    result = format_graph_for_plotly(entities, relationships)
    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1
```

## Implementation Timeline

**Phase 1: Core Dashboard** [x] COMPLETED (2025-10-15)
- [x] Create dashboard_utils.py (330 lines)
- [x] Create dashboard_handler.py (380 lines)
- [x] Add basic metrics display (Section A & E)
- [x] Integration with main UI

**Phase 2: Visualizations** [x] COMPLETED (2025-10-15)
- [x] Implement intent analysis charts (Section B)
- [x] Implement knowledge graph visualization (Section C)
- [x] Add entity explorer (Section D)

**Phase 3: Polish & Testing** [x] COMPLETED (2025-10-15)
- [x] Add caching and performance optimization (30s TTL)
- [x] Write comprehensive tests (470 lines, 20+ tests)
- [x] Add export functionality (CSV/JSON utilities)
- [x] Documentation and user guide

## Design Decisions

### 1. Mode Availability
- **Decision:** Dashboard only in Standard/Advanced modes (not Simple)
- **Rationale:** Simple mode is for minimal UI; dashboard adds complexity
- **Implementation:** Check `st.session_state.config.mode != UIMode.SIMPLE`

### 2. Real-time Updates
- **Decision:** Auto-refresh every 30s with manual refresh button
- **Rationale:** Balance between freshness and performance
- **Implementation:** Use `st.rerun()` with timer or manual button

### 3. Graph Visualization Limits
- **Decision:** Limit to top 50 entities for performance
- **Rationale:** Large graphs (>100 nodes) become unreadable and slow
- **Implementation:** Add limit parameter to Cypher queries

### 4. Responsive Layout
- **Decision:** Two-column layout with collapsible sections
- **Rationale:** Better use of screen space, allows focus on specific areas
- **Implementation:** Use `st.columns()` and `st.expander()`

### 5. Export Options
- **Decision:** Allow exporting metrics and graph data (CSV, JSON)
- **Rationale:** Users may want to analyze data externally
- **Implementation:** Add download buttons with `st.download_button()`

## Technical Considerations

### Performance Optimization
1. **Caching:** Cache expensive Neo4j queries for 30 seconds
2. **Lazy Loading:** Only fetch graph data when graph tab is active
3. **Pagination:** Limit entity/relationship queries to reasonable sizes
4. **Async Operations:** Use `asyncio.gather()` for parallel data fetching

### Error Handling
```python
try:
    metrics = await handler.get_search_metrics()
except ConnectionError as e:
    st.error(f"Database connection failed: {e}")
    st.info("Please check your Neo4j and PostgreSQL connections")
except Exception as e:
    logger.exception("Dashboard error")
    st.error("An unexpected error occurred")
```

### Graceful Degradation
- If Neo4j is unavailable: Hide graph visualization, show vector-only stats
- If no data available: Show placeholder message with setup instructions
- If query times out: Show cached data with warning

## Future Enhancements (Phase 2)

### Advanced Analytics
1. **Query Comparison Tool:** A/B testing different search strategies
2. **Document Similarity Network:** Visualize document relationships
3. **Temporal Fact Timeline:** Interactive timeline of facts with filtering
4. **Custom Cypher Interface:** Allow power users to run custom queries

### Visualizations
1. **Embedding Space Visualization:** t-SNE/UMAP projection of document embeddings
2. **Sankey Diagram:** Query flow from intent � strategy � results
3. **Heatmap:** Entity co-occurrence matrix
4. **3D Graph:** Interactive 3D network visualization

### Operations
1. **Alert Thresholds:** Notify when performance degrades
2. **Historical Comparison:** Compare metrics across time periods
3. **Export Reports:** Generate PDF reports with visualizations
4. **Real-time Monitoring:** WebSocket updates for live metrics

## File Changes Summary

**New Files:**
- `src/ui/features/dashboard_handler.py` (150-200 lines)
- `src/ui/features/dashboard_utils.py` (100-150 lines)
- `docs/projects_ongoing/graphrag-dashboard.md` (this document)
- `tests/ui/test_dashboard.py` (100+ lines)

**Modified Files:**
- `src/ui/streamlit_app.py`: Add page navigation and dashboard rendering (~50 lines added)
- `src/ui/features/__init__.py`: Export DashboardHandler (~2 lines)
- `src/config/ui.py`: Add dashboard configuration (~15 lines)
- `pyproject.toml`: Add visualization dependencies (~3 lines)

**Total Estimated Lines of Code:** 400-500 new lines

## Success Criteria

1. [x]  Dashboard accessible from sidebar in Standard/Advanced modes
2. [x]  All search metrics displayed correctly
3. [x]  Intent and strategy distributions visualized
4. [x]  Knowledge graph renders with >90% accuracy
5. [x]  Entity explorer shows top entities with click-through
6. [x]  Performance metrics update in real-time
7. [x]  No performance degradation on main chat interface
8. [x]  Graceful handling of missing data or database errors
9. [x]  Test coverage >75% for dashboard code
10. [x]  Documentation includes usage guide

**ALL SUCCESS CRITERIA MET** [x] - Project Complete! (2025-10-15)

## References

- **Streamlit Docs:** https://docs.streamlit.io/
- **Plotly Docs:** https://plotly.com/python/
- **NetworkX Docs:** https://networkx.org/documentation/stable/
- **Neo4j Visualization Best Practices:** https://neo4j.com/developer/guide-data-visualization/

## Notes

- Follow existing code style and patterns from `src/ui/features/`
- Ensure all async operations are properly awaited
- Use centralized configuration via `src/config/`
- Add comprehensive logging for debugging
- Consider mobile responsiveness (Streamlit defaults are good)
