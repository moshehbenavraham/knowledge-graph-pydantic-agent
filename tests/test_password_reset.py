"""
Comprehensive tests for password reset flow.

Tests all password reset functionality:
- Token generation and validation
- Email sending (mocked SMTP)
- Password strength validation
- Complete reset flow
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.auth import password_reset

# =====================================================
# FIXTURES
# =====================================================


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return {
        "id": str(uuid4()),
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
    }


@pytest.fixture
def sample_reset_token():
    """Sample reset token."""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "token": "reset_token_abc123xyz",
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        "used_at": None,
    }


@pytest.fixture
def mock_smtp_server():
    """Mock SMTP server."""
    mock_server = MagicMock()
    mock_server.starttls = MagicMock()
    mock_server.login = MagicMock()
    mock_server.send_message = MagicMock()

    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_smtp.return_value.__exit__ = MagicMock()
        yield mock_server


# =====================================================
# EMAIL SENDING TESTS
# =====================================================


@pytest.mark.asyncio
async def test_send_reset_email_smtp_success(mock_smtp_server):
    """Test successful SMTP email sending."""
    # Patch module-level variables instead of os.environ (they're loaded at import time)
    with patch("src.auth.password_reset.SMTP_HOST", "smtp.gmail.com"):
        with patch("src.auth.password_reset.SMTP_PORT", 587):
            with patch("src.auth.password_reset.SMTP_USER", "test@gmail.com"):
                with patch("src.auth.password_reset.SMTP_PASSWORD", "testpass"):
                    with patch("src.auth.password_reset.SMTP_FROM_EMAIL", "noreply@test.com"):
                        result = await password_reset.send_reset_email_smtp(
                            email="recipient@example.com",
                            reset_token="token123",
                            reset_url="http://localhost:8501/reset",
                        )

                        assert result is True
                        mock_smtp_server.starttls.assert_called_once()
                        mock_smtp_server.login.assert_called_once_with("test@gmail.com", "testpass")
                        mock_smtp_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_reset_email_smtp_no_auth(mock_smtp_server):
    """Test SMTP email sending without authentication."""
    with patch.dict(
        "os.environ",
        {"SMTP_HOST": "localhost", "SMTP_PORT": "25", "SMTP_USER": "", "SMTP_PASSWORD": ""},
    ):
        result = await password_reset.send_reset_email_smtp(
            email="recipient@example.com",
            reset_token="token123",
            reset_url="http://localhost:8501/reset",
        )

        assert result is True
        mock_smtp_server.starttls.assert_called_once()
        mock_smtp_server.login.assert_not_called()  # No auth when credentials empty


@pytest.mark.asyncio
async def test_send_reset_email_smtp_connection_error():
    """Test SMTP email sending with connection error."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = ConnectionRefusedError("Connection refused")

        result = await password_reset.send_reset_email_smtp(
            email="recipient@example.com",
            reset_token="token123",
            reset_url="http://localhost:8501/reset",
        )

        assert result is False


@pytest.mark.asyncio
async def test_send_reset_email_smtp_authentication_error():
    """Test SMTP email sending with authentication error."""
    mock_server = MagicMock()
    mock_server.starttls = MagicMock()
    mock_server.login.side_effect = Exception("Authentication failed")

    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__.return_value = mock_server
        # __exit__ should return None/False to allow exceptions to propagate
        mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

        # Patch module-level variables instead of os.environ
        with patch("src.auth.password_reset.SMTP_HOST", "smtp.gmail.com"):
            with patch("src.auth.password_reset.SMTP_PORT", 587):
                with patch("src.auth.password_reset.SMTP_USER", "test@gmail.com"):
                    with patch("src.auth.password_reset.SMTP_PASSWORD", "wrongpass"):
                        with patch("src.auth.password_reset.SMTP_FROM_EMAIL", "noreply@test.com"):
                            result = await password_reset.send_reset_email_smtp(
                                email="recipient@example.com",
                                reset_token="token123",
                                reset_url="http://localhost:8501/reset",
                            )

                            assert result is False


@pytest.mark.asyncio
async def test_send_reset_email_disabled():
    """Test email sending when disabled."""
    with patch.dict("os.environ", {"EMAIL_ENABLED": "false"}):
        result = await password_reset.send_reset_email(
            email="test@example.com", reset_token="token123", reset_url="http://localhost:8501"
        )

        assert result is False


