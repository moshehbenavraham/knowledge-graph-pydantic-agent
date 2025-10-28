"""
Comprehensive tests for auth/enforce_2fa.py.

Tests 2FA enforcement functionality including requirement checking and setup flow.
"""

from unittest.mock import MagicMock, patch


class TestCheck2FARequirement:
    """Test check_2fa_requirement function."""

    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_user_requires_2fa_enabled(self, mock_get_user, mock_get_totp):
        """Test user requires and has 2FA enabled."""
        from src.auth.enforce_2fa import check_2fa_requirement

        # Mock user with 2FA requirement
        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
            "requires_2fa": True,
        }

        # Mock TOTP manager
        mock_totp = MagicMock()
        mock_totp.is_2fa_enabled.return_value = True
        mock_get_totp.return_value = mock_totp

        requires, enabled = check_2fa_requirement("testuser")

        assert requires is True
        assert enabled is True
        mock_totp.is_2fa_enabled.assert_called_once_with("user-123")

    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_user_requires_2fa_not_enabled(self, mock_get_user, mock_get_totp):
        """Test user requires but hasn't enabled 2FA."""
        from src.auth.enforce_2fa import check_2fa_requirement

        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
            "requires_2fa": True,
        }

        mock_totp = MagicMock()
        mock_totp.is_2fa_enabled.return_value = False
        mock_get_totp.return_value = mock_totp

        requires, enabled = check_2fa_requirement("testuser")

        assert requires is True
        assert enabled is False

    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_user_no_2fa_requirement(self, mock_get_user, mock_get_totp):
        """Test user doesn't require 2FA."""
        from src.auth.enforce_2fa import check_2fa_requirement

        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
            "requires_2fa": False,
        }

        mock_totp = MagicMock()
        mock_totp.is_2fa_enabled.return_value = False
        mock_get_totp.return_value = mock_totp

        requires, enabled = check_2fa_requirement("testuser")

        assert requires is False
        assert enabled is False

    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_user_not_found(self, mock_get_user):
        """Test when user doesn't exist."""
        from src.auth.enforce_2fa import check_2fa_requirement

        mock_get_user.return_value = None

        requires, enabled = check_2fa_requirement("nonexistent")

        assert requires is False
        assert enabled is False

    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_exception_handling(self, mock_get_user):
        """Test exception handling in check."""
        from src.auth.enforce_2fa import check_2fa_requirement

        mock_get_user.side_effect = Exception("Database error")

        requires, enabled = check_2fa_requirement("testuser")

        assert requires is False
        assert enabled is False

    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_missing_requires_2fa_field(self, mock_get_user, mock_get_totp):
        """Test user without requires_2fa field defaults to False."""
        from src.auth.enforce_2fa import check_2fa_requirement

        # User without requires_2fa field
        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
        }

        mock_totp = MagicMock()
        mock_totp.is_2fa_enabled.return_value = False
        mock_get_totp.return_value = mock_totp

        requires, enabled = check_2fa_requirement("testuser")

        assert requires is False


class TestRender2FASetupRequired:
    """Test render_2fa_setup_required function."""

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_render_setup_qr_code(self, mock_get_user, mock_get_totp, mock_get_backup, mock_st):
        """Test rendering 2FA setup with QR code."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        # Mock session state
        mock_st.session_state = {"username": "testuser"}

        # Mock user
        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
        }

        # Mock TOTP manager
        mock_totp = MagicMock()
        mock_totp.generate_and_store_secret.return_value = "SECRET123"
        mock_totp.generate_qr_code.return_value = b"qr_code_image"
        mock_get_totp.return_value = mock_totp

        # Mock backup code manager
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_2fa_setup_required()

        # Verify warning shown
        mock_st.warning.assert_called_once()

        # Verify QR code generated
        mock_totp.generate_and_store_secret.assert_called_once_with("user-123")
        mock_totp.generate_qr_code.assert_called_once_with("SECRET123", "testuser")

        # Verify QR code displayed
        mock_st.image.assert_called()

    @patch("src.auth.enforce_2fa.st")
    def test_render_no_username_in_session(self, mock_st):
        """Test rendering when no username in session."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        # No username in session
        mock_st.session_state = {}

        render_2fa_setup_required()

        # Verify error shown
        mock_st.error.assert_called_once()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_render_user_not_found(self, mock_get_user, mock_st):
        """Test rendering when user not found."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        mock_st.session_state = {"username": "testuser"}
        mock_get_user.return_value = None

        render_2fa_setup_required()

        # Verify error shown
        mock_st.error.assert_called()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_render_with_secret_in_session(
        self, mock_get_user, mock_get_totp, mock_get_backup, mock_st
    ):
        """Test rendering when secret already in session (step 2)."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        # Mock session state with existing secret
        mock_session = {"username": "testuser", "2fa_setup_secret": "EXISTING_SECRET"}
        mock_st.session_state = mock_session

        # Create a property mock for get method
        def session_get(key, default=None):
            return mock_session.get(key, default)

        type(mock_st.session_state).get = session_get

        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
        }

        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_2fa_setup_required()

        # Secret generation should be skipped (secret exists)
        # Should not call generate_and_store_secret
        mock_totp.generate_and_store_secret.assert_not_called()


