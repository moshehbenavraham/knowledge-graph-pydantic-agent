"""
Password History Module

This module provides password history tracking to prevent password reuse.
Stores last 5 password hashes and validates new passwords against them.

Features:
- Track last 5 password hashes per user
- Validate new passwords against history
- Automatic cleanup of old passwords (keep only last 5)
- IP tracking for audit trail
"""

from datetime import UTC, datetime

import bcrypt
import structlog

from src.clients.database import get_supabase_client
from supabase import Client

logger = structlog.get_logger(__name__)


class PasswordHistoryManager:
    """Manages password history for preventing password reuse."""

    MAX_HISTORY = 5  # Keep last 5 passwords

    def __init__(self) -> None:
        """Initialize Password History Manager."""
        self.client: Client | None = None

    def _get_client(self) -> Client:
        """Get Supabase client (cached)."""
        if not self.client:
            self.client = get_supabase_client()
        return self.client

    async def add_password_to_history(
        self, user_id: str, password_hash: str, ip_address: str | None = None
    ) -> None:
        """
        Add password hash to user's history.

        Automatically maintains only the last 5 passwords.

        Args:
            user_id: User's UUID
            password_hash: Bcrypt hash of the password
            ip_address: IP address where password was changed
        """
        client = self._get_client()

        # Add new password to history
        data = {
            "user_id": user_id,
            "password_hash": password_hash,
            "created_ip": ip_address,
        }

        client.table("auth_password_history").insert(data).execute()

        # Cleanup old passwords (keep only last 5)
        await self._cleanup_old_passwords(user_id)

        # Update password_changed_at timestamp in auth_users
        client.table("auth_users").update(
            {"password_changed_at": datetime.now(UTC).isoformat()}
        ).eq("id", user_id).execute()

    async def is_password_reused(self, user_id: str, new_password: str) -> bool:
        """
        Check if new password matches any of the last 5 passwords.

        Args:
            user_id: User's UUID
            new_password: Plaintext password to check

        Returns:
            True if password was used recently, False if it's a new password
        """
        client = self._get_client()

        # Get last 5 password hashes
        result = (
            client.table("auth_password_history")
            .select("password_hash")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(self.MAX_HISTORY)
            .execute()
        )

        if not result.data:
            return False

        # Check new password against each historical hash
        new_password_bytes = new_password.encode()

        for record in result.data:
            password_hash = record["password_hash"]
            if bcrypt.checkpw(new_password_bytes, password_hash.encode()):
                return True

        return False

    async def get_password_history_count(self, user_id: str) -> int:
        """
        Get count of passwords in history for user.

        Args:
            user_id: User's UUID

        Returns:
            Number of passwords in history (max 5)
        """
        client = self._get_client()

        result = (
            client.table("auth_password_history")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )

        return result.count if result.count else 0

    async def get_password_change_dates(self, user_id: str) -> list[datetime]:
        """
        Get dates of password changes for user.

        Args:
            user_id: User's UUID

        Returns:
            List of datetime objects when passwords were changed
        """
        client = self._get_client()

        result = (
            client.table("auth_password_history")
            .select("created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(self.MAX_HISTORY)
            .execute()
        )

        if not result.data:
            return []

        return [
            datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
            for record in result.data
        ]

    async def _cleanup_old_passwords(self, user_id: str) -> None:
        """
        Remove passwords beyond the last 5.

        Args:
            user_id: User's UUID
        """
        client = self._get_client()

        # Get all passwords for user, ordered by date
        result = (
            client.table("auth_password_history")
            .select("id")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        if not result.data or len(result.data) <= self.MAX_HISTORY:
            return

        # Get IDs of passwords to delete (beyond last 5)
        ids_to_delete = [record["id"] for record in result.data[self.MAX_HISTORY :]]

        # Delete old passwords
        for password_id in ids_to_delete:
            client.table("auth_password_history").delete().eq("id", password_id).execute()

    async def clear_history(self, user_id: str) -> int:
        """
        Clear all password history for user.

        Useful when user account is deleted or for testing.

        Args:
            user_id: User's UUID

        Returns:
            Number of records deleted
        """
        client = self._get_client()

        result = client.table("auth_password_history").delete().eq("user_id", user_id).execute()

        return len(result.data) if result.data else 0


# Singleton instance
_password_history_manager: PasswordHistoryManager | None = None


def get_password_history_manager() -> PasswordHistoryManager:
    """
    Get singleton Password History Manager instance.

    Returns:
        PasswordHistoryManager instance
    """
    logger.debug("Getting password history manager singleton instance")
    global _password_history_manager

    if _password_history_manager is None:
        _password_history_manager = PasswordHistoryManager()

    return _password_history_manager


# Helper functions for integration with existing auth system


async def validate_new_password(user_id: str, new_password: str) -> tuple[bool, str]:
    """
    Validate new password against history and strength requirements.

    Args:
        user_id: User's UUID
        new_password: Plaintext password to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if password is valid
        - (False, error_message) if password is invalid
    """
    manager = get_password_history_manager()

    # Check if password was used recently
    is_reused = await manager.is_password_reused(user_id, new_password)

    if is_reused:
        return (
            False,
            "This password has been used recently. Please choose a different password. "
            "You cannot reuse any of your last 5 passwords.",
        )

    return (True, "")


async def record_password_change(
    user_id: str, password_hash: str, ip_address: str | None = None
) -> None:
    """
    Record password change in history.

    Call this function after successfully changing a user's password.

    Args:
        user_id: User's UUID
        password_hash: Bcrypt hash of the new password
        ip_address: IP address where password was changed
    """
    manager = get_password_history_manager()
    await manager.add_password_to_history(user_id, password_hash, ip_address)
