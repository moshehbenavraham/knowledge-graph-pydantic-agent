"""Tests for graceful degradation handlers."""

from unittest.mock import AsyncMock, patch

import pytest

from src.agentic_rag.resilience import (
    DegradationResult,
    DegradationState,
    GracefulDegradationError,
    GracefulDegradationHandler,
    SearchDegradationHandler,
    ServiceType,
    get_search_degradation_handler,
)


class TestDegradationState:
    """Tests for DegradationState dataclass."""

    def test_initial_state(self) -> None:
        """Initial state should not be degraded."""
        state = DegradationState()
        assert state.is_degraded is False
        assert state.fallback_count == 0
        assert state.last_error is None

    def test_enter_degraded_mode(self) -> None:
        """enter_degraded_mode should update state correctly."""
        state = DegradationState()
        state.enter_degraded_mode("Test error")

        assert state.is_degraded is True
        assert state.degraded_since is not None
        assert state.fallback_count == 1
        assert state.last_error == "Test error"

    def test_exit_degraded_mode(self) -> None:
        """exit_degraded_mode should reset degraded state."""
        state = DegradationState()
        state.enter_degraded_mode("Test error")
        state.exit_degraded_mode()

        assert state.is_degraded is False
        assert state.degraded_since is None
        assert state.last_recovery is not None
        assert state.last_error is None

    def test_to_dict(self) -> None:
        """to_dict should return all state fields."""
        state = DegradationState()
        state.enter_degraded_mode("Test error")

        data = state.to_dict()
        assert "is_degraded" in data
        assert "fallback_count" in data
        assert "last_error" in data
        assert data["is_degraded"] is True


class TestDegradationResult:
    """Tests for DegradationResult dataclass."""

    def test_successful_primary(self) -> None:
        """Result from successful primary should not indicate fallback."""
        result = DegradationResult(value="primary result")
        assert result.used_fallback is False
        assert result.fallback_reason is None

    def test_fallback_used(self) -> None:
        """Result from fallback should include reason."""
        result = DegradationResult(
            value="fallback result",
            used_fallback=True,
            fallback_reason="Primary service unavailable",
            primary_service=ServiceType.NEO4J,
            fallback_description="vector-only search",
        )
        assert result.used_fallback is True
        assert result.fallback_reason == "Primary service unavailable"


