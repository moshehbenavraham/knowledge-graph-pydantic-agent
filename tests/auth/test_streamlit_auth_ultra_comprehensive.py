"""Ultra comprehensive tests for streamlit_auth.py (target: 60%+ coverage)."""

from unittest.mock import MagicMock, Mock, patch

import pytest


class TestDatabaseAuthSettings:
    """Test database auth setting functions."""

    def test_get_use_database_auth_true(self):
        from src.auth.streamlit_auth import get_use_database_auth

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.use_database_auth = True
            mock_get_settings.return_value = mock_settings

            result = get_use_database_auth()
            assert result is True

    def test_get_use_database_auth_false(self):
        from src.auth.streamlit_auth import get_use_database_auth

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.use_database_auth = False
            mock_get_settings.return_value = mock_settings

            result = get_use_database_auth()
            assert result is False

    def test_get_oauth_enabled_true(self):
        from src.auth.streamlit_auth import get_oauth_enabled

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.oauth_enabled = True
            mock_get_settings.return_value = mock_settings

            result = get_oauth_enabled()
            assert result is True

    def test_get_oauth_enabled_false(self):
        from src.auth.streamlit_auth import get_oauth_enabled

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.oauth_enabled = False
            mock_get_settings.return_value = mock_settings

            result = get_oauth_enabled()
            assert result is False

    def test_get_google_oauth_enabled(self):
        from src.auth.streamlit_auth import get_google_oauth_enabled

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.google_client_id = "test-client-id"
            mock_settings.google_client_secret = "test-secret"
            mock_get_settings.return_value = mock_settings

            result = get_google_oauth_enabled()
            assert result is True

    def test_get_google_oauth_disabled_missing_credentials(self):
        from src.auth.streamlit_auth import get_google_oauth_enabled

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.google_client_id = None
            mock_settings.google_client_secret = None
            mock_get_settings.return_value = mock_settings

            result = get_google_oauth_enabled()
            assert result is False

    def test_get_github_oauth_enabled(self):
        from src.auth.streamlit_auth import get_github_oauth_enabled

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.github_client_id = "test-client-id"
            mock_settings.github_client_secret = "test-secret"
            mock_get_settings.return_value = mock_settings

            result = get_github_oauth_enabled()
            assert result is True

    def test_get_github_oauth_disabled_missing_credentials(self):
        from src.auth.streamlit_auth import get_github_oauth_enabled

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.github_client_id = None
            mock_settings.github_client_secret = None
            mock_get_settings.return_value = mock_settings

            result = get_github_oauth_enabled()
            assert result is False


@pytest.mark.asyncio
class TestLoadCredentialsFromDatabase:
    """Test load_credentials_from_database() function."""

    async def test_load_credentials_success(self):
        from src.auth.streamlit_auth import load_credentials_from_database

        mock_users = [
            {
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "User One",
                "is_active": True,
                "password_hash": "hashed1",
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "full_name": "User Two",
                "is_active": True,
                "password_hash": "hashed2",
            },
        ]

        with patch("src.auth.db.list_users") as mock_list_users:
            mock_list_users.return_value = mock_users

            with patch("src.clients.database.get_supabase_client") as mock_get_client:
                mock_client = Mock()
                mock_table = Mock()
                mock_select = Mock()
                mock_eq = Mock()
                mock_limit = Mock()

                mock_client.table.return_value = mock_table
                mock_table.select.return_value = mock_select
                mock_select.eq.return_value = mock_eq
                mock_eq.limit.return_value = mock_limit
                mock_limit.execute.return_value = Mock(data=[{"password_hash": "hashed_password"}])

                mock_get_client.return_value = mock_client

                result = await load_credentials_from_database()

                assert "usernames" in result
                assert "user1" in result["usernames"]
                assert "user2" in result["usernames"]
                assert result["usernames"]["user1"]["email"] == "user1@example.com"
                assert result["usernames"]["user1"]["name"] == "User One"

    async def test_load_credentials_skip_inactive_users(self):
        from src.auth.streamlit_auth import load_credentials_from_database

        mock_users = [
            {
                "username": "active_user",
                "email": "active@example.com",
                "full_name": "Active User",
                "is_active": True,
                "password_hash": "hashed_active",
            },
            {
                "username": "inactive_user",
                "email": "inactive@example.com",
                "full_name": "Inactive User",
                "is_active": False,
                "password_hash": "hashed_inactive",
            },
        ]

        with patch("src.auth.db.list_users") as mock_list_users:
            mock_list_users.return_value = mock_users

            with patch("src.clients.database.get_supabase_client") as mock_get_client:
                mock_client = Mock()
                mock_table = Mock()
                mock_client.table.return_value = mock_table
                mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
                    data=[{"password_hash": "hashed"}]
                )
                mock_get_client.return_value = mock_client

                result = await load_credentials_from_database()

                assert "active_user" in result["usernames"]
                assert "inactive_user" not in result["usernames"]

    async def test_load_credentials_database_error(self):
        from src.auth.streamlit_auth import load_credentials_from_database

        with patch("src.auth.db.list_users") as mock_list_users:
            mock_list_users.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception, match="Database connection failed"):
                await load_credentials_from_database()


