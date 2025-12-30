"""
Agentic RAG models package.

This package contains Pydantic models for structured data in the RAG system.
"""

from src.agentic_rag.models.document_reference import (
    DocumentReference,
    extract_document_metadata,
)

__all__ = [
    "DocumentReference",
    "extract_document_metadata",
]
