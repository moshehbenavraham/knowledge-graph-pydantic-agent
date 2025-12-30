"""Comprehensive tests for Streamlit authentication module.

Tests authentication flow, session management, OAuth integration, password reset,
and database/YAML backend switching.
Target coverage: 70%+ (up from 45.22%)
"""

from unittest.mock import Mock, patch

import pytest
import streamlit as st
import yaml

from src.auth.streamlit_auth import (
    check_oauth_callback,
    create_db_session,
    get_authenticator,
    get_github_oauth_enabled,
    get_google_oauth_enabled,
    get_oauth_enabled,
    get_use_database_auth,
    handle_oauth_callback,
    initiate_oauth_login,
    load_auth_config,
    load_credentials_from_database,
    render_login_page,
    render_logout_button,
    render_oauth_buttons,
    require_authentication,
    revoke_db_session,
)


class TestGetSettings:
    """Test settings getter functions."""

    @patch("src.auth.streamlit_auth.get_settings")
    def test_get_use_database_auth_true(self, mock_settings):
        """Test get_use_database_auth when True."""
        mock_settings.return_value.use_database_auth = True
        assert get_use_database_auth() is True

    @patch("src.auth.streamlit_auth.get_settings")
    def test_get_use_database_auth_false(self, mock_settings):
        """Test get_use_database_auth when False."""
        mock_settings.return_value.use_database_auth = False
        assert get_use_database_auth() is False

    @patch("src.auth.streamlit_auth.get_settings")
    def test_get_oauth_enabled_true(self, mock_settings):
        """Test get_oauth_enabled when True."""
        mock_settings.return_value.oauth_enabled = True
        assert get_oauth_enabled() is True

    @patch("src.auth.streamlit_auth.get_settings")
    def test_get_oauth_enabled_false(self, mock_settings):
        """Test get_oauth_enabled when False."""
        mock_settings.return_value.oauth_enabled = False
        assert get_oauth_enabled() is False

    @patch("src.auth.streamlit_auth.get_settings")
    def test_get_google_oauth_enabled_with_credentials(self, mock_settings):
        """Test Google OAuth enabled when credentials exist."""
        mock_settings.return_value.google_client_id = "test_id"
        mock_settings.return_value.google_client_secret = "test_secret"
        assert get_google_oauth_enabled() is True

    @patch("src.auth.streamlit_auth.get_settings")
    def test_get_google_oauth_enabled_missing_credentials(self, mock_settings):
        """Test Google OAuth disabled when credentials missing."""
        mock_settings.return_value.google_client_id = None
        mock_settings.return_value.google_client_secret = None
        assert get_google_oauth_enabled() is False

    @patch("src.auth.streamlit_auth.get_settings")
    def test_get_github_oauth_enabled_with_credentials(self, mock_settings):
        """Test GitHub OAuth enabled when credentials exist."""
        mock_settings.return_value.github_client_id = "test_id"
        mock_settings.return_value.github_client_secret = "test_secret"
        assert get_github_oauth_enabled() is True

    @patch("src.auth.streamlit_auth.get_settings")
    def test_get_github_oauth_enabled_missing_credentials(self, mock_settings):
        """Test GitHub OAuth disabled when credentials missing."""
        mock_settings.return_value.github_client_id = None
        mock_settings.return_value.github_client_secret = None
        assert get_github_oauth_enabled() is False


