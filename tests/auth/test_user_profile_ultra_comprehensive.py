"""Ultra comprehensive tests for user_profile.py (target: 80%+ coverage)."""

from unittest.mock import MagicMock, patch


class TestGetUserInfo:
    """Test get_user_info() function."""

    def test_get_user_info_success(self):
        from src.auth.user_profile import get_user_info

        mock_user = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "full_name": "Test User",
        }

        with patch("src.auth.user_profile.get_user_by_username") as mock_get_user:
            mock_get_user.return_value = mock_user

            result = get_user_info("test_user")

            assert result == mock_user
            mock_get_user.assert_called_once_with("test_user")

    def test_get_user_info_not_found(self):
        from src.auth.user_profile import get_user_info

        with patch("src.auth.user_profile.get_user_by_username") as mock_get_user:
            mock_get_user.return_value = None

            result = get_user_info("nonexistent")

            assert result is None

    def test_get_user_info_error(self):
        from src.auth.user_profile import get_user_info

        with patch("src.auth.user_profile.get_user_by_username") as mock_get_user:
            mock_get_user.side_effect = Exception("Database error")

            result = get_user_info("test_user")

            assert result is None


class TestChangeUserPassword:
    """Test change_user_password() function."""

    def test_change_user_password_success(self):
        from src.auth.user_profile import change_user_password

        mock_user = {"id": 123, "username": "test_user"}

        with patch("src.auth.user_profile.verify_user_password") as mock_verify:
            mock_verify.return_value = mock_user

            with patch("src.auth.user_profile.update_user_password") as mock_update:
                success, message = change_user_password("test_user", "old_password", "new_password")

                assert success is True
                assert "successfully" in message
                mock_verify.assert_called_once_with("test_user", "old_password")
                mock_update.assert_called_once_with(123, "new_password")

    def test_change_user_password_wrong_current_password(self):
        from src.auth.user_profile import change_user_password

        with patch("src.auth.user_profile.verify_user_password") as mock_verify:
            mock_verify.return_value = None

            success, message = change_user_password("test_user", "wrong_password", "new_password")

            assert success is False
            assert "incorrect" in message

    def test_change_user_password_error(self):
        from src.auth.user_profile import change_user_password

        with patch("src.auth.user_profile.verify_user_password") as mock_verify:
            mock_verify.side_effect = Exception("Database error")

            success, message = change_user_password("test_user", "old_password", "new_password")

            assert success is False
            assert "Failed" in message


