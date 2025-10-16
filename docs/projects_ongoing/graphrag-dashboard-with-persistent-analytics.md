# GraphRAG Dashboard with Persistent Analytics - Implementation Plan

**Version:** 1.2.0
**Status:** Architecture & Planning
**Architect:** Senior Lead Engineer
**Estimated Effort:** 5-7 days
**Priority:** High

---

## Executive Summary

Migrate the GraphRAG dashboard from transient in-memory statistics to the persistent analytics platform introduced in v1.1.0. The work is a surgical refactor that reuses the existing logging pipeline and data model while keeping the UI and API contracts stable.

**Core principle:** all dashboard metrics are sourced from the analytics tables and materialized views in PostgreSQL, not from in-memory counters. The logging pipeline already captures the required data; the dashboard must read it efficiently.

---

## Current State Analysis

### What We Have (Strengths)

1. **Persistent analytics infrastructure (v1.1.0).** Five partitioned PostgreSQL tables (`search_analytics`, `tool_usage_analytics`, `agent_interactions`, `ingestion_analytics`, `system_metrics`) plus three materialized views (`daily_search_summary`, `intent_distribution_7d`, `tool_performance_7d`). An `AnalyticsLogger` batches events with <5 ms overhead.
2. **Dashboard UI (Streamlit).** Interactive GraphRAG dashboard with pyvis graph visualization, sections for search analytics, intent analysis, knowledge graph, entity explorer, and performance metrics. Supports real-time refresh, error handling, and Neo4j integration.
3. **DashboardHandler implementation.** Clean architecture with `ConnectionManager`, 30 s cache, and helper methods (`get_search_metrics`, `get_intent_distribution`, `get_performance_metrics`, etc.).

### What Needs Work (Gaps)

1. **In-memory dependencies.** Metrics methods call `HybridSearch.get_stats()`, `IntentAnalyzer.get_stats()`, `VectorSearch.get_stats()`, and `GraphSearch.get_stats()`. Data resets on restart, is not multi-instance safe, and cannot provide historical trends.
2. **Feature coverage.** Time-series queries are unimplemented, tool usage and agent interaction analytics are absent, no percentile latency metrics, and no time-window filtering.
3. **Architecture coupling.** The handler spins up search components solely to read counters, preventing analytics from loading when search services are idle and adding unnecessary dependencies.

---

## Architecture Design

### Design Principles

1. Single source of truth: analytics tables and materialized views.
2. Clean separation: dashboard code never touches runtime search components for metrics.
3. Performance first: favor materialized views, parameterized queries, and caching.
4. Backward compatibility: preserve handler signatures, UI behavior, and API responses.
5. Non-breaking deployment: no changes to the logging pipeline or database schema.
6. Production safety: graceful degradation and clear operational observability.

### Data Flow Overview

1. Search, tool, and agent operations emit events through `AnalyticsLogger`.
2. The logger batches events asynchronously and writes to partitioned PostgreSQL tables.
3. Hourly jobs refresh materialized views that pre-aggregate expensive queries.
4. `DashboardHandler` queries tables or views via `ConnectionManager`, layering 30 s caching.
5. Streamlit UI screens and REST endpoints render the cached analytics payloads.

---

## Implementation Plan

### Phase 1: Core DashboardHandler Refactoring (Day 1-2)

**Goal:** Serve dashboard metrics exclusively from the analytics database.

#### 1.1 Replace Search Metrics Queries

Current approach reads `HybridSearch.get_stats()`. Replace with a direct query:

```python
async with self.connection_manager.get_pg_connection() as conn:
    summary = await conn.fetchrow(
        """
        SELECT
            COUNT(*) AS total_searches,
            AVG(total_latency_ms) AS avg_latency_ms,
            COUNT(*) FILTER (WHERE graph_boost_applied) AS graph_boosts,
            COUNT(*) FILTER (WHERE entity_boost_applied) AS entity_boosts,
            COUNT(*) FILTER (WHERE cache_hit) AS cache_hits
        FROM search_analytics
        WHERE created_at >= NOW() - INTERVAL '7 days'
        """
    )

    strategies = await conn.fetch(
        """
        SELECT strategy_used, search_count
        FROM intent_distribution_7d
        ORDER BY search_count DESC
        """
    )
```

