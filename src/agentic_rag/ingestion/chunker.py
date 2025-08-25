"""
Document chunking strategies for intelligent text splitting.

Provides both semantic (LLM-powered) and simple (rule-based) chunking approaches.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..config import get_config

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Available chunking strategies."""

    SEMANTIC = "semantic"
    SIMPLE = "simple"
    AUTO = "auto"


@dataclass
class ChunkingConfig:
    """Configuration for document chunking."""

    chunk_size: int = field(default_factory=lambda: get_config().ingestion.chunk_size)
    chunk_overlap: int = field(default_factory=lambda: get_config().ingestion.chunk_overlap)
    max_chunk_size: int = 2000
    min_chunk_size: int = 100
    use_semantic_splitting: bool = field(
        default_factory=lambda: get_config().ingestion.use_semantic_chunking
    )
    preserve_structure: bool = True
    strategy: ChunkingStrategy = ChunkingStrategy.AUTO

    def __post_init__(self):
        """Validate configuration."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        if self.min_chunk_size <= 0:
            raise ValueError("Minimum chunk size must be positive")
        if self.max_chunk_size < self.chunk_size:
            self.max_chunk_size = self.chunk_size * 2


@dataclass
class DocumentChunk:
    """Represents a single document chunk."""

    content: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)
    token_count: int | None = None
    embedding: list[float] | None = None
    entities: list[Any] = field(default_factory=list)
    facts: list[Any] = field(default_factory=list)
    relationships: list[Any] = field(default_factory=list)

    def __post_init__(self):
        """Calculate token count if not provided."""
        if self.token_count is None:
            # Rough estimation: ~4 characters per token
            self.token_count = len(self.content) // 4

    @property
    def id(self) -> str | None:
        """Get chunk ID if stored."""
        return self.metadata.get("chunk_id")


class SemanticChunker:
    """
    LLM-powered semantic chunking for intelligent document splitting.

    Uses language models to identify semantic boundaries and create
    coherent chunks that preserve context and meaning.
    """

    def __init__(self, config: ChunkingConfig):
        """
        Initialize semantic chunker.

        Args:
            config: Chunking configuration
        """
        self.config = config
        self._llm_client = None

    @property
    def llm_client(self):
        """Lazy load LLM client."""
        if self._llm_client is None:
            from pydantic_ai import Agent

            llm_config = get_config().llm
            self._llm_client = Agent(
                model=f"{llm_config.provider}:{llm_config.extraction_model}",
                api_key=llm_config.api_key,
            )
        return self._llm_client

    async def chunk(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> list[DocumentChunk]:
        """
        Chunk document using semantic boundaries.

        Args:
            content: Document content to chunk
            metadata: Optional metadata for chunks

        Returns:
            List of document chunks
        """
        if not content.strip():
            return []

        # Check if semantic chunking is appropriate
        if len(content) <= self.config.chunk_size:
            # Single chunk for small documents
            return [
                DocumentChunk(
                    content=content.strip(),
                    index=0,
                    start_char=0,
                    end_char=len(content),
                    metadata=metadata or {},
                )
            ]

        try:
            # Identify structural sections
            sections = self._identify_sections(content)

            # Use LLM to find semantic boundaries
            chunks = await self._semantic_chunk_sections(sections)

            # Create chunk objects
            return self._create_chunk_objects(chunks, content, metadata)

        except Exception as e:
            logger.warning(f"Semantic chunking failed, falling back to simple: {e}")
            # Fallback to simple chunking
            simple_chunker = SimpleChunker(self.config)
            return simple_chunker.chunk(content, metadata)

    def _identify_sections(self, content: str) -> list[str]:
        """
        Identify structural sections in the document.

        Args:
            content: Document content

        Returns:
            List of sections
        """
        # Patterns for structural elements
        patterns = [
            (r"^#{1,6}\s+.+$", "header"),  # Markdown headers
            (r"^\d+\.\s+.+$", "numbered_list"),  # Numbered lists
            (r"^[-*+]\s+.+$", "bullet_list"),  # Bullet lists
            (r"^```[\s\S]*?```$", "code_block"),  # Code blocks
            (r"^\|.+\|$", "table_row"),  # Table rows
        ]

        lines = content.split("\n")
        sections = []
        current_section = []
        current_type = "paragraph"

        for line in lines:
            # Check if line matches any pattern
            line_type = "paragraph"
            for pattern, ptype in patterns:
                if re.match(pattern, line, re.MULTILINE):
                    line_type = ptype
                    break

            # Handle section transitions
            if line_type != current_type and current_section:
                sections.append("\n".join(current_section))
                current_section = [line]
                current_type = line_type
            else:
                current_section.append(line)

        # Add final section
        if current_section:
            sections.append("\n".join(current_section))

        return [s for s in sections if s.strip()]

    async def _semantic_chunk_sections(self, sections: list[str]) -> list[str]:
        """
        Group sections into semantic chunks using LLM.

        Args:
            sections: List of document sections

        Returns:
            List of semantic chunks
        """
        chunks = []
        current_chunk = ""

        for section in sections:
            # Check if adding section exceeds size limit
            potential_chunk = f"{current_chunk}\n\n{section}" if current_chunk else section

            if len(potential_chunk) <= self.config.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # Handle oversized sections
                if len(section) > self.config.max_chunk_size:
                    # Split using LLM
                    sub_chunks = await self._llm_split_section(section)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = section

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        # Filter by minimum size
        return [c for c in chunks if len(c) >= self.config.min_chunk_size]

    async def _llm_split_section(self, section: str) -> list[str]:
        """
        Split a long section using LLM for semantic boundaries.

        Args:
            section: Section to split

        Returns:
            List of sub-chunks
        """
        try:
            prompt = f"""
            Split the following text into semantically coherent chunks.
            Each chunk should:
            1. Be roughly {self.config.chunk_size} characters
            2. End at natural semantic boundaries
            3. Maintain context and readability
            4. Not exceed {self.config.max_chunk_size} characters

            Return ONLY the split text with "---CHUNK---" between chunks.

            Text:
            {section}
            """

            response = await self.llm_client.run(prompt)
            chunks = [c.strip() for c in response.data.split("---CHUNK---")]

            # Validate chunk sizes
            valid_chunks = []
            for chunk in chunks:
                if self.config.min_chunk_size <= len(chunk) <= self.config.max_chunk_size:
                    valid_chunks.append(chunk)

            return valid_chunks if valid_chunks else self._simple_split(section)

        except Exception as e:
            logger.error(f"LLM splitting failed: {e}")
            return self._simple_split(section)

    def _simple_split(self, text: str) -> list[str]:
        """
        Simple fallback splitting by sentence boundaries.

        Args:
            text: Text to split

        Returns:
            List of chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.config.chunk_size, len(text))

            if end >= len(text):
                chunks.append(text[start:])
                break

            # Find sentence boundary
            for i in range(end, max(start + self.config.min_chunk_size, end - 200), -1):
                if text[i] in ".!?\n":
                    end = i + 1
                    break

            chunks.append(text[start:end])
            start = end - self.config.chunk_overlap

        return chunks

    def _create_chunk_objects(
        self, chunks: list[str], original_content: str, metadata: dict[str, Any] | None
    ) -> list[DocumentChunk]:
        """
        Create DocumentChunk objects from text chunks.

        Args:
            chunks: List of text chunks
            original_content: Original document content
            metadata: Chunk metadata

        Returns:
            List of DocumentChunk objects
        """
        chunk_objects = []
        current_pos = 0

        for i, chunk_text in enumerate(chunks):
            # Find position in original content
            start_pos = original_content.find(chunk_text, current_pos)
            if start_pos == -1:
                start_pos = current_pos

            end_pos = start_pos + len(chunk_text)

            # Create chunk metadata
            chunk_metadata = {
                **(metadata or {}),
                "chunk_method": "semantic",
                "chunk_index": i,
                "total_chunks": len(chunks),
            }

            chunk_objects.append(
                DocumentChunk(
                    content=chunk_text.strip(),
                    index=i,
                    start_char=start_pos,
                    end_char=end_pos,
                    metadata=chunk_metadata,
                )
            )

            current_pos = end_pos - self.config.chunk_overlap

        return chunk_objects


