"""
Comprehensive tests for resilience utilities.

Tests circuit breaker pattern and retry logic with exponential backoff.
"""

import asyncio
import time

import aiohttp
import pytest

from src.utils.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    RetryStrategy,
    circuit_breaker,
    retry,
    retry_on_database_error,
    retry_on_network_error,
)


class TestCircuitBreakerClass:
    """Test CircuitBreaker class functionality."""

    def test_initialization_defaults(self):
        """Test circuit breaker initialization with defaults."""
        breaker = CircuitBreaker()

        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60.0
        assert breaker.expected_exceptions == (Exception,)
        assert breaker.name == "unnamed"
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._last_failure_time is None

    def test_initialization_custom(self):
        """Test circuit breaker initialization with custom parameters."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exceptions=(ValueError, KeyError),
            name="test_circuit",
        )

        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 30.0
        assert breaker.expected_exceptions == (ValueError, KeyError)
        assert breaker.name == "test_circuit"

    def test_successful_call_sync(self):
        """Test successful synchronous call."""
        breaker = CircuitBreaker(name="test_sync")

        def success_func(x, y):
            return x + y

        result = breaker.call(success_func, 5, 10)

        assert result == 15
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_successful_call_async(self):
        """Test successful asynchronous call."""
        breaker = CircuitBreaker(name="test_async")

        async def success_func(x, y):
            await asyncio.sleep(0.01)
            return x * y

        result = await breaker.call_async(success_func, 5, 10)

        assert result == 50
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_failed_call_increments_counter(self):
        """Test that failed calls increment failure counter."""
        breaker = CircuitBreaker(failure_threshold=3, name="test_fail")

        def failing_func():
            raise ValueError("Test error")

        # First failure
        with pytest.raises(ValueError):
            breaker.call(failing_func)

        assert breaker._failure_count == 1
        assert breaker.state == CircuitState.CLOSED

        # Second failure
        with pytest.raises(ValueError):
            breaker.call(failing_func)

        assert breaker._failure_count == 2
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_opens_on_threshold(self):
        """Test circuit opens when failure threshold is reached."""
        breaker = CircuitBreaker(failure_threshold=3, name="test_open")

        def failing_func():
            raise ValueError("Test error")

        # Reach threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker._failure_count == 3
        assert breaker.state == CircuitState.OPEN

    def test_circuit_rejects_when_open(self):
        """Test circuit breaker rejects calls when open."""
        breaker = CircuitBreaker(failure_threshold=2, name="test_reject")

        def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Now it should reject without calling the function
        with pytest.raises(CircuitBreakerError, match="test_reject"):
            breaker.call(lambda: "should not execute")

    @pytest.mark.asyncio
    async def test_circuit_rejects_async_when_open(self):
        """Test circuit breaker rejects async calls when open."""
        breaker = CircuitBreaker(failure_threshold=2, name="test_reject_async")

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call_async(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Now it should reject without calling the function
        with pytest.raises(CircuitBreakerError, match="test_reject_async"):
            await breaker.call_async(lambda: "should not execute")

    def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions to half-open after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, name="test_half_open")

        def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Check state (accessing state property triggers transition)
        assert breaker.state == CircuitState.HALF_OPEN

    def test_successful_call_in_half_open_closes_circuit(self):
        """Test successful call in half-open state closes circuit."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, name="test_recovery")

        def failing_func():
            raise ValueError("Test error")

        def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        # Wait for recovery timeout
        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        # Successful call should close circuit
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_failed_call_in_half_open_reopens_circuit(self):
        """Test failed call in half-open state reopens circuit."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, name="test_reopen")

        def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        # Wait for recovery timeout
        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        # Failed call should reopen circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    def test_manual_reset(self):
        """Test manual circuit breaker reset."""
        breaker = CircuitBreaker(failure_threshold=2, name="test_reset")

        def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker._failure_count == 2

        # Manual reset
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._last_failure_time is None

    def test_expected_exceptions_filtering(self):
        """Test that only expected exceptions trigger circuit."""
        breaker = CircuitBreaker(
            failure_threshold=2, expected_exceptions=(ValueError,), name="test_filter"
        )

        def value_error_func():
            raise ValueError("Expected")

        def key_error_func():
            raise KeyError("Unexpected")

        # ValueError should trigger circuit
        with pytest.raises(ValueError):
            breaker.call(value_error_func)
        assert breaker._failure_count == 1

        # KeyError should not trigger circuit (unexpected)
        with pytest.raises(KeyError):
            breaker.call(key_error_func)
        assert breaker._failure_count == 1  # Still 1


class TestCircuitBreakerDecorator:
    """Test circuit_breaker decorator."""

    def test_decorator_on_sync_function(self):
        """Test circuit breaker decorator on synchronous function."""
        call_count = 0

        @circuit_breaker(failure_threshold=2, name="test_sync_decorator")
        def flaky_function(should_fail: bool):
            nonlocal call_count
            call_count += 1
            if should_fail:
                raise ValueError("Failure")
            return "success"

        # Successful calls
        assert flaky_function(False) == "success"
        assert call_count == 1

        # Fail twice to open circuit
        with pytest.raises(ValueError):
            flaky_function(True)
        with pytest.raises(ValueError):
            flaky_function(True)
        assert call_count == 3

        # Circuit should be open now
        with pytest.raises(CircuitBreakerError):
            flaky_function(False)
        assert call_count == 3  # Function not called

    @pytest.mark.asyncio
    async def test_decorator_on_async_function(self):
        """Test circuit breaker decorator on asynchronous function."""
        call_count = 0

        @circuit_breaker(failure_threshold=2, name="test_async_decorator")
        async def flaky_async_function(should_fail: bool):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if should_fail:
                raise ValueError("Failure")
            return "success"

        # Successful calls
        result = await flaky_async_function(False)
        assert result == "success"
        assert call_count == 1

        # Fail twice to open circuit
        with pytest.raises(ValueError):
            await flaky_async_function(True)
        with pytest.raises(ValueError):
            await flaky_async_function(True)
        assert call_count == 3

        # Circuit should be open now
        with pytest.raises(CircuitBreakerError):
            await flaky_async_function(False)
        assert call_count == 3  # Function not called


class TestRetryStrategyClass:
    """Test RetryStrategy class functionality."""

    def test_initialization_defaults(self):
        """Test retry strategy initialization with defaults."""
        strategy = RetryStrategy()

        assert strategy.max_attempts == 3
        assert strategy.base_delay == 1.0
        assert strategy.max_delay == 60.0
        assert strategy.exponential_base == 2.0
        assert strategy.jitter is True
        assert strategy.retriable_exceptions == (Exception,)

    def test_initialization_custom(self):
        """Test retry strategy initialization with custom parameters."""
        strategy = RetryStrategy(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
            retriable_exceptions=(ValueError,),
        )

        assert strategy.max_attempts == 5
        assert strategy.base_delay == 0.5
        assert strategy.max_delay == 30.0
        assert strategy.exponential_base == 3.0
        assert strategy.jitter is False
        assert strategy.retriable_exceptions == (ValueError,)

    def test_calculate_delay_no_jitter(self):
        """Test delay calculation without jitter."""
        strategy = RetryStrategy(
            base_delay=1.0, exponential_base=2.0, jitter=False, max_delay=100.0
        )

        assert strategy.calculate_delay(0) == 1.0  # 1.0 * 2^0
        assert strategy.calculate_delay(1) == 2.0  # 1.0 * 2^1
        assert strategy.calculate_delay(2) == 4.0  # 1.0 * 2^2
        assert strategy.calculate_delay(3) == 8.0  # 1.0 * 2^3

    def test_calculate_delay_with_max(self):
        """Test delay calculation respects max_delay."""
        strategy = RetryStrategy(base_delay=1.0, exponential_base=2.0, jitter=False, max_delay=5.0)

        assert strategy.calculate_delay(0) == 1.0
        assert strategy.calculate_delay(1) == 2.0
        assert strategy.calculate_delay(2) == 4.0
        assert strategy.calculate_delay(3) == 5.0  # Capped at max_delay
        assert strategy.calculate_delay(10) == 5.0  # Still capped

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter adds randomness."""
        strategy = RetryStrategy(base_delay=2.0, exponential_base=2.0, jitter=True)

        # With jitter, delay should be between 50% and 150% of base
        delays = [strategy.calculate_delay(0) for _ in range(10)]

        # All delays should be different (probabilistically)
        assert len(set(delays)) > 1
        # All delays should be in reasonable range (1.0 to 3.0 for attempt 0)
        assert all(1.0 <= d <= 3.0 for d in delays)

    def test_execute_success_first_try(self):
        """Test retry execute succeeds on first try."""
        strategy = RetryStrategy(max_attempts=3)
        call_count = 0

        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = strategy.execute(success_func)

        assert result == "success"
        assert call_count == 1

    def test_execute_success_after_retries(self):
        """Test retry execute succeeds after failures."""
        strategy = RetryStrategy(max_attempts=3, base_delay=0.01)
        call_count = 0

        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = strategy.execute(eventually_succeeds)

        assert result == "success"
        assert call_count == 3

    def test_execute_exhausts_retries(self):
        """Test retry execute exhausts all attempts."""
        strategy = RetryStrategy(max_attempts=3, base_delay=0.01)
        call_count = 0

        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            strategy.execute(always_fails)

        assert call_count == 3  # All attempts used

    @pytest.mark.asyncio
    async def test_execute_async_success_first_try(self):
        """Test async retry execute succeeds on first try."""
        strategy = RetryStrategy(max_attempts=3)
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return "success"

        result = await strategy.execute_async(success_func)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_async_success_after_retries(self):
        """Test async retry execute succeeds after failures."""
        strategy = RetryStrategy(max_attempts=3, base_delay=0.01)
        call_count = 0

        async def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = await strategy.execute_async(eventually_succeeds)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_async_exhausts_retries(self):
        """Test async retry execute exhausts all attempts."""
        strategy = RetryStrategy(max_attempts=3, base_delay=0.01)
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await strategy.execute_async(always_fails)

        assert call_count == 3

    def test_only_retriable_exceptions_trigger_retry(self):
        """Test that only specified exceptions trigger retry."""
        strategy = RetryStrategy(
            max_attempts=3, base_delay=0.01, retriable_exceptions=(ValueError,)
        )
        call_count = 0

        def raises_key_error():
            nonlocal call_count
            call_count += 1
            raise KeyError("Not retriable")

        # KeyError should not trigger retry
        with pytest.raises(KeyError, match="Not retriable"):
            strategy.execute(raises_key_error)

        assert call_count == 1  # Only one attempt


