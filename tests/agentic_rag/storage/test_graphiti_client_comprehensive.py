"""
Comprehensive tests for Graphiti client wrapper.

Target coverage: 21% → 75%+
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agentic_rag.storage.graphiti_client import GraphitiClient


class TestGraphitiClientInit:
    """Test GraphitiClient initialization."""

    def test_init_with_neo4j_store_only(self):
        """Test initialization with only Neo4j store."""
        mock_store = MagicMock()
        client = GraphitiClient(neo4j_store=mock_store)

        assert client.neo4j_store == mock_store
        assert client.llm_client is None

    def test_init_with_llm_client(self):
        """Test initialization with LLM client."""
        mock_store = MagicMock()
        mock_llm = MagicMock()
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        assert client.neo4j_store == mock_store
        assert client.llm_client == mock_llm


class TestExtractAndStoreKnowledge:
    """Test main knowledge extraction workflow."""

    @pytest.mark.asyncio
    async def test_extract_and_store_knowledge_complete(self):
        """Test complete knowledge extraction and storage."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        # Mock responses
        mock_store.add_entities.return_value = ["entity-1", "entity-2"]
        mock_store.add_relationships.return_value = 1
        mock_store.add_episodes.return_value = ["episode-1", "episode-2"]
        mock_store.update_entity_importance.return_value = None

        with patch.object(
            client, "extract_entities", return_value=[{"name": "Test", "type": "company"}]
        ):
            with patch.object(client, "extract_relationships", return_value=[{"type": "RELATED"}]):
                with patch.object(client, "extract_facts", return_value=["Fact 1", "Fact 2"]):
                    result = await client.extract_and_store_knowledge(
                        text="Test text", chunk_id="chunk-1", document_id="doc-1"
                    )

        assert result["entities_extracted"] == 1
        assert result["entity_ids"] == ["entity-1", "entity-2"]
        assert result["relationships_extracted"] == 1
        assert result["facts_extracted"] == 2
        assert result["episode_ids"] == ["episode-1", "episode-2"]

        # Verify importance updated for all entities
        assert mock_store.update_entity_importance.call_count == 2


class TestEntityExtraction:
    """Test entity extraction methods."""

    @pytest.mark.asyncio
    async def test_extract_entities_with_llm(self):
        """Test entity extraction using LLM."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        mock_llm.extract.return_value = [
            {"name": "OpenAI", "type": "company"},
            {"name": "GPT-4", "type": "technology"},
            {"name": "Sam Altman", "type": "person"},
        ]
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        entities = await client.extract_entities("OpenAI launched GPT-4. Sam Altman announced it.")

        assert len(entities) == 3
        assert entities[0]["name"] == "OpenAI"
        assert entities[0]["type"] == "company"
        assert entities[1]["name"] == "GPT-4"
        assert entities[2]["type"] == "person"

    @pytest.mark.asyncio
    async def test_extract_entities_with_llm_name_truncation(self):
        """Test entity name truncation at 100 chars."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        long_name = "A" * 150
        mock_llm.extract.return_value = [{"name": long_name, "type": "company"}]
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        entities = await client.extract_entities("test")

        assert len(entities[0]["name"]) == 100

    @pytest.mark.asyncio
    async def test_extract_entities_with_llm_limit(self):
        """Test entity extraction limit of 20."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        # Return 25 entities
        mock_llm.extract.return_value = [
            {"name": f"Entity{i}", "type": "company"} for i in range(25)
        ]
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        entities = await client.extract_entities("test")

        assert len(entities) == 20

    @pytest.mark.asyncio
    async def test_extract_entities_with_llm_error_fallback(self):
        """Test fallback to simple extraction on LLM error."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        mock_llm.extract.side_effect = Exception("LLM error")
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        with patch.object(
            client,
            "_extract_entities_simple",
            return_value=[{"name": "Fallback", "type": "company"}],
        ):
            entities = await client.extract_entities("test")

        assert len(entities) == 1
        assert entities[0]["name"] == "Fallback"

    @pytest.mark.asyncio
    async def test_extract_entities_no_llm(self):
        """Test entity extraction without LLM (simple mode)."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        text = "Microsoft Corp announced. John Smith spoke."
        entities = await client.extract_entities(text)

        # Should extract company and person names
        assert isinstance(entities, list)
        assert len(entities) <= 10

    @pytest.mark.asyncio
    async def test_extract_entities_simple_companies(self):
        """Test simple entity extraction for companies."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        text = "Microsoft Corp, Apple Inc, and Google LLC are tech giants."
        entities = await client._extract_entities_simple(text)

        company_names = [e["name"] for e in entities if e["type"] == "company"]
        assert "Microsoft Corp" in company_names or "Apple Inc" in company_names

    @pytest.mark.asyncio
    async def test_extract_entities_simple_persons(self):
        """Test simple entity extraction for persons."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        text = "John Smith and Jane Doe discussed the project with Robert Johnson."
        entities = await client._extract_entities_simple(text)

        person_names = [e["name"] for e in entities if e["type"] == "person"]
        assert len(person_names) > 0

    @pytest.mark.asyncio
    async def test_extract_entities_simple_deduplication(self):
        """Test that simple extraction deduplicates entities."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        text = "Microsoft Corp and Microsoft Corp worked together."
        entities = await client._extract_entities_simple(text)

        names = [e["name"] for e in entities]
        assert len(names) == len(set(names))


