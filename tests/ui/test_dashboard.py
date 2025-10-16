"""
Tests for GraphRAG Dashboard components.

Tests dashboard handler, utilities, and integration with search components.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ui.features.dashboard_handler import DashboardHandler
from src.ui.features.dashboard_utils import (
    aggregate_time_series,
    calculate_graph_statistics,
    format_graph_for_plotly,
    generate_entity_cypher,
    generate_relationship_cypher,
    generate_top_entities_cypher,
)


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager for testing."""
    manager = MagicMock()
    manager.get_neo4j_session = AsyncMock()
    manager.pg_metrics = MagicMock(
        active_connections=5,
        idle_connections=3,
        total_queries=100,
        failed_queries=2,
        avg_query_time_ms=15.5,
    )
    manager.neo4j_metrics = MagicMock(
        active_connections=3,
        idle_connections=2,
        total_queries=50,
        failed_queries=1,
        avg_query_time_ms=25.3,
    )
    return manager


@pytest.fixture
def dashboard_handler(mock_connection_manager):
    """Create dashboard handler with mocked dependencies."""
    handler = DashboardHandler(mock_connection_manager)

    # Mock search components
    handler.hybrid_search.get_stats = MagicMock(
        return_value={
            "searches": 100,
            "total_latency": 50.0,
            "strategies": {"HYBRID": 60, "VECTOR_HEAVY": 30, "GRAPH_HEAVY": 10},
            "graph_boosts": 20,
            "entity_boosts": 15,
        }
    )

    handler.vector_search.get_stats = MagicMock(
        return_value={
            "queries": 100,
            "cache_hits": 25,
            "avg_query_time_ms": 150.5,
        }
    )

    handler.graph_search.get_stats = MagicMock(
        return_value={
            "queries": 80,
            "entities_found": 200,
            "relationships_found": 350,
            "avg_query_time_ms": 250.3,
        }
    )

    handler.intent_analyzer.get_stats = MagicMock(
        return_value={
            "intents": {
                "VECTOR_HEAVY": 40,
                "GRAPH_HEAVY": 25,
                "HYBRID": 35,
            }
        }
    )

    return handler


# Test Dashboard Handler


@pytest.mark.asyncio
async def test_get_search_metrics(dashboard_handler):
    """Test search metrics retrieval."""
    metrics = await dashboard_handler.get_search_metrics()

    assert metrics["total_searches"] == 100
    assert metrics["avg_latency_ms"] == 500.0  # 50.0 * 1000 / 100
    assert metrics["most_used_strategy"] == "HYBRID"
    assert "boost_rate" in metrics
    assert metrics["boost_rate"] == 0.35  # (20 + 15) / 100
    assert "strategy_distribution" in metrics
    assert "vector_stats" in metrics
    assert "graph_stats" in metrics


@pytest.mark.asyncio
async def test_get_intent_distribution(dashboard_handler):
    """Test intent distribution retrieval."""
    distribution = await dashboard_handler.get_intent_distribution()

    assert isinstance(distribution, dict)
    assert "VECTOR_HEAVY" in distribution
    assert "GRAPH_HEAVY" in distribution
    assert "HYBRID" in distribution

    # Check percentages sum to 100
    total = sum(distribution.values())
    assert abs(total - 100.0) < 0.1  # Allow for floating point errors


@pytest.mark.asyncio
async def test_get_graph_data(dashboard_handler):
    """Test graph data retrieval."""
    # Mock Neo4j session
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(
        return_value=[
            {
                "id": "e1",
                "name": "OpenAI",
                "type": "Company",
                "relationship_count": 5,
            },
            {"id": "e2", "name": "GPT-4", "type": "Model", "relationship_count": 3},
        ]
    )

    mock_session.run = AsyncMock(return_value=mock_result)
    dashboard_handler.connection_manager.get_neo4j_session = MagicMock(return_value=mock_session)

    graph_data = await dashboard_handler.get_graph_data(limit=10)

    assert "entities" in graph_data
    assert "relationships" in graph_data
    assert len(graph_data["entities"]) > 0


@pytest.mark.asyncio
async def test_get_top_entities(dashboard_handler):
    """Test top entities retrieval."""
    # Mock Neo4j session
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(
        return_value=[
            {
                "id": "e1",
                "name": "OpenAI",
                "type": "Company",
                "relationship_count": 10,
                "chunk_count": 5,
                "created_at": "2024-01-01",
            },
            {
                "id": "e2",
                "name": "GPT-4",
                "type": "Model",
                "relationship_count": 8,
                "chunk_count": 3,
                "created_at": "2024-01-02",
            },
        ]
    )

    mock_session.run = AsyncMock(return_value=mock_result)
    dashboard_handler.connection_manager.get_neo4j_session = MagicMock(return_value=mock_session)

    entities = await dashboard_handler.get_top_entities(limit=20)

    assert isinstance(entities, list)
    assert len(entities) == 2
    assert entities[0]["name"] == "OpenAI"
    assert entities[0]["relationship_count"] == 10


