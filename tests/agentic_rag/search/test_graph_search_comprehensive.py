"""
Comprehensive tests for GraphSearch - knowledge graph search for facts and relationships.

Covers:
- Initialization and configuration
- Fact search via Graphiti
- Entity search by name
- Relationship search
- Entity timeline retrieval
- Entity relationship traversal
- Chunk reference extraction
- Statistics tracking
- Error handling
- Parallel search execution
- Data model conversions (to_dict)
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agentic_rag.search.graph_search import (
    GraphEntity,
    GraphFact,
    GraphRelationship,
    GraphSearch,
    GraphSearchResult,
)

# ===== Fixtures =====


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager."""
    cm = Mock()
    return cm


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = Mock()
    return config


@pytest.fixture
def graph_search(mock_connection_manager, mock_config):
    """Create GraphSearch instance with mocks."""
    with patch("src.agentic_rag.search.graph_search.get_config", return_value=mock_config):
        gs = GraphSearch(mock_connection_manager)
        return gs


@pytest.fixture
def sample_facts():
    """Sample graph facts."""
    return [
        GraphFact(
            fact="OpenAI released GPT-4 in March 2023",
            timestamp=datetime(2023, 3, 14),
            confidence=0.9,
            source_chunk="chunk_123",
            entities=["OpenAI", "GPT-4"],
        ),
        GraphFact(
            fact="GPT-4 is a large language model",
            timestamp=None,
            confidence=0.85,
            source_chunk="chunk_456",
            entities=["GPT-4"],
        ),
    ]


@pytest.fixture
def sample_entities():
    """Sample graph entities."""
    return [
        GraphEntity(
            id="entity_1",
            name="OpenAI",
            type="Organization",
            chunk_refs=["chunk_123", "chunk_789"],
            confidence=0.95,
        ),
        GraphEntity(
            id="entity_2",
            name="GPT-4",
            type="Product",
            chunk_refs=["chunk_456"],
            confidence=0.9,
        ),
    ]


@pytest.fixture
def sample_relationships():
    """Sample graph relationships."""
    return [
        GraphRelationship(
            source="OpenAI",
            target="GPT-4",
            type="CREATED",
            confidence=0.9,
            properties={"year": 2023, "source_chunk": "chunk_123"},
        ),
        GraphRelationship(
            source="Sam Altman",
            target="OpenAI",
            type="LEADS",
            confidence=0.95,
            properties={},
        ),
    ]


# ===== Initialization Tests =====


class TestGraphSearchInit:
    """Test GraphSearch initialization."""

    def test_init_requires_connection_manager(self):
        """Test that initialization requires connection manager."""
        with pytest.raises(
            ValueError, match="GraphSearch requires an initialized ConnectionManager"
        ):
            GraphSearch(None)

    def test_init_with_connection_manager(self, mock_connection_manager, mock_config):
        """Test successful initialization."""
        with patch("src.agentic_rag.search.graph_search.get_config", return_value=mock_config):
            gs = GraphSearch(mock_connection_manager)

            assert gs.connection_manager == mock_connection_manager
            assert gs.neo4j_store is not None
            assert gs.graphiti_client is not None

    def test_init_creates_stats(self, graph_search):
        """Test that initialization creates stats tracking."""
        assert graph_search._stats["searches"] == 0
        assert graph_search._stats["facts_found"] == 0
        assert graph_search._stats["entities_found"] == 0


# ===== Main Search Tests =====