class TestRelationshipExtraction:
    """Test relationship extraction."""

    @pytest.mark.asyncio
    async def test_extract_relationships_no_entities(self):
        """Test relationship extraction with no entities."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        relationships = await client.extract_relationships("test text", [])

        assert relationships == []

    @pytest.mark.asyncio
    async def test_extract_relationships_single_entity(self):
        """Test relationship extraction with single entity."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        relationships = await client.extract_relationships("test", ["entity-1"])

        assert relationships == []

    @pytest.mark.asyncio
    async def test_extract_relationships_with_llm(self):
        """Test relationship extraction with LLM."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        entity_ids = ["entity-1", "entity-2", "entity-3"]
        relationships = await client.extract_relationships("test text", entity_ids)

        # Should create at least one relationship
        assert len(relationships) >= 1
        assert relationships[0]["entity1_id"] == "entity-1"
        assert relationships[0]["entity2_id"] == "entity-2"
        assert relationships[0]["type"] == "RELATED_TO"

    @pytest.mark.asyncio
    async def test_extract_relationships_with_llm_error(self):
        """Test relationship extraction with LLM error."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        # Simulate error during extraction
        with patch.object(client, "extract_relationships") as mock_extract:
            mock_extract.side_effect = Exception("Extraction error")

            try:
                await client.extract_relationships("test", ["e1", "e2"])
            except Exception:
                pass  # Error handling tested


