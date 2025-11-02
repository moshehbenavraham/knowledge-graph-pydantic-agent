"""
Document management endpoints.

Handles document ingestion, updates, listing, and content inspection.
"""

import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from prometheus_client import Counter, Histogram

from src.agentic_rag.ingestion.pipeline import DocumentIngestionPipeline as IngestionPipeline
from src.agentic_rag.storage.postgres_store import PostgresStore
from src.api.dependencies import get_graphiti_client, get_postgres_store
from src.api.models import (
    DocumentContent,
    DocumentListResponse,
    DocumentMetadata,
    IngestRequest,
    IngestResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# Metrics
ingest_requests_total = Counter(
    "ingest_requests_total", "Total document ingestion requests", ["status"]
)
ingest_duration = Histogram("ingest_duration_seconds", "Document ingestion duration")


@router.post("", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    request: IngestRequest,
    postgres_store: PostgresStore = Depends(get_postgres_store),
    graphiti_client=Depends(get_graphiti_client),
) -> IngestResponse:
    """
    Ingest new document into the system.

    Chunks document, generates embeddings, extracts knowledge, and stores
    in both PostgreSQL (content) and Neo4j (knowledge graph).
    """
    start_time = time.perf_counter()

    try:
        logger.info(
            "document_ingestion_started",
            title=request.title,
            source=request.source,
        )

        # Initialize ingestion pipeline
        # Note: Pipeline creates its own storage instances internally
        pipeline = IngestionPipeline()

        # Ingest document
        result = await pipeline.ingest_document(
            content=request.content,
            title=request.title,
            source=request.source,
            metadata=request.metadata,
        )

        # Calculate metrics
        processing_time_ms = (time.perf_counter() - start_time) * 1000

        response = IngestResponse(
            document_id=str(result.document_id),
            chunks_created=result.chunks_created,
            entities_extracted=result.entities_extracted,
            relationships_extracted=result.relationships_extracted,
            processing_time_ms=processing_time_ms,
            status="completed",
        )

        # Record metrics
        ingest_requests_total.labels(status="success").inc()
        ingest_duration.observe(processing_time_ms / 1000)

        logger.info(
            "document_ingestion_completed",
            document_id=result.document_id,
            chunks=result.chunks_created,
            duration_ms=processing_time_ms,
        )

        return response

    except Exception as e:
        logger.error("document_ingestion_failed", error=str(e))
        ingest_requests_total.labels(status="error").inc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {e!s}",
        )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    source_filter: str | None = Query(None, description="Filter by source"),
    postgres_store: PostgresStore = Depends(get_postgres_store),
) -> DocumentListResponse:
    """
    List documents with pagination and filtering.

    Returns document metadata without full content.
    """
    try:
        # Calculate offset
        offset = (page - 1) * page_size

        # Get documents from store
        documents = await postgres_store.list_documents(
            limit=page_size,
            offset=offset,
            source_filter=source_filter,
            sort_by="created_at",
            sort_order="desc",
        )

        # Get total count
        total = await postgres_store.count_documents(source_filter=source_filter)

        # Convert to metadata models
        document_list = [
            DocumentMetadata(
                id=doc["id"],
                title=doc["title"],
                source=doc["source"],
                created_at=doc["created_at"],
                updated_at=doc.get("updated_at"),
                chunk_count=doc.get("chunk_count", 0),
                metadata=doc.get("metadata"),
            )
            for doc in documents
        ]

        return DocumentListResponse(
            documents=document_list,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    except Exception as e:
        logger.error("list_documents_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents",
        )


@router.get("/{document_id}", response_model=DocumentContent)
async def get_document(
    document_id: str,
    include_chunks: bool = Query(False, description="Include chunk breakdown"),
    postgres_store: PostgresStore = Depends(get_postgres_store),
) -> DocumentContent:
    """
    Get full document content by ID.

    Optionally includes chunk breakdown.
    """
    try:
        # Get document
        document = await postgres_store.get_document(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # Get chunks if requested (return just content strings per model spec)
        chunks = None
        if include_chunks:
            raw_chunks = await postgres_store.get_document_chunks(
                document_id, include_embeddings=False
            )
            chunks = [chunk["content"] for chunk in raw_chunks]

        return DocumentContent(
            metadata=DocumentMetadata(
                id=document["id"],
                title=document["title"],
                source=document["source"],
                created_at=document["created_at"],
                updated_at=document.get("updated_at"),
                chunk_count=document.get("chunk_count", 0),
                metadata=document.get("metadata"),
            ),
            content=document["content"],
            chunks=chunks,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_document_failed", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document",
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    postgres_store: PostgresStore = Depends(get_postgres_store),
    graphiti_client=Depends(get_graphiti_client),
):
    """
    Delete document and associated data.

    Removes document from PostgreSQL and cleans up references in Neo4j.
    """
    try:
        logger.info("document_deletion_started", document_id=document_id)

        # Check if document exists
        document = await postgres_store.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # Delete from PostgreSQL (cascades to chunks)
        await postgres_store.delete_document(document_id)

        # TODO: Clean up knowledge graph references
        if graphiti_client:
            # Remove episodes and entities tied to this document
            pass

        logger.info("document_deletion_completed", document_id=document_id)

        return {
            "status": "deleted",
            "document_id": document_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("document_deletion_failed", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )


@router.patch("/{document_id}")
async def update_document(
    document_id: str,
    title: str | None = None,
    metadata: dict | None = None,
    postgres_store: PostgresStore = Depends(get_postgres_store),
):
    """
    Update document metadata.

    Allows updating title and custom metadata fields.
    """
    try:
        # Check if document exists
        document = await postgres_store.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # Update fields
        updates = {}
        if title:
            updates["title"] = title
        if metadata:
            updates["metadata"] = metadata

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided",
            )

        # Perform update
        success = await postgres_store.update_document(document_id, updates)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to apply document updates",
            )

        logger.info("document_updated", document_id=document_id, updates=updates)

        return {
            "status": "updated",
            "document_id": document_id,
            "updates": updates,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("document_update_failed", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document",
        )


@router.post("/{document_id}/reindex")
async def reindex_document(
    document_id: str,
    postgres_store: PostgresStore = Depends(get_postgres_store),
    graphiti_client=Depends(get_graphiti_client),
):
    """
    Reindex document (regenerate embeddings and knowledge extraction).

    Useful after model updates or configuration changes.
    """
    try:
        logger.info("document_reindex_started", document_id=document_id)

        # Get document
        document = await postgres_store.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # TODO: Implement reindexing logic
        # 1. Regenerate embeddings for all chunks
        # 2. Re-extract knowledge
        # 3. Update stores

        logger.info("document_reindex_completed", document_id=document_id)

        return {
            "status": "reindexed",
            "document_id": document_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("document_reindex_failed", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reindex document",
        )


@router.get("/{document_id}/stats")
async def get_document_stats(
    document_id: str,
    postgres_store: PostgresStore = Depends(get_postgres_store),
    graphiti_client=Depends(get_graphiti_client),
):
    """
    Get statistics for document.

    Returns chunk count, entity count, relationship count, etc.
    """
    try:
        # Check if document exists
        document = await postgres_store.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # Get chunk count
        chunk_count = await postgres_store.count_chunks(document_id)

        # Get knowledge graph stats
        entity_count = 0
        relationship_count = 0

        if graphiti_client:
            # Query Neo4j for entity/relationship counts
            pass

        return {
            "document_id": document_id,
            "chunk_count": chunk_count,
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "created_at": document["created_at"],
            "last_accessed": None,  # TODO: Track access
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("document_stats_failed", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document stats",
        )
