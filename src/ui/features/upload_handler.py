"""File upload handler for Streamlit UI."""

import asyncio
import base64
import contextlib
import io
from typing import Any

import nest_asyncio
import pandas as pd
import streamlit as st
import structlog
from streamlit.runtime.uploaded_file_manager import UploadedFile

from supabase import Client

logger = structlog.get_logger(__name__)


async def process_document_upload(
    file: UploadedFile, supabase_client: Client, embedding_client: Any
) -> dict[str, Any]:
    """
    Process an uploaded document (PDF, TXT, MD, etc.).

    Args:
        file: Streamlit UploadedFile object
        supabase_client: Supabase client
        embedding_client: OpenAI client for embeddings

    Returns:
        Processing result dictionary
    """
    from src.agentic_rag.ingestion.chunker import semantic_chunk
    from src.agentic_rag.ingestion.embedder import generate_embeddings

    logger.info(
        "=" * 80,
    )
    logger.info(
        "Document upload started",
        file_name=file.name,
        file_type=file.type,
        file_size_kb=round(file.size / 1024, 2),
    )

    try:
        # Read file content
        logger.debug("Reading file content...")
        content = file.read().decode("utf-8")
        content_length = len(content)
        logger.info(
            "File content read",
            content_length=content_length,
            content_preview=content[:100] + "...",
        )

        # Chunk the document
        logger.info("Chunking document...", chunk_size=1000, overlap=200)
        chunks = semantic_chunk(content, chunk_size=1000, overlap=200)
        chunk_count = len(chunks)
        logger.info("Document chunked successfully", chunk_count=chunk_count)

        # Generate embeddings
        logger.info("Generating embeddings...", chunk_count=chunk_count)
        embeddings = await generate_embeddings(
            [chunk["content"] for chunk in chunks], embedding_client
        )
        logger.info("Embeddings generated successfully", embedding_count=len(embeddings))

        # Store in database
        logger.info("Preparing documents for database insertion...")
        documents = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
            doc = {
                "title": f"{file.name} - Chunk {i+1}",
                "source": file.name,
                "content": chunk["content"],
                "embedding": embedding,
                "metadata": {
                    "source": file.name,
                    "chunk_index": i,
                    "file_type": file.type,
                    "upload_source": "streamlit_ui",
                },
            }
            documents.append(doc)

        # Insert into Supabase
        logger.info("Inserting documents into Supabase...", document_count=len(documents))
        supabase_client.table("documents").insert(documents).execute()
        logger.info("Documents inserted successfully", document_count=len(documents))

        logger.info(
            "Document upload COMPLETE",
            file_name=file.name,
            chunks=chunk_count,
            success=True,
        )

        return {
            "success": True,
            "message": f"Uploaded {file.name} ({len(chunks)} chunks)",
            "chunks": len(chunks),
            "document_id": file.name,
        }

    except Exception as e:
        logger.exception(
            "Document upload FAILED",
            file_name=file.name,
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "success": False,
            "message": f"Upload failed: {e!s}",
            "error": str(e),
        }


async def process_image_upload(file: UploadedFile, supabase_client: Client) -> dict[str, Any]:
    """
    Process an uploaded image.

    Args:
        file: Streamlit UploadedFile object
        supabase_client: Supabase client

    Returns:
        Processing result dictionary
    """
    logger.info(
        "=" * 80,
    )
    logger.info(
        "Image upload started",
        file_name=file.name,
        file_type=file.type,
        file_size_kb=round(file.size / 1024, 2),
    )

    try:
        # Read image as bytes
        logger.debug("Reading image bytes...")
        image_bytes = file.read()
        logger.info("Image bytes read", byte_count=len(image_bytes))

        # Encode as base64 for storage
        logger.debug("Encoding image as base64...")
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        base64_length = len(image_base64)
        logger.info("Image encoded", base64_length=base64_length)

        # Store in database
        logger.info("Preparing image document for database insertion...")
        doc = {
            "title": file.name,
            "source": file.name,
            "content": f"[Image: {file.name}]",
            "metadata": {
                "source": file.name,
                "file_type": file.type,
                "upload_source": "streamlit_ui",
                "image_data": image_base64,
                "is_image": True,
            },
        }

        logger.info("Inserting image document into Supabase...")
        supabase_client.table("documents").insert(doc).execute()
        logger.info("Image document inserted successfully")

        logger.info(
            "Image upload COMPLETE",
            file_name=file.name,
            success=True,
        )

        return {
            "success": True,
            "message": f"Uploaded image {file.name}",
            "document_id": file.name,
        }

    except Exception as e:
        logger.exception(
            "Image upload FAILED",
            file_name=file.name,
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "success": False,
            "message": f"Upload failed: {e!s}",
            "error": str(e),
        }


