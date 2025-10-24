"""
Comprehensive tests for DashboardHandler - analytics data retrieval with caching.

Covers dashboard_handler.py and dashboard_utils.py together.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from src.ui.features.dashboard_handler import DashboardHandler
from src.ui.features.dashboard_utils import (
    generate_entity_cypher,
    generate_relationship_cypher,
    generate_top_entities_cypher,
    generate_entity_timeline_cypher,
)


# ===== Fixtures =====


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager."""
    cm = Mock()
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
            "total_graph_boosts": 30,
            "total_entity_boosts": 25,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_summary)

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = mock_conn
        dashboard_handler.connection_manager.get_pg_connection.return_value.__aexit__.return_value = AsyncMock(return_value=False)

        metrics = await dashboard_handler.get_search_metrics(window="7d")

        assert metrics["total_searches"] == 100
        assert metrics["avg_latency_ms"] == 150.5

    async def test_get_search_metrics_caching(self, dashboard_handler):
        """Test that metrics are cached."""
        mock_summary = {"total_searches": 100}
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_summary)

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = mock_conn
        dashboard_handler.connection_manager.get_pg_connection.return_value.__aexit__.return_value = AsyncMock(return_value=False)

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

        dashboard_handler.connection_manager.get_pg_connection.return_value.__aenter__.return_value = mock_conn
        dashboard_handler.connection_manager.get_pg_connection.return_value.__aexit__.return_value = AsyncMock(return_value=False)

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
        query = generate_entity_timeline_cypher(entity_id="entity_123", limit=20)

        assert "'entity_123'" in query
        assert "Episode" in query or "MENTIONED_IN" in query
        assert "LIMIT 20" in query