@pytest.mark.asyncio
class TestMainSearch:
    """Test main graph search method."""

    async def test_search_combines_all_sources(
        self, graph_search, sample_facts, sample_entities, sample_relationships
    ):
        """Test that search combines facts, entities, and relationships."""
        with (
            patch.object(graph_search, "_search_facts", new=AsyncMock(return_value=sample_facts)),
            patch.object(
                graph_search, "_search_entities", new=AsyncMock(return_value=sample_entities)
            ),
            patch.object(
                graph_search,
                "_search_relationships",
                new=AsyncMock(return_value=sample_relationships),
            ),
        ):
            result = await graph_search.search("OpenAI GPT-4", limit=20)

            assert len(result.facts) == 2
            assert len(result.entities) == 2
            assert len(result.relationships) == 2
            assert result.query_time > 0

    async def test_search_updates_stats(self, graph_search, sample_facts):
        """Test that search updates statistics."""
        with (
            patch.object(graph_search, "_search_facts", new=AsyncMock(return_value=sample_facts)),
            patch.object(graph_search, "_search_entities", new=AsyncMock(return_value=[])),
            patch.object(graph_search, "_search_relationships", new=AsyncMock(return_value=[])),
        ):
            await graph_search.search("test query", limit=20)

            assert graph_search._stats["searches"] == 1
            assert graph_search._stats["facts_found"] == 2
            assert graph_search._stats["total_latency"] > 0

    async def test_search_handles_exceptions(self, graph_search):
        """Test that search handles component failures gracefully."""
        # One component fails, others succeed
        with (
            patch.object(
                graph_search,
                "_search_facts",
                new=AsyncMock(side_effect=Exception("Fact search failed")),
            ),
            patch.object(graph_search, "_search_entities", new=AsyncMock(return_value=[])),
            patch.object(graph_search, "_search_relationships", new=AsyncMock(return_value=[])),
        ):
            result = await graph_search.search("test query", limit=20)

            # Should return empty facts but not crash
            assert result.facts == []
            assert isinstance(result, GraphSearchResult)

    async def test_search_extracts_chunk_refs(
        self, graph_search, sample_facts, sample_entities, sample_relationships
    ):
        """Test that search extracts chunk references."""
        with (
            patch.object(graph_search, "_search_facts", new=AsyncMock(return_value=sample_facts)),
            patch.object(
                graph_search, "_search_entities", new=AsyncMock(return_value=sample_entities)
            ),
            patch.object(
                graph_search,
                "_search_relationships",
                new=AsyncMock(return_value=sample_relationships),
            ),
        ):
            result = await graph_search.search("test query", limit=20)

            assert len(result.chunk_refs) > 0
            # Should include chunk_123, chunk_456, chunk_789 from various sources
            assert "chunk_123" in result.chunk_refs


# ===== Fact Search Tests =====


@pytest.mark.asyncio
class TestSearchFacts:
    """Test fact search functionality."""

    async def test_search_facts_via_graphiti(self, graph_search):
        """Test fact search uses Graphiti client."""
        graphiti_results = [
            {
                "fact": "OpenAI released GPT-4",
                "timestamp": datetime(2023, 3, 14),
                "confidence": 0.9,
                "source_chunk": "chunk_123",
                "entities": ["OpenAI", "GPT-4"],
            }
        ]

        graph_search.graphiti_client.search = AsyncMock(return_value=graphiti_results)

        facts = await graph_search._search_facts("GPT-4", limit=20)

        assert len(facts) == 1
        assert facts[0].fact == "OpenAI released GPT-4"
        assert facts[0].confidence == 0.9
        graph_search.graphiti_client.search.assert_called_once_with("GPT-4", limit=20)

    async def test_search_facts_with_content_field(self, graph_search):
        """Test fact search handles 'content' field as fallback."""
        graphiti_results = [
            {
                "content": "This is fact content",  # Using 'content' instead of 'fact'
                "confidence": 0.8,
                "source_chunk": "chunk_456",
            }
        ]

        graph_search.graphiti_client.search = AsyncMock(return_value=graphiti_results)

        facts = await graph_search._search_facts("test", limit=10)

        assert len(facts) == 1
        assert facts[0].fact == "This is fact content"

    async def test_search_facts_truncates_long_facts(self, graph_search):
        """Test that facts longer than 500 chars are truncated."""
        long_fact = "x" * 600  # 600 characters

        graphiti_results = [
            {
                "fact": long_fact,
                "confidence": 0.8,
                "source_chunk": "chunk_123",
            }
        ]

        graph_search.graphiti_client.search = AsyncMock(return_value=graphiti_results)

        facts = await graph_search._search_facts("test", limit=10)

        assert len(facts[0].fact) == 500

    async def test_search_facts_handles_errors(self, graph_search):
        """Test fact search handles errors gracefully."""
        graph_search.graphiti_client.search = AsyncMock(side_effect=Exception("Graphiti error"))

        facts = await graph_search._search_facts("test", limit=10)

        # Should return empty list, not crash
        assert facts == []