class TestLoadAuthConfig:
    """Test load_auth_config() function."""

    def test_load_auth_config_yaml_mode(self):
        from src.auth.streamlit_auth import load_auth_config

        mock_config_data = {
            "credentials": {"usernames": {"test_user": {"email": "test@example.com"}}},
            "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
        }

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.use_database_auth = False
            mock_settings.auth_cookie_key = "test_key"
            mock_get_settings.return_value = mock_settings

            with patch("src.auth.streamlit_auth.Path") as mock_path:
                mock_path.return_value.exists.return_value = True

                with patch("builtins.open", create=True) as mock_open:
                    import yaml

                    mock_open.return_value.__enter__.return_value.read.return_value = yaml.dump(
                        mock_config_data
                    )

                    with patch("yaml.safe_load") as mock_yaml_load:
                        mock_yaml_load.return_value = mock_config_data

                        result = load_auth_config()

                        assert "credentials" in result
                        assert "cookie" in result

    def test_load_auth_config_database_mode(self):
        from src.auth.streamlit_auth import load_auth_config

        mock_credentials = {
            "usernames": {"db_user": {"email": "db@example.com", "name": "DB User"}}
        }

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.use_database_auth = True
            mock_settings.auth_cookie_key = "test_key"
            mock_get_settings.return_value = mock_settings

            with patch("src.auth.streamlit_auth.Path") as mock_path:
                mock_path.return_value.exists.return_value = True

                with patch("builtins.open", create=True) as mock_open:
                    import yaml

                    mock_config_data = {
                        "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30}
                    }
                    mock_open.return_value.__enter__.return_value.read.return_value = yaml.dump(
                        mock_config_data
                    )

                    with patch("yaml.safe_load") as mock_yaml_load:
                        mock_yaml_load.return_value = mock_config_data

                        with patch("asyncio.run") as mock_asyncio_run:
                            mock_asyncio_run.return_value = mock_credentials

                            with patch("nest_asyncio.apply"):
                                result = load_auth_config()

                                assert "credentials" in result
                                assert result["credentials"] == mock_credentials

    def test_load_auth_config_no_file_database_mode(self):
        from src.auth.streamlit_auth import load_auth_config

        mock_credentials = {"usernames": {"test_user": {"email": "test@test.com", "name": "Test"}}}

        with patch("src.auth.streamlit_auth.get_settings") as mock_get_settings:
            mock_settings = Mock()
            mock_settings.use_database_auth = True
            mock_settings.auth_cookie_key = "test_key"
            mock_get_settings.return_value = mock_settings

            with patch("pathlib.Path.exists", return_value=False):
                with patch(
                    "src.auth.streamlit_auth.load_credentials_from_database",
                    return_value=mock_credentials,
                ):
                    with patch(
                        "src.auth.streamlit_auth.asyncio.run", return_value=mock_credentials
                    ):
                        result = load_auth_config()

                        assert "cookie" in result
                        assert result["cookie"]["key"] == "test_key"


