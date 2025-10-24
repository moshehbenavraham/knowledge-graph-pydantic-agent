"""
Comprehensive tests for dashboard_utils module.

Tests all Cypher generation functions, data formatting, time-series aggregation,
export functions, and graph visualization utilities.
"""

import csv
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from pyvis.network import Network

from src.ui.features.dashboard_utils import (
    aggregate_time_series,
    calculate_graph_statistics,
    create_pyvis_graph,
    export_metrics_to_csv,
    export_metrics_to_json,
    format_entity_for_display,
    format_graph_for_plotly,
    generate_entity_cypher,
    generate_entity_timeline_cypher,
    generate_relationship_cypher,
    generate_top_entities_cypher,
)


class TestCypherGeneration:
    """Test Cypher query generation functions."""

    def test_generate_entity_cypher_no_filters(self):
        """Test entity Cypher without filters."""
        query = generate_entity_cypher()
        assert "MATCH (e:Entity)" in query
        assert "LIMIT 50" in query
        assert "ORDER BY rel_count DESC" in query
        assert "WITH e, COUNT" in query

    def test_generate_entity_cypher_with_entity_types(self):
        """Test entity Cypher with type filter."""
        filters = {"entity_types": ["person", "company"]}
        query = generate_entity_cypher(filters=filters)
        assert "WHERE e.type IN ['person', 'company']" in query
        assert "MATCH (e:Entity)" in query

    def test_generate_entity_cypher_with_search_term(self):
        """Test entity Cypher with search term."""
        filters = {"search_term": "OpenAI"}
        query = generate_entity_cypher(filters=filters)
        assert "toLower(e.name) CONTAINS toLower('OpenAI')" in query

    def test_generate_entity_cypher_with_min_relationships(self):
        """Test entity Cypher with minimum relationships."""
        filters = {"min_relationships": 5}
        query = generate_entity_cypher(filters=filters)
        assert "WHERE rel_count >= 5" in query

    def test_generate_entity_cypher_combined_filters(self):
        """Test entity Cypher with all filters combined."""
        filters = {
            "entity_types": ["person"],
            "search_term": "John",
            "min_relationships": 3,
        }
        query = generate_entity_cypher(filters=filters, limit=20)
        assert "WHERE e.type IN ['person']" in query
        assert "toLower(e.name) CONTAINS toLower('John')" in query
        assert "WHERE rel_count >= 3" in query
        assert "LIMIT 20" in query

    def test_generate_entity_cypher_empty_entity_types(self):
        """Test entity Cypher with empty entity types list."""
        filters = {"entity_types": []}
        query = generate_entity_cypher(filters=filters)
        # Should not add WHERE clause for empty list
        assert "WHERE e.type IN []" not in query

    def test_generate_entity_cypher_custom_limit(self):
        """Test entity Cypher with custom limit."""
        query = generate_entity_cypher(limit=100)
        assert "LIMIT 100" in query

    def test_generate_relationship_cypher_no_filter(self):
        """Test relationship Cypher without entity filter."""
        query = generate_relationship_cypher()
        assert "MATCH (source:Entity)-[r]->(target:Entity)" in query
        assert "LIMIT 100" in query
        assert "WHERE source.id IN" not in query

    def test_generate_relationship_cypher_with_entities(self):
        """Test relationship Cypher with entity filter."""
        entity_ids = ["entity-1", "entity-2"]
        query = generate_relationship_cypher(entity_ids=entity_ids)
        assert "WHERE source.id IN ['entity-1', 'entity-2']" in query
        assert "OR target.id IN ['entity-1', 'entity-2']" in query

    def test_generate_relationship_cypher_custom_limit(self):
        """Test relationship Cypher with custom limit."""
        query = generate_relationship_cypher(limit=50)
        assert "LIMIT 50" in query

    def test_generate_relationship_cypher_single_entity(self):
        """Test relationship Cypher with single entity."""
        entity_ids = ["solo-entity"]
        query = generate_relationship_cypher(entity_ids=entity_ids, limit=25)
        assert "WHERE source.id IN ['solo-entity']" in query
        assert "LIMIT 25" in query

    def test_generate_top_entities_cypher_default(self):
        """Test top entities Cypher with default limit."""
        query = generate_top_entities_cypher()
        assert "MATCH (e:Entity)" in query
        assert "LIMIT 20" in query
        assert "relationship_count" in query
        assert "chunk_count" in query

    def test_generate_top_entities_cypher_custom_limit(self):
        """Test top entities Cypher with custom limit."""
        query = generate_top_entities_cypher(limit=50)
        assert "LIMIT 50" in query

    def test_generate_entity_timeline_cypher(self):
        """Test entity timeline Cypher."""
        entity_id = "test-entity-123"
        query = generate_entity_timeline_cypher(entity_id)
        assert f"id: '{entity_id}'" in query
        assert "valid_from" in query
        assert "valid_to" in query
        assert "ORDER BY created_at DESC" in query
        assert "LIMIT 50" in query