# ===== Entity Search Tests =====


@pytest.mark.asyncio
class TestSearchEntities:
    """Test entity search functionality."""

    async def test_search_entities_by_name(self, graph_search):
        """Test entity search by name."""
        neo4j_results = [
            {
                "id": "entity_1",
                "name": "OpenAI",
                "type": "Organization",
                "chunk_refs": ["chunk_123"],
                "confidence": 0.95,
            }
        ]

        graph_search.neo4j_store.execute_query = AsyncMock(return_value=neo4j_results)

        entities = await graph_search._search_entities("OpenAI", limit=10)

        assert len(entities) == 1
        assert entities[0].name == "OpenAI"
        assert entities[0].type == "Organization"

    async def test_search_entities_case_insensitive(self, graph_search):
        """Test entity search is case-insensitive."""
        graph_search.neo4j_store.execute_query = AsyncMock(return_value=[])

        await graph_search._search_entities("openai", limit=10)

        # Verify query was called (case insensitivity is in Cypher query)
        graph_search.neo4j_store.execute_query.assert_called_once()
        call_args = graph_search.neo4j_store.execute_query.call_args
        cypher = call_args[0][0]
        assert "toLower" in cypher

    async def test_search_entities_with_missing_fields(self, graph_search):
        """Test entity search handles missing optional fields."""
        neo4j_results = [
            {
                "id": "entity_1",
                "name": "OpenAI",
                "type": "Organization",
                # Missing chunk_refs and confidence
            }
        ]

        graph_search.neo4j_store.execute_query = AsyncMock(return_value=neo4j_results)

        entities = await graph_search._search_entities("OpenAI", limit=10)

        assert len(entities) == 1
        assert entities[0].chunk_refs == []
        assert entities[0].confidence == 1.0  # Default

    async def test_search_entities_handles_errors(self, graph_search):
        """Test entity search handles errors gracefully."""
        graph_search.neo4j_store.execute_query = AsyncMock(side_effect=Exception("Neo4j error"))

        entities = await graph_search._search_entities("test", limit=10)

        assert entities == []


# ===== Relationship Search Tests =====


