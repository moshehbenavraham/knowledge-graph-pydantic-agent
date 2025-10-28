"""
Comprehensive tests for DashboardHandler - analytics data retrieval with caching.

Covers dashboard_handler.py and dashboard_utils.py together.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.ui.features.dashboard_handler import DashboardHandler
from src.ui.features.dashboard_utils import (
    generate_entity_cypher,
    generate_entity_timeline_cypher,
    generate_relationship_cypher,
    generate_top_entities_cypher,
)

# ===== Fixtures =====


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager."""
    cm = Mock()
    # Set up async context managers for connections
    pg_ctx = AsyncMock()
    pg_ctx.__aenter__ = AsyncMock()
    pg_ctx.__aexit__ = AsyncMock(return_value=False)
    cm.get_pg_connection = Mock(return_value=pg_ctx)

    neo4j_ctx = AsyncMock()
    neo4j_ctx.__aenter__ = AsyncMock()
    neo4j_ctx.__aexit__ = AsyncMock(return_value=False)
    cm.get_neo4j_connection = Mock(return_value=neo4j_ctx)

    neo4j_session_ctx = AsyncMock()
    neo4j_session_ctx.__aenter__ = AsyncMock()
    neo4j_session_ctx.__aexit__ = AsyncMock(return_value=False)
    cm.get_neo4j_session = Mock(return_value=neo4j_session_ctx)

    return cm


@pytest.fixture
def dashboard_handler(mock_connection_manager):
    """Create DashboardHandler instance."""
    return DashboardHandler(mock_connection_manager)


# ===== DashboardHandler Tests =====


class TestDashboardHandlerInit:
    """Test DashboardHandler initialization."""

    def test_init_with_connection_manager(self, mock_connection_manager):
        """Test initialization with connection manager."""
        handler = DashboardHandler(mock_connection_manager)

        assert handler.connection_manager == mock_connection_manager
        assert handler._cache == {}

    def test_init_without_connection_manager(self):
        """Test initialization without connection manager."""
        handler = DashboardHandler(None)

        assert handler.connection_manager is not None


class TestDashboardCache:
    """Test dashboard caching."""

    def test_get_cached_miss(self, dashboard_handler):
        """Test cache miss."""
        result = dashboard_handler._get_cached("nonexistent")

        assert result is None

    def test_set_and_get_cache(self, dashboard_handler):
        """Test caching values."""
        test_value = {"test": "data"}

        dashboard_handler._set_cache("test_key", test_value)
        cached = dashboard_handler._get_cached("test_key")

        assert cached == test_value

    def test_cache_expiration(self, dashboard_handler):
        """Test cache expires after TTL."""
        dashboard_handler._cache_ttl = timedelta(seconds=0)
        test_value = {"test": "data"}

        dashboard_handler._set_cache("test_key", test_value)

        import time

        time.sleep(0.1)

        cached = dashboard_handler._get_cached("test_key")
        assert cached is None


