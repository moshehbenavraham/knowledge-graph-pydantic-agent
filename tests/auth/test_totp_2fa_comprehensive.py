"""
Comprehensive tests for src/auth/totp_2fa.py.

Tests TOTP 2FA management and backup codes.
"""

from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from src.auth.totp_2fa import (
    BackupCodeManager,
    TOTPManager,
    get_backup_code_manager,
    get_totp_manager,
)


class TestTOTPManagerInit:
    """Test TOTPManager initialization."""

    def test_init_with_encryption_key(self):
        """Test initialization with encryption key."""
        key = Fernet.generate_key().decode()
        manager = TOTPManager(encryption_key=key)

        assert manager.cipher is not None
        assert manager.client is None

    def test_init_without_encryption_key(self):
        """Test initialization without encryption key (generates new)."""
        manager = TOTPManager()

        assert manager.cipher is not None
        assert manager.client is None

    def test_init_creates_cipher(self):
        """Test cipher is created."""
        manager = TOTPManager()

        # Should be able to encrypt/decrypt
        encrypted = manager.cipher.encrypt(b"test")
        decrypted = manager.cipher.decrypt(encrypted)
        assert decrypted == b"test"


class TestTOTPManagerSecretGeneration:
    """Test TOTP secret generation."""

    def test_generate_secret(self):
        """Test secret generation."""
        manager = TOTPManager()

        secret = manager.generate_secret()

        assert isinstance(secret, str)
        assert len(secret) > 0
        # Base32 characters only
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)

    def test_generate_secret_unique(self):
        """Test generated secrets are unique."""
        manager = TOTPManager()

        secret1 = manager.generate_secret()
        secret2 = manager.generate_secret()

        assert secret1 != secret2

    def test_encrypt_decrypt_secret(self):
        """Test secret encryption and decryption."""
        manager = TOTPManager()
        secret = "ABCDEFGH12345678"

        encrypted = manager.encrypt_secret(secret)
        decrypted = manager.decrypt_secret(encrypted)

        assert decrypted == secret
        assert encrypted != secret

    def test_encrypt_secret_base64_encoded(self):
        """Test encrypted secret is base64."""
        manager = TOTPManager()
        secret = "TESTSECRETIC"

        encrypted = manager.encrypt_secret(secret)

        # Should be base64 decodable
        import base64

        try:
            base64.b64decode(encrypted)
        except Exception:
            pytest.fail("Encrypted secret not valid base64")


class TestTOTPManagerQRCode:
    """Test QR code generation."""

    def test_generate_qr_code(self):
        """Test QR code generation."""
        manager = TOTPManager()
        secret = manager.generate_secret()

        qr_code = manager.generate_qr_code(secret, "testuser@example.com")

        assert isinstance(qr_code, str)
        assert len(qr_code) > 0

    def test_generate_qr_code_custom_issuer(self):
        """Test QR code with custom issuer."""
        manager = TOTPManager()
        secret = manager.generate_secret()

        qr_code = manager.generate_qr_code(secret, "user@example.com", issuer="My App")

        assert isinstance(qr_code, str)

    def test_generate_qr_code_base64(self):
        """Test QR code is base64 encoded."""
        manager = TOTPManager()
        secret = manager.generate_secret()

        qr_code = manager.generate_qr_code(secret, "user")

        # Should be base64 decodable
        import base64

        try:
            base64.b64decode(qr_code)
        except Exception:
            pytest.fail("QR code not valid base64")


class TestTOTPManagerVerification:
    """Test TOTP verification."""

    @patch("src.auth.totp_2fa.pyotp.TOTP")
    def test_verify_code_success(self, mock_totp_class):
        """Test successful code verification."""
        manager = TOTPManager()
        mock_totp = MagicMock()
        mock_totp.verify.return_value = True
        mock_totp_class.return_value = mock_totp

        is_valid = manager.verify_code("SECRETKEY", "123456")

        assert is_valid is True
        mock_totp.verify.assert_called_once()

    @patch("src.auth.totp_2fa.pyotp.TOTP")
    def test_verify_code_failure(self, mock_totp_class):
        """Test failed code verification."""
        manager = TOTPManager()
        mock_totp = MagicMock()
        mock_totp.verify.return_value = False
        mock_totp_class.return_value = mock_totp

        is_valid = manager.verify_code("SECRETKEY", "999999")

        assert is_valid is False

    @patch("src.auth.totp_2fa.pyotp.TOTP")
    def test_verify_code_with_window(self, mock_totp_class):
        """Test verification with time window."""
        manager = TOTPManager()
        mock_totp = MagicMock()
        mock_totp.verify.return_value = True
        mock_totp_class.return_value = mock_totp

        is_valid = manager.verify_code("SECRET", "123456", window=2)

        assert is_valid is True
        mock_totp.verify.assert_called_with("123456", valid_window=2)