class TestRenderUserProfile:
    """Test render_user_profile() function."""

    @patch("streamlit.sidebar")
    def test_render_user_profile_success(self, mock_sidebar):
        from src.auth.user_profile import render_user_profile

        mock_user = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_email_verified": True,
            "email_verified_at": "2025-01-01T12:00:00",
            "created_at": "2024-01-01T00:00:00",
            "last_login_at": "2025-10-28T10:00:00",
        }

        with patch("src.auth.user_profile.get_user_info") as mock_get_user:
            mock_get_user.return_value = mock_user

            with patch("streamlit.sidebar.markdown") as mock_markdown:
                with patch("streamlit.sidebar.expander") as mock_expander:
                    mock_expander_context = MagicMock()
                    mock_expander.return_value.__enter__.return_value = mock_expander_context

                    render_user_profile("test_user")

                    mock_get_user.assert_called_once_with("test_user")
                    mock_expander.assert_called()

    @patch("streamlit.sidebar")
    def test_render_user_profile_user_not_found(self, mock_sidebar):
        from src.auth.user_profile import render_user_profile

        with patch("src.auth.user_profile.get_user_info") as mock_get_user:
            mock_get_user.return_value = None

            with patch("streamlit.sidebar.error") as mock_error:
                render_user_profile("test_user")

                mock_error.assert_called_once()

    @patch("streamlit.sidebar")
    def test_render_user_profile_unverified_email(self, mock_sidebar):
        from src.auth.user_profile import render_user_profile

        mock_user = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_email_verified": False,
            "email_verified_at": None,
            "created_at": "2024-01-01T00:00:00",
            "last_login_at": "2025-10-28T10:00:00",
        }

        with patch("src.auth.user_profile.get_user_info") as mock_get_user:
            mock_get_user.return_value = mock_user

            with patch("streamlit.sidebar.markdown"):
                with patch("streamlit.sidebar.expander") as mock_expander:
                    mock_expander_context = MagicMock()
                    mock_expander.return_value.__enter__.return_value = mock_expander_context

                    with patch("streamlit.markdown") as mock_markdown:
                        with patch("streamlit.warning") as mock_warning:
                            with patch("streamlit.button") as mock_button:
                                mock_button.return_value = False

                                render_user_profile("test_user")

                                mock_warning.assert_called()

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state")
    def test_render_user_profile_change_password(self, mock_session_state, mock_sidebar):
        from src.auth.user_profile import render_user_profile

        mock_user = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_email_verified": True,
            "created_at": "2024-01-01T00:00:00",
            "last_login_at": "2025-10-28T10:00:00",
        }

        session_dict = {"change_password_inputs": {"current": "", "new": "", "confirm": ""}}
        mock_session_state.__contains__ = lambda self, key: key in session_dict
        mock_session_state.__getitem__ = lambda self, key: session_dict[key]
        mock_session_state.__setitem__ = lambda self, key, value: session_dict.__setitem__(
            key, value
        )

        with patch("src.auth.user_profile.get_user_info") as mock_get_user:
            mock_get_user.return_value = mock_user

            with patch("streamlit.sidebar.markdown"):
                with patch("streamlit.sidebar.expander") as mock_expander:
                    mock_expander_context = MagicMock()
                    mock_expander.return_value.__enter__.return_value = mock_expander_context

                    with patch("streamlit.text_input") as mock_text_input:
                        mock_text_input.side_effect = [
                            "current_pass",
                            "new_pass",
                            "new_pass",
                        ]

                        with patch("streamlit.button") as mock_button:
                            mock_button.return_value = True

                            with patch(
                                "src.auth.user_profile.is_password_strong"
                            ) as mock_is_strong:
                                mock_is_strong.return_value = (True, "")

                                with patch(
                                    "src.auth.user_profile.change_user_password"
                                ) as mock_change:
                                    mock_change.return_value = (True, "Success")

                                    with patch("streamlit.success") as mock_success:
                                        with patch("streamlit.rerun") as mock_rerun:
                                            render_user_profile("test_user")

                                            mock_change.assert_called()

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state")
    def test_render_user_profile_change_password_mismatch(self, mock_session_state, mock_sidebar):
        from src.auth.user_profile import render_user_profile

        mock_user = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_email_verified": True,
            "created_at": "2024-01-01T00:00:00",
        }

        session_dict = {"change_password_inputs": {"current": "", "new": "", "confirm": ""}}
        mock_session_state.__contains__ = lambda self, key: key in session_dict
        mock_session_state.__getitem__ = lambda self, key: session_dict[key]

        with patch("src.auth.user_profile.get_user_info") as mock_get_user:
            mock_get_user.return_value = mock_user

            with patch("streamlit.sidebar.markdown"):
                with patch("streamlit.sidebar.expander") as mock_expander:
                    mock_expander_context = MagicMock()
                    mock_expander.return_value.__enter__.return_value = mock_expander_context

                    with patch("streamlit.text_input") as mock_text_input:
                        mock_text_input.side_effect = [
                            "current_pass",
                            "new_pass",
                            "different_pass",
                        ]

                        with patch("streamlit.button") as mock_button:
                            mock_button.return_value = True

                            with patch("streamlit.error") as mock_error:
                                render_user_profile("test_user")

                                mock_error.assert_called()

    @patch("streamlit.sidebar")
    def test_render_user_profile_active_sessions(self, mock_sidebar):
        from src.auth.user_profile import render_user_profile

        mock_user = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_email_verified": True,
            "created_at": "2024-01-01T00:00:00",
        }

        mock_sessions = [
            {
                "id": 1,
                "session_token": "token1",
                "created_at": "2025-10-28T09:00:00",
                "last_activity_at": "2025-10-28T10:00:00",
                "session_type": "web",
                "ip_address": "192.168.1.1",
            },
            {
                "id": 2,
                "session_token": "token2",
                "created_at": "2025-10-27T09:00:00",
                "last_activity_at": "2025-10-28T09:00:00",
                "session_type": "api",
                "ip_address": "192.168.1.2",
            },
        ]

        with patch("src.auth.user_profile.get_user_info") as mock_get_user:
            mock_get_user.return_value = mock_user

            with patch("src.auth.user_profile.get_user_sessions") as mock_get_sessions:
                mock_get_sessions.return_value = mock_sessions

                with patch("streamlit.sidebar.markdown"):
                    with patch("streamlit.sidebar.expander") as mock_expander:
                        mock_expander_context = MagicMock()
                        mock_expander.return_value.__enter__.return_value = mock_expander_context

                        with patch("streamlit.markdown"):
                            with patch("streamlit.text"):
                                with patch("streamlit.button") as mock_button:
                                    mock_button.return_value = False

                                    render_user_profile("test_user")

                                    mock_get_sessions.assert_called_once()

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state")
    def test_render_user_profile_revoke_session(self, mock_session_state, mock_sidebar):
        from src.auth.user_profile import render_user_profile

        mock_user = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_email_verified": True,
            "created_at": "2024-01-01T00:00:00",
        }

        mock_sessions = [
            {
                "id": 1,
                "session_token": "token1",
                "created_at": "2025-10-28T09:00:00",
                "last_activity_at": "2025-10-28T10:00:00",
                "session_type": "web",
                "ip_address": "192.168.1.1",
            }
        ]

        with patch("src.auth.user_profile.get_user_info") as mock_get_user:
            mock_get_user.return_value = mock_user

            with patch("src.auth.user_profile.get_user_sessions") as mock_get_sessions:
                mock_get_sessions.return_value = mock_sessions

                with patch("streamlit.sidebar.markdown"):
                    with patch("streamlit.sidebar.expander") as mock_expander:
                        mock_expander_context = MagicMock()
                        mock_expander.return_value.__enter__.return_value = mock_expander_context

                        with patch("streamlit.markdown"):
                            with patch("streamlit.text"):
                                with patch("streamlit.button") as mock_button:
                                    mock_button.return_value = True

                                    with patch(
                                        "src.auth.user_profile.revoke_session"
                                    ) as mock_revoke:
                                        mock_revoke.return_value = True

                                        with patch("streamlit.success") as mock_success:
                                            with patch("streamlit.rerun") as mock_rerun:
                                                render_user_profile("test_user")

                                                mock_revoke.assert_called_once()

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state")
    def test_render_user_profile_revoke_all_sessions(self, mock_session_state, mock_sidebar):
        from src.auth.user_profile import render_user_profile

        mock_user = {
            "id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_email_verified": True,
            "created_at": "2024-01-01T00:00:00",
        }

        mock_sessions = [
            {
                "id": 1,
                "session_token": "token1",
                "created_at": "2025-10-28T09:00:00",
                "last_activity_at": "2025-10-28T10:00:00",
                "session_type": "web",
                "ip_address": "192.168.1.1",
            },
            {
                "id": 2,
                "session_token": "token2",
                "created_at": "2025-10-27T09:00:00",
                "last_activity_at": "2025-10-28T09:00:00",
                "session_type": "web",
                "ip_address": "192.168.1.2",
            },
        ]

        session_dict = {"confirm_revoke_all": True}
        mock_session_state.__contains__ = lambda self, key: key in session_dict
        mock_session_state.__delitem__ = lambda self, key: session_dict.pop(key, None)
        mock_session_state.clear = lambda: session_dict.clear()

        with patch("src.auth.user_profile.get_user_info") as mock_get_user:
            mock_get_user.return_value = mock_user

            with patch("src.auth.user_profile.get_user_sessions") as mock_get_sessions:
                mock_get_sessions.return_value = mock_sessions

                with patch("streamlit.sidebar.markdown"):
                    with patch("streamlit.sidebar.expander") as mock_expander:
                        mock_expander_context = MagicMock()
                        mock_expander.return_value.__enter__.return_value = mock_expander_context

                        with patch("streamlit.markdown"):
                            with patch("streamlit.text"):
                                with patch("streamlit.button") as mock_button:
                                    # First call returns False for individual revoke
                                    # Last call returns True for revoke all
                                    mock_button.side_effect = [False, False, True]

                                    with patch(
                                        "src.auth.user_profile.revoke_all_user_sessions"
                                    ) as mock_revoke_all:
                                        mock_revoke_all.return_value = 2

                                        with patch("streamlit.success") as mock_success:
                                            with patch("streamlit.info") as mock_info:
                                                with patch("streamlit.rerun") as mock_rerun:
                                                    render_user_profile("test_user")

                                                    mock_revoke_all.assert_called_once()

    @patch("streamlit.sidebar")
    def test_render_user_profile_error(self, mock_sidebar):
        from src.auth.user_profile import render_user_profile

        with patch("src.auth.user_profile.get_user_info") as mock_get_user:
            mock_get_user.side_effect = Exception("Unexpected error")

            with patch("streamlit.sidebar.error") as mock_error:
                render_user_profile("test_user")

                mock_error.assert_called_once()