**Benefits:** historical data, multi-instance safety, and the ability to add time-window filters.

#### 1.2 Replace Intent Distribution Queries

Current approach reads `IntentAnalyzer.get_stats()`. Use the materialized view directly:

```python
async with self.connection_manager.get_pg_connection() as conn:
    rows = await conn.fetch(
        """
        SELECT
            detected_intent,
            search_count,
            avg_latency_ms,
            avg_chunks_returned
        FROM intent_distribution_7d
        ORDER BY search_count DESC
        """
    )

total = sum(row["search_count"] for row in rows) or 1
distribution = {
    row["detected_intent"]: row["search_count"] / total * 100 for row in rows
}
```

**Benefits:** leverages pre-computed data for fast queries and exposes latency by intent.

#### 1.3 Replace Performance Metrics Queries

Current implementation aggregates in-memory latency counters. Replace with percentile queries:

```python
async with self.connection_manager.get_pg_connection() as conn:
    metrics = await conn.fetchrow(
        """
        SELECT
            AVG(vector_latency_ms) AS avg_vector_latency_ms,
            AVG(graph_latency_ms) AS avg_graph_latency_ms,
            AVG(ranking_latency_ms) AS avg_ranking_latency_ms,
            AVG(total_latency_ms) AS avg_total_latency_ms,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_latency_ms) AS p50_latency_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms) AS p95_latency_ms,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_latency_ms) AS p99_latency_ms,
            COUNT(*) FILTER (WHERE cache_hit) / NULLIF(COUNT(*), 0)::float AS cache_hit_rate
        FROM search_analytics
        WHERE created_at >= NOW() - INTERVAL '7 days'
        """
    )
```

**Benefits:** exposes percentile latency, improved cache hit accuracy, and removes handler coupling.

#### 1.4 Remove `_ensure_search_components`

Delete the helper that lazily initializes search components. The handler should depend only on `ConnectionManager`, except for Neo4j interactions in graph visualisations. This simplifies initialization and allows analytics to load even when search backends are offline.

### Phase 2: New Analytics Features (Day 3)

#### 2.1 Implement `get_time_series_data`

```python
async def get_time_series_data(
    self,
    window: str = "7d",
    metric: str = "searches"
) -> list[dict[str, Any]]:
    if window in {"7d", "30d"}:
        days = 7 if window == "7d" else 30
        async with self.connection_manager.get_pg_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    date AS timestamp,
                    total_searches AS searches,
                    avg_latency_ms AS latency,
                    cache_hits,
                    graph_boosts
                FROM daily_search_summary
                WHERE date >= CURRENT_DATE - ($1::int) * INTERVAL '1 day'
                ORDER BY date ASC
                """,
                days,
            )
    else:
        async with self.connection_manager.get_pg_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    DATE_TRUNC('hour', created_at) AS timestamp,
                    COUNT(*) AS searches,
                    AVG(total_latency_ms) AS latency,
                    COUNT(*) FILTER (WHERE cache_hit) AS cache_hits,
                    COUNT(*) FILTER (WHERE graph_boost_applied) AS graph_boosts
                FROM search_analytics
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY DATE_TRUNC('hour', created_at)
                ORDER BY timestamp ASC
                """
            )

    return [
        {"timestamp": row["timestamp"], metric: row[metric]}
        for row in rows
        if metric in row
    ]
```

#### 2.2 Add `get_tool_usage_metrics`

```python
async def get_tool_usage_metrics(self, window: str = "7d") -> dict[str, Any]:
    async with self.connection_manager.get_pg_connection() as conn:
        summary = await conn.fetchrow(
            """
            SELECT
                SUM(total_calls) AS total_calls,
                COUNT(DISTINCT tool_name) AS unique_tools,
                AVG(success_rate) AS avg_success_rate
            FROM tool_performance_7d
            """
        )

        tools = await conn.fetch(
            """
            SELECT
                tool_name,
                total_calls,
                success_rate,
                avg_execution_time_ms,
                p95_execution_time_ms
            FROM tool_performance_7d
            ORDER BY total_calls DESC
            LIMIT 20
            """
        )

    return {
        "total_calls": summary["total_calls"] or 0,
        "unique_tools": summary["unique_tools"] or 0,
        "success_rate": summary["avg_success_rate"] or 0.0,
        "tools": [dict(row) for row in tools],
    }
```