@pytest.mark.asyncio
async def test_send_reset_email_smtp_provider(mock_smtp_server):
    """Test email sending with SMTP provider."""
    with patch("src.auth.password_reset.EMAIL_ENABLED", True):
        with patch("src.auth.password_reset.EMAIL_PROVIDER", "smtp"):
            with patch.dict(
                "os.environ",
                {
                    "SMTP_HOST": "smtp.gmail.com",
                    "SMTP_PORT": "587",
                    "SMTP_USER": "test@gmail.com",
                    "SMTP_PASSWORD": "testpass",
                    "SMTP_FROM_EMAIL": "noreply@test.com",
                },
            ):
                result = await password_reset.send_reset_email(
                    email="test@example.com",
                    reset_token="token123",
                    reset_url="http://localhost:8501",
                )

                assert result is True


@pytest.mark.asyncio
async def test_send_reset_email_unsupported_provider():
    """Test email sending with unsupported provider."""
    with patch.dict("os.environ", {"EMAIL_ENABLED": "true", "EMAIL_PROVIDER": "unsupported"}):
        result = await password_reset.send_reset_email(
            email="test@example.com", reset_token="token123", reset_url="http://localhost:8501"
        )

        assert result is False


# =====================================================
# PASSWORD RESET REQUEST TESTS
# =====================================================


@pytest.mark.asyncio
async def test_request_password_reset_by_username(sample_user, mock_smtp_server):
    """Test password reset request by username."""
    with patch("src.auth.password_reset.get_user_by_username", return_value=sample_user):
        with patch("src.auth.password_reset.create_reset_token", return_value="token123"):
            with patch.dict("os.environ", {"EMAIL_ENABLED": "true", "EMAIL_PROVIDER": "smtp"}):
                success, message = await password_reset.request_password_reset(
                    username_or_email="testuser",
                    reset_url="http://localhost:8501",
                    client_ip="127.0.0.1",
                )

                assert success is True
                assert "password reset link has been sent" in message.lower()


@pytest.mark.asyncio
async def test_request_password_reset_by_email(sample_user, mock_smtp_server):
    """Test password reset request by email."""
    with patch("src.auth.password_reset.get_user_by_username", return_value=None):
        with patch("src.auth.password_reset.get_user_by_email", return_value=sample_user):
            with patch("src.auth.password_reset.create_reset_token", return_value="token123"):
                with patch.dict("os.environ", {"EMAIL_ENABLED": "true", "EMAIL_PROVIDER": "smtp"}):
                    success, message = await password_reset.request_password_reset(
                        username_or_email="test@example.com",
                        reset_url="http://localhost:8501",
                    )

                    assert success is True
                    assert "password reset link has been sent" in message.lower()


@pytest.mark.asyncio
async def test_request_password_reset_nonexistent_user():
    """Test password reset for non-existent user (security: don't reveal)."""
    with patch("src.auth.password_reset.get_user_by_username", return_value=None):
        with patch("src.auth.password_reset.get_user_by_email", return_value=None):
            success, message = await password_reset.request_password_reset(
                username_or_email="nonexistent",
                reset_url="http://localhost:8501",
            )

            # Should still return success to not reveal if user exists
            assert success is True
            assert "password reset link has been sent" in message.lower()


@pytest.mark.asyncio
async def test_request_password_reset_inactive_user(sample_user):
    """Test password reset for inactive user."""
    inactive_user = sample_user.copy()
    inactive_user["is_active"] = False

    with patch("src.auth.password_reset.get_user_by_username", return_value=inactive_user):
        success, message = await password_reset.request_password_reset(
            username_or_email="testuser",
            reset_url="http://localhost:8501",
        )

        # Should still return success to not reveal user status
        assert success is True
        assert "password reset link has been sent" in message.lower()


@pytest.mark.asyncio
async def test_request_password_reset_email_disabled(sample_user):
    """Test password reset when email is disabled."""
    with patch("src.auth.password_reset.get_user_by_username", return_value=sample_user):
        with patch("src.auth.password_reset.create_reset_token", return_value="token123"):
            with patch.dict("os.environ", {"EMAIL_ENABLED": "false"}):
                success, message = await password_reset.request_password_reset(
                    username_or_email="testuser",
                    reset_url="http://localhost:8501",
                )

                assert success is True
                assert "password reset link has been sent" in message.lower()


