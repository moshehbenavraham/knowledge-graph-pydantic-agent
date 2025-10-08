"""
Agent-specific configuration facade.

Provides convenient access to agent and search-related settings.
"""

from .settings import SearchStrategy, WebSearchProvider, get_settings


class AgentConfig:
    """Facade for agent-related configuration."""

    def __init__(self):
        """Initialize with current settings."""
        self._settings = get_settings()

    @property
    def llm_model(self) -> str:
        """Get LLM model name."""
        return self._settings.get_effective_llm_model()

    @property
    def llm_temperature(self) -> float:
        """Get LLM temperature."""
        return self._settings.llm_temperature

    @property
    def llm_max_tokens(self) -> int:
        """Get max tokens for LLM."""
        return self._settings.llm_max_tokens

    @property
    def extraction_model(self) -> str:
        """Get extraction model name."""
        return self._settings.extraction_model

    @property
    def enable_graph(self) -> bool:
        """Check if graph features are enabled."""
        return self._settings.enable_graph

    @property
    def enable_parallel_search(self) -> bool:
        """Check if parallel search is enabled."""
        return self._settings.enable_parallel_search

    @property
    def vector_search_timeout(self) -> float:
        """Get vector search timeout."""
        return self._settings.vector_search_timeout

    @property
    def graph_search_timeout(self) -> float:
        """Get graph search timeout."""
        return self._settings.graph_search_timeout

    @property
    def default_search_strategy(self) -> SearchStrategy:
        """Get default search strategy."""
        return SearchStrategy.SMART

    @property
    def web_search_provider(self) -> WebSearchProvider | None:
        """Get web search provider."""
        return self._settings.web_search_provider

    @property
    def jina_api_key(self) -> str | None:
        """Get Jina API key."""
        return self._settings.jina_api_key

    @property
    def brave_api_key(self) -> str | None:
        """Get Brave API key."""
        return self._settings.brave_api_key

    @property
    def searxng_base_url(self) -> str | None:
        """Get SearXNG base URL."""
        return self._settings.searxng_base_url

    def get_search_config(self) -> dict[str, any]:
        """Get search configuration dictionary."""
        return {
            "enable_graph": self.enable_graph,
            "enable_parallel": self.enable_parallel_search,
            "vector_timeout": self.vector_search_timeout,
            "graph_timeout": self.graph_search_timeout,
            "default_strategy": self.default_search_strategy,
        }

    def get_web_search_config(self) -> dict[str, str | None]:
        """Get web search configuration."""
        return {
            "provider": self.web_search_provider,
            "jina_api_key": self.jina_api_key,
            "brave_api_key": self.brave_api_key,
            "searxng_base_url": self.searxng_base_url,
        }

    def has_web_search_configured(self) -> bool:
        """Check if any web search provider is configured."""
        return bool(self.jina_api_key or self.brave_api_key or self.searxng_base_url)


# Singleton instance
agent_config = AgentConfig()