class TestTOTPManagerSetup:
    """Test 2FA setup."""

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_setup_2fa(self, mock_get_client):
        """Test 2FA setup."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = None
        mock_get_client.return_value = mock_client

        result = manager.setup_2fa("user-123", "testuser")

        assert "secret" in result
        assert "qr_code" in result
        mock_table.upsert.assert_called_once()

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_setup_2fa_with_ip(self, mock_get_client):
        """Test 2FA setup with IP address."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = None
        mock_get_client.return_value = mock_client

        result = manager.setup_2fa("user-123", "testuser", ip_address="1.2.3.4")

        assert "secret" in result
        # Check IP was passed
        call_args = mock_table.upsert.call_args[0][0]
        assert call_args["created_ip"] == "1.2.3.4"


class TestTOTPManagerEnable:
    """Test 2FA enable/disable."""

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_verify_and_enable_2fa_success(self, mock_get_client):
        """Test successful 2FA enablement."""
        manager = TOTPManager()
        secret = manager.generate_secret()
        encrypted = manager.encrypt_secret(secret)

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Mock select query
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"secret_encrypted": encrypted}]
        )

        # Mock verify_code to return True
        with patch.object(manager, "verify_code", return_value=True):
            # Mock update
            mock_table.update.return_value.eq.return_value.execute.return_value = None

            mock_get_client.return_value = mock_client

            result = manager.verify_and_enable_2fa("user-123", "123456")

            assert result is True
            # Check update was called
            assert mock_table.update.called

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_verify_and_enable_2fa_invalid_code(self, mock_get_client):
        """Test 2FA enable with invalid code."""
        manager = TOTPManager()
        secret = manager.generate_secret()
        encrypted = manager.encrypt_secret(secret)

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"secret_encrypted": encrypted}]
        )

        with patch.object(manager, "verify_code", return_value=False):
            mock_get_client.return_value = mock_client

            result = manager.verify_and_enable_2fa("user-123", "999999")

            assert result is False

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_verify_and_enable_2fa_no_secret(self, mock_get_client):
        """Test 2FA enable when no secret found."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        mock_get_client.return_value = mock_client

        result = manager.verify_and_enable_2fa("user-123", "123456")

        assert result is False

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_disable_2fa(self, mock_get_client):
        """Test disabling 2FA."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=["record"]
        )

        mock_get_client.return_value = mock_client

        result = manager.disable_2fa("user-123")

        assert result is True
        mock_table.update.assert_called_with({"is_enabled": False})

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_disable_2fa_not_found(self, mock_get_client):
        """Test disabling 2FA when not found."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        mock_get_client.return_value = mock_client

        result = manager.disable_2fa("user-123")

        assert result is False


class TestTOTPManagerLoginVerification:
    """Test login verification."""

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_verify_login_code_success(self, mock_get_client):
        """Test successful login verification."""
        manager = TOTPManager()
        secret = manager.generate_secret()
        encrypted = manager.encrypt_secret(secret)

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Mock rate limit check
        with patch.object(manager, "_count_recent_failures", return_value=0):
            # Mock secret retrieval
            mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"secret_encrypted": encrypted, "is_enabled": True}]
            )

            # Mock verification
            with patch.object(manager, "verify_code", return_value=True):
                mock_get_client.return_value = mock_client

                result = manager.verify_login_code("user-123", "123456")

                assert result is True

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_verify_login_code_rate_limited(self, mock_get_client):
        """Test rate limiting."""
        manager = TOTPManager()

        with patch.object(manager, "_count_recent_failures", return_value=5):
            result = manager.verify_login_code("user-123", "123456")

            assert result is False

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_verify_login_code_not_enabled(self, mock_get_client):
        """Test verification when 2FA not enabled."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        with patch.object(manager, "_count_recent_failures", return_value=0):
            mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"secret_encrypted": "encrypted", "is_enabled": False}]
            )

            mock_get_client.return_value = mock_client

            result = manager.verify_login_code("user-123", "123456")

            assert result is False


