"""
Unit tests for the cache module.

Tests CacheConfig, QueryCache, cache key generation, and timeout wrappers.
"""

import asyncio

import pytest

from src.agentic_rag.cache import (
    CacheConfig,
    CacheEntryConfig,
    CacheStats,
    CacheType,
    QueryCache,
    generate_cache_key,
    get_default_cache_config,
    get_query_cache,
    reset_query_cache,
    timeout_wrapper,
    with_cache,
    with_timeout,
)


class TestCacheConfig:
    """Tests for CacheConfig model."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CacheConfig()

        assert config.enabled is True
        assert config.default_ttl_seconds == 300
        assert config.default_max_size == 500
        assert config.cache_empty_results is True

    def test_config_validation(self) -> None:
        """Test configuration validation."""
        # Valid TTL
        config = CacheConfig(default_ttl_seconds=60)
        assert config.default_ttl_seconds == 60

        # TTL too low
        with pytest.raises(ValueError):
            CacheConfig(default_ttl_seconds=5)

        # TTL too high
        with pytest.raises(ValueError):
            CacheConfig(default_ttl_seconds=4000)

    def test_cache_types_initialized(self) -> None:
        """Test all cache types are initialized."""
        config = CacheConfig()

        for cache_type in CacheType:
            assert cache_type in config.cache_types
            assert isinstance(config.cache_types[cache_type], CacheEntryConfig)

    def test_get_config_for_type(self) -> None:
        """Test getting config for specific cache type."""
        config = CacheConfig()

        multi_hop_config = config.get_config_for_type(CacheType.MULTI_HOP)
        assert isinstance(multi_hop_config, CacheEntryConfig)
        assert multi_hop_config.ttl_seconds == 600  # Default for MULTI_HOP

    def test_get_ttl(self) -> None:
        """Test getting TTL for cache type."""
        config = CacheConfig()

        ttl = config.get_ttl(CacheType.VECTOR_SEARCH)
        assert ttl == 300

    def test_get_max_size(self) -> None:
        """Test getting max size for cache type."""
        config = CacheConfig()

        max_size = config.get_max_size(CacheType.VECTOR_SEARCH)
        assert max_size == 500

    def test_is_enabled(self) -> None:
        """Test cache enabled check."""
        config = CacheConfig(enabled=True)
        assert config.is_enabled(CacheType.VECTOR_SEARCH) is True

        config = CacheConfig(enabled=False)
        assert config.is_enabled(CacheType.VECTOR_SEARCH) is False

    def test_to_dict(self) -> None:
        """Test config serialization."""
        config = CacheConfig()
        result = config.to_dict()

        assert "enabled" in result
        assert "default_ttl_seconds" in result
        assert "cache_types" in result
        assert isinstance(result["cache_types"], dict)


class TestCacheEntryConfig:
    """Tests for CacheEntryConfig model."""

    def test_default_entry_config(self) -> None:
        """Test default entry configuration."""
        entry = CacheEntryConfig()

        assert entry.enabled is True
        assert entry.ttl_seconds == 300
        assert entry.max_size == 100

    def test_custom_entry_config(self) -> None:
        """Test custom entry configuration."""
        entry = CacheEntryConfig(enabled=False, ttl_seconds=600, max_size=200)

        assert entry.enabled is False
        assert entry.ttl_seconds == 600
        assert entry.max_size == 200


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_default_stats(self) -> None:
        """Test default statistics."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.total_requests == 0

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        stats = CacheStats(hits=75, misses=25, total_requests=100)

        assert stats.hit_rate == 75.0

    def test_hit_rate_zero_requests(self) -> None:
        """Test hit rate with zero requests."""
        stats = CacheStats()

        assert stats.hit_rate == 0.0

    def test_to_dict(self) -> None:
        """Test stats serialization."""
        stats = CacheStats(hits=10, misses=5, total_requests=15)
        result = stats.to_dict()

        assert result["hits"] == 10
        assert result["misses"] == 5
        assert result["hit_rate_percent"] == pytest.approx(66.67, rel=0.1)


