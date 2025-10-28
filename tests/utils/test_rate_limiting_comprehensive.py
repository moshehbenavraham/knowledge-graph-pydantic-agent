"""
Comprehensive tests for src/utils/rate_limiting.py.

Tests rate limiting for API calls and user requests.
"""

import asyncio
import contextlib
import time
from unittest.mock import AsyncMock, patch

import pytest

from src.utils.rate_limiting import (
    APIRateLimiter,
    RateLimiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    UserRateLimiter,
    rate_limit,
    rate_limiter,
)


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_init_default_burst(self):
        """Test initialization with default burst size."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60
        assert limiter.burst_size == 10  # Default equals max_requests

    def test_init_custom_burst(self):
        """Test initialization with custom burst size."""
        limiter = RateLimiter(max_requests=10, window_seconds=60, burst_size=20)

        assert limiter.burst_size == 20

    @pytest.mark.asyncio
    async def test_is_allowed_first_request(self):
        """Test first request is always allowed."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        allowed, info = await limiter.is_allowed("user1")

        assert allowed is True
        assert info["allowed"] is True
        assert info["remaining_tokens"] >= 0
        assert "reset_time" in info

    @pytest.mark.asyncio
    async def test_is_allowed_multiple_requests(self):
        """Test multiple requests within limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        for _i in range(5):
            allowed, _info = await limiter.is_allowed("user1")
            assert allowed is True

    @pytest.mark.asyncio
    async def test_is_allowed_exceeds_limit(self):
        """Test request denied when limit exceeded."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # First two allowed
        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        # Third denied
        allowed, info = await limiter.is_allowed("user1")

        assert allowed is False
        assert info["allowed"] is False
        assert info["remaining_tokens"] == 0
        assert "retry_after" in info

    @pytest.mark.asyncio
    async def test_is_allowed_different_users(self):
        """Test different users have separate limits."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # User1 uses their limit
        await limiter.is_allowed("user1")

        # User2 should still be allowed
        allowed, _info = await limiter.is_allowed("user2")

        assert allowed is True

    @pytest.mark.asyncio
    async def test_is_allowed_token_refill(self):
        """Test tokens refill over time."""
        limiter = RateLimiter(max_requests=10, window_seconds=1)  # 1 second window

        # Use all tokens
        for _ in range(10):
            await limiter.is_allowed("user1")

        # Wait for refill
        await asyncio.sleep(1.1)

        # Should be allowed again
        allowed, _info = await limiter.is_allowed("user1")

        assert allowed is True

    @pytest.mark.asyncio
    async def test_is_allowed_sliding_window(self):
        """Test sliding window cleans old requests."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Make 2 requests
        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        # Wait for window to pass
        await asyncio.sleep(1.1)

        # Old requests should be cleaned
        allowed, _info = await limiter.is_allowed("user1")

        assert allowed is True

    def test_get_stats(self):
        """Test getting rate limit stats."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        stats = limiter.get_stats("user1")

        assert "requests_in_window" in stats
        assert "remaining_tokens" in stats
        assert "window_seconds" in stats
        assert "max_requests" in stats
        assert stats["max_requests"] == 10

    @pytest.mark.asyncio
    async def test_get_stats_after_requests(self):
        """Test stats reflect recent requests."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        stats = limiter.get_stats("user1")

        assert stats["requests_in_window"] == 2
        assert stats["remaining_tokens"] < 5