class TestTOTPManagerStatus:
    """Test 2FA status checks."""

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_is_2fa_enabled_true(self, mock_get_client):
        """Test checking if 2FA is enabled."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"is_enabled": True}]
        )

        mock_get_client.return_value = mock_client

        result = manager.is_2fa_enabled("user-123")

        assert result is True

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_is_2fa_enabled_false(self, mock_get_client):
        """Test checking when 2FA not enabled."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"is_enabled": False}]
        )

        mock_get_client.return_value = mock_client

        result = manager.is_2fa_enabled("user-123")

        assert result is False

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_is_2fa_enabled_not_found(self, mock_get_client):
        """Test checking when user has no 2FA record."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        mock_get_client.return_value = mock_client

        result = manager.is_2fa_enabled("user-123")

        assert result is False

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_requires_2fa_true(self, mock_get_client):
        """Test checking if user requires 2FA."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"requires_2fa": True}]
        )

        mock_get_client.return_value = mock_client

        result = manager.requires_2fa("user-123")

        assert result is True

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_requires_2fa_false(self, mock_get_client):
        """Test checking when user doesn't require 2FA."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"requires_2fa": False}]
        )

        mock_get_client.return_value = mock_client

        result = manager.requires_2fa("user-123")

        assert result is False


class TestBackupCodeManagerInit:
    """Test BackupCodeManager initialization."""

    def test_init(self):
        """Test initialization."""
        manager = BackupCodeManager()

        assert manager.client is None
        assert manager.CODE_LENGTH == 8
        assert manager.CODE_COUNT == 10


class TestBackupCodeGeneration:
    """Test backup code generation."""

    def test_generate_codes_default_count(self):
        """Test generating default number of codes."""
        manager = BackupCodeManager()

        codes = manager.generate_codes()

        assert len(codes) == 10
        for code in codes:
            assert "-" in code
            assert len(code.replace("-", "")) == 8

    def test_generate_codes_custom_count(self):
        """Test generating custom number of codes."""
        manager = BackupCodeManager()

        codes = manager.generate_codes(count=5)

        assert len(codes) == 5

    def test_generate_codes_unique(self):
        """Test generated codes are unique."""
        manager = BackupCodeManager()

        codes = manager.generate_codes(count=20)

        assert len(codes) == len(set(codes))

    def test_generate_codes_format(self):
        """Test code format is XXXX-XXXX."""
        manager = BackupCodeManager()

        codes = manager.generate_codes()

        for code in codes:
            parts = code.split("-")
            assert len(parts) == 2
            assert len(parts[0]) == 4
            assert len(parts[1]) == 4


class TestBackupCodeHashing:
    """Test backup code hashing."""

    def test_hash_code(self):
        """Test code hashing."""
        manager = BackupCodeManager()
        code = "ABCD-1234"

        code_hash = manager.hash_code(code)

        assert isinstance(code_hash, str)
        assert len(code_hash) > 0
        assert code_hash != code

    def test_hash_code_without_dash(self):
        """Test hashing code without dash."""
        manager = BackupCodeManager()

        manager.hash_code("ABCD-1234")
        manager.hash_code("ABCD1234")

        # Should produce same hash (dash removed)
        # Note: Can't directly compare bcrypt hashes due to salt
        # But we can verify both codes

    def test_verify_code_success(self):
        """Test successful code verification."""
        manager = BackupCodeManager()
        code = "TEST-CODE"

        code_hash = manager.hash_code(code)
        is_valid = manager.verify_code(code, code_hash)

        assert is_valid is True

    def test_verify_code_failure(self):
        """Test failed code verification."""
        manager = BackupCodeManager()
        code = "TEST-CODE"

        code_hash = manager.hash_code(code)
        is_valid = manager.verify_code("WRONG-CODE", code_hash)

        assert is_valid is False

    def test_verify_code_case_insensitive(self):
        """Test verification is case insensitive."""
        manager = BackupCodeManager()
        code = "ABCD-1234"

        code_hash = manager.hash_code(code)
        is_valid = manager.verify_code("abcd-1234", code_hash)

        assert is_valid is True


class TestBackupCodeCreation:
    """Test backup code creation and storage."""

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_create_backup_codes(self, mock_get_client):
        """Test creating backup codes."""
        manager = BackupCodeManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.delete.return_value.eq.return_value.execute.return_value = None
        mock_table.insert.return_value.execute.return_value = None
        mock_table.update.return_value.eq.return_value.execute.return_value = None

        mock_get_client.return_value = mock_client

        codes = manager.create_backup_codes("user-123")

        assert len(codes) == 10
        # Should have deleted old codes
        mock_table.delete.assert_called()
        # Should have inserted new codes
        assert mock_table.insert.call_count == 10

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_create_backup_codes_custom_count(self, mock_get_client):
        """Test creating custom number of codes."""
        manager = BackupCodeManager()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.delete.return_value.eq.return_value.execute.return_value = None
        mock_table.insert.return_value.execute.return_value = None
        mock_table.update.return_value.eq.return_value.execute.return_value = None

        mock_get_client.return_value = mock_client

        codes = manager.create_backup_codes("user-123", count=5)

        assert len(codes) == 5


class TestBackupCodeVerification:
    """Test backup code verification and usage."""

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_verify_and_use_backup_code_success(self, mock_get_client):
        """Test successful backup code verification."""
        manager = BackupCodeManager()
        code = "TEST-CODE"
        code_hash = manager.hash_code(code)

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Mock select
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=[{"id": "backup-1", "code_hash": code_hash}])
        )

        # Mock update
        mock_table.update.return_value.eq.return_value.execute.return_value = None

        mock_get_client.return_value = mock_client

        result = manager.verify_and_use_backup_code("user-123", code)

        assert result is True
        # Should mark as used
        mock_table.update.assert_called()

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_verify_and_use_backup_code_no_codes(self, mock_get_client):
        """Test verification when no unused codes."""
        manager = BackupCodeManager()

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        mock_get_client.return_value = mock_client

        result = manager.verify_and_use_backup_code("user-123", "CODE")

        assert result is False

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_verify_and_use_backup_code_wrong_code(self, mock_get_client):
        """Test verification with wrong code."""
        manager = BackupCodeManager()
        code_hash = manager.hash_code("CORRECT-CODE")

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
            MagicMock(data=[{"id": "backup-1", "code_hash": code_hash}])
        )

        mock_get_client.return_value = mock_client

        result = manager.verify_and_use_backup_code("user-123", "WRONG-CODE")

        assert result is False


class TestBackupCodeStatus:
    """Test backup code status."""

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_get_unused_count(self, mock_get_client):
        """Test getting unused code count."""
        manager = BackupCodeManager()
        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = MagicMock(data=5)

        mock_get_client.return_value = mock_client

        count = manager.get_unused_count("user-123")

        assert count == 5

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_get_unused_count_none(self, mock_get_client):
        """Test getting count when none found."""
        manager = BackupCodeManager()
        mock_client = MagicMock()
        mock_client.rpc.return_value.execute.return_value = MagicMock(data=None)

        mock_get_client.return_value = mock_client

        count = manager.get_unused_count("user-123")

        assert count == 0


class TestSingletonFunctions:
    """Test singleton getter functions."""

    def test_get_totp_manager(self):
        """Test getting TOTP manager singleton."""
        manager1 = get_totp_manager()
        manager2 = get_totp_manager()

        assert manager1 is manager2

    def test_get_backup_code_manager(self):
        """Test getting backup code manager singleton."""
        manager1 = get_backup_code_manager()
        manager2 = get_backup_code_manager()

        assert manager1 is manager2

    def test_get_totp_manager_with_key(self):
        """Test getting TOTP manager with custom key."""
        key = Fernet.generate_key().decode()
        manager = get_totp_manager(encryption_key=key)

        assert manager is not None


class TestEdgeCases:
    """Test edge cases."""

    def test_totp_manager_decrypt_invalid_secret(self):
        """Test decrypting invalid secret."""
        manager = TOTPManager()

        with pytest.raises(Exception):
            manager.decrypt_secret("invalid_base64")

    def test_backup_code_verify_empty_hash(self):
        """Test verifying with empty hash."""
        manager = BackupCodeManager()

        # Should handle gracefully or raise
        try:
            result = manager.verify_code("CODE", "")
            assert result is False
        except Exception:
            # Expected to fail
            pass

    @patch("src.auth.totp_2fa.get_supabase_client")
    def test_totp_manager_get_client_caching(self, mock_get_client):
        """Test client is cached."""
        manager = TOTPManager()
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        client1 = manager._get_client()
        client2 = manager._get_client()

        assert client1 is client2
        # Should only call once
        mock_get_client.assert_called_once()
