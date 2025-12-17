"""
Comprehensive tests for cache utilities.

Tests:
- RedisCache initialization
- Key generation
- Get/Set/Delete operations
- Flush operations
- Exists checks
- Increment operations
- Health checks
- Global cache instance
- Cache decorator (async and sync)
- Cache invalidation
"""

import pickle
from unittest.mock import Mock, patch

import pytest

from src.utils.cache import (
    RedisCache,
    get_cache,
    invalidate_cache,
)
from src.utils.cache import (
    cache as cache_decorator,
)


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    client = Mock()
    client.ping.return_value = True
    client.get.return_value = None
    client.setex.return_value = True
    client.delete.return_value = 1
    client.exists.return_value = False
    client.incr.return_value = 1
    client.flushdb.return_value = True
    return client


@pytest.fixture
def mock_connection_pool():
    """Create mock connection pool."""
    with patch("src.utils.cache.ConnectionPool") as mock_pool:
        pool_instance = Mock()
        mock_pool.from_url.return_value = pool_instance
        yield mock_pool


class TestRedisCacheInitialization:
    """Test RedisCache initialization."""

    def test_init_with_redis_connection(self, mock_connection_pool):
        """Test initialization with successful Redis connection."""
        with patch("src.utils.cache.redis.Redis") as mock_redis_class:
            with patch("src.utils.cache.get_settings") as mock_settings:
                mock_settings.return_value = Mock(redis_url="redis://localhost:6381")
                mock_redis_class.return_value.ping.return_value = True

                cache = RedisCache()

                assert cache._redis_client is not None
                assert cache.ttl == 3600
                assert cache.enable_fallback is True

    def test_init_with_custom_ttl(self, mock_connection_pool):
        """Test initialization with custom TTL."""
        with patch("src.utils.cache.redis.Redis") as mock_redis_class:
            with patch("src.utils.cache.get_settings") as mock_settings:
                mock_settings.return_value = Mock(redis_url="redis://localhost:6381")
                mock_redis_class.return_value.ping.return_value = True

                cache = RedisCache(ttl=7200)

                assert cache.ttl == 7200

    def test_init_with_redis_connection_failure_fallback(self):
        """Test initialization falls back to memory cache on Redis failure."""
        with patch("src.utils.cache.redis.Redis") as mock_redis_class:
            with patch("src.utils.cache.get_settings") as mock_settings:
                mock_settings.return_value = Mock(redis_url="redis://localhost:6381")
                mock_redis_class.side_effect = Exception("Connection failed")

                cache = RedisCache(enable_fallback=True)

                assert cache._redis_client is None
                assert cache.enable_fallback is True
                assert isinstance(cache._memory_cache, dict)

    def test_init_with_redis_failure_no_fallback(self):
        """Test initialization raises exception when fallback is disabled."""
        with patch("src.utils.cache.redis.Redis") as mock_redis_class:
            with patch("src.utils.cache.get_settings") as mock_settings:
                mock_settings.return_value = Mock(redis_url="redis://localhost:6381")
                mock_redis_class.side_effect = Exception("Connection failed")

                with pytest.raises(Exception) as exc_info:
                    RedisCache(enable_fallback=False)

                assert "Connection failed" in str(exc_info.value)


class TestKeyGeneration:
    """Test cache key generation."""

    def test_generate_key_simple(self):
        """Test generating key with simple arguments."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None  # Disable Redis

        key = cache._generate_key("test", "arg1", "arg2")

        assert key.startswith("test:")
        assert len(key) > 5  # Has hash

    def test_generate_key_with_kwargs(self):
        """Test generating key with kwargs."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None

        key = cache._generate_key("test", arg1="value1", arg2="value2")

        assert key.startswith("test:")

    def test_generate_key_consistent(self):
        """Test key generation is consistent."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None

        key1 = cache._generate_key("test", "arg1", kwarg1="value1")
        key2 = cache._generate_key("test", "arg1", kwarg1="value1")

        assert key1 == key2

    def test_generate_key_different_for_different_args(self):
        """Test keys differ for different arguments."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None

        key1 = cache._generate_key("test", "arg1")
        key2 = cache._generate_key("test", "arg2")

        assert key1 != key2