@pytest.mark.asyncio
class TestSearchRelationships:
    """Test relationship search functionality."""

    async def test_search_relationships_finds_relevant_entities_first(self, graph_search):
        """Test relationship search finds entities first."""
        sample_entities = [
            GraphEntity(id="entity_1", name="OpenAI", type="Organization"),
        ]

        with patch.object(
            graph_search, "_search_entities", new=AsyncMock(return_value=sample_entities)
        ):
            graph_search.neo4j_store.execute_query = AsyncMock(return_value=[])

            await graph_search._search_relationships("OpenAI", limit=10)

            graph_search._search_entities.assert_called_once_with("OpenAI", 10)

    async def test_search_relationships_returns_empty_if_no_entities(self, graph_search):
        """Test relationship search returns empty if no entities found."""
        with patch.object(graph_search, "_search_entities", new=AsyncMock(return_value=[])):
            relationships = await graph_search._search_relationships("unknown", limit=10)

            assert relationships == []

    async def test_search_relationships_queries_by_entity_ids(self, graph_search):
        """Test relationship search queries using entity IDs."""
        sample_entities = [
            GraphEntity(id="entity_1", name="OpenAI", type="Organization"),
            GraphEntity(id="entity_2", name="GPT-4", type="Product"),
        ]

        neo4j_results = [
            {
                "source": "OpenAI",
                "target": "GPT-4",
                "type": "CREATED",
                "confidence": 0.9,
                "properties": {},
            }
        ]

        with patch.object(
            graph_search, "_search_entities", new=AsyncMock(return_value=sample_entities)
        ):
            graph_search.neo4j_store.execute_query = AsyncMock(return_value=neo4j_results)

            relationships = await graph_search._search_relationships("OpenAI", limit=10)

            assert len(relationships) == 1
            assert relationships[0].source == "OpenAI"
            assert relationships[0].target == "GPT-4"

            # Verify entity_ids were passed
            call_args = graph_search.neo4j_store.execute_query.call_args
            params = call_args[0][1]
            assert params["entity_ids"] == ["entity_1", "entity_2"]

    async def test_search_relationships_handles_errors(self, graph_search):
        """Test relationship search handles errors gracefully."""
        with patch.object(
            graph_search, "_search_entities", new=AsyncMock(side_effect=Exception("Error"))
        ):
            relationships = await graph_search._search_relationships("test", limit=10)

            assert relationships == []


# ===== Entity Timeline Tests =====


@pytest.mark.asyncio
class TestEntityTimeline:
    """Test entity timeline retrieval."""

    async def test_find_entity_timeline(self, graph_search):
        """Test finding entity timeline."""
        # Mock entity lookup
        entity_lookup_result = [{"entity_id": "entity_123"}]

        # Mock timeline results
        timeline_facts = [
            {
                "fact": "Event 1",
                "timestamp": datetime(2023, 1, 1),
                "confidence": 0.9,
                "source_chunk": "chunk_1",
            },
            {
                "fact": "Event 2",
                "timestamp": datetime(2023, 2, 1),
                "confidence": 0.85,
                "source_chunk": "chunk_2",
            },
        ]

        graph_search.neo4j_store.execute_query = AsyncMock(return_value=entity_lookup_result)
        graph_search.neo4j_store.get_entity_timeline = AsyncMock(return_value=timeline_facts)

        facts = await graph_search.find_entity_timeline("OpenAI", limit=20)

        assert len(facts) == 2
        assert facts[0].fact == "Event 1"
        assert facts[0].entities == ["OpenAI"]

    async def test_find_entity_timeline_entity_not_found(self, graph_search):
        """Test timeline when entity not found."""
        graph_search.neo4j_store.execute_query = AsyncMock(return_value=[])

        facts = await graph_search.find_entity_timeline("UnknownEntity", limit=20)

        assert facts == []

    async def test_find_entity_timeline_truncates_facts(self, graph_search):
        """Test that timeline facts are truncated."""
        entity_lookup_result = [{"entity_id": "entity_123"}]

        long_fact = "x" * 600
        timeline_facts = [
            {
                "fact": long_fact,
                "timestamp": datetime.now(),
                "confidence": 0.9,
                "source_chunk": "chunk_1",
            }
        ]

        graph_search.neo4j_store.execute_query = AsyncMock(return_value=entity_lookup_result)
        graph_search.neo4j_store.get_entity_timeline = AsyncMock(return_value=timeline_facts)

        facts = await graph_search.find_entity_timeline("OpenAI", limit=20)

        assert len(facts[0].fact) == 500

    async def test_find_entity_timeline_handles_errors(self, graph_search):
        """Test timeline handles errors gracefully."""
        graph_search.neo4j_store.execute_query = AsyncMock(side_effect=Exception("Neo4j error"))

        facts = await graph_search.find_entity_timeline("OpenAI", limit=20)

        assert facts == []


# ===== Entity Relationships Tests =====


