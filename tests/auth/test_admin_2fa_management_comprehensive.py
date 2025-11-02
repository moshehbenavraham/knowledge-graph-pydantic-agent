"""
Comprehensive tests for auth/admin_2fa_management.py.

Tests admin 2FA management UI functionality.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestIsAdmin:
    """Test is_admin function."""

    @pytest.mark.asyncio
    @patch("src.auth.admin_2fa_management.get_user_roles")
    @patch("src.auth.db.get_user_by_username")
    async def test_user_is_admin(self, mock_get_user, mock_get_roles):
        """Test user with admin role."""
        from src.auth.admin_2fa_management import is_admin

        mock_get_user.return_value = {"id": "user-123", "username": "adminuser"}
        mock_get_roles.return_value = [{"name": "admin", "description": "Administrator"}]

        result = await is_admin("adminuser")

        assert result is True

    @pytest.mark.asyncio
    @patch("src.auth.admin_2fa_management.get_user_roles")
    @patch("src.auth.db.get_user_by_username")
    async def test_user_is_not_admin(self, mock_get_user, mock_get_roles):
        """Test user without admin role."""
        from src.auth.admin_2fa_management import is_admin

        mock_get_user.return_value = {"id": "user-123", "username": "normaluser"}
        mock_get_roles.return_value = [{"name": "user", "description": "Regular user"}]

        result = await is_admin("normaluser")

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.db.get_user_by_username")
    async def test_user_not_found(self, mock_get_user):
        """Test when user doesn't exist."""
        from src.auth.admin_2fa_management import is_admin

        mock_get_user.return_value = None

        result = await is_admin("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.db.get_user_by_username")
    async def test_exception_handling(self, mock_get_user):
        """Test exception handling."""
        from src.auth.admin_2fa_management import is_admin

        mock_get_user.side_effect = Exception("Database error")

        result = await is_admin("testuser")

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.admin_2fa_management.get_user_roles")
    @patch("src.auth.db.get_user_by_username")
    async def test_multiple_roles_with_admin(self, mock_get_user, mock_get_roles):
        """Test user with multiple roles including admin."""
        from src.auth.admin_2fa_management import is_admin

        mock_get_user.return_value = {"id": "user-123", "username": "multiuser"}
        mock_get_roles.return_value = [
            {"name": "user"},
            {"name": "admin"},
            {"name": "viewer"},
        ]

        result = await is_admin("multiuser")

        assert result is True

    @pytest.mark.asyncio
    @patch("src.auth.admin_2fa_management.get_user_roles")
    @patch("src.auth.db.get_user_by_username")
    async def test_empty_roles_list(self, mock_get_user, mock_get_roles):
        """Test user with empty roles list."""
        from src.auth.admin_2fa_management import is_admin

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}
        mock_get_roles.return_value = []

        result = await is_admin("testuser")

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.admin_2fa_management.get_user_roles")
    @patch("src.auth.db.get_user_by_username")
    async def test_roles_without_name_field(self, mock_get_user, mock_get_roles):
        """Test roles without name field."""
        from src.auth.admin_2fa_management import is_admin

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}
        mock_get_roles.return_value = [{"description": "Some role"}]  # Missing 'name'

        result = await is_admin("testuser")

        assert result is False


class TestRender2FAManagementUI:
    """Test render_2fa_management_ui function."""

    @patch("src.auth.admin_2fa_management.st")
    def test_not_authenticated(self, mock_st):
        """Test when user is not authenticated."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = None

        render_2fa_management_ui()

        mock_st.error.assert_called_once_with("Not authenticated")

    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_not_admin_user(self, mock_st, mock_asyncio_run):
        """Test when user is not admin."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = "normaluser"
        mock_asyncio_run.return_value = False

        render_2fa_management_ui()

        mock_st.error.assert_called_once_with("⛔ Access denied. Admin privileges required.")

    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_empty_user_list(self, mock_st, mock_asyncio_run):
        """Test when there are no active users."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = "adminuser"

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:
                return True  # is_admin
            return []  # Empty user list

        mock_asyncio_run.side_effect = asyncio_side_effect

        render_2fa_management_ui()

        mock_st.info.assert_called_once_with("No active users found.")

    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_exception_in_user_loading(self, mock_st, mock_asyncio_run):
        """Test exception handling during user loading."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = "adminuser"

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            raise Exception("Database error")

        mock_asyncio_run.side_effect = asyncio_side_effect

        render_2fa_management_ui()

        # Verify error was displayed
        assert any(
            "Failed to load user list" in str(call.args) for call in mock_st.error.call_args_list
        )