@pytest.mark.asyncio
class TestLoadCredentialsFromDatabase:
    """Test load_credentials_from_database() async function."""

    async def test_load_credentials_from_database_success(self):
        """Test successful credential loading from database."""
        mock_users = [
            {
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "is_active": True,
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "full_name": "User Two",
                "is_active": True,
            },
        ]

        with patch("src.auth.db.list_users", return_value=mock_users):
            with patch("src.clients.database.get_supabase_client") as mock_client:
                mock_table = Mock()
                mock_result = Mock()
                mock_result.data = [{"password_hash": "hash1"}]
                mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                    mock_result
                )
                mock_client.return_value.table.return_value = mock_table

                credentials = await load_credentials_from_database()

        assert "usernames" in credentials
        assert "user1" in credentials["usernames"]
        assert credentials["usernames"]["user1"]["email"] == "user1@example.com"

    async def test_load_credentials_filters_inactive_users(self):
        """Test that inactive users are filtered out."""
        mock_users = [
            {
                "username": "active",
                "is_active": True,
                "email": "active@test.com",
                "full_name": "Active",
            },
            {
                "username": "inactive",
                "is_active": False,
                "email": "inactive@test.com",
                "full_name": "Inactive",
            },
        ]

        with patch("src.auth.db.list_users", return_value=mock_users):
            with patch("src.clients.database.get_supabase_client") as mock_client:
                mock_table = Mock()
                mock_result = Mock()
                mock_result.data = [{"password_hash": "hash"}]
                mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                    mock_result
                )
                mock_client.return_value.table.return_value = mock_table

                credentials = await load_credentials_from_database()

        assert "active" in credentials["usernames"]
        assert "inactive" not in credentials["usernames"]

    async def test_load_credentials_handles_database_error(self):
        """Test handling of database error."""
        with patch("src.auth.db.list_users", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                await load_credentials_from_database()


class TestLoadAuthConfig:
    """Test load_auth_config() function."""

    def test_load_auth_config_yaml_mode(self, tmp_path):
        """Test loading config in YAML mode."""
        config_file = tmp_path / "auth_config.yaml"
        config_data = {
            "credentials": {
                "usernames": {
                    "user1": {"email": "user1@test.com", "name": "User One", "password": "hash"}
                }
            },
            "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
            "preauthorized": {"emails": []},
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("src.auth.streamlit_auth.get_settings") as mock_settings:
            mock_settings.return_value.use_database_auth = False

            config = load_auth_config(str(config_file))

        assert "credentials" in config
        assert "user1" in config["credentials"]["usernames"]

    def test_load_auth_config_database_mode(self):
        """Test loading config in database mode."""
        mock_credentials = {
            "usernames": {
                "user1": {"email": "user1@test.com", "name": "User One", "password": "hash"}
            }
        }

        with patch("src.auth.streamlit_auth.get_settings") as mock_settings:
            mock_settings.return_value.use_database_auth = True
            mock_settings.return_value.auth_cookie_key = "test_key"

            with patch("pathlib.Path.exists", return_value=False):
                # Mock the async credential loader directly to avoid database connection
                with patch(
                    "src.auth.streamlit_auth.load_credentials_from_database",
                    return_value=mock_credentials,
                ):
                    with patch(
                        "src.auth.streamlit_auth.asyncio.run", return_value=mock_credentials
                    ):
                        config = load_auth_config()

        assert "credentials" in config
        assert "user1" in config["credentials"]["usernames"]

    def test_load_auth_config_file_not_found_yaml_mode(self):
        """Test error when config file missing in YAML mode."""
        with patch("src.auth.streamlit_auth.get_settings") as mock_settings:
            mock_settings.return_value.use_database_auth = False

            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(FileNotFoundError):
                    load_auth_config("nonexistent.yaml")

    def test_load_auth_config_database_mode_with_fallback(self, tmp_path):
        """Test fallback to YAML when database fails."""
        config_file = tmp_path / "auth_config.yaml"
        config_data = {
            "credentials": {"usernames": {"user1": {}}},
            "cookie": {"name": "test", "key": "key", "expiry_days": 30},
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("src.auth.streamlit_auth.get_settings") as mock_settings:
            mock_settings.return_value.use_database_auth = True

            with patch("src.auth.streamlit_auth.asyncio.run", side_effect=Exception("DB error")):
                config = load_auth_config(str(config_file))

        # Should fall back to YAML credentials
        assert "credentials" in config


class TestGetAuthenticator:
    """Test get_authenticator() function."""

    def test_get_authenticator_with_config(self):
        """Test getting authenticator with provided config."""
        config = {
            "credentials": {"usernames": {}},
            "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
            "preauthorized": {"emails": []},
        }

        with patch("src.auth.streamlit_auth.stauth.Authenticate") as mock_auth:
            get_authenticator(config)

            mock_auth.assert_called_once()

    def test_get_authenticator_loads_config(self):
        """Test that authenticator loads config if not provided."""
        with patch("src.auth.streamlit_auth.load_auth_config") as mock_load:
            mock_load.return_value = {
                "credentials": {"usernames": {}},
                "cookie": {"name": "test", "key": "key", "expiry_days": 30},
                "preauthorized": {"emails": []},
            }

            with patch("src.auth.streamlit_auth.stauth.Authenticate"):
                get_authenticator()

            mock_load.assert_called_once()


class MockSessionState(dict):
    """Mock session state that supports both dict-like and attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"No attribute {name}")

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(f"No attribute {name}")


class TestRenderLoginPage:
    """Test render_login_page() function."""

    @patch("streamlit.markdown")
    @patch("streamlit.info")
    @patch("streamlit.warning")
    @patch("streamlit.checkbox")
    def test_render_login_page_initial_state(
        self, mock_checkbox, mock_warning, mock_info, mock_markdown
    ):
        """Test login page renders in initial state."""
        mock_checkbox.return_value = False

        # Create a mock session_state that supports both dict and attribute access
        mock_session_state = MockSessionState({"authentication_status": None})

        with patch("src.auth.streamlit_auth.load_auth_config") as mock_load:
            mock_load.return_value = {
                "credentials": {"usernames": {}},
                "cookie": {"name": "test", "key": "key", "expiry_days": 30},
            }

            with patch("src.auth.streamlit_auth.get_authenticator") as mock_get_auth:
                mock_auth = Mock()
                mock_auth.login = Mock()
                mock_get_auth.return_value = mock_auth

                with patch.object(st, "session_state", mock_session_state):
                    _name, _username, auth_status = render_login_page()

        assert auth_status is None

    @patch("streamlit.error")
    def test_render_login_page_failed_login(self, mock_error):
        """Test login page shows error on failed login."""
        # Create a mock session_state that supports both dict and attribute access
        mock_session_state = MockSessionState(
            {
                "authentication_status": False,
                "username": "testuser",
                "auth_config": {
                    "credentials": {"usernames": {}},
                    "cookie": {"name": "test", "key": "key", "expiry_days": 30},
                },
            }
        )

        with patch("src.auth.streamlit_auth.get_rate_limiter") as mock_rate_limiter:
            mock_limiter = Mock()
            mock_limiter.is_locked_out.return_value = (False, 0)
            mock_limiter.get_remaining_attempts.return_value = 3
            mock_rate_limiter.return_value = mock_limiter

            with patch("src.auth.streamlit_auth.load_auth_config"):
                with patch("src.auth.streamlit_auth.get_authenticator"):
                    with patch("streamlit.checkbox"):
                        with patch("streamlit.markdown"):
                            with patch("streamlit.info"):
                                with patch("streamlit.warning"):
                                    with patch("src.auth.streamlit_auth.asyncio.run"):
                                        with patch.object(st, "session_state", mock_session_state):
                                            render_login_page()

        mock_error.assert_called()


class TestRenderLogoutButton:
    """Test render_logout_button() function."""

    @patch("streamlit.sidebar")
    @patch("streamlit.markdown")
    @patch("streamlit.button")
    def test_render_logout_button_displays(self, mock_button, mock_markdown, mock_sidebar):
        """Test that logout button is displayed."""
        mock_button.return_value = False
        mock_auth = Mock()

        render_logout_button(mock_auth, "Test User")

        assert mock_button.called

    @patch("streamlit.sidebar")
    @patch("streamlit.markdown")
    @patch("streamlit.button")
    @patch("streamlit.rerun")
    def test_render_logout_button_click(self, mock_rerun, mock_button, mock_markdown, mock_sidebar):
        """Test logout button click triggers logout."""
        mock_button.return_value = True
        mock_auth = Mock()

        # Create proper mock session state
        mock_session = {"username": "testuser", "db_session_token": "token123"}

        with patch.object(st, "session_state", mock_session):
            with patch("src.auth.streamlit_auth.asyncio.run"):
                render_logout_button(mock_auth, "Test User")

        mock_auth.logout.assert_called_once()


@pytest.mark.asyncio
class TestCreateDbSession:
    """Test create_db_session() async function."""

    async def test_create_db_session_success(self):
        """Test successful session creation."""
        with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=True):
            with patch("src.auth.db.get_user_by_username") as mock_get_user:
                mock_get_user.return_value = {"id": "user123", "username": "testuser"}

                with patch("src.auth.db.create_session") as mock_create:
                    mock_create.return_value = {"id": "session123", "session_token": "token123"}

                    with patch("streamlit.context"):
                        token = await create_db_session("testuser")

        assert token == "token123"

    async def test_create_db_session_with_remember_me(self):
        """Test session creation with remember_me extends duration."""
        with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=True):
            with patch("src.auth.db.get_user_by_username") as mock_get_user:
                mock_get_user.return_value = {"id": "user123"}

                with patch("src.auth.db.create_session") as mock_create:
                    mock_create.return_value = {"id": "session123", "session_token": "token123"}

                    with patch("streamlit.context"):
                        await create_db_session("testuser", remember_me=True)

                # Check that expires_in_days was 90
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["expires_in_days"] == 90

    async def test_create_db_session_user_not_found(self):
        """Test session creation when user not found."""
        with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=True):
            with patch("src.auth.db.get_user_by_username", return_value=None):
                token = await create_db_session("nonexistent")

        assert token is None

    async def test_create_db_session_yaml_mode_returns_none(self):
        """Test that YAML mode doesn't create DB sessions."""
        with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=False):
            token = await create_db_session("testuser")

        assert token is None


@pytest.mark.asyncio
class TestRevokeDbSession:
    """Test revoke_db_session() async function."""

    async def test_revoke_db_session_success(self):
        """Test successful session revocation."""
        with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=True):
            with patch("src.auth.db.revoke_session") as mock_revoke:
                mock_revoke.return_value = True

                result = await revoke_db_session("token123")

        assert result is True

    async def test_revoke_db_session_yaml_mode(self):
        """Test that YAML mode returns False."""
        with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=False):
            result = await revoke_db_session("token123")

        assert result is False

    async def test_revoke_db_session_none_token(self):
        """Test revoking None token returns False."""
        result = await revoke_db_session(None)

        assert result is False

    async def test_revoke_db_session_error(self):
        """Test error handling in session revocation."""
        with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=True):
            with patch("src.auth.db.revoke_session", side_effect=Exception("DB error")):
                result = await revoke_db_session("token123")

        assert result is False


