"""
Comprehensive tests for Neo4jStore.

Covers all methods including add_entities, add_relationships, add_episodes,
execute_query, search_entities, get_entity_relationships, search_episodes,
get_entity_timeline, update_entity_importance, find_paths, get_graph_statistics,
and cleanup_orphaned_entities.

Target: Increase coverage from 35% to 90%+ (cover 91 uncovered lines).
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.agentic_rag.storage.neo4j_store import Neo4jStore


@pytest.fixture
def mock_connection_manager():
    """Mock ConnectionManager with Neo4j session support."""
    mock_manager = Mock()

    # Create mock session
    mock_session = AsyncMock()

    # Create async context manager for get_neo4j_session
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    mock_manager.get_neo4j_session.return_value = mock_context

    return mock_manager


@pytest.fixture
def neo4j_store(mock_connection_manager):
    """Create Neo4jStore instance with mocked connection."""
    return Neo4jStore(mock_connection_manager)


# =====================================================
# ADD ENTITIES TESTS
# =====================================================


@pytest.mark.asyncio
async def test_add_entities_success(neo4j_store, mock_connection_manager):
    """Test adding entities successfully."""
    entities = [
        {"name": "Alice", "type": "Person"},
        {"name": "Bob", "type": "Person"},
        {"name": "Acme Corp", "type": "Organization"},
    ]
    chunk_id = "chunk_123"

    # Mock session and result
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"entity_id": "entity_001"})
    mock_session.run = AsyncMock(return_value=mock_result)

    # Configure context manager
    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    entity_ids = await neo4j_store.add_entities(entities, chunk_id)

    assert len(entity_ids) == 3
    assert all(entity_id == "entity_001" for entity_id in entity_ids)
    assert mock_session.run.call_count == 3


@pytest.mark.asyncio
async def test_add_entities_empty_list(neo4j_store):
    """Test adding empty entity list."""
    entities = []
    chunk_id = "chunk_123"

    entity_ids = await neo4j_store.add_entities(entities, chunk_id)

    assert entity_ids == []


@pytest.mark.asyncio
async def test_add_entities_single_entity(neo4j_store, mock_connection_manager):
    """Test adding single entity."""
    entities = [{"name": "Alice", "type": "Person"}]
    chunk_id = "chunk_123"

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"entity_id": "entity_alice"})
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    entity_ids = await neo4j_store.add_entities(entities, chunk_id)

    assert len(entity_ids) == 1
    assert entity_ids[0] == "entity_alice"


# =====================================================
# ADD RELATIONSHIPS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_add_relationships_success(neo4j_store, mock_connection_manager):
    """Test adding relationships successfully."""
    relationships = [
        {
            "source": "Alice",
            "target": "Bob",
            "type": "KNOWS",
            "subtype": "colleague",
            "confidence": 0.9,
            "strength": 0.8,
        }
    ]
    chunk_id = "chunk_123"

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"rel_id": "rel_001"})
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    count = await neo4j_store.add_relationships(relationships, chunk_id)

    assert count == 1
    assert mock_session.run.call_count == 2  # 1 for rel, 1 for updating counts


@pytest.mark.asyncio
async def test_add_relationships_with_entity_ids(neo4j_store, mock_connection_manager):
    """Test adding relationships using entity1_id/entity2_id keys."""
    relationships = [{"entity1_id": "Alice", "entity2_id": "Bob", "type": "WORKS_WITH"}]
    chunk_id = "chunk_123"

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"rel_id": "rel_002"})
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    count = await neo4j_store.add_relationships(relationships, chunk_id)

    assert count == 1


@pytest.mark.asyncio
async def test_add_relationships_missing_entity_names(neo4j_store, mock_connection_manager):
    """Test skipping relationships with missing entity names."""
    relationships = [
        {"source": "Alice", "target": None},  # Missing target
        {"source": None, "target": "Bob"},  # Missing source
        {},  # Missing both
    ]
    chunk_id = "chunk_123"

    mock_session = AsyncMock()
    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    count = await neo4j_store.add_relationships(relationships, chunk_id)

    assert count == 0


@pytest.mark.asyncio
async def test_add_relationships_empty_list(neo4j_store):
    """Test adding empty relationship list."""
    relationships = []
    chunk_id = "chunk_123"

    count = await neo4j_store.add_relationships(relationships, chunk_id)

    assert count == 0


@pytest.mark.asyncio
async def test_add_relationships_default_values(neo4j_store, mock_connection_manager):
    """Test adding relationships with default values."""
    relationships = [{"source": "Alice", "target": "Bob"}]  # Minimal data
    chunk_id = "chunk_123"

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"rel_id": "rel_003"})
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    count = await neo4j_store.add_relationships(relationships, chunk_id)

    assert count == 1
    # Verify defaults were used
    call_args = mock_session.run.call_args_list[0]
    assert call_args[1]["rel_type"] == "RELATED_TO"
    assert call_args[1]["rel_subtype"] == "general"
    assert call_args[1]["confidence"] == 0.8
    assert call_args[1]["strength"] == 0.5


# =====================================================
# ADD EPISODES TESTS
# =====================================================


@pytest.mark.asyncio
async def test_add_episodes_success(neo4j_store, mock_connection_manager):
    """Test adding episodes successfully."""
    facts = ["Alice met Bob in 2020", "They started working together"]
    entity_names = ["Alice", "Bob"]
    chunk_id = "chunk_123"
    document_id = "doc_456"

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"episode_id": "episode_001"})
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    episode_ids = await neo4j_store.add_episodes(facts, entity_names, chunk_id, document_id)

    assert len(episode_ids) == 2
    # Each episode creates 2 queries (episode + linking)
    assert mock_session.run.call_count == 4


@pytest.mark.asyncio
async def test_add_episodes_long_fact_truncation(neo4j_store, mock_connection_manager):
    """Test that long facts are truncated to 500 chars."""
    long_fact = "x" * 600  # 600 chars
    facts = [long_fact]
    entity_names = ["Alice"]
    chunk_id = "chunk_123"
    document_id = "doc_456"

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"episode_id": "episode_002"})
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    episode_ids = await neo4j_store.add_episodes(facts, entity_names, chunk_id, document_id)

    assert len(episode_ids) == 1
    # Verify truncation
    call_args = mock_session.run.call_args_list[0]
    fact_param = call_args[1]["fact"]
    assert len(fact_param) == 500  # 497 + "..."
    assert fact_param.endswith("...")


@pytest.mark.asyncio
async def test_add_episodes_no_entity_names(neo4j_store, mock_connection_manager):
    """Test adding episodes without entity names."""
    facts = ["Some general fact"]
    entity_names = []
    chunk_id = "chunk_123"
    document_id = "doc_456"

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"episode_id": "episode_003"})
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    episode_ids = await neo4j_store.add_episodes(facts, entity_names, chunk_id, document_id)

    assert len(episode_ids) == 1
    # Only 1 query (no linking since no entities)
    assert mock_session.run.call_count == 1


@pytest.mark.asyncio
async def test_add_episodes_empty_facts(neo4j_store):
    """Test adding empty facts list."""
    facts = []
    entity_names = ["Alice"]
    chunk_id = "chunk_123"
    document_id = "doc_456"

    episode_ids = await neo4j_store.add_episodes(facts, entity_names, chunk_id, document_id)

    assert episode_ids == []


# =====================================================
# EXECUTE QUERY TESTS
# =====================================================


@pytest.mark.asyncio
async def test_execute_query_success(neo4j_store, mock_connection_manager):
    """Test executing custom Cypher query."""
    cypher = "MATCH (n) RETURN n LIMIT 10"
    parameters = {"limit": 10}

    mock_session = AsyncMock()

    # Create async iterator for results
    mock_records = [{"n": {"name": "Alice"}}, {"n": {"name": "Bob"}}]

    async def async_iter_records():
        for record in mock_records:
            yield record

    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter_records()
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    results = await neo4j_store.execute_query(cypher, parameters)

    assert len(results) == 2
    assert results[0]["n"]["name"] == "Alice"
    assert results[1]["n"]["name"] == "Bob"


@pytest.mark.asyncio
async def test_execute_query_no_parameters(neo4j_store, mock_connection_manager):
    """Test executing query without parameters."""
    cypher = "MATCH (n) RETURN count(n)"

    mock_session = AsyncMock()

    async def async_iter_empty(self):
        return
        yield

    mock_result = AsyncMock()
    mock_result.__aiter__ = async_iter_empty
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    results = await neo4j_store.execute_query(cypher)

    assert results == []


# =====================================================
# SEARCH ENTITIES TESTS
# =====================================================


@pytest.mark.asyncio
async def test_search_entities_exact_match(neo4j_store, mock_connection_manager):
    """Test searching entities with exact match."""
    query = "Alice"
    limit = 10

    mock_session = AsyncMock()

    # Mock exact match results
    mock_records = [{"e": {"id": "e1", "name": "Alice", "type": "Person", "importance_score": 0.9}}]

    async def async_iter_records():
        for record in mock_records:
            yield record

    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter_records()
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    entities = await neo4j_store.search_entities(query, limit)

    assert len(entities) == 1
    assert entities[0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_search_entities_fuzzy_search(neo4j_store, mock_connection_manager):
    """Test searching entities with fuzzy search fallback."""
    query = "Alic"
    limit = 10

    mock_session = AsyncMock()

    # First query (exact match) returns empty
    async def async_iter_empty(self):
        return
        yield

    # Second query (fuzzy search) returns results
    mock_fuzzy_records = [{"e": {"id": "e1", "name": "Alice", "type": "Person"}, "score": 0.95}]

    async def async_iter_fuzzy():
        for record in mock_fuzzy_records:
            yield record

    # Configure two different results for two consecutive calls
    mock_result1 = AsyncMock()
    mock_result1.__aiter__ = async_iter_empty

    mock_result2 = AsyncMock()
    mock_result2.__aiter__ = lambda self: async_iter_fuzzy()

    mock_session.run = AsyncMock(side_effect=[mock_result1, mock_result2])

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    entities = await neo4j_store.search_entities(query, limit)

    assert len(entities) == 1
    assert entities[0]["name"] == "Alice"
    assert "search_score" in entities[0]
    assert entities[0]["search_score"] == 0.95


@pytest.mark.asyncio
async def test_search_entities_no_results(neo4j_store, mock_connection_manager):
    """Test searching entities with no results."""
    query = "NonexistentEntity"
    limit = 10

    mock_session = AsyncMock()

    async def async_iter_empty(self):
        return
        yield

    mock_result = AsyncMock()
    mock_result.__aiter__ = async_iter_empty
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    entities = await neo4j_store.search_entities(query, limit)

    assert entities == []


# =====================================================
# GET ENTITY RELATIONSHIPS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_entity_relationships_success(neo4j_store, mock_connection_manager):
    """Test getting entity relationships."""
    entity_id = "entity_123"
    depth = 2

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(
        return_value={
            "e": {"id": entity_id, "name": "Alice"},
            "relationships": [{"type": "KNOWS", "confidence": 0.9}],
            "related_entities": [{"id": "entity_456", "name": "Bob"}],
        }
    )
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    result = await neo4j_store.get_entity_relationships(entity_id, depth)

    assert result is not None
    assert result["entity"]["name"] == "Alice"
    assert len(result["relationships"]) == 1
    assert len(result["related_entities"]) == 1


@pytest.mark.asyncio
async def test_get_entity_relationships_depth_cap(neo4j_store, mock_connection_manager):
    """Test that depth is capped at 3."""
    entity_id = "entity_123"
    depth = 10  # Request depth 10

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(
        return_value={"e": {"id": entity_id}, "relationships": [], "related_entities": []}
    )
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    await neo4j_store.get_entity_relationships(entity_id, depth)

    # Verify depth was capped
    call_args = mock_session.run.call_args
    assert call_args[1]["depth"] == 3


@pytest.mark.asyncio
async def test_get_entity_relationships_not_found(neo4j_store, mock_connection_manager):
    """Test getting relationships for non-existent entity."""
    entity_id = "nonexistent"
    depth = 1

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    result = await neo4j_store.get_entity_relationships(entity_id, depth)

    assert result is None


# =====================================================
# SEARCH EPISODES TESTS
# =====================================================


@pytest.mark.asyncio
async def test_search_episodes_basic(neo4j_store, mock_connection_manager):
    """Test basic episode search."""
    query = "meeting"
    limit = 20

    mock_session = AsyncMock()

    mock_records = [{"ep": {"id": "ep1", "fact": "Meeting happened"}, "score": 0.85}]

    async def async_iter_records():
        for record in mock_records:
            yield record

    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter_records()
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    episodes = await neo4j_store.search_episodes(query, limit=limit)

    assert len(episodes) == 1
    assert episodes[0]["fact"] == "Meeting happened"
    assert "search_score" in episodes[0]


@pytest.mark.asyncio
async def test_search_episodes_with_entity_filter(neo4j_store, mock_connection_manager):
    """Test episode search filtered by entities."""
    query = "meeting"
    entity_ids = ["entity_123", "entity_456"]
    limit = 20

    mock_session = AsyncMock()

    async def async_iter_empty(self):
        return
        yield

    mock_result = AsyncMock()
    mock_result.__aiter__ = async_iter_empty
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    await neo4j_store.search_episodes(query, entity_ids=entity_ids, limit=limit)

    # Verify entity_ids were passed (params dict is 2nd positional arg)
    call_args = mock_session.run.call_args
    assert call_args[0][1]["entity_ids"] == entity_ids


@pytest.mark.asyncio
async def test_search_episodes_with_time_range(neo4j_store, mock_connection_manager):
    """Test episode search filtered by time range."""
    query = "meeting"
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2024, 12, 31)
    time_range = (start_time, end_time)
    limit = 20

    mock_session = AsyncMock()

    async def async_iter_empty(self):
        return
        yield

    mock_result = AsyncMock()
    mock_result.__aiter__ = async_iter_empty
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    await neo4j_store.search_episodes(query, time_range=time_range, limit=limit)

    # Verify time range was passed (params dict is 2nd positional arg)
    call_args = mock_session.run.call_args
    assert call_args[0][1]["start_time"] == start_time
    assert call_args[0][1]["end_time"] == end_time


# =====================================================
# GET ENTITY TIMELINE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_entity_timeline_success(neo4j_store, mock_connection_manager):
    """Test getting entity timeline."""
    entity_id = "entity_123"
    limit = 50

    mock_session = AsyncMock()

    mock_records = [
        {"ep": {"id": "ep1", "fact": "First event", "timestamp": "2024-01-01"}},
        {"ep": {"id": "ep2", "fact": "Second event", "timestamp": "2024-01-02"}},
    ]

    async def async_iter_records():
        for record in mock_records:
            yield record

    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter_records()
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    timeline = await neo4j_store.get_entity_timeline(entity_id, limit)

    assert len(timeline) == 2
    assert timeline[0]["fact"] == "First event"
    assert timeline[1]["fact"] == "Second event"


@pytest.mark.asyncio
async def test_get_entity_timeline_empty(neo4j_store, mock_connection_manager):
    """Test getting timeline for entity with no episodes."""
    entity_id = "entity_123"
    limit = 50

    mock_session = AsyncMock()

    async def async_iter_empty(self):
        return
        yield

    mock_result = AsyncMock()
    mock_result.__aiter__ = async_iter_empty
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    timeline = await neo4j_store.get_entity_timeline(entity_id, limit)

    assert timeline == []


# =====================================================
# UPDATE ENTITY IMPORTANCE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_update_entity_importance_success(neo4j_store, mock_connection_manager):
    """Test updating entity importance score."""
    entity_id = "entity_123"

    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=AsyncMock())

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    # Should not raise
    await neo4j_store.update_entity_importance(entity_id)

    # Verify query was executed
    mock_session.run.assert_called_once()


# =====================================================
# FIND PATHS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_find_paths_success(neo4j_store, mock_connection_manager):
    """Test finding paths between entities."""
    entity1_id = "entity_123"
    entity2_id = "entity_456"
    max_depth = 3

    mock_session = AsyncMock()

    # Mock path object
    mock_node1 = {"id": entity1_id, "name": "Alice"}
    mock_node2 = {"id": "entity_789", "name": "Carol"}
    mock_node3 = {"id": entity2_id, "name": "Bob"}

    mock_rel1 = {"type": "KNOWS", "confidence": 0.9}
    mock_rel2 = {"type": "WORKS_WITH", "confidence": 0.8}

    mock_path = Mock()
    mock_path.nodes = [mock_node1, mock_node2, mock_node3]
    mock_path.relationships = [mock_rel1, mock_rel2]

    mock_records = [{"path": mock_path}]

    async def async_iter_records():
        for record in mock_records:
            yield record

    mock_result = AsyncMock()
    mock_result.__aiter__ = lambda self: async_iter_records()
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    paths = await neo4j_store.find_paths(entity1_id, entity2_id, max_depth)

    assert len(paths) == 1
    assert len(paths[0]["nodes"]) == 3
    assert len(paths[0]["relationships"]) == 2
    assert paths[0]["length"] == 2


@pytest.mark.asyncio
async def test_find_paths_no_path_exists(neo4j_store, mock_connection_manager):
    """Test finding paths when no path exists."""
    entity1_id = "entity_123"
    entity2_id = "entity_456"
    max_depth = 3

    mock_session = AsyncMock()

    async def async_iter_empty(self):
        return
        yield

    mock_result = AsyncMock()
    mock_result.__aiter__ = async_iter_empty
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    paths = await neo4j_store.find_paths(entity1_id, entity2_id, max_depth)

    assert paths == []


# =====================================================
# GET GRAPH STATISTICS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_graph_statistics_success(neo4j_store, mock_connection_manager):
    """Test getting graph statistics."""
    mock_session = AsyncMock()

    # Mock count queries for each label
    mock_entity_count = AsyncMock()
    mock_entity_count.single = AsyncMock(return_value={"count": 100})

    mock_episode_count = AsyncMock()
    mock_episode_count.single = AsyncMock(return_value={"count": 50})

    mock_concept_count = AsyncMock()
    mock_concept_count.single = AsyncMock(return_value={"count": 20})

    mock_event_count = AsyncMock()
    mock_event_count.single = AsyncMock(return_value={"count": 10})

    mock_rel_count = AsyncMock()
    mock_rel_count.single = AsyncMock(return_value={"count": 200})

    # Mock top entities query
    mock_top_entities = [
        {"name": "Alice", "type": "Person", "score": 0.95},
        {"name": "Bob", "type": "Person", "score": 0.85},
    ]

    async def async_iter_top_entities():
        for record in mock_top_entities:
            yield record

    mock_top_result = AsyncMock()
    mock_top_result.__aiter__ = lambda self: async_iter_top_entities()

    # Configure sequential calls
    mock_session.run = AsyncMock(
        side_effect=[
            mock_entity_count,
            mock_episode_count,
            mock_concept_count,
            mock_event_count,
            mock_rel_count,
            mock_top_result,
        ]
    )

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    stats = await neo4j_store.get_graph_statistics()

    assert stats["entity_count"] == 100
    assert stats["episode_count"] == 50
    assert stats["concept_count"] == 20
    assert stats["event_count"] == 10
    assert stats["relationship_count"] == 200
    assert len(stats["top_entities"]) == 2
    assert "graph_density" in stats
    assert stats["graph_density"] > 0


@pytest.mark.asyncio
async def test_get_graph_statistics_empty_graph(neo4j_store, mock_connection_manager):
    """Test getting statistics for empty graph."""
    mock_session = AsyncMock()

    # Mock empty counts
    mock_empty_count = AsyncMock()
    mock_empty_count.single = AsyncMock(return_value={"count": 0})

    async def async_iter_empty(self):
        return
        yield

    mock_empty_result = AsyncMock()
    mock_empty_result.__aiter__ = async_iter_empty

    # All queries return 0
    mock_session.run = AsyncMock(
        side_effect=[
            mock_empty_count,  # Entity
            mock_empty_count,  # Episode
            mock_empty_count,  # Concept
            mock_empty_count,  # Event
            mock_empty_count,  # Relationships
            mock_empty_result,  # Top entities
        ]
    )

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    stats = await neo4j_store.get_graph_statistics()

    assert stats["entity_count"] == 0
    assert stats["relationship_count"] == 0
    assert stats["graph_density"] == 0
    assert stats["top_entities"] == []


# =====================================================
# CLEANUP ORPHANED ENTITIES TESTS
# =====================================================


@pytest.mark.asyncio
async def test_cleanup_orphaned_entities_success(neo4j_store, mock_connection_manager):
    """Test cleanup of orphaned entities."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"deleted_count": 5})
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    # Should log info about deleted entities
    await neo4j_store.cleanup_orphaned_entities()

    mock_session.run.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_orphaned_entities_none_found(neo4j_store, mock_connection_manager):
    """Test cleanup when no orphaned entities exist."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"deleted_count": 0})
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_context = mock_connection_manager.get_neo4j_session.return_value
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)

    # Should not log (deleted_count = 0)
    await neo4j_store.cleanup_orphaned_entities()

    mock_session.run.assert_called_once()
