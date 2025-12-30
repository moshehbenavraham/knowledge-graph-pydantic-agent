"""Tests for circuit breaker state machine."""

import asyncio

import pytest

from src.agentic_rag.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    ServiceType,
    get_circuit_breaker,
    get_circuit_breaker_registry,
)


class TestCircuitBreakerStates:
    """Tests for circuit breaker state transitions."""

    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        """Create a fresh circuit breaker for testing."""
        return CircuitBreaker(
            service=ServiceType.NEO4J,
            failure_threshold=3,
            recovery_timeout=1,  # Short timeout for testing
            half_open_requests=2,
        )

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, breaker: CircuitBreaker) -> None:
        """Circuit breaker should start in CLOSED state."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open
        assert not breaker.is_half_open

    @pytest.mark.asyncio
    async def test_can_execute_when_closed(self, breaker: CircuitBreaker) -> None:
        """Should allow execution when circuit is closed."""
        assert await breaker.can_execute() is True

    @pytest.mark.asyncio
    async def test_opens_after_failure_threshold(self, breaker: CircuitBreaker) -> None:
        """Circuit should open after failure threshold is reached."""
        for i in range(3):
            await breaker.record_failure(Exception(f"Error {i}"))

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open

    @pytest.mark.asyncio
    async def test_rejects_requests_when_open(self, breaker: CircuitBreaker) -> None:
        """Should reject requests when circuit is open."""
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure(Exception("Error"))

        assert await breaker.can_execute() is False

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self, breaker: CircuitBreaker) -> None:
        """Should transition to half-open after recovery timeout."""
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure(Exception("Error"))

        assert breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Should transition to half-open on next can_execute
        assert await breaker.can_execute() is True
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_on_success_in_half_open(self, breaker: CircuitBreaker) -> None:
        """Should close circuit on success in half-open state."""
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure(Exception("Error"))

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Transition to half-open
        await breaker.can_execute()
        assert breaker.is_half_open

        # Record success
        await breaker.record_success()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(self, breaker: CircuitBreaker) -> None:
        """Should reopen circuit on failure in half-open state."""
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure(Exception("Error"))

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Transition to half-open
        await breaker.can_execute()
        assert breaker.is_half_open

        # Record failure
        await breaker.record_failure(Exception("Still failing"))

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, breaker: CircuitBreaker) -> None:
        """Success should reset failure count when circuit is closed."""
        await breaker.record_failure(Exception("Error 1"))
        await breaker.record_failure(Exception("Error 2"))
        assert breaker.failure_count == 2

        await breaker.record_success()
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_request_limit(self, breaker: CircuitBreaker) -> None:
        """Half-open state should limit number of requests."""
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure(Exception("Error"))

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # First request transitions to half-open (doesn't count toward limit)
        assert await breaker.can_execute() is True
        assert breaker.is_half_open

        # Next half_open_requests (2) are allowed
        assert await breaker.can_execute() is True  # Count: 1
        assert await breaker.can_execute() is True  # Count: 2

        # Fourth request should be rejected (limit reached)
        assert await breaker.can_execute() is False


class TestCircuitBreakerExecute:
    """Tests for circuit breaker execute method."""

    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        """Create a fresh circuit breaker for testing."""
        return CircuitBreaker(
            service=ServiceType.NEO4J,
            failure_threshold=3,
            recovery_timeout=1,
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, breaker: CircuitBreaker) -> None:
        """Execute should return function result on success."""

        async def successful_func() -> str:
            return "success"

        result = await breaker.execute(successful_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_records_success(self, breaker: CircuitBreaker) -> None:
        """Execute should record success after successful call."""
        await breaker.record_failure(Exception("Previous error"))
        assert breaker.failure_count == 1

        async def successful_func() -> str:
            return "success"

        await breaker.execute(successful_func)
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_execute_records_failure(self, breaker: CircuitBreaker) -> None:
        """Execute should record failure and re-raise exception."""

        async def failing_func() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await breaker.execute(failing_func)

        assert breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_execute_raises_circuit_open_error(self, breaker: CircuitBreaker) -> None:
        """Execute should raise CircuitOpenError when circuit is open."""
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure(Exception("Error"))

        async def any_func() -> str:
            return "success"

        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.execute(any_func)

        assert exc_info.value.service == ServiceType.NEO4J


class TestCircuitBreakerReset:
    """Tests for circuit breaker reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_clears_state(self) -> None:
        """Reset should clear all state."""
        breaker = CircuitBreaker(
            service=ServiceType.NEO4J,
            failure_threshold=3,
            recovery_timeout=60,
        )

        # Put circuit in open state
        for _ in range(3):
            await breaker.record_failure(Exception("Error"))

        assert breaker.is_open

        await breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0


class TestCircuitBreakerStatus:
    """Tests for circuit breaker status reporting."""

    @pytest.mark.asyncio
    async def test_get_status(self) -> None:
        """get_status should return complete circuit state."""
        breaker = CircuitBreaker(
            service=ServiceType.NEO4J,
            failure_threshold=5,
            recovery_timeout=60,
        )

        await breaker.record_failure(Exception("Error"))
        await breaker.record_success()

        status = breaker.get_status()

        assert status["service"] == "neo4j"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0  # Reset by success
        assert status["success_count"] == 1
        assert status["failure_threshold"] == 5
        assert status["recovery_timeout"] == 60


class TestCircuitBreakerRegistry:
    """Tests for circuit breaker registry."""

    @pytest.mark.asyncio
    async def test_get_breaker_creates_new(self) -> None:
        """get_breaker should create new breaker if not exists."""
        registry = get_circuit_breaker_registry()

        # Clear any existing breaker for this service
        registry._breakers.pop(ServiceType.WEB_SEARCH, None)

        breaker = registry.get_breaker(ServiceType.WEB_SEARCH)
        assert breaker is not None
        assert breaker.service == ServiceType.WEB_SEARCH

    @pytest.mark.asyncio
    async def test_get_breaker_returns_same_instance(self) -> None:
        """get_breaker should return same instance for same service."""
        registry = get_circuit_breaker_registry()

        breaker1 = registry.get_breaker(ServiceType.NEO4J)
        breaker2 = registry.get_breaker(ServiceType.NEO4J)

        assert breaker1 is breaker2

    @pytest.mark.asyncio
    async def test_get_all_status(self) -> None:
        """get_all_status should return status for all breakers."""
        registry = get_circuit_breaker_registry()

        # Ensure at least one breaker exists
        registry.get_breaker(ServiceType.NEO4J)

        all_status = registry.get_all_status()
        assert "neo4j" in all_status

    @pytest.mark.asyncio
    async def test_reset_all(self) -> None:
        """reset_all should reset all circuit breakers."""
        registry = get_circuit_breaker_registry()

        breaker = registry.get_breaker(ServiceType.NEO4J)
        for _ in range(5):
            await breaker.record_failure(Exception("Error"))

        await registry.reset_all()

        assert breaker.state == CircuitState.CLOSED


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_circuit_breaker(self) -> None:
        """get_circuit_breaker should return breaker for service."""
        breaker = get_circuit_breaker(ServiceType.NEO4J)
        assert breaker.service == ServiceType.NEO4J