class TestAPIRateLimiter:
    """Test APIRateLimiter class."""

    def test_init_creates_limiters(self):
        """Test initialization creates service limiters."""
        api_limiter = APIRateLimiter()

        assert "openai" in api_limiter.limiters
        assert "brave" in api_limiter.limiters
        assert "jina" in api_limiter.limiters
        assert "supabase" in api_limiter.limiters
        assert "mem0" in api_limiter.limiters

    @pytest.mark.asyncio
    async def test_check_api_limit_known_service(self):
        """Test checking limit for known service."""
        api_limiter = APIRateLimiter()

        allowed, info = await api_limiter.check_api_limit("openai", "user1")

        assert isinstance(allowed, bool)
        assert "service" in info
        assert info["service"] == "openai"

    @pytest.mark.asyncio
    async def test_check_api_limit_unknown_service(self):
        """Test checking limit for unknown service."""
        api_limiter = APIRateLimiter()

        allowed, info = await api_limiter.check_api_limit("unknown_service", "user1")

        assert allowed is True
        assert info["allowed"] is True

    @pytest.mark.asyncio
    async def test_check_api_limit_default_user(self):
        """Test checking limit with default system user."""
        api_limiter = APIRateLimiter()

        allowed, _info = await api_limiter.check_api_limit("openai")

        assert isinstance(allowed, bool)

    @pytest.mark.asyncio
    async def test_check_api_limit_exceeds(self):
        """Test API limit exceeded."""
        api_limiter = APIRateLimiter()

        # Use up all requests for a low-limit service
        for _ in range(61):  # OpenAI has 60 RPM
            await api_limiter.check_api_limit("openai", "user1")

        # Next should be denied
        allowed, _info = await api_limiter.check_api_limit("openai", "user1")

        assert allowed is False

    @pytest.mark.asyncio
    async def test_wait_for_api_limit_immediate(self):
        """Test wait returns immediately when allowed."""
        api_limiter = APIRateLimiter()

        result = await api_limiter.wait_for_api_limit("openai", "user1")

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_api_limit_timeout(self):
        """Test wait times out when limit not available."""
        api_limiter = APIRateLimiter()

        # Exhaust limit
        for _ in range(61):
            await api_limiter.check_api_limit("openai", "user_timeout")

        # Wait with very short timeout
        result = await api_limiter.wait_for_api_limit("openai", "user_timeout", max_wait=0.1)

        assert result is False