@pytest.mark.asyncio
async def test_get_entity_timeline(dashboard_handler):
    """Test entity timeline retrieval."""
    # Mock Neo4j session
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(
        return_value=[
            {
                "description": "OpenAI was founded",
                "valid_from": "2015-12-11",
                "valid_to": None,
                "created_at": "2024-01-01",
            },
            {
                "description": "GPT-3 was released",
                "valid_from": "2020-06-11",
                "valid_to": None,
                "created_at": "2024-01-02",
            },
        ]
    )

    mock_session.run = AsyncMock(return_value=mock_result)
    dashboard_handler.connection_manager.get_neo4j_session = MagicMock(return_value=mock_session)

    timeline = await dashboard_handler.get_entity_timeline("e1")

    assert isinstance(timeline, list)
    assert len(timeline) == 2
    assert timeline[0]["description"] == "OpenAI was founded"


@pytest.mark.asyncio
async def test_get_performance_metrics(dashboard_handler):
    """Test performance metrics retrieval."""
    metrics = await dashboard_handler.get_performance_metrics()

    assert "vector_latency_ms" in metrics
    assert "graph_latency_ms" in metrics
    assert "cache_hit_rate" in metrics
    assert "db_connections_active" in metrics
    assert "db_connections_idle" in metrics
    assert "pg_metrics" in metrics
    assert "neo4j_metrics" in metrics

    # Check calculated values
    assert metrics["vector_latency_ms"] == 150.5
    assert metrics["graph_latency_ms"] == 250.3
    assert metrics["cache_hit_rate"] == 0.25  # 25/100
    assert metrics["db_connections_active"] == 8  # 5 + 3
    assert metrics["db_connections_idle"] == 5  # 3 + 2


@pytest.mark.asyncio
async def test_cache_functionality(dashboard_handler):
    """Test caching of expensive queries."""
    # First call - should execute
    metrics1 = await dashboard_handler.get_search_metrics()

    # Second call - should use cache
    metrics2 = await dashboard_handler.get_search_metrics()

    assert metrics1 == metrics2

    # Clear cache
    dashboard_handler.clear_cache()

    # Third call - should execute again
    metrics3 = await dashboard_handler.get_search_metrics()
    assert metrics3 == metrics1  # Same data, but freshly fetched


# Test Dashboard Utils


def test_generate_entity_cypher_basic():
    """Test basic entity Cypher query generation."""
    query = generate_entity_cypher(limit=50)

    assert "MATCH (e:Entity)" in query
    assert "LIMIT 50" in query
    assert "rel_count" in query


def test_generate_entity_cypher_with_filters():
    """Test entity Cypher query with filters."""
    filters = {
        "entity_types": ["Company", "Person"],
        "min_relationships": 5,
        "search_term": "OpenAI",
    }

    query = generate_entity_cypher(filters=filters, limit=20)

    assert "MATCH (e:Entity)" in query
    assert "Company" in query
    assert "Person" in query
    assert "rel_count >= 5" in query
    assert "OpenAI" in query.lower()
    assert "LIMIT 20" in query


def test_generate_relationship_cypher():
    """Test relationship Cypher query generation."""
    entity_ids = ["e1", "e2", "e3"]
    query = generate_relationship_cypher(entity_ids=entity_ids, limit=100)

    assert "MATCH (source:Entity)-[r]->(target:Entity)" in query
    assert "e1" in query
    assert "e2" in query
    assert "e3" in query
    assert "LIMIT 100" in query


def test_generate_top_entities_cypher():
    """Test top entities Cypher query generation."""
    query = generate_top_entities_cypher(limit=20)

    assert "MATCH (e:Entity)" in query
    assert "relationship_count" in query
    assert "ORDER BY relationship_count DESC" in query
    assert "LIMIT 20" in query


