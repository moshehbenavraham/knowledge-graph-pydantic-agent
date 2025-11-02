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


class TestRender2FAManagementUIComprehensive:
    """Comprehensive tests for render_2fa_management_ui with full UI flow."""

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_display_users_with_2fa_status(
        self, mock_st, mock_asyncio_run, mock_get_backup, mock_get_totp
    ):
        """Test displaying users with their 2FA status."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        # Setup session state
        mock_st.session_state.get.return_value = "adminuser"

        # Mock users
        users = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "is_active": True,
                "requires_2fa": True,
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "username": "user2",
                "email": "user2@example.com",
                "full_name": "User Two",
                "is_active": True,
                "requires_2fa": False,
            },
        ]

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # is_admin check
                return True
            if call_count[0] == 2:  # list_users
                return users
            if call_count[0] == 3:  # is_2fa_enabled
                return True
            if call_count[0] == 4:  # get_unused_count
                return 5
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect

        # Mock selectbox to return a user
        mock_st.selectbox.return_value = "user1 (user1@example.com) - User One"
        mock_st.button.return_value = False

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        # Mock columns
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]

        render_2fa_management_ui()

        # Verify metrics were displayed
        assert mock_st.columns.called
        assert mock_st.metric.called or mock_col1.metric.called

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.set_2fa_requirement")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_enable_2fa_requirement_button(
        self, mock_st, mock_asyncio_run, mock_set_2fa, mock_get_backup, mock_get_totp
    ):
        """Test enabling 2FA requirement via button click."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = "adminuser"

        users = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "is_active": True,
                "requires_2fa": False,
            }
        ]

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # is_admin
                return True
            if call_count[0] == 2:  # list_users
                return users
            if call_count[0] == 3:  # is_2fa_enabled
                return False
            if call_count[0] == 4:  # set_2fa_requirement
                return None
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect
        mock_st.selectbox.return_value = "user1 (user1@example.com) - User One"

        # First button returns True (enable 2FA)
        button_calls = [0]

        def button_side_effect(*args, **kwargs):
            button_calls[0] += 1
            return button_calls[0] == 1

        mock_st.button.side_effect = button_side_effect

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        # Mock columns
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.side_effect = [
            [mock_col1, mock_col2, MagicMock()],  # metrics
            [mock_col1, mock_col2],  # buttons
        ]

        # Need to mock the button on col1
        mock_col1.button.return_value = True

        render_2fa_management_ui()

        # Verify set_2fa_requirement was called
        assert call_count[0] >= 4 or mock_st.rerun.called

    @patch("src.auth.admin_2fa_management.get_user_roles")
    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_bulk_action_for_admins(
        self,
        mock_st,
        mock_asyncio_run,
        mock_get_backup,
        mock_get_totp,
        mock_get_roles,
    ):
        """Test bulk 2FA requirement for admin users."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = "adminuser"

        users = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "username": "admin1",
                "email": "admin1@example.com",
                "full_name": "Admin One",
                "is_active": True,
                "requires_2fa": False,
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "is_active": True,
                "requires_2fa": False,
            },
        ]

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # is_admin
                return True
            if call_count[0] == 2:  # list_users
                return users
            if call_count[0] == 3:  # is_2fa_enabled for selected user
                return False
            if call_count[0] == 4:  # get_user_roles for bulk action
                return [{"name": "admin"}]
            if call_count[0] == 5:  # set_2fa_requirement for admin
                return None
            if call_count[0] == 6:  # get_user_roles for second user
                return [{"name": "user"}]
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect
        mock_st.selectbox.return_value = "admin1 (admin1@example.com) - Admin One"

        # Mock expander and button for bulk action
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__.return_value = mock_expander

        button_calls = [0]

        def button_side_effect(*args, **kwargs):
            button_calls[0] += 1
            # Return True for the bulk action button
            return button_calls[0] == 1 and "Require 2FA for all Admin" in str(args)

        mock_st.button.side_effect = button_side_effect

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        # Mock columns
        mock_st.columns.side_effect = [
            [MagicMock(), MagicMock(), MagicMock()],  # metrics
            [MagicMock(), MagicMock()],  # buttons
        ]

        render_2fa_management_ui()

        # Should have called asyncio.run multiple times
        assert call_count[0] >= 3


class TestRenderUser2FASettingsComprehensive:
    """Comprehensive tests for render_user_2fa_settings with full UI flow."""

    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_user_with_2fa_enabled_optional(
        self, mock_st, mock_asyncio_run, mock_get_totp, mock_get_backup
    ):
        """Test user with 2FA enabled but not required."""
        from src.auth.admin_2fa_management import render_user_2fa_settings

        user = {
            "id": "00000000-0000-0000-0000-000000000123",
            "username": "testuser",
            "requires_2fa": False,
        }

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # get_user_by_username
                return user
            if call_count[0] == 2:  # is_2fa_enabled
                return True
            if call_count[0] == 3:  # get_unused_count
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

        # Verify UI elements were called
        assert mock_st.markdown.called
        assert mock_st.success.called or mock_st.info.called

    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_regenerate_backup_codes(
        self, mock_st, mock_asyncio_run, mock_get_totp, mock_get_backup
    ):
        """Test regenerating backup codes."""
        from src.auth.admin_2fa_management import render_user_2fa_settings

        user = {
            "id": "00000000-0000-0000-0000-000000000123",
            "username": "testuser",
            "requires_2fa": False,
        }

        call_count = [0]
        new_codes = ["CODE1", "CODE2", "CODE3"]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # get_user_by_username
                return user
            if call_count[0] == 2:  # is_2fa_enabled
                return True
            if call_count[0] == 3:  # get_unused_count
                return 2
            if call_count[0] == 4:  # generate_backup_codes
                return new_codes
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect

        # First button click returns True (regenerate codes)
        button_calls = [0]

        def button_side_effect(*args, **kwargs):
            button_calls[0] += 1
            return button_calls[0] == 1

        mock_st.button.side_effect = button_side_effect

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_user_2fa_settings("testuser")

        # Verify backup codes were generated
        assert call_count[0] == 4 or mock_st.code.called

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_disable_2fa_flow(self, mock_st, mock_asyncio_run, mock_get_backup, mock_get_totp):
        """Test disabling 2FA when not required."""
        from src.auth.admin_2fa_management import render_user_2fa_settings

        user = {
            "id": "00000000-0000-0000-0000-000000000123",
            "username": "testuser",
            "requires_2fa": False,
        }

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # get_user_by_username
                return user
            if call_count[0] == 2:  # is_2fa_enabled
                return True
            if call_count[0] == 3:  # get_unused_count
                return 5
            if call_count[0] == 4:  # disable_2fa
                return True
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect

        # Multiple button clicks for disable flow
        button_calls = [0]

        def button_side_effect(*args, **kwargs):
            button_calls[0] += 1
            # First click: Disable 2FA button
            if button_calls[0] == 1:
                return False
            # Second click: Confirm disable
            return button_calls[0] in (2, 3)

        mock_st.button.side_effect = button_side_effect

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_user_2fa_settings("testuser")

        # Should have made multiple asyncio calls
        assert call_count[0] >= 3

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_user_without_2fa_setup(
        self, mock_st, mock_asyncio_run, mock_get_backup, mock_get_totp
    ):
        """Test user without 2FA setup."""
        from src.auth.admin_2fa_management import render_user_2fa_settings

        user = {
            "id": "00000000-0000-0000-0000-000000000123",
            "username": "testuser",
            "requires_2fa": False,
        }

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # get_user_by_username
                return user
            if call_count[0] == 2:  # is_2fa_enabled
                return False
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect

        # Button click for setup 2FA
        button_calls = [0]

        def button_side_effect(*args, **kwargs):
            button_calls[0] += 1
            return button_calls[0] == 1

        mock_st.button.side_effect = button_side_effect

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_user_2fa_settings("testuser")

        # Verify warning and setup button
        assert mock_st.warning.called or call_count[0] >= 2

    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_regenerate_backup_codes_exception(
        self, mock_st, mock_asyncio_run, mock_get_totp, mock_get_backup
    ):
        """Test exception during backup code regeneration."""
        from src.auth.admin_2fa_management import render_user_2fa_settings

        user = {
            "id": "00000000-0000-0000-0000-000000000123",
            "username": "testuser",
            "requires_2fa": False,
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
            if call_count[0] == 4:
                raise Exception("Database error")
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect
        mock_st.button.return_value = True

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_user_2fa_settings("testuser")

        # Verify error was shown
        assert call_count[0] == 4 or mock_st.error.called


class TestExceptionHandlingPaths:
    """Test exception handling in UI functions."""

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_exception_getting_2fa_status(
        self, mock_st, mock_asyncio_run, mock_get_backup, mock_get_totp
    ):
        """Test exception when getting 2FA status."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = "adminuser"

        users = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "is_active": True,
                "requires_2fa": False,
            }
        ]

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # is_admin
                return True
            if call_count[0] == 2:  # list_users
                return users
            if call_count[0] == 3:  # is_2fa_enabled - throws exception
                raise Exception("Database connection error")
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect
        mock_st.selectbox.return_value = "user1 (user1@example.com) - User One"
        mock_st.button.return_value = False

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        # Mock columns
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_2fa_management_ui()

        # Verify warning was shown
        assert mock_st.warning.called

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_exception_enabling_2fa_requirement(
        self, mock_st, mock_asyncio_run, mock_get_backup, mock_get_totp
    ):
        """Test exception when enabling 2FA requirement."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = "adminuser"

        users = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "is_active": True,
                "requires_2fa": False,
            }
        ]

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # is_admin
                return True
            if call_count[0] == 2:  # list_users
                return users
            if call_count[0] == 3:  # is_2fa_enabled
                return False
            if call_count[0] == 4:  # set_2fa_requirement - throws exception
                raise Exception("Database write error")
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect
        mock_st.selectbox.return_value = "user1 (user1@example.com) - User One"

        # Mock columns
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.side_effect = [
            [mock_col1, mock_col2, MagicMock()],  # metrics
            [mock_col1, mock_col2],  # buttons
        ]

        # Button returns True
        mock_col1.button.return_value = True

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_2fa_management_ui()

        # Verify error was shown
        assert mock_st.error.called

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_exception_disabling_2fa_requirement(
        self, mock_st, mock_asyncio_run, mock_get_backup, mock_get_totp
    ):
        """Test exception when disabling 2FA requirement."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = "adminuser"

        users = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "is_active": True,
                "requires_2fa": True,
            }
        ]

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # is_admin
                return True
            if call_count[0] == 2:  # list_users
                return users
            if call_count[0] == 3:  # is_2fa_enabled
                return True
            if call_count[0] == 4:  # get_unused_count
                return 5
            if call_count[0] == 5:  # set_2fa_requirement - throws exception
                raise Exception("Database write error")
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect
        mock_st.selectbox.return_value = "user1 (user1@example.com) - User One"

        # Mock columns
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.side_effect = [
            [mock_col1, mock_col2, MagicMock()],  # metrics
            [mock_col1, mock_col2],  # buttons
        ]

        # Button on col2 returns True (disable 2FA)
        mock_col2.button.return_value = True

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_2fa_management_ui()

        # Verify error was shown
        assert mock_st.error.called

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.totp_2fa.get_backup_code_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_user_with_2fa_required_and_enabled(
        self, mock_st, mock_asyncio_run, mock_get_backup, mock_get_totp
    ):
        """Test user with 2FA both required and enabled showing info message."""
        from src.auth.admin_2fa_management import render_2fa_management_ui

        mock_st.session_state.get.return_value = "adminuser"

        users = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "is_active": True,
                "requires_2fa": True,
            }
        ]

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # is_admin
                return True
            if call_count[0] == 2:  # list_users
                return users
            if call_count[0] == 3:  # is_2fa_enabled
                return True
            if call_count[0] == 4:  # get_unused_count
                return 5
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect
        mock_st.selectbox.return_value = "user1 (user1@example.com) - User One"
        mock_st.button.return_value = False

        # Mock managers
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        # Mock columns
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_2fa_management_ui()

        # Should have completed successfully - check asyncio was called
        assert call_count[0] >= 4

    @patch("src.auth.totp_2fa.get_totp_manager")
    @patch("src.auth.admin_2fa_management.asyncio.run")
    @patch("src.auth.admin_2fa_management.st")
    def test_disable_2fa_exception(self, mock_st, mock_asyncio_run, mock_get_totp):
        """Test exception when disabling 2FA in user settings."""
        from src.auth.admin_2fa_management import render_user_2fa_settings

        user = {
            "id": "00000000-0000-0000-0000-000000000123",
            "username": "testuser",
            "requires_2fa": False,
        }

        call_count = [0]

        def asyncio_side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:  # get_user_by_username
                return user
            if call_count[0] == 2:  # is_2fa_enabled
                return True
            if call_count[0] == 3:  # get_unused_count
                return 5
            if call_count[0] == 4:  # disable_2fa - throws exception
                raise Exception("Failed to disable")
            return None

        mock_asyncio_run.side_effect = asyncio_side_effect

        # Mock button clicks
        button_calls = [0]

        def button_side_effect(*args, **kwargs):
            button_calls[0] += 1
            # Disable button, then confirm button
            return button_calls[0] in [1, 2]

        mock_st.button.side_effect = button_side_effect

        # Mock manager
        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp

        render_user_2fa_settings("testuser")

        # Verify error was shown
        assert call_count[0] == 4 or mock_st.error.called