class TestUserRateLimiter:
    """Test UserRateLimiter class."""

    def test_init_creates_tier_limiters(self):
        """Test initialization creates tier limiters."""
        user_limiter = UserRateLimiter()

        assert "free" in user_limiter.limiters
        assert "premium" in user_limiter.limiters
        assert "enterprise" in user_limiter.limiters

    def test_default_tier_is_free(self):
        """Test users default to free tier."""
        user_limiter = UserRateLimiter()

        tier = user_limiter.user_tiers["new_user"]

        assert tier == "free"

    def test_set_user_tier_valid(self):
        """Test setting valid user tier."""
        user_limiter = UserRateLimiter()

        user_limiter.set_user_tier("user1", "premium")

        assert user_limiter.user_tiers["user1"] == "premium"

    def test_set_user_tier_invalid(self):
        """Test setting invalid tier doesn't change."""
        user_limiter = UserRateLimiter()
        user_limiter.set_user_tier("user1", "free")

        user_limiter.set_user_tier("user1", "invalid_tier")

        assert user_limiter.user_tiers["user1"] == "free"

    @pytest.mark.asyncio
    async def test_check_user_limit_free_tier(self):
        """Test checking limit for free tier user."""
        user_limiter = UserRateLimiter()

        allowed, info = await user_limiter.check_user_limit("free_user")

        assert isinstance(allowed, bool)
        assert info["tier"] == "free"

    @pytest.mark.asyncio
    async def test_check_user_limit_premium_tier(self):
        """Test checking limit for premium tier user."""
        user_limiter = UserRateLimiter()
        user_limiter.set_user_tier("premium_user", "premium")

        allowed, info = await user_limiter.check_user_limit("premium_user")

        assert allowed is True
        assert info["tier"] == "premium"

    @pytest.mark.asyncio
    async def test_check_user_limit_different_limits(self):
        """Test different tiers have different limits."""
        user_limiter = UserRateLimiter()
        user_limiter.set_user_tier("premium_user", "premium")

        # Free user (10 per minute)
        for _ in range(11):
            await user_limiter.check_user_limit("free_user")

        free_allowed, _ = await user_limiter.check_user_limit("free_user")

        # Premium user should still be allowed (100 per minute)
        premium_allowed, _ = await user_limiter.check_user_limit("premium_user")

        assert free_allowed is False
        assert premium_allowed is True

    def test_get_user_stats(self):
        """Test getting user stats."""
        user_limiter = UserRateLimiter()

        stats = user_limiter.get_user_stats("user1")

        assert "tier" in stats
        assert "requests_in_window" in stats
        assert stats["tier"] == "free"


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware class."""

    def test_init(self):
        """Test middleware initialization."""
        middleware = RateLimitMiddleware()

        assert middleware.api_limiter is not None
        assert middleware.user_limiter is not None

    @pytest.mark.asyncio
    async def test_check_limits_user_only(self):
        """Test checking only user limits."""
        middleware = RateLimitMiddleware()

        allowed, info = await middleware.check_limits("user1")

        assert isinstance(allowed, bool)
        assert info["type"] == "allowed"
        assert "user_info" in info

    @pytest.mark.asyncio
    async def test_check_limits_with_service(self):
        """Test checking both user and API limits."""
        middleware = RateLimitMiddleware()

        allowed, info = await middleware.check_limits("user1", service="openai")

        assert isinstance(allowed, bool)
        if allowed:
            assert "api_info" in info

    @pytest.mark.asyncio
    async def test_check_limits_user_exceeded(self):
        """Test when user limit exceeded."""
        middleware = RateLimitMiddleware()

        # Exhaust user limit (free tier = 10 per minute)
        for _ in range(11):
            await middleware.check_limits("user_test")

        allowed, info = await middleware.check_limits("user_test")

        assert allowed is False
        assert info["type"] == "user_limit"

    @pytest.mark.asyncio
    async def test_enforce_limits_success(self):
        """Test enforcing limits when allowed."""
        middleware = RateLimitMiddleware()

        # Should not raise exception
        await middleware.enforce_limits("user1")

    @pytest.mark.asyncio
    async def test_enforce_limits_user_exceeded(self):
        """Test enforce raises exception when user limit exceeded."""
        middleware = RateLimitMiddleware()

        # Exhaust limit
        for _ in range(11):
            with contextlib.suppress(RateLimitExceededError):
                await middleware.enforce_limits("user_enforce")

        # Should raise exception
        with pytest.raises(RateLimitExceededError) as exc_info:
            await middleware.enforce_limits("user_enforce")

        assert "User rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_enforce_limits_api_exceeded(self):
        """Test enforce raises exception when API limit exceeded."""
        middleware = RateLimitMiddleware()

        # Exhaust API limit (this would require many requests)
        # For testing, we can patch the check_api_limit method
        with patch.object(
            middleware.api_limiter,
            "check_api_limit",
            new=AsyncMock(return_value=(False, {"service": "test", "retry_after": 60})),
        ):
            with pytest.raises(RateLimitExceededError) as exc_info:
                await middleware.enforce_limits("user1", service="test")

            assert "API rate limit exceeded" in str(exc_info.value)

    def test_get_all_stats(self):
        """Test getting comprehensive stats."""
        middleware = RateLimitMiddleware()

        stats = middleware.get_all_stats("user1")

        assert "user" in stats
        assert "apis" in stats
        assert "timestamp" in stats
        assert "openai" in stats["apis"]


class TestRateLimitExceededError:
    """Test RateLimitExceededError exception."""

    def test_error_creation(self):
        """Test error can be created."""
        error = RateLimitExceededError("Test message")

        assert str(error) == "Test message"

    def test_error_is_exception(self):
        """Test error is an Exception."""
        error = RateLimitExceededError("Test")

        assert isinstance(error, Exception)

    def test_error_can_be_raised(self):
        """Test error can be raised and caught."""
        with pytest.raises(RateLimitExceededError):
            raise RateLimitExceededError("Test error")


class TestRateLimitDecorator:
    """Test rate_limit decorator."""

    @pytest.mark.asyncio
    async def test_decorator_async_function(self):
        """Test decorator on async function."""

        @rate_limit(service="openai")
        async def test_function(user_id="test"):
            return "success"

        result = await test_function(user_id="user1")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_enforces_limits(self):
        """Test decorator enforces rate limits."""

        @rate_limit()
        async def test_function(user_id="test"):
            return "success"

        # Exhaust limit (free tier = 10 per minute)
        for _ in range(11):
            with contextlib.suppress(RateLimitExceededError):
                await test_function(user_id="limited_user")

        # Should raise exception
        with pytest.raises(RateLimitExceededError):
            await test_function(user_id="limited_user")

    def test_decorator_sync_function(self):
        """Test decorator on sync function."""

        @rate_limit()
        def test_function(user_id="test"):
            return "success"

        # Should work (though rate limiting may be skipped in certain contexts)
        result = test_function(user_id="user1")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_with_service(self):
        """Test decorator with specific service."""

        @rate_limit(service="jina")
        async def test_function(user_id="test"):
            return "success"

        result = await test_function(user_id="user1")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_anonymous_user(self):
        """Test decorator with anonymous user."""

        @rate_limit()
        async def test_function():
            return "success"

        # Should use "anonymous" as user_id
        result = await test_function()

        assert result == "success"


class TestGlobalRateLimiter:
    """Test global rate_limiter instance."""

    def test_global_instance_exists(self):
        """Test global rate_limiter instance exists."""
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimitMiddleware)

    @pytest.mark.asyncio
    async def test_global_instance_functional(self):
        """Test global instance is functional."""
        allowed, info = await rate_limiter.check_limits("global_user")

        assert isinstance(allowed, bool)
        assert isinstance(info, dict)


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_user(self):
        """Test concurrent requests for same user."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # Make concurrent requests
        tasks = [limiter.is_allowed("concurrent_user") for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Should respect limit
        allowed_count = sum(1 for allowed, _ in results if allowed)
        assert allowed_count <= 5

    @pytest.mark.asyncio
    async def test_very_short_window(self):
        """Test rate limiter with very short window."""
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)

        await limiter.is_allowed("user1")

        # Should be denied immediately
        allowed, _info = await limiter.is_allowed("user1")

        assert allowed is False

        # Wait for window
        await asyncio.sleep(0.2)

        # Should be allowed again
        allowed, _info = await limiter.is_allowed("user1")

        assert allowed is True

    def test_zero_max_requests(self):
        """Test limiter with zero max requests."""
        limiter = RateLimiter(max_requests=0, window_seconds=60)

        # Should create limiter without error
        assert limiter.max_requests == 0

    @pytest.mark.asyncio
    async def test_negative_burst_size(self):
        """Test limiter handles negative burst size."""
        # Negative burst should use max_requests
        limiter = RateLimiter(max_requests=10, window_seconds=60, burst_size=-1)

        # Should still work (implementation may vary)
        allowed, _info = await limiter.is_allowed("user1")

        assert isinstance(allowed, bool)

    @pytest.mark.asyncio
    async def test_stats_empty_user(self):
        """Test getting stats for user with no requests."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        stats = limiter.get_stats("never_seen_user")

        assert stats["requests_in_window"] == 0

    @pytest.mark.asyncio
    async def test_api_limiter_case_sensitive_service(self):
        """Test API limiter is case sensitive."""
        api_limiter = APIRateLimiter()

        # Lowercase should work
        allowed1, _ = await api_limiter.check_api_limit("openai")

        # Uppercase should be unknown
        allowed2, info2 = await api_limiter.check_api_limit("OPENAI")

        assert allowed1 is True
        assert allowed2 is True  # Unknown services are allowed
        assert info2["service"] == "OPENAI"


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_many_users_performance(self):
        """Test performance with many users."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        # Create requests for 100 different users
        tasks = [limiter.is_allowed(f"user_{i}") for i in range(100)]

        start_time = time.time()
        await asyncio.gather(*tasks)
        duration = time.time() - start_time

        # Should complete reasonably fast (< 1 second for 100 users)
        assert duration < 1.0

    @pytest.mark.asyncio
    async def test_stats_performance(self):
        """Test stats retrieval performance."""
        limiter = RateLimiter(max_requests=100, window_seconds=60)

        # Make many requests
        for _ in range(50):
            await limiter.is_allowed("perf_user")

        # Getting stats should be fast
        start_time = time.time()
        for _ in range(100):
            limiter.get_stats("perf_user")
        duration = time.time() - start_time

        # Should be very fast (< 0.1 seconds for 100 stat calls)
        assert duration < 0.1
