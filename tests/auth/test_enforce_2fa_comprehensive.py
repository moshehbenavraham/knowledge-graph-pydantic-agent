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

        requires, _enabled = check_2fa_requirement("testuser")

        assert requires is False


class TestRender2FASetupRequired:
    """Test render_2fa_setup_required function."""

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_render_setup_qr_code(self, mock_get_user, mock_get_totp, mock_get_backup, mock_st):
        """Test rendering 2FA setup with QR code."""
        import base64

        from src.auth.enforce_2fa import render_2fa_setup_required

        # Mock session state as dict-like object
        mock_session_dict = {"username": "testuser"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__getitem__.side_effect = lambda key: mock_session_dict[key]
        mock_session.__contains__.side_effect = lambda key: key in mock_session_dict
        mock_session.__setitem__.side_effect = lambda key, value: mock_session_dict.__setitem__(
            key, value
        )
        mock_st.session_state = mock_session

        # Mock user
        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
        }

        # Mock TOTP manager - setup_2fa returns dict with secret and qr_code
        mock_totp = MagicMock()
        # qr_code is base64-encoded PNG
        qr_code_base64 = base64.b64encode(b"qr_code_image").decode()
        mock_totp.setup_2fa.return_value = {"secret": "SECRET123", "qr_code": qr_code_base64}
        mock_get_totp.return_value = mock_totp

        # Mock backup code manager
        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_2fa_setup_required()

        # Verify warning shown
        mock_st.warning.assert_called_once()

        # Verify setup_2fa called
        mock_totp.setup_2fa.assert_called_once_with("user-123", "testuser")

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
        # Mock session state with existing secret
        from unittest.mock import MagicMock

        from src.auth.enforce_2fa import render_2fa_setup_required

        mock_session_dict = {"username": "testuser", "2fa_setup_secret": "EXISTING_SECRET"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__getitem__.side_effect = lambda key: mock_session_dict[key]
        mock_session.__contains__.side_effect = lambda key: key in mock_session_dict
        mock_st.session_state = mock_session

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

        _requires, _enabled = check_2fa_requirement("testuser")

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
        import base64

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

        # Step 2: Render setup UI with proper session mock
        mock_session_dict = {"username": "testuser"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__getitem__.side_effect = lambda key: mock_session_dict[key]
        mock_session.__contains__.side_effect = lambda key: key in mock_session_dict
        mock_session.__setitem__.side_effect = lambda key, value: mock_session_dict.__setitem__(
            key, value
        )
        mock_st.session_state = mock_session

        # Mock setup_2fa return
        qr_code_base64 = base64.b64encode(b"qr_code").decode()
        mock_totp.setup_2fa.return_value = {"secret": "SECRET123", "qr_code": qr_code_base64}

        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        render_2fa_setup_required()

        # Verify setup initiated
        mock_totp.setup_2fa.assert_called()


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


class TestRender2FASetupVerification:
    """Test 2FA setup verification flow."""

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_valid_verification_code(self, mock_get_user, mock_get_totp, mock_get_backup, mock_st):
        """Test successful 2FA verification during setup."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        mock_session_dict = {"username": "testuser", "2fa_setup_secret": "SECRET123"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__getitem__.side_effect = lambda key: mock_session_dict[key]
        mock_session.__contains__.side_effect = lambda key: key in mock_session_dict
        mock_session.pop = MagicMock()
        mock_session.__setitem__ = MagicMock()
        mock_st.session_state = mock_session

        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
        }

        mock_totp = MagicMock()
        # verify_and_enable_2fa combines verify and enable
        mock_totp.verify_and_enable_2fa.return_value = True
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        # create_backup_codes is the actual method name
        mock_backup.create_backup_codes.return_value = ["CODE1", "CODE2", "CODE3"]
        mock_get_backup.return_value = mock_backup

        # Mock text_input to return valid code
        mock_st.text_input.return_value = "123456"
        mock_st.button.side_effect = [True, False]  # Verify button clicked

        # Mock columns
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        render_2fa_setup_required()

        # Verify 2FA was enabled using the combined method
        mock_totp.verify_and_enable_2fa.assert_called_once()
        mock_backup.create_backup_codes.assert_called_once()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_invalid_verification_code(self, mock_get_user, mock_get_totp, mock_st):
        """Test invalid verification code during setup."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        mock_session_dict = {"username": "testuser", "2fa_setup_secret": "SECRET123"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__getitem__.side_effect = lambda key: mock_session_dict[key]
        mock_session.__contains__.side_effect = lambda key: key in mock_session_dict
        mock_st.session_state = mock_session

        mock_get_user.return_value = {
            "id": "user-123",
            "username": "testuser",
        }

        mock_totp = MagicMock()
        mock_totp.verify_totp.return_value = False
        mock_get_totp.return_value = mock_totp

        mock_st.text_input.return_value = "999999"
        mock_st.button.side_effect = [True]

        # Mock columns
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        render_2fa_setup_required()

        # Verify error was shown
        mock_st.error.assert_called()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_empty_verification_code(self, mock_get_user, mock_get_totp, mock_st):
        """Test empty verification code during setup."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        mock_session_dict = {"username": "testuser", "2fa_setup_secret": "SECRET123"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__getitem__.side_effect = lambda key: key in mock_session_dict
        mock_session.__contains__.side_effect = lambda key: key in mock_session_dict
        mock_st.session_state = mock_session

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp

        mock_st.text_input.return_value = ""
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        render_2fa_setup_required()

        # Verify error for invalid code
        assert mock_st.error.called

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_enable_2fa_fails(self, mock_get_user, mock_get_totp, mock_st):
        """Test when enable_2fa returns False."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        mock_session_dict = {"username": "testuser", "2fa_setup_secret": "SECRET123"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__getitem__.side_effect = lambda key: mock_session_dict[key]
        mock_session.__contains__.side_effect = lambda key: key in mock_session_dict
        mock_st.session_state = mock_session

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        mock_totp.verify_totp.return_value = True
        mock_totp.enable_2fa.return_value = False
        mock_get_totp.return_value = mock_totp

        mock_st.text_input.return_value = "123456"
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        render_2fa_setup_required()

        # Verify error shown
        mock_st.error.assert_called()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_exception(self, mock_get_user, mock_get_totp, mock_st):
        """Test exception during verification."""
        from src.auth.enforce_2fa import render_2fa_setup_required

        mock_session_dict = {"username": "testuser", "2fa_setup_secret": "SECRET123"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__getitem__.side_effect = lambda key: mock_session_dict[key]
        mock_session.__contains__.side_effect = lambda key: key in mock_session_dict
        mock_st.session_state = mock_session

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        mock_totp.verify_totp.side_effect = Exception("Verification error")
        mock_get_totp.return_value = mock_totp

        mock_st.text_input.return_value = "123456"
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        render_2fa_setup_required()

        # Verify error shown
        assert mock_st.error.called


class TestRender2FAVerificationFlow:
    """Test 2FA verification during login."""

    @patch("src.auth.enforce_2fa.st")
    def test_verification_no_username(self, mock_st):
        """Test verification with no username in session."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_st.session_state = {}

        result = render_2fa_verification()

        assert result is False
        mock_st.error.assert_called()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_user_not_found(self, mock_get_user, mock_st):
        """Test verification when user not found."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_st.session_state = {"username": "testuser"}
        mock_get_user.return_value = None

        result = render_2fa_verification()

        assert result is False
        mock_st.error.assert_called()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_valid_totp_code(
        self, mock_get_user, mock_get_backup, mock_get_totp, mock_st
    ):
        """Test successful TOTP verification."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_session_dict = {"username": "testuser"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__setitem__ = MagicMock()
        mock_st.session_state = mock_session

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        # The actual method is verify_login_code
        mock_totp.verify_login_code.return_value = True
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        mock_st.text_input.return_value = "123456"
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        result = render_2fa_verification()

        assert result is True
        mock_totp.verify_login_code.assert_called_once()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_invalid_totp_code(
        self, mock_get_user, mock_get_backup, mock_get_totp, mock_st
    ):
        """Test invalid TOTP verification."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_session_dict = {"username": "testuser"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_st.session_state = mock_session

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        mock_totp.verify_login_code.return_value = False
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        mock_st.text_input.return_value = "999999"
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        result = render_2fa_verification()

        assert result is False

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_valid_backup_code(
        self, mock_get_user, mock_get_totp, mock_get_backup, mock_st
    ):
        """Test successful backup code verification."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_session_dict = {"username": "testuser"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_session.__setitem__ = MagicMock()
        mock_st.session_state = mock_session

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        # The actual method is verify_and_use_backup_code
        mock_backup.verify_and_use_backup_code.return_value = True
        mock_get_backup.return_value = mock_backup

        # Input should be 8 characters for backup code
        mock_st.text_input.return_value = "ABCDEFGH"
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        result = render_2fa_verification()

        assert result is True
        mock_backup.verify_and_use_backup_code.assert_called_once()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_invalid_backup_code(
        self, mock_get_user, mock_get_totp, mock_get_backup, mock_st
    ):
        """Test invalid backup code verification."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_session_dict = {"username": "testuser"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_st.session_state = mock_session

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        # The actual method is verify_and_use_backup_code
        mock_backup.verify_and_use_backup_code.return_value = False
        mock_get_backup.return_value = mock_backup

        # Input should be 8 characters for backup code (without dash)
        mock_st.text_input.return_value = "XXXXYYYY"
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        result = render_2fa_verification()

        assert result is False

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_empty_code(self, mock_get_user, mock_get_backup, mock_get_totp, mock_st):
        """Test empty verification code."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_st.session_state = {"username": "testuser"}
        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        mock_st.text_input.return_value = ""
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        result = render_2fa_verification()

        assert result is False

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_invalid_format(
        self, mock_get_user, mock_get_backup, mock_get_totp, mock_st
    ):
        """Test invalid code format."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_st.session_state = {"username": "testuser"}
        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        mock_st.text_input.return_value = "ABC"
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        result = render_2fa_verification()

        assert result is False

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_exception(self, mock_get_user, mock_get_totp, mock_get_backup, mock_st):
        """Test exception during verification."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_session_dict = {"username": "testuser"}
        mock_session = MagicMock()
        mock_session.get.side_effect = lambda key, default=None: mock_session_dict.get(key, default)
        mock_st.session_state = mock_session

        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        # The actual method is verify_login_code
        mock_totp.verify_login_code.side_effect = Exception("Verification error")
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        mock_st.text_input.return_value = "123456"
        mock_st.button.side_effect = [True]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        result = render_2fa_verification()

        assert result is False

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_totp_manager")
    @patch("src.auth.enforce_2fa.get_backup_code_manager")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_no_button_click(
        self, mock_get_user, mock_get_backup, mock_get_totp, mock_st
    ):
        """Test verification form display without button click."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_st.session_state = {"username": "testuser"}
        mock_get_user.return_value = {"id": "user-123", "username": "testuser"}

        mock_totp = MagicMock()
        mock_get_totp.return_value = mock_totp

        mock_backup = MagicMock()
        mock_get_backup.return_value = mock_backup

        mock_st.text_input.return_value = "123456"
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        result = render_2fa_verification()

        assert result is False

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.get_user_by_username")
    def test_verification_exception_in_outer_try(self, mock_get_user, mock_st):
        """Test exception in outer try block."""
        from src.auth.enforce_2fa import render_2fa_verification

        mock_st.session_state = {"username": "testuser"}
        mock_get_user.side_effect = Exception("Database error")

        result = render_2fa_verification()

        assert result is False


class TestEnforce2FAIfRequired:
    """Test enforce_2fa_if_required function."""

    @patch("src.auth.enforce_2fa.check_2fa_requirement")
    def test_enforce_no_2fa_required(self, mock_check):
        """Test when user doesn't require 2FA."""
        from src.auth.enforce_2fa import enforce_2fa_if_required

        mock_check.return_value = (False, False)

        result = enforce_2fa_if_required("testuser")

        assert result is True

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.render_2fa_setup_required")
    @patch("src.auth.enforce_2fa.check_2fa_requirement")
    def test_enforce_2fa_required_not_enabled(self, mock_check, mock_render_setup, mock_st):
        """Test when 2FA required but not enabled."""
        from src.auth.enforce_2fa import enforce_2fa_if_required

        mock_check.return_value = (True, False)
        mock_st.session_state = {}

        result = enforce_2fa_if_required("testuser")

        assert result is False
        mock_render_setup.assert_called_once()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.check_2fa_requirement")
    def test_enforce_2fa_already_verified(self, mock_check, mock_st):
        """Test when 2FA already verified in session."""
        from src.auth.enforce_2fa import enforce_2fa_if_required

        mock_check.return_value = (True, True)
        mock_st.session_state = {"2fa_verified": True}

        result = enforce_2fa_if_required("testuser")

        assert result is True

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.render_2fa_verification")
    @patch("src.auth.enforce_2fa.check_2fa_requirement")
    def test_enforce_2fa_verification_needed(self, mock_check, mock_render_verify, mock_st):
        """Test when 2FA verification needed."""
        from src.auth.enforce_2fa import enforce_2fa_if_required

        mock_check.return_value = (True, True)
        mock_st.session_state = {}
        mock_render_verify.return_value = False

        result = enforce_2fa_if_required("testuser")

        assert result is False
        mock_render_verify.assert_called_once()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.render_2fa_verification")
    @patch("src.auth.enforce_2fa.check_2fa_requirement")
    def test_enforce_2fa_verification_successful(self, mock_check, mock_render_verify, mock_st):
        """Test successful 2FA verification triggers rerun."""
        from src.auth.enforce_2fa import enforce_2fa_if_required

        mock_check.return_value = (True, True)
        mock_st.session_state = {}
        mock_render_verify.return_value = True

        result = enforce_2fa_if_required("testuser")

        # Function returns False because st.rerun() is called
        assert result is False
        mock_st.rerun.assert_called_once()

    @patch("src.auth.enforce_2fa.st")
    @patch("src.auth.enforce_2fa.check_2fa_requirement")
    def test_enforce_exception_handling(self, mock_check, mock_st):
        """Test exception handling in enforcement."""
        from src.auth.enforce_2fa import enforce_2fa_if_required

        mock_check.side_effect = Exception("Check failed")

        result = enforce_2fa_if_required("testuser")

        assert result is False
        mock_st.error.assert_called()