#### 2.3 Add `get_agent_interaction_metrics`

```python
async def get_agent_interaction_metrics(self, window: str = "7d") -> dict[str, Any]:
    window_interval = window_to_interval(window)  # returns datetime.timedelta
    async with self.connection_manager.get_pg_connection() as conn:
        stats = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS unique_sessions,
                AVG(response_time_ms) AS avg_response_time_ms,
                COUNT(*) FILTER (WHERE rag_used) / NULLIF(COUNT(*), 0)::float AS rag_usage_rate,
                COUNT(*) FILTER (WHERE user_feedback = 'thumbs_up') AS thumbs_up,
                COUNT(*) FILTER (WHERE user_feedback = 'thumbs_down') AS thumbs_down,
                COUNT(*) FILTER (WHERE user_feedback IS NOT NULL) / NULLIF(COUNT(*), 0)::float AS feedback_rate
            FROM agent_interactions
            WHERE created_at >= NOW() - $1::interval
            """,
            window_interval,
        )

    return dict(stats or {})
```

Adjust the helper used in `window_to_interval` to validate inputs and prevent SQL injection.

### Phase 3: UI Enhancements (Day 4)

#### 3.1 Time-Series Visualisation

Add a "Trends Over Time" section in `src/ui/streamlit_app.py`:

```python
st.divider()
st.header("Trends Over Time")

col1, col2 = st.columns(2)
with col1:
    selected_window = st.selectbox("Time Window", ["24h", "7d", "30d"], index=1)
with col2:
    selected_metric = st.selectbox(
        "Metric",
        ["searches", "latency", "cache_hits", "graph_boosts"],
        format_func=lambda x: x.replace("_", " ").title(),
    )

try:
    series = await handler.get_time_series_data(
        window=selected_window,
        metric=selected_metric,
    )
    if series:
        df = pd.DataFrame(series)
        fig = px.line(
            df,
            x="timestamp",
            y=selected_metric,
            title=f"{selected_metric.replace('_', ' ').title()} Over {selected_window}",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No time-series data available for the selected window.")
except Exception:
    logger.exception("Error rendering time-series data")
    st.error("Unable to load trends. Please try again later.")
```

#### 3.2 Tool Usage Section

Add a "Tool Usage Analytics" block:

```python
st.divider()
st.header("Tool Usage Analytics")

try:
    tool_metrics = await handler.get_tool_usage_metrics()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Calls", tool_metrics["total_calls"])
    col2.metric("Unique Tools", tool_metrics["unique_tools"])
    col3.metric(
        "Average Success Rate",
        f"{tool_metrics['success_rate'] * 100:.1f}%",
    )

    st.dataframe(pd.DataFrame(tool_metrics["tools"]))
except Exception:
    logger.exception("Error rendering tool analytics")
    st.error("Unable to load tool usage analytics at this time.")
```

Add a similar section for agent interaction metrics with summary statistics and a table.

### Phase 4: Analytics API Endpoints (Day 5)

Create `src/api/endpoints/analytics.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.dependencies import get_connection_manager
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.ui.features.dashboard_handler import DashboardHandler

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class SearchMetricsResponse(BaseModel):
    total_searches: int
    avg_latency_ms: float
    most_used_strategy: str | None
    strategy_distribution: dict[str, int]


@router.get("/search-metrics", response_model=SearchMetricsResponse)
async def search_metrics(
    window: str = Query("7d", pattern="^(24h|7d|30d)$"),
    conn_manager: ConnectionManager = Depends(get_connection_manager),
) -> SearchMetricsResponse:
    handler = DashboardHandler(conn_manager)
    try:
        metrics = await handler.get_search_metrics(window=window)
        return SearchMetricsResponse(**metrics)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

Add similar endpoints for time-series, tool metrics, and agent interactions. Register the router in `src/api/main.py`.

### Phase 5: Testing and Validation (Day 6)

1. **Unit tests (`tests/ui/test_dashboard_handler.py`).**
   - Ensure each handler method issues queries against analytics tables.
   - Validate caching behavior and time-window parameter handling.
   - Assert graceful degradation when tables are missing (mock `asyncpg.UndefinedTableError`).
2. **Integration tests (`tests/integration/test_dashboard_analytics.py`).**
   - Execute a search and confirm analytics rows are created.
   - Refresh materialized views and assert dashboard data updates.
   - Hit the REST endpoints and validate response schemas.
3. **Manual QA checklist.**
   - Dashboard loads under 2 seconds with cached data.
   - Time-series widgets render for all windows.
   - Tool and agent sections populate after relevant activity.
   - UI communicates analytics initialization gracefully.

Example unit test:

```python
@pytest.mark.asyncio
async def test_get_search_metrics_queries_analytics_tables(mock_connection_manager):
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "total_searches": 100,
        "avg_latency_ms": 150.5,
        "graph_boosts": 30,
        "entity_boosts": 20,
        "cache_hits": 40,
    }
    mock_conn.fetch.return_value = [
        {"strategy_used": "HYBRID", "search_count": 60},
        {"strategy_used": "VECTOR_HEAVY", "search_count": 40},
    ]
    mock_connection_manager.get_pg_connection.return_value.__aenter__.return_value = mock_conn

    handler = DashboardHandler(mock_connection_manager)
    metrics = await handler.get_search_metrics()

    assert metrics["total_searches"] == 100
    mock_conn.fetchrow.assert_called_once()