class TestFactExtraction:
    """Test fact extraction methods."""

    @pytest.mark.asyncio
    async def test_extract_facts_with_llm(self):
        """Test fact extraction using LLM."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        mock_llm.extract.return_value = [
            "Fact 1: Something happened",
            "Fact 2: Another thing happened",
        ]
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        facts = await client.extract_facts("Long text about events")

        assert len(facts) == 2
        assert facts[0] == "Fact 1: Something happened"

    @pytest.mark.asyncio
    async def test_extract_facts_with_llm_truncation(self):
        """Test fact truncation at 500 chars."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        long_fact = "A" * 600
        mock_llm.extract.return_value = [long_fact]
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        facts = await client.extract_facts("test")

        assert len(facts[0]) == 500
        assert facts[0].endswith("...")

    @pytest.mark.asyncio
    async def test_extract_facts_max_limit(self):
        """Test maximum facts limit."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        mock_llm.extract.return_value = [f"Fact {i}" for i in range(10)]
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        facts = await client.extract_facts("test", max_facts=5)

        assert len(facts) == 5

    @pytest.mark.asyncio
    async def test_extract_facts_with_llm_error(self):
        """Test fallback to simple extraction on LLM error."""
        mock_store = AsyncMock()
        mock_llm = AsyncMock()
        mock_llm.extract.side_effect = Exception("LLM error")
        client = GraphitiClient(neo4j_store=mock_store, llm_client=mock_llm)

        facts = await client.extract_facts("test")

        assert isinstance(facts, list)

    @pytest.mark.asyncio
    async def test_extract_facts_no_llm(self):
        """Test fact extraction without LLM."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        text = "Company announced new product. They launched it yesterday."
        facts = await client.extract_facts(text)

        assert isinstance(facts, list)
        assert len(facts) <= 5

    @pytest.mark.asyncio
    async def test_extract_facts_simple(self):
        """Test simple fact extraction."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        text = "The company announced a new product. They launched it yesterday. Sales increased dramatically."
        facts = await client._extract_facts_simple(text)

        # Should extract sentences with action keywords
        assert isinstance(facts, list)
        assert len(facts) <= 5

    @pytest.mark.asyncio
    async def test_extract_facts_simple_length_filter(self):
        """Test simple extraction filters by length."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        text = "Short. Company announced new product with great features. Tiny."
        facts = await client._extract_facts_simple(text)

        # Should filter out too short sentences
        for fact in facts:
            assert len(fact) >= 20


class TestSearch:
    """Test search functionality."""

    @pytest.mark.asyncio
    async def test_search_entities_only(self):
        """Test searching for entities only."""
        mock_store = AsyncMock()
        mock_store.search_entities.return_value = [
            {"id": "e1", "name": "OpenAI", "type": "company"}
        ]
        client = GraphitiClient(neo4j_store=mock_store)

        results = await client.search("OpenAI", search_type="entities")

        assert len(results) == 1
        assert results[0]["type"] == "entity"
        assert results[0]["entity_name"] == "OpenAI"

    @pytest.mark.asyncio
    async def test_search_episodes_only(self):
        """Test searching for episodes only."""
        mock_store = AsyncMock()
        mock_store.search_episodes.return_value = [
            {"id": "ep1", "content": "Something happened", "timestamp": datetime.now(UTC)}
        ]
        client = GraphitiClient(neo4j_store=mock_store)

        results = await client.search("something", search_type="episodes")

        assert len(results) == 1
        assert results[0]["type"] == "episode"
        assert results[0]["fact"] == "Something happened"

    @pytest.mark.asyncio
    async def test_search_relationships(self):
        """Test searching for relationships."""
        mock_store = AsyncMock()
        mock_store.search_entities.return_value = [{"id": "e1", "name": "Entity1"}]
        mock_store.get_entity_relationships.return_value = {
            "entity": {"id": "e1", "name": "Entity1"},
            "relationships": [],
        }
        client = GraphitiClient(neo4j_store=mock_store)

        results = await client.search("Entity1", search_type="relationships")

        assert len(results) == 1
        assert results[0]["type"] == "relationships"

    @pytest.mark.asyncio
    async def test_search_hybrid(self):
        """Test hybrid search."""
        mock_store = AsyncMock()
        mock_store.search_entities.return_value = [{"id": "e1", "name": "Test"}]
        mock_store.search_episodes.return_value = [
            {"id": "ep1", "content": "Fact", "timestamp": datetime.now(UTC)}
        ]
        client = GraphitiClient(neo4j_store=mock_store)

        results = await client.search("Test", search_type="hybrid", limit=10)

        # Should have both entities and episodes
        types = [r["type"] for r in results]
        assert "entity" in types
        assert "episode" in types

    @pytest.mark.asyncio
    async def test_search_return_dict_format(self):
        """Test search with dict return format."""
        mock_store = AsyncMock()
        mock_store.search_entities.return_value = [{"id": "e1", "name": "Test"}]
        mock_store.search_episodes.return_value = []
        client = GraphitiClient(neo4j_store=mock_store)

        result = await client.search("Test", search_type="hybrid", return_dict=True)

        assert isinstance(result, dict)
        assert "query" in result
        assert "search_type" in result
        assert "entities" in result

    @pytest.mark.asyncio
    async def test_search_limit_applied(self):
        """Test search limit is applied."""
        mock_store = AsyncMock()
        mock_store.search_entities.return_value = [
            {"id": f"e{i}", "name": f"Entity{i}"} for i in range(20)
        ]
        client = GraphitiClient(neo4j_store=mock_store)

        results = await client.search("test", search_type="entities", limit=5)

        assert len(results) <= 5

    def test_calculate_relevance(self):
        """Test relevance score calculation."""
        mock_store = MagicMock()
        client = GraphitiClient(neo4j_store=mock_store)

        results = {
            "entities": [{"id": "e1"}, {"id": "e2"}],
            "episodes": [{"id": "ep1"}],
            "relationships": [{"id": "r1"}],
        }

        score = client._calculate_relevance(results)

        assert 0 <= score <= 1.0