async def process_tabular_upload(file: UploadedFile, supabase_client: Client) -> dict[str, Any]:
    """
    Process an uploaded CSV/Excel file.

    Args:
        file: Streamlit UploadedFile object
        supabase_client: Supabase client

    Returns:
        Processing result dictionary
    """
    logger.info(
        "=" * 80,
    )
    logger.info(
        "Tabular upload started",
        file_name=file.name,
        file_type=file.type,
        file_size_kb=round(file.size / 1024, 2),
    )

    try:
        # Read tabular data
        logger.debug("Reading tabular data...")
        if file.name.endswith(".csv"):
            logger.debug("Processing CSV file...")
            df = pd.read_csv(io.BytesIO(file.read()))
        elif file.name.endswith((".xlsx", ".xls")):
            logger.debug("Processing Excel file...")
            df = pd.read_excel(io.BytesIO(file.read()))
        else:
            logger.warning(
                "Unsupported tabular file type",
                file_name=file.name,
                file_type=file.type,
            )
            return {
                "success": False,
                "message": "Unsupported file type. Use CSV or Excel.",
            }

        row_count = len(df)
        col_count = len(df.columns)
        logger.info(
            "Tabular data loaded successfully",
            rows=row_count,
            columns=col_count,
            column_names=list(df.columns),
        )

        # Store metadata about the dataset
        logger.info("Preparing dataset metadata...")
        doc = {
            "title": file.name,
            "source": file.name,
            "content": f"[Dataset: {file.name}]",
            "metadata": {
                "source": file.name,
                "file_type": file.type,
                "upload_source": "streamlit_ui",
                "is_tabular": True,
                "columns": list(df.columns),
                "row_count": len(df),
                "schema": df.dtypes.astype(str).to_dict(),
            },
        }

        # Insert dataset metadata
        logger.info("Inserting dataset metadata into Supabase...")
        result = supabase_client.table("documents").insert(doc).execute()
        dataset_id = result.data[0]["id"] if result.data else file.name
        logger.info("Dataset metadata inserted", dataset_id=dataset_id)

        # Store individual rows
        logger.info("Preparing individual rows for insertion...", row_count=row_count)
        rows_data = []
        for idx, row in df.iterrows():
            row_doc = {
                "dataset_id": dataset_id,
                "row_data": row.to_dict(),
                "row_index": int(idx),
            }
            rows_data.append(row_doc)

        # Batch insert rows
        if rows_data:
            logger.info("Batch inserting rows into Supabase...", row_count=len(rows_data))
            supabase_client.table("document_rows").insert(rows_data).execute()
            logger.info("Rows inserted successfully", row_count=len(rows_data))

        logger.info(
            "Tabular upload COMPLETE",
            file_name=file.name,
            rows=row_count,
            columns=col_count,
            dataset_id=dataset_id,
            success=True,
        )

        return {
            "success": True,
            "message": f"Uploaded {file.name} ({len(df)} rows, {len(df.columns)} columns)",
            "rows": len(df),
            "columns": len(df.columns),
            "dataset_id": dataset_id,
        }

    except Exception as e:
        logger.exception(
            "Tabular upload FAILED",
            file_name=file.name,
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "success": False,
            "message": f"Upload failed: {e!s}",
            "error": str(e),
        }


def render_upload_section(supabase_client: Client, embedding_client: Any) -> None:
    """
    Render the file upload section in the sidebar.

    Args:
        supabase_client: Supabase client
        embedding_client: OpenAI client for embeddings
    """
    st.subheader("📤 Upload Files")

    # File type selector
    upload_type = st.selectbox(
        "File Type",
        ["Documents (PDF, TXT, MD)", "Images (PNG, JPG)", "Data (CSV, Excel)"],
        help="Select the type of file you want to upload",
    )

    # File uploader with appropriate file types
    if "Documents" in upload_type:
        accepted_types = ["txt", "md", "pdf"]
        file = st.file_uploader(
            "Upload Document",
            type=accepted_types,
            help="Supports: TXT, Markdown, PDF",
        )
    elif "Images" in upload_type:
        accepted_types = ["png", "jpg", "jpeg", "gif", "webp"]
        file = st.file_uploader(
            "Upload Image",
            type=accepted_types,
            help="Supports: PNG, JPG, JPEG, GIF, WEBP",
        )
    else:  # Data
        accepted_types = ["csv", "xlsx", "xls"]
        file = st.file_uploader(
            "Upload Data",
            type=accepted_types,
            help="Supports: CSV, Excel (XLSX, XLS)",
        )

    if file is not None:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.caption(f"📄 {file.name} ({file.size / 1024:.1f} KB)")

        with col2:
            if st.button("Upload", type="primary", use_container_width=True):
                logger.info(
                    "Upload button clicked",
                    file_name=file.name,
                    file_type=file.type,
                    upload_type=upload_type,
                    file_size_kb=round(file.size / 1024, 2),
                )

                with st.spinner("Processing..."):
                    # Process based on file type
                    # Use asyncio.create_task or run in executor since we're already in an event loop
                    # Enable nested event loops for Streamlit compatibility
                    with contextlib.suppress(Exception):
                        nest_asyncio.apply()  # May already be applied

                    try:
                        if "Documents" in upload_type:
                            logger.debug("Calling process_document_upload...")
                            result = asyncio.run(
                                process_document_upload(file, supabase_client, embedding_client)
                            )
                        elif "Images" in upload_type:
                            logger.debug("Calling process_image_upload...")
                            result = asyncio.run(process_image_upload(file, supabase_client))
                        else:
                            logger.debug("Calling process_tabular_upload...")
                            result = asyncio.run(process_tabular_upload(file, supabase_client))
                    except RuntimeError:
                        # Fallback: run in current loop
                        logger.debug("RuntimeError caught, using fallback loop execution")
                        loop = asyncio.get_event_loop()
                        if "Documents" in upload_type:
                            result = loop.run_until_complete(
                                process_document_upload(file, supabase_client, embedding_client)
                            )
                        elif "Images" in upload_type:
                            result = loop.run_until_complete(
                                process_image_upload(file, supabase_client)
                            )
                        else:
                            result = loop.run_until_complete(
                                process_tabular_upload(file, supabase_client)
                            )

                    # Show result
                    if result["success"]:
                        logger.info(
                            "Upload completed successfully",
                            file_name=file.name,
                            result_message=result["message"],
                        )
                        st.success(result["message"])
                    else:
                        logger.error(
                            "Upload failed",
                            file_name=file.name,
                            error_message=result["message"],
                        )
                        st.error(result["message"])
