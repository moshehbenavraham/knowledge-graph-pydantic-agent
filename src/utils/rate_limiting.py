"""Rate limiting utilities for API calls and user requests."""

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, ParamSpec, TypeVar

from .monitoring import ERROR_COUNT, logger

P = ParamSpec("P")
T = TypeVar("T")


class RateLimiter:
    """Token bucket rate limiter with sliding window."""

    def __init__(self, max_requests: int, window_seconds: int, burst_size: int | None = None):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_size = burst_size or max_requests
        self.requests: defaultdict[str, deque[float]] = defaultdict(
            deque
        )  # user_id -> deque of timestamps
        self.tokens: defaultdict[str, Any] = defaultdict(
            lambda: self.burst_size
        )  # user_id -> available tokens
        self.last_refill: dict[str, float] = {}  # user_id -> last refill time
        self.lock = asyncio.Lock()

    async def is_allowed(self, user_id: str) -> tuple[bool, dict]:
        """Check if request is allowed for user."""
        async with self.lock:
            now = time.time()

            # Initialize last_refill for new users
            if user_id not in self.last_refill:
                self.last_refill[user_id] = now

            # Refill tokens based on time passed
            time_passed = now - self.last_refill[user_id]
            tokens_to_add = (time_passed / self.window_seconds) * self.max_requests
            self.tokens[user_id] = min(self.burst_size, self.tokens[user_id] + tokens_to_add)
            self.last_refill[user_id] = now

            # Clean old requests from sliding window
            cutoff_time = now - self.window_seconds
            user_requests = self.requests[user_id]
            while user_requests and user_requests[0] < cutoff_time:
                user_requests.popleft()

            # Check if request is allowed
            if self.tokens[user_id] >= 1:
                self.tokens[user_id] -= 1
                user_requests.append(now)

                return True, {
                    "allowed": True,
                    "remaining_tokens": int(self.tokens[user_id]),
                    "reset_time": now + self.window_seconds,
                    "requests_in_window": len(user_requests),
                }
            ERROR_COUNT.labels(
                error_type="RateLimitExceeded", component="rate_limiter", severity="warning"
            ).inc()

            return False, {
                "allowed": False,
                "remaining_tokens": 0,
                "reset_time": now + self.window_seconds,
                "requests_in_window": len(user_requests),
                "retry_after": self.window_seconds / self.max_requests,
            }

    def get_stats(self, user_id: str) -> dict:
        """Get current rate limiting stats for user."""
        now = time.time()
        user_requests = self.requests[user_id]

        # Clean old requests
        cutoff_time = now - self.window_seconds
        while user_requests and user_requests[0] < cutoff_time:
            user_requests.popleft()

        return {
            "requests_in_window": len(user_requests),
            "remaining_tokens": int(self.tokens[user_id]),
            "window_seconds": self.window_seconds,
            "max_requests": self.max_requests,
        }


class APIRateLimiter:
    """Rate limiter for external API calls."""

    def __init__(self) -> None:
        # Different limits for different services
        self.limiters = {
            "openai": RateLimiter(max_requests=60, window_seconds=60),  # 60 RPM
            "brave": RateLimiter(max_requests=100, window_seconds=3600),  # 100 per hour
            "jina": RateLimiter(max_requests=200, window_seconds=60),  # 200 RPM (generous)
            "supabase": RateLimiter(max_requests=1000, window_seconds=60),  # 1000 RPM
            "mem0": RateLimiter(max_requests=100, window_seconds=60),  # 100 RPM
        }

    async def check_api_limit(self, service: str, user_id: str = "system") -> tuple[bool, dict]:
        """Check if API call is allowed for service."""
        if service not in self.limiters:
            logger.warning("Unknown service for rate limiting", service=service)
            return True, {"allowed": True, "service": service}

        limiter = self.limiters[service]
        allowed, info = await limiter.is_allowed(f"{service}_{user_id}")

        if not allowed:
            logger.warning(
                "API rate limit exceeded",
                service=service,
                user_id=user_id,
                retry_after=info.get("retry_after", 0),
            )

        info["service"] = service
        return allowed, info

    async def wait_for_api_limit(
        self, service: str, user_id: str = "system", max_wait: float = 60.0
    ) -> bool:
        """Wait until API call is allowed, with maximum wait time."""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            allowed, info = await self.check_api_limit(service, user_id)
            if allowed:
                return True

            # Wait for a short time before retrying
            wait_time = min(info.get("retry_after", 1.0), 5.0)
            await asyncio.sleep(wait_time)

        logger.error(
            "API rate limit wait timeout", service=service, user_id=user_id, max_wait=max_wait
        )
        return False