class TestRetryDecorator:
    """Test retry decorator."""

    def test_decorator_on_sync_function(self):
        """Test retry decorator on synchronous function."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        def flaky_function(fail_times: int):
            nonlocal call_count
            call_count += 1
            if call_count <= fail_times:
                raise ValueError("Failure")
            return "success"

        # Reset counter
        call_count = 0
        result = flaky_function(2)

        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded third time

    @pytest.mark.asyncio
    async def test_decorator_on_async_function(self):
        """Test retry decorator on asynchronous function."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01)
        async def flaky_async_function(fail_times: int):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if call_count <= fail_times:
                raise ValueError("Failure")
            return "success"

        # Reset counter
        call_count = 0
        result = await flaky_async_function(2)

        assert result == "success"
        assert call_count == 3

    def test_decorator_exhausts_retries(self):
        """Test retry decorator exhausts all attempts."""

        @retry(max_attempts=3, base_delay=0.01)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()


class TestConvenienceDecorators:
    """Test convenience retry decorators."""

    @pytest.mark.asyncio
    async def test_retry_on_network_error(self):
        """Test retry_on_network_error decorator."""
        call_count = 0

        @retry_on_network_error(max_attempts=3)
        async def network_operation(should_fail: bool):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if should_fail:
                raise aiohttp.ClientError("Network error")
            return "success"

        # Successful call
        call_count = 0
        result = await network_operation(False)
        assert result == "success"
        assert call_count == 1

        # Failed call should retry
        call_count = 0
        with pytest.raises(aiohttp.ClientError):
            await network_operation(True)
        assert call_count == 3  # Exhausted all attempts

    @pytest.mark.asyncio
    async def test_retry_on_database_error(self):
        """Test retry_on_database_error decorator."""
        call_count = 0

        @retry_on_database_error(max_attempts=3)
        async def database_operation(should_fail: bool):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if should_fail:
                raise ConnectionError("Database connection lost")
            return "success"

        # Successful call
        call_count = 0
        result = await database_operation(False)
        assert result == "success"
        assert call_count == 1

        # Failed call should retry
        call_count = 0
        with pytest.raises(ConnectionError):
            await database_operation(True)
        assert call_count == 3


class TestIntegrationScenarios:
    """Test integration scenarios combining circuit breaker and retry."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry(self):
        """Test circuit breaker and retry working together."""
        call_count = 0

        @circuit_breaker(failure_threshold=5, name="test_integration")
        @retry(max_attempts=2, base_delay=0.01)
        async def protected_operation(should_fail: bool):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if should_fail:
                raise ValueError("Failure")
            return "success"

        # Successful operation
        call_count = 0
        result = await protected_operation(False)
        assert result == "success"
        assert call_count == 1

        # Operation that fails but retries (2 attempts per call)
        call_count = 0
        for _ in range(2):
            with pytest.raises(ValueError):
                await protected_operation(True)
        # 2 calls * 2 attempts each = 4 failures
        assert call_count == 4

    def test_state_persistence_across_calls(self):
        """Test that circuit breaker state persists across calls."""
        breaker = CircuitBreaker(failure_threshold=2, name="test_persistence")

        def failing_func():
            raise ValueError("Failure")

        # First failure
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker._failure_count == 1

        # Second failure should open circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitState.OPEN

        # Subsequent calls should be rejected immediately
        for _ in range(3):
            with pytest.raises(CircuitBreakerError):
                breaker.call(lambda: "never executed")
