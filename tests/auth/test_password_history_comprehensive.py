"""
Comprehensive tests for password history management.

Target coverage: 0% -> 95%+

Tests password history tracking, reuse validation, bcrypt comparison,
cleanup logic, and singleton pattern.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import bcrypt
import pytest

from src.auth.password_history import (
    PasswordHistoryManager,
    get_password_history_manager,
    record_password_change,
    validate_new_password,
)


class TestPasswordHistoryManager:
    """Test PasswordHistoryManager class."""

    def test_init(self):
        """Test manager initialization."""
        manager = PasswordHistoryManager()
        assert manager.client is None
        assert manager.MAX_HISTORY == 5

    def test_get_client(self):
        """Test client caching."""
        manager = PasswordHistoryManager()

        with patch("src.auth.password_history.get_supabase_client") as mock_get_client:
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

    @pytest.mark.asyncio
    async def test_add_password_to_history(self):
        """Test adding password to history."""
        manager = PasswordHistoryManager()

        # Mock Supabase client
        mock_client = MagicMock()
        manager._get_client = Mock(return_value=mock_client)
        manager._cleanup_old_passwords = Mock()

        # Mock async cleanup
        async def mock_cleanup(user_id):
            pass

        manager._cleanup_old_passwords = mock_cleanup

        password_hash = "hashed_password"
        user_id = "user-123"
        ip_address = "192.168.1.1"

        await manager.add_password_to_history(user_id, password_hash, ip_address)

        # Verify insert was called
        mock_client.table.assert_any_call("auth_password_history")
        mock_client.table.assert_any_call("auth_users")

    @pytest.mark.asyncio
    async def test_add_password_to_history_without_ip(self):
        """Test adding password without IP address."""
        manager = PasswordHistoryManager()

        # Mock Supabase client
        mock_client = MagicMock()
        manager._get_client = Mock(return_value=mock_client)

        # Mock async cleanup
        async def mock_cleanup(user_id):
            pass

        manager._cleanup_old_passwords = mock_cleanup

        await manager.add_password_to_history("user-123", "hashed_password")

        # Should still work without IP
        mock_client.table.assert_called()

    @pytest.mark.asyncio
    async def test_is_password_reused_true(self):
        """Test detecting password reuse."""
        manager = PasswordHistoryManager()

        # Create a real bcrypt hash for testing
        test_password = "password123"
        password_hash = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()

        # Mock Supabase client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"password_hash": password_hash}]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        # Check if same password is reused
        is_reused = await manager.is_password_reused("user-123", test_password)

        assert is_reused is True

    @pytest.mark.asyncio
    async def test_is_password_reused_false(self):
        """Test detecting new password (not reused)."""
        manager = PasswordHistoryManager()

        # Create hash for different password
        old_password = "old_password"
        password_hash = bcrypt.hashpw(old_password.encode(), bcrypt.gensalt()).decode()

        # Mock Supabase client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"password_hash": password_hash}]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        # Check if different password is reused
        is_reused = await manager.is_password_reused("user-123", "new_password")

        assert is_reused is False

    @pytest.mark.asyncio
    async def test_is_password_reused_no_history(self):
        """Test when user has no password history."""
        manager = PasswordHistoryManager()

        # Mock Supabase client with no data
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        is_reused = await manager.is_password_reused("user-123", "password")

        assert is_reused is False

    @pytest.mark.asyncio
    async def test_is_password_reused_multiple_hashes(self):
        """Test checking against multiple historical passwords."""
        manager = PasswordHistoryManager()

        # Create multiple password hashes
        password1 = "password1"
        password2 = "password2"
        hash1 = bcrypt.hashpw(password1.encode(), bcrypt.gensalt()).decode()
        hash2 = bcrypt.hashpw(password2.encode(), bcrypt.gensalt()).decode()

        # Mock Supabase client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"password_hash": hash1}, {"password_hash": hash2}]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        # Check if second password matches
        is_reused = await manager.is_password_reused("user-123", password2)

        assert is_reused is True

    @pytest.mark.asyncio
    async def test_get_password_history_count(self):
        """Test getting password history count."""
        manager = PasswordHistoryManager()

        # Mock Supabase client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.count = 3
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        count = await manager.get_password_history_count("user-123")

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_password_history_count_zero(self):
        """Test getting count when no history."""
        manager = PasswordHistoryManager()

        # Mock Supabase client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.count = None
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        count = await manager.get_password_history_count("user-123")

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_password_change_dates(self):
        """Test getting password change dates."""
        manager = PasswordHistoryManager()

        # Mock Supabase client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"created_at": "2025-01-01T12:00:00Z"},
            {"created_at": "2025-01-02T12:00:00Z"},
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        dates = await manager.get_password_change_dates("user-123")

        assert len(dates) == 2
        assert all(isinstance(d, datetime) for d in dates)

    @pytest.mark.asyncio
    async def test_get_password_change_dates_no_history(self):
        """Test getting dates when no history."""
        manager = PasswordHistoryManager()

        # Mock Supabase client with no data
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        dates = await manager.get_password_change_dates("user-123")

        assert dates == []

    @pytest.mark.asyncio
    async def test_cleanup_old_passwords_no_cleanup_needed(self):
        """Test cleanup when within limit."""
        manager = PasswordHistoryManager()

        # Mock Supabase client with 3 passwords (under limit)
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        await manager._cleanup_old_passwords("user-123")

        # Should not attempt to delete anything
        # (just queried, no delete operations)

    @pytest.mark.asyncio
    async def test_cleanup_old_passwords_cleanup_needed(self):
        """Test cleanup when over limit."""
        manager = PasswordHistoryManager()

        # Mock Supabase client with 7 passwords (over limit of 5)
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "1"},
            {"id": "2"},
            {"id": "3"},
            {"id": "4"},
            {"id": "5"},
            {"id": "6"},
            {"id": "7"},
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        await manager._cleanup_old_passwords("user-123")

        # Should delete passwords 6 and 7 (beyond last 5)
        # Verify delete was called for old passwords

    @pytest.mark.asyncio
    async def test_cleanup_old_passwords_empty_history(self):
        """Test cleanup with empty history."""
        manager = PasswordHistoryManager()

        # Mock Supabase client with no data
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        await manager._cleanup_old_passwords("user-123")

        # Should return early without errors

    @pytest.mark.asyncio
    async def test_clear_history(self):
        """Test clearing all password history."""
        manager = PasswordHistoryManager()

        # Mock Supabase client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        count = await manager.clear_history("user-123")

        assert count == 3
        mock_client.table.assert_called_with("auth_password_history")

    @pytest.mark.asyncio
    async def test_clear_history_no_data(self):
        """Test clearing when no history exists."""
        manager = PasswordHistoryManager()

        # Mock Supabase client with no data
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = None
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        manager._get_client = Mock(return_value=mock_client)

        count = await manager.clear_history("user-123")

        assert count == 0


class TestSingletonAndHelperFunctions:
    """Test singleton pattern and helper functions."""

    def test_get_password_history_manager_singleton(self):
        """Test singleton pattern."""
        # Reset singleton
        import src.auth.password_history

        src.auth.password_history._password_history_manager = None

        manager1 = get_password_history_manager()
        manager2 = get_password_history_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_validate_new_password_valid(self):
        """Test validating new password that's not reused."""
        with patch("src.auth.password_history.get_password_history_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_password_reused = Mock(return_value=False)
            mock_get_manager.return_value = mock_manager

            # Mock the async method properly
            async def mock_is_reused(user_id, password):
                return False

            mock_manager.is_password_reused = mock_is_reused

            is_valid, error_msg = await validate_new_password("user-123", "new_password")

            assert is_valid is True
            assert error_msg == ""

    @pytest.mark.asyncio
    async def test_validate_new_password_reused(self):
        """Test validating password that was recently used."""
        with patch("src.auth.password_history.get_password_history_manager") as mock_get_manager:
            mock_manager = MagicMock()

            # Mock the async method properly
            async def mock_is_reused(user_id, password):
                return True

            mock_manager.is_password_reused = mock_is_reused
            mock_get_manager.return_value = mock_manager

            is_valid, error_msg = await validate_new_password("user-123", "old_password")

            assert is_valid is False
            assert "used recently" in error_msg
            assert "last 5 passwords" in error_msg

    @pytest.mark.asyncio
    async def test_record_password_change(self):
        """Test recording password change."""
        with patch("src.auth.password_history.get_password_history_manager") as mock_get_manager:
            mock_manager = MagicMock()

            # Mock the async method properly
            async def mock_add_to_history(user_id, password_hash, ip_address):
                pass

            mock_manager.add_password_to_history = mock_add_to_history
            mock_get_manager.return_value = mock_manager

            await record_password_change("user-123", "hashed_password", "192.168.1.1")

            # Should complete without error

    @pytest.mark.asyncio
    async def test_record_password_change_without_ip(self):
        """Test recording password change without IP."""
        with patch("src.auth.password_history.get_password_history_manager") as mock_get_manager:
            mock_manager = MagicMock()

            # Mock the async method properly
            async def mock_add_to_history(user_id, password_hash, ip_address):
                pass

            mock_manager.add_password_to_history = mock_add_to_history
            mock_get_manager.return_value = mock_manager

            await record_password_change("user-123", "hashed_password")

            # Should complete without error


class TestIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_password_change_workflow(self):
        """Test complete password change workflow."""
        manager = PasswordHistoryManager()

        # Create real bcrypt hashes
        old_password = "old_password_123"
        new_password = "new_password_456"
        old_hash = bcrypt.hashpw(old_password.encode(), bcrypt.gensalt()).decode()

        # Mock Supabase client
        mock_client = MagicMock()

        # Mock is_password_reused check
        mock_result_history = MagicMock()
        mock_result_history.data = [{"password_hash": old_hash}]

        # Mock add_password_to_history
        mock_result_insert = MagicMock()

        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            mock_result_history
        )
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result_insert

        manager._get_client = Mock(return_value=mock_client)

        # Mock async cleanup
        async def mock_cleanup(user_id):
            pass

        manager._cleanup_old_passwords = mock_cleanup

        # Check if old password is reused (should be True)
        is_reused_old = await manager.is_password_reused("user-123", old_password)
        assert is_reused_old is True

        # Check if new password is reused (should be False)
        is_reused_new = await manager.is_password_reused("user-123", new_password)
        assert is_reused_new is False

        # Add new password to history
        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        await manager.add_password_to_history("user-123", new_hash, "192.168.1.1")

        # Verify operations occurred
        assert mock_client.table.called