@pytest.mark.asyncio
class TestEntityRelationships:
    """Test entity relationship traversal."""

    async def test_find_entity_relationships(self, graph_search):
        """Test finding entity relationships."""
        neo4j_results = [
            {
                "entity_name": "GPT-4",
                "entity_type": "Product",
                "relationships": [
                    {"type": "CREATED", "confidence": 0.9, "properties": {}},
                ],
            },
            {
                "entity_name": "Sam Altman",
                "entity_type": "Person",
                "relationships": [
                    {"type": "LEADS", "confidence": 0.95, "properties": {}},
                ],
            },
        ]

        graph_search.neo4j_store.execute_query = AsyncMock(return_value=neo4j_results)

        result = await graph_search.find_entity_relationships("OpenAI", depth=2)

        assert result["central_entity"] == "OpenAI"
        assert len(result["related_entities"]) == 2
        assert result["related_entities"][0]["name"] == "GPT-4"

    async def test_find_entity_relationships_with_depth(self, graph_search):
        """Test relationship traversal respects depth parameter."""
        graph_search.neo4j_store.execute_query = AsyncMock(return_value=[])

        await graph_search.find_entity_relationships("OpenAI", depth=3)

        # Verify depth was passed to query
        call_args = graph_search.neo4j_store.execute_query.call_args
        params = call_args[0][1]
        assert params["depth"] == 3

    async def test_find_entity_relationships_handles_errors(self, graph_search):
        """Test relationship traversal handles errors gracefully."""
        graph_search.neo4j_store.execute_query = AsyncMock(side_effect=Exception("Neo4j error"))

        result = await graph_search.find_entity_relationships("OpenAI", depth=2)

        assert result["central_entity"] == "OpenAI"
        assert result["related_entities"] == []


# ===== Chunk Reference Extraction Tests =====


class TestChunkRefExtraction:
    """Test chunk reference extraction."""

    def test_extract_chunk_refs_from_facts(self, graph_search, sample_facts):
        """Test extracting chunk refs from facts."""
        chunk_refs = graph_search._extract_chunk_refs(sample_facts, [], [])

        assert "chunk_123" in chunk_refs
        assert "chunk_456" in chunk_refs

    def test_extract_chunk_refs_from_entities(self, graph_search, sample_entities):
        """Test extracting chunk refs from entities."""
        chunk_refs = graph_search._extract_chunk_refs([], sample_entities, [])

        assert "chunk_123" in chunk_refs
        assert "chunk_456" in chunk_refs
        assert "chunk_789" in chunk_refs

    def test_extract_chunk_refs_from_relationships(self, graph_search, sample_relationships):
        """Test extracting chunk refs from relationship properties."""
        chunk_refs = graph_search._extract_chunk_refs([], [], sample_relationships)

        # Only first relationship has source_chunk in properties
        assert "chunk_123" in chunk_refs

    def test_extract_chunk_refs_deduplication(
        self, graph_search, sample_facts, sample_entities, sample_relationships
    ):
        """Test that chunk refs are deduplicated."""
        chunk_refs = graph_search._extract_chunk_refs(
            sample_facts, sample_entities, sample_relationships
        )

        # chunk_123 appears in multiple places, should only appear once
        assert chunk_refs.count("chunk_123") == 1

    def test_extract_chunk_refs_empty(self, graph_search):
        """Test extracting chunk refs from empty results."""
        chunk_refs = graph_search._extract_chunk_refs([], [], [])

        assert chunk_refs == []


# ===== Statistics Tests =====


