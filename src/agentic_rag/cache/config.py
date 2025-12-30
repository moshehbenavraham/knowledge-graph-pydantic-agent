"""
Cache configuration models using Pydantic.

Provides configurable settings for query caching with TTL, size limits,
and per-query-type tuning options.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class CacheType(str, Enum):
    """Types of cached queries."""

    VECTOR_SEARCH = "vector_search"
    GRAPH_SEARCH = "graph_search"
    MULTI_HOP = "multi_hop"
    TEMPORAL_TREND = "temporal_trend"
    COMPARISON = "comparison"
    HYBRID = "hybrid"


class CacheEntryConfig(BaseModel):
    """Configuration for a specific cache entry type."""

    enabled: bool = Field(
        default=True,
        description="Whether caching is enabled for this type",
    )
    ttl_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Time-to-live in seconds (10-3600)",
    )
    max_size: int = Field(
        default=100,
        ge=10,
        le=10000,
        description="Maximum number of entries (10-10000)",
    )


class CacheConfig(BaseModel):
    """
    Main cache configuration model.

    Provides global settings and per-query-type overrides for caching behavior.
    Uses sensible defaults optimized for the Agentic GraphRAG system.

    Attributes:
        enabled: Global cache enable/disable flag
        default_ttl_seconds: Default TTL for all cache entries
        default_max_size: Default maximum cache size
        cache_empty_results: Whether to cache empty query results
        cache_types: Per-query-type configuration overrides
    """

    enabled: bool = Field(
        default=True,
        description="Global cache enable/disable",
    )
    default_ttl_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Default TTL in seconds (5 minutes default)",
    )
    default_max_size: int = Field(
        default=500,
        ge=10,
        le=10000,
        description="Default max cache size",
    )
    cache_empty_results: bool = Field(
        default=True,
        description="Whether to cache empty results (prevents repeated empty queries)",
    )
    cache_types: dict[CacheType, CacheEntryConfig] = Field(
        default_factory=lambda: {
            CacheType.VECTOR_SEARCH: CacheEntryConfig(ttl_seconds=300, max_size=500),
            CacheType.GRAPH_SEARCH: CacheEntryConfig(ttl_seconds=300, max_size=200),
            CacheType.MULTI_HOP: CacheEntryConfig(ttl_seconds=600, max_size=100),
            CacheType.TEMPORAL_TREND: CacheEntryConfig(ttl_seconds=600, max_size=100),
            CacheType.COMPARISON: CacheEntryConfig(ttl_seconds=600, max_size=100),
            CacheType.HYBRID: CacheEntryConfig(ttl_seconds=300, max_size=300),
        },
        description="Per-query-type cache configuration",
    )

    @model_validator(mode="after")
    def validate_cache_types(self) -> "CacheConfig":
        """Ensure all cache types have configurations."""
        for cache_type in CacheType:
            if cache_type not in self.cache_types:
                self.cache_types[cache_type] = CacheEntryConfig()
        return self

    def get_config_for_type(self, cache_type: CacheType) -> CacheEntryConfig:
        """
        Get configuration for a specific cache type.

        Args:
            cache_type: The type of cache query

        Returns:
            CacheEntryConfig for the specified type
        """
        return self.cache_types.get(cache_type, CacheEntryConfig())

    def get_ttl(self, cache_type: CacheType) -> int:
        """
        Get TTL for a specific cache type.

        Args:
            cache_type: The type of cache query

        Returns:
            TTL in seconds
        """
        config = self.get_config_for_type(cache_type)
        return config.ttl_seconds if config.enabled else 0

    def get_max_size(self, cache_type: CacheType) -> int:
        """
        Get max size for a specific cache type.

        Args:
            cache_type: The type of cache query

        Returns:
            Maximum cache size
        """
        config = self.get_config_for_type(cache_type)
        return config.max_size

    def is_enabled(self, cache_type: CacheType) -> bool:
        """
        Check if caching is enabled for a specific type.

        Args:
            cache_type: The type of cache query

        Returns:
            True if caching is enabled for this type
        """
        if not self.enabled:
            return False
        config = self.get_config_for_type(cache_type)
        return config.enabled

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of cache config
        """
        return {
            "enabled": self.enabled,
            "default_ttl_seconds": self.default_ttl_seconds,
            "default_max_size": self.default_max_size,
            "cache_empty_results": self.cache_empty_results,
            "cache_types": {k.value: v.model_dump() for k, v in self.cache_types.items()},
        }


def get_default_cache_config() -> CacheConfig:
    """
    Get default cache configuration.

    Returns:
        Default CacheConfig instance
    """
    return CacheConfig()
