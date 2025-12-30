import base64
import sys
from pathlib import Path
from typing import Any

import structlog
from supabase import create_client
from supabase.client import Client

structlog_logger = structlog.get_logger(__name__)

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings

# Initialize Supabase client using centralized configuration
settings = get_settings()
if settings.supabase_url is None or settings.supabase_service_key is None:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured")
supabase: Client = (
    create_client(  # Constitution exception: CONST-III-001 - RAG pipeline module-level client using centralized config
        settings.supabase_url, settings.supabase_service_key
    )
)


def delete_document_by_file_id(file_id: str) -> None:
    """
    Delete all records related to a specific file ID (documents and chunks).

    Args:
        file_id: The Google Drive file ID
    """
    structlog_logger.info("delete_document_by_file_id called", file_id=file_id)
    try:
        # Delete document by file_id in metadata (cascades to chunks)
        response = supabase.table("documents").delete().eq("metadata->>file_id", file_id).execute()
        structlog_logger.info(
            "Deleted documents", documents_deleted=len(response.data), file_id=file_id
        )
    except Exception as e:
        structlog_logger.error("Error deleting documents", error=str(e), file_id=file_id)

    structlog_logger.info("delete_document_by_file_id completed", file_id=file_id)


def insert_document_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    file_id: str,
    file_url: str,
    file_title: str,
    mime_type: str,
    file_contents: bytes | None = None,
) -> None:
    """
    Insert document and chunks with embeddings into the Supabase database (new schema).

    Args:
        chunks: List of text chunks
        embeddings: List of embedding vectors for each chunk
        file_id: The Google Drive file ID
        file_url: The URL to access the file
        file_title: The title of the file
        mime_type: The mime type of the file
        file_contents: Optional binary of the file to store as metadata
    """
    structlog_logger.info(
        "insert_document_chunks called",
        file_id=file_id,
        file_title=file_title,
        num_chunks=len(chunks),
        has_file_contents=file_contents is not None,
    )
    try:
        # Ensure we have the same number of chunks and embeddings
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")

        # 1. Create the parent document
        full_content = "\n\n".join(chunks)
        file_bytes_str = base64.b64encode(file_contents).decode("utf-8") if file_contents else None

        doc_data = {
            "title": file_title,
            "source": file_url,
            "content": full_content,
            "metadata": {
                "file_id": file_id,
                "file_url": file_url,
                "mime_type": mime_type,
                **({"file_contents": file_bytes_str} if file_bytes_str else {}),
            },
        }

        doc_response = supabase.table("documents").insert(doc_data).execute()
        document_id = doc_response.data[0]["id"]
        structlog_logger.info("Created document", document_id=document_id, file_id=file_id)

        # 2. Create chunks with embeddings
        chunk_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
            chunk_data.append(
                {
                    "document_id": document_id,
                    "content": chunk,
                    "embedding_1536": embedding,
                    "chunk_index": i,
                    "start_char": 0,  # Can be calculated if needed
                    "end_char": len(chunk),
                    "metadata": {
                        "file_id": file_id,
                        "chunk_index": i,
                    },
                }
            )

        # Insert chunks in batch
        supabase.table("chunks").insert(chunk_data).execute()

        structlog_logger.info(
            "insert_document_chunks completed", file_id=file_id, chunks_inserted=len(chunk_data)
        )
    except Exception as e:
        structlog_logger.error("Error inserting document chunks", error=str(e), file_id=file_id)


def insert_or_update_document_metadata(
    file_id: str, file_title: str, file_url: str, schema: list[str] | None = None
) -> None:
    """
    No-op function - metadata now stored in documents table.

    Args:
        file_id: The Google Drive file ID (used as primary key)
        file_title: The title of the file
        file_url: The URL to access the file
        schema: Optional schema for tabular files (column names)
    """
    structlog_logger.info(
        "insert_or_update_document_metadata called (no-op - metadata in documents table)",
        file_id=file_id,
        file_title=file_title,
        has_schema=schema is not None,
    )


def insert_document_rows(file_id: str, rows: list[dict[str, Any]]) -> None:
    """
    Insert rows from a tabular file into the document_rows table.

    Args:
        file_id: The Google Drive file ID
        rows: List of row data as dictionaries
    """
    structlog_logger.info("insert_document_rows called", file_id=file_id, num_rows=len(rows))
    try:
        # Find the document UUID by file_id in metadata
        doc_response = (
            supabase.table("documents").select("id").eq("metadata->>file_id", file_id).execute()
        )

        if not doc_response.data:
            structlog_logger.error("Document not found for file_id", file_id=file_id)
            return

        document_id = doc_response.data[0]["id"]
        structlog_logger.info("Found document", document_id=document_id, file_id=file_id)

        # Delete existing rows for this document
        supabase.table("document_rows").delete().eq("dataset_id", document_id).execute()
        structlog_logger.info("Deleted existing rows", document_id=document_id)

        # Insert new rows with row_index
        row_data_list = []
        for i, row in enumerate(rows):
            row_data_list.append({"dataset_id": document_id, "row_data": row, "row_index": i})

        if row_data_list:
            supabase.table("document_rows").insert(row_data_list).execute()

        structlog_logger.info(
            "Inserted document rows", document_id=document_id, rows_inserted=len(row_data_list)
        )
    except Exception as e:
        structlog_logger.error("Error inserting document rows", error=str(e), file_id=file_id)