class TestGracefulDegradationHandler:
    """Tests for GracefulDegradationHandler."""

    @pytest.fixture
    def handler(self) -> GracefulDegradationHandler[str]:
        """Create a handler for testing."""
        return GracefulDegradationHandler(
            primary_service=ServiceType.NEO4J,
            fallback_description="vector-only search",
            enabled=True,
        )

    @pytest.mark.asyncio
    async def test_successful_primary(self, handler: GracefulDegradationHandler[str]) -> None:
        """Successful primary should not trigger fallback."""

        async def primary() -> str:
            return "primary result"

        async def fallback() -> str:
            return "fallback result"

        result = await handler.execute(primary, fallback)

        assert result.value == "primary result"
        assert result.used_fallback is False

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(
        self, handler: GracefulDegradationHandler[str]
    ) -> None:
        """Should use fallback when primary fails."""

        async def primary() -> str:
            raise ConnectionError("Neo4j unavailable")

        async def fallback() -> str:
            return "fallback result"

        result = await handler.execute(primary, fallback)

        assert result.value == "fallback result"
        assert result.used_fallback is True
        assert result.primary_service == ServiceType.NEO4J
        assert result.fallback_description == "vector-only search"

    @pytest.mark.asyncio
    async def test_disabled_degradation_raises(self) -> None:
        """When disabled, should raise primary error."""
        handler: GracefulDegradationHandler[str] = GracefulDegradationHandler(
            primary_service=ServiceType.NEO4J,
            fallback_description="vector-only search",
            enabled=False,
        )

        async def primary() -> str:
            raise ConnectionError("Neo4j unavailable")

        async def fallback() -> str:
            return "fallback result"

        with pytest.raises(ConnectionError):
            await handler.execute(primary, fallback)

    @pytest.mark.asyncio
    async def test_tracks_degradation_state(self, handler: GracefulDegradationHandler[str]) -> None:
        """Handler should track degradation state."""

        async def primary() -> str:
            raise ConnectionError("Neo4j unavailable")

        async def fallback() -> str:
            return "fallback result"

        await handler.execute(primary, fallback)

        assert handler.state.is_degraded is True
        assert handler.state.fallback_count == 1

    @pytest.mark.asyncio
    async def test_exits_degraded_on_recovery(
        self, handler: GracefulDegradationHandler[str]
    ) -> None:
        """Should exit degraded mode when primary recovers."""
        call_count = 0

        async def primary() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Neo4j unavailable")
            return "primary result"

        async def fallback() -> str:
            return "fallback result"

        # First call - triggers fallback
        result1 = await handler.execute(primary, fallback)
        assert result1.used_fallback is True
        assert handler.state.is_degraded is True

        # Second call - primary recovers
        result2 = await handler.execute(primary, fallback)
        assert result2.used_fallback is False
        assert handler.state.is_degraded is False

    @pytest.mark.asyncio
    async def test_preemptive_fallback_when_circuit_open(
        self, handler: GracefulDegradationHandler[str]
    ) -> None:
        """Should use fallback preemptively when circuit is open."""

        async def primary() -> str:
            return "primary result"

        async def fallback() -> str:
            return "fallback result"

        # Mock the circuit breaker to be open
        with patch("src.agentic_rag.resilience.handlers.get_circuit_breaker") as mock_get_breaker:
            mock_breaker = AsyncMock()
            mock_breaker.is_open = True
            mock_get_breaker.return_value = mock_breaker

            result = await handler.execute(primary, fallback)

        assert result.value == "fallback result"
        assert result.used_fallback is True

    @pytest.mark.asyncio
    async def test_double_failure_raises(self, handler: GracefulDegradationHandler[str]) -> None:
        """Should raise when both primary and fallback fail."""

        async def primary() -> str:
            raise ConnectionError("Primary failed")

        async def fallback() -> str:
            raise RuntimeError("Fallback also failed")

        with pytest.raises(GracefulDegradationError):
            await handler.execute(primary, fallback, raise_on_fallback_failure=True)

    @pytest.mark.asyncio
    async def test_get_status(self, handler: GracefulDegradationHandler[str]) -> None:
        """get_status should return complete handler state."""
        status = handler.get_status()

        assert status["primary_service"] == "neo4j"
        assert status["fallback_description"] == "vector-only search"
        assert status["enabled"] is True
        assert "degradation_state" in status


class TestSearchDegradationHandler:
    """Tests for SearchDegradationHandler."""

    @pytest.mark.asyncio
    async def test_search_degradation(self) -> None:
        """SearchDegradationHandler should work for search operations."""
        handler = SearchDegradationHandler(enabled=True)

        async def hybrid_search() -> list[str]:
            raise ConnectionError("Graph unavailable")

        async def vector_search() -> list[str]:
            return ["vector result"]

        result = await handler.execute_search(hybrid_search, vector_search)

        assert result.value == ["vector result"]
        assert result.used_fallback is True
        assert result.fallback_description == "vector-only search"

    def test_search_handler_service_type(self) -> None:
        """SearchDegradationHandler should target Neo4j."""
        handler = SearchDegradationHandler()
        assert handler.primary_service == ServiceType.NEO4J


class TestGetSearchDegradationHandler:
    """Tests for get_search_degradation_handler singleton."""

    def test_returns_singleton(self) -> None:
        """Should return the same instance."""
        handler1 = get_search_degradation_handler()
        handler2 = get_search_degradation_handler()
        assert handler1 is handler2

    def test_is_search_handler(self) -> None:
        """Should return a SearchDegradationHandler."""
        handler = get_search_degradation_handler()
        assert isinstance(handler, SearchDegradationHandler)
