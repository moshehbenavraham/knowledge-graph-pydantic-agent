"""
Comprehensive tests for src/auth/email_verification.py.

Tests email verification flow for user registration.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.auth.email_verification import (
    check_user_email_verified,
    create_verification_token,
    request_email_verification,
    send_verification_email,
    send_verification_email_smtp,
    use_verification_token,
    verify_verification_token,
)


class TestCreateVerificationToken:
    """Test verification token creation."""

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    @patch("src.auth.email_verification.hash_password")
    async def test_create_token_success(self, mock_hash, mock_get_client):
        """Test successful token creation."""
        mock_hash.return_value = "hashed_token"
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "token-123"}])
        mock_get_client.return_value = mock_client

        token = await create_verification_token("user-123")

        assert isinstance(token, str)
        assert len(token) > 0
        mock_table.insert.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    @patch("src.auth.email_verification.hash_password")
    async def test_create_token_with_custom_expiry(self, mock_hash, mock_get_client):
        """Test token creation with custom expiry."""
        mock_hash.return_value = "hashed_token"
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "token-123"}])
        mock_get_client.return_value = mock_client

        token = await create_verification_token("user-123", expires_in_hours=48)

        assert isinstance(token, str)

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    @patch("src.auth.email_verification.hash_password")
    async def test_create_token_with_ip(self, mock_hash, mock_get_client):
        """Test token creation with IP address."""
        mock_hash.return_value = "hashed_token"
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "token-123"}])
        mock_get_client.return_value = mock_client

        token = await create_verification_token("user-123", created_ip="1.2.3.4")

        assert isinstance(token, str)
        # Check IP was passed
        call_args = mock_table.insert.call_args[0][0]
        assert call_args["created_ip"] == "1.2.3.4"

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    @patch("src.auth.email_verification.hash_password")
    async def test_create_token_no_data_returned(self, mock_hash, mock_get_client):
        """Test token creation when no data returned."""
        mock_hash.return_value = "hashed_token"
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = MagicMock(data=None)
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception, match="Failed to create verification token"):
            await create_verification_token("user-123")

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    async def test_create_token_database_error(self, mock_get_client):
        """Test token creation with database error."""
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("Database error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await create_verification_token("user-123")


class TestVerifyVerificationToken:
    """Test token verification."""

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    @patch("src.auth.email_verification.verify_password")
    async def test_verify_token_success(self, mock_verify_password, mock_get_client):
        """Test successful token verification."""
        mock_verify_password.return_value = True
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        mock_table.select.return_value.is_.return_value.gt.return_value.execute.return_value = (
            MagicMock(data=[{"id": "token-123", "token_hash": "hashed", "expires_at": future_time}])
        )

        mock_get_client.return_value = mock_client

        result = await verify_verification_token("test_token")

        assert result is not None
        assert result["id"] == "token-123"

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    async def test_verify_token_no_tokens_found(self, mock_get_client):
        """Test verification when no tokens found."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value.is_.return_value.gt.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        mock_get_client.return_value = mock_client

        result = await verify_verification_token("test_token")

        assert result is None

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    @patch("src.auth.email_verification.verify_password")
    async def test_verify_token_no_matching_hash(self, mock_verify_password, mock_get_client):
        """Test verification when hash doesn't match."""
        mock_verify_password.return_value = False
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        mock_table.select.return_value.is_.return_value.gt.return_value.execute.return_value = (
            MagicMock(
                data=[
                    {"id": "token-123", "token_hash": "different_hash", "expires_at": future_time}
                ]
            )
        )

        mock_get_client.return_value = mock_client

        result = await verify_verification_token("test_token")

        assert result is None

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    async def test_verify_token_database_error(self, mock_get_client):
        """Test verification with database error."""
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("Database error")
        mock_get_client.return_value = mock_client

        result = await verify_verification_token("test_token")

        assert result is None


