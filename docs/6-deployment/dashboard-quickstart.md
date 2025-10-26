# GraphRAG Dashboard - Quick Start Guide

**Version:** 1.0.2
**Date:** 2025-10-16
**Status:** Production Ready ✅

## Overview

The GraphRAG Analytics Dashboard provides real-time visualization and monitoring of your Agentic RAG system, including search patterns, knowledge graph structure, entity relationships, and system performance.

## Prerequisites

### Required
- **Python 3.11+** installed
- **PostgreSQL/Supabase** configured and running
- **Neo4j Aura** configured and running (for graph visualization)
- **Luminari Agent** installed with dashboard dependencies

### Installation

1. **Install Dashboard Dependencies:**
   ```bash
   pip install plotly>=5.18.0 networkx>=3.2.1 pyvis>=0.3.2
   # OR using uv
   uv pip install plotly>=5.18.0 networkx>=3.2.1 pyvis>=0.3.2
   ```

2. **Verify Environment Variables:**
   Ensure your `.env` file has the following configured:
   ```bash
   # PostgreSQL/Supabase
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_KEY=your_service_key

   # Neo4j Aura
   NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password

   # Optional: Enable graph features
   ENABLE_GRAPH=true
   ENABLE_GRAPH_SEARCH=true
   ```

## Accessing the Dashboard

### Option 1: Standard Mode (Recommended)
```bash
make run-ui
# OR
UI_MODE=standard streamlit run src/ui/streamlit_app.py
```

### Option 2: Advanced Mode (All Features)
```bash
make run-ui-advanced
# OR
UI_MODE=advanced streamlit run src/ui/streamlit_app.py
```