class TestRenderUserProfileSimple:
    """Test render_user_profile_simple() function."""

    @patch("streamlit.sidebar")
    def test_render_user_profile_simple_with_email(self, mock_sidebar):
        from src.auth.user_profile import render_user_profile_simple

        with patch("streamlit.sidebar.markdown") as mock_markdown:
            with patch("streamlit.sidebar.expander") as mock_expander:
                mock_expander_context = MagicMock()
                mock_expander.return_value.__enter__.return_value = mock_expander_context

                with patch("streamlit.markdown") as mock_markdown_inner:
                    with patch("streamlit.info") as mock_info:
                        render_user_profile_simple("test_user", "Test User", "test@example.com")

                        assert mock_markdown.call_count >= 2  # Title + divider
                        mock_info.assert_called_once()

    @patch("streamlit.sidebar")
    def test_render_user_profile_simple_without_email(self, mock_sidebar):
        from src.auth.user_profile import render_user_profile_simple

        with patch("streamlit.sidebar.markdown") as mock_markdown:
            with patch("streamlit.sidebar.expander") as mock_expander:
                mock_expander_context = MagicMock()
                mock_expander.return_value.__enter__.return_value = mock_expander_context

                with patch("streamlit.markdown") as mock_markdown_inner:
                    with patch("streamlit.info") as mock_info:
                        render_user_profile_simple("test_user", "Test User")

                        assert mock_markdown.call_count >= 2
                        mock_info.assert_called_once()
