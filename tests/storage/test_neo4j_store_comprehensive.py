"""
Comprehensive tests for Neo4jStore - lightweight entity and relationship management.

Covers:
- Entity creation and management
- Relationship creation between entities
- Episode/fact creation with temporal data
- Entity search (exact and fuzzy)
- Relationship traversal
- Episode search with filters
- Entity timeline queries
- Path finding between entities
- Graph statistics
- Importance score calculation
- Cleanup operations
- Custom Cypher queries
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from src.agentic_rag.storage.neo4j_store import Neo4jStore


# ===== Fixtures =====


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager."""
    cm = Mock()
    return cm


@pytest.fixture
def neo4j_store(mock_connection_manager):
    """Create Neo4jStore instance."""
    return Neo4jStore(mock_connection_manager)


@pytest.fixture
def mock_session():
    """Mock Neo4j session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_result():
    """Mock Neo4j query result."""
    result = AsyncMock()
    return result


# ===== Entity Tests =====


@pytest.mark.asyncio
class TestAddEntities:
    """Test entity creation and management."""

    async def test_add_single_entity(self, neo4j_store, mock_session, mock_result):
        """Test adding a single entity."""
        entities = [{"name": "OpenAI", "type": "Organization"}]
        source_chunk_id = "chunk_123"

        mock_record = {"entity_id": "entity_abc"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        entity_ids = await neo4j_store.add_entities(entities, source_chunk_id)

        assert len(entity_ids) == 1
        assert entity_ids[0] == "entity_abc"
        mock_session.run.assert_called_once()

    async def test_add_multiple_entities(self, neo4j_store, mock_session, mock_result):
        """Test adding multiple entities."""
        entities = [
            {"name": "OpenAI", "type": "Organization"},
            {"name": "GPT-4", "type": "Product"},
            {"name": "Sam Altman", "type": "Person"},
        ]
        source_chunk_id = "chunk_123"

        mock_result.single.side_effect = [
            {"entity_id": f"entity_{i}"} for i in range(len(entities))
        ]
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        entity_ids = await neo4j_store.add_entities(entities, source_chunk_id)

        assert len(entity_ids) == 3
        assert mock_session.run.call_count == 3

    async def test_add_entities_creates_or_merges(self, neo4j_store, mock_session, mock_result):
        """Test that entities use MERGE (create or update)."""
        entities = [{"name": "OpenAI", "type": "Organization"}]
        source_chunk_id = "chunk_123"

        mock_record = {"entity_id": "entity_abc"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.add_entities(entities, source_chunk_id)

        # Verify MERGE query was used
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "MERGE" in query
        assert "ON CREATE SET" in query
        assert "ON MATCH SET" in query


# ===== Relationship Tests =====


@pytest.mark.asyncio
class TestAddRelationships:
    """Test relationship creation."""

    async def test_add_relationship_with_source_target(
        self, neo4j_store, mock_session, mock_result
    ):
        """Test adding relationship using source/target format."""
        relationships = [
            {
                "source": "OpenAI",
                "target": "GPT-4",
                "type": "CREATED",
                "confidence": 0.9,
            }
        ]
        source_chunk_id = "chunk_123"

        mock_record = {"rel_id": "rel_abc"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        count = await neo4j_store.add_relationships(relationships, source_chunk_id)

        assert count == 1
        # Two calls: one for relationship, one for updating entity counts
        assert mock_session.run.call_count == 2

    async def test_add_relationship_with_entity_ids(
        self, neo4j_store, mock_session, mock_result
    ):
        """Test adding relationship using entity1_id/entity2_id format."""
        relationships = [
            {
                "entity1_id": "OpenAI",
                "entity2_id": "GPT-4",
                "type": "CREATED",
            }
        ]
        source_chunk_id = "chunk_123"

        mock_record = {"rel_id": "rel_abc"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        count = await neo4j_store.add_relationships(relationships, source_chunk_id)

        assert count == 1

    async def test_add_relationship_skips_missing_entities(
        self, neo4j_store, mock_session, mock_result
    ):
        """Test that relationships with missing entity names are skipped."""
        relationships = [
            {"source": "OpenAI", "target": None, "type": "CREATED"},  # Missing target
            {"source": None, "target": "GPT-4", "type": "USES"},  # Missing source
        ]
        source_chunk_id = "chunk_123"

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        count = await neo4j_store.add_relationships(relationships, source_chunk_id)

        assert count == 0
        mock_session.run.assert_not_called()

    async def test_add_multiple_relationships(self, neo4j_store, mock_session, mock_result):
        """Test adding multiple relationships."""
        relationships = [
            {"source": "OpenAI", "target": "GPT-4", "type": "CREATED"},
            {"source": "Sam Altman", "target": "OpenAI", "type": "LEADS"},
        ]
        source_chunk_id = "chunk_123"

        mock_record = {"rel_id": "rel_abc"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        count = await neo4j_store.add_relationships(relationships, source_chunk_id)

        assert count == 2
        # 2 relationships + 2 entity count updates = 4 calls
        assert mock_session.run.call_count == 4


# ===== Episode Tests =====


@pytest.mark.asyncio
class TestAddEpisodes:
    """Test temporal fact/episode creation."""

    async def test_add_single_episode(self, neo4j_store, mock_session, mock_result):
        """Test adding a single episode."""
        facts = ["OpenAI released GPT-4 in March 2023"]
        entity_names = ["OpenAI", "GPT-4"]
        source_chunk_id = "chunk_123"
        source_document_id = "doc_456"

        mock_record = {"episode_id": "episode_abc"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        episode_ids = await neo4j_store.add_episodes(
            facts, entity_names, source_chunk_id, source_document_id
        )

        assert len(episode_ids) == 1
        assert episode_ids[0] == "episode_abc"
        # One call for episode + one call for linking entities
        assert mock_session.run.call_count == 2

    async def test_add_episode_truncates_long_facts(self, neo4j_store, mock_session, mock_result):
        """Test that long facts are truncated to 500 chars."""
        long_fact = "x" * 600  # 600 chars
        facts = [long_fact]
        entity_names = ["Entity1"]
        source_chunk_id = "chunk_123"
        source_document_id = "doc_456"

        mock_record = {"episode_id": "episode_abc"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.add_episodes(facts, entity_names, source_chunk_id, source_document_id)

        # Verify fact was truncated
        call_args = mock_session.run.call_args_list[0]
        params = call_args[1]
        assert len(params["fact"]) == 500
        assert params["fact"].endswith("...")

    async def test_add_episode_without_entities(self, neo4j_store, mock_session, mock_result):
        """Test adding episode without entity links."""
        facts = ["Some generic fact"]
        entity_names = []
        source_chunk_id = "chunk_123"
        source_document_id = "doc_456"

        mock_record = {"episode_id": "episode_abc"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        episode_ids = await neo4j_store.add_episodes(
            facts, entity_names, source_chunk_id, source_document_id
        )

        assert len(episode_ids) == 1
        # Only one call (no entity linking)
        assert mock_session.run.call_count == 1


# ===== Search Tests =====


@pytest.mark.asyncio
class TestSearchEntities:
    """Test entity search functionality."""

    async def test_search_entities_exact_match(self, neo4j_store, mock_session, mock_result):
        """Test entity search with exact match."""
        query = "OpenAI"
        limit = 10

        mock_records = [
            {"e": {"name": "OpenAI", "type": "Organization", "importance_score": 0.8}}
        ]

        async def mock_async_iter():
            for record in mock_records:
                yield record

        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        entities = await neo4j_store.search_entities(query, limit)

        assert len(entities) == 1
        assert entities[0]["name"] == "OpenAI"

    async def test_search_entities_fuzzy_fallback(self, neo4j_store, mock_session):
        """Test entity search falls back to fuzzy search."""
        query = "OpnAI"  # Typo
        limit = 10

        # First call returns empty (exact match fails)
        mock_result_empty = AsyncMock()

        async def mock_empty_iter():
            return
            yield  # Empty generator

        mock_result_empty.__aiter__ = mock_empty_iter

        # Second call returns fuzzy results
        mock_result_fuzzy = AsyncMock()
        mock_records = [
            {"e": {"name": "OpenAI", "type": "Organization"}, "score": 0.95}
        ]

        async def mock_fuzzy_iter():
            for record in mock_records:
                yield record

        mock_result_fuzzy.__aiter__ = mock_fuzzy_iter

        mock_session.run.side_effect = [mock_result_empty, mock_result_fuzzy]

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        entities = await neo4j_store.search_entities(query, limit)

        assert len(entities) == 1
        assert entities[0]["name"] == "OpenAI"
        assert entities[0]["search_score"] == 0.95
        # Two calls: exact match + fuzzy search
        assert mock_session.run.call_count == 2


# ===== Relationship Traversal Tests =====


@pytest.mark.asyncio
class TestGetEntityRelationships:
    """Test entity relationship retrieval."""

    async def test_get_entity_relationships(self, neo4j_store, mock_session, mock_result):
        """Test getting relationships for an entity."""
        entity_id = "entity_123"
        depth = 1

        mock_record = {
            "e": {"id": entity_id, "name": "OpenAI"},
            "relationships": [{"type": "CREATED", "confidence": 0.9}],
            "related_entities": [{"id": "entity_456", "name": "GPT-4"}],
        }
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        result = await neo4j_store.get_entity_relationships(entity_id, depth)

        assert result["entity"]["id"] == entity_id
        assert len(result["relationships"]) == 1
        assert len(result["related_entities"]) == 1

    async def test_get_entity_relationships_not_found(
        self, neo4j_store, mock_session, mock_result
    ):
        """Test getting relationships for non-existent entity."""
        entity_id = "entity_999"

        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        result = await neo4j_store.get_entity_relationships(entity_id, 1)

        assert result is None

    async def test_get_entity_relationships_caps_depth(
        self, neo4j_store, mock_session, mock_result
    ):
        """Test that depth is capped at 3."""
        entity_id = "entity_123"
        depth = 10  # Request large depth

        mock_result.single.return_value = {
            "e": {},
            "relationships": [],
            "related_entities": [],
        }
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.get_entity_relationships(entity_id, depth)

        # Verify depth parameter was capped at 3
        call_args = mock_session.run.call_args
        params = call_args[1]
        assert params["depth"] == 3


# ===== Episode Search Tests =====


@pytest.mark.asyncio
class TestSearchEpisodes:
    """Test episode/fact search."""

    async def test_search_episodes_basic(self, neo4j_store, mock_session, mock_result):
        """Test basic episode search."""
        query = "GPT-4 release"
        limit = 20

        mock_records = [
            {
                "ep": {"fact": "GPT-4 was released in March 2023", "timestamp": datetime.now()},
                "score": 0.9,
            }
        ]

        async def mock_async_iter():
            for record in mock_records:
                yield record

        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        episodes = await neo4j_store.search_episodes(query, limit=limit)

        assert len(episodes) == 1
        assert episodes[0]["search_score"] == 0.9

    async def test_search_episodes_with_entity_filter(
        self, neo4j_store, mock_session, mock_result
    ):
        """Test episode search filtered by entities."""
        query = "release"
        entity_ids = ["entity_123", "entity_456"]
        limit = 20

        async def mock_async_iter():
            return
            yield

        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.search_episodes(query, entity_ids=entity_ids, limit=limit)

        # Verify entity filter was applied
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        assert params["entity_ids"] == entity_ids

    async def test_search_episodes_with_time_range(self, neo4j_store, mock_session, mock_result):
        """Test episode search with time range filter."""
        query = "release"
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 12, 31)
        time_range = (start_time, end_time)

        async def mock_async_iter():
            return
            yield

        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.search_episodes(query, time_range=time_range)

        # Verify time range filter was applied
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        assert params["start_time"] == start_time
        assert params["end_time"] == end_time


# ===== Timeline Tests =====


@pytest.mark.asyncio
class TestGetEntityTimeline:
    """Test entity timeline retrieval."""

    async def test_get_entity_timeline(self, neo4j_store, mock_session, mock_result):
        """Test getting timeline for an entity."""
        entity_id = "entity_123"
        limit = 50

        mock_records = [
            {"ep": {"fact": "Event 1", "timestamp": datetime(2023, 1, 1)}},
            {"ep": {"fact": "Event 2", "timestamp": datetime(2023, 2, 1)}},
        ]

        async def mock_async_iter():
            for record in mock_records:
                yield record

        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        timeline = await neo4j_store.get_entity_timeline(entity_id, limit)

        assert len(timeline) == 2
        assert timeline[0]["fact"] == "Event 1"


# ===== Graph Operations Tests =====


@pytest.mark.asyncio
class TestGraphOperations:
    """Test graph-wide operations."""

    async def test_update_entity_importance(self, neo4j_store, mock_session):
        """Test updating entity importance score."""
        entity_id = "entity_123"

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.update_entity_importance(entity_id)

        mock_session.run.assert_called_once()
        # Verify importance calculation is in query
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "importance_score" in query

    async def test_find_paths_between_entities(self, neo4j_store, mock_session, mock_result):
        """Test finding paths between two entities."""
        entity1_id = "entity_123"
        entity2_id = "entity_456"
        max_depth = 3

        # Mock path object
        mock_path = Mock()
        mock_path.nodes = [
            {"id": entity1_id, "name": "Entity1"},
            {"id": "entity_789", "name": "Entity3"},
            {"id": entity2_id, "name": "Entity2"},
        ]
        mock_path.relationships = [
            {"type": "RELATED_TO"},
            {"type": "CONNECTED_TO"},
        ]

        mock_records = [{"path": mock_path}]

        async def mock_async_iter():
            for record in mock_records:
                yield record

        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        paths = await neo4j_store.find_paths(entity1_id, entity2_id, max_depth)

        assert len(paths) == 1
        assert paths[0]["length"] == 2
        assert len(paths[0]["nodes"]) == 3

    async def test_get_graph_statistics(self, neo4j_store, mock_session, mock_result):
        """Test getting graph statistics."""
        # Mock count queries
        mock_results = [
            Mock(single=AsyncMock(return_value={"count": 100})),  # Entities
            Mock(single=AsyncMock(return_value={"count": 50})),  # Episodes
            Mock(single=AsyncMock(return_value={"count": 10})),  # Concepts
            Mock(single=AsyncMock(return_value={"count": 5})),  # Events
            Mock(single=AsyncMock(return_value={"count": 75})),  # Relationships
        ]

        # Mock top entities query
        top_entities_result = AsyncMock()
        top_entities_records = [
            {"name": "Entity1", "type": "Organization", "score": 0.9},
            {"name": "Entity2", "type": "Product", "score": 0.8},
        ]

        async def mock_top_entities_iter():
            for record in top_entities_records:
                yield record

        top_entities_result.__aiter__ = mock_top_entities_iter
        mock_results.append(top_entities_result)

        mock_session.run.side_effect = mock_results

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        stats = await neo4j_store.get_graph_statistics()

        assert stats["entity_count"] == 100
        assert stats["episode_count"] == 50
        assert stats["relationship_count"] == 75
        assert len(stats["top_entities"]) == 2
        assert "graph_density" in stats

    async def test_cleanup_orphaned_entities(self, neo4j_store, mock_session, mock_result):
        """Test cleanup of orphaned entities."""
        mock_record = {"deleted_count": 5}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.cleanup_orphaned_entities()

        mock_session.run.assert_called_once()
        # Verify DELETE query
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        assert "DELETE" in query

    async def test_cleanup_no_orphans(self, neo4j_store, mock_session, mock_result):
        """Test cleanup when no orphans exist."""
        mock_record = {"deleted_count": 0}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.cleanup_orphaned_entities()

        mock_session.run.assert_called_once()


# ===== Custom Query Tests =====


@pytest.mark.asyncio
class TestExecuteQuery:
    """Test custom Cypher query execution."""

    async def test_execute_query_basic(self, neo4j_store, mock_session, mock_result):
        """Test executing a basic Cypher query."""
        cypher = "MATCH (n:Entity) RETURN n.name as name LIMIT 5"
        parameters = {}

        mock_records = [
            {"name": "Entity1"},
            {"name": "Entity2"},
        ]

        async def mock_async_iter():
            for record in mock_records:
                yield record

        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        results = await neo4j_store.execute_query(cypher, parameters)

        assert len(results) == 2
        assert results[0]["name"] == "Entity1"
        mock_session.run.assert_called_once_with(cypher, parameters)

    async def test_execute_query_with_parameters(self, neo4j_store, mock_session, mock_result):
        """Test executing query with parameters."""
        cypher = "MATCH (n:Entity {name: $name}) RETURN n"
        parameters = {"name": "OpenAI"}

        async def mock_async_iter():
            return
            yield

        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.execute_query(cypher, parameters)

        mock_session.run.assert_called_once_with(cypher, parameters)

    async def test_execute_query_none_parameters(self, neo4j_store, mock_session, mock_result):
        """Test executing query with None parameters."""
        cypher = "RETURN 1"

        async def mock_async_iter():
            return
            yield

        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result

        neo4j_store.connection_manager.get_neo4j_session.return_value.__aenter__.return_value = (
            mock_session
        )
        neo4j_store.connection_manager.get_neo4j_session.return_value.__aexit__.return_value = (
            AsyncMock(return_value=False)
        )

        await neo4j_store.execute_query(cypher, None)

        # Should pass empty dict if parameters are None
        mock_session.run.assert_called_once_with(cypher, {})
