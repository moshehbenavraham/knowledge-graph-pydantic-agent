"""
Main document ingestion pipeline orchestrator.

Coordinates chunking, embedding, knowledge extraction, and storage
across PostgreSQL and Neo4j while maintaining zero content duplication.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from ..config import get_config
from ..storage.connection_manager import ConnectionManager
from ..storage.graphiti_client import GraphitiClient
from ..storage.neo4j_store import Neo4jStore
from ..storage.postgres_store import PostgresStore
from ..storage.supabase_rest_store import SupabaseRestStore
from .chunker import DocumentChunk, SemanticChunker, SimpleChunker, get_chunking_config
from .embedder import EmbeddingGenerator, get_embedding_config
from .knowledge_extractor import KnowledgeExtractor

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of document ingestion."""

    document_id: UUID
    title: str
    source: str
    chunks_created: int
    entities_extracted: int
    relationships_extracted: int
    facts_extracted: int
    processing_time: float
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if ingestion was successful."""
        return len(self.errors) == 0 and self.chunks_created > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": str(self.document_id),
            "title": self.title,
            "source": self.source,
            "chunks_created": self.chunks_created,
            "entities_extracted": self.entities_extracted,
            "relationships_extracted": self.relationships_extracted,
            "facts_extracted": self.facts_extracted,
            "processing_time": self.processing_time,
            "success": self.success,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class DocumentIngestionPipeline:
    """
    Orchestrates the complete document ingestion process.

    Key responsibilities:
    - Document discovery and reading
    - Chunking coordination
    - Embedding generation
    - Knowledge extraction
    - Dual-database storage
    - Error handling and recovery
    """

    def __init__(self, config: dict[str, Any] | None = None, use_rest_api: bool = False):
        """
        Initialize ingestion pipeline.

        Args:
            config: Optional configuration overrides
            use_rest_api: Force use of REST API instead of direct PostgreSQL
        """
        self.config = get_config()
        self.use_rest_api = use_rest_api

        # Initialize storage - use REST API if forced or if PostgreSQL unavailable
        if use_rest_api:
            logger.info("Using Supabase REST API for storage (forced)")
            from src.config import get_settings

            settings = get_settings()
            self.pg_store = SupabaseRestStore(settings.supabase_url, settings.supabase_service_key)
            self.connection_manager = None
        else:
            logger.info("Initializing direct PostgreSQL connection")
            self.connection_manager = ConnectionManager()
            self.pg_store = PostgresStore(self.connection_manager)

        # Initialize Neo4j if enabled (skip for REST-only mode)
        if not use_rest_api and self.config.performance.enable_graph:
            self.neo4j_store = Neo4jStore(self.connection_manager)
            self.graphiti_client = GraphitiClient(self.neo4j_store)
        else:
            if use_rest_api:
                logger.info("Skipping Neo4j initialization (REST API mode)")
            self.neo4j_store = None
            self.graphiti_client = None

        # Configure chunking
        self.chunking_config = get_chunking_config()
        if self.chunking_config.get("use_semantic_splitting"):
            self.chunker = SemanticChunker(self.chunking_config)
        else:
            self.chunker = SimpleChunker(self.chunking_config)

        # Configure embedding
        self.embedder = EmbeddingGenerator(get_embedding_config())

        # Configure extraction
        self.extractor = KnowledgeExtractor()

        # Statistics
        self._stats = {
            "documents_processed": 0,
            "chunks_created": 0,
            "entities_extracted": 0,
            "facts_extracted": 0,
            "errors": 0,
        }

    async def ingest_document(
        self, content: str, title: str, source: str, metadata: dict[str, Any] | None = None
    ) -> IngestionResult:
        """
        Main ingestion workflow.

        Steps:
        1. Chunk document based on strategy
        2. Generate embeddings for chunks
        3. Extract entities and facts
        4. Store in PostgreSQL
        5. Update knowledge graph
        6. Maintain cross-references

        Args:
            content: Document content
            title: Document title
            source: Document source/filename
            metadata: Additional metadata

        Returns:
            IngestionResult with processing details
        """
        start_time = datetime.now()
        errors = []

        try:
            logger.info(f"Starting ingestion for document: {title}")

            # Step 1: Chunk document
            logger.debug("Chunking document...")
            chunks = await self._chunk_document(content, title, source, metadata)

            if not chunks:
                raise ValueError("No chunks created from document")

            logger.info(f"Created {len(chunks)} chunks")

            # Step 2: Generate embeddings
            logger.debug("Generating embeddings...")
            chunks = await self._generate_embeddings(chunks)

            # Step 3: Store document and chunks in PostgreSQL
            logger.debug("Storing in PostgreSQL...")
            doc_id, chunk_ids = await self._store_in_postgres(
                title, source, content, chunks, metadata
            )

            # Step 4: Extract knowledge from chunks
            logger.debug("Extracting knowledge...")
            extraction_results = await self._extract_knowledge(chunks, chunk_ids)

            # Step 5: Store knowledge in Neo4j (if enabled and available)
            if self.config.performance.enable_graph and self.neo4j_store is not None:
                logger.debug("Updating knowledge graph...")
                await self._update_knowledge_graph(extraction_results, doc_id, chunk_ids)
            elif self.use_rest_api:
                logger.debug("Skipping knowledge graph update (REST API mode)")

            # Step 6: Update cross-references
            logger.debug("Updating cross-references...")
            await self._update_cross_references(chunk_ids, extraction_results)

            # Calculate statistics
            total_entities = sum(len(r["entities"]) for r in extraction_results)
            total_relationships = sum(len(r["relationships"]) for r in extraction_results)
            total_facts = sum(len(r["facts"]) for r in extraction_results)

            # Update global stats
            self._stats["documents_processed"] += 1
            self._stats["chunks_created"] += len(chunks)
            self._stats["entities_extracted"] += total_entities
            self._stats["facts_extracted"] += total_facts

            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Successfully ingested document {doc_id}: "
                f"{len(chunks)} chunks, {total_entities} entities, "
                f"{total_facts} facts in {processing_time:.2f}s"
            )

            return IngestionResult(
                document_id=doc_id,
                title=title,
                source=source,
                chunks_created=len(chunks),
                entities_extracted=total_entities,
                relationships_extracted=total_relationships,
                facts_extracted=total_facts,
                processing_time=processing_time,
                errors=errors,
                metadata={"chunk_ids": [str(cid) for cid in chunk_ids]},
            )

        except Exception as e:
            logger.error(f"Ingestion failed for {title}: {e}")
            self._stats["errors"] += 1
            errors.append(str(e))

            # Return partial result
            return IngestionResult(
                document_id=UUID("00000000-0000-0000-0000-000000000000"),
                title=title,
                source=source,
                chunks_created=0,
                entities_extracted=0,
                relationships_extracted=0,
                facts_extracted=0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                errors=errors,
            )

    async def _chunk_document(
        self, content: str, title: str, source: str, metadata: dict[str, Any] | None
    ) -> list[DocumentChunk]:
        """
        Chunk document using configured strategy.

        Args:
            content: Document content
            title: Document title
            source: Document source
            metadata: Additional metadata

        Returns:
            List of document chunks
        """
        chunk_metadata = {"title": title, "source": source, **(metadata or {})}

        if isinstance(self.chunker, SemanticChunker):
            chunks = await self.chunker.chunk(content, chunk_metadata)
        else:
            chunks = self.chunker.chunk(content, chunk_metadata)

        return chunks

    async def _generate_embeddings(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """
        Generate embeddings for chunks.

        Args:
            chunks: Document chunks

        Returns:
            Chunks with embeddings
        """
        return await self.embedder.embed_chunks(chunks)

    async def _store_in_postgres(
        self,
        title: str,
        source: str,
        content: str,
        chunks: list[DocumentChunk],
        metadata: dict[str, Any] | None,
    ) -> tuple[UUID, list[UUID]]:
        """
        Store document and chunks in PostgreSQL.

        Args:
            title: Document title
            source: Document source
            content: Full document content
            chunks: Document chunks with embeddings
            metadata: Document metadata

        Returns:
            Document ID and chunk IDs
        """
        # Store document
        doc_id = await self.pg_store.store_document(title, source, content, metadata)

        # Prepare chunk data
        chunk_data = []
        for chunk in chunks:
            chunk_dict = {
                "content": chunk.content,
                "embedding_1536": (
                    chunk.embedding if chunk.embedding and len(chunk.embedding) == 1536 else None
                ),
                "embedding_768": (
                    chunk.embedding if chunk.embedding and len(chunk.embedding) == 768 else None
                ),
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "metadata": chunk.metadata,
                "token_count": chunk.token_count,
            }

            # Handle multi-dimension embeddings
            if hasattr(chunk, "embeddings") and isinstance(chunk.embeddings, dict):
                chunk_dict["embedding_1536"] = chunk.embeddings.get("embedding_1536")
                chunk_dict["embedding_768"] = chunk.embeddings.get("embedding_768")

            chunk_data.append(chunk_dict)

        # Store chunks
        chunk_ids = await self.pg_store.store_chunks(doc_id, chunk_data)

        return doc_id, chunk_ids

    async def _extract_knowledge(
        self, chunks: list[DocumentChunk], chunk_ids: list[UUID]
    ) -> list[dict[str, Any]]:
        """
        Extract knowledge from chunks.

        Args:
            chunks: Document chunks
            chunk_ids: Chunk IDs from PostgreSQL

        Returns:
            List of extraction results
        """
        extraction_results = []

        # Process chunks in parallel (with limit)
        semaphore = asyncio.Semaphore(5)  # Limit concurrent extractions

        async def extract_chunk(chunk: DocumentChunk, chunk_id: UUID):
            async with semaphore:
                try:
                    result = await self.extractor.extract(chunk.content, str(chunk_id))

                    # Add to chunk object
                    chunk.entities = result["entities"]
                    chunk.facts = result["facts"]
                    chunk.relationships = result["relationships"]

                    return result
                except Exception as e:
                    logger.warning(f"Knowledge extraction failed for chunk {chunk_id}: {e}")
                    return {
                        "entities": [],
                        "relationships": [],
                        "facts": [],
                        "chunk_id": str(chunk_id),
                    }

        # Extract from all chunks
        tasks = [
            extract_chunk(chunk, chunk_id)
            for chunk, chunk_id in zip(chunks, chunk_ids, strict=False)
        ]

        extraction_results = await asyncio.gather(*tasks)

        return extraction_results

    async def _update_knowledge_graph(
        self, extraction_results: list[dict[str, Any]], document_id: UUID, chunk_ids: list[UUID]
    ):
        """
        Update Neo4j knowledge graph with extracted knowledge.

        Args:
            extraction_results: Extraction results for each chunk
            document_id: Document ID
            chunk_ids: Chunk IDs
        """
        try:
            # Aggregate all entities
            all_entities = []
            entity_map = {}  # name -> entity_id

            for result, chunk_id in zip(extraction_results, chunk_ids, strict=False):
                for entity in result["entities"]:
                    if entity.name not in entity_map:
                        # Store entity in Neo4j (name and type only)
                        entity_id = await self.neo4j_store.create_entity(
                            name=entity.name,
                            entity_type=(
                                entity.type.value if hasattr(entity.type, "value") else entity.type
                            ),
                            chunk_refs=[str(chunk_id)],
                            confidence=entity.confidence,
                        )
                        entity_map[entity.name] = entity_id
                    else:
                        # Update existing entity with new chunk reference
                        await self.neo4j_store.add_chunk_reference(
                            entity_map[entity.name], str(chunk_id)
                        )

            # Store relationships
            for result, chunk_id in zip(extraction_results, chunk_ids, strict=False):
                for rel in result["relationships"]:
                    if rel.source in entity_map and rel.target in entity_map:
                        await self.neo4j_store.create_relationship(
                            source_id=entity_map[rel.source],
                            target_id=entity_map[rel.target],
                            rel_type=rel.type.value if hasattr(rel.type, "value") else rel.type,
                            properties={
                                "confidence": rel.confidence,
                                "source_chunk": str(chunk_id),
                                "temporal_marker": rel.temporal_marker,
                            },
                        )

            # Store facts as episodes (via Graphiti)
            for result, chunk_id in zip(extraction_results, chunk_ids, strict=False):
                for fact in result["facts"]:
                    # Get entity IDs for fact
                    fact_entity_ids = [
                        entity_map[name] for name in fact.entities if name in entity_map
                    ]

                    await self.graphiti_client.add_episode(
                        content=fact.text[:500],  # Enforce limit
                        timestamp=fact.timestamp or datetime.now(),
                        entity_ids=fact_entity_ids,
                        source_id=str(chunk_id),
                    )

        except Exception as e:
            logger.error(f"Failed to update knowledge graph: {e}")
            # Continue processing even if graph update fails

    async def _update_cross_references(
        self, chunk_ids: list[UUID], extraction_results: list[dict[str, Any]]
    ):
        """
        Update PostgreSQL chunks with entity references.

        Args:
            chunk_ids: Chunk IDs
            extraction_results: Extraction results
        """
        for chunk_id, result in zip(chunk_ids, extraction_results, strict=False):
            entity_names = [e.name for e in result["entities"]]

            if entity_names:
                await self.pg_store.update_chunk_metadata(chunk_id, {"entity_refs": entity_names})

    async def ingest_batch(
        self, documents: list[dict[str, Any]], max_concurrent: int = 3
    ) -> list[IngestionResult]:
        """
        Ingest multiple documents in batch.

        Args:
            documents: List of document dictionaries with content, title, source
            max_concurrent: Maximum concurrent ingestions

        Returns:
            List of ingestion results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def ingest_with_semaphore(doc: dict[str, Any]):
            async with semaphore:
                return await self.ingest_document(
                    content=doc["content"],
                    title=doc["title"],
                    source=doc["source"],
                    metadata=doc.get("metadata"),
                )

        tasks = [ingest_with_semaphore(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    IngestionResult(
                        document_id=UUID("00000000-0000-0000-0000-000000000000"),
                        title=documents[i]["title"],
                        source=documents[i]["source"],
                        chunks_created=0,
                        entities_extracted=0,
                        relationships_extracted=0,
                        facts_extracted=0,
                        processing_time=0,
                        errors=[str(result)],
                    )
                )
            else:
                final_results.append(result)

        return final_results

    def get_stats(self) -> dict[str, Any]:
        """
        Get ingestion statistics.

        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()

        # Add embedder stats
        stats["embedding_stats"] = self.embedder.get_stats()

        # Calculate averages
        if stats["documents_processed"] > 0:
            stats["avg_chunks_per_doc"] = stats["chunks_created"] / stats["documents_processed"]
            stats["avg_entities_per_doc"] = (
                stats["entities_extracted"] / stats["documents_processed"]
            )
            stats["avg_facts_per_doc"] = stats["facts_extracted"] / stats["documents_processed"]

        return stats