class TestStatistics:
    """Test statistics tracking and retrieval."""

    def test_get_stats_empty(self, graph_search):
        """Test getting stats before any searches."""
        stats = graph_search.get_stats()

        assert stats["searches"] == 0
        assert stats["facts_found"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_searches(self, graph_search, sample_facts):
        """Test stats after performing searches."""
        with (
            patch.object(graph_search, "_search_facts", new=AsyncMock(return_value=sample_facts)),
            patch.object(graph_search, "_search_entities", new=AsyncMock(return_value=[])),
            patch.object(graph_search, "_search_relationships", new=AsyncMock(return_value=[])),
        ):
            await graph_search.search("query 1", limit=20)
            await graph_search.search("query 2", limit=20)

        stats = graph_search.get_stats()

        assert stats["searches"] == 2
        assert stats["facts_found"] == 4  # 2 facts x 2 searches
        assert "avg_latency" in stats
        assert "avg_facts_per_search" in stats

    @pytest.mark.asyncio
    async def test_stats_calculates_averages(self, graph_search, sample_facts, sample_entities):
        """Test that stats calculate proper averages."""
        with (
            patch.object(graph_search, "_search_facts", new=AsyncMock(return_value=sample_facts)),
            patch.object(
                graph_search, "_search_entities", new=AsyncMock(return_value=sample_entities)
            ),
            patch.object(graph_search, "_search_relationships", new=AsyncMock(return_value=[])),
        ):
            await graph_search.search("test", limit=20)

        stats = graph_search.get_stats()

        assert stats["avg_facts_per_search"] == 2.0
        assert stats["avg_entities_per_search"] == 2.0


# ===== Data Model Tests =====


class TestDataModels:
    """Test data model to_dict conversions."""

    def test_graph_fact_to_dict(self):
        """Test GraphFact to_dict conversion."""
        fact = GraphFact(
            fact="Test fact",
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            confidence=0.9,
            source_chunk="chunk_123",
            entities=["Entity1", "Entity2"],
        )

        fact_dict = fact.to_dict()

        assert fact_dict["fact"] == "Test fact"
        assert fact_dict["timestamp"] == "2023-01-01T12:00:00"
        assert fact_dict["confidence"] == 0.9
        assert fact_dict["entities"] == ["Entity1", "Entity2"]

    def test_graph_fact_to_dict_no_timestamp(self):
        """Test GraphFact to_dict with None timestamp."""
        fact = GraphFact(
            fact="Test fact",
            timestamp=None,
            confidence=0.8,
            source_chunk="chunk_123",
        )

        fact_dict = fact.to_dict()

        assert fact_dict["timestamp"] is None

    def test_graph_entity_to_dict(self):
        """Test GraphEntity to_dict conversion."""
        entity = GraphEntity(
            id="entity_123",
            name="OpenAI",
            type="Organization",
            chunk_refs=["chunk_1", "chunk_2"],
            confidence=0.95,
        )

        entity_dict = entity.to_dict()

        assert entity_dict["id"] == "entity_123"
        assert entity_dict["name"] == "OpenAI"
        assert entity_dict["type"] == "Organization"
        assert entity_dict["chunk_refs"] == ["chunk_1", "chunk_2"]

    def test_graph_relationship_to_dict(self):
        """Test GraphRelationship to_dict conversion."""
        rel = GraphRelationship(
            source="OpenAI",
            target="GPT-4",
            type="CREATED",
            confidence=0.9,
            properties={"year": 2023},
        )

        rel_dict = rel.to_dict()

        assert rel_dict["source"] == "OpenAI"
        assert rel_dict["target"] == "GPT-4"
        assert rel_dict["type"] == "CREATED"
        assert rel_dict["properties"]["year"] == 2023

    def test_graph_search_result_to_dict(self, sample_facts, sample_entities, sample_relationships):
        """Test GraphSearchResult to_dict conversion."""
        result = GraphSearchResult(
            facts=sample_facts,
            entities=sample_entities,
            relationships=sample_relationships,
            chunk_refs=["chunk_1", "chunk_2"],
            query_time=0.5,
        )

        result_dict = result.to_dict()

        assert len(result_dict["facts"]) == 2
        assert len(result_dict["entities"]) == 2
        assert len(result_dict["relationships"]) == 2
        assert result_dict["query_time"] == 0.5
        assert result_dict["chunk_refs"] == ["chunk_1", "chunk_2"]
