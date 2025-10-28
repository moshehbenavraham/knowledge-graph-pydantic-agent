"""
Agent-specific configuration facade.

Provides convenient access to agent and search-related settings.
"""

import structlog

from .settings import SearchStrategy, WebSearchProvider, get_settings

logger = structlog.get_logger(__name__)


class AgentConfig:
    """Facade for agent-related configuration."""

    @property
    def llm_provider(self) -> str:
        """Get LLM provider."""
        return get_settings().llm_provider

    @property
    def llm_model(self) -> str:
        """Get LLM model name."""
        return get_settings().get_effective_llm_model()

    @property
    def llm_temperature(self) -> float:
        """Get LLM temperature."""
        return get_settings().llm_temperature

    @property
    def llm_max_tokens(self) -> int:
        """Get max tokens for LLM."""
        return get_settings().llm_max_tokens

    @property
    def extraction_model(self) -> str:
        """Get extraction model name."""
        return get_settings().extraction_model

    @property
    def enable_graph(self) -> bool:
        """Check if graph features are enabled."""
        return get_settings().enable_graph

    @property
    def enable_parallel_search(self) -> bool:
        """Check if parallel search is enabled."""
        return get_settings().enable_parallel_search

    @property
    def vector_search_timeout(self) -> float:
        """Get vector search timeout."""
        return get_settings().vector_search_timeout

    @property
    def graph_search_timeout(self) -> float:
        """Get graph search timeout."""
        return get_settings().graph_search_timeout

    @property
    def default_search_strategy(self) -> SearchStrategy:
        """Get default search strategy."""
        return SearchStrategy.SMART

    @property
    def web_search_provider(self) -> WebSearchProvider | None:
        """Get web search provider."""
        return get_settings().web_search_provider

    @property
    def jina_api_key(self) -> str | None:
        """Get Jina API key."""
        return get_settings().jina_api_key

    @property
    def brave_api_key(self) -> str | None:
        """Get Brave API key."""
        return get_settings().brave_api_key

    @property
    def searxng_base_url(self) -> str | None:
        """Get SearXNG base URL."""
        return get_settings().searxng_base_url

    def get_search_config(self) -> dict[str, any]:
        """Get search configuration dictionary."""
        logger.info(
            "Getting search configuration",
            enable_graph=self.enable_graph,
            enable_parallel=self.enable_parallel_search,
        )
        return {
            "enable_graph": self.enable_graph,
            "enable_parallel": self.enable_parallel_search,
            "vector_timeout": self.vector_search_timeout,
            "graph_timeout": self.graph_search_timeout,
            "default_strategy": self.default_search_strategy,
        }

    def get_web_search_config(self) -> dict[str, str | None]:
        """Get web search configuration."""
        logger.info("Getting web search configuration", provider=self.web_search_provider)
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
