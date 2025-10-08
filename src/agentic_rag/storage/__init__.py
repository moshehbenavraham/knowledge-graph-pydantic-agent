"""
Storage layer for Agentic RAG system.

Provides connection management and operations for:
- PostgreSQL with pgvector for document storage and vector search
- Neo4j with Graphiti for knowledge graph indexing
"""

from .connection_manager import ConnectionManager, close_connections, get_connection_manager

__all__ = ["ConnectionManager", "close_connections", "get_connection_manager"]