@pytest.mark.asyncio
class TestHandleOAuthCallback:
    """Test handle_oauth_callback() async function."""

    async def test_handle_oauth_callback_success(self):
        """Test successful OAuth callback handling."""
        mock_user = {
            "username": "oauth_user",
            "full_name": "OAuth User",
        }
        mock_result = {
            "user": mock_user,
            "is_new_user": False,
        }

        with patch("src.auth.oauth_handler.complete_oauth_flow", return_value=mock_result):
            with patch("src.auth.security.log_auth_event"):
                user = await handle_oauth_callback("google", "auth_code", "state123")

        assert user == mock_user

    async def test_handle_oauth_callback_new_user(self):
        """Test OAuth callback with new user creation."""
        mock_user = {"username": "new_user", "full_name": "New User"}
        mock_result = {"user": mock_user, "is_new_user": True}

        with patch("src.auth.oauth_handler.complete_oauth_flow", return_value=mock_result):
            with patch("src.auth.security.log_auth_event"):
                user = await handle_oauth_callback("github", "auth_code", "state123")

        assert user["username"] == "new_user"

    async def test_handle_oauth_callback_error(self):
        """Test OAuth callback error handling."""
        with patch(
            "src.auth.oauth_handler.complete_oauth_flow", side_effect=Exception("OAuth error")
        ):
            with patch("src.auth.security.log_auth_event"):
                user = await handle_oauth_callback("google", "bad_code", "state")

        assert user is None


