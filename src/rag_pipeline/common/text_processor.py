import csv
import io
import sys
import tempfile
from pathlib import Path
from typing import Any

import pypdf
import structlog
from openai import OpenAI

structlog_logger = structlog.get_logger(__name__)

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings

# Initialize OpenAI client using centralized configuration
settings = get_settings()
api_key = settings.embedding_api_key or "ollama"
openai_client = OpenAI(api_key=api_key, base_url=settings.embedding_base_url)


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 0) -> list[str]:
    """
    Split text into chunks of specified size with optional overlap.

    Args:
        text: The text to chunk
        chunk_size: Size of each chunk in characters
        overlap: Number of overlapping characters between chunks

    Returns:
        List of text chunks
    """
    structlog_logger.info(
        "chunk_text called",
        text_length=len(text) if text else 0,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    if not text:
        structlog_logger.info("chunk_text completed - empty text", num_chunks=0)
        return []

    # Clean the text
    text = text.replace("\r", "")

    # Split text into chunks
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i : i + chunk_size]
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)

    structlog_logger.info(
        "chunk_text completed",
        num_chunks=len(chunks),
        text_length=len(text),
        chunk_size=chunk_size,
        overlap=overlap,
    )
    return chunks


def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from a PDF file.

    Args:
        file_content: Binary content of the PDF file

    Returns:
        Extracted text from the PDF
    """
    structlog_logger.info("extract_text_from_pdf called", file_size_bytes=len(file_content))

    # Create a temporary file to store the PDF content
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name

    try:
        # Open the PDF file
        with Path(temp_file_path).open("rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            structlog_logger.info("PDF opened", num_pages=num_pages)
            text = ""

            # Extract text from each page
            for _page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"

        structlog_logger.info(
            "extract_text_from_pdf completed", num_pages=num_pages, text_length=len(text)
        )
        return text
    except Exception as e:
        structlog_logger.error("Error extracting text from PDF", error=str(e))
        raise
    finally:
        # Clean up the temporary file
        temp_path = Path(temp_file_path)
        if temp_path.exists():
            temp_path.unlink()


def extract_text_from_file(
    file_content: bytes, mime_type: str, file_name: str, config: dict[str, Any] | None = None
) -> str:
    """
    Extract text from a file based on its MIME type.

    Args:
        file_content: Binary content of the file
        mime_type: MIME type of the file
        config: Configuration dictionary with supported_mime_types

    Returns:
        Extracted text from the file
    """
    structlog_logger.info(
        "extract_text_from_file called",
        mime_type=mime_type,
        file_name=file_name,
        file_size_bytes=len(file_content),
    )

    supported_mime_types = []
    if config and "supported_mime_types" in config:
        supported_mime_types = config["supported_mime_types"]

    if "application/pdf" in mime_type:
        structlog_logger.info("extract_text_from_file - processing as PDF", mime_type=mime_type)
        result = extract_text_from_pdf(file_content)
        structlog_logger.info("extract_text_from_file completed - PDF", text_length=len(result))
        return result
    if mime_type.startswith("image"):
        structlog_logger.info("extract_text_from_file completed - image", file_name=file_name)
        return file_name
    if config and any(mime_type.startswith(t) for t in supported_mime_types):
        result = file_content.decode("utf-8", errors="replace")
        structlog_logger.info(
            "extract_text_from_file completed - supported mime type",
            mime_type=mime_type,
            text_length=len(result),
        )
        return result
    # For unsupported file types, just try to extract the text
    result = file_content.decode("utf-8", errors="replace")
    structlog_logger.info(
        "extract_text_from_file completed - unsupported mime type fallback",
        mime_type=mime_type,
        text_length=len(result),
    )
    return result


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Create embeddings for a list of text chunks using OpenAI.

    Args:
        texts: List of text chunks to embed

    Returns:
        List of embedding vectors
    """
    structlog_logger.info(
        "create_embeddings called", num_texts=len(texts), model=settings.embedding_model
    )

    if not texts:
        structlog_logger.info("create_embeddings completed - empty texts", num_embeddings=0)
        return []

    try:
        response = openai_client.embeddings.create(model=settings.embedding_model, input=texts)

        # Extract the embedding vectors from the response
        embeddings = [item.embedding for item in response.data]

        structlog_logger.info(
            "create_embeddings completed",
            num_embeddings=len(embeddings),
            embedding_dim=len(embeddings[0]) if embeddings else 0,
            model=settings.embedding_model,
        )
        return embeddings
    except Exception as e:
        structlog_logger.error(
            "Error creating embeddings",
            error=str(e),
            num_texts=len(texts),
            model=settings.embedding_model,
        )
        raise


def is_tabular_file(mime_type: str, config: dict[str, Any] | None = None) -> bool:
    """
    Check if a file is tabular based on its MIME type.

    Args:
        mime_type: The MIME type of the file
        config: Optional configuration dictionary

    Returns:
        bool: True if the file is tabular (CSV or Excel), False otherwise
    """
    structlog_logger.info("is_tabular_file called", mime_type=mime_type)

    # Default tabular MIME types if config is not provided
    tabular_mime_types = [
        "csv",
        "xlsx",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.google-apps.spreadsheet",
    ]

    # Use tabular_mime_types from config if available
    if config and "tabular_mime_types" in config:
        tabular_mime_types = config["tabular_mime_types"]

    result = any(mime_type.startswith(t) for t in tabular_mime_types)
    structlog_logger.info("is_tabular_file completed", mime_type=mime_type, is_tabular=result)
    return result


def extract_schema_from_csv(file_content: bytes) -> list[str]:
    """
    Extract column names from a CSV file.

    Args:
        file_content: The binary content of the CSV file

    Returns:
        List[str]: List of column names
    """
    structlog_logger.info("extract_schema_from_csv called", file_size_bytes=len(file_content))

    try:
        # Decode the CSV content
        text_content = file_content.decode("utf-8", errors="replace")
        csv_reader = csv.reader(io.StringIO(text_content))
        # Get the header row (first row)
        header = next(csv_reader)
        structlog_logger.info(
            "extract_schema_from_csv completed", num_columns=len(header), columns=header
        )
        return header
    except Exception as e:
        structlog_logger.error("Error extracting schema from CSV", error=str(e))
        return []


def extract_rows_from_csv(file_content: bytes) -> list[dict[str, Any]]:
    """
    Extract rows from a CSV file as a list of dictionaries.

    Args:
        file_content: The binary content of the CSV file

    Returns:
        List[Dict[str, Any]]: List of row data as dictionaries
    """
    structlog_logger.info("extract_rows_from_csv called", file_size_bytes=len(file_content))

    try:
        # Decode the CSV content
        text_content = file_content.decode("utf-8", errors="replace")
        csv_reader = csv.DictReader(io.StringIO(text_content))
        rows = list(csv_reader)
        structlog_logger.info(
            "extract_rows_from_csv completed",
            num_rows=len(rows),
            num_columns=len(rows[0]) if rows else 0,
        )
        return rows
    except Exception as e:
        structlog_logger.error("Error extracting rows from CSV", error=str(e))
        return []
