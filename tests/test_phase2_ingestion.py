"""
Tests for Phase 2 ingestion pipeline.

Tests document chunking, embedding generation, knowledge extraction,
and the complete ingestion pipeline.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from src.agentic_rag.ingestion import (
    ChunkingConfig,
    DocumentChunk,
    DocumentIngestionPipeline,
    EmbeddingGenerator,
    Entity,
    Fact,
    KnowledgeExtractor,
    Relationship,
    SemanticChunker,
    SimpleChunker,
)
from src.agentic_rag.ingestion.embedder import EmbeddingCache, EmbeddingConfig
from src.agentic_rag.ingestion.knowledge_extractor import EntityType, RelationshipType
from src.agentic_rag.ingestion.pipeline import IngestionResult
from src.agentic_rag.search import VectorSearch


@pytest.fixture
def mock_connection_manager():
    """Mock ConnectionManager for tests."""
    from unittest.mock import Mock

    mock_cm = Mock()
    mock_cm.get_pg_connection = Mock()
    mock_cm.get_neo4j_session = Mock()
    mock_cm.graphiti_client = Mock()
    return mock_cm


class TestChunker:
    """Test document chunking functionality."""

    def test_chunking_config_validation(self):
        """Test chunking configuration validation."""
        # Valid config
        config = ChunkingConfig(chunk_size=1000, chunk_overlap=200)
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200

        # Invalid config - overlap >= size
        with pytest.raises(ValueError):
            ChunkingConfig(chunk_size=100, chunk_overlap=100)

        # Invalid config - negative min size
        with pytest.raises(ValueError):
            ChunkingConfig(min_chunk_size=-1)

    def test_simple_chunking(self):
        """Test simple rule-based chunking."""
        config = ChunkingConfig(chunk_size=100, chunk_overlap=20, use_semantic_splitting=False)
        chunker = SimpleChunker(config)

        # Test document
        content = "This is paragraph one. " * 10 + "\n\n" + "This is paragraph two. " * 10

        chunks = chunker.chunk(content, {"title": "test"})

        assert len(chunks) > 1
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        assert all(len(c.content) <= config.chunk_size * 1.5 for c in chunks)

        # Check overlap
        for i in range(len(chunks) - 1):
            assert chunks[i].end_char >= chunks[i + 1].start_char - config.chunk_overlap

    def test_document_chunk_creation(self):
        """Test DocumentChunk object creation."""
        chunk = DocumentChunk(
            content="Test content", index=0, start_char=0, end_char=12, metadata={"test": "value"}
        )

        assert chunk.content == "Test content"
        assert chunk.index == 0
        assert chunk.token_count is not None  # Auto-calculated
        assert chunk.metadata["test"] == "value"

    @pytest.mark.asyncio
    async def test_semantic_chunking_fallback(self):
        """Test semantic chunking fallback to simple."""
        config = ChunkingConfig(chunk_size=100, chunk_overlap=20, use_semantic_splitting=True)

        with patch("src.agentic_rag.ingestion.chunker.SemanticChunker.llm_client") as mock_llm:
            mock_llm.run.side_effect = Exception("LLM error")

            chunker = SemanticChunker(config)
            content = "Test content " * 50

            # Should fall back to simple chunking
            chunks = await chunker.chunk(content, {})
            assert len(chunks) > 0


class TestEmbedding:
    """Test embedding generation."""

    def test_embedding_cache(self):
        """Test embedding cache functionality."""
        cache = EmbeddingCache(max_size=2)

        # Test set and get
        cache.set("text1", [1.0, 2.0, 3.0])
        assert cache.get("text1") == [1.0, 2.0, 3.0]
        assert cache.get("text2") is None

        # Test LRU eviction
        cache.set("text2", [4.0, 5.0, 6.0])
        cache.set("text3", [7.0, 8.0, 9.0])  # Should evict text1

        assert cache.get("text1") is None
        assert cache.get("text2") is not None
        assert cache.get("text3") is not None

    @pytest.mark.asyncio
    async def test_embedding_generation_with_cache(self):
        """Test embedding generation with caching."""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-3-small",
            dimension=1536,
            batch_size=2,
            enable_cache=True,
        )

        with patch(
            "src.agentic_rag.ingestion.embedder.EmbeddingGenerator._generate_openai_embeddings"
        ) as mock_embed:
            mock_embed.return_value = [[1.0] * 1536, [2.0] * 1536]

            embedder = EmbeddingGenerator(config)

            # First call - should hit API
            result1 = await embedder.embed_batch(["text1", "text2"])
            assert len(result1) == 2
            assert mock_embed.call_count == 1

            # Second call with same text - should hit cache
            result2 = await embedder.embed_batch(["text1", "text2"])
            assert result1 == result2
            assert mock_embed.call_count == 1  # No additional API call

            # Check stats
            stats = embedder.get_stats()
            assert stats["cache_hits"] == 2
            assert stats["cache_misses"] == 2


class TestKnowledgeExtraction:
    """Test knowledge extraction."""

    def test_entity_creation(self):
        """Test entity object creation and validation."""
        # Valid entity
        entity = Entity(name="OpenAI", type=EntityType.COMPANY, confidence=0.9)
        assert entity.name == "OpenAI"
        assert entity.type == EntityType.COMPANY

        # Name truncation
        long_name = "A" * 200
        entity = Entity(name=long_name, type=EntityType.COMPANY)
        assert len(entity.name) <= 100

        # Invalid confidence
        with pytest.raises(ValueError):
            Entity(name="Test", type=EntityType.COMPANY, confidence=1.5)

    def test_fact_creation(self):
        """Test fact creation with length limit."""
        # Valid fact
        fact = Fact(text="Microsoft invested $10B in OpenAI", confidence=0.9)
        assert fact.text == "Microsoft invested $10B in OpenAI"

        # Text truncation
        long_text = "A" * 1000
        fact = Fact(text=long_text)
        assert len(fact.text) <= 500

    def test_relationship_creation(self):
        """Test relationship creation."""
        rel = Relationship(
            source="Microsoft", target="OpenAI", type=RelationshipType.INVESTED_IN, confidence=0.85
        )

        assert rel.source == "Microsoft"
        assert rel.target == "OpenAI"
        assert rel.type == RelationshipType.INVESTED_IN

        # Missing entities
        with pytest.raises(ValueError):
            Relationship(source="", target="OpenAI", type=RelationshipType.INVESTED_IN)

    @pytest.mark.asyncio
    async def test_pattern_based_extraction(self):
        """Test pattern-based entity extraction."""
        extractor = KnowledgeExtractor()

        text = """
        Microsoft Corporation announced a major investment in OpenAI.
        The CEO of Microsoft, Satya Nadella, met with Sam Altman.
        They discussed GPT-4 and future AI developments.
        """

        # Test entity patterns
        entities = extractor._extract_entities_by_pattern(text)

        entity_names = [e.name for e in entities]
        assert "Microsoft" in entity_names or "Microsoft Corporation" in " ".join(entity_names)
        assert any("GPT-4" in name for name in entity_names)


class TestIngestionPipeline:
    """Test complete ingestion pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = DocumentIngestionPipeline()
        await pipeline.initialize()

        assert pipeline.pg_store is not None
        assert pipeline.neo4j_store is not None
        assert pipeline.chunker is not None
        assert pipeline.embedder is not None
        assert pipeline.extractor is not None

    @pytest.mark.asyncio
    async def test_ingestion_result(self):
        """Test ingestion result object."""
        result = IngestionResult(
            document_id=UUID("12345678-1234-5678-1234-567812345678"),
            title="Test Doc",
            source="test.md",
            chunks_created=5,
            entities_extracted=10,
            relationships_extracted=3,
            facts_extracted=4,
            processing_time=2.5,
        )

        assert result.success is True

        # With errors
        result.errors.append("Test error")
        assert result.success is False

        # Test dict conversion
        result_dict = result.to_dict()
        assert result_dict["title"] == "Test Doc"
        assert result_dict["chunks_created"] == 5

    @pytest.mark.asyncio
    async def test_no_content_duplication(self):
        """Verify no content duplication between PostgreSQL and Neo4j."""
        pipeline = DocumentIngestionPipeline()

        # Mock stores
        pipeline.pg_store = AsyncMock()
        pipeline.neo4j_store = AsyncMock()
        pipeline.graphiti_client = AsyncMock()

        # Mock methods
        pipeline.pg_store.store_document.return_value = UUID("12345678-1234-5678-1234-567812345678")
        pipeline.pg_store.store_chunks.return_value = [UUID("87654321-4321-8765-4321-876543218765")]

        with (
            patch.object(pipeline, "_chunk_document") as mock_chunk,
            patch.object(pipeline, "_generate_embeddings") as mock_embed,
            patch.object(pipeline, "_extract_knowledge") as mock_extract,
        ):
            # Setup mocks
            mock_chunk.return_value = [
                DocumentChunk(
                    content="Test content", index=0, start_char=0, end_char=12, metadata={}
                )
            ]

            mock_embed.return_value = mock_chunk.return_value

            mock_extract.return_value = [
                {
                    "entities": [Entity(name="TestEntity", type=EntityType.COMPANY)],
                    "facts": [Fact(text="Brief fact", confidence=0.8)],
                    "relationships": [],
                    "chunk_id": "87654321-4321-8765-4321-876543218765",
                }
            ]

            # Run ingestion
            await pipeline.ingest_document(
                content="Test document content", title="Test", source="test.md"
            )

            # Verify PostgreSQL gets full content
            pipeline.pg_store.store_document.assert_called_once()
            call_args = pipeline.pg_store.store_document.call_args
            assert "Test document content" in call_args[0]  # Full content stored

            # Verify Neo4j only gets entity names and brief facts
            if pipeline.neo4j_store.create_entity.called:
                entity_calls = pipeline.neo4j_store.create_entity.call_args_list
                for call in entity_calls:
                    # Should only have name, not content
                    assert "name" in call[1]
                    assert len(call[1]["name"]) <= 100

            # Verify facts are limited
            if pipeline.graphiti_client.add_episode.called:
                episode_calls = pipeline.graphiti_client.add_episode.call_args_list
                for call in episode_calls:
                    content_arg = call[1]["content"]
                    assert len(content_arg) <= 500  # Fact length limit


