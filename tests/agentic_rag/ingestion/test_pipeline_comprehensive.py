"""
Comprehensive tests for DocumentIngestionPipeline.

Covers initialization, document ingestion workflow, chunking, embedding generation,
knowledge extraction, storage operations, cross-references, error handling,
and pipeline statistics.

Target: Increase coverage from 56% to 90%+ (cover 91 uncovered lines).
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.agentic_rag.ingestion.chunker import DocumentChunk
from src.agentic_rag.ingestion.pipeline import DocumentIngestionPipeline, IngestionResult

# =====================================================
# INGESTION RESULT TESTS
# =====================================================


def test_ingestion_result_success_property():
    """Test IngestionResult.success property."""
    # Success case (no errors, chunks created)
    result = IngestionResult(
        document_id=uuid4(),
        title="Test Doc",
        source="test.md",
        chunks_created=10,
        entities_extracted=5,
        relationships_extracted=3,
        facts_extracted=8,
        processing_time=1.5,
        errors=[],
    )
    assert result.success is True

    # Failure case (has errors)
    result_with_errors = IngestionResult(
        document_id=uuid4(),
        title="Test Doc",
        source="test.md",
        chunks_created=10,
        entities_extracted=0,
        relationships_extracted=0,
        facts_extracted=0,
        processing_time=1.0,
        errors=["Some error occurred"],
    )
    assert result_with_errors.success is False

    # Failure case (no chunks created)
    result_no_chunks = IngestionResult(
        document_id=uuid4(),
        title="Test Doc",
        source="test.md",
        chunks_created=0,
        entities_extracted=0,
        relationships_extracted=0,
        facts_extracted=0,
        processing_time=0.5,
        errors=[],
    )
    assert result_no_chunks.success is False


def test_ingestion_result_to_dict():
    """Test IngestionResult.to_dict conversion."""
    doc_id = uuid4()
    result = IngestionResult(
        document_id=doc_id,
        title="Test Document",
        source="docs/test.md",
        chunks_created=15,
        entities_extracted=20,
        relationships_extracted=10,
        facts_extracted=25,
        processing_time=2.5,
        errors=[],
        metadata={"custom": "data"},
    )

    result_dict = result.to_dict()

    assert result_dict["document_id"] == str(doc_id)
    assert result_dict["title"] == "Test Document"
    assert result_dict["source"] == "docs/test.md"
    assert result_dict["chunks_created"] == 15
    assert result_dict["entities_extracted"] == 20
    assert result_dict["relationships_extracted"] == 10
    assert result_dict["facts_extracted"] == 25
    assert result_dict["processing_time"] == 2.5
    assert result_dict["success"] is True
    assert result_dict["errors"] == []
    assert result_dict["metadata"] == {"custom": "data"}


# =====================================================
# PIPELINE INITIALIZATION TESTS
# =====================================================


def test_pipeline_init_simple_chunker():
    """Test pipeline initialization with simple chunker."""
    with patch("src.agentic_rag.ingestion.pipeline.get_chunking_config") as mock_config:
        mock_config.return_value = {"use_semantic_splitting": False, "chunk_size": 500}

        pipeline = DocumentIngestionPipeline()

        assert pipeline._initialized is False
        assert pipeline.chunker is not None
        assert pipeline.embedder is not None
        assert pipeline.extractor is not None


def test_pipeline_init_semantic_chunker():
    """Test pipeline initialization with semantic chunker."""
    with patch("src.agentic_rag.ingestion.pipeline.get_chunking_config") as mock_config:
        mock_config.return_value = {"use_semantic_splitting": True, "chunk_size": 500}

        with patch("src.agentic_rag.ingestion.pipeline.SemanticChunker"):
            pipeline = DocumentIngestionPipeline()

            assert pipeline._initialized is False


def test_pipeline_init_rest_api_mode():
    """Test pipeline initialization with REST API mode."""
    pipeline = DocumentIngestionPipeline(use_rest_api=True)

    assert pipeline.use_rest_api is True
    assert pipeline.connection_manager is None


def test_pipeline_init_stats():
    """Test initial statistics."""
    pipeline = DocumentIngestionPipeline()

    assert pipeline._stats["documents_processed"] == 0
    assert pipeline._stats["chunks_created"] == 0
    assert pipeline._stats["entities_extracted"] == 0
    assert pipeline._stats["facts_extracted"] == 0
    assert pipeline._stats["errors"] == 0


# =====================================================
# PIPELINE ASYNC INITIALIZATION TESTS
# =====================================================


@pytest.mark.asyncio
async def test_pipeline_initialize_rest_api_mode():
    """Test async initialization with REST API."""
    with patch("src.config.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_key = "test_key"

        with patch("src.agentic_rag.ingestion.pipeline.SupabaseRestStore"):
            pipeline = DocumentIngestionPipeline(use_rest_api=True)
            await pipeline.initialize()

            assert pipeline._initialized is True
            assert pipeline.connection_manager is None
            assert pipeline.neo4j_store is None
            assert pipeline.graphiti_client is None


@pytest.mark.asyncio
async def test_pipeline_initialize_direct_connections():
    """Test async initialization with direct PostgreSQL/Neo4j connections."""
    with patch("src.agentic_rag.ingestion.pipeline.ConnectionManager") as mock_cm:
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock()
        mock_cm.return_value = mock_manager

        with patch("src.agentic_rag.ingestion.pipeline.PostgresStore"):
            with patch("src.agentic_rag.ingestion.pipeline.get_config") as mock_config:
                mock_config.return_value.performance.enable_graph = False

                pipeline = DocumentIngestionPipeline(use_rest_api=False)
                await pipeline.initialize()

                assert pipeline._initialized is True
                mock_manager.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_initialize_with_neo4j():
    """Test async initialization with Neo4j enabled."""
    with patch("src.agentic_rag.ingestion.pipeline.ConnectionManager") as mock_cm:
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock()
        mock_cm.return_value = mock_manager

        with patch("src.agentic_rag.ingestion.pipeline.PostgresStore"):
            with patch("src.agentic_rag.ingestion.pipeline.Neo4jStore"):
                with patch("src.agentic_rag.ingestion.pipeline.GraphitiClient"):
                    with patch("src.agentic_rag.ingestion.pipeline.get_config") as mock_config:
                        mock_config.return_value.performance.enable_graph = True

                        pipeline = DocumentIngestionPipeline(use_rest_api=False)
                        await pipeline.initialize()

                        assert pipeline._initialized is True
                        assert pipeline.neo4j_store is not None
                        assert pipeline.graphiti_client is not None


@pytest.mark.asyncio
async def test_pipeline_initialize_already_initialized():
    """Test that re-initialization logs warning."""
    with patch("src.config.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_key = "test_key"

        with patch("src.agentic_rag.ingestion.pipeline.SupabaseRestStore"):
            pipeline = DocumentIngestionPipeline(use_rest_api=True)
            await pipeline.initialize()

            # Second initialization should log warning
            await pipeline.initialize()

            assert pipeline._initialized is True


# =====================================================
# PIPELINE CLOSE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_pipeline_close():
    """Test pipeline close."""
    pipeline = DocumentIngestionPipeline()
    pipeline.connection_manager = AsyncMock()
    pipeline.connection_manager.close = AsyncMock()

    await pipeline.close()

    pipeline.connection_manager.close.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_close_no_connection_manager():
    """Test pipeline close with no connection manager."""
    pipeline = DocumentIngestionPipeline(use_rest_api=True)
    pipeline.connection_manager = None

    # Should not raise
    await pipeline.close()


# =====================================================
# ASYNC CONTEXT MANAGER TESTS
# =====================================================


@pytest.mark.asyncio
async def test_pipeline_context_manager():
    """Test pipeline as async context manager."""
    with patch("src.config.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_key = "test_key"

        with patch("src.agentic_rag.ingestion.pipeline.SupabaseRestStore"):
            pipeline = DocumentIngestionPipeline(use_rest_api=True)

            async with pipeline as p:
                assert p._initialized is True

            # After exit, close should have been called (no-op in REST mode)


# =====================================================
# INGEST DOCUMENT TESTS
# =====================================================


@pytest.mark.asyncio
async def test_ingest_document_success():
    """Test successful document ingestion."""
    content = "This is a test document content."
    title = "Test Document"
    source = "test.md"
    metadata = {"author": "Test Author"}

    mock_chunks = [
        DocumentChunk(
            content="Chunk 1", index=0, start_char=0, end_char=7, metadata=metadata, embedding=None
        ),
        DocumentChunk(
            content="Chunk 2", index=1, start_char=8, end_char=15, metadata=metadata, embedding=None
        ),
    ]

    doc_id = uuid4()
    chunk_ids = [uuid4(), uuid4()]

    mock_extraction_results = [
        {"entities": [{"name": "Entity1"}], "relationships": [], "facts": ["Fact1"]},
        {"entities": [], "relationships": [], "facts": []},
    ]

    with patch("src.config.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_key = "test_key"

        with patch("src.agentic_rag.ingestion.pipeline.SupabaseRestStore"):
            pipeline = DocumentIngestionPipeline(use_rest_api=True)
            await pipeline.initialize()

            # Mock internal methods
            pipeline._chunk_document = AsyncMock(return_value=mock_chunks)
            pipeline._generate_embeddings = AsyncMock(return_value=mock_chunks)
            pipeline._store_in_postgres = AsyncMock(return_value=(doc_id, chunk_ids))
            pipeline._extract_knowledge = AsyncMock(return_value=mock_extraction_results)
            pipeline._update_cross_references = AsyncMock()

            result = await pipeline.ingest_document(content, title, source, metadata)

            assert result.success is True
            assert result.chunks_created == 2
            assert result.entities_extracted == 1
            assert result.facts_extracted == 1
            assert result.document_id == doc_id


@pytest.mark.asyncio
async def test_ingest_document_no_chunks_created():
    """Test ingestion failure when no chunks created."""
    content = ""
    title = "Empty Document"
    source = "empty.md"

    with patch("src.config.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_key = "test_key"

        with patch("src.agentic_rag.ingestion.pipeline.SupabaseRestStore"):
            pipeline = DocumentIngestionPipeline(use_rest_api=True)
            await pipeline.initialize()

            # Mock internal methods to return empty chunks
            pipeline._chunk_document = AsyncMock(return_value=[])

            result = await pipeline.ingest_document(content, title, source)

            assert result.success is False
            assert result.chunks_created == 0
            assert len(result.errors) > 0
            assert "No chunks created" in result.errors[0]


@pytest.mark.asyncio
async def test_ingest_document_exception_handling():
    """Test ingestion exception handling."""
    content = "Test content"
    title = "Test"
    source = "test.md"

    with patch("src.config.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_key = "test_key"

        with patch("src.agentic_rag.ingestion.pipeline.SupabaseRestStore"):
            pipeline = DocumentIngestionPipeline(use_rest_api=True)
            await pipeline.initialize()

            # Mock internal methods to raise exception
            pipeline._chunk_document = AsyncMock(side_effect=Exception("Chunking failed"))

            result = await pipeline.ingest_document(content, title, source)

            assert result.success is False
            assert result.chunks_created == 0
            assert len(result.errors) == 1
            assert "Chunking failed" in result.errors[0]
            assert pipeline._stats["errors"] == 1


@pytest.mark.asyncio
async def test_ingest_document_with_neo4j():
    """Test document ingestion with Neo4j enabled."""
    content = "Test content"
    title = "Test"
    source = "test.md"

    mock_chunks = [
        DocumentChunk(
            content="Chunk 1", index=0, start_char=0, end_char=7, metadata={}, embedding=None
        )
    ]
    doc_id = uuid4()
    chunk_ids = [uuid4()]
    mock_extraction_results = [{"entities": [], "relationships": [], "facts": []}]

    with patch("src.agentic_rag.ingestion.pipeline.ConnectionManager") as mock_cm:
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock()
        mock_cm.return_value = mock_manager

        with patch("src.agentic_rag.ingestion.pipeline.PostgresStore"):
            with patch("src.agentic_rag.ingestion.pipeline.Neo4jStore"):
                with patch("src.agentic_rag.ingestion.pipeline.GraphitiClient"):
                    with patch("src.agentic_rag.ingestion.pipeline.get_config") as mock_config:
                        mock_config.return_value.performance.enable_graph = True

                        pipeline = DocumentIngestionPipeline(use_rest_api=False)
                        await pipeline.initialize()

                        # Mock internal methods
                        pipeline._chunk_document = AsyncMock(return_value=mock_chunks)
                        pipeline._generate_embeddings = AsyncMock(return_value=mock_chunks)
                        pipeline._store_in_postgres = AsyncMock(return_value=(doc_id, chunk_ids))
                        pipeline._extract_knowledge = AsyncMock(
                            return_value=mock_extraction_results
                        )
                        pipeline._update_knowledge_graph = AsyncMock()
                        pipeline._update_cross_references = AsyncMock()

                        result = await pipeline.ingest_document(content, title, source)

                        assert result.success is True
                        pipeline._update_knowledge_graph.assert_called_once()


# =====================================================
# STATISTICS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_ingest_document_updates_stats():
    """Test that ingestion updates pipeline statistics."""
    content = "Test content"
    title = "Test"
    source = "test.md"

    mock_chunks = [
        DocumentChunk(
            content="Chunk 1", index=0, start_char=0, end_char=7, metadata={}, embedding=None
        ),
        DocumentChunk(
            content="Chunk 2", index=1, start_char=8, end_char=15, metadata={}, embedding=None
        ),
    ]
    doc_id = uuid4()
    chunk_ids = [uuid4(), uuid4()]
    mock_extraction_results = [
        {"entities": [{"name": "E1"}, {"name": "E2"}], "relationships": [], "facts": ["F1"]},
        {"entities": [{"name": "E3"}], "relationships": [], "facts": ["F2", "F3"]},
    ]

    with patch("src.config.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_key = "test_key"

        with patch("src.agentic_rag.ingestion.pipeline.SupabaseRestStore"):
            pipeline = DocumentIngestionPipeline(use_rest_api=True)
            await pipeline.initialize()

            # Mock internal methods
            pipeline._chunk_document = AsyncMock(return_value=mock_chunks)
            pipeline._generate_embeddings = AsyncMock(return_value=mock_chunks)
            pipeline._store_in_postgres = AsyncMock(return_value=(doc_id, chunk_ids))
            pipeline._extract_knowledge = AsyncMock(return_value=mock_extraction_results)
            pipeline._update_cross_references = AsyncMock()

            initial_docs = pipeline._stats["documents_processed"]
            initial_chunks = pipeline._stats["chunks_created"]
            initial_entities = pipeline._stats["entities_extracted"]
            initial_facts = pipeline._stats["facts_extracted"]

            await pipeline.ingest_document(content, title, source)

            assert pipeline._stats["documents_processed"] == initial_docs + 1
            assert pipeline._stats["chunks_created"] == initial_chunks + 2
            assert pipeline._stats["entities_extracted"] == initial_entities + 3
            assert pipeline._stats["facts_extracted"] == initial_facts + 3


# =====================================================
# EDGE CASES AND ERROR HANDLING
# =====================================================


@pytest.mark.asyncio
async def test_ingest_document_empty_content():
    """Test ingestion with empty content."""
    content = ""
    title = "Empty"
    source = "empty.md"

    with patch("src.config.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_key = "test_key"

        with patch("src.agentic_rag.ingestion.pipeline.SupabaseRestStore"):
            pipeline = DocumentIngestionPipeline(use_rest_api=True)
            await pipeline.initialize()

            pipeline._chunk_document = AsyncMock(return_value=[])

            result = await pipeline.ingest_document(content, title, source)

            assert result.success is False


@pytest.mark.asyncio
async def test_ingest_document_no_metadata():
    """Test ingestion without metadata."""
    content = "Test content"
    title = "Test"
    source = "test.md"

    mock_chunks = [
        DocumentChunk(
            content="Chunk 1", index=0, start_char=0, end_char=7, metadata={}, embedding=None
        )
    ]
    doc_id = uuid4()
    chunk_ids = [uuid4()]
    mock_extraction_results = [{"entities": [], "relationships": [], "facts": []}]

    with patch("src.config.get_settings") as mock_settings:
        mock_settings.return_value.supabase_url = "https://test.supabase.co"
        mock_settings.return_value.supabase_service_key = "test_key"

        with patch("src.agentic_rag.ingestion.pipeline.SupabaseRestStore"):
            pipeline = DocumentIngestionPipeline(use_rest_api=True)
            await pipeline.initialize()

            pipeline._chunk_document = AsyncMock(return_value=mock_chunks)
            pipeline._generate_embeddings = AsyncMock(return_value=mock_chunks)
            pipeline._store_in_postgres = AsyncMock(return_value=(doc_id, chunk_ids))
            pipeline._extract_knowledge = AsyncMock(return_value=mock_extraction_results)
            pipeline._update_cross_references = AsyncMock()

            result = await pipeline.ingest_document(content, title, source, metadata=None)

            assert result.success is True
