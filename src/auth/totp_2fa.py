"""
Two-Factor Authentication (2FA) Module using TOTP

This module provides comprehensive 2FA functionality including:
- TOTP secret generation and verification
- QR code generation for authenticator apps
- Backup code generation and validation
- 2FA enablement/disablement
- Rate limiting for verification attempts

Dependencies:
- pyotp: TOTP generation and verification
- qrcode: QR code generation
- cryptography: Secret encryption
- bcrypt: Backup code hashing
"""

import base64
import io
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import cast

import bcrypt
import pyotp
import qrcode
import structlog
from cryptography.fernet import Fernet
from supabase import Client

from src.clients.database import get_supabase_client
from src.config import get_settings

logger = structlog.get_logger(__name__)

settings = get_settings()


class TOTPManager:
    """Manages TOTP (Time-based One-Time Password) operations for 2FA."""

    def __init__(self, encryption_key: str | None = None):
        """
        Initialize TOTP Manager.

        Args:
            encryption_key: Fernet encryption key for secret storage.
                          If None, generates a new key (for testing only).
        """
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode())
        else:
            # Generate key for testing/development only
            self.cipher = Fernet(Fernet.generate_key())

        self.client: Client | None = None

    def _get_client(self) -> Client:
        """Get Supabase client (cached)."""
        if not self.client:
            self.client = get_supabase_client()
        return self.client

    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret (base32-encoded random string).

        Returns:
            Base32-encoded secret string
        """
        logger.debug("generate_secret called")
        return pyotp.random_base32()

    def encrypt_secret(self, secret: str) -> str:
        """
        Encrypt TOTP secret for database storage.

        Args:
            secret: Base32-encoded TOTP secret

        Returns:
            Encrypted secret (base64-encoded)
        """
        logger.debug("encrypt_secret called", has_secret=bool(secret))
        encrypted_bytes = self.cipher.encrypt(secret.encode())
        return base64.b64encode(encrypted_bytes).decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """
        Decrypt TOTP secret from database.

        Args:
            encrypted_secret: Base64-encoded encrypted secret

        Returns:
            Decrypted base32-encoded TOTP secret
        """
        logger.debug("decrypt_secret called", has_encrypted_secret=bool(encrypted_secret))
        encrypted_bytes = base64.b64decode(encrypted_secret.encode())
        decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()

    def generate_qr_code(
        self, secret: str, username: str, issuer: str = "Knowledge Graph Pydantic Agent"
    ) -> str:
        """
        Generate QR code for authenticator app setup.

        Args:
            secret: Base32-encoded TOTP secret
            username: User's username or email
            issuer: Application name (default: "Knowledge Graph Pydantic Agent")

        Returns:
            Base64-encoded PNG image of QR code
        """
        logger.info(
            "generate_qr_code called", username=username, issuer=issuer, has_secret=bool(secret)
        )
        # Generate provisioning URI for authenticator apps
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=username, issuer_name=issuer)

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        # Convert to PNG image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64 for display in Streamlit
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        return img_base64

    def verify_code(self, secret: str, code: str, window: int = 1) -> bool:
        """
        Verify TOTP code against secret.

        Args:
            secret: Base32-encoded TOTP secret
            code: 6-digit TOTP code from authenticator app
            window: Number of time windows to check (default: 1 = ±30s)

        Returns:
            True if code is valid, False otherwise
        """
        logger.debug(
            "verify_code called", has_secret=bool(secret), has_code=bool(code), window=window
        )
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)

    def setup_2fa(
        self, user_id: str, username: str, ip_address: str | None = None
    ) -> dict[str, str]:
        """
        Initialize 2FA setup for a user.

        Creates TOTP secret and QR code, but does NOT enable 2FA yet.
        User must verify the code before 2FA is enabled.

        Args:
            user_id: User's UUID
            username: User's username or email
            ip_address: IP address of setup request

        Returns:
            Dictionary with 'secret' and 'qr_code' (base64-encoded PNG)
        """
        logger.info("setup_2fa called", user_id=user_id, username=username, ip_address=ip_address)
        client = self._get_client()

        # Generate new TOTP secret
        secret = self.generate_secret()
        encrypted_secret = self.encrypt_secret(secret)

        # Store in database (disabled until verified)
        data = {
            "user_id": user_id,
            "secret_encrypted": encrypted_secret,
            "is_enabled": False,
            "created_ip": ip_address,
        }

        # Upsert (insert or update if already exists)
        client.table("auth_totp_secrets").upsert(data).execute()

        # Generate QR code
        qr_code = self.generate_qr_code(secret, username)

        return {"secret": secret, "qr_code": qr_code}

    def verify_and_enable_2fa(self, user_id: str, code: str, ip_address: str | None = None) -> bool:
        """
        Verify TOTP code and enable 2FA for user.

        Args:
            user_id: User's UUID
            code: 6-digit TOTP code from authenticator app
            ip_address: IP address of verification request

        Returns:
            True if code verified and 2FA enabled, False otherwise
        """
        logger.info(
            "verify_and_enable_2fa called",
            user_id=user_id,
            has_code=bool(code),
            ip_address=ip_address,
        )
        client = self._get_client()

        # Get user's TOTP secret
        result = (
            client.table("auth_totp_secrets")
            .select("secret_encrypted")
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            return False

        encrypted_secret = result.data[0]["secret_encrypted"]
        secret = self.decrypt_secret(encrypted_secret)

        # Verify code
        if not self.verify_code(secret, code):
            # Log failed attempt
            self._log_2fa_attempt(user_id, False, "totp", ip_address)
            return False

        # Enable 2FA
        client.table("auth_totp_secrets").update(
            {"is_enabled": True, "verified_at": datetime.now(UTC).isoformat()}
        ).eq("user_id", user_id).execute()

        # Log successful verification
        self._log_2fa_attempt(user_id, True, "totp", ip_address)

        return True

    def disable_2fa(self, user_id: str) -> bool:
        """
        Disable 2FA for user.

        Args:
            user_id: User's UUID

        Returns:
            True if 2FA was disabled, False if user didn't have 2FA
        """
        logger.info("disable_2fa called", user_id=user_id)
        client = self._get_client()

        result = (
            client.table("auth_totp_secrets")
            .update({"is_enabled": False})
            .eq("user_id", user_id)
            .execute()
        )

        return len(result.data) > 0

    def verify_login_code(self, user_id: str, code: str, ip_address: str | None = None) -> bool:
        """
        Verify TOTP code during login.

        Args:
            user_id: User's UUID
            code: 6-digit TOTP code from authenticator app
            ip_address: IP address of login request

        Returns:
            True if code is valid, False otherwise
        """
        logger.info(
            "verify_login_code called", user_id=user_id, has_code=bool(code), ip_address=ip_address
        )
        client = self._get_client()

        # Check rate limiting (max 5 failures per hour)
        failure_count = self._count_recent_failures(user_id)
        if failure_count >= 5:
            return False

        # Get user's TOTP secret
        result = (
            client.table("auth_totp_secrets")
            .select("secret_encrypted, is_enabled")
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data or not result.data[0]["is_enabled"]:
            return False

        encrypted_secret = result.data[0]["secret_encrypted"]
        secret = self.decrypt_secret(encrypted_secret)

        # Verify code
        is_valid = self.verify_code(secret, code)

        # Log attempt
        self._log_2fa_attempt(user_id, is_valid, "totp", ip_address)

        return is_valid

    def is_2fa_enabled(self, user_id: str) -> bool:
        """
        Check if 2FA is enabled for user.

        Args:
            user_id: User's UUID

        Returns:
            True if 2FA is enabled, False otherwise
        """
        logger.debug("is_2fa_enabled called", user_id=user_id)
        client = self._get_client()

        result = (
            client.table("auth_totp_secrets").select("is_enabled").eq("user_id", user_id).execute()
        )

        if not result.data:
            return False

        return cast("bool", result.data[0]["is_enabled"])

    def requires_2fa(self, user_id: str) -> bool:
        """
        Check if user is required to have 2FA (e.g., admin users).

        Args:
            user_id: User's UUID

        Returns:
            True if 2FA is required for this user, False otherwise
        """
        logger.debug("requires_2fa called", user_id=user_id)
        client = self._get_client()

        result = client.table("auth_users").select("requires_2fa").eq("id", user_id).execute()

        if not result.data:
            return False

        return cast("bool", result.data[0].get("requires_2fa", False))

    def _log_2fa_attempt(
        self,
        user_id: str,
        success: bool,
        code_type: str,
        ip_address: str | None = None,
    ) -> None:
        """
        Log 2FA verification attempt.

        Args:
            user_id: User's UUID
            success: Whether verification succeeded
            code_type: Type of code ('totp' or 'backup')
            ip_address: IP address of attempt
        """
        client = self._get_client()

        data = {
            "user_id": user_id,
            "success": success,
            "code_type": code_type,
            "ip_address": ip_address,
        }

        client.table("auth_2fa_attempts").insert(data).execute()

    def _count_recent_failures(self, user_id: str) -> int:
        """
        Count failed 2FA attempts in last hour.

        Args:
            user_id: User's UUID

        Returns:
            Number of failed attempts in last hour
        """
        client = self._get_client()

        result = client.rpc("count_recent_2fa_failures", {"p_user_id": user_id}).execute()

        return result.data if result.data else 0


class BackupCodeManager:
    """Manages backup codes for 2FA recovery."""

    CODE_LENGTH = 8
    CODE_COUNT = 10

    def __init__(self) -> None:
        """Initialize Backup Code Manager."""
        self.client: Client | None = None

    def _get_client(self) -> Client:
        """Get Supabase client (cached)."""
        if not self.client:
            self.client = get_supabase_client()
        return self.client

    def generate_codes(self, count: int = CODE_COUNT) -> list[str]:
        """
        Generate random backup codes.

        Args:
            count: Number of codes to generate (default: 10)

        Returns:
            List of backup codes (e.g., ['A1B2C3D4', ...])
        """
        logger.info("generate_codes called", count=count)
        codes = []
        alphabet = string.ascii_uppercase + string.digits

        for _ in range(count):
            code = "".join(secrets.choice(alphabet) for _ in range(self.CODE_LENGTH))
            # Format as XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)

        return codes

    def hash_code(self, code: str) -> str:
        """
        Hash backup code with bcrypt.

        Args:
            code: Backup code (with or without dash)

        Returns:
            Bcrypt hash
        """
        logger.debug("hash_code called", has_code=bool(code))
        # Remove dash for hashing
        code_normalized = code.replace("-", "").upper()
        return bcrypt.hashpw(code_normalized.encode(), bcrypt.gensalt()).decode()

    def verify_code(self, code: str, code_hash: str) -> bool:
        """
        Verify backup code against hash.

        Args:
            code: Backup code entered by user
            code_hash: Stored bcrypt hash

        Returns:
            True if code matches hash, False otherwise
        """
        logger.debug("verify_code called", has_code=bool(code), has_hash=bool(code_hash))
        # Remove dash and normalize
        code_normalized = code.replace("-", "").upper()
        return bcrypt.checkpw(code_normalized.encode(), code_hash.encode())

    def create_backup_codes(
        self, user_id: str, count: int = CODE_COUNT, expires_days: int = 90
    ) -> list[str]:
        """
        Generate and store new backup codes for user.

        Replaces any existing backup codes.

        Args:
            user_id: User's UUID
            count: Number of codes to generate
            expires_days: Days until codes expire (default: 90)

        Returns:
            List of backup codes (plaintext, for user to save)
        """
        logger.info(
            "create_backup_codes called", user_id=user_id, count=count, expires_days=expires_days
        )
        client = self._get_client()

        # Generate codes
        codes = self.generate_codes(count)

        # Delete existing backup codes
        client.table("auth_backup_codes").delete().eq("user_id", user_id).execute()

        # Store hashed codes
        expires_at = datetime.now(UTC) + timedelta(days=expires_days)

        for code in codes:
            code_hash = self.hash_code(code)
            data = {
                "user_id": user_id,
                "code_hash": code_hash,
                "expires_at": expires_at.isoformat(),
            }
            client.table("auth_backup_codes").insert(data).execute()

        # Update backup codes metadata in totp_secrets
        client.table("auth_totp_secrets").update(
            {
                "backup_codes_generated_at": datetime.now(UTC).isoformat(),
                "backup_codes_count": count,
            }
        ).eq("user_id", user_id).execute()

        return codes

    def verify_and_use_backup_code(
        self, user_id: str, code: str, ip_address: str | None = None
    ) -> bool:
        """
        Verify backup code and mark as used.

        Args:
            user_id: User's UUID
            code: Backup code entered by user
            ip_address: IP address of verification request

        Returns:
            True if code is valid and unused, False otherwise
        """
        logger.info(
            "verify_and_use_backup_code called",
            user_id=user_id,
            has_code=bool(code),
            ip_address=ip_address,
        )
        client = self._get_client()

        # Get all unused backup codes for user
        result = (
            client.table("auth_backup_codes")
            .select("id, code_hash")
            .eq("user_id", user_id)
            .eq("is_used", False)
            .execute()
        )

        if not result.data:
            # Log failed attempt
            self._log_backup_attempt(user_id, False, ip_address)
            return False

        # Check each code
        for backup_code in result.data:
            if self.verify_code(code, backup_code["code_hash"]):
                # Mark as used
                client.table("auth_backup_codes").update(
                    {
                        "is_used": True,
                        "used_at": datetime.now(UTC).isoformat(),
                        "used_ip": ip_address,
                    }
                ).eq("id", backup_code["id"]).execute()

                # Log successful attempt
                self._log_backup_attempt(user_id, True, ip_address)

                return True

        # No matching code found
        self._log_backup_attempt(user_id, False, ip_address)
        return False

    def get_unused_count(self, user_id: str) -> int:
        """
        Get count of unused backup codes for user.

        Args:
            user_id: User's UUID

        Returns:
            Number of unused, non-expired backup codes
        """
        logger.debug("get_unused_count called", user_id=user_id)
        client = self._get_client()

        result = client.rpc("get_unused_backup_codes_count", {"p_user_id": user_id}).execute()

        return result.data if result.data else 0

    def _log_backup_attempt(
        self, user_id: str, success: bool, ip_address: str | None = None
    ) -> None:
        """
        Log backup code verification attempt.

        Args:
            user_id: User's UUID
            success: Whether verification succeeded
            ip_address: IP address of attempt
        """
        client = self._get_client()

        data = {
            "user_id": user_id,
            "success": success,
            "code_type": "backup",
            "ip_address": ip_address,
        }

        client.table("auth_2fa_attempts").insert(data).execute()


# Singleton instances
_totp_manager: TOTPManager | None = None
_backup_code_manager: BackupCodeManager | None = None


def get_totp_manager(encryption_key: str | None = None) -> TOTPManager:
    """
    Get singleton TOTP Manager instance.

    Args:
        encryption_key: Fernet encryption key (required for production)

    Returns:
        TOTPManager instance
    """
    logger.debug("get_totp_manager called", has_encryption_key=bool(encryption_key))
    global _totp_manager

    if _totp_manager is None:
        # Use OAUTH_ENCRYPTION_KEY from settings (same key used for OAuth tokens)
        key = encryption_key or getattr(settings, "oauth_encryption_key", None)
        _totp_manager = TOTPManager(encryption_key=key)

    return _totp_manager


def get_backup_code_manager() -> BackupCodeManager:
    """
    Get singleton Backup Code Manager instance.

    Returns:
        BackupCodeManager instance
    """
    logger.debug("get_backup_code_manager called")
    global _backup_code_manager

    if _backup_code_manager is None:
        _backup_code_manager = BackupCodeManager()

    return _backup_code_manager