class TestInitiateOAuthLogin:
    """Test initiate_oauth_login() function."""

    @patch("streamlit.markdown")
    @patch("streamlit.stop")
    @patch("streamlit.session_state", {})
    def test_initiate_oauth_login_google(self, mock_stop, mock_markdown):
        """Test initiating Google OAuth login."""
        with patch("src.auth.oauth_handler.initiate_oauth_flow") as mock_flow:
            mock_flow.return_value = ("https://google.com/oauth", "state123")

            with patch(
                "src.auth.streamlit_auth.asyncio.run",
                return_value=("https://google.com/oauth", "state123"),
            ):
                initiate_oauth_login("google")

        assert st.session_state.get("oauth_state_google") == "state123"
        mock_stop.assert_called_once()

    @patch("streamlit.markdown")
    @patch("streamlit.stop")
    @patch("streamlit.session_state", {})
    def test_initiate_oauth_login_github(self, mock_stop, mock_markdown):
        """Test initiating GitHub OAuth login."""
        with patch("src.auth.oauth_handler.initiate_oauth_flow") as mock_flow:
            mock_flow.return_value = ("https://github.com/oauth", "state456")

            with patch(
                "src.auth.streamlit_auth.asyncio.run",
                return_value=("https://github.com/oauth", "state456"),
            ):
                initiate_oauth_login("github")

        assert st.session_state.get("oauth_state_github") == "state456"

    @patch("streamlit.error")
    def test_initiate_oauth_login_error(self, mock_error):
        """Test OAuth initiation error handling."""
        # The initiate_oauth_login uses asyncio.run internally
        with patch("src.auth.streamlit_auth.asyncio.run", side_effect=Exception("Config error")):
            initiate_oauth_login("google")

        mock_error.assert_called()


