"""Redis caching utilities for performance optimization."""

import hashlib
import json
import pickle  # nosec B403 - Used only for internal cache, not user input
from collections.abc import Callable
from functools import wraps
from typing import Any

import redis
import structlog
from redis import ConnectionPool
from redis.exceptions import RedisError

from src.config import get_settings

logger = structlog.get_logger()


class RedisCache:
    """Redis cache manager with fallback to in-memory cache."""

    def __init__(
        self,
        redis_url: str | None = None,
        ttl: int = 3600,
        max_connections: int = 50,
        socket_timeout: int = 5,
        enable_fallback: bool = True,
    ):
        """Initialize Redis cache manager.

        Args:
            redis_url: Redis connection URL
            ttl: Default time-to-live in seconds
            max_connections: Maximum number of connections in pool
            socket_timeout: Socket timeout in seconds
            enable_fallback: Enable in-memory fallback cache
        """
        self.ttl = ttl
        self.enable_fallback = enable_fallback
        self._memory_cache: dict = {}
        self._redis_client: redis.Redis | None = None

        settings = get_settings()
        redis_url = redis_url or settings.redis_url

        if redis_url is None:
            logger.warning("No Redis URL configured, using in-memory cache")
            self._redis_client = None
            return

        try:
            # Create connection pool for better performance
            pool = ConnectionPool.from_url(
                redis_url,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_timeout,
                decode_responses=False,  # Handle bytes for pickle
            )
            self._redis_client = redis.Redis(connection_pool=pool)
            # Test connection
            self._redis_client.ping()
            logger.info("Redis cache connected", url=redis_url)
        except (RedisError, Exception) as e:
            logger.warning(
                "Redis connection failed, using in-memory cache",
                error=str(e),
                fallback_enabled=enable_fallback,
            )
            if not enable_fallback:
                raise

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments."""
        key_data = {
            "prefix": prefix,
            "args": args,
            "kwargs": sorted(kwargs.items()),
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()
        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        try:
            if self._redis_client:
                value = self._redis_client.get(key)
                if value:
                    return pickle.loads(value)  # nosec B301 - Internal cache only
                return None
        except (RedisError, Exception) as e:
            logger.debug("Redis get failed", key=key, error=str(e))

        # Use fallback if Redis unavailable or failed
        if self.enable_fallback:
            return self._memory_cache.get(key)
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache with optional TTL."""
        ttl = ttl or self.ttl
        try:
            if self._redis_client:
                serialized = pickle.dumps(value)
                return bool(self._redis_client.setex(key, ttl, serialized))
        except (RedisError, Exception) as e:
            logger.debug("Redis set failed", key=key, error=str(e))

        # Use fallback if Redis unavailable or failed
        if self.enable_fallback:
            self._memory_cache[key] = value
            # Simple memory cache size limit
            if len(self._memory_cache) > 10000:
                # Remove oldest entries
                for _ in range(1000):
                    self._memory_cache.pop(next(iter(self._memory_cache)))
            return True
        return False

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            if self._redis_client:
                return bool(self._redis_client.delete(key))
        except (RedisError, Exception) as e:
            logger.debug("Redis delete failed", key=key, error=str(e))

        # Use fallback if Redis unavailable or failed
        if self.enable_fallback and key in self._memory_cache:
            del self._memory_cache[key]
            return True
        return False

    def flush(self) -> bool:
        """Flush all cache entries."""
        try:
            if self._redis_client:
                self._redis_client.flushdb()
            self._memory_cache.clear()
            return True
        except (RedisError, Exception) as e:
            logger.error("Redis flush failed", error=str(e))
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            if self._redis_client:
                return bool(self._redis_client.exists(key))
        except (RedisError, Exception) as e:
            logger.debug("Redis exists check failed", key=key, error=str(e))

        # Use fallback if Redis unavailable or failed
        if self.enable_fallback:
            return key in self._memory_cache
        return False

    def incr(self, key: str, amount: int = 1) -> int | None:
        """Increment counter in cache."""
        try:
            if self._redis_client:
                return self._redis_client.incr(key, amount)
        except (RedisError, Exception) as e:
            logger.debug("Redis incr failed", key=key, error=str(e))

        # Use fallback if Redis unavailable or failed
        if self.enable_fallback:
            current = self._memory_cache.get(key, 0)
            self._memory_cache[key] = current + amount
            return self._memory_cache[key]
        return None

    def health_check(self) -> bool:
        """Check if Redis is healthy."""
        logger.info(
            "health_check called",
            redis_client_available=self._redis_client is not None,
            fallback_enabled=self.enable_fallback,
        )
        try:
            if self._redis_client:
                logger.info("Checking Redis health with ping")
                ping_result = self._redis_client.ping()
                logger.info(
                    "Redis health check completed",
                    status="healthy" if ping_result else "unhealthy",
                    ping_result=ping_result,
                )
                return ping_result
            logger.info(
                "Redis client not available, using fallback mode",
                fallback_healthy=self.enable_fallback,
            )
            return self.enable_fallback  # Fallback mode is "healthy"
        except Exception as e:
            logger.error("Redis health check failed", error=str(e), error_type=type(e).__name__)
            return False


# Global cache instance
_cache_instance: RedisCache | None = None


def get_cache() -> RedisCache:
    """Get or create global cache instance."""
    global _cache_instance
    logger.info("get_cache called", instance_exists=_cache_instance is not None)
    if _cache_instance is None:
        logger.info("Creating new global RedisCache instance")
        _cache_instance = RedisCache()
        logger.info(
            "Global RedisCache instance created",
            redis_available=_cache_instance._redis_client is not None,
            fallback_enabled=_cache_instance.enable_fallback,
            ttl=_cache_instance.ttl,
        )
    else:
        logger.info("Returning existing global RedisCache instance")
    return _cache_instance


def cache(
    prefix: str = "func",
    ttl: int = 3600,
    key_func: Callable | None = None,
):
    """Decorator for caching function results.

    Args:
        prefix: Cache key prefix
        ttl: Time-to-live in seconds
        key_func: Custom function to generate cache key
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_obj = get_cache()

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_obj._generate_key(f"{prefix}:{func.__name__}", *args, **kwargs)

            # Try to get from cache
            cached_value = cache_obj.get(cache_key)
            if cached_value is not None:
                logger.debug("Cache hit", function=func.__name__, key=cache_key)
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            cache_obj.set(cache_key, result, ttl)
            logger.debug("Cache miss, stored", function=func.__name__, key=cache_key)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_obj = get_cache()

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_obj._generate_key(f"{prefix}:{func.__name__}", *args, **kwargs)

            # Try to get from cache
            cached_value = cache_obj.get(cache_key)
            if cached_value is not None:
                logger.debug("Cache hit", function=func.__name__, key=cache_key)
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            cache_obj.set(cache_key, result, ttl)
            logger.debug("Cache miss, stored", function=func.__name__, key=cache_key)

            return result

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(pattern: str) -> int:
    """Invalidate cache entries matching pattern.

    Args:
        pattern: Redis pattern (e.g., "search:*")

    Returns:
        Number of keys deleted
    """
    cache_obj = get_cache()
    deleted = 0

    try:
        if cache_obj._redis_client:
            keys = cache_obj._redis_client.keys(pattern)
            if keys:
                deleted = cache_obj._redis_client.delete(*keys)
                logger.info("Cache invalidated", pattern=pattern, keys_deleted=deleted)
    except (RedisError, Exception) as e:
        logger.error("Cache invalidation failed", pattern=pattern, error=str(e))

    return deleted