class TestCacheGet:
    """Test cache get operations."""

    def test_get_from_redis(self, mock_redis_client):
        """Test getting value from Redis."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client

        test_value = {"data": "test"}
        mock_redis_client.get.return_value = pickle.dumps(test_value)

        result = cache.get("test_key")

        assert result == test_value
        mock_redis_client.get.assert_called_once_with("test_key")

    def test_get_cache_miss(self, mock_redis_client):
        """Test cache miss returns None."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        mock_redis_client.get.return_value = None

        result = cache.get("nonexistent_key")

        assert result is None

    def test_get_from_fallback_cache(self):
        """Test getting value from fallback memory cache."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None
        cache._memory_cache["test_key"] = "test_value"

        result = cache.get("test_key")

        assert result == "test_value"

    def test_get_redis_error_fallback(self, mock_redis_client):
        """Test fallback to memory cache on Redis error."""
        from redis.exceptions import RedisError

        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        cache._memory_cache["test_key"] = "fallback_value"
        mock_redis_client.get.side_effect = RedisError("Connection lost")

        result = cache.get("test_key")

        assert result == "fallback_value"


class TestCacheSet:
    """Test cache set operations."""

    def test_set_to_redis(self, mock_redis_client):
        """Test setting value in Redis."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        mock_redis_client.setex.return_value = True

        result = cache.set("test_key", "test_value")

        assert result is True
        mock_redis_client.setex.assert_called_once()

    def test_set_with_custom_ttl(self, mock_redis_client):
        """Test setting value with custom TTL."""
        cache = RedisCache(ttl=3600, enable_fallback=True)
        cache._redis_client = mock_redis_client

        cache.set("test_key", "test_value", ttl=7200)

        # Verify TTL was passed
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][1] == 7200  # TTL parameter

    def test_set_to_fallback_cache(self):
        """Test setting value in fallback memory cache."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None

        result = cache.set("test_key", "test_value")

        assert result is True
        assert cache._memory_cache["test_key"] == "test_value"

    def test_set_fallback_memory_limit(self):
        """Test memory cache size limit enforcement."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None

        # Fill beyond limit
        for i in range(10100):
            cache._memory_cache[f"key_{i}"] = f"value_{i}"

        cache.set("new_key", "new_value")

        # Should have removed old entries
        assert len(cache._memory_cache) < 10100

    def test_set_redis_error_fallback(self, mock_redis_client):
        """Test fallback to memory cache on Redis error."""
        from redis.exceptions import RedisError

        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        mock_redis_client.setex.side_effect = RedisError("Connection lost")

        result = cache.set("test_key", "test_value")

        assert result is True
        assert cache._memory_cache["test_key"] == "test_value"


class TestCacheDelete:
    """Test cache delete operations."""

    def test_delete_from_redis(self, mock_redis_client):
        """Test deleting value from Redis."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        mock_redis_client.delete.return_value = 1

        result = cache.delete("test_key")

        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_key")

    def test_delete_from_fallback_cache(self):
        """Test deleting value from fallback memory cache."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None
        cache._memory_cache["test_key"] = "test_value"

        result = cache.delete("test_key")

        assert result is True
        assert "test_key" not in cache._memory_cache

    def test_delete_redis_error_fallback(self, mock_redis_client):
        """Test fallback to memory cache on Redis error."""
        from redis.exceptions import RedisError

        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        cache._memory_cache["test_key"] = "test_value"
        mock_redis_client.delete.side_effect = RedisError("Connection lost")

        result = cache.delete("test_key")

        assert result is True
        assert "test_key" not in cache._memory_cache