class TestRenderOAuthButtons:
    """Test render_oauth_buttons() function."""

    @patch("streamlit.button")
    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    def test_render_oauth_buttons_both_providers(self, mock_columns, mock_markdown, mock_button):
        """Test rendering OAuth buttons for both providers."""
        mock_col1 = Mock()
        mock_col2 = Mock()
        mock_col1.__enter__ = Mock(return_value=None)
        mock_col1.__exit__ = Mock(return_value=False)
        mock_col2.__enter__ = Mock(return_value=None)
        mock_col2.__exit__ = Mock(return_value=False)
        mock_columns.return_value = (mock_col1, mock_col2)
        mock_button.return_value = False

        with patch("src.auth.streamlit_auth.get_oauth_enabled", return_value=True):
            with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=True):
                with patch("src.auth.streamlit_auth.get_google_oauth_enabled", return_value=True):
                    with patch(
                        "src.auth.streamlit_auth.get_github_oauth_enabled", return_value=True
                    ):
                        render_oauth_buttons()

        # Buttons are rendered using st.button inside column context managers
        assert mock_button.call_count >= 2

    def test_render_oauth_buttons_oauth_disabled(self):
        """Test that buttons don't render when OAuth disabled."""
        with patch("src.auth.streamlit_auth.get_oauth_enabled", return_value=False):
            with patch("streamlit.button") as mock_button:
                render_oauth_buttons()

        mock_button.assert_not_called()

    def test_render_oauth_buttons_yaml_mode(self):
        """Test that buttons don't render in YAML mode."""
        with patch("src.auth.streamlit_auth.get_oauth_enabled", return_value=True):
            with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=False):
                with patch("streamlit.button") as mock_button:
                    render_oauth_buttons()

        mock_button.assert_not_called()


