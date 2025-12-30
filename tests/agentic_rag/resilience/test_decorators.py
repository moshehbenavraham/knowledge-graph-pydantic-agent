"""Tests for resilience decorators (retry and circuit breaker)."""

from unittest.mock import AsyncMock, patch

import pytest

from src.agentic_rag.resilience import (
    MaxRetriesExceededError,
    calculate_backoff_delay,
    with_retry,
)


class TestCalculateBackoffDelay:
    """Tests for exponential backoff calculation."""

    def test_first_attempt_returns_base_delay(self) -> None:
        """First attempt should return approximately base delay."""
        delay = calculate_backoff_delay(0, base_delay=1.0, max_delay=10.0, jitter=False)
        assert delay == 1.0

    def test_exponential_growth(self) -> None:
        """Delay should grow exponentially with attempt number."""
        delays = [
            calculate_backoff_delay(i, base_delay=1.0, max_delay=100.0, jitter=False)
            for i in range(5)
        ]
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]

    def test_max_delay_cap(self) -> None:
        """Delay should not exceed max_delay."""
        delay = calculate_backoff_delay(10, base_delay=1.0, max_delay=10.0, jitter=False)
        assert delay == 10.0

    def test_jitter_adds_randomness(self) -> None:
        """Jitter should add randomness to delay."""
        delays = {
            calculate_backoff_delay(1, base_delay=1.0, max_delay=10.0, jitter=True)
            for _ in range(100)
        }
        # With jitter, we should see variation
        assert len(delays) > 1
        # All values should be between base and base + 50% jitter
        for d in delays:
            assert 2.0 <= d <= 3.0  # 2.0 base + 0-50% jitter


class TestWithRetryDecorator:
    """Tests for the with_retry decorator."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self) -> None:
        """Successful calls should not trigger retries."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        async def successful_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self) -> None:
        """Transient errors should trigger retries."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        async def failing_then_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Connection timed out")
            return "success"

        result = await failing_then_success()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self) -> None:
        """Should raise MaxRetriesExceededError after all attempts fail."""

        @with_retry(max_attempts=3, base_delay=0.01)
        async def always_fails() -> None:
            raise TimeoutError("Always fails")

        with pytest.raises(MaxRetriesExceededError) as exc_info:
            await always_fails()

        assert exc_info.value.max_attempts == 3
        assert "always_fails" in exc_info.value.operation

    @pytest.mark.asyncio
    async def test_non_retriable_error_not_retried(self) -> None:
        """Fatal errors should not be retried."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        async def auth_failure() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid authentication token")

        with pytest.raises(ValueError):
            await auth_failure()

        # Should only be called once - no retries for auth errors
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_custom_retriable_exceptions(self) -> None:
        """Should only retry on specified exception types."""
        call_count = 0

        class CustomError(Exception):
            pass

        @with_retry(
            max_attempts=3,
            base_delay=0.01,
            retriable_exceptions=(CustomError,),
        )
        async def custom_error_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise CustomError("Custom transient error")
            return "success"

        result = await custom_error_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_on_retry_callback(self) -> None:
        """on_retry callback should be called before each retry."""
        retry_attempts: list[tuple[int, Exception]] = []

        def track_retries(attempt: int, error: Exception) -> None:
            retry_attempts.append((attempt, error))

        @with_retry(max_attempts=3, base_delay=0.01, on_retry=track_retries)
        async def failing_func() -> str:
            if len(retry_attempts) < 2:
                raise TimeoutError("Temporary failure")
            return "success"

        result = await failing_func()
        assert result == "success"
        assert len(retry_attempts) == 2
        assert all(isinstance(e, TimeoutError) for _, e in retry_attempts)

    @pytest.mark.asyncio
    async def test_uses_asyncio_sleep(self) -> None:
        """Should use asyncio.sleep, not time.sleep."""
        call_count = 0

        @with_retry(max_attempts=2, base_delay=0.1)
        async def failing_once() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("First attempt fails")
            return "success"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await failing_once()

        assert result == "success"
        assert mock_sleep.called


class TestWithRetryDecoratorSettings:
    """Tests for retry decorator with settings integration."""

    @pytest.mark.asyncio
    async def test_uses_settings_defaults(self) -> None:
        """Should use settings values when not specified."""
        with patch("src.config.get_settings") as mock_settings:
            mock_settings.return_value.retry_max_attempts = 2
            mock_settings.return_value.retry_base_delay_seconds = 0.01
            mock_settings.return_value.retry_max_delay_seconds = 0.1

            call_count = 0

            @with_retry()
            async def always_fails() -> None:
                nonlocal call_count
                call_count += 1
                raise TimeoutError("fails")

            with pytest.raises(MaxRetriesExceededError):
                await always_fails()

            assert call_count == 2  # Uses settings.retry_max_attempts