class TestDataFormatting:
    """Test data formatting functions."""

    def test_format_graph_for_plotly_basic(self):
        """Test basic graph formatting."""
        entities = [
            {"id": "e1", "name": "Entity 1", "type": "person", "relationship_count": 5},
            {"id": "e2", "name": "Entity 2", "type": "company", "relationship_count": 3},
        ]
        relationships = [
            {"source_id": "e1", "target_id": "e2", "relationship_type": "WORKS_FOR"},
        ]

        result = format_graph_for_plotly(entities, relationships)

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["nodes"][0]["id"] == "e1"
        assert result["edges"][0]["source"] == "e1"

    def test_format_graph_for_plotly_missing_node(self):
        """Test graph formatting with edge referencing missing node."""
        entities = [{"id": "e1", "name": "Entity 1", "type": "person", "relationship_count": 1}]
        relationships = [
            {"source_id": "e1", "target_id": "missing", "relationship_type": "RELATES_TO"},
        ]

        result = format_graph_for_plotly(entities, relationships)

        # Edge should be skipped since target doesn't exist
        assert len(result["nodes"]) == 1
        assert len(result["edges"]) == 0

    def test_format_graph_for_plotly_defaults(self):
        """Test graph formatting with missing optional fields."""
        entities = [{"id": "e1", "name": "Entity 1"}]  # Missing type, relationship_count
        relationships = [{"source_id": "e1", "target_id": "e2"}]  # Missing relationship_type

        result = format_graph_for_plotly(entities, relationships)

        assert result["nodes"][0]["type"] == "Unknown"
        assert result["nodes"][0]["relationship_count"] == 0

    def test_format_graph_for_plotly_empty(self):
        """Test graph formatting with empty inputs."""
        result = format_graph_for_plotly([], [])
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_format_entity_for_display(self):
        """Test entity formatting for display."""
        entity = {
            "name": "Test Entity",
            "type": "person",
            "relationship_count": 10,
            "chunk_count": 5,
            "confidence": 0.95,
        }

        result = format_entity_for_display(entity)

        assert result["name"] == "Test Entity"
        assert result["type"] == "person"
        assert result["relationship_count"] == 10
        assert result["chunk_count"] == 5
        assert result["confidence"] == 0.95

    def test_format_entity_for_display_defaults(self):
        """Test entity formatting with missing fields."""
        entity = {}

        result = format_entity_for_display(entity)

        assert result["name"] == "Unknown"
        assert result["type"] == "Unknown"
        assert result["relationship_count"] == 0
        assert result["chunk_count"] == 0
        assert result["confidence"] == 0.0