@pytest.mark.asyncio
async def test_request_password_reset_exception():
    """Test password reset with exception."""
    with patch(
        "src.auth.password_reset.get_user_by_username",
        side_effect=Exception("Database error"),
    ):
        success, message = await password_reset.request_password_reset(
            username_or_email="testuser",
            reset_url="http://localhost:8501",
        )

        assert success is False
        assert "error occurred" in message.lower()


# =====================================================
# TOKEN VALIDATION TESTS
# =====================================================


@pytest.mark.asyncio
async def test_validate_reset_token_valid(sample_reset_token):
    """Test validation of valid reset token."""
    with patch("src.auth.password_reset.verify_reset_token", return_value=sample_reset_token):
        is_valid, message, token_record = await password_reset.validate_reset_token("token123")

        assert is_valid is True
        assert "valid" in message.lower()
        assert token_record == sample_reset_token


@pytest.mark.asyncio
async def test_validate_reset_token_invalid():
    """Test validation of invalid reset token."""
    with patch("src.auth.password_reset.verify_reset_token", return_value=None):
        is_valid, message, token_record = await password_reset.validate_reset_token("invalid_token")

        assert is_valid is False
        assert "invalid" in message.lower() and "expired" in message.lower()
        assert token_record is None


@pytest.mark.asyncio
async def test_validate_reset_token_exception():
    """Test token validation with exception."""
    with patch(
        "src.auth.password_reset.verify_reset_token",
        side_effect=Exception("Database error"),
    ):
        is_valid, message, token_record = await password_reset.validate_reset_token("token123")

        assert is_valid is False
        assert "error occurred" in message.lower()
        assert token_record is None


# =====================================================
# PASSWORD RESET COMPLETION TESTS
# =====================================================


@pytest.mark.asyncio
async def test_reset_password_with_token_success():
    """Test successful password reset with token."""
    with patch("src.auth.password_reset.use_reset_token", return_value=True):
        success, message = await password_reset.reset_password_with_token(
            token="valid_token", new_password="NewPassword123!", client_ip="127.0.0.1"
        )

        assert success is True
        assert "successful" in message.lower()


@pytest.mark.asyncio
async def test_reset_password_with_token_failure():
    """Test password reset with invalid token."""
    with patch("src.auth.password_reset.use_reset_token", return_value=False):
        success, message = await password_reset.reset_password_with_token(
            token="invalid_token", new_password="NewPassword123!"
        )

        assert success is False
        assert "failed" in message.lower()


@pytest.mark.asyncio
async def test_reset_password_with_token_expired():
    """Test password reset with expired token."""
    with patch(
        "src.auth.password_reset.use_reset_token",
        side_effect=Exception("Invalid or expired token"),
    ):
        success, message = await password_reset.reset_password_with_token(
            token="expired_token", new_password="NewPassword123!"
        )

        assert success is False
        assert "invalid" in message.lower() and "expired" in message.lower()


@pytest.mark.asyncio
async def test_reset_password_with_token_exception():
    """Test password reset with unexpected exception."""
    with patch(
        "src.auth.password_reset.use_reset_token",
        side_effect=Exception("Database connection error"),
    ):
        success, message = await password_reset.reset_password_with_token(
            token="token123", new_password="NewPassword123!"
        )

        assert success is False
        assert "error occurred" in message.lower()


# =====================================================
# PASSWORD STRENGTH VALIDATION TESTS
# =====================================================


def test_is_password_strong_valid():
    """Test password strength validation with strong password."""
    is_strong, message = password_reset.is_password_strong("StrongPass123!")

    assert is_strong is True
    assert "strong" in message.lower()


def test_is_password_strong_too_short():
    """Test password strength validation with short password."""
    is_strong, message = password_reset.is_password_strong("Short1!")

    assert is_strong is False
    assert "at least 8 characters" in message.lower()


def test_is_password_strong_no_uppercase():
    """Test password strength validation without uppercase."""
    is_strong, message = password_reset.is_password_strong("weakpass123!")

    assert is_strong is False
    assert "uppercase" in message.lower()


def test_is_password_strong_no_lowercase():
    """Test password strength validation without lowercase."""
    is_strong, message = password_reset.is_password_strong("WEAKPASS123!")

    assert is_strong is False
    assert "lowercase" in message.lower()


def test_is_password_strong_no_digits():
    """Test password strength validation without digits."""
    is_strong, message = password_reset.is_password_strong("WeakPassword!")

    assert is_strong is False
    assert "numbers" in message.lower()


def test_is_password_strong_no_special():
    """Test password strength validation without special characters."""
    is_strong, message = password_reset.is_password_strong("WeakPassword123")

    assert is_strong is False
    assert "special character" in message.lower()


def test_is_password_strong_edge_cases():
    """Test password strength with edge cases."""
    # Exactly 8 characters with all requirements
    is_strong, _ = password_reset.is_password_strong("Pass123!")
    assert is_strong is True

    # Multiple special characters
    is_strong, _ = password_reset.is_password_strong("P@ssw0rd!#$")
    assert is_strong is True

    # Very long password
    is_strong, _ = password_reset.is_password_strong("VeryLongPassword123!WithManyChars")
    assert is_strong is True

    # Only special characters (no letters/digits)
    is_strong, _ = password_reset.is_password_strong("!@#$%^&*")
    assert is_strong is False


# =====================================================
# INTEGRATION TESTS (COMPLETE FLOW)
# =====================================================


@pytest.mark.asyncio
async def test_complete_password_reset_flow(sample_user, sample_reset_token, mock_smtp_server):
    """Test complete password reset flow from request to completion."""
    # Step 1: Request password reset
    with patch("src.auth.password_reset.get_user_by_username", return_value=sample_user):
        with patch(
            "src.auth.password_reset.create_reset_token",
            return_value=sample_reset_token["token"],
        ):
            with patch.dict("os.environ", {"EMAIL_ENABLED": "true", "EMAIL_PROVIDER": "smtp"}):
                success, message = await password_reset.request_password_reset(
                    username_or_email="testuser",
                    reset_url="http://localhost:8501",
                )

                assert success is True

    # Step 2: Validate token
    with patch("src.auth.password_reset.verify_reset_token", return_value=sample_reset_token):
        is_valid, message, token_record = await password_reset.validate_reset_token(
            sample_reset_token["token"]
        )

        assert is_valid is True

    # Step 3: Check password strength
    is_strong, message = password_reset.is_password_strong("NewStrongPass123!")
    assert is_strong is True

    # Step 4: Reset password
    with patch("src.auth.password_reset.use_reset_token", return_value=True):
        success, message = await password_reset.reset_password_with_token(
            token=sample_reset_token["token"],
            new_password="NewStrongPass123!",
            client_ip="127.0.0.1",
        )

        assert success is True


@pytest.mark.asyncio
async def test_password_reset_flow_with_weak_password(sample_user, sample_reset_token):
    """Test password reset flow with weak password."""
    # Request password reset
    with patch("src.auth.password_reset.get_user_by_username", return_value=sample_user):
        with patch(
            "src.auth.password_reset.create_reset_token",
            return_value=sample_reset_token["token"],
        ):
            with patch.dict("os.environ", {"EMAIL_ENABLED": "false"}):
                success, _ = await password_reset.request_password_reset(
                    username_or_email="testuser",
                    reset_url="http://localhost:8501",
                )

                assert success is True

    # Validate token
    with patch("src.auth.password_reset.verify_reset_token", return_value=sample_reset_token):
        is_valid, _, _ = await password_reset.validate_reset_token(sample_reset_token["token"])
        assert is_valid is True

    # Check weak password
    is_strong, message = password_reset.is_password_strong("weak")
    assert is_strong is False
    assert "at least 8 characters" in message.lower()

    # Should not proceed to reset with weak password (handled by UI)


@pytest.mark.asyncio
async def test_password_reset_flow_token_reuse(sample_user, sample_reset_token):
    """Test that tokens cannot be reused after successful reset."""
    # Request reset
    with patch("src.auth.password_reset.get_user_by_username", return_value=sample_user):
        with patch(
            "src.auth.password_reset.create_reset_token",
            return_value=sample_reset_token["token"],
        ):
            with patch.dict("os.environ", {"EMAIL_ENABLED": "false"}):
                success, _ = await password_reset.request_password_reset(
                    username_or_email="testuser",
                    reset_url="http://localhost:8501",
                )
                assert success is True

    # First reset - success
    with patch("src.auth.password_reset.use_reset_token", return_value=True):
        success, _ = await password_reset.reset_password_with_token(
            token=sample_reset_token["token"],
            new_password="NewPassword123!",
        )
        assert success is True

    # Second reset attempt with same token - should fail
    with patch("src.auth.password_reset.use_reset_token", return_value=False):
        success, message = await password_reset.reset_password_with_token(
            token=sample_reset_token["token"],
            new_password="AnotherPassword123!",
        )
        assert success is False
        assert "failed" in message.lower()