class TestUseVerificationToken:
    """Test using verification token."""

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.verify_verification_token")
    @patch("src.auth.email_verification.get_supabase_client")
    async def test_use_token_success(self, mock_get_client, mock_verify):
        """Test successfully using token."""
        mock_verify.return_value = {"id": "token-123", "user_id": "user-456"}
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user-456"}]
        )

        mock_get_client.return_value = mock_client

        result = await use_verification_token("test_token")

        assert result is True

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.verify_verification_token")
    async def test_use_token_invalid_token(self, mock_verify):
        """Test using invalid token."""
        mock_verify.return_value = None

        with pytest.raises(Exception, match="Invalid or expired verification token"):
            await use_verification_token("invalid_token")

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.verify_verification_token")
    @patch("src.auth.email_verification.get_supabase_client")
    async def test_use_token_with_ip(self, mock_get_client, mock_verify):
        """Test using token with IP address."""
        mock_verify.return_value = {"id": "token-123", "user_id": "user-456"}
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user-456"}]
        )

        mock_get_client.return_value = mock_client

        result = await use_verification_token("test_token", verified_ip="1.2.3.4")

        assert result is True

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.verify_verification_token")
    @patch("src.auth.email_verification.get_supabase_client")
    async def test_use_token_user_update_fails(self, mock_get_client, mock_verify):
        """Test using token when user update fails."""
        mock_verify.return_value = {"id": "token-123", "user_id": "user-456"}
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

        mock_get_client.return_value = mock_client

        with pytest.raises(Exception, match="Failed to update user verification status"):
            await use_verification_token("test_token")


class TestSendVerificationEmailSMTP:
    """Test sending verification email via SMTP."""

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_settings")
    @patch("smtplib.SMTP")
    async def test_send_email_smtp_success(self, mock_smtp_class, mock_get_settings):
        """Test successful SMTP email send."""
        mock_settings = MagicMock()
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_from_email = "noreply@example.com"
        mock_settings.smtp_user = "user"
        mock_settings.smtp_password = "pass"
        mock_get_settings.return_value = mock_settings

        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=None)
        mock_smtp_class.return_value = mock_smtp

        result = await send_verification_email_smtp(
            "user@example.com", "TOKEN123", "https://example.com/verify", "Test User"
        )

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_settings")
    @patch("smtplib.SMTP")
    async def test_send_email_smtp_no_auth(self, mock_smtp_class, mock_get_settings):
        """Test SMTP email without authentication."""
        mock_settings = MagicMock()
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_from_email = "noreply@example.com"
        mock_settings.smtp_user = None
        mock_settings.smtp_password = None
        mock_get_settings.return_value = mock_settings

        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=None)
        mock_smtp_class.return_value = mock_smtp

        result = await send_verification_email_smtp(
            "user@example.com", "TOKEN123", "https://example.com/verify", "Test User"
        )

        assert result is True
        mock_smtp.starttls.assert_called_once()
        # Should not call login
        mock_smtp.login.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_settings")
    @patch("smtplib.SMTP")
    async def test_send_email_smtp_error(self, mock_smtp_class, mock_get_settings):
        """Test SMTP email with error."""
        mock_settings = MagicMock()
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_from_email = "noreply@example.com"
        mock_get_settings.return_value = mock_settings

        mock_smtp_class.side_effect = Exception("SMTP error")

        result = await send_verification_email_smtp(
            "user@example.com", "TOKEN", "https://example.com/verify", "User"
        )

        assert result is False


class TestSendVerificationEmail:
    """Test provider-agnostic email sending."""

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_settings")
    async def test_send_email_disabled(self, mock_get_settings):
        """Test when email is disabled."""
        mock_settings = MagicMock()
        mock_settings.email_enabled = False
        mock_get_settings.return_value = mock_settings

        result = await send_verification_email(
            "user@example.com", "TOKEN", "https://example.com/verify", "User"
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_settings")
    @patch("src.auth.email_verification.send_verification_email_smtp")
    async def test_send_email_smtp_provider(self, mock_send_smtp, mock_get_settings):
        """Test with SMTP provider."""
        mock_settings = MagicMock()
        mock_settings.email_enabled = True
        mock_settings.email_provider = "smtp"
        mock_get_settings.return_value = mock_settings

        mock_send_smtp.return_value = True

        result = await send_verification_email(
            "user@example.com", "TOKEN", "https://example.com/verify", "User"
        )

        assert result is True
        mock_send_smtp.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_settings")
    async def test_send_email_unsupported_provider(self, mock_get_settings):
        """Test with unsupported provider."""
        mock_settings = MagicMock()
        mock_settings.email_enabled = True
        mock_settings.email_provider = "unsupported"
        mock_get_settings.return_value = mock_settings

        result = await send_verification_email(
            "user@example.com", "TOKEN", "https://example.com/verify", "User"
        )

        assert result is False


class TestRequestEmailVerification:
    """Test requesting email verification."""

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    @patch("src.auth.email_verification.create_verification_token")
    @patch("src.auth.email_verification.send_verification_email")
    async def test_request_verification_success(self, mock_send, mock_create_token, mock_get_user):
        """Test successful verification request."""
        mock_get_user.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "full_name": "Test User",
            "is_email_verified": False,
        }
        mock_create_token.return_value = "TOKEN123"
        mock_send.return_value = True

        success, message = await request_email_verification(
            "user-123", "https://example.com/verify"
        )

        assert success is True
        assert "sent" in message.lower()

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    async def test_request_verification_user_not_found(self, mock_get_user):
        """Test request when user not found."""
        mock_get_user.return_value = None

        success, message = await request_email_verification(
            "user-123", "https://example.com/verify"
        )

        assert success is False
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    async def test_request_verification_already_verified(self, mock_get_user):
        """Test request when already verified."""
        mock_get_user.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "is_email_verified": True,
        }

        success, message = await request_email_verification(
            "user-123", "https://example.com/verify"
        )

        assert success is True
        assert "already verified" in message.lower()

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    @patch("src.auth.email_verification.create_verification_token")
    @patch("src.auth.email_verification.send_verification_email")
    async def test_request_verification_email_not_sent(
        self, mock_send, mock_create_token, mock_get_user
    ):
        """Test request when email not sent."""
        mock_get_user.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "full_name": "Test User",
            "is_email_verified": False,
        }
        mock_create_token.return_value = "TOKEN123"
        mock_send.return_value = False

        success, message = await request_email_verification(
            "user-123", "https://example.com/verify"
        )

        assert success is True
        assert "could not be sent" in message.lower()

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    async def test_request_verification_exception(self, mock_get_user):
        """Test request with exception."""
        mock_get_user.side_effect = Exception("Database error")

        success, message = await request_email_verification(
            "user-123", "https://example.com/verify"
        )

        assert success is False
        assert "error occurred" in message.lower()