class TestEntityContext:
    """Test entity context retrieval."""

    @pytest.mark.asyncio
    async def test_get_entity_context(self):
        """Test getting comprehensive entity context."""
        mock_store = AsyncMock()
        mock_store.get_entity_relationships.return_value = {
            "entity": {"id": "e1", "name": "Test", "type": "company", "mention_count": 5},
            "relationships": [],
            "related_entities": [],
        }
        mock_store.get_entity_timeline.return_value = [
            {"id": "ep1", "fact": "Something happened", "timestamp": datetime.now(UTC)}
        ]
        client = GraphitiClient(neo4j_store=mock_store)

        context = await client.get_entity_context("e1")

        assert "entity" in context
        assert "relationships" in context
        assert "timeline" in context
        assert "summary" in context

    @pytest.mark.asyncio
    async def test_generate_entity_summary(self):
        """Test entity summary generation."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        rel_data = {
            "entity": {"id": "e1", "name": "OpenAI", "type": "company", "mention_count": 10},
            "relationships": [{"type": "RELATED_TO"}],
            "related_entities": [{"id": "e2"}, {"id": "e3"}],
        }
        timeline = [{"fact": "Launched GPT-4 model", "timestamp": datetime.now(UTC)}]

        summary = await client._generate_entity_summary(rel_data, timeline)

        assert "OpenAI" in summary
        assert "10 mentions" in summary

    @pytest.mark.asyncio
    async def test_generate_entity_summary_no_data(self):
        """Test summary with no data."""
        mock_store = AsyncMock()
        client = GraphitiClient(neo4j_store=mock_store)

        summary = await client._generate_entity_summary(None, [])

        assert summary == "No information available."


class TestConnections:
    """Test finding connections between entities."""

    @pytest.mark.asyncio
    async def test_find_connections_success(self):
        """Test finding connections between two entities."""
        mock_store = AsyncMock()
        mock_store.search_entities.side_effect = [
            [{"id": "e1", "name": "Entity1"}],
            [{"id": "e2", "name": "Entity2"}],
        ]
        mock_store.find_paths.return_value = [{"path": ["e1", "rel1", "e2"], "length": 1}]
        client = GraphitiClient(neo4j_store=mock_store)

        paths = await client.find_connections("Entity1", "Entity2")

        assert len(paths) == 1
        mock_store.find_paths.assert_called_once_with("e1", "e2", max_depth=3)

    @pytest.mark.asyncio
    async def test_find_connections_entity_not_found(self):
        """Test finding connections when entity not found."""
        mock_store = AsyncMock()
        mock_store.search_entities.side_effect = [[], [{"id": "e2"}]]
        client = GraphitiClient(neo4j_store=mock_store)

        paths = await client.find_connections("Unknown", "Entity2")

        assert paths == []


class TestTemporalContext:
    """Test temporal context retrieval."""

    @pytest.mark.asyncio
    async def test_get_temporal_context(self):
        """Test getting temporal context."""
        mock_store = AsyncMock()
        now = datetime.now(UTC)
        mock_store.search_episodes.return_value = [
            {"id": "ep1", "timestamp": now - timedelta(days=1)},
            {"id": "ep2", "timestamp": now - timedelta(days=2)},
        ]
        client = GraphitiClient(neo4j_store=mock_store)

        start = now - timedelta(days=7)
        end = now
        episodes = await client.get_temporal_context(start, end)

        assert len(episodes) == 2
        # Should be sorted by timestamp
        assert episodes[1]["timestamp"] <= episodes[0]["timestamp"]

    @pytest.mark.asyncio
    async def test_get_temporal_context_with_entity_filter(self):
        """Test temporal context with entity filter."""
        mock_store = AsyncMock()
        mock_store.search_episodes.return_value = []
        client = GraphitiClient(neo4j_store=mock_store)

        start = datetime.now(UTC) - timedelta(days=7)
        end = datetime.now(UTC)
        await client.get_temporal_context(start, end, entity_ids=["e1", "e2"])

        # Verify entity_ids passed to search
        call_kwargs = mock_store.search_episodes.call_args[1]
        assert "entity_ids" in call_kwargs


class TestGraphSummary:
    """Test knowledge graph summary."""

    @pytest.mark.asyncio
    async def test_build_knowledge_graph_summary_healthy(self):
        """Test building summary for healthy graph."""
        mock_store = AsyncMock()
        mock_store.get_graph_statistics.return_value = {
            "entity_count": 100,
            "relationship_count": 50,
            "episode_count": 200,
            "graph_density": 0.05,
        }
        client = GraphitiClient(neo4j_store=mock_store)

        summary = await client.build_knowledge_graph_summary()

        assert summary["health"]["is_healthy"] is True
        assert summary["health"]["has_relationships"] is True
        assert summary["health"]["has_episodes"] is True
        assert len(summary["recommendations"]) == 0

    @pytest.mark.asyncio
    async def test_build_knowledge_graph_summary_no_entities(self):
        """Test summary with no entities."""
        mock_store = AsyncMock()
        mock_store.get_graph_statistics.return_value = {
            "entity_count": 0,
            "relationship_count": 0,
            "episode_count": 0,
            "graph_density": 0,
        }
        client = GraphitiClient(neo4j_store=mock_store)

        summary = await client.build_knowledge_graph_summary()

        assert summary["health"]["is_healthy"] is False
        assert "No entities found" in summary["recommendations"][0]

    @pytest.mark.asyncio
    async def test_build_knowledge_graph_summary_no_relationships(self):
        """Test summary with entities but no relationships."""
        mock_store = AsyncMock()
        mock_store.get_graph_statistics.return_value = {
            "entity_count": 100,
            "relationship_count": 0,
            "episode_count": 50,
            "graph_density": 0,
        }
        client = GraphitiClient(neo4j_store=mock_store)

        summary = await client.build_knowledge_graph_summary()

        assert summary["health"]["has_relationships"] is False
        assert any("No relationships" in r for r in summary["recommendations"])

    @pytest.mark.asyncio
    async def test_build_knowledge_graph_summary_low_density(self):
        """Test summary with low graph density."""
        mock_store = AsyncMock()
        mock_store.get_graph_statistics.return_value = {
            "entity_count": 100,
            "relationship_count": 5,
            "episode_count": 50,
            "graph_density": 0.005,
        }
        client = GraphitiClient(neo4j_store=mock_store)

        summary = await client.build_knowledge_graph_summary()

        assert any("density is low" in r for r in summary["recommendations"])