class TestRenderUser2FASettings:
    """Test render_user_2fa_settings function."""

    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_user_not_found(self, mock_st, mock_asyncio_run):
        """Test when user doesn't exist."""
        from src.auth.admin_2fa_management import render_user_2fa_settings

        mock_asyncio_run.return_value = None

        render_user_2fa_settings("nonexistent")

        mock_st.error.assert_called_once_with("User not found")

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_user_with_2fa_required(
        self, mock_st, mock_asyncio_run, mock_get_backup, mock_get_totp
    ):
        """Test user with 2FA required by admin."""
        from src.auth.admin_2fa_management import render_user_2fa_settings

        user = {
            "id": "00000000-0000-0000-0000-000000000123",
            "username": "testuser",
            "requires_2fa": True,
        }

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:
                return user
            if call_count[0] == 2:
                return True
            if call_count[0] == 3:
                return 5
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect
        mock_st.button.return_value = False

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_user_2fa_settings("testuser")

        assert mock_st.info.called

    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_exception_handling(self, mock_st, mock_asyncio_run):
        """Test exception handling in settings."""
        from src.auth.admin_2fa_management import render_user_2fa_settings

        mock_asyncio_run.side_effect = Exception("Database error")

        render_user_2fa_settings("testuser")

        mock_st.error.assert_called_once()


class TestLogging:
    """Test logging functionality."""

    @pytest.mark.asyncio
    @patch("src.auth.admin_2fa_management.logger")
    @patch("src.auth.db.get_user_by_username")
    async def test_error_logging_in_is_admin(self, mock_get_user, mock_logger):
        """Test that errors are logged in is_admin."""
        from src.auth.admin_2fa_management import is_admin

        mock_get_user.side_effect = Exception("Test error")

        await is_admin("testuser")

        mock_logger.error.assert_called_once()
        args, _kwargs = mock_logger.error.call_args
        assert "Failed to check admin status" in args[0]


class TestModuleImports:
    """Test module imports work correctly."""

    def test_module_imports(self):
        """Test that module can be imported."""
        import src.auth.admin_2fa_management

        assert hasattr(src.auth.admin_2fa_management, "is_admin")
        assert hasattr(src.auth.admin_2fa_management, "render_2fa_management_ui")
        assert hasattr(src.auth.admin_2fa_management, "render_user_2fa_settings")

    def test_functions_are_callable(self):
        """Test that functions are callable."""
        from src.auth.admin_2fa_management import (
            is_admin,
            render_2fa_management_ui,
            render_user_2fa_settings,
        )

        assert callable(is_admin)
        assert callable(render_2fa_management_ui)
        assert callable(render_user_2fa_settings)


class TestIntegrationScenarios:
    """Integration test scenarios."""

    @pytest.mark.asyncio
    @patch("src.auth.admin_2fa_management.get_user_roles")
    @patch("src.auth.db.get_user_by_username")
    async def test_admin_check_flow(self, mock_get_user, mock_get_roles):
        """Test admin check flow."""
        from src.auth.admin_2fa_management import is_admin

        # Scenario 1: Admin user
        mock_get_user.return_value = {"id": "admin-123", "username": "admin"}
        mock_get_roles.return_value = [{"name": "admin"}]
        assert await is_admin("admin") is True

        # Scenario 2: Regular user
        mock_get_user.return_value = {"id": "user-123", "username": "user"}
        mock_get_roles.return_value = [{"name": "user"}]
        assert await is_admin("user") is False

        # Scenario 3: Non-existent user
        mock_get_user.return_value = None
        assert await is_admin("nobody") is False