class TestCheckUserEmailVerified:
    """Test checking if email is verified."""

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    async def test_check_verified_true(self, mock_get_user):
        """Test checking verified user."""
        mock_get_user.return_value = {"id": "user-123", "is_email_verified": True}

        result = await check_user_email_verified("user-123")

        assert result is True

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    async def test_check_verified_false(self, mock_get_user):
        """Test checking unverified user."""
        mock_get_user.return_value = {"id": "user-123", "is_email_verified": False}

        result = await check_user_email_verified("user-123")

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    async def test_check_verified_user_not_found(self, mock_get_user):
        """Test checking when user not found."""
        mock_get_user.return_value = None

        result = await check_user_email_verified("user-123")

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    async def test_check_verified_exception(self, mock_get_user):
        """Test checking with exception."""
        mock_get_user.side_effect = Exception("Database error")

        result = await check_user_email_verified("user-123")

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    async def test_check_verified_missing_field(self, mock_get_user):
        """Test checking when field missing."""
        mock_get_user.return_value = {"id": "user-123"}  # Missing is_email_verified

        result = await check_user_email_verified("user-123")

        assert result is False


class TestIntegrationScenarios:
    """Test integrated verification scenarios."""

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_user_by_id")
    @patch("src.auth.email_verification.create_verification_token")
    @patch("src.auth.email_verification.send_verification_email")
    @patch("src.auth.email_verification.verify_verification_token")
    @patch("src.auth.email_verification.get_supabase_client")
    async def test_full_verification_flow(
        self, mock_get_client, mock_verify_token, mock_send, mock_create_token, mock_get_user
    ):
        """Test complete verification flow."""
        # Step 1: Request verification
        mock_get_user.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "full_name": "Test User",
            "is_email_verified": False,
        }
        mock_create_token.return_value = "TOKEN123"
        mock_send.return_value = True

        success1, _message1 = await request_email_verification(
            "user-123", "https://example.com/verify"
        )
        assert success1 is True

        # Step 2: Verify token
        mock_verify_token.return_value = {"id": "token-123", "user_id": "user-123"}
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user-123"}]
        )
        mock_get_client.return_value = mock_client

        success2 = await use_verification_token("TOKEN123")
        assert success2 is True


class TestEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    @patch("src.auth.email_verification.get_supabase_client")
    @patch("src.auth.email_verification.hash_password")
    async def test_create_token_with_zero_expiry(self, mock_hash, mock_get_client):
        """Test creating token with zero expiry."""
        mock_hash.return_value = "hashed"
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "token-123"}])
        mock_get_client.return_value = mock_client

        token = await create_verification_token("user-123", expires_in_hours=0)

        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_verify_empty_token(self):
        """Test verifying empty token."""
        # Should handle gracefully (will query database and find nothing)
        with patch("src.auth.email_verification.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            mock_table.select.return_value.is_.return_value.gt.return_value.execute.return_value = (
                MagicMock(data=[])
            )
            mock_get_client.return_value = mock_client

            result = await verify_verification_token("")

            assert result is None