@pytest.mark.asyncio
class TestSearchMetrics:
    """Test search metrics retrieval."""

    async def test_get_search_metrics_basic(self, dashboard_handler):
        """Test fetching search metrics."""
        mock_summary = {
            "total_searches": 100,
            "avg_latency_ms": 150.5,
            "avg_vector_latency_ms": 50.0,
            "avg_graph_latency_ms": 100.0,
            "graph_boosts": 30,
            "entity_boosts": 25,
            "cache_hits": 20,
            "avg_entities_found": 5,
            "avg_relationships_found": 3,
        }

        mock_strategies = [
            {"strategy_used": "HYBRID", "search_count": 60},
            {"strategy_used": "VECTOR_HEAVY", "search_count": 40},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_summary)
        mock_conn.fetch = AsyncMock(return_value=mock_strategies)

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        metrics = await dashboard_handler.get_search_metrics(window="7d")

        assert metrics["total_searches"] == 100
        assert metrics["avg_latency_ms"] == 150.5

    async def test_get_search_metrics_caching(self, dashboard_handler):
        """Test that metrics are cached."""
        mock_summary = {
            "total_searches": 100,
            "avg_latency_ms": 150.5,
            "avg_vector_latency_ms": 50.0,
            "avg_graph_latency_ms": 100.0,
            "graph_boosts": 30,
            "entity_boosts": 25,
            "cache_hits": 20,
            "avg_entities_found": 5,
            "avg_relationships_found": 3,
        }
        mock_strategies = [{"strategy_used": "HYBRID", "search_count": 100}]

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_summary)
        mock_conn.fetch = AsyncMock(return_value=mock_strategies)

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        # First call
        metrics1 = await dashboard_handler.get_search_metrics(window="7d")

        # Second call (should use cache)
        metrics2 = await dashboard_handler.get_search_metrics(window="7d")

        assert metrics1 == metrics2
        # Should only query database once
        assert mock_conn.fetchrow.call_count == 1

    async def test_get_search_metrics_different_windows(self, dashboard_handler):
        """Test metrics with different time windows."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={})

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        await dashboard_handler.get_search_metrics(window="24h")

        # Verify interval was converted correctly
        call_args = mock_conn.fetchrow.call_args
        query = call_args[0][0]
        assert "24 hours" in query


# ===== Cypher Query Generation Tests (dashboard_utils.py) =====


class TestGenerateEntityCypher:
    """Test entity Cypher query generation."""

    def test_generate_basic_query(self):
        """Test basic entity query without filters."""
        query = generate_entity_cypher(filters=None, limit=50)

        assert "MATCH (e:Entity)" in query
        assert "LIMIT 50" in query

    def test_generate_with_entity_types(self):
        """Test query with entity type filters."""
        filters = {"entity_types": ["Organization", "Product"]}

        query = generate_entity_cypher(filters=filters, limit=50)

        assert "'Organization'" in query
        assert "'Product'" in query
        assert "e.type IN" in query

    def test_generate_with_search_term(self):
        """Test query with search term."""
        filters = {"search_term": "OpenAI"}

        query = generate_entity_cypher(filters=filters, limit=50)

        assert "toLower(e.name) CONTAINS" in query
        assert "'OpenAI'" in query

    def test_generate_with_min_relationships(self):
        """Test query with minimum relationships filter."""
        filters = {"min_relationships": 5}

        query = generate_entity_cypher(filters=filters, limit=50)

        assert "rel_count >= 5" in query

    def test_generate_with_all_filters(self):
        """Test query with all filters combined."""
        filters = {
            "entity_types": ["Organization"],
            "search_term": "OpenAI",
            "min_relationships": 3,
        }

        query = generate_entity_cypher(filters=filters, limit=100)

        assert "e.type IN" in query
        assert "toLower(e.name) CONTAINS" in query
        assert "rel_count >= 3" in query
        assert "LIMIT 100" in query


class TestGenerateRelationshipCypher:
    """Test relationship Cypher query generation."""

    def test_generate_basic_query(self):
        """Test basic relationship query."""
        query = generate_relationship_cypher(entity_ids=None, limit=100)

        assert "MATCH (source:Entity)-[r]->(target:Entity)" in query
        assert "LIMIT 100" in query

    def test_generate_with_entity_ids(self):
        """Test query filtered by entity IDs."""
        entity_ids = ["entity_123", "entity_456"]

        query = generate_relationship_cypher(entity_ids=entity_ids, limit=50)

        assert "'entity_123'" in query
        assert "'entity_456'" in query
        assert "WHERE source.id IN" in query

    def test_generate_returns_properties(self):
        """Test that query returns relationship properties."""
        query = generate_relationship_cypher()

        assert "properties(r)" in query
        assert "type(r)" in query


class TestGenerateTopEntitiesCypher:
    """Test top entities Cypher query generation."""

    def test_generate_top_entities_query(self):
        """Test generating top entities query."""
        query = generate_top_entities_cypher(limit=10)

        assert "MATCH (e:Entity)" in query
        assert "ORDER BY" in query
        assert "LIMIT 10" in query


class TestGenerateEntityTimelineCypher:
    """Test entity timeline Cypher query generation."""

    def test_generate_timeline_query(self):
        """Test generating entity timeline query."""
        query = generate_entity_timeline_cypher(entity_id="entity_123")

        assert "'entity_123'" in query
        assert "LIMIT 50" in query


# ===== Additional Comprehensive Tests =====


@pytest.mark.asyncio
class TestGraphData:
    """Test graph data retrieval."""

    async def test_get_graph_data_success(self, dashboard_handler):
        """Test successful graph data retrieval."""
        mock_neo4j_session = AsyncMock()
        mock_entity_result = AsyncMock()
        mock_entity_result.data = AsyncMock(
            return_value=[
                {"id": "e1", "name": "Entity 1", "type": "person", "relationship_count": 5},
                {"id": "e2", "name": "Entity 2", "type": "company", "relationship_count": 3},
            ]
        )
        mock_rel_result = AsyncMock()
        mock_rel_result.data = AsyncMock(
            return_value=[
                {
                    "source_id": "e1",
                    "target_id": "e2",
                    "relationship_type": "WORKS_FOR",
                    "summary": "",
                },
            ]
        )
        mock_neo4j_session.run = AsyncMock(side_effect=[mock_entity_result, mock_rel_result])

        dashboard_handler.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_neo4j_session
        )

        graph_data = await dashboard_handler.get_graph_data(limit=50)

        assert len(graph_data["entities"]) == 2
        assert len(graph_data["relationships"]) == 1

    async def test_get_graph_data_error(self, dashboard_handler):
        """Test graph data error handling."""
        mock_neo4j_session = AsyncMock()
        mock_neo4j_session.run = AsyncMock(side_effect=Exception("Neo4j error"))

        dashboard_handler.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_neo4j_session
        )

        graph_data = await dashboard_handler.get_graph_data()

        assert graph_data["entities"] == []
        assert graph_data["relationships"] == []
        assert "error" in graph_data


@pytest.mark.asyncio
class TestTopEntities:
    """Test top entities retrieval."""

    async def test_get_top_entities_success(self, dashboard_handler):
        """Test successful top entities retrieval."""
        mock_neo4j_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(
            return_value=[
                {
                    "id": "e1",
                    "name": "Top Entity",
                    "type": "person",
                    "relationship_count": 100,
                    "chunk_count": 50,
                    "created_at": datetime.now(),
                },
            ]
        )
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        dashboard_handler.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_neo4j_session
        )

        entities = await dashboard_handler.get_top_entities(limit=20)

        assert len(entities) == 1
        assert entities[0]["name"] == "Top Entity"

    async def test_get_top_entities_error(self, dashboard_handler):
        """Test top entities error handling."""
        mock_neo4j_session = AsyncMock()
        mock_neo4j_session.run = AsyncMock(side_effect=Exception("Query failed"))

        dashboard_handler.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_neo4j_session
        )

        entities = await dashboard_handler.get_top_entities()

        assert entities == []


@pytest.mark.asyncio
class TestEntityTimeline:
    """Test entity timeline retrieval."""

    async def test_get_entity_timeline_success(self, dashboard_handler):
        """Test successful entity timeline retrieval."""
        mock_neo4j_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(
            return_value=[
                {
                    "description": "Event 1",
                    "valid_from": datetime(2024, 1, 1),
                    "valid_to": None,
                    "created_at": datetime(2024, 1, 1),
                },
            ]
        )
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        dashboard_handler.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_neo4j_session
        )

        timeline = await dashboard_handler.get_entity_timeline("entity-123")

        assert len(timeline) == 1
        assert timeline[0]["description"] == "Event 1"

    async def test_get_entity_timeline_error(self, dashboard_handler):
        """Test entity timeline error handling."""
        mock_neo4j_session = AsyncMock()
        mock_neo4j_session.run = AsyncMock(side_effect=Exception("Timeline query failed"))

        dashboard_handler.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_neo4j_session
        )

        timeline = await dashboard_handler.get_entity_timeline("entity-456")

        assert timeline == []


@pytest.mark.asyncio
class TestPerformanceMetrics:
    """Test performance metrics retrieval."""

    async def test_get_performance_metrics_success(self, dashboard_handler):
        """Test successful performance metrics retrieval."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            side_effect=[
                {
                    "avg_vector_latency_ms": 50.0,
                    "avg_graph_latency_ms": 30.0,
                    "avg_ranking_latency_ms": 10.0,
                    "avg_total_latency_ms": 90.0,
                    "p50_latency_ms": 85.0,
                    "p95_latency_ms": 120.0,
                    "p99_latency_ms": 150.0,
                    "cache_hits": 40,
                    "total_searches": 100,
                },
                {
                    "pg_active_connections": 5,
                    "pg_idle_connections": 3,
                    "neo4j_active_connections": 2,
                    "system_cache_hit_rate": 0.45,
                },
            ]
        )

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        metrics = await dashboard_handler.get_performance_metrics(window="7d")

        assert metrics["vector_latency_ms"] == 50.0
        assert metrics["p50_latency_ms"] == 85.0

    async def test_get_performance_metrics_error(self, dashboard_handler):
        """Test performance metrics error handling."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Metrics query failed"))

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        metrics = await dashboard_handler.get_performance_metrics()

        assert metrics["vector_latency_ms"] == 0
        assert "error" in metrics


@pytest.mark.asyncio
class TestIntentDistribution:
    """Test intent distribution retrieval."""

    async def test_get_intent_distribution_success(self, dashboard_handler):
        """Test successful intent distribution retrieval."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "detected_intent": "VECTOR_HEAVY",
                    "search_count": 60,
                    "avg_latency_ms": 100.0,
                    "avg_chunks_returned": 10,
                },
                {
                    "detected_intent": "HYBRID",
                    "search_count": 40,
                    "avg_latency_ms": 150.0,
                    "avg_chunks_returned": 12,
                },
            ]
        )

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        distribution = await dashboard_handler.get_intent_distribution(window="7d")

        assert distribution["VECTOR_HEAVY"] == 60.0
        assert distribution["HYBRID"] == 40.0

    async def test_get_intent_distribution_error(self, dashboard_handler):
        """Test intent distribution error handling."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("Query failed"))

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        distribution = await dashboard_handler.get_intent_distribution(window="24h")

        assert distribution == {}


@pytest.mark.asyncio
class TestTimeSeriesData:
    """Test time series data retrieval."""

    async def test_get_time_series_data_success(self, dashboard_handler):
        """Test successful time series data retrieval."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "timestamp": datetime(2024, 1, 1),
                    "searches": 100,
                    "latency": 150.0,
                    "cache_hits": 40,
                    "graph_boosts": 30,
                },
            ]
        )

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        data = await dashboard_handler.get_time_series_data(window="7d", metric="searches")

        assert len(data) == 1
        assert data[0]["searches"] == 100

    async def test_get_time_series_data_error(self, dashboard_handler):
        """Test time series data error handling."""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("Time series query failed"))

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        data = await dashboard_handler.get_time_series_data(window="30d", metric="latency")

        assert data == []