class TestGetAuthenticator:
    """Test get_authenticator() function."""

    def test_get_authenticator_with_config(self):
        from src.auth.streamlit_auth import get_authenticator

        mock_config = {
            "credentials": {"usernames": {}},
            "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
            "preauthorized": {"emails": []},
        }

        with patch("src.auth.streamlit_auth.stauth.Authenticate") as MockAuthenticate:
            get_authenticator(mock_config)

            MockAuthenticate.assert_called_once()

    def test_get_authenticator_without_config(self):
        from src.auth.streamlit_auth import get_authenticator

        with patch("src.auth.streamlit_auth.load_auth_config") as mock_load_config:
            mock_config = {
                "credentials": {"usernames": {}},
                "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
                "preauthorized": {"emails": []},
            }
            mock_load_config.return_value = mock_config

            with patch("src.auth.streamlit_auth.stauth.Authenticate") as MockAuthenticate:
                get_authenticator()

                mock_load_config.assert_called_once()
                MockAuthenticate.assert_called_once()


@pytest.mark.asyncio
class TestCreateDBSession:
    """Test create_db_session() function."""

    async def test_create_db_session_success(self):
        from src.auth.streamlit_auth import create_db_session

        mock_user = {"id": 123, "username": "test_user"}
        mock_session = {
            "id": 456,
            "session_token": "test-token-123",
            "user_id": 123,
        }

        with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_get_use_db:
            mock_get_use_db.return_value = True

            with patch("src.auth.db.get_user_by_username") as mock_get_user:
                mock_get_user.return_value = mock_user

                with patch("src.auth.db.create_session") as mock_create_session:
                    mock_create_session.return_value = mock_session

                    result = await create_db_session("test_user")

                    assert result == "test-token-123"
                    mock_create_session.assert_called_once()

    async def test_create_db_session_remember_me(self):
        from src.auth.streamlit_auth import create_db_session

        mock_user = {"id": 123, "username": "test_user"}
        mock_session = {
            "id": 456,
            "session_token": "test-token-123",
            "user_id": 123,
        }

        with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_get_use_db:
            mock_get_use_db.return_value = True

            with patch("src.auth.db.get_user_by_username") as mock_get_user:
                mock_get_user.return_value = mock_user

                with patch("src.auth.db.create_session") as mock_create_session:
                    mock_create_session.return_value = mock_session

                    result = await create_db_session("test_user", remember_me=True)

                    assert result == "test-token-123"
                    # Check that expires_in_days was set to 90
                    call_args = mock_create_session.call_args
                    assert call_args[1]["expires_in_days"] == 90

    async def test_create_db_session_yaml_mode(self):
        from src.auth.streamlit_auth import create_db_session

        with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_get_use_db:
            mock_get_use_db.return_value = False

            result = await create_db_session("test_user")

            assert result is None

    async def test_create_db_session_user_not_found(self):
        from src.auth.streamlit_auth import create_db_session

        with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_get_use_db:
            mock_get_use_db.return_value = True

            with patch("src.auth.db.get_user_by_username") as mock_get_user:
                mock_get_user.return_value = None

                result = await create_db_session("nonexistent_user")

                assert result is None


@pytest.mark.asyncio
class TestRevokeDBSession:
    """Test revoke_db_session() function."""

    async def test_revoke_db_session_success(self):
        from src.auth.streamlit_auth import revoke_db_session

        with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_get_use_db:
            mock_get_use_db.return_value = True

            with patch("src.auth.db.revoke_session") as mock_revoke_session:
                mock_revoke_session.return_value = True

                result = await revoke_db_session("test-token-123")

                assert result is True
                mock_revoke_session.assert_called_once_with("test-token-123")

    async def test_revoke_db_session_yaml_mode(self):
        from src.auth.streamlit_auth import revoke_db_session

        with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_get_use_db:
            mock_get_use_db.return_value = False

            result = await revoke_db_session("test-token-123")

            assert result is False

    async def test_revoke_db_session_no_token(self):
        from src.auth.streamlit_auth import revoke_db_session

        with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_get_use_db:
            mock_get_use_db.return_value = True

            result = await revoke_db_session(None)

            assert result is False