class TestCheckOAuthCallback:
    """Test check_oauth_callback() function."""

    def test_check_oauth_callback_success(self):
        """Test successful OAuth callback check."""
        mock_user = {"username": "oauth_user", "full_name": "OAuth User"}
        mock_session_state = MockSessionState({"oauth_state_google": "state123"})
        mock_query_params = {"code": "auth_code", "state": "state123"}

        with patch("src.auth.streamlit_auth.get_oauth_enabled", return_value=True):
            with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=True):
                with patch("src.auth.streamlit_auth.asyncio.run", return_value=mock_user):
                    with patch.object(st, "session_state", mock_session_state):
                        with patch.object(st, "query_params", mock_query_params):
                            username, name = check_oauth_callback()

        assert username == "oauth_user"
        assert name == "OAuth User"

    @patch("streamlit.query_params", {})
    def test_check_oauth_callback_no_code(self):
        """Test callback check with no code parameter."""
        with patch("src.auth.streamlit_auth.get_oauth_enabled", return_value=True):
            with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=True):
                username, name = check_oauth_callback()

        assert username is None
        assert name is None

    def test_check_oauth_callback_oauth_disabled(self):
        """Test callback check when OAuth is disabled."""
        with patch("src.auth.streamlit_auth.get_oauth_enabled", return_value=False):
            username, name = check_oauth_callback()

        assert username is None
        assert name is None


class TestRequireAuthentication:
    """Test require_authentication() function."""

    @patch("streamlit.stop")
    def test_require_authentication_already_authenticated(self, mock_stop):
        """Test require_authentication when already authenticated."""
        mock_session_state = MockSessionState(
            {
                "authentication_status": True,
                "name": "Test User",
                "username": "testuser",
            }
        )

        with patch("src.auth.streamlit_auth.get_authenticator") as mock_auth:
            mock_auth.return_value = Mock()

            with patch.object(st, "session_state", mock_session_state):
                name, _authenticator = require_authentication()

        assert name == "Test User"
        mock_stop.assert_not_called()

    @patch("streamlit.stop")
    def test_require_authentication_not_authenticated(self, mock_stop):
        """Test require_authentication shows login page when not authenticated."""
        mock_session_state = MockSessionState({"authentication_status": None})

        with patch("src.auth.streamlit_auth.check_oauth_callback", return_value=(None, None)):
            with patch(
                "src.auth.streamlit_auth.render_login_page", return_value=("Name", "user", None)
            ):
                with patch.object(st, "session_state", mock_session_state):
                    require_authentication()

        mock_stop.assert_called_once()

    @patch("streamlit.stop")
    @patch("streamlit.rerun")
    def test_require_authentication_successful_login(self, mock_rerun, mock_stop):
        """Test require_authentication on successful login."""
        mock_session_state = MockSessionState({"authentication_status": None})

        with patch("src.auth.streamlit_auth.check_oauth_callback", return_value=(None, None)):
            with patch(
                "src.auth.streamlit_auth.render_login_page", return_value=("Name", "user", True)
            ):
                with patch("src.auth.streamlit_auth.get_rate_limiter") as mock_limiter:
                    mock_limiter.return_value.record_successful_login = Mock()

                    with patch("src.auth.streamlit_auth.get_use_database_auth", return_value=False):
                        with patch("src.auth.streamlit_auth.asyncio.run"):
                            with patch.object(st, "session_state", mock_session_state):
                                require_authentication()

        mock_rerun.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_load_auth_config_with_empty_file(self, tmp_path):
        """Test loading empty config file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        with patch("src.auth.streamlit_auth.get_settings") as mock_settings:
            mock_settings.return_value.use_database_auth = False

            with pytest.raises(Exception):
                load_auth_config(str(config_file))

    @pytest.mark.asyncio
    async def test_load_credentials_with_empty_database(self):
        """Test loading credentials when database is empty."""
        with patch("src.auth.db.list_users", return_value=[]):
            credentials = await load_credentials_from_database()

        assert credentials["usernames"] == {}

    def test_get_authenticator_with_invalid_config(self):
        """Test get_authenticator with invalid config."""
        config = {}  # Missing required fields

        with pytest.raises(Exception):
            get_authenticator(config)