class TestCacheFlush:
    """Test cache flush operations."""

    def test_flush_redis(self, mock_redis_client):
        """Test flushing Redis cache."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        cache._memory_cache["key"] = "value"

        result = cache.flush()

        assert result is True
        mock_redis_client.flushdb.assert_called_once()
        assert len(cache._memory_cache) == 0

    def test_flush_fallback_only(self):
        """Test flushing fallback cache only."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None
        cache._memory_cache["key1"] = "value1"
        cache._memory_cache["key2"] = "value2"

        result = cache.flush()

        assert result is True
        assert len(cache._memory_cache) == 0

    def test_flush_redis_error(self, mock_redis_client):
        """Test flush handles Redis errors."""
        from redis.exceptions import RedisError

        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        mock_redis_client.flushdb.side_effect = RedisError("Flush failed")

        result = cache.flush()

        assert result is False


class TestCacheExists:
    """Test cache exists checks."""

    def test_exists_in_redis(self, mock_redis_client):
        """Test checking if key exists in Redis."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        mock_redis_client.exists.return_value = 1

        result = cache.exists("test_key")

        assert result is True
        mock_redis_client.exists.assert_called_once_with("test_key")

    def test_exists_in_fallback_cache(self):
        """Test checking if key exists in fallback cache."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None
        cache._memory_cache["test_key"] = "test_value"

        result = cache.exists("test_key")

        assert result is True

    def test_not_exists(self, mock_redis_client):
        """Test checking non-existent key."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        mock_redis_client.exists.return_value = 0

        result = cache.exists("nonexistent_key")

        assert result is False


class TestCacheIncr:
    """Test cache increment operations."""

    def test_incr_in_redis(self, mock_redis_client):
        """Test incrementing counter in Redis."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        mock_redis_client.incr.return_value = 5

        result = cache.incr("counter", amount=1)

        assert result == 5
        mock_redis_client.incr.assert_called_once_with("counter", 1)

    def test_incr_in_fallback_cache(self):
        """Test incrementing counter in fallback cache."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None
        cache._memory_cache["counter"] = 10

        result = cache.incr("counter", amount=5)

        assert result == 15
        assert cache._memory_cache["counter"] == 15

    def test_incr_new_key_in_fallback(self):
        """Test incrementing new key starts from 0."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None

        result = cache.incr("new_counter", amount=3)

        assert result == 3
        assert cache._memory_cache["new_counter"] == 3


