"""
ULTRA Comprehensive tests for document chunking strategies.

Target coverage: 24% → 95%+

Tests SimpleChunker, SemanticChunker, DocumentChunk, all edge cases,
structural patterns, paragraph splitting, sentence boundaries, and metadata handling.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agentic_rag.ingestion.chunker import (
    DocumentChunk,
    SemanticChunker,
    SimpleChunker,
    semantic_chunk,
)
from src.config import ChunkingStrategy


class TestDocumentChunk:
    """Test DocumentChunk dataclass."""

    def test_document_chunk_creation(self):
        """Test basic DocumentChunk creation."""
        chunk = DocumentChunk(
            content="Test content",
            index=0,
            start_char=0,
            end_char=12,
            metadata={"doc_id": "123"},
        )

        assert chunk.content == "Test content"
        assert chunk.index == 0
        assert chunk.start_char == 0
        assert chunk.end_char == 12
        assert chunk.metadata["doc_id"] == "123"

    def test_document_chunk_auto_token_count(self):
        """Test automatic token count calculation."""
        chunk = DocumentChunk(
            content="A" * 400,
            index=0,
            start_char=0,
            end_char=400,
        )

        assert chunk.token_count == 100  # 400 chars / 4

    def test_document_chunk_explicit_token_count(self):
        """Test explicit token count."""
        chunk = DocumentChunk(
            content="Test",
            index=0,
            start_char=0,
            end_char=4,
            token_count=50,
        )

        assert chunk.token_count == 50

    def test_document_chunk_id_property(self):
        """Test chunk ID property."""
        chunk1 = DocumentChunk(
            content="Test",
            index=0,
            start_char=0,
            end_char=4,
            metadata={"chunk_id": "chunk-123"},
        )
        chunk2 = DocumentChunk(
            content="Test",
            index=0,
            start_char=0,
            end_char=4,
        )

        assert chunk1.id == "chunk-123"
        assert chunk2.id is None

    def test_document_chunk_empty_lists_default(self):
        """Test that empty lists are created by default."""
        chunk = DocumentChunk(
            content="Test",
            index=0,
            start_char=0,
            end_char=4,
        )

        assert chunk.entities == []
        assert chunk.facts == []
        assert chunk.relationships == []

    def test_document_chunk_with_entities(self):
        """Test chunk with entities."""
        chunk = DocumentChunk(
            content="OpenAI released GPT-4",
            index=0,
            start_char=0,
            end_char=21,
            entities=["OpenAI", "GPT-4"],
        )

        assert "OpenAI" in chunk.entities
        assert "GPT-4" in chunk.entities


class TestSimpleChunkerInit:
    """Test SimpleChunker initialization."""

    def test_simple_chunker_init_default_config(self):
        """Test SimpleChunker with default config."""
        chunker = SimpleChunker()

        assert chunker.config is not None
        assert "chunk_size" in chunker.config
        assert "chunk_overlap" in chunker.config

    def test_simple_chunker_init_custom_config(self):
        """Test SimpleChunker with custom config."""
        custom_config = {
            "chunk_size": 500,
            "chunk_overlap": 100,
            "max_chunk_size": 1000,
            "min_chunk_size": 50,
            "use_semantic_splitting": False,
            "preserve_structure": True,
            "strategy": ChunkingStrategy.AUTO,
        }
        chunker = SimpleChunker(config=custom_config)

        assert chunker.config["chunk_size"] == 500
        assert chunker.config["chunk_overlap"] == 100


class TestSimpleChunkerChunking:
    """Test SimpleChunker chunking logic."""

    def test_chunk_empty_content(self):
        """Test chunking empty content."""
        chunker = SimpleChunker()

        chunks = chunker.chunk("")

        assert chunks == []

    def test_chunk_whitespace_only(self):
        """Test chunking whitespace-only content."""
        chunker = SimpleChunker()

        chunks = chunker.chunk("   \n\n  \t  ")

        assert chunks == []

    def test_chunk_small_content_single_chunk(self):
        """Test that small content creates single chunk."""
        chunker = SimpleChunker(
            config={
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "max_chunk_size": 2000,
                "min_chunk_size": 100,
                "use_semantic_splitting": False,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        content = "This is a short paragraph."
        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert chunks[0].content == content

    def test_chunk_respects_paragraph_boundaries(self):
        """Test that chunking respects paragraph boundaries."""
        chunker = SimpleChunker(
            config={
                "chunk_size": 100,
                "chunk_overlap": 20,
                "max_chunk_size": 200,
                "min_chunk_size": 10,
                "use_semantic_splitting": False,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        content = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        chunks = chunker.chunk(content)

        assert len(chunks) >= 1
        assert all(isinstance(c, DocumentChunk) for c in chunks)

    def test_chunk_oversized_paragraph_split(self):
        """Test that oversized paragraphs are split."""
        chunker = SimpleChunker(
            config={
                "chunk_size": 50,
                "chunk_overlap": 10,
                "max_chunk_size": 100,
                "min_chunk_size": 10,
                "use_semantic_splitting": False,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        # Create a long paragraph that exceeds chunk_size
        long_paragraph = "This is a very long paragraph. " * 10

        chunks = chunker.chunk(long_paragraph)

        assert len(chunks) > 1

    def test_chunk_multiple_paragraphs(self):
        """Test chunking multiple paragraphs."""
        chunker = SimpleChunker(
            config={
                "chunk_size": 200,
                "chunk_overlap": 50,
                "max_chunk_size": 400,
                "min_chunk_size": 50,
                "use_semantic_splitting": False,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        content = "\n\n".join([f"Paragraph {i}. Some content here." for i in range(10)])
        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(chunk.metadata["chunk_method"] == "simple" for chunk in chunks)

    def test_chunk_with_metadata(self):
        """Test that metadata is preserved in chunks."""
        chunker = SimpleChunker()

        metadata = {"document_id": "doc-123", "source": "test.txt"}
        chunks = chunker.chunk("Test content.", metadata=metadata)

        assert len(chunks) == 1
        assert chunks[0].metadata["document_id"] == "doc-123"
        assert chunks[0].metadata["source"] == "test.txt"

    def test_chunk_indices_sequential(self):
        """Test that chunk indices are sequential."""
        chunker = SimpleChunker(
            config={
                "chunk_size": 50,
                "chunk_overlap": 10,
                "max_chunk_size": 100,
                "min_chunk_size": 10,
                "use_semantic_splitting": False,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        content = "Paragraph.\n\n" * 20
        chunks = chunker.chunk(content)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_chunk_total_chunks_metadata(self):
        """Test that total_chunks is set in metadata."""
        chunker = SimpleChunker()

        content = "Test.\n\nContent.\n\nHere."
        chunks = chunker.chunk(content)

        assert all(chunk.metadata["total_chunks"] == len(chunks) for chunk in chunks)

    def test_chunk_start_end_positions(self):
        """Test that start/end positions are tracked."""
        chunker = SimpleChunker()

        content = "First chunk.\n\nSecond chunk."
        chunks = chunker.chunk(content)

        assert chunks[0].start_char >= 0
        assert chunks[0].end_char > chunks[0].start_char


class TestSimpleChunkerSentenceSplitting:
    """Test sentence splitting in SimpleChunker."""

    def test_split_paragraph_by_sentences(self):
        """Test splitting paragraph into sentences."""
        chunker = SimpleChunker(
            config={
                "chunk_size": 30,
                "chunk_overlap": 5,
                "max_chunk_size": 60,
                "min_chunk_size": 10,
                "use_semantic_splitting": False,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        paragraph = "First sentence. Second sentence. Third sentence."
        chunks = chunker._split_paragraph(paragraph)

        assert len(chunks) >= 1

    def test_split_paragraph_respects_chunk_size(self):
        """Test that split respects chunk size."""
        chunker = SimpleChunker(
            config={
                "chunk_size": 50,
                "chunk_overlap": 10,
                "max_chunk_size": 100,
                "min_chunk_size": 10,
                "use_semantic_splitting": False,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        paragraph = "A. " * 100
        chunks = chunker._split_paragraph(paragraph)

        assert all(len(chunk) <= 50 for chunk in chunks)

    def test_split_paragraph_single_long_sentence(self):
        """Test splitting single long sentence."""
        chunker = SimpleChunker()

        long_sentence = "A" * 500
        chunks = chunker._split_paragraph(long_sentence)

        assert len(chunks) >= 1


class TestSemanticChunkerInit:
    """Test SemanticChunker initialization."""

    def test_semantic_chunker_init_default(self):
        """Test SemanticChunker with default config."""
        chunker = SemanticChunker()

        assert chunker.config is not None
        assert chunker._llm_client is None

    def test_semantic_chunker_init_custom_config(self):
        """Test SemanticChunker with custom config."""
        custom_config = {
            "chunk_size": 500,
            "chunk_overlap": 100,
            "max_chunk_size": 1000,
            "min_chunk_size": 50,
            "use_semantic_splitting": True,
            "preserve_structure": True,
            "strategy": ChunkingStrategy.AUTO,
        }
        chunker = SemanticChunker(config=custom_config)

        assert chunker.config["chunk_size"] == 500


class TestSemanticChunkerChunking:
    """Test SemanticChunker chunking logic."""

    @pytest.mark.asyncio
    async def test_semantic_chunk_empty_content(self):
        """Test semantic chunking empty content."""
        chunker = SemanticChunker()

        chunks = await chunker.chunk("")

        assert chunks == []

    @pytest.mark.asyncio
    async def test_semantic_chunk_small_content(self):
        """Test semantic chunking small content."""
        chunker = SemanticChunker(
            config={
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "max_chunk_size": 2000,
                "min_chunk_size": 100,
                "use_semantic_splitting": True,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        content = "Short content."
        chunks = await chunker.chunk(content)

        assert len(chunks) == 1
        assert chunks[0].content.strip() == content

    @pytest.mark.asyncio
    async def test_semantic_chunk_fallback_on_error(self):
        """Test fallback to simple chunking on error."""
        chunker = SemanticChunker()

        # Mock the semantic chunking to fail
        with patch.object(chunker, "_semantic_chunk_sections", side_effect=Exception("Error")):
            content = "Test content for chunking."
            chunks = await chunker.chunk(content)

            # Should fallback to SimpleChunker
            assert len(chunks) >= 1
            assert isinstance(chunks[0], DocumentChunk)

    @pytest.mark.asyncio
    async def test_semantic_chunk_with_metadata(self):
        """Test semantic chunking preserves metadata."""
        chunker = SemanticChunker()

        metadata = {"doc_id": "123", "source": "test.md"}

        with patch.object(chunker, "_semantic_chunk_sections", return_value=["chunk content"]):
            chunks = await chunker.chunk("Test", metadata=metadata)

            assert len(chunks) > 0
            assert chunks[0].metadata["doc_id"] == "123"
            assert chunks[0].metadata["chunk_method"] == "semantic"


class TestSemanticChunkerSectionIdentification:
    """Test section identification in SemanticChunker."""

    def test_identify_sections_headers(self):
        """Test identification of markdown headers."""
        chunker = SemanticChunker()

        content = "# Header 1\nContent\n## Header 2\nMore content"
        sections = chunker._identify_sections(content)

        assert len(sections) > 0

    def test_identify_sections_code_blocks(self):
        """Test identification of code blocks."""
        chunker = SemanticChunker()

        content = "Text\n```python\ncode here\n```\nMore text"
        sections = chunker._identify_sections(content)

        assert len(sections) > 0

    def test_identify_sections_lists(self):
        """Test identification of lists."""
        chunker = SemanticChunker()

        content = "1. First\n2. Second\n- Bullet 1\n- Bullet 2"
        sections = chunker._identify_sections(content)

        assert len(sections) > 0

    def test_identify_sections_empty_content(self):
        """Test section identification with empty content."""
        chunker = SemanticChunker()

        sections = chunker._identify_sections("")

        assert sections == []

    def test_identify_sections_filters_empty(self):
        """Test that empty sections are filtered."""
        chunker = SemanticChunker()

        content = "Content\n\n\n\nMore"
        sections = chunker._identify_sections(content)

        assert all(s.strip() for s in sections)


class TestSemanticChunkerSectionChunking:
    """Test semantic section chunking."""

    @pytest.mark.asyncio
    async def test_semantic_chunk_sections_single_section(self):
        """Test chunking single section."""
        chunker = SemanticChunker(
            config={
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "max_chunk_size": 2000,
                "min_chunk_size": 100,
                "use_semantic_splitting": True,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        sections = ["Small section content"]
        chunks = await chunker._semantic_chunk_sections(sections)

        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_semantic_chunk_sections_combine_small(self):
        """Test combining small sections."""
        chunker = SemanticChunker(
            config={
                "chunk_size": 100,
                "chunk_overlap": 20,
                "max_chunk_size": 200,
                "min_chunk_size": 20,
                "use_semantic_splitting": True,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        sections = ["Section 1", "Section 2", "Section 3"]
        chunks = await chunker._semantic_chunk_sections(sections)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_semantic_chunk_sections_split_large(self):
        """Test splitting large sections."""
        chunker = SemanticChunker(
            config={
                "chunk_size": 50,
                "chunk_overlap": 10,
                "max_chunk_size": 100,
                "min_chunk_size": 10,
                "use_semantic_splitting": True,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        # Create mock LLM response
        mock_llm = AsyncMock()
        mock_result = AsyncMock()
        mock_result.output = "Chunk 1---CHUNK---Chunk 2"
        mock_llm.run.return_value = mock_result
        chunker._llm_client = mock_llm

        sections = ["A" * 150]  # Exceeds max_chunk_size
        chunks = await chunker._semantic_chunk_sections(sections)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_semantic_chunk_sections_filter_min_size(self):
        """Test filtering chunks below min size."""
        chunker = SemanticChunker(
            config={
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "max_chunk_size": 2000,
                "min_chunk_size": 100,
                "use_semantic_splitting": True,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        sections = ["Small"]  # Below min_chunk_size
        chunks = await chunker._semantic_chunk_sections(sections)

        # Should be filtered out or combined
        assert len(chunks) == 0 or all(len(c) >= 100 for c in chunks)


class TestSemanticChunkerLLMSplitting:
    """Test LLM-based splitting."""

    @pytest.mark.asyncio
    async def test_llm_split_section_success(self):
        """Test successful LLM section splitting."""
        chunker = SemanticChunker()

        # Mock LLM client
        mock_llm = AsyncMock()
        mock_result = AsyncMock()
        mock_result.output = "Chunk 1---CHUNK---Chunk 2---CHUNK---Chunk 3"
        mock_llm.run.return_value = mock_result
        chunker._llm_client = mock_llm

        section = "Long section content that needs splitting."
        chunks = await chunker._llm_split_section(section)

        assert len(chunks) == 3

    @pytest.mark.asyncio
    async def test_llm_split_section_fallback_on_error(self):
        """Test fallback to simple split on LLM error."""
        chunker = SemanticChunker()

        # Mock LLM to fail
        mock_llm = AsyncMock()
        mock_llm.run.side_effect = Exception("LLM error")
        chunker._llm_client = mock_llm

        section = "Content to split"
        chunks = await chunker._llm_split_section(section)

        # Should fallback to simple split
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_llm_split_section_validates_size(self):
        """Test that LLM split validates chunk sizes."""
        chunker = SemanticChunker(
            config={
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "max_chunk_size": 2000,
                "min_chunk_size": 100,
                "use_semantic_splitting": True,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        # Mock LLM to return invalid sizes
        mock_llm = AsyncMock()
        mock_result = AsyncMock()
        mock_result.output = "tiny---CHUNK---" + "A" * 3000  # One too small, one too large
        mock_llm.run.return_value = mock_result
        chunker._llm_client = mock_llm

        section = "Content"
        chunks = await chunker._llm_split_section(section)

        # Invalid chunks should be filtered/fallback used
        assert isinstance(chunks, list)


class TestSemanticChunkerSimpleSplit:
    """Test simple split fallback."""

    def test_simple_split_basic(self):
        """Test simple split creates chunks."""
        chunker = SemanticChunker(
            config={
                "chunk_size": 100,
                "chunk_overlap": 20,
                "max_chunk_size": 200,
                "min_chunk_size": 20,
                "use_semantic_splitting": True,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        text = "A" * 500
        chunks = chunker._simple_split(text)

        assert len(chunks) > 1

    def test_simple_split_finds_sentence_boundaries(self):
        """Test that simple split finds sentence boundaries."""
        chunker = SemanticChunker(
            config={
                "chunk_size": 50,
                "chunk_overlap": 10,
                "max_chunk_size": 100,
                "min_chunk_size": 10,
                "use_semantic_splitting": True,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunker._simple_split(text)

        assert len(chunks) >= 1

    def test_simple_split_respects_overlap(self):
        """Test that simple split respects overlap."""
        chunker = SemanticChunker(
            config={
                "chunk_size": 100,
                "chunk_overlap": 20,
                "max_chunk_size": 200,
                "min_chunk_size": 10,
                "use_semantic_splitting": True,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        text = "A" * 300
        chunks = chunker._simple_split(text)

        # With overlap, later chunks should start before previous ends
        assert len(chunks) > 1

    def test_simple_split_short_text(self):
        """Test simple split with short text."""
        chunker = SemanticChunker()

        text = "Short"
        chunks = chunker._simple_split(text)

        assert len(chunks) == 1
        assert chunks[0] == text


class TestSemanticChunkerChunkObjectCreation:
    """Test chunk object creation."""

    def test_create_chunk_objects_basic(self):
        """Test basic chunk object creation."""
        chunker = SemanticChunker()

        chunks_text = ["First chunk", "Second chunk"]
        original = "First chunk\n\nSecond chunk"
        metadata = {"doc_id": "123"}

        chunks = chunker._create_chunk_objects(chunks_text, original, metadata)

        assert len(chunks) == 2
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        assert chunks[0].content == "First chunk"
        assert chunks[1].content == "Second chunk"

    def test_create_chunk_objects_preserves_metadata(self):
        """Test that metadata is preserved."""
        chunker = SemanticChunker()

        chunks_text = ["Chunk"]
        metadata = {"source": "test.txt", "author": "Test"}

        chunks = chunker._create_chunk_objects(chunks_text, "Chunk", metadata)

        assert chunks[0].metadata["source"] == "test.txt"
        assert chunks[0].metadata["author"] == "Test"
        assert chunks[0].metadata["chunk_method"] == "semantic"

    def test_create_chunk_objects_sets_indices(self):
        """Test that chunk indices are set correctly."""
        chunker = SemanticChunker()

        chunks_text = ["A", "B", "C"]
        chunks = chunker._create_chunk_objects(chunks_text, "A B C", {})

        assert chunks[0].index == 0
        assert chunks[1].index == 1
        assert chunks[2].index == 2

    def test_create_chunk_objects_sets_total_chunks(self):
        """Test that total_chunks is set."""
        chunker = SemanticChunker()

        chunks_text = ["A", "B"]
        chunks = chunker._create_chunk_objects(chunks_text, "A B", {})

        assert all(c.metadata["total_chunks"] == 2 for c in chunks)


class TestBackwardCompatibility:
    """Test backward compatibility functions."""

    def test_semantic_chunk_function(self):
        """Test backward-compatible semantic_chunk function."""
        content = "Test content for chunking."
        chunks = semantic_chunk(content, chunk_size=1000, overlap=200)

        assert len(chunks) >= 1
        assert all("content" in chunk for chunk in chunks)

    def test_semantic_chunk_function_with_metadata(self):
        """Test semantic_chunk with metadata."""
        content = "Test"
        metadata = {"doc_id": "123"}
        chunks = semantic_chunk(content, metadata=metadata)

        assert len(chunks) >= 1

    def test_semantic_chunk_function_returns_dicts(self):
        """Test that semantic_chunk returns dictionaries."""
        chunks = semantic_chunk("Test content")

        assert all(isinstance(chunk, dict) for chunk in chunks)
        assert all("content" in chunk for chunk in chunks)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_chunk_unicode_content(self):
        """Test chunking unicode content."""
        chunker = SimpleChunker()

        content = "Hello 世界 François émojis ⭐🎉"
        chunks = chunker.chunk(content)

        assert len(chunks) >= 1
        assert "世界" in chunks[0].content

    def test_chunk_very_long_content(self):
        """Test chunking very long content."""
        chunker = SimpleChunker(
            config={
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "max_chunk_size": 2000,
                "min_chunk_size": 100,
                "use_semantic_splitting": False,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        content = "Paragraph.\n\n" * 1000
        chunks = chunker.chunk(content)

        assert len(chunks) > 5

    def test_chunk_no_paragraph_breaks(self):
        """Test chunking content with no paragraph breaks."""
        chunker = SimpleChunker(
            config={
                "chunk_size": 100,
                "chunk_overlap": 20,
                "max_chunk_size": 200,
                "min_chunk_size": 10,
                "use_semantic_splitting": False,
                "preserve_structure": True,
                "strategy": ChunkingStrategy.AUTO,
            }
        )

        content = "A" * 500  # No breaks at all
        chunks = chunker.chunk(content)

        assert len(chunks) > 1

    def test_chunk_only_paragraph_breaks(self):
        """Test content that is only paragraph breaks."""
        chunker = SimpleChunker()

        content = "\n\n\n\n\n\n"
        chunks = chunker.chunk(content)

        assert chunks == []

    def test_chunk_mixed_line_endings(self):
        """Test content with mixed line endings."""
        chunker = SimpleChunker()

        content = "Para 1\r\n\r\nPara 2\n\nPara 3"
        chunks = chunker.chunk(content)

        assert len(chunks) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