class TestQueryCache:
    """Tests for QueryCache class."""

    def setup_method(self) -> None:
        """Reset cache before each test."""
        reset_query_cache()

    def test_cache_initialization(self) -> None:
        """Test cache initialization."""
        cache = QueryCache()

        assert cache.config.enabled is True
        assert len(cache._caches) > 0

    def test_cache_get_miss(self) -> None:
        """Test cache miss."""
        cache = QueryCache()

        hit, value = cache.get(CacheType.VECTOR_SEARCH, "nonexistent_key")

        assert hit is False
        assert value is None

    def test_cache_set_and_get(self) -> None:
        """Test cache set and get."""
        cache = QueryCache()
        test_value = {"result": "test_data"}

        # Set value
        success = cache.set(CacheType.VECTOR_SEARCH, "test_key", test_value)
        assert success is True

        # Get value
        hit, value = cache.get(CacheType.VECTOR_SEARCH, "test_key")
        assert hit is True
        assert value == test_value

    def test_cache_disabled(self) -> None:
        """Test cache when disabled."""
        config = CacheConfig(enabled=False)
        cache = QueryCache(config)

        # Set should return False
        success = cache.set(CacheType.VECTOR_SEARCH, "test_key", "value")
        assert success is False

        # Get should return miss
        hit, _value = cache.get(CacheType.VECTOR_SEARCH, "test_key")
        assert hit is False

    def test_cache_invalidate_key(self) -> None:
        """Test invalidating specific key."""
        cache = QueryCache()
        cache.set(CacheType.VECTOR_SEARCH, "test_key", "value")

        count = cache.invalidate(CacheType.VECTOR_SEARCH, "test_key")
        assert count == 1

        hit, _ = cache.get(CacheType.VECTOR_SEARCH, "test_key")
        assert hit is False

    def test_cache_invalidate_type(self) -> None:
        """Test invalidating entire cache type."""
        cache = QueryCache()
        cache.set(CacheType.VECTOR_SEARCH, "key1", "value1")
        cache.set(CacheType.VECTOR_SEARCH, "key2", "value2")

        count = cache.invalidate(CacheType.VECTOR_SEARCH)
        assert count == 2

    def test_cache_invalidate_all(self) -> None:
        """Test invalidating all caches."""
        cache = QueryCache()
        cache.set(CacheType.VECTOR_SEARCH, "key1", "value1")
        cache.set(CacheType.MULTI_HOP, "key2", "value2")

        count = cache.invalidate_all()
        assert count >= 2

    def test_cache_stats(self) -> None:
        """Test cache statistics."""
        cache = QueryCache()

        # Generate some activity
        cache.set(CacheType.VECTOR_SEARCH, "key", "value")
        cache.get(CacheType.VECTOR_SEARCH, "key")  # Hit
        cache.get(CacheType.VECTOR_SEARCH, "missing")  # Miss

        stats = cache.get_stats(CacheType.VECTOR_SEARCH)
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2

    def test_cache_current_size(self) -> None:
        """Test getting current cache size."""
        cache = QueryCache()

        cache.set(CacheType.VECTOR_SEARCH, "key1", "value1")
        cache.set(CacheType.VECTOR_SEARCH, "key2", "value2")

        size = cache.get_current_size(CacheType.VECTOR_SEARCH)
        assert size == 2

    def test_skip_empty_results(self) -> None:
        """Test skipping empty results when configured."""
        config = CacheConfig(cache_empty_results=False)
        cache = QueryCache(config)

        # Empty list should not be cached
        success = cache.set(CacheType.VECTOR_SEARCH, "empty_key", [])
        assert success is False

        # Non-empty should be cached
        success = cache.set(CacheType.VECTOR_SEARCH, "full_key", ["item"])
        assert success is True


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_basic_key_generation(self) -> None:
        """Test basic key generation."""
        key = generate_cache_key("test query")

        assert isinstance(key, str)
        assert len(key) == 64  # SHA-256 hex length

    def test_deterministic_keys(self) -> None:
        """Test keys are deterministic."""
        key1 = generate_cache_key("test query", {"limit": 10})
        key2 = generate_cache_key("test query", {"limit": 10})

        assert key1 == key2

    def test_different_params_different_keys(self) -> None:
        """Test different params produce different keys."""
        key1 = generate_cache_key("test query", {"limit": 10})
        key2 = generate_cache_key("test query", {"limit": 20})

        assert key1 != key2

    def test_prefix_affects_key(self) -> None:
        """Test prefix affects key."""
        key1 = generate_cache_key("query", prefix="vector")
        key2 = generate_cache_key("query", prefix="graph")

        assert key1 != key2

    def test_case_insensitive_query(self) -> None:
        """Test query is normalized to lowercase."""
        key1 = generate_cache_key("TEST QUERY")
        key2 = generate_cache_key("test query")

        assert key1 == key2

    def test_param_ordering_independent(self) -> None:
        """Test parameter ordering doesn't affect key."""
        key1 = generate_cache_key("query", {"a": 1, "b": 2})
        key2 = generate_cache_key("query", {"b": 2, "a": 1})

        assert key1 == key2