class SimpleChunker:
    """
    Rule-based chunking for fast, deterministic text splitting.

    Splits text based on paragraph boundaries, sentence endings,
    and size constraints without using language models.
    """

    def __init__(self, config: ChunkingConfig):
        """
        Initialize simple chunker.

        Args:
            config: Chunking configuration
        """
        self.config = config

    def chunk(self, content: str, metadata: dict[str, Any] | None = None) -> list[DocumentChunk]:
        """
        Chunk document using simple rules.

        Args:
            content: Document content to chunk
            metadata: Optional metadata for chunks

        Returns:
            List of document chunks
        """
        if not content.strip():
            return []

        # Split on paragraphs
        paragraphs = re.split(r"\n\s*\n", content)

        chunks = []
        current_chunk = ""
        current_pos = 0
        chunk_index = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Check if adding paragraph exceeds size
            potential_chunk = f"{current_chunk}\n\n{paragraph}" if current_chunk else paragraph

            if len(potential_chunk) <= self.config.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(
                        self._create_chunk(
                            current_chunk,
                            chunk_index,
                            current_pos,
                            current_pos + len(current_chunk),
                            metadata,
                        )
                    )

                    # Update position with overlap
                    overlap_start = max(0, len(current_chunk) - self.config.chunk_overlap)
                    current_pos += overlap_start
                    chunk_index += 1

                # Handle oversized paragraphs
                if len(paragraph) > self.config.chunk_size:
                    # Split paragraph
                    para_chunks = self._split_paragraph(paragraph)
                    for pc in para_chunks:
                        chunks.append(
                            self._create_chunk(
                                pc, chunk_index, current_pos, current_pos + len(pc), metadata
                            )
                        )
                        current_pos += max(0, len(pc) - self.config.chunk_overlap)
                        chunk_index += 1
                    current_chunk = ""
                else:
                    current_chunk = paragraph

        # Add final chunk
        if current_chunk:
            chunks.append(
                self._create_chunk(
                    current_chunk,
                    chunk_index,
                    current_pos,
                    current_pos + len(current_chunk),
                    metadata,
                )
            )

        # Update total chunks in metadata
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)

        return chunks

    def _split_paragraph(self, paragraph: str) -> list[str]:
        """
        Split a long paragraph into chunks.

        Args:
            paragraph: Paragraph to split

        Returns:
            List of paragraph chunks
        """
        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            potential_chunk = f"{current_chunk} {sentence}" if current_chunk else sentence

            if len(potential_chunk) <= self.config.chunk_size:
                current_chunk = potential_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        metadata: dict[str, Any] | None,
    ) -> DocumentChunk:
        """
        Create a DocumentChunk object.

        Args:
            content: Chunk content
            index: Chunk index
            start_pos: Start position in document
            end_pos: End position in document
            metadata: Chunk metadata

        Returns:
            DocumentChunk object
        """
        chunk_metadata = {**(metadata or {}), "chunk_method": "simple", "chunk_index": index}

        return DocumentChunk(
            content=content.strip(),
            index=index,
            start_char=start_pos,
            end_char=end_pos,
            metadata=chunk_metadata,
        )
