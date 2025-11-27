"""Adapter to use Agentic RAG pipeline from legacy RAG watchers."""

import asyncio
from typing import Any

import structlog

from src.agentic_rag.ingestion.pipeline import DocumentIngestionPipeline, IngestionResult

logger = structlog.get_logger(__name__)


async def process_file_with_agentic_rag(
    text: str,
    file_id: str,
    file_title: str,
    file_url: str,
    mime_type: str | None = None,
    use_rest_api: bool = False,
) -> bool:
    """
    Process file using Agentic RAG pipeline.

    This adapter allows legacy RAG watchers (Google Drive, Local Files) to use
    the full Agentic RAG pipeline with knowledge extraction and Neo4j graph storage.

    Args:
        text: Extracted text content from the file
        file_id: File identifier (Google Drive ID or local file path)
        file_title: File title/name (without extension)
        file_url: File URL (webViewLink for Google Drive or file:// path for local)
        mime_type: MIME type of the file (optional)
        use_rest_api: Force Supabase REST API mode (default: False, uses PostgreSQL)

    Returns:
        True if successful, False otherwise

    Example:
        >>> success = await process_file_with_agentic_rag(
        ...     text="Document content...",
        ...     file_id="/path/to/file.txt",
        ...     file_title="file",
        ...     file_url="file:///path/to/file.txt",
        ...     mime_type="text/plain",
        ... )
    """
    logger.info(
        "process_file_with_agentic_rag called",
        file_id=file_id,
        file_title=file_title,
        text_length=len(text),
        mime_type=mime_type,
        use_rest_api=use_rest_api,
    )

    try:
        # Initialize pipeline with context manager (handles initialize/close)
        async with DocumentIngestionPipeline(use_rest_api=use_rest_api) as pipeline:
            # Determine source type from URL
            source_type = "google_drive" if "drive.google.com" in file_url else "local_file"

            # Build metadata dictionary
            metadata: dict[str, Any] = {
                "file_id": file_id,
                "source_type": source_type,
            }
            if mime_type:
                metadata["mime_type"] = mime_type

            logger.info(
                "Starting document ingestion",
                file_id=file_id,
                source_type=source_type,
                metadata=metadata,
            )

            # Ingest document through full Agentic RAG pipeline
            result: IngestionResult = await pipeline.ingest_document(
                content=text,
                title=file_title,
                source=file_url,
                metadata=metadata,
            )

            if result.success:
                logger.info(
                    "Agentic RAG processing complete",
                    file_id=file_id,
                    document_id=str(result.document_id),
                    chunks=result.chunks_created,
                    entities=result.entities_extracted,
                    relationships=result.relationships_extracted,
                    facts=result.facts_extracted,
                    processing_time_seconds=round(result.processing_time, 2),
                )
                return True
            logger.error(
                "Agentic RAG processing failed",
                file_id=file_id,
                errors=result.errors,
                processing_time_seconds=round(result.processing_time, 2),
            )
            return False

    except Exception as e:
        logger.exception(
            "Error in Agentic RAG processing",
            file_id=file_id,
            file_title=file_title,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False

    # Unreachable but satisfies mypy's control flow analysis
    return False


def process_file_with_agentic_rag_sync(
    text: str,
    file_id: str,
    file_title: str,
    file_url: str,
    mime_type: str | None = None,
    use_rest_api: bool = False,
) -> bool:
    """
    Synchronous wrapper for async Agentic RAG processing.

    This is a convenience function for legacy code that cannot easily use async/await.
    It creates a new event loop and runs the async function to completion.

    Args:
        text: Extracted text content from the file
        file_id: File identifier (Google Drive ID or local file path)
        file_title: File title/name (without extension)
        file_url: File URL (webViewLink for Google Drive or file:// path for local)
        mime_type: MIME type of the file (optional)
        use_rest_api: Force Supabase REST API mode (default: False, uses PostgreSQL)

    Returns:
        True if successful, False otherwise

    Example:
        >>> success = process_file_with_agentic_rag_sync(
        ...     text="Document content...",
        ...     file_id="/path/to/file.txt",
        ...     file_title="file",
        ...     file_url="file:///path/to/file.txt",
        ... )
    """
    logger.info(
        "process_file_with_agentic_rag_sync called (synchronous wrapper)",
        file_id=file_id,
        file_title=file_title,
    )

    return asyncio.run(
        process_file_with_agentic_rag(
            text=text,
            file_id=file_id,
            file_title=file_title,
            file_url=file_url,
            mime_type=mime_type,
            use_rest_api=use_rest_api,
        )
    )