class TestSingletonCache:
    """Tests for global cache singleton."""

    def setup_method(self) -> None:
        """Reset cache before each test."""
        reset_query_cache()

    def test_get_query_cache_singleton(self) -> None:
        """Test singleton behavior."""
        cache1 = get_query_cache()
        cache2 = get_query_cache()

        assert cache1 is cache2

    def test_reset_query_cache(self) -> None:
        """Test cache reset."""
        cache1 = get_query_cache()
        reset_query_cache()
        cache2 = get_query_cache()

        assert cache1 is not cache2


class TestTimeoutWrapper:
    """Tests for timeout wrapper decorator."""

    @pytest.mark.asyncio
    async def test_with_timeout_success(self) -> None:
        """Test successful execution within timeout."""

        async def fast_coro() -> str:
            return "success"

        result = await with_timeout(fast_coro(), timeout_seconds=1.0)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_with_timeout_exceeded(self) -> None:
        """Test timeout exceeded."""

        async def slow_coro() -> str:
            await asyncio.sleep(2.0)
            return "never reached"

        result = await with_timeout(slow_coro(), timeout_seconds=0.1, fallback="fallback")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_with_timeout_callback(self) -> None:
        """Test timeout with callback."""
        callback_called = False

        def on_timeout() -> str:
            nonlocal callback_called
            callback_called = True
            return "from_callback"

        async def slow_coro() -> str:
            await asyncio.sleep(2.0)
            return "never reached"

        result = await with_timeout(slow_coro(), timeout_seconds=0.1, on_timeout=on_timeout)
        assert result == "from_callback"
        assert callback_called is True

    @pytest.mark.asyncio
    async def test_timeout_wrapper_decorator(self) -> None:
        """Test timeout_wrapper decorator."""

        @timeout_wrapper(timeout_seconds=0.1, fallback="timeout_fallback")
        async def slow_function() -> str:
            await asyncio.sleep(2.0)
            return "never reached"

        result = await slow_function()
        assert result == "timeout_fallback"


class TestWithCacheDecorator:
    """Tests for with_cache decorator."""

    def setup_method(self) -> None:
        """Reset cache before each test."""
        reset_query_cache()

    @pytest.mark.asyncio
    async def test_with_cache_decorator(self) -> None:
        """Test caching decorator."""
        call_count = 0

        @with_cache(CacheType.VECTOR_SEARCH, key_prefix="test")
        async def cached_function(query: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": query, "call": call_count}

        # First call - should execute function
        result1 = await cached_function("test query")
        assert result1["call"] == 1

        # Second call - should return cached result
        result2 = await cached_function("test query")
        assert result2["call"] == 1  # Same as first call
        assert call_count == 1  # Function only called once

    @pytest.mark.asyncio
    async def test_with_cache_different_queries(self) -> None:
        """Test caching with different queries."""
        call_count = 0

        @with_cache(CacheType.VECTOR_SEARCH, key_prefix="test")
        async def cached_function(query: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": query, "call": call_count}

        result1 = await cached_function("query1")
        result2 = await cached_function("query2")

        assert result1["call"] == 1
        assert result2["call"] == 2
        assert call_count == 2  # Function called twice for different queries


class TestGetDefaultCacheConfig:
    """Tests for get_default_cache_config function."""

    def test_returns_config(self) -> None:
        """Test function returns CacheConfig."""
        config = get_default_cache_config()

        assert isinstance(config, CacheConfig)
        assert config.enabled is True
