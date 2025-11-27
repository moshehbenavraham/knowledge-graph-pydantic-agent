"""
Password Breach Detection Module

This module integrates with the haveibeenpwned.com Passwords API (v3)
to check if passwords have been exposed in data breaches.

Uses k-Anonymity model:
- Only sends first 5 characters of SHA-1 hash to API
- API returns all hashes with that prefix
- Client verifies full hash locally
- No passwords are sent to the API

API Documentation: https://haveibeenpwned.com/API/v3#PwnedPasswords
"""

import hashlib
from datetime import UTC, datetime

import httpx
import structlog

from src.clients.database import get_supabase_client
from supabase import Client

logger = structlog.get_logger(__name__)


class BreachDetectionManager:
    """Manages password breach detection using haveibeenpwned.com API."""

    HIBP_API_URL = "https://api.pwnedpasswords.com/range/{hash_prefix}"
    TIMEOUT = 10.0  # seconds

    def __init__(self) -> None:
        """Initialize Breach Detection Manager."""
        self.client: Client | None = None

    def _get_client(self) -> Client:
        """Get Supabase client (cached)."""
        if not self.client:
            self.client = get_supabase_client()
        return self.client

    def _hash_password(self, password: str) -> str:
        """
        Hash password with SHA-1 for breach detection.

        Note: SHA-1 is used because it's the haveibeenpwned.com API standard.
        This is NOT used for password storage (we use bcrypt for that).

        Args:
            password: Plaintext password

        Returns:
            Uppercase SHA-1 hash (40 characters)
        """
        sha1_hash = hashlib.sha1(password.encode(), usedforsecurity=False).hexdigest()
        return sha1_hash.upper()

    async def check_password_breach(
        self, password: str, user_id: str | None = None, check_type: str = "manual"
    ) -> tuple[bool, int]:
        """
        Check if password has been exposed in data breaches.

        Uses k-Anonymity model - only first 5 chars of hash sent to API.

        Args:
            password: Plaintext password to check
            user_id: Optional user ID for logging
            check_type: Type of check ('registration', 'login', 'password_change', 'manual')

        Returns:
            Tuple of (is_breached, breach_count)
            - is_breached: True if password found in breaches
            - breach_count: Number of times password appears in breaches
        """
        # Hash password
        password_hash = self._hash_password(password)

        # Split hash into prefix (5 chars) and suffix (35 chars)
        hash_prefix = password_hash[:5]
        hash_suffix = password_hash[5:]

        try:
            # Query haveibeenpwned.com API using centralized HTTP client factory
            from src.config.clients import clients_config

            async with clients_config.create_http_client(  # CONST-III-001 - Use centralized HTTP client factory
                timeout=self.TIMEOUT
            ) as client:
                response = await client.get(
                    self.HIBP_API_URL.format(hash_prefix=hash_prefix),
                    headers={"User-Agent": "BaseAgent-PasswordBreachDetection"},
                )

                if response.status_code != 200:
                    # API error - log but don't block user
                    await self._log_breach_check(
                        user_id=user_id,
                        hash_prefix=hash_prefix,
                        is_breached=False,
                        breach_count=0,
                        check_type=check_type,
                    )
                    return (False, 0)

                # Parse response (format: "SUFFIX:COUNT\r\n" for each hash)
                response_lines = response.text.strip().split("\r\n")

                for line in response_lines:
                    suffix, count = line.split(":")
                    if suffix == hash_suffix:
                        # Password found in breaches
                        breach_count = int(count)
                        await self._log_breach_check(
                            user_id=user_id,
                            hash_prefix=hash_prefix,
                            is_breached=True,
                            breach_count=breach_count,
                            check_type=check_type,
                        )
                        return (True, breach_count)

                # Password not found in breaches
                await self._log_breach_check(
                    user_id=user_id,
                    hash_prefix=hash_prefix,
                    is_breached=False,
                    breach_count=0,
                    check_type=check_type,
                )
                return (False, 0)

        except httpx.TimeoutException:
            # Timeout - log but don't block user
            await self._log_breach_check(
                user_id=user_id,
                hash_prefix=hash_prefix,
                is_breached=False,
                breach_count=0,
                check_type=f"{check_type}_timeout",
            )
            return (False, 0)

        except Exception:
            # Other error - log but don't block user
            await self._log_breach_check(
                user_id=user_id,
                hash_prefix=hash_prefix,
                is_breached=False,
                breach_count=0,
                check_type=f"{check_type}_error",
            )
            return (False, 0)

    async def get_breach_status(self, password: str) -> tuple[bool, int, str | None]:
        """
        Check breach status and return user-friendly message.

        Args:
            password: Plaintext password to check

        Returns:
            Tuple of (is_breached, breach_count, message)
            - is_breached: True if password found in breaches
            - breach_count: Number of times password appears
            - message: User-friendly message explaining the result
        """
        is_breached, breach_count = await self.check_password_breach(password)

        if not is_breached:
            return (False, 0, "Password has not been found in any known data breaches.")

        if breach_count < 10:
            message = (
                f"⚠️ This password has been found in {breach_count} data breach(es). "
                "We recommend choosing a different password for better security."
            )
        elif breach_count < 100:
            message = (
                f"⚠️ Warning: This password has been found in {breach_count} data breaches. "
                "Please choose a more secure password."
            )
        else:
            message = (
                f"🚨 Critical: This password has been found in {breach_count:,} data breaches! "
                "This password is highly compromised and should NOT be used."
            )

        return (True, breach_count, message)

    async def get_last_check(self, user_id: str) -> datetime | None:
        """
        Get timestamp of last breach check for user.

        Args:
            user_id: User's UUID

        Returns:
            Datetime of last check, or None if never checked
        """
        client = self._get_client()

        result = (
            client.table("auth_users").select("last_breach_check_at").eq("id", user_id).execute()
        )

        if not result.data or not result.data[0].get("last_breach_check_at"):
            return None

        return datetime.fromisoformat(result.data[0]["last_breach_check_at"].replace("Z", "+00:00"))

    async def should_check_breach(self, user_id: str, check_interval_days: int = 30) -> bool:
        """
        Determine if breach check should be performed based on last check date.

        Args:
            user_id: User's UUID
            check_interval_days: Days between automatic checks (default: 30)

        Returns:
            True if check should be performed, False otherwise
        """
        last_check = await self.get_last_check(user_id)

        if not last_check:
            return True

        days_since_check = (datetime.now(UTC) - last_check).days
        return days_since_check >= check_interval_days

    async def _log_breach_check(
        self,
        hash_prefix: str,
        is_breached: bool,
        breach_count: int,
        check_type: str,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """
        Log breach check to database.

        Args:
            hash_prefix: First 5 characters of SHA-1 hash
            is_breached: Whether password was found in breaches
            breach_count: Number of times password appears
            check_type: Type of check
            user_id: Optional user UUID
            ip_address: Optional IP address
        """
        client = self._get_client()

        data = {
            "password_hash_prefix": hash_prefix,
            "is_breached": is_breached,
            "breach_count": breach_count,
            "check_type": check_type,
            "ip_address": ip_address,
        }

        if user_id:
            data["user_id"] = user_id

        client.table("auth_breach_checks").insert(data).execute()

        # Update last_breach_check_at in auth_users
        if user_id:
            client.table("auth_users").update(
                {"last_breach_check_at": datetime.now(UTC).isoformat()}
            ).eq("id", user_id).execute()


# Singleton instance
_breach_detection_manager: BreachDetectionManager | None = None


def get_breach_detection_manager() -> BreachDetectionManager:
    """
    Get singleton Breach Detection Manager instance.

    Returns:
        BreachDetectionManager instance
    """
    logger.debug("Getting breach detection manager singleton instance")
    global _breach_detection_manager

    if _breach_detection_manager is None:
        _breach_detection_manager = BreachDetectionManager()

    return _breach_detection_manager


# Helper functions for integration with existing auth system


async def check_password_safety(
    password: str, user_id: str | None = None, check_type: str = "manual"
) -> tuple[bool, str]:
    """
    Check if password is safe to use (not breached).

    Args:
        password: Plaintext password to check
        user_id: Optional user ID for logging
        check_type: Type of check

    Returns:
        Tuple of (is_safe, message)
        - is_safe: True if password is safe, False if breached
        - message: User-friendly message
    """
    manager = get_breach_detection_manager()
    is_breached, _, message = await manager.get_breach_status(password)

    if is_breached:
        return (False, message or "Password found in breach database")

    return (True, message or "Password is safe")


async def validate_password_breach(
    password: str, user_id: str | None = None, check_type: str = "manual"
) -> tuple[bool, str]:
    """
    Validate password against breach database.

    Similar to check_password_safety but returns validation tuple format.

    Args:
        password: Plaintext password to check
        user_id: Optional user ID for logging
        check_type: Type of check

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if password is safe
        - (False, error_message) if password is breached
    """
    is_safe, message = await check_password_safety(password, user_id, check_type)

    if not is_safe:
        return (False, message)

    return (True, "")