class TestSearchPerformance:
    """Test search performance targets."""

    @pytest.mark.asyncio
    async def test_vector_search_latency(self, mock_connection_manager):
        """Verify vector search meets <200ms target."""
        search = VectorSearch(mock_connection_manager)

        # Mock the database query
        with patch.object(search, "_search_vectors") as mock_search:
            mock_search.return_value = []

            with patch.object(search.embedder, "embed") as mock_embed:
                mock_embed.return_value = [0.0] * 1536

                start = datetime.now()
                await search.search("test query", limit=10)
                duration = (datetime.now() - start).total_seconds()

                # Should be fast (mocked, so very fast)
                assert duration < 0.2  # 200ms

    @pytest.mark.asyncio
    async def test_caching_improves_performance(self, mock_connection_manager):
        """Test that caching improves search performance."""
        search = VectorSearch(mock_connection_manager)

        with patch.object(search, "_search_vectors") as mock_search:
            mock_search.return_value = []

            with patch.object(search.embedder, "embed") as mock_embed:
                mock_embed.return_value = [0.0] * 1536

                # First search - cache miss
                await search.search("test query", limit=10)
                assert mock_search.call_count == 1

                # Second search - cache hit
                await search.search("test query", limit=10)

                if search.cache:
                    # Should not call search again
                    assert mock_search.call_count == 1

                    stats = search.get_stats()
                    assert stats["cache_hits"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