@pytest.mark.asyncio
class TestHandleOAuthCallback:
    """Test handle_oauth_callback() function."""

    async def test_handle_oauth_callback_success(self):
        from src.auth.streamlit_auth import handle_oauth_callback

        mock_result = {
            "user": {"username": "oauth_user", "full_name": "OAuth User"},
            "is_new_user": False,
        }

        with patch("src.auth.oauth_handler.complete_oauth_flow") as mock_complete_flow:
            mock_complete_flow.return_value = mock_result

            with patch("src.auth.streamlit_auth.log_auth_event") as mock_log_event:
                result = await handle_oauth_callback("google", "auth-code-123", "state-abc")

                assert result == mock_result["user"]
                mock_complete_flow.assert_called_once_with("google", "auth-code-123", "state-abc")
                mock_log_event.assert_called_once()

    async def test_handle_oauth_callback_new_user(self):
        from src.auth.streamlit_auth import handle_oauth_callback

        mock_result = {
            "user": {"username": "new_oauth_user", "full_name": "New User"},
            "is_new_user": True,
        }

        with patch("src.auth.oauth_handler.complete_oauth_flow") as mock_complete_flow:
            mock_complete_flow.return_value = mock_result

            with patch("src.auth.streamlit_auth.log_auth_event") as mock_log_event:
                result = await handle_oauth_callback("github", "auth-code-456", "state-xyz")

                assert result["username"] == "new_oauth_user"
                mock_log_event.assert_called_once()

    async def test_handle_oauth_callback_error(self):
        from src.auth.streamlit_auth import handle_oauth_callback

        with patch("src.auth.oauth_handler.complete_oauth_flow") as mock_complete_flow:
            mock_complete_flow.side_effect = Exception("OAuth error")

            with patch("src.auth.streamlit_auth.log_auth_event") as mock_log_event:
                result = await handle_oauth_callback("google", "auth-code-123", "state-abc")

                assert result is None
                mock_log_event.assert_called_once()


class TestInitiateOAuthLogin:
    """Test initiate_oauth_login() function."""

    @patch("streamlit.session_state")
    @patch("streamlit.markdown")
    @patch("streamlit.stop")
    def test_initiate_oauth_login_google(self, mock_stop, mock_markdown, mock_session_state):
        from src.auth.streamlit_auth import initiate_oauth_login

        mock_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?..."
        mock_state = "random-state-123"

        with patch("src.auth.oauth_handler.initiate_oauth_flow"):
            with patch("asyncio.run") as mock_asyncio_run:
                mock_asyncio_run.return_value = (mock_auth_url, mock_state)

                session_dict = {}
                mock_session_state.__setitem__ = lambda self, key, value: session_dict.__setitem__(
                    key, value
                )

                initiate_oauth_login("google")

                mock_asyncio_run.assert_called_once()
                assert "oauth_state_google" in session_dict
                mock_markdown.assert_called_once()
                mock_stop.assert_called_once()

    @patch("streamlit.error")
    def test_initiate_oauth_login_error(self, mock_error):
        from src.auth.streamlit_auth import initiate_oauth_login

        with patch("src.auth.oauth_handler.initiate_oauth_flow"):
            with patch("asyncio.run") as mock_asyncio_run:
                mock_asyncio_run.side_effect = Exception("OAuth initiation failed")

                initiate_oauth_login("google")

                mock_error.assert_called_once()


class TestRenderOAuthButtons:
    """Test render_oauth_buttons() function."""

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_render_oauth_buttons_both_enabled(self, mock_button, mock_columns, mock_markdown):
        from src.auth.streamlit_auth import render_oauth_buttons

        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_columns.return_value = [mock_col1, mock_col2]
        mock_button.return_value = False

        with patch("src.auth.streamlit_auth.get_oauth_enabled") as mock_get_oauth:
            mock_get_oauth.return_value = True

            with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_get_use_db:
                mock_get_use_db.return_value = True

                with patch("src.auth.streamlit_auth.get_google_oauth_enabled") as mock_google:
                    mock_google.return_value = True

                    with patch("src.auth.streamlit_auth.get_github_oauth_enabled") as mock_github:
                        mock_github.return_value = True

                        render_oauth_buttons()

                        mock_markdown.assert_called()
                        mock_columns.assert_called_once()

    @patch("streamlit.markdown")
    def test_render_oauth_buttons_oauth_disabled(self, mock_markdown):
        from src.auth.streamlit_auth import render_oauth_buttons

        with patch("src.auth.streamlit_auth.get_oauth_enabled") as mock_get_oauth:
            mock_get_oauth.return_value = False

            render_oauth_buttons()

            # Should return early, no markdown calls
            assert mock_markdown.call_count == 0

    @patch("streamlit.markdown")
    def test_render_oauth_buttons_yaml_mode(self, mock_markdown):
        from src.auth.streamlit_auth import render_oauth_buttons

        with patch("src.auth.streamlit_auth.get_oauth_enabled") as mock_get_oauth:
            mock_get_oauth.return_value = True

            with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_get_use_db:
                mock_get_use_db.return_value = False

                render_oauth_buttons()

                # Should return early
                assert mock_markdown.call_count == 0


