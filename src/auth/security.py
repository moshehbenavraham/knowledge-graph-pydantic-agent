"""Security features for authentication system.

This module provides rate limiting, login attempt tracking, and security event logging.
"""

import time
from collections import defaultdict
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class LoginRateLimiter:
    """Rate limiter for login attempts.

    Tracks failed login attempts and enforces temporary lockouts after exceeding
    the maximum allowed attempts within a time window.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        window_minutes: int = 15,
        lockout_minutes: int = 15,
    ):
        """Initialize rate limiter.

        Args:
            max_attempts: Maximum failed attempts before lockout
            window_minutes: Time window in minutes to track attempts
            lockout_minutes: Duration in minutes to lock out after max attempts
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_minutes * 60
        self.lockout_seconds = lockout_minutes * 60

        # Track failed attempts: {username: [(timestamp, ip_address), ...]}
        self._failed_attempts: dict[str, list[tuple[float, str]]] = defaultdict(list)

        # Track lockouts: {username: lockout_until_timestamp}
        self._lockouts: dict[str, float] = {}

    def _cleanup_old_attempts(self, username: str) -> None:
        """Remove attempts outside the tracking window.

        Args:
            username: Username to clean up attempts for
        """
        cutoff = time.time() - self.window_seconds
        if username in self._failed_attempts:
            self._failed_attempts[username] = [
                (ts, ip) for ts, ip in self._failed_attempts[username] if ts > cutoff
            ]

    def _cleanup_expired_lockouts(self) -> None:
        """Remove expired lockouts."""
        current_time = time.time()
        expired = [user for user, until in self._lockouts.items() if until <= current_time]
        for user in expired:
            del self._lockouts[user]
            logger.info("Lockout expired", username=user)

    def is_locked_out(self, username: str) -> tuple[bool, float]:
        """Check if username is currently locked out.

        Args:
            username: Username to check

        Returns:
            Tuple of (is_locked_out, seconds_remaining)
        """
        logger.debug("Checking lockout status", username=username)
        self._cleanup_expired_lockouts()

        if username in self._lockouts:
            remaining = self._lockouts[username] - time.time()
            if remaining > 0:
                return True, remaining
            # Lockout expired, clean up
            del self._lockouts[username]
            return False, 0.0

        return False, 0.0

    def record_failed_attempt(self, username: str, ip_address: str = "unknown") -> None:
        """Record a failed login attempt.

        Args:
            username: Username that failed login
            ip_address: IP address of the attempt (optional)
        """
        self._cleanup_old_attempts(username)

        # Add new failed attempt
        self._failed_attempts[username].append((time.time(), ip_address))

        # Check if should be locked out
        attempt_count = len(self._failed_attempts[username])
        logger.warning(
            "Failed login attempt",
            username=username,
            ip_address=ip_address,
            attempt_count=attempt_count,
            max_attempts=self.max_attempts,
        )

        if attempt_count >= self.max_attempts:
            # Lock out user
            lockout_until = time.time() + self.lockout_seconds
            self._lockouts[username] = lockout_until

            logger.error(
                "User locked out due to excessive failed attempts",
                username=username,
                lockout_duration_minutes=self.lockout_seconds / 60,
                attempt_count=attempt_count,
            )

    def record_successful_login(self, username: str) -> None:
        """Record successful login and clear failed attempts.

        Args:
            username: Username that successfully logged in
        """
        # Clear failed attempts
        if username in self._failed_attempts:
            del self._failed_attempts[username]

        # Clear lockout if any
        if username in self._lockouts:
            del self._lockouts[username]

        logger.info("Successful login", username=username)

    def get_remaining_attempts(self, username: str) -> int:
        """Get remaining attempts before lockout.

        Args:
            username: Username to check

        Returns:
            Number of remaining attempts (0 if locked out)
        """
        logger.debug("Getting remaining attempts", username=username)
        self._cleanup_old_attempts(username)

        if username in self._lockouts:
            return 0

        failed_count = len(self._failed_attempts.get(username, []))
        return max(0, self.max_attempts - failed_count)

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with current state statistics
        """
        self._cleanup_expired_lockouts()

        return {
            "tracked_users": len(self._failed_attempts),
            "locked_out_users": len(self._lockouts),
            "max_attempts": self.max_attempts,
            "window_minutes": self.window_seconds / 60,
            "lockout_minutes": self.lockout_seconds / 60,
        }


# Global rate limiter instance
_rate_limiter: LoginRateLimiter | None = None


def get_rate_limiter() -> LoginRateLimiter:
    """Get global rate limiter instance.

    Returns:
        Global LoginRateLimiter instance
    """
    logger.debug("Getting rate limiter instance")
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = LoginRateLimiter(
            max_attempts=5,
            window_minutes=15,
            lockout_minutes=15,
        )
    return _rate_limiter


async def log_auth_event(
    event_type: str,
    username: str,
    success: bool,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log authentication event (currently logged to auth tables only).

    Note: Analytics system integration disabled until dedicated auth event model is added.
    Auth events are already logged to auth_sessions and other auth-specific tables.

    Args:
        event_type: Type of auth event (login, logout, password_change, etc.)
        username: Username involved in the event
        success: Whether the event was successful
        metadata: Optional additional metadata
    """
    # TODO: Add dedicated auth event model to analytics system
    # For now, auth events are logged to database auth tables (auth_sessions, etc.)
    logger.info(
        "Auth event",
        event_type=event_type,
        username=username,
        success=success,
        metadata=metadata or {},
    )