Once the UI loads (http://localhost:8501):
1. Look for the sidebar navigation
2. Click **"📊 Dashboard"**
3. Dashboard will initialize and display analytics

## Dashboard Features

### 1. 🔍 Search Analytics
**Location:** Top section

**What it shows:**
- Total number of searches performed
- Average query latency in milliseconds
- Most frequently used search strategy
- Graph boost rate (how often graph data enhances results)
- Bar chart showing distribution of search strategies

**Use cases:**
- Monitor system performance over time
- Identify which search strategies are most effective
- Track latency trends to optimize performance

---

### 2. 🎯 Intent Analysis
**Location:** Middle-left section

**What it shows:**
- Pie chart of query intent distribution
- Breakdown of VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, TEMPORAL, ENTITY_FOCUSED queries

**Use cases:**
- Understand what types of queries users are asking
- Optimize search strategy weights based on common intents
- Validate that intent analyzer is working correctly

---

### 3. 🕸️ Knowledge Graph Visualization
**Location:** Full-width section (below Intent Analysis)

**What it shows:**
- **Interactive network graph** powered by pyvis (Neo4j Enterprise-style)
- **Draggable nodes** - Click and drag individual nodes to reposition and explore relationships
- **Physics simulation** - Nodes naturally repel and attract based on connections (ForceAtlas2 algorithm)
- **Color-coded by entity type** - 8 distinct colors (person, company, organization, location, event, technology, product, concept)
- **Dynamic node sizing** - Node size scales with connection count (15-50px range)
- **Adjustable entity limit** - Display 10-200 entities via slider
- **Rich tooltips** - Hover to see entity name, type, connections, and interaction hints

**Interactive Controls:**
- **Drag nodes:** Click and drag any node to reposition it manually
- **Pan canvas:** Click and drag the background to move the entire graph
- **Zoom:** Scroll wheel to zoom in/out
- **Layout selector:** Choose Force-Directed (default), Hierarchical, or Circular layout
- **Navigation buttons:** Use built-in pan/zoom controls in bottom-right corner
- **Hover tooltips:** Move mouse over nodes to see detailed information

**Tips for Exploration:**
1. **Start with force-directed layout** - Lets physics organize the graph naturally
2. **Drag highly connected nodes** to the center to see their relationships clearly
3. **Use hierarchical layout** for organizational/temporal structures
4. **Reduce entity count** if the graph feels cluttered
5. **Zoom in** on specific clusters to examine details

**Use cases:**
- Visualize knowledge graph structure and connections
- Identify highly connected entities (hubs)
- Manually arrange nodes to understand complex relationships
- Discover unexpected connections between entities
- Verify entity extraction quality

---

### 4. 🏷️ Entity Explorer
**Location:** Bottom-left section

**What it shows:**
- Table of top 20 most connected entities
- Columns: Entity Name, Type, Relationships, Chunks
- Entity timeline viewer (select entity from dropdown)

**How to use:**
1. Browse the top entities table
2. Select an entity from the dropdown
3. View temporal facts timeline for that entity
4. See when facts were created and their validity periods

**Use cases:**
- Identify most important entities in your knowledge base
- Review entity extraction results
- Explore temporal information about specific entities
- Validate fact extraction accuracy

---

### 5. ⚡ Performance Metrics
**Location:** Bottom-right section

**What it shows:**
- Query latency breakdown (Vector, Graph, Total)
- Cache hit rate percentage
- Active/idle database connections
- Detailed PostgreSQL and Neo4j metrics (expandable)

**Metrics included:**
- Total queries executed
- Failed query count
- Average query time (ms)
- Connection pool status

**Use cases:**
- Monitor database performance
- Identify bottlenecks (vector vs graph search)
- Track cache effectiveness
- Ensure database connections are healthy

---

## Dashboard Controls

### 🔄 Refresh Button
**Location:** Top-right corner

**What it does:**
- Clears the 30-second cache
- Forces fresh data retrieval from all sources
- Useful when you've just ingested new documents

### ⚙️ UI Mode Selector
**Location:** Sidebar

**Options:**
- **Simple:** Dashboard not available
- **Standard:** Dashboard accessible ✅
- **Advanced:** Dashboard accessible + all advanced features ✅

## Common Workflows

### Workflow 1: After Document Ingestion
1. Ingest new documents: `make ingest`
2. Open dashboard
3. Click "🔄 Refresh"
4. Check:
   - Entity Explorer for new entities
   - Knowledge Graph for new relationships
   - Search Analytics for updated metrics

### Workflow 2: Performance Monitoring
1. Navigate to Dashboard
2. Review Performance Metrics section
3. Check:
   - Average latencies (should be <1s for most queries)
   - Cache hit rate (higher is better)
   - Database connections (should not be at max)
4. If issues found:
   - Check database health
   - Review connection pool settings
   - Consider increasing cache TTL

### Workflow 3: Search Strategy Optimization
1. Review Search Analytics section
2. Check strategy distribution
3. Review Intent Analysis pie chart
4. Adjust search weights in config if needed:
   ```python
   # src/agentic_rag/config.py
   search_strategy_weights = {
       "VECTOR_HEAVY": 0.3,
       "GRAPH_HEAVY": 0.2,
       "HYBRID": 0.4,  # Increase if HYBRID performs well
       # ...
   }
   ```

### Workflow 4: Knowledge Graph Exploration
1. Navigate to Knowledge Graph section
2. Adjust "Max Entities" slider (start with 50-100)
3. Choose a layout (Force-Directed recommended for initial exploration)
4. **Interact with the graph:**
   - Drag nodes to reposition them
   - Click-drag background to pan
   - Scroll to zoom in/out
   - Hover over nodes for details
5. Look for:
   - Highly connected entities (large nodes, many edges)
   - Entity clusters (groups of related entities)
   - Isolated entities (may need better extraction)
   - Unexpected relationships between entities
6. **Pro tips:**
   - Drag hub entities to the center
   - Switch to hierarchical layout for organizational structures
   - Reduce entity count if graph is too cluttered
   - Use zoom to focus on specific clusters
7. Select entities in Entity Explorer for detailed timelines

## Troubleshooting

### Dashboard Won't Load
**Error:** "Failed to initialize dashboard"

**Solutions:**
1. Check database connections:
   ```bash
   # Test PostgreSQL
   psql $SUPABASE_URL

   # Test Neo4j (if installed locally)
   cypher-shell -a $NEO4J_URI -u $NEO4J_USER -p $NEO4J_PASSWORD
   ```
2. Verify environment variables in `.env`
3. Check logs for specific error messages

### No Data Displayed
**Symptoms:** All sections show "No data available"

**Solutions:**
1. Ensure documents have been ingested:
   ```bash
   make ingest
   ```
2. Perform some searches in the Chat interface to generate metrics
3. Click "🔄 Refresh" to reload data
4. Check that `ENABLE_GRAPH=true` in `.env`

### Graph Visualization Empty
**Symptoms:** "No entities in knowledge graph yet"

**Solutions:**
1. Verify Neo4j is running and accessible
2. Check that documents were ingested with graph extraction:
   ```bash
   make ingest-clean  # Full re-ingestion
   ```
3. Verify `ENABLE_GRAPH_SEARCH=true` in `.env`
4. Check Neo4j has entities:
   ```cypher
   MATCH (e:Entity) RETURN count(e)
   ```

### Slow Dashboard Loading
**Symptoms:** Dashboard takes >10 seconds to load

**Solutions:**
1. Reduce "Max Entities" slider value
2. Check database connection latency
3. Verify cache is working (should improve after first load)
4. Consider increasing cache TTL in `src/config/ui.py`:
   ```python
   class DashboardConfig:
       cache_ttl_seconds: int = 60  # Increase from 30
   ```

### Connection Pool Errors
**Error:** "Too many connections" or "Connection pool exhausted"

**Solutions:**
1. Check active connections in Performance Metrics
2. Increase pool size in ConnectionManager:
   ```python
   # src/agentic_rag/config.py
   pg_pool_size: int = 20  # Increase if needed
   neo4j_pool_size: int = 50
   ```
3. Restart the application to reset pools

## Best Practices

1. **Regular Monitoring:**
   - Check dashboard after each ingestion
   - Monitor performance metrics daily
   - Review intent distribution weekly

2. **Performance Optimization:**
   - Keep Max Entities slider at reasonable values (20-50)
   - Use cache effectively (don't over-refresh)
   - Monitor latency trends

3. **Data Quality:**
   - Review entity extraction quality in Entity Explorer
   - Verify relationships make sense in graph visualization
   - Check temporal facts for accuracy

4. **System Health:**
   - Watch connection pool usage
   - Monitor cache hit rates
   - Track query failure rates

## Advanced Configuration

### Customizing Dashboard Behavior

Edit `src/config/ui.py`:

```python
@dataclass
class DashboardConfig:
    enabled: bool = True                    # Enable/disable dashboard
    refresh_interval_seconds: int = 30      # Auto-refresh interval
    max_entities_display: int = 50          # Default entity limit
    default_time_window: str = "7d"         # Time window for metrics
    enable_export: bool = True              # Enable CSV/JSON export
    cache_ttl_seconds: int = 30             # Cache time-to-live
```

### Extending Dashboard Functionality

The dashboard is built with modular components:

- **Handler:** `src/ui/features/dashboard_handler.py`
- **Utilities:** `src/ui/features/dashboard_utils.py`
- **Tests:** `tests/ui/test_dashboard.py`

To add new visualizations:
1. Add data retrieval method to `DashboardHandler`
2. Add formatting utilities to `dashboard_utils.py`
3. Add rendering code to `render_dashboard()` in `streamlit_app.py`
4. Write tests in `test_dashboard.py`

## Support

### Documentation
- Implementation plan: `docs/projects_ongoing/graphrag-dashboard.md`
- Bug fixes: `docs/projects_ongoing/graphrag-dashboard-BUGS-FIXED.md`
- Main README: `README.md` (UI Features section)

### Getting Help
1. Check the troubleshooting section above
2. Review logs: `logs/` directory
3. Check database connectivity
4. Verify environment configuration

## Feature Roadmap

**Future Enhancements** (see `graphrag-dashboard.md` Phase 2):
- Query comparison tool for A/B testing
- Document similarity network visualization
- Custom Cypher query interface
- Embedding space visualization (t-SNE/UMAP)
- Alert thresholds and notifications
- Historical metrics comparison
- PDF report generation

---

**Last Updated:** 2025-10-16
**Dashboard Version:** 1.0.2
**Compatible with:** Luminari Agent v1.0.2+