class TestCheckOAuthCallback:
    """Test check_oauth_callback() function."""

    @patch("streamlit.query_params")
    @patch("streamlit.session_state")
    def test_check_oauth_callback_google_success(self, mock_session_state, mock_query_params):
        from src.auth.streamlit_auth import check_oauth_callback

        mock_query_params.get.side_effect = lambda key: {
            "code": "auth-code-123",
            "state": "state-abc",
        }.get(key)

        mock_query_params.__contains__ = lambda self, key: True
        mock_query_params.__str__ = lambda self: "google"

        session_dict = {"oauth_state_google": "state-abc"}
        mock_session_state.get = lambda key: session_dict.get(key)
        mock_session_state.pop = lambda key, default=None: session_dict.pop(key, default)
        mock_query_params.clear = Mock()

        with patch("src.auth.streamlit_auth.get_oauth_enabled") as mock_oauth_enabled:
            mock_oauth_enabled.return_value = True

            with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_use_db:
                mock_use_db.return_value = True

                with patch("src.auth.streamlit_auth.handle_oauth_callback"):
                    with patch("asyncio.run") as mock_asyncio_run:
                        mock_user = {"username": "google_user", "full_name": "Google User"}
                        mock_asyncio_run.return_value = mock_user

                        username, name = check_oauth_callback()

                        assert username == "google_user"
                        assert name == "Google User"

    @patch("streamlit.query_params")
    def test_check_oauth_callback_no_code(self, mock_query_params):
        from src.auth.streamlit_auth import check_oauth_callback

        mock_query_params.get.return_value = None

        with patch("src.auth.streamlit_auth.get_oauth_enabled") as mock_oauth_enabled:
            mock_oauth_enabled.return_value = True

            with patch("src.auth.streamlit_auth.get_use_database_auth") as mock_use_db:
                mock_use_db.return_value = True

                username, name = check_oauth_callback()

                assert username is None
                assert name is None

    @patch("streamlit.query_params")
    def test_check_oauth_callback_oauth_disabled(self, mock_query_params):
        from src.auth.streamlit_auth import check_oauth_callback

        with patch("src.auth.streamlit_auth.get_oauth_enabled") as mock_oauth_enabled:
            mock_oauth_enabled.return_value = False

            username, name = check_oauth_callback()

            assert username is None
            assert name is None


class TestRenderLogoutButton:
    """Test render_logout_button() function."""

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state")
    def test_render_logout_button_display(self, mock_session_state, mock_sidebar):
        from src.auth.streamlit_auth import render_logout_button

        mock_authenticator = Mock()
        mock_session_state.get.return_value = "test_user"

        with patch("streamlit.markdown") as mock_markdown:
            with patch("streamlit.button") as mock_button:
                mock_button.return_value = False

                render_logout_button(mock_authenticator, "Test User")

                mock_markdown.assert_called()
                mock_button.assert_called_once()

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state")
    @patch("streamlit.rerun")
    def test_render_logout_button_clicked(self, mock_rerun, mock_session_state, mock_sidebar):
        from src.auth.streamlit_auth import render_logout_button

        mock_authenticator = Mock()
        session_dict = {"username": "test_user", "db_session_token": None}
        mock_session_state.get = lambda key, default=None: session_dict.get(key, default)
        mock_session_state.clear = lambda: session_dict.clear()

        with patch("streamlit.markdown"):
            with patch("streamlit.button") as mock_button:
                mock_button.return_value = True

                with patch("asyncio.run"):
                    with patch("src.auth.streamlit_auth.log_auth_event"):
                        render_logout_button(mock_authenticator, "Test User")

                        mock_authenticator.logout.assert_called_once()
                        mock_rerun.assert_called_once()
