"""
Query result caching with TTL-based LRU eviction.

Provides a thread-safe, async-compatible caching layer for query results
with configurable TTL, size limits, and performance logging.
"""

import asyncio
import hashlib
import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import structlog
from cachetools import TTLCache  # type: ignore[import-untyped]

from .config import CacheConfig, CacheType, get_default_cache_config

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    cache_type: CacheType = CacheType.HYBRID

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "cache_type": self.cache_type.value,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "total_requests": self.total_requests,
            "hit_rate_percent": round(self.hit_rate, 2),
        }


class QueryCache:
    """
    Thread-safe query result cache with TTL-based LRU eviction.

    Provides caching for different query types with configurable TTL and size limits.
    Uses cachetools.TTLCache for efficient time-based expiration.

    Attributes:
        config: Cache configuration settings
        _caches: Dictionary of TTLCache instances per cache type
        _stats: Dictionary of CacheStats per cache type
        _lock: Thread lock for thread-safe operations
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        """
        Initialize QueryCache with configuration.

        Args:
            config: Optional CacheConfig, uses defaults if not provided
        """
        self.config = config or get_default_cache_config()
        self._caches: dict[CacheType, TTLCache[str, Any]] = {}
        self._stats: dict[CacheType, CacheStats] = {}
        self._lock = threading.RLock()

        self._initialize_caches()
        logger.info(
            "QueryCache initialized",
            enabled=self.config.enabled,
            cache_types=len(self._caches),
        )

    def _initialize_caches(self) -> None:
        """Initialize TTLCache instances for each cache type."""
        for cache_type in CacheType:
            if self.config.is_enabled(cache_type):
                ttl = self.config.get_ttl(cache_type)
                max_size = self.config.get_max_size(cache_type)
                self._caches[cache_type] = TTLCache(maxsize=max_size, ttl=ttl)
                self._stats[cache_type] = CacheStats(cache_type=cache_type)
                logger.debug(
                    "Cache initialized",
                    cache_type=cache_type.value,
                    ttl_seconds=ttl,
                    max_size=max_size,
                )

    def get(
        self,
        cache_type: CacheType,
        key: str,
    ) -> tuple[bool, Any]:
        """
        Get a value from cache.

        Args:
            cache_type: Type of cache to query
            key: Cache key

        Returns:
            Tuple of (hit: bool, value: Any)
        """
        if not self.config.is_enabled(cache_type):
            return False, None

        with self._lock:
            cache = self._caches.get(cache_type)
            stats = self._stats.get(cache_type)

            if cache is None or stats is None:
                return False, None

            stats.total_requests += 1

            try:
                value = cache[key]
                stats.hits += 1
                logger.debug(
                    "Cache hit",
                    cache_type=cache_type.value,
                    key_hash=key[:16],
                    hit_rate=f"{stats.hit_rate:.1f}%",
                )
                return True, value
            except KeyError:
                stats.misses += 1
                logger.debug(
                    "Cache miss",
                    cache_type=cache_type.value,
                    key_hash=key[:16],
                )
                return False, None

    def set(
        self,
        cache_type: CacheType,
        key: str,
        value: Any,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            cache_type: Type of cache
            key: Cache key
            value: Value to cache

        Returns:
            True if value was cached, False otherwise
        """
        if not self.config.is_enabled(cache_type):
            return False

        # Skip empty results if configured
        if not self.config.cache_empty_results and self._is_empty_result(value):
            logger.debug(
                "Skipping empty result",
                cache_type=cache_type.value,
            )
            return False

        with self._lock:
            cache = self._caches.get(cache_type)
            if cache is None:
                return False

            # Track evictions
            pre_size = len(cache)
            cache[key] = value
            post_size = len(cache)

            if post_size <= pre_size and pre_size > 0:
                stats = self._stats.get(cache_type)
                if stats:
                    stats.evictions += 1

            logger.debug(
                "Cache set",
                cache_type=cache_type.value,
                key_hash=key[:16],
                cache_size=post_size,
            )
            return True

    def _is_empty_result(self, value: Any) -> bool:
        """Check if a result is considered empty."""
        if value is None:
            return True
        if isinstance(value, list | dict) and len(value) == 0:
            return True
        return hasattr(value, "__len__") and len(value) == 0

    def invalidate(self, cache_type: CacheType, key: str | None = None) -> int:
        """
        Invalidate cache entries.

        Args:
            cache_type: Type of cache to invalidate
            key: Optional specific key to invalidate. If None, clears entire cache type.

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            cache = self._caches.get(cache_type)
            if cache is None:
                return 0

            if key is None:
                count = len(cache)
                cache.clear()
                logger.info(
                    "Cache cleared",
                    cache_type=cache_type.value,
                    entries_cleared=count,
                )
                return count
            if key in cache:
                del cache[key]
                logger.debug(
                    "Cache entry invalidated",
                    cache_type=cache_type.value,
                    key_hash=key[:16],
                )
                return 1
            return 0

    def invalidate_all(self) -> int:
        """
        Invalidate all cache entries across all cache types.

        Returns:
            Total number of entries invalidated
        """
        total = 0
        for cache_type in CacheType:
            total += self.invalidate(cache_type)
        logger.info("All caches cleared", total_entries_cleared=total)
        return total

    def get_stats(self, cache_type: CacheType | None = None) -> dict[str, Any]:
        """
        Get cache statistics.

        Args:
            cache_type: Optional specific cache type. If None, returns all stats.

        Returns:
            Dictionary of cache statistics
        """
        with self._lock:
            if cache_type is not None:
                stats = self._stats.get(cache_type)
                if stats:
                    return stats.to_dict()
                return {}

            return {ct.value: stats.to_dict() for ct, stats in self._stats.items()}

    def get_current_size(self, cache_type: CacheType) -> int:
        """
        Get current number of entries in cache.

        Args:
            cache_type: Type of cache

        Returns:
            Number of entries
        """
        with self._lock:
            cache = self._caches.get(cache_type)
            return len(cache) if cache else 0

    def get_prometheus_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get cache statistics formatted for Prometheus export.

        Returns statistics for all cache types in a format suitable for
        CacheMetricsCollector.collect().

        Returns:
            Dictionary mapping cache type names to their stats:
            {
                "cache_type_name": {
                    "hits": int,
                    "misses": int,
                    "evictions": int,
                    "hit_rate_percent": float,
                    "current_size": int,
                },
                ...
            }
        """
        with self._lock:
            result: dict[str, dict[str, Any]] = {}

            for cache_type, stats in self._stats.items():
                cache = self._caches.get(cache_type)
                current_size = len(cache) if cache else 0

                result[cache_type.value] = {
                    "hits": stats.hits,
                    "misses": stats.misses,
                    "evictions": stats.evictions,
                    "hit_rate_percent": round(stats.hit_rate, 2),
                    "current_size": current_size,
                }

            return result

    def update_config(self, config: CacheConfig) -> None:
        """
        Update cache configuration (reinitializes caches).

        Args:
            config: New cache configuration
        """
        with self._lock:
            old_stats = self._stats.copy()
            self.config = config
            self._caches.clear()
            self._stats.clear()
            self._initialize_caches()

            # Preserve stats where applicable
            for cache_type, stats in old_stats.items():
                if cache_type in self._stats:
                    self._stats[cache_type] = stats

            logger.info("Cache config updated", enabled=config.enabled)


