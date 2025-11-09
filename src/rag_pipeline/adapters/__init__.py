"""Adapters for integrating Agentic RAG with legacy RAG watchers."""

from src.rag_pipeline.adapters.agentic_rag_adapter import (
    process_file_with_agentic_rag,
    process_file_with_agentic_rag_sync,
)

__all__ = [
    "process_file_with_agentic_rag",
    "process_file_with_agentic_rag_sync",
]