@pytest.mark.asyncio
class TestToolUsageMetrics:
    """Test tool usage metrics retrieval."""

    async def test_get_tool_usage_metrics_success(self, dashboard_handler):
        """Test successful tool usage metrics retrieval."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            return_value={"total_calls": 500, "unique_tools": 10, "avg_success_rate": 0.95}
        )
        mock_conn.fetch = AsyncMock(
            return_value=[
                {
                    "tool_name": "smart_search",
                    "total_calls": 200,
                    "success_rate": 0.98,
                    "avg_execution_time_ms": 100.0,
                    "p95_execution_time_ms": 150.0,
                },
            ]
        )

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        metrics = await dashboard_handler.get_tool_usage_metrics(window="7d")

        assert metrics["total_calls"] == 500
        assert len(metrics["tools"]) == 1

    async def test_get_tool_usage_metrics_error(self, dashboard_handler):
        """Test tool usage metrics error handling."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Tool metrics failed"))

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        metrics = await dashboard_handler.get_tool_usage_metrics()

        assert metrics["total_calls"] == 0
        assert "error" in metrics


@pytest.mark.asyncio
class TestAgentInteractionMetrics:
    """Test agent interaction metrics retrieval."""

    async def test_get_agent_interaction_metrics_success(self, dashboard_handler):
        """Test successful agent interaction metrics retrieval."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            return_value={
                "total_interactions": 1000,
                "unique_sessions": 150,
                "avg_response_time_ms": 250.0,
                "rag_usage_rate": 0.75,
                "thumbs_up": 80,
                "thumbs_down": 20,
                "feedback_rate": 0.10,
            }
        )

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        metrics = await dashboard_handler.get_agent_interaction_metrics(window="7d")

        assert metrics["total_interactions"] == 1000
        assert metrics["thumbs_up"] == 80

    async def test_get_agent_interaction_metrics_error(self, dashboard_handler):
        """Test agent interaction metrics error handling."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=Exception("Interaction query failed"))

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        metrics = await dashboard_handler.get_agent_interaction_metrics()

        assert metrics["total_interactions"] == 0
        assert "error" in metrics


@pytest.mark.asyncio
class TestMaterializedViewsRefresh:
    """Test materialized views refresh."""

    async def test_refresh_materialized_views_success(self, dashboard_handler):
        """Test successful materialized views refresh."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        result = await dashboard_handler.refresh_materialized_views()

        assert result is True

    async def test_refresh_materialized_views_error(self, dashboard_handler):
        """Test materialized views refresh error handling."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Refresh failed"))

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        result = await dashboard_handler.refresh_materialized_views()

        assert result is False


class TestClearCache:
    """Test cache clearing."""

    def test_clear_cache(self, dashboard_handler):
        """Test clearing all cache."""
        dashboard_handler._set_cache("key1", "value1")
        dashboard_handler._set_cache("key2", "value2")

        dashboard_handler.clear_cache()

        assert dashboard_handler._cache == {}
