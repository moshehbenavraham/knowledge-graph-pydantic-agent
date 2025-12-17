"""
Comprehensive tests for Redis caching utilities.

Tests cache manager with Redis and in-memory fallback.
"""

import asyncio
import pickle  # nosec B403 - pickle needed for testing cache serialization
from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from src.utils.cache import RedisCache, cache, get_cache, invalidate_cache


class TestRedisCacheClass:
    """Test RedisCache class functionality."""

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_initialization_with_redis_success(self, mock_pool, mock_redis):
        """Test successful Redis initialization."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        cache_obj = RedisCache(redis_url="redis://localhost:6381")

        assert cache_obj.ttl == 3600
        assert cache_obj.enable_fallback is True
        assert cache_obj._redis_client == mock_redis_instance
        mock_redis_instance.ping.assert_called_once()

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_initialization_with_redis_failure_fallback_enabled(self, mock_pool, mock_redis):
        """Test Redis connection failure with fallback enabled."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.side_effect = RedisConnectionError("Connection refused")

        # Should not raise, fallback to memory cache
        cache_obj = RedisCache(redis_url="redis://localhost:6381", enable_fallback=True)

        assert cache_obj._redis_client is not None
        assert cache_obj._memory_cache == {}

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_initialization_with_redis_failure_fallback_disabled(self, mock_pool, mock_redis):
        """Test Redis connection failure with fallback disabled."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.side_effect = RedisConnectionError("Connection refused")

        # Should raise exception
        with pytest.raises(RedisConnectionError):
            RedisCache(redis_url="redis://localhost:6381", enable_fallback=False)

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_initialization_custom_parameters(self, mock_pool, mock_redis):
        """Test initialization with custom parameters."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        cache_obj = RedisCache(
            redis_url="redis://localhost:6381",
            ttl=7200,
            max_connections=100,
            socket_timeout=10,
            enable_fallback=False,
        )

        assert cache_obj.ttl == 7200
        assert cache_obj.enable_fallback is False

    def test_generate_key_consistency(self):
        """Test that key generation is consistent for same inputs."""
        cache_obj = RedisCache(enable_fallback=True)

        key1 = cache_obj._generate_key("test", "arg1", "arg2", kwarg1="value1")
        key2 = cache_obj._generate_key("test", "arg1", "arg2", kwarg1="value1")

        assert key1 == key2
        assert key1.startswith("test:")

    def test_generate_key_differs_for_different_inputs(self):
        """Test that key generation differs for different inputs."""
        cache_obj = RedisCache(enable_fallback=True)

        key1 = cache_obj._generate_key("test", "arg1", kwarg1="value1")
        key2 = cache_obj._generate_key("test", "arg2", kwarg1="value1")
        key3 = cache_obj._generate_key("test", "arg1", kwarg1="value2")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_get_from_redis_success(self, mock_pool, mock_redis):
        """Test successful get from Redis."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.get.return_value = pickle.dumps({"result": "value"})

        cache_obj = RedisCache()
        result = cache_obj.get("test_key")

        assert result == {"result": "value"}
        mock_redis_instance.get.assert_called_once_with("test_key")

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_get_from_redis_not_found(self, mock_pool, mock_redis):
        """Test get from Redis when key not found."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.get.return_value = None

        cache_obj = RedisCache()
        result = cache_obj.get("nonexistent_key")

        assert result is None

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_get_redis_failure_fallback_to_memory(self, mock_pool, mock_redis):
        """Test get falls back to memory cache on Redis error."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.get.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache(enable_fallback=True)
        cache_obj._memory_cache["test_key"] = "fallback_value"

        result = cache_obj.get("test_key")

        assert result == "fallback_value"

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_set_to_redis_success(self, mock_pool, mock_redis):
        """Test successful set to Redis."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.setex.return_value = True

        cache_obj = RedisCache(ttl=1800)
        result = cache_obj.set("test_key", {"data": "value"}, ttl=3600)

        assert result is True
        mock_redis_instance.setex.assert_called_once()
        call_args = mock_redis_instance.setex.call_args
        assert call_args[0][0] == "test_key"
        assert call_args[0][1] == 3600  # Custom TTL
        assert pickle.loads(call_args[0][2]) == {
            "data": "value"
        }  # nosec B301 - testing pickle serialization with known data

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_set_to_redis_default_ttl(self, mock_pool, mock_redis):
        """Test set to Redis uses default TTL."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.setex.return_value = True

        cache_obj = RedisCache(ttl=1800)
        cache_obj.set("test_key", "value")

        call_args = mock_redis_instance.setex.call_args
        assert call_args[0][1] == 1800  # Default TTL

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_set_redis_failure_fallback_to_memory(self, mock_pool, mock_redis):
        """Test set falls back to memory cache on Redis error."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.setex.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache(enable_fallback=True)
        result = cache_obj.set("test_key", "value")

        assert result is True
        assert cache_obj._memory_cache["test_key"] == "value"

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_set_memory_cache_size_limit(self, mock_pool, mock_redis):
        """Test memory cache enforces size limit."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.setex.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache(enable_fallback=True)

        # Fill cache beyond limit
        for i in range(10100):
            cache_obj._memory_cache[f"key_{i}"] = f"value_{i}"

        # Trigger size limit logic
        cache_obj.set("overflow_key", "overflow_value")

        # Cache should be trimmed (around 9001 keys after removing 1000)
        assert len(cache_obj._memory_cache) <= 9101

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_delete_from_redis_success(self, mock_pool, mock_redis):
        """Test successful delete from Redis."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.delete.return_value = 1

        cache_obj = RedisCache()
        result = cache_obj.delete("test_key")

        assert result is True
        mock_redis_instance.delete.assert_called_once_with("test_key")

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_delete_redis_failure_fallback_to_memory(self, mock_pool, mock_redis):
        """Test delete falls back to memory cache on Redis error."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.delete.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache(enable_fallback=True)
        cache_obj._memory_cache["test_key"] = "value"

        result = cache_obj.delete("test_key")

        assert result is True
        assert "test_key" not in cache_obj._memory_cache

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_flush_success(self, mock_pool, mock_redis):
        """Test successful flush."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.flushdb.return_value = True

        cache_obj = RedisCache()
        cache_obj._memory_cache["key1"] = "value1"

        result = cache_obj.flush()

        assert result is True
        mock_redis_instance.flushdb.assert_called_once()
        assert cache_obj._memory_cache == {}

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_flush_redis_failure(self, mock_pool, mock_redis):
        """Test flush handles Redis errors."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.flushdb.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache()
        result = cache_obj.flush()

        assert result is False

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_exists_in_redis(self, mock_pool, mock_redis):
        """Test exists check in Redis."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.exists.return_value = 1

        cache_obj = RedisCache()
        result = cache_obj.exists("test_key")

        assert result is True
        mock_redis_instance.exists.assert_called_once_with("test_key")

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_exists_redis_failure_fallback_to_memory(self, mock_pool, mock_redis):
        """Test exists falls back to memory cache on Redis error."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.exists.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache(enable_fallback=True)
        cache_obj._memory_cache["test_key"] = "value"

        result = cache_obj.exists("test_key")

        assert result is True

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_incr_in_redis(self, mock_pool, mock_redis):
        """Test increment counter in Redis."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.incr.return_value = 5

        cache_obj = RedisCache()
        result = cache_obj.incr("counter_key", amount=2)

        assert result == 5
        mock_redis_instance.incr.assert_called_once_with("counter_key", 2)

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_incr_redis_failure_fallback_to_memory(self, mock_pool, mock_redis):
        """Test increment falls back to memory cache on Redis error."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.incr.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache(enable_fallback=True)
        cache_obj._memory_cache["counter_key"] = 10

        result = cache_obj.incr("counter_key", amount=3)

        assert result == 13
        assert cache_obj._memory_cache["counter_key"] == 13

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_incr_new_key_in_memory(self, mock_pool, mock_redis):
        """Test increment new key in memory cache."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.incr.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache(enable_fallback=True)

        result = cache_obj.incr("new_counter", amount=5)

        assert result == 5
        assert cache_obj._memory_cache["new_counter"] == 5

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_health_check_redis_healthy(self, mock_pool, mock_redis):
        """Test health check with healthy Redis."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        cache_obj = RedisCache()
        result = cache_obj.health_check()

        assert result is True

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_health_check_redis_unhealthy(self, mock_pool, mock_redis):
        """Test health check with unhealthy Redis."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.side_effect = [True, RedisError("Connection lost")]

        cache_obj = RedisCache()
        result = cache_obj.health_check()

        assert result is False

    def test_health_check_fallback_mode(self):
        """Test health check in fallback mode."""
        cache_obj = RedisCache(enable_fallback=True)
        cache_obj._redis_client = None

        result = cache_obj.health_check()

        assert result is True  # Fallback mode is "healthy"


