"""Tests for user-friendly error message formatting."""

from src.agentic_rag.resilience import (
    CircuitOpenError,
    ErrorMessageFormatter,
    GracefulDegradationError,
    MaxRetriesExceededError,
    ServiceType,
    format_degradation_notice,
    format_error_for_user,
    format_retry_notice,
    get_service_display_name,
)


class TestGetServiceDisplayName:
    """Tests for service display name function."""

    def test_neo4j_display_name(self) -> None:
        """Neo4j should display as 'knowledge graph'."""
        assert get_service_display_name(ServiceType.NEO4J) == "knowledge graph"

    def test_supabase_display_name(self) -> None:
        """Supabase should display as 'document database'."""
        assert get_service_display_name(ServiceType.SUPABASE) == "document database"

    def test_none_service(self) -> None:
        """None should return generic 'service'."""
        assert get_service_display_name(None) == "service"


class TestFormatErrorForUser:
    """Tests for format_error_for_user function."""

    def test_circuit_open_error(self) -> None:
        """CircuitOpenError should format with recovery time."""
        error = CircuitOpenError(ServiceType.NEO4J, recovery_time_seconds=30)
        message = format_error_for_user(error)

        assert "knowledge graph" in message
        assert "30 seconds" in message
        assert "temporarily unavailable" in message

    def test_circuit_open_error_minutes(self) -> None:
        """Long recovery time should show minutes."""
        error = CircuitOpenError(ServiceType.NEO4J, recovery_time_seconds=120)
        message = format_error_for_user(error)

        assert "2 minutes" in message

    def test_max_retries_exceeded_error(self) -> None:
        """MaxRetriesExceededError should suggest retry later."""
        error = MaxRetriesExceededError(
            operation="test_operation",
            max_attempts=3,
            last_error=TimeoutError("Connection timed out"),
        )
        message = format_error_for_user(error)

        assert "could not be completed" in message
        assert "try again later" in message

    def test_graceful_degradation_error(self) -> None:
        """GracefulDegradationError should mention backup search."""
        error = GracefulDegradationError(
            primary_service=ServiceType.NEO4J,
            fallback_description="vector-only search",
        )
        message = format_error_for_user(error)

        assert "backup search" in message.lower() or "vector-only" in message.lower()

    def test_timeout_error(self) -> None:
        """Timeout errors should suggest simplifying query."""
        error = TimeoutError("Connection timed out")
        message = format_error_for_user(error)

        assert "took too long" in message

    def test_connection_error(self) -> None:
        """Connection errors should suggest checking connection."""
        error = ConnectionError("Connection refused")
        message = format_error_for_user(error)

        assert "connect" in message.lower()

    def test_rate_limit_error(self) -> None:
        """Rate limit errors should suggest waiting."""
        error = Exception("Rate limit exceeded: too many requests")
        message = format_error_for_user(error)

        assert "wait" in message.lower()

    def test_generic_error_hides_details(self) -> None:
        """Unknown errors should not expose internal details."""
        error = ValueError("Internal database error: connection string invalid")
        message = format_error_for_user(error)

        # Should not contain internal details
        assert "connection string" not in message
        assert "database error" not in message.lower()


class TestFormatDegradationNotice:
    """Tests for format_degradation_notice function."""

    def test_formats_notice(self) -> None:
        """Should format degradation notice correctly."""
        notice = format_degradation_notice(
            ServiceType.NEO4J,
            "vector-only search",
        )

        assert "vector-only search" in notice
        assert "knowledge graph" in notice


class TestFormatRetryNotice:
    """Tests for format_retry_notice function."""

    def test_remaining_attempts(self) -> None:
        """Should show remaining attempts."""
        notice = format_retry_notice(1, 3)
        assert "2 attempts remaining" in notice

    def test_final_attempt(self) -> None:
        """Should indicate final attempt."""
        notice = format_retry_notice(2, 3)
        assert "final attempt" in notice


class TestErrorMessageFormatter:
    """Tests for ErrorMessageFormatter class."""

    def test_format_basic(self) -> None:
        """format should produce user-friendly message."""
        formatter = ErrorMessageFormatter()
        message = formatter.format(TimeoutError("Connection timed out"))

        assert "took too long" in message

    def test_format_with_context(self) -> None:
        """format_with_context should add operation context."""
        formatter = ErrorMessageFormatter(include_service_names=True)
        message = formatter.format_with_context(
            TimeoutError("Connection timed out"),
            operation="fetch_data",
        )

        assert "fetch data" in message.lower() or "took too long" in message

    def test_recovery_suggestion_timeout(self) -> None:
        """Should provide recovery suggestion for timeout."""
        formatter = ErrorMessageFormatter()
        suggestion = formatter.format_recovery_suggestion(TimeoutError("Connection timed out"))

        assert suggestion is not None
        assert "simplify" in suggestion.lower()

    def test_recovery_suggestion_circuit_open(self) -> None:
        """Should provide recovery suggestion for circuit open."""
        formatter = ErrorMessageFormatter()
        error = CircuitOpenError(ServiceType.NEO4J, recovery_time_seconds=30)
        suggestion = formatter.format_recovery_suggestion(error)

        assert suggestion is not None
        assert "recovering" in suggestion.lower() or "shortly" in suggestion.lower()