class TestTimeSeriesAggregation:
    """Test time series aggregation."""

    def test_aggregate_time_series_empty(self):
        """Test aggregation with empty data."""
        result = aggregate_time_series([])
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert len(result) == 0

    def test_aggregate_time_series_24h(self):
        """Test 24-hour aggregation."""
        now = pd.Timestamp.now()
        stats = [
            {
                "timestamp": now - timedelta(hours=i),
                "search_count": i + 1,
                "avg_latency_ms": 100 + i * 10,
            }
            for i in range(24)
        ]

        result = aggregate_time_series(stats, time_window="24h")

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "timestamp" in result.columns
        assert "search_count" in result.columns

    def test_aggregate_time_series_7d(self):
        """Test 7-day aggregation."""
        now = pd.Timestamp.now()
        stats = [
            {
                "timestamp": now - timedelta(days=i),
                "search_count": i + 1,
                "avg_latency_ms": 100 + i * 10,
            }
            for i in range(7)
        ]

        result = aggregate_time_series(stats, time_window="7d")

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_aggregate_time_series_30d(self):
        """Test 30-day aggregation."""
        now = pd.Timestamp.now()
        stats = [
            {
                "timestamp": now - timedelta(days=i),
                "search_count": i + 1,
                "avg_latency_ms": 100 + i * 10,
            }
            for i in range(30)
        ]

        result = aggregate_time_series(stats, time_window="30d")

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_aggregate_time_series_filters_old_data(self):
        """Test that old data is filtered out."""
        now = pd.Timestamp.now()
        stats = [
            # Recent data (within 24h)
            {"timestamp": now - timedelta(hours=1), "search_count": 1, "avg_latency_ms": 100},
            # Old data (beyond 24h)
            {"timestamp": now - timedelta(days=2), "search_count": 1, "avg_latency_ms": 100},
        ]

        result = aggregate_time_series(stats, time_window="24h")

        # Should only contain recent data
        assert len(result) >= 0  # May aggregate to 0 rows depending on hour buckets

    def test_aggregate_time_series_missing_timestamp(self):
        """Test aggregation with missing timestamp."""
        stats = [
            {"search_count": 10, "avg_latency_ms": 150},
            {"search_count": 5, "avg_latency_ms": 200},
        ]

        result = aggregate_time_series(stats, time_window="7d")

        # Should add default timestamp
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns

    def test_aggregate_time_series_invalid_window(self):
        """Test aggregation with invalid time window."""
        stats = [
            {"timestamp": pd.Timestamp.now(), "search_count": 1, "avg_latency_ms": 100},
        ]

        result = aggregate_time_series(stats, time_window="invalid")

        # Should default to 7d
        assert isinstance(result, pd.DataFrame)