class TestGlobalCacheInstance:
    """Test global cache instance management."""

    def teardown_method(self):
        """Reset global cache instance after each test."""
        import src.utils.cache

        src.utils.cache._cache_instance = None

    @patch("src.utils.cache.RedisCache")
    def test_get_cache_creates_instance(self, mock_redis_cache):
        """Test get_cache creates instance on first call."""
        mock_instance = MagicMock()
        mock_redis_cache.return_value = mock_instance

        cache_obj = get_cache()

        assert cache_obj == mock_instance
        mock_redis_cache.assert_called_once()

    @patch("src.utils.cache.RedisCache")
    def test_get_cache_reuses_instance(self, mock_redis_cache):
        """Test get_cache reuses existing instance."""
        mock_instance = MagicMock()
        mock_redis_cache.return_value = mock_instance

        cache_obj1 = get_cache()
        cache_obj2 = get_cache()

        assert cache_obj1 == cache_obj2
        mock_redis_cache.assert_called_once()  # Only one creation


class TestCacheDecorator:
    """Test cache decorator functionality."""

    def teardown_method(self):
        """Reset global cache instance after each test."""
        import src.utils.cache

        src.utils.cache._cache_instance = None

    @patch("src.utils.cache.get_cache")
    def test_decorator_on_sync_function_cache_miss(self, mock_get_cache):
        """Test cache decorator on sync function with cache miss."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        mock_cache._generate_key.return_value = "test:func:hash123"

        call_count = 0

        @cache(prefix="test", ttl=1800)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        result = expensive_function(5, 10)

        assert result == 15
        assert call_count == 1
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch("src.utils.cache.get_cache")
    def test_decorator_on_sync_function_cache_hit(self, mock_get_cache):
        """Test cache decorator on sync function with cache hit."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = 42
        mock_get_cache.return_value = mock_cache
        mock_cache._generate_key.return_value = "test:func:hash123"

        call_count = 0

        @cache(prefix="test", ttl=1800)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        result = expensive_function(5, 10)

        assert result == 42  # Cached value
        assert call_count == 0  # Function not called
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.utils.cache.get_cache")
    async def test_decorator_on_async_function_cache_miss(self, mock_get_cache):
        """Test cache decorator on async function with cache miss."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        mock_cache._generate_key.return_value = "test:async_func:hash123"

        call_count = 0

        @cache(prefix="test", ttl=1800)
        async def async_expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * y

        result = await async_expensive_function(5, 10)

        assert result == 50
        assert call_count == 1
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.utils.cache.get_cache")
    async def test_decorator_on_async_function_cache_hit(self, mock_get_cache):
        """Test cache decorator on async function with cache hit."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = 99
        mock_get_cache.return_value = mock_cache
        mock_cache._generate_key.return_value = "test:async_func:hash123"

        call_count = 0

        @cache(prefix="test", ttl=1800)
        async def async_expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * y

        result = await async_expensive_function(5, 10)

        assert result == 99  # Cached value
        assert call_count == 0  # Function not called

    @patch("src.utils.cache.get_cache")
    def test_decorator_with_custom_key_func(self, mock_get_cache):
        """Test cache decorator with custom key function."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        def custom_key(x, y):
            return f"custom:key:{x}:{y}"

        @cache(prefix="test", ttl=1800, key_func=custom_key)
        def function_with_custom_key(x, y):
            return x + y

        function_with_custom_key(5, 10)

        # Verify custom key was used
        mock_cache.get.assert_called_once_with("custom:key:5:10")


class TestInvalidateCache:
    """Test cache invalidation functionality."""

    def teardown_method(self):
        """Reset global cache instance after each test."""
        import src.utils.cache

        src.utils.cache._cache_instance = None

    @patch("src.utils.cache.get_cache")
    def test_invalidate_cache_success(self, mock_get_cache):
        """Test successful cache invalidation."""
        mock_cache = MagicMock()
        mock_redis = MagicMock()
        mock_cache._redis_client = mock_redis
        mock_redis.keys.return_value = ["search:key1", "search:key2"]
        mock_redis.delete.return_value = 2
        mock_get_cache.return_value = mock_cache

        deleted = invalidate_cache("search:*")

        assert deleted == 2
        mock_redis.keys.assert_called_once_with("search:*")
        mock_redis.delete.assert_called_once_with("search:key1", "search:key2")

    @patch("src.utils.cache.get_cache")
    def test_invalidate_cache_no_matches(self, mock_get_cache):
        """Test cache invalidation with no matching keys."""
        mock_cache = MagicMock()
        mock_redis = MagicMock()
        mock_cache._redis_client = mock_redis
        mock_redis.keys.return_value = []
        mock_get_cache.return_value = mock_cache

        deleted = invalidate_cache("nonexistent:*")

        assert deleted == 0
        mock_redis.keys.assert_called_once_with("nonexistent:*")
        mock_redis.delete.assert_not_called()

    @patch("src.utils.cache.get_cache")
    def test_invalidate_cache_redis_error(self, mock_get_cache):
        """Test cache invalidation handles Redis errors."""
        mock_cache = MagicMock()
        mock_redis = MagicMock()
        mock_cache._redis_client = mock_redis
        mock_redis.keys.side_effect = RedisError("Connection lost")
        mock_get_cache.return_value = mock_cache

        deleted = invalidate_cache("pattern:*")

        assert deleted == 0

    @patch("src.utils.cache.get_cache")
    def test_invalidate_cache_no_redis_client(self, mock_get_cache):
        """Test cache invalidation when Redis client is None."""
        mock_cache = MagicMock()
        mock_cache._redis_client = None
        mock_get_cache.return_value = mock_cache

        deleted = invalidate_cache("pattern:*")

        assert deleted == 0


class TestIntegrationScenarios:
    """Test integration scenarios."""

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_full_cache_lifecycle_with_memory_fallback(self, mock_pool, mock_redis):
        """Test complete cache lifecycle with memory fallback."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        # Simulate Redis errors to trigger fallback
        mock_redis_instance.setex.side_effect = RedisError("Connection lost")
        mock_redis_instance.get.side_effect = RedisError("Connection lost")
        mock_redis_instance.exists.side_effect = RedisError("Connection lost")
        mock_redis_instance.delete.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache(enable_fallback=True)

        # Set value (will fallback to memory)
        cache_obj.set("lifecycle_key", {"data": "test"})

        # Get value (will fallback to memory)
        value = cache_obj.get("lifecycle_key")
        assert value == {"data": "test"}

        # Check existence (will fallback to memory)
        assert cache_obj.exists("lifecycle_key") is True

        # Delete value (will fallback to memory)
        cache_obj.delete("lifecycle_key")

        # Verify deleted
        assert cache_obj.get("lifecycle_key") is None
        assert cache_obj.exists("lifecycle_key") is False

    @patch("src.utils.cache.redis.Redis")
    @patch("src.utils.cache.ConnectionPool")
    def test_counter_increment_in_memory(self, mock_pool, mock_redis):
        """Test counter increment in memory cache."""
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        # Simulate Redis errors to trigger fallback
        mock_redis_instance.incr.side_effect = RedisError("Connection lost")

        cache_obj = RedisCache(enable_fallback=True)

        # Increment new counter (will fallback to memory)
        result = cache_obj.incr("counter", amount=1)
        assert result == 1

        # Increment again
        result = cache_obj.incr("counter", amount=5)
        assert result == 6

        # Increment again (default amount=1)
        result = cache_obj.incr("counter")
        assert result == 7
