"""
Centralized configuration module.

Provides a single source of truth for all application settings.
"""

from .settings import (
    ChunkingStrategy,
    EmbeddingProvider,
    Environment,
    LLMProvider,
    SearchStrategy,
    Settings,
    UIMode,
    WebSearchProvider,
    get_settings,
    reload_settings,
)

try:
    from src.agentic_rag.search.intent_analyzer import SearchIntent
except ImportError:
    SearchIntent = None

__all__ = [
    "ChunkingStrategy",
    "EmbeddingProvider",
    "Environment",
    "LLMProvider",
    "SearchIntent",
    "SearchStrategy",
    "Settings",
    "UIMode",
    "WebSearchProvider",
    "get_settings",
    "reload_settings",
]