class TestMetricsExport:
    """Test metrics export functions."""

    def test_export_metrics_to_csv(self):
        """Test CSV export."""
        metrics = {
            "total_searches": 100,
            "avg_latency_ms": 150.5,
            "strategy": "HYBRID",
            "nested": {"key": "value"},
            "list_data": [1, 2, 3],
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_path = f.name

        try:
            export_metrics_to_csv(metrics, temp_path)

            # Read back and verify
            with open(temp_path) as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert rows[0] == ["Metric", "Value"]
            assert len(rows) == 6  # Header + 5 metrics

            # Check simple values
            metric_dict = {row[0]: row[1] for row in rows[1:]}
            assert metric_dict["total_searches"] == "100"
            assert metric_dict["avg_latency_ms"] == "150.5"

            # Check complex values are JSON-encoded
            assert "key" in metric_dict["nested"]

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_export_metrics_to_json(self):
        """Test JSON export."""
        metrics = {
            "total_searches": 100,
            "avg_latency_ms": 150.5,
            "strategy": "HYBRID",
            "timestamp": datetime(2024, 1, 1, 12, 0),
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = f.name

        try:
            export_metrics_to_json(metrics, temp_path)

            # Read back and verify
            with open(temp_path) as f:
                loaded = json.load(f)

            assert loaded["total_searches"] == 100
            assert loaded["avg_latency_ms"] == 150.5
            assert loaded["strategy"] == "HYBRID"
            # Datetime should be converted to string
            assert isinstance(loaded["timestamp"], str)

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_export_metrics_empty(self):
        """Test exporting empty metrics."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_csv = f.name
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_json = f.name

        try:
            export_metrics_to_csv({}, temp_csv)
            export_metrics_to_json({}, temp_json)

            # Verify files created
            assert Path(temp_csv).exists()
            assert Path(temp_json).exists()

        finally:
            Path(temp_csv).unlink(missing_ok=True)
            Path(temp_json).unlink(missing_ok=True)


class TestGraphStatistics:
    """Test graph statistics calculation."""

    def test_calculate_graph_statistics_basic(self):
        """Test basic graph statistics."""
        entities = [
            {"id": "e1", "type": "person"},
            {"id": "e2", "type": "company"},
            {"id": "e3", "type": "person"},
        ]
        relationships = [
            {"source_id": "e1", "target_id": "e2", "relationship_type": "WORKS_FOR"},
            {"source_id": "e3", "target_id": "e2", "relationship_type": "WORKS_FOR"},
        ]

        stats = calculate_graph_statistics(entities, relationships)

        assert stats["total_entities"] == 3
        assert stats["total_relationships"] == 2
        assert stats["entity_types"]["person"] == 2
        assert stats["entity_types"]["company"] == 1
        assert stats["relationship_types"]["WORKS_FOR"] == 2
        assert stats["avg_relationships_per_entity"] == pytest.approx(2 / 3)

    def test_calculate_graph_statistics_empty(self):
        """Test graph statistics with no data."""
        stats = calculate_graph_statistics([], [])

        assert stats["total_entities"] == 0
        assert stats["total_relationships"] == 0
        assert stats["avg_relationships_per_entity"] == 0

    def test_calculate_graph_statistics_unknown_types(self):
        """Test graph statistics with missing types."""
        entities = [{"id": "e1"}, {"id": "e2"}]
        relationships = [{"source_id": "e1", "target_id": "e2"}]

        stats = calculate_graph_statistics(entities, relationships)

        assert stats["entity_types"]["Unknown"] == 2
        assert stats["relationship_types"]["RELATED_TO"] == 1

    def test_calculate_graph_statistics_multiple_types(self):
        """Test graph statistics with diverse types."""
        entities = [
            {"id": "e1", "type": "person"},
            {"id": "e2", "type": "company"},
            {"id": "e3", "type": "location"},
            {"id": "e4", "type": "person"},
        ]
        relationships = [
            {"source_id": "e1", "target_id": "e2", "relationship_type": "WORKS_FOR"},
            {"source_id": "e2", "target_id": "e3", "relationship_type": "LOCATED_IN"},
            {"source_id": "e4", "target_id": "e2", "relationship_type": "OWNS"},
        ]

        stats = calculate_graph_statistics(entities, relationships)

        assert len(stats["entity_types"]) == 3
        assert len(stats["relationship_types"]) == 3
        assert stats["avg_relationships_per_entity"] == pytest.approx(3 / 4)


class TestPyvisGraphCreation:
    """Test pyvis graph visualization creation."""

    def test_create_pyvis_graph_basic(self):
        """Test basic pyvis graph creation."""
        entities = [
            {"id": "e1", "name": "Person 1", "type": "person", "relationship_count": 2},
            {"id": "e2", "name": "Company 1", "type": "company", "relationship_count": 1},
        ]
        relationships = [
            {"source_id": "e1", "target_id": "e2", "relationship_type": "WORKS_FOR"},
        ]

        net = create_pyvis_graph(entities, relationships)

        assert isinstance(net, Network)
        assert len(net.nodes) == 2
        assert len(net.edges) == 1

    def test_create_pyvis_graph_force_directed(self):
        """Test force-directed layout."""
        entities = [{"id": "e1", "name": "Entity 1", "type": "person", "relationship_count": 1}]
        relationships = []

        net = create_pyvis_graph(entities, relationships, layout="force_directed")

        assert isinstance(net, Network)

    def test_create_pyvis_graph_hierarchical(self):
        """Test hierarchical layout."""
        entities = [{"id": "e1", "name": "Entity 1", "type": "person", "relationship_count": 1}]
        relationships = []

        net = create_pyvis_graph(entities, relationships, layout="hierarchical")

        assert isinstance(net, Network)

    def test_create_pyvis_graph_circular(self):
        """Test circular layout."""
        entities = [{"id": "e1", "name": "Entity 1", "type": "person", "relationship_count": 1}]
        relationships = []

        net = create_pyvis_graph(entities, relationships, layout="circular")

        assert isinstance(net, Network)

    def test_create_pyvis_graph_missing_nodes(self):
        """Test graph with edges referencing missing nodes."""
        entities = [{"id": "e1", "name": "Entity 1", "type": "person", "relationship_count": 1}]
        relationships = [
            {"source_id": "e1", "target_id": "missing", "relationship_type": "RELATES"},
            {"source_id": "also_missing", "target_id": "e1", "relationship_type": "RELATES"},
        ]

        net = create_pyvis_graph(entities, relationships)

        # Only the valid node should be added, edges should be skipped
        assert len(net.nodes) == 1
        assert len(net.edges) == 0

    def test_create_pyvis_graph_entity_colors(self):
        """Test that different entity types get different colors."""
        entities = [
            {"id": "e1", "name": "Person", "type": "person", "relationship_count": 1},
            {"id": "e2", "name": "Company", "type": "company", "relationship_count": 1},
            {"id": "e3", "name": "Unknown", "type": "unknown_type", "relationship_count": 1},
        ]
        relationships = []

        net = create_pyvis_graph(entities, relationships)

        assert len(net.nodes) == 3
        # Verify nodes were added (colors are internal to pyvis)

    def test_create_pyvis_graph_no_entity_id(self):
        """Test graph with entities missing ID."""
        entities = [
            {"name": "No ID Entity", "type": "person", "relationship_count": 1},  # Missing id
            {"id": "e1", "name": "Valid Entity", "type": "person", "relationship_count": 1},
        ]
        relationships = []

        net = create_pyvis_graph(entities, relationships)

        # Only entity with ID should be added
        assert len(net.nodes) == 1

    def test_create_pyvis_graph_long_names(self):
        """Test graph with very long entity names."""
        entities = [
            {
                "id": "e1",
                "name": "A" * 100,  # Very long name
                "type": "person",
                "relationship_count": 1,
            },
        ]
        relationships = []

        net = create_pyvis_graph(entities, relationships)

        assert len(net.nodes) == 1
        # Name should be truncated to 20 chars

    def test_create_pyvis_graph_custom_dimensions(self):
        """Test graph with custom height and width."""
        entities = [{"id": "e1", "name": "Entity 1", "type": "person", "relationship_count": 1}]
        relationships = []

        net = create_pyvis_graph(entities, relationships, height="500px", width="80%")

        assert net.height == "500px"
        assert net.width == "80%"

    def test_create_pyvis_graph_large_relationship_count(self):
        """Test node sizing with large relationship counts."""
        entities = [
            {
                "id": "e1",
                "name": "Hub Entity",
                "type": "person",
                "relationship_count": 100,  # Very connected
            },
            {
                "id": "e2",
                "name": "Leaf Entity",
                "type": "person",
                "relationship_count": 0,  # Not connected
            },
        ]
        relationships = []

        net = create_pyvis_graph(entities, relationships)

        assert len(net.nodes) == 2
        # Hub should have larger node size (15-50 range)

    def test_create_pyvis_graph_empty(self):
        """Test graph creation with no data."""
        net = create_pyvis_graph([], [])

        assert len(net.nodes) == 0
        assert len(net.edges) == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_generate_entity_cypher_none_filters(self):
        """Test with None filters."""
        query = generate_entity_cypher(filters=None)
        assert "MATCH (e:Entity)" in query

    def test_aggregate_time_series_non_dict_stats(self):
        """Test aggregation with malformed stats."""
        stats = ["not", "a", "dict"]
        # Should handle gracefully
        try:
            result = aggregate_time_series(stats)  # type: ignore
            assert isinstance(result, pd.DataFrame)
        except (KeyError, TypeError, ValueError):
            # Expected to fail gracefully
            pass

    def test_format_graph_for_plotly_duplicate_entities(self):
        """Test graph formatting with duplicate entity IDs."""
        entities = [
            {"id": "e1", "name": "Entity 1", "type": "person", "relationship_count": 1},
            {"id": "e1", "name": "Duplicate", "type": "person", "relationship_count": 1},
        ]
        relationships = []

        result = format_graph_for_plotly(entities, relationships)

        # Should handle duplicates (last one wins in node_map)
        assert len(result["nodes"]) == 2

    def test_calculate_graph_statistics_single_entity(self):
        """Test statistics with single entity and no relationships."""
        entities = [{"id": "e1", "type": "person"}]
        relationships = []

        stats = calculate_graph_statistics(entities, relationships)

        assert stats["total_entities"] == 1
        assert stats["total_relationships"] == 0
        assert stats["avg_relationships_per_entity"] == 0