def test_format_graph_for_plotly():
    """Test graph data formatting for plotly."""
    entities = [
        {"id": "1", "name": "OpenAI", "type": "Company", "relationship_count": 5},
        {"id": "2", "name": "GPT-4", "type": "Model", "relationship_count": 3},
        {"id": "3", "name": "Sam Altman", "type": "Person", "relationship_count": 4},
    ]

    relationships = [
        {"source_id": "1", "target_id": "2", "relationship_type": "DEVELOPED"},
        {"source_id": "3", "target_id": "1", "relationship_type": "LEADS"},
    ]

    result = format_graph_for_plotly(entities, relationships)

    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) == 3
    assert len(result["edges"]) == 2

    # Check node structure
    assert result["nodes"][0]["id"] == "1"
    assert result["nodes"][0]["name"] == "OpenAI"
    assert result["nodes"][0]["type"] == "Company"

    # Check edge structure
    assert result["edges"][0]["source"] == "1"
    assert result["edges"][0]["target"] == "2"
    assert result["edges"][0]["type"] == "DEVELOPED"


def test_format_graph_filters_invalid_edges():
    """Test that graph formatting filters edges with missing nodes."""
    entities = [
        {"id": "1", "name": "OpenAI", "type": "Company"},
    ]

    relationships = [
        {
            "source_id": "1",
            "target_id": "999",
            "relationship_type": "INVALID",
        },  # Target doesn't exist
        {"source_id": "1", "target_id": "1", "relationship_type": "SELF"},  # Valid
    ]

    result = format_graph_for_plotly(entities, relationships)

    # Should only include the self-referencing edge
    assert len(result["edges"]) == 1
    assert result["edges"][0]["source"] == "1"
    assert result["edges"][0]["target"] == "1"


def test_aggregate_time_series_empty():
    """Test time series aggregation with empty data."""
    result = aggregate_time_series([])

    assert result.empty
    assert "timestamp" in result.columns


def test_aggregate_time_series_with_data():
    """Test time series aggregation with real data."""
    from datetime import datetime, timedelta

    now = datetime.now()
    stats = [
        {
            "timestamp": now - timedelta(hours=i),
            "search_count": 10 + i,
            "avg_latency_ms": 100 + i * 5,
        }
        for i in range(24)
    ]

    result = aggregate_time_series(stats, time_window="24h")

    assert not result.empty
    assert "timestamp" in result.columns
    assert "search_count" in result.columns
    assert len(result) > 0


def test_calculate_graph_statistics():
    """Test graph statistics calculation."""
    entities = [
        {"id": "1", "name": "OpenAI", "type": "Company"},
        {"id": "2", "name": "GPT-4", "type": "Model"},
        {"id": "3", "name": "Sam Altman", "type": "Person"},
    ]

    relationships = [
        {"source_id": "1", "target_id": "2", "relationship_type": "DEVELOPED"},
        {"source_id": "3", "target_id": "1", "relationship_type": "LEADS"},
        {"source_id": "1", "target_id": "3", "relationship_type": "EMPLOYS"},
    ]

    stats = calculate_graph_statistics(entities, relationships)

    assert stats["total_entities"] == 3
    assert stats["total_relationships"] == 3
    assert stats["entity_types"]["Company"] == 1
    assert stats["entity_types"]["Model"] == 1
    assert stats["entity_types"]["Person"] == 1
    assert stats["relationship_types"]["DEVELOPED"] == 1
    assert stats["relationship_types"]["LEADS"] == 1
    assert stats["relationship_types"]["EMPLOYS"] == 1
    assert stats["avg_relationships_per_entity"] == 1.0  # 3 relationships / 3 entities


def test_calculate_graph_statistics_empty():
    """Test graph statistics with empty data."""
    stats = calculate_graph_statistics([], [])

    assert stats["total_entities"] == 0
    assert stats["total_relationships"] == 0
    assert stats["avg_relationships_per_entity"] == 0


# Integration Tests


@pytest.mark.asyncio
async def test_dashboard_handler_error_handling(mock_connection_manager):
    """Test dashboard handler gracefully handles errors."""
    handler = DashboardHandler(mock_connection_manager)

    # Mock search components to raise errors
    handler.hybrid_search.get_stats = MagicMock(side_effect=Exception("Test error"))

    # Should not raise, but return default values
    metrics = await handler.get_search_metrics()

    assert "error" in metrics
    assert metrics["total_searches"] == 0


@pytest.mark.asyncio
async def test_dashboard_handler_neo4j_unavailable(mock_connection_manager):
    """Test dashboard handler when Neo4j is unavailable."""
    handler = DashboardHandler(mock_connection_manager)

    # Mock Neo4j session to raise connection error
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(side_effect=Exception("Connection failed"))
    handler.connection_manager.get_neo4j_session = MagicMock(return_value=mock_session)

    # Should not raise, but return empty data
    graph_data = await handler.get_graph_data()

    assert "error" in graph_data
    assert graph_data["entities"] == []
    assert graph_data["relationships"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
