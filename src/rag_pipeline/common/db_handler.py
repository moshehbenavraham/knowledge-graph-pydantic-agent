import base64
import sys
import traceback
from pathlib import Path
from typing import Any

import structlog

from supabase import create_client  # type: ignore
from supabase.client import Client

structlog_logger = structlog.get_logger(__name__)

sys.path.append(str(Path(__file__).parent.resolve()))
from text_processor import (
    chunk_text,
    create_embeddings,
    extract_rows_from_csv,
    extract_schema_from_csv,
    is_tabular_file,
)

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings

# Initialize Supabase client using centralized configuration
settings = get_settings()
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


def process_file_for_rag(
    file_content: bytes,
    text: str,
    file_id: str,
    file_url: str,
    file_title: str,
    mime_type: str | None = None,
    config: dict[str, Any] | None = None,
) -> bool | None:
    """
    Process a file for the RAG pipeline - delete existing records and insert new ones.

    Args:
        file_content: The binary content of the file
        text: The text content extracted from the file
        file_id: The Google Drive file ID
        file_url: The URL to access the file
        file_title: The title of the file
        mime_type: Mime type of the file
        config: Configuration for things like the chunk size and overlap
    """
    structlog_logger.info(
        "process_file_for_rag called",
        file_id=file_id,
        file_title=file_title,
        mime_type=mime_type,
        text_length=len(text),
    )
    try:
        # First, delete any existing records for this file
        delete_document_by_file_id(file_id)

        # Check if this is a tabular file
        is_tabular = False
        schema = None

        if mime_type:
            is_tabular = is_tabular_file(mime_type, config)

        if is_tabular:
            # Extract schema (column names) from CSV
            schema = extract_schema_from_csv(file_content)

        # First, insert or update document metadata (needed for foreign key constraint)
        insert_or_update_document_metadata(file_id, file_title, file_url, schema)

        # Then, if it's a tabular file, insert the rows
        if is_tabular:
            # Extract and insert rows for tabular files
            rows = extract_rows_from_csv(file_content)
            if rows:
                insert_document_rows(file_id, rows)

        # Get text processing settings from config
        text_processing = config.get("text_processing", {}) if config else {}
        chunk_size = text_processing.get("default_chunk_size", 400)
        chunk_overlap = text_processing.get("default_chunk_overlap", 0)

        # Chunk the text
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        if not chunks:
            structlog_logger.warning("No chunks created", file_id=file_id, file_title=file_title)
            return None

        # Create embeddings for the chunks
        embeddings = create_embeddings(chunks)

        # For images, don't chunk the image, just store the title for RAG and include the binary in the metadata
        if mime_type and mime_type.startswith("image"):
            insert_document_chunks(
                chunks, embeddings, file_id, file_url, file_title, mime_type, file_content
            )
            structlog_logger.info(
                "process_file_for_rag completed - image file",
                file_id=file_id,
                chunks_created=len(chunks),
            )
            return True

        # Insert the chunks with their embeddings
        insert_document_chunks(
            chunks,
            embeddings,
            file_id,
            file_url,
            file_title,
            mime_type or "application/octet-stream",
        )

        structlog_logger.info(
            "process_file_for_rag completed", file_id=file_id, chunks_created=len(chunks)
        )
        return True
    except Exception as e:
        traceback.print_exc()
        structlog_logger.error("Error processing file for RAG", error=str(e), file_id=file_id)
        return False
