"""Tests for authentication security features."""

import time

import pytest

from src.auth.security import LoginRateLimiter, get_rate_limiter


@pytest.fixture
def rate_limiter():
    """Create a fresh rate limiter for testing."""
    return LoginRateLimiter(max_attempts=3, window_minutes=5, lockout_minutes=5)


def test_rate_limiter_initialization(rate_limiter):
    """Test rate limiter initializes with correct settings."""
    assert rate_limiter.max_attempts == 3
    assert rate_limiter.window_seconds == 5 * 60
    assert rate_limiter.lockout_seconds == 5 * 60


def test_no_lockout_initially(rate_limiter):
    """Test that users are not locked out initially."""
    is_locked, remaining = rate_limiter.is_locked_out("testuser")
    assert is_locked is False
    assert remaining == 0.0


def test_record_failed_attempt(rate_limiter):
    """Test recording failed login attempts."""
    rate_limiter.record_failed_attempt("testuser", "192.168.1.1")

    remaining = rate_limiter.get_remaining_attempts("testuser")
    assert remaining == 2  # 3 max - 1 failed = 2 remaining


def test_lockout_after_max_attempts(rate_limiter):
    """Test that user is locked out after max failed attempts."""
    # Record max attempts (3)
    for i in range(3):
        rate_limiter.record_failed_attempt("testuser", f"192.168.1.{i}")

    # Should be locked out
    is_locked, remaining = rate_limiter.is_locked_out("testuser")
    assert is_locked is True
    assert remaining > 0

    # Remaining attempts should be 0
    assert rate_limiter.get_remaining_attempts("testuser") == 0


def test_successful_login_clears_failed_attempts(rate_limiter):
    """Test that successful login clears failed attempts."""
    # Record some failed attempts
    rate_limiter.record_failed_attempt("testuser")
    rate_limiter.record_failed_attempt("testuser")

    # Verify there are failed attempts
    assert rate_limiter.get_remaining_attempts("testuser") == 1

    # Successful login should clear
    rate_limiter.record_successful_login("testuser")

    # Should have full attempts again
    assert rate_limiter.get_remaining_attempts("testuser") == 3


def test_successful_login_clears_lockout(rate_limiter):
    """Test that successful login clears active lockout."""
    # Lock out user
    for _ in range(3):
        rate_limiter.record_failed_attempt("testuser")

    is_locked, _ = rate_limiter.is_locked_out("testuser")
    assert is_locked is True

    # Successful login (e.g., after manual unlock)
    rate_limiter.record_successful_login("testuser")

    # Should no longer be locked
    is_locked, _ = rate_limiter.is_locked_out("testuser")
    assert is_locked is False


def test_multiple_users_independent(rate_limiter):
    """Test that rate limiting is independent per user."""
    # Lock out user1
    for _ in range(3):
        rate_limiter.record_failed_attempt("user1")

    # user2 should not be affected
    is_locked, _ = rate_limiter.is_locked_out("user2")
    assert is_locked is False
    assert rate_limiter.get_remaining_attempts("user2") == 3


def test_lockout_expires_after_timeout(rate_limiter):
    """Test that lockout expires after timeout period."""
    # Create rate limiter with very short lockout (1 second for testing)
    fast_limiter = LoginRateLimiter(max_attempts=2, window_minutes=1, lockout_minutes=0.02)

    # Lock out user
    fast_limiter.record_failed_attempt("testuser")
    fast_limiter.record_failed_attempt("testuser")

    # Should be locked
    is_locked, _ = fast_limiter.is_locked_out("testuser")
    assert is_locked is True

    # Wait for lockout to expire (1.5 seconds to be safe)
    time.sleep(1.5)

    # Should no longer be locked
    is_locked, _ = fast_limiter.is_locked_out("testuser")
    assert is_locked is False


def test_old_attempts_cleaned_up(rate_limiter):
    """Test that attempts outside the time window are cleaned up."""
    # Create rate limiter with very short window (1 second)
    fast_limiter = LoginRateLimiter(max_attempts=3, window_minutes=0.02, lockout_minutes=5)

    # Record an attempt
    fast_limiter.record_failed_attempt("testuser")
    assert fast_limiter.get_remaining_attempts("testuser") == 2

    # Wait for window to pass
    time.sleep(1.5)

    # Old attempt should be cleaned up, back to full attempts
    assert fast_limiter.get_remaining_attempts("testuser") == 3


def test_get_stats(rate_limiter):
    """Test getting rate limiter statistics."""
    # Add some data
    rate_limiter.record_failed_attempt("user1")
    rate_limiter.record_failed_attempt("user2")

    # Lock out user3
    for _ in range(3):
        rate_limiter.record_failed_attempt("user3")

    stats = rate_limiter.get_stats()

    assert stats["tracked_users"] >= 2  # At least user1 and user2
    assert stats["locked_out_users"] == 1  # user3 is locked out
    assert stats["max_attempts"] == 3
    assert stats["window_minutes"] == 5
    assert stats["lockout_minutes"] == 5


def test_get_global_rate_limiter():
    """Test getting global rate limiter instance."""
    limiter1 = get_rate_limiter()
    limiter2 = get_rate_limiter()

    # Should be same instance
    assert limiter1 is limiter2


def test_rate_limiter_with_no_ip_address(rate_limiter):
    """Test recording failed attempt without IP address."""
    rate_limiter.record_failed_attempt("testuser")  # No IP provided

    remaining = rate_limiter.get_remaining_attempts("testuser")
    assert remaining == 2  # Should still work


def test_remaining_attempts_calculation(rate_limiter):
    """Test remaining attempts calculation is correct."""
    # Start with max attempts
    assert rate_limiter.get_remaining_attempts("testuser") == 3

    # After 1 failure
    rate_limiter.record_failed_attempt("testuser")
    assert rate_limiter.get_remaining_attempts("testuser") == 2

    # After 2 failures
    rate_limiter.record_failed_attempt("testuser")
    assert rate_limiter.get_remaining_attempts("testuser") == 1

    # After 3 failures (locked out)
    rate_limiter.record_failed_attempt("testuser")
    assert rate_limiter.get_remaining_attempts("testuser") == 0


def test_lockout_remaining_time_decreases(rate_limiter):
    """Test that lockout remaining time decreases over time."""
    # Lock out user
    for _ in range(3):
        rate_limiter.record_failed_attempt("testuser")

    # Get initial remaining time
    is_locked1, remaining1 = rate_limiter.is_locked_out("testuser")
    assert is_locked1 is True

    # Wait a bit
    time.sleep(0.5)

    # Check again - remaining time should be less
    is_locked2, remaining2 = rate_limiter.is_locked_out("testuser")
    assert is_locked2 is True
    assert remaining2 < remaining1


def test_empty_username_handling(rate_limiter):
    """Test handling of empty username."""
    rate_limiter.record_failed_attempt("")

    # Should track empty string as a username
    remaining = rate_limiter.get_remaining_attempts("")
    assert remaining == 2