class TestRender2FAVerification:
    """Test render_2fa_verification function if it exists."""

    def test_render_verification_imports(self):
        """Test that module can be imported."""
        import src.auth.enforce_2fa

        # Module should import successfully
        assert hasattr(src.auth.enforce_2fa, "check_2fa_requirement")
        assert hasattr(src.auth.enforce_2fa, "render_2fa_setup_required")


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_totp_manager_exception(self, mock_get_user, mock_get_totp):
        """Test when TOTP manager throws exception."""
        from src.auth.enforce_2fa import check_2fa_requirement

        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
            "requires_2fa": True,
        }

        mock_totp = MagicMock()
        mock_totp.is_2fa_enabled.side_effect = Exception("TOTP error")
        mock_get_totp.return_value = mock_totp

        requires, enabled = check_2fa_requirement("testuser")

        # Should return False, False on exception
        assert requires is False
        assert enabled is False

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_render_exception_in_user_lookup(self, mock_get_user, mock_st):
        """Test render when user lookup throws exception."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        mock_st.session_state = {"username": "testuser"}
        mock_get_user.side_effect = Exception("Database error")

        # Should handle exception gracefully
        render_2fa_setup_required()

    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_user_with_empty_id(self, mock_get_user, mock_get_totp):
        """Test user with empty ID."""
        from src.auth.enforce_2fa import check_2fa_requirement

        mock_get_user.return_value = {
            "id": "",
            "username": "testuser",
            "requires_2fa": True,
        }

        mock_totp = MagicMock()
        mock_totp.is_2fa_enabled.return_value = False
        mock_get_totp.return_value = mock_totp

        requires, enabled = check_2fa_requirement("testuser")

        # Should still work with empty ID
        mock_totp.is_2fa_enabled.assert_called_once_with("")


class TestIntegration:
    """Integration tests for 2FA enforcement flow."""

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_full_setup_flow(self, mock_get_user, mock_get_totp, mock_get_backup, mock_st):
        """Test complete 2FA setup flow."""
        from src.auth.enforce_2fa import check_2fa_requirement, render_2fa_setup_required

        # Step 1: Check requirement
        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
            "requires_2fa": True,
        }

        mock_totp = MagicMock()
        mock_totp.is_2fa_enabled.return_value = False
        mock_get_totp.return_value = mock_totp

        requires, enabled = check_2fa_requirement("testuser")
        assert requires is True
        assert enabled is False

        # Step 2: Render setup UI
        mock_st.session_state = {"username": "testuser"}
        mock_totp.generate_and_store_secret.return_value = "SECRET123"
        mock_totp.generate_qr_code.return_value = b"qr_code"

        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_2fa_setup_required()

        # Verify setup initiated
        mock_totp.generate_and_store_secret.assert_called()


class TestLogging:
    """Test logging functionality."""

    @patch("src.auth.enforce_2fa.logger")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_error_logging(self, mock_get_user, mock_logger):
        """Test that errors are logged."""
        from src.auth.enforce_2fa import check_2fa_requirement

        mock_get_user.side_effect = Exception("Test error")

        check_2fa_requirement("testuser")

        # Verify error was logged
        mock_logger.error.assert_called_once()


class TestMultipleUsers:
    """Test handling multiple users."""

    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_multiple_users_different_requirements(self, mock_get_user, mock_get_totp):
        """Test checking requirements for multiple users."""
        from src.auth.enforce_2fa import check_2fa_requirement

        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp

        # User 1: requires 2FA, has it
        mock_get_user.return_value = {
            "id": "user-1",
            "requires_2fa": True,
        }
        mock_totp.is_2fa_enabled.return_value = True

        requires1, enabled1 = check_2fa_requirement("user1")
        assert requires1 is True
        assert enabled1 is True

        # User 2: doesn't require 2FA
        mock_get_user.return_value = {
            "id": "user-2",
            "requires_2fa": False,
        }
        mock_totp.is_2fa_enabled.return_value = False

        requires2, enabled2 = check_2fa_requirement("user2")
        assert requires2 is False
        assert enabled2 is False

        # User 3: requires 2FA, doesn't have it
        mock_get_user.return_value = {
            "id": "user-3",
            "requires_2fa": True,
        }
        mock_totp.is_2fa_enabled.return_value = False

        requires3, enabled3 = check_2fa_requirement("user3")
        assert requires3 is True
        assert enabled3 is False