class UserRateLimiter:
    """Rate limiter for user requests."""

    def __init__(self) -> None:
        # Different limits for different user tiers
        self.limiters = {
            "free": RateLimiter(max_requests=10, window_seconds=60),  # 10 per minute
            "premium": RateLimiter(max_requests=100, window_seconds=60),  # 100 per minute
            "enterprise": RateLimiter(max_requests=1000, window_seconds=60),  # 1000 per minute
        }
        self.user_tiers: defaultdict[str, str] = defaultdict(lambda: "free")  # user_id -> tier

    def set_user_tier(self, user_id: str, tier: str) -> None:
        """Set user tier for rate limiting."""
        if tier in self.limiters:
            self.user_tiers[user_id] = tier
            logger.info("User tier updated", user_id=user_id, tier=tier)
        else:
            logger.warning("Invalid user tier", user_id=user_id, tier=tier)

    async def check_user_limit(self, user_id: str) -> tuple[bool, dict]:
        """Check if user request is allowed."""
        tier = self.user_tiers[user_id]
        limiter = self.limiters[tier]

        allowed, info = await limiter.is_allowed(user_id)
        info["tier"] = tier

        if not allowed:
            logger.warning(
                "User rate limit exceeded",
                user_id=user_id,
                tier=tier,
                retry_after=info.get("retry_after", 0),
            )

        return allowed, info

    def get_user_stats(self, user_id: str) -> dict:
        """Get rate limiting stats for user."""
        logger.info("get_user_stats called", user_id=user_id)

        tier = self.user_tiers[user_id]
        logger.info("Retrieved user tier", user_id=user_id, tier=tier)

        limiter = self.limiters[tier]
        stats = limiter.get_stats(user_id)
        stats["tier"] = tier

        logger.info(
            "get_user_stats completed",
            user_id=user_id,
            tier=tier,
            requests_in_window=stats.get("requests_in_window"),
            remaining_tokens=stats.get("remaining_tokens"),
        )
        return stats


class RateLimitMiddleware:
    """Middleware for applying rate limits to requests."""

    def __init__(self) -> None:
        self.api_limiter = APIRateLimiter()
        self.user_limiter = UserRateLimiter()

    async def check_limits(self, user_id: str, service: str | None = None) -> tuple[bool, dict]:
        """Check both user and API limits."""
        # Check user limit first
        user_allowed, user_info = await self.user_limiter.check_user_limit(user_id)
        if not user_allowed:
            return False, {"type": "user_limit", **user_info}

        # Check API limit if service specified
        if service:
            api_allowed, api_info = await self.api_limiter.check_api_limit(service, user_id)
            if not api_allowed:
                return False, {"type": "api_limit", **api_info}

            return True, {"type": "allowed", "user_info": user_info, "api_info": api_info}

        return True, {"type": "allowed", "user_info": user_info}

    async def enforce_limits(self, user_id: str, service: str | None = None) -> None:
        """Enforce rate limits, raising exception if exceeded."""
        allowed, info = await self.check_limits(user_id, service)

        if not allowed:
            if info["type"] == "user_limit":
                raise RateLimitExceededError(
                    f"User rate limit exceeded. Tier: {info['tier']}, "
                    f"retry after {info.get('retry_after', 60)} seconds"
                )
            if info["type"] == "api_limit":
                raise RateLimitExceededError(
                    f"API rate limit exceeded for {info['service']}. "
                    f"Retry after {info.get('retry_after', 60)} seconds"
                )

    def get_all_stats(self, user_id: str) -> dict:
        """Get comprehensive rate limiting stats for user."""
        logger.info("get_all_stats called", user_id=user_id)

        user_stats = self.user_limiter.get_user_stats(user_id)
        logger.info(
            "Retrieved user stats",
            user_id=user_id,
            tier=user_stats.get("tier"),
            remaining_tokens=user_stats.get("remaining_tokens"),
        )

        api_stats = {}
        for service in self.api_limiter.limiters:
            limiter = self.api_limiter.limiters[service]
            api_stats[service] = limiter.get_stats(f"{service}_{user_id}")

        logger.info(
            "Retrieved API stats for all services", user_id=user_id, services=list(api_stats.keys())
        )

        result = {"user": user_stats, "apis": api_stats, "timestamp": datetime.now(UTC).isoformat()}
        logger.info("get_all_stats completed", user_id=user_id, num_services=len(api_stats))

        return result


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""

    pass


# Global rate limit middleware
rate_limiter = RateLimitMiddleware()


def rate_limit(
    service: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to apply rate limiting to functions."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            user_id = str(kwargs.get("user_id", "anonymous"))

            # Enforce rate limits
            await rate_limiter.enforce_limits(user_id, service)

            # Execute function
            return await func(*args, **kwargs)  # type: ignore[misc]

        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            user_id = str(kwargs.get("user_id", "anonymous"))

            # For sync functions, we need to run the async check
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, we can't easily check
                # In a real implementation, you might want to use a different approach
                logger.warning(
                    "Rate limiting check skipped in sync context", function=func.__name__
                )
            else:
                loop.run_until_complete(rate_limiter.enforce_limits(user_id, service))

            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator
