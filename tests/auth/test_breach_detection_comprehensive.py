"""
Comprehensive tests for password breach detection module.

Target coverage: 0% -> 95%+

Tests haveibeenpwned.com API integration, k-anonymity model, breach detection logic,
error handling, logging, and singleton pattern.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from src.auth.breach_detection import (
    BreachDetectionManager,
    check_password_safety,
    get_breach_detection_manager,
    validate_password_breach,
)


class TestBreachDetectionManager:
    """Test BreachDetectionManager class."""

    def test_init(self):
        """Test manager initialization."""
        manager = BreachDetectionManager()
        assert manager.client is None
        assert manager.HIBP_API_URL == "https://api.pwnedpasswords.com/range/{hash_prefix}"
        assert manager.TIMEOUT == 10.0

    def test_get_client(self):
        """Test client caching."""
        manager = BreachDetectionManager()

        with patch("src.auth.breach_detection.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # First call should create client
            client1 = manager._get_client()
            assert client1 == mock_client
            mock_get_client.assert_called_once()

            # Second call should use cached client
            client2 = manager._get_client()
            assert client2 == mock_client
            mock_get_client.assert_called_once()  # Still only called once

    def test_hash_password(self):
        """Test password hashing with SHA-1."""
        manager = BreachDetectionManager()

        # Test known password hash
        password = "password123"
        hash_result = manager._hash_password(password)

        # Should be uppercase SHA-1 hash (40 characters)
        assert len(hash_result) == 40
        assert hash_result.isupper()
        assert hash_result.isalnum()

        # Test consistency
        hash_result2 = manager._hash_password(password)
        assert hash_result == hash_result2

        # Test different password gives different hash
        hash_result3 = manager._hash_password("different")
        assert hash_result != hash_result3

    @pytest.mark.asyncio
    async def test_check_password_breach_found(self):
        """Test checking breached password."""
        manager = BreachDetectionManager()

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            "ABCDE12345:100\r\n5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8:3861493\r\nOTHERHASH:50\r\n"
        )

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock()

        with patch("src.config.clients.clients_config.create_http_client") as mock_create:
            mock_create.return_value = mock_http_client

            # Mock _log_breach_check
            manager._log_breach_check = AsyncMock()

            # Test with "password" (known hash starts with 5BAA6)
            is_breached, count = await manager.check_password_breach("password")

            assert is_breached is True
            assert count == 3861493

            # Verify logging was called
            manager._log_breach_check.assert_called_once()
            call_args = manager._log_breach_check.call_args[1]
            assert call_args["is_breached"] is True
            assert call_args["breach_count"] == 3861493

    @pytest.mark.asyncio
    async def test_check_password_breach_not_found(self):
        """Test checking non-breached password."""
        manager = BreachDetectionManager()

        # Mock HTTP response with no matching hash
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OTHERHASH1:100\r\nOTHERHASH2:50\r\n"

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock()

        with patch("src.config.clients.clients_config.create_http_client") as mock_create:
            mock_create.return_value = mock_http_client
            manager._log_breach_check = AsyncMock()

            is_breached, count = await manager.check_password_breach("secure_password_123")

            assert is_breached is False
            assert count == 0

            # Verify logging
            call_args = manager._log_breach_check.call_args[1]
            assert call_args["is_breached"] is False
            assert call_args["breach_count"] == 0

    @pytest.mark.asyncio
    async def test_check_password_breach_api_error(self):
        """Test handling API error."""
        manager = BreachDetectionManager()

        # Mock HTTP response with error status
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock()

        with patch("src.config.clients.clients_config.create_http_client") as mock_create:
            mock_create.return_value = mock_http_client
            manager._log_breach_check = AsyncMock()

            # Should not block user on API error
            is_breached, count = await manager.check_password_breach("test_password")

            assert is_breached is False
            assert count == 0

    @pytest.mark.asyncio
    async def test_check_password_breach_timeout(self):
        """Test handling timeout."""
        manager = BreachDetectionManager()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock()

        with patch("src.config.clients.clients_config.create_http_client") as mock_create:
            mock_create.return_value = mock_http_client
            manager._log_breach_check = AsyncMock()

            # Should not block user on timeout
            is_breached, count = await manager.check_password_breach("test_password")

            assert is_breached is False
            assert count == 0

            # Verify logging includes timeout type
            call_args = manager._log_breach_check.call_args[1]
            assert "timeout" in call_args["check_type"]

    @pytest.mark.asyncio
    async def test_check_password_breach_general_exception(self):
        """Test handling general exception."""
        manager = BreachDetectionManager()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock()

        with patch("src.config.clients.clients_config.create_http_client") as mock_create:
            mock_create.return_value = mock_http_client
            manager._log_breach_check = AsyncMock()

            # Should not block user on exception
            is_breached, count = await manager.check_password_breach("test_password")

            assert is_breached is False
            assert count == 0

            # Verify logging includes error type
            call_args = manager._log_breach_check.call_args[1]
            assert "error" in call_args["check_type"]

    @pytest.mark.asyncio
    async def test_check_password_breach_with_user_id(self):
        """Test checking with user_id for logging."""
        manager = BreachDetectionManager()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "HASH1:10\r\n"

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock()

        with patch("src.config.clients.clients_config.create_http_client") as mock_create:
            mock_create.return_value = mock_http_client
            manager._log_breach_check = AsyncMock()

            await manager.check_password_breach(
                "password", user_id="user-123", check_type="registration"
            )

            # Verify user_id and check_type were passed to logging
            call_args = manager._log_breach_check.call_args[1]
            assert call_args["user_id"] == "user-123"
            assert call_args["check_type"] == "registration"

    @pytest.mark.asyncio
    async def test_get_breach_status_not_breached(self):
        """Test get_breach_status for safe password."""
        manager = BreachDetectionManager()
        manager.check_password_breach = AsyncMock(return_value=(False, 0))

        is_breached, count, message = await manager.get_breach_status("secure_password")

        assert is_breached is False
        assert count == 0
        assert "not been found" in message

    @pytest.mark.asyncio
    async def test_get_breach_status_low_breach_count(self):
        """Test get_breach_status with low breach count."""
        manager = BreachDetectionManager()
        manager.check_password_breach = AsyncMock(return_value=(True, 5))

        is_breached, count, message = await manager.get_breach_status("weak_password")

        assert is_breached is True
        assert count == 5
        assert "⚠️" in message
        assert "5 data breach(es)" in message

    @pytest.mark.asyncio
    async def test_get_breach_status_medium_breach_count(self):
        """Test get_breach_status with medium breach count."""
        manager = BreachDetectionManager()
        manager.check_password_breach = AsyncMock(return_value=(True, 50))

        is_breached, count, message = await manager.get_breach_status("weak_password")

        assert is_breached is True
        assert count == 50
        assert "⚠️" in message
        assert "50 data breaches" in message

    @pytest.mark.asyncio
    async def test_get_breach_status_high_breach_count(self):
        """Test get_breach_status with high breach count."""
        manager = BreachDetectionManager()
        manager.check_password_breach = AsyncMock(return_value=(True, 1000))

        is_breached, count, message = await manager.get_breach_status("very_weak_password")

        assert is_breached is True
        assert count == 1000
        assert "🚨" in message
        assert "Critical" in message
        assert "1,000" in message

    @pytest.mark.asyncio
    async def test_get_last_check_exists(self):
        """Test getting last check timestamp."""
        manager = BreachDetectionManager()

        # Mock Supabase client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"last_breach_check_at": "2025-01-01T12:00:00Z"}]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        result = await manager.get_last_check("user-123")

        assert result is not None
        assert isinstance(result, datetime)

    @pytest.mark.asyncio
    async def test_get_last_check_not_exists(self):
        """Test getting last check when none exists."""
        manager = BreachDetectionManager()

        # Mock Supabase client with no data
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        result = await manager.get_last_check("user-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_should_check_breach_never_checked(self):
        """Test should_check_breach when never checked."""
        manager = BreachDetectionManager()
        manager.get_last_check = AsyncMock(return_value=None)

        result = await manager.should_check_breach("user-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_should_check_breach_within_interval(self):
        """Test should_check_breach when recently checked."""
        manager = BreachDetectionManager()

        # Last check was 10 days ago (use naive datetime)
        from datetime import timedelta

        last_check = datetime.now() - timedelta(days=10)
        manager.get_last_check = AsyncMock(return_value=last_check)

        result = await manager.should_check_breach("user-123", check_interval_days=30)

        assert result is False

    @pytest.mark.asyncio
    async def test_should_check_breach_outside_interval(self):
        """Test should_check_breach when check is due."""
        manager = BreachDetectionManager()

        # Last check was 35 days ago (use naive datetime)
        from datetime import timedelta

        last_check = datetime.now() - timedelta(days=35)
        manager.get_last_check = AsyncMock(return_value=last_check)

        result = await manager.should_check_breach("user-123", check_interval_days=30)

        assert result is True

    @pytest.mark.asyncio
    async def test_log_breach_check_with_user_id(self):
        """Test logging breach check with user_id."""
        manager = BreachDetectionManager()

        # Mock Supabase client
        mock_client = MagicMock()
        manager._get_client = Mock(return_value=mock_client)

        await manager._log_breach_check(
            hash_prefix="5BAA6",
            is_breached=True,
            breach_count=100,
            check_type="login",
            user_id="user-123",
            ip_address="192.168.1.1",
        )

        # Verify insert was called
        mock_client.table.assert_any_call("auth_breach_checks")
        mock_client.table.assert_any_call("auth_users")

    @pytest.mark.asyncio
    async def test_log_breach_check_without_user_id(self):
        """Test logging breach check without user_id."""
        manager = BreachDetectionManager()

        # Mock Supabase client
        mock_client = MagicMock()
        manager._get_client = Mock(return_value=mock_client)

        await manager._log_breach_check(
            hash_prefix="5BAA6",
            is_breached=False,
            breach_count=0,
            check_type="manual",
        )

        # Verify insert was called
        mock_client.table.assert_called_once_with("auth_breach_checks")


class TestSingletonAndHelperFunctions:
    """Test singleton pattern and helper functions."""

    def test_get_breach_detection_manager_singleton(self):
        """Test singleton pattern."""
        # Reset singleton
        import src.auth.breach_detection

        src.auth.breach_detection._breach_detection_manager = None

        manager1 = get_breach_detection_manager()
        manager2 = get_breach_detection_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_check_password_safety_safe(self):
        """Test check_password_safety with safe password."""
        with patch("src.auth.breach_detection.get_breach_detection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_breach_status = AsyncMock(return_value=(False, 0, "Password is safe"))
            mock_get_manager.return_value = mock_manager

            is_safe, message = await check_password_safety("secure_password")

            assert is_safe is True
            assert message == "Password is safe"

    @pytest.mark.asyncio
    async def test_check_password_safety_breached(self):
        """Test check_password_safety with breached password."""
        with patch("src.auth.breach_detection.get_breach_detection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_breach_status = AsyncMock(
                return_value=(True, 100, "Password is breached")
            )
            mock_get_manager.return_value = mock_manager

            is_safe, message = await check_password_safety("weak_password")

            assert is_safe is False
            assert message == "Password is breached"

    @pytest.mark.asyncio
    async def test_validate_password_breach_valid(self):
        """Test validate_password_breach with valid password."""
        with patch("src.auth.breach_detection.check_password_safety") as mock_check:
            mock_check.return_value = (True, "Password is safe")

            is_valid, error_msg = await validate_password_breach("secure_password")

            assert is_valid is True
            assert error_msg == ""

    @pytest.mark.asyncio
    async def test_validate_password_breach_invalid(self):
        """Test validate_password_breach with invalid password."""
        with patch("src.auth.breach_detection.check_password_safety") as mock_check:
            mock_check.return_value = (False, "Password is breached")

            is_valid, error_msg = await validate_password_breach("weak_password")

            assert is_valid is False
            assert error_msg == "Password is breached"

    @pytest.mark.asyncio
    async def test_check_password_safety_with_params(self):
        """Test check_password_safety with user_id and check_type."""
        with patch("src.auth.breach_detection.get_breach_detection_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_breach_status = AsyncMock(return_value=(False, 0, "Safe"))
            mock_get_manager.return_value = mock_manager

            await check_password_safety("password", user_id="user-123", check_type="registration")

            # Verify get_breach_status was called
            mock_manager.get_breach_status.assert_called_once_with("password")