```

### Phase 6: Documentation and Deployment (Day 7)

1. Update `docs/analytics_system.md`, `CLAUDE.md`, `README.md`, and `docs/CHANGELOG.md` with dashboard integration notes.
2. Document new endpoints in `docs/api_documentation.md`.
3. Add `docs/migrations/v1.1_to_v1.2_dashboard.md` summarizing upgrade steps.
4. Deployment checklist: run tests, refresh materialized views, monitor metrics after release, and update runbooks.

---

## Risk Assessment and Mitigation

### High Risks

1. **Slow dashboard queries.** Mitigate with materialized views, indexed filters, caching, and query timeouts. Profile with `EXPLAIN ANALYZE`.
2. **Missing analytics tables on fresh installs.** Provide health checks, fallback messaging, and optionally retain in-memory stats as a temporary fallback.

### Medium Risks

1. **Stale materialized views.** Document refresh cadence, expose "last refreshed" timestamps, and provide a manual refresh function.
2. **Unexpected downstream dependencies on `get_stats()`.** Keep existing methods, add deprecation warnings, and compile a removal plan for v2.0.0.

### Low Risks

1. **Increased PostgreSQL load.** Monitor resource usage, leverage connection pooling, and tune cache TTLs. Scale the database tier if dashboard adoption grows.

---

## Performance Targets

- Dashboard initial load under 2 seconds; cached refresh under 1 second.
- Time-series queries finish within 500 ms.
- REST endpoints satisfy P95 latency below 200 ms.
- Additional database load from dashboard queries stays below 10 QPS.

---

## Success Criteria

**Must have**

- All dashboard metrics sourced from analytics tables.
- Time-series charts, tool usage, and agent interaction sections render correctly.
- No regression in existing dashboard functionality or API contracts.
- Unit and integration tests pass in CI.

**Should have**

- Percentile latency metrics available in the UI.
- Time-window filtering for 24h, 7d, and 30d windows.
- Graceful error handling when analytics is initializing.

**Nice to have**

- CSV or JSON export of dashboard data.
- Grafana templates and alerting hooks for analytics anomalies.

---

## Timeline and Milestones

- **Day 1-2:** DashboardHandler refactor.
- **Day 3:** New analytics data methods.
- **Day 4:** UI enhancements.
- **Day 5:** REST endpoints.
- **Day 6:** Automated tests and manual QA.
- **Day 7:** Documentation and deployment readiness.

---

## Open Questions

1. What is the desired refresh cadence for materialized views in production?
2. Should cache TTL increase beyond 30 seconds to reduce database load?
3. Which time window should be the dashboard default (24h vs 7d vs 30d)?
4. Do analytics endpoints require separate rate limits compared to search APIs?
5. Should Grafana dashboard templates ship with v1.2.0 or wait for v1.3.0?

---

## Conclusion

The refactor turns the dashboard into a persistent, historically accurate analytics surface without rewriting the logging pipeline or disrupting the UI. By querying the analytics database directly, we eliminate restart volatility, support multi-instance deployments, and unlock richer reporting while maintaining backward compatibility. This plan keeps downtime at zero and preserves a clear path for future enhancements.