class TestHealthCheck:
    """Test cache health checks."""

    def test_health_check_redis_healthy(self, mock_redis_client):
        """Test health check with healthy Redis."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = mock_redis_client
        mock_redis_client.ping.return_value = True

        result = cache.health_check()

        assert result is True

    def test_health_check_fallback_mode(self):
        """Test health check in fallback mode."""
        cache = RedisCache(enable_fallback=True)
        cache._redis_client = None

        result = cache.health_check()

        assert result is True  # Fallback mode is considered healthy

    def test_health_check_redis_down(self, mock_redis_client):
        """Test health check with Redis down."""
        cache = RedisCache(enable_fallback=False)
        cache._redis_client = mock_redis_client
        mock_redis_client.ping.side_effect = Exception("Connection failed")

        result = cache.health_check()

        assert result is False


class TestGlobalCacheInstance:
    """Test global cache instance."""

    def test_get_cache_creates_instance(self):
        """Test get_cache creates global instance."""
        with patch("src.utils.cache._cache_instance", None):
            with patch("src.utils.cache.RedisCache") as mock_cache_class:
                mock_instance = Mock()
                mock_cache_class.return_value = mock_instance

                result = get_cache()

                assert result == mock_instance

    def test_get_cache_reuses_instance(self):
        """Test get_cache reuses existing instance."""
        existing_instance = Mock()

        with patch("src.utils.cache._cache_instance", existing_instance):
            result = get_cache()

            assert result == existing_instance


class TestCacheDecorator:
    """Test cache decorator."""

    @pytest.mark.asyncio
    async def test_cache_decorator_async_cache_miss(self):
        """Test cache decorator with async function (cache miss)."""
        with patch("src.utils.cache.get_cache") as mock_get_cache:
            mock_cache = Mock()
            mock_cache.get.return_value = None
            mock_cache.set = Mock()
            mock_cache._generate_key.return_value = "test_key"
            mock_get_cache.return_value = mock_cache

            @cache_decorator(prefix="test", ttl=300)
            async def test_func(arg1):
                return f"result_{arg1}"

            result = await test_func("value1")

            assert result == "result_value1"
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_decorator_async_cache_hit(self):
        """Test cache decorator with async function (cache hit)."""
        with patch("src.utils.cache.get_cache") as mock_get_cache:
            mock_cache = Mock()
            mock_cache.get.return_value = "cached_result"
            mock_cache._generate_key.return_value = "test_key"
            mock_get_cache.return_value = mock_cache

            @cache_decorator(prefix="test")
            async def test_func(arg1):
                return f"result_{arg1}"

            result = await test_func("value1")

            assert result == "cached_result"
            mock_cache.get.assert_called_once()
            # Should not call set on cache hit

    def test_cache_decorator_sync_cache_miss(self):
        """Test cache decorator with sync function (cache miss)."""
        with patch("src.utils.cache.get_cache") as mock_get_cache:
            mock_cache = Mock()
            mock_cache.get.return_value = None
            mock_cache.set = Mock()
            mock_cache._generate_key.return_value = "test_key"
            mock_get_cache.return_value = mock_cache

            @cache_decorator(prefix="test")
            def test_func(arg1):
                return f"result_{arg1}"

            result = test_func("value1")

            assert result == "result_value1"
            mock_cache.set.assert_called_once()

    def test_cache_decorator_sync_cache_hit(self):
        """Test cache decorator with sync function (cache hit)."""
        with patch("src.utils.cache.get_cache") as mock_get_cache:
            mock_cache = Mock()
            mock_cache.get.return_value = "cached_result"
            mock_cache._generate_key.return_value = "test_key"
            mock_get_cache.return_value = mock_cache

            @cache_decorator(prefix="test")
            def test_func(arg1):
                return f"result_{arg1}"

            result = test_func("value1")

            assert result == "cached_result"

    def test_cache_decorator_custom_key_func(self):
        """Test cache decorator with custom key function."""
        with patch("src.utils.cache.get_cache") as mock_get_cache:
            mock_cache = Mock()
            mock_cache.get.return_value = None
            mock_cache.set = Mock()
            mock_get_cache.return_value = mock_cache

            def custom_key_func(arg1):
                return f"custom_{arg1}"

            @cache_decorator(prefix="test", key_func=custom_key_func)
            def test_func(arg1):
                return f"result_{arg1}"

            test_func("value1")

            # Verify custom key function was used
            mock_cache.get.assert_called_once_with("custom_value1")


class TestCacheInvalidation:
    """Test cache invalidation."""

    def test_invalidate_cache_pattern(self, mock_redis_client):
        """Test invalidating cache with pattern."""
        with patch("src.utils.cache.get_cache") as mock_get_cache:
            mock_cache = Mock()
            mock_cache._redis_client = mock_redis_client
            mock_redis_client.keys.return_value = ["search:key1", "search:key2"]
            mock_redis_client.delete.return_value = 2
            mock_get_cache.return_value = mock_cache

            result = invalidate_cache("search:*")

            assert result == 2
            mock_redis_client.keys.assert_called_once_with("search:*")
            mock_redis_client.delete.assert_called_once_with("search:key1", "search:key2")

    def test_invalidate_cache_no_matches(self, mock_redis_client):
        """Test invalidating cache with no matches."""
        with patch("src.utils.cache.get_cache") as mock_get_cache:
            mock_cache = Mock()
            mock_cache._redis_client = mock_redis_client
            mock_redis_client.keys.return_value = []
            mock_get_cache.return_value = mock_cache

            result = invalidate_cache("nonexistent:*")

            assert result == 0

    def test_invalidate_cache_error(self, mock_redis_client):
        """Test invalidation error handling."""
        from redis.exceptions import RedisError

        with patch("src.utils.cache.get_cache") as mock_get_cache:
            mock_cache = Mock()
            mock_cache._redis_client = mock_redis_client
            mock_redis_client.keys.side_effect = RedisError("Connection failed")
            mock_get_cache.return_value = mock_cache

            result = invalidate_cache("test:*")

            assert result == 0