def generate_cache_key(
    query: str,
    params: dict[str, Any] | None = None,
    prefix: str = "",
) -> str:
    """
    Generate a deterministic cache key from query and parameters.

    Uses SHA-256 hashing for consistent key generation regardless of
    parameter ordering.

    Args:
        query: The query string
        params: Optional query parameters
        prefix: Optional prefix for key namespacing

    Returns:
        Hexadecimal cache key string
    """
    # Normalize query
    normalized_query = query.strip().lower()

    # Sort and serialize parameters for deterministic hashing
    if params:
        sorted_params = json.dumps(params, sort_keys=True, default=str)
    else:
        sorted_params = ""

    # Combine and hash
    combined = f"{prefix}:{normalized_query}:{sorted_params}"
    key_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    return key_hash


# Global cache instance (singleton)
_query_cache: QueryCache | None = None
_cache_lock = threading.Lock()


def get_query_cache(config: CacheConfig | None = None) -> QueryCache:
    """
    Get the global QueryCache instance (singleton).

    Args:
        config: Optional configuration for initialization

    Returns:
        QueryCache instance
    """
    global _query_cache

    with _cache_lock:
        if _query_cache is None:
            _query_cache = QueryCache(config)
        return _query_cache


def reset_query_cache() -> None:
    """Reset the global cache instance (for testing)."""
    global _query_cache
    with _cache_lock:
        _query_cache = None


def with_cache(
    cache_type: CacheType,
    key_prefix: str = "",
    param_keys: list[str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for caching async function results.

    Args:
        cache_type: Type of cache to use
        key_prefix: Optional prefix for cache keys
        param_keys: List of parameter names to include in cache key

    Returns:
        Decorated function with caching
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = get_query_cache()

            # Build cache key from specified parameters
            params_for_key: dict[str, Any] = {}
            if param_keys:
                for key in param_keys:
                    if key in kwargs:
                        params_for_key[key] = kwargs[key]

            # Use first string argument as query if available
            query = ""
            for arg in args:
                if isinstance(arg, str):
                    query = arg
                    break
            if not query and "query" in kwargs:
                query = str(kwargs.get("query", ""))

            cache_key = generate_cache_key(
                query=query,
                params=params_for_key,
                prefix=f"{key_prefix}:{func.__name__}",
            )

            # Try cache first
            hit, cached_value = cache.get(cache_type, cache_key)
            if hit:
                return cached_value

            # Execute function
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)  # type: ignore[misc]
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Cache result
            cache.set(cache_type, cache_key, result)

            logger.debug(
                "Cached function result",
                function=func.__name__,
                cache_type=cache_type.value,
                elapsed_ms=round(elapsed_ms, 2),
            )

            return result

        return wrapper  # type: ignore[return-value]

    return decorator


async def with_timeout(
    coro: Any,
    timeout_seconds: float,
    fallback: Any = None,
    on_timeout: Callable[[], Any] | None = None,
) -> Any:
    """
    Execute a coroutine with timeout and graceful fallback.

    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds
        fallback: Value to return on timeout
        on_timeout: Optional callback to execute on timeout

    Returns:
        Coroutine result or fallback value
    """
    try:
        async with asyncio.timeout(timeout_seconds):
            return await coro
    except TimeoutError:
        logger.warning(
            "Query timeout",
            timeout_seconds=timeout_seconds,
            fallback_used=fallback is not None or on_timeout is not None,
        )
        if on_timeout:
            return on_timeout()
        return fallback


def timeout_wrapper(
    timeout_seconds: float,
    fallback: Any = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for adding timeout with graceful degradation to async functions.

    Args:
        timeout_seconds: Timeout in seconds
        fallback: Value to return on timeout

    Returns:
        Decorated function with timeout handling
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                async with asyncio.timeout(timeout_seconds):
                    return await func(*args, **kwargs)  # type: ignore[misc]
            except TimeoutError:
                logger.warning(
                    "Function timeout",
                    function=func.__name__,
                    timeout_seconds=timeout_seconds,
                )
                return fallback

        return wrapper  # type: ignore[return-value]

    return decorator
