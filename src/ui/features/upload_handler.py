"""File upload handler for Streamlit UI."""

import asyncio
import base64
import contextlib
import io
import logging
from typing import Any

import pandas as pd
import streamlit as st

from supabase import Client

logger = logging.getLogger(__name__)


async def process_document_upload(
    file, supabase_client: Client, embedding_client: Any
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

    try:
        # Read file content
        content = file.read().decode("utf-8")

        # Chunk the document
        chunks = semantic_chunk(content, chunk_size=1000, overlap=200)

        # Generate embeddings
        embeddings = await generate_embeddings(
            [chunk["content"] for chunk in chunks], embedding_client
        )

        # Store in database
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
        supabase_client.table("documents").insert(documents).execute()

        return {
            "success": True,
            "message": f"Uploaded {file.name} ({len(chunks)} chunks)",
            "chunks": len(chunks),
            "document_id": file.name,
        }

    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        return {
            "success": False,
            "message": f"Upload failed: {e!s}",
            "error": str(e),
        }


async def process_image_upload(file, supabase_client: Client) -> dict[str, Any]:
    """
    Process an uploaded image.

    Args:
        file: Streamlit UploadedFile object
        supabase_client: Supabase client

    Returns:
        Processing result dictionary
    """
    try:
        # Read image as bytes
        image_bytes = file.read()

        # Encode as base64 for storage
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # Store in database
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

        supabase_client.table("documents").insert(doc).execute()

        return {
            "success": True,
            "message": f"Uploaded image {file.name}",
            "document_id": file.name,
        }

    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        return {
            "success": False,
            "message": f"Upload failed: {e!s}",
            "error": str(e),
        }


async def process_tabular_upload(file, supabase_client: Client) -> dict[str, Any]:
    """
    Process an uploaded CSV/Excel file.

    Args:
        file: Streamlit UploadedFile object
        supabase_client: Supabase client

    Returns:
        Processing result dictionary
    """
    try:
        # Read tabular data
        if file.name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file.read()))
        elif file.name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file.read()))
        else:
            return {
                "success": False,
                "message": "Unsupported file type. Use CSV or Excel.",
            }

        # Store metadata about the dataset
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
        result = supabase_client.table("documents").insert(doc).execute()
        dataset_id = result.data[0]["id"] if result.data else file.name

        # Store individual rows
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
            supabase_client.table("document_rows").insert(rows_data).execute()

        return {
            "success": True,
            "message": f"Uploaded {file.name} ({len(df)} rows, {len(df.columns)} columns)",
            "rows": len(df),
            "columns": len(df.columns),
            "dataset_id": dataset_id,
        }

    except Exception as e:
        logger.error(f"Tabular upload failed: {e}")
        return {
            "success": False,
            "message": f"Upload failed: {e!s}",
            "error": str(e),
        }


def render_upload_section(supabase_client: Client, embedding_client: Any):
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
                with st.spinner("Processing..."):
                    # Process based on file type
                    # Use asyncio.create_task or run in executor since we're already in an event loop
                    import nest_asyncio

                    # Enable nested event loops for Streamlit compatibility
                    with contextlib.suppress(Exception):
                        nest_asyncio.apply()  # May already be applied

                    try:
                        if "Documents" in upload_type:
                            result = asyncio.run(
                                process_document_upload(file, supabase_client, embedding_client)
                            )
                        elif "Images" in upload_type:
                            result = asyncio.run(process_image_upload(file, supabase_client))
                        else:
                            result = asyncio.run(process_tabular_upload(file, supabase_client))
                    except RuntimeError:
                        # Fallback: run in current loop
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
                        st.success(result["message"])
                    else:
                        st.error(result["message"])
