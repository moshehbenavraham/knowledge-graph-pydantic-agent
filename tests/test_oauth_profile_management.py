"""
Comprehensive tests for OAuth profile management functionality.

Tests OAuth account linking, unlinking, provider configuration,
and profile UI rendering.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.auth.oauth_profile_management import (
    _get_oauth_providers,
    get_linked_oauth_accounts,
    get_provider_display_name,
    get_provider_icon,
    render_oauth_account_management,
    render_oauth_linking_callback_handler,
)

# =====================================================
# FIXTURES
# =====================================================


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    mock = MagicMock()
    mock.oauth_enabled = True
    mock.google_client_id = "google_client_id_123"
    mock.google_client_secret = "google_client_secret_123"
    mock.github_client_id = "github_client_id_456"
    mock.github_client_secret = "github_client_secret_456"
    mock.microsoft_client_id = None
    mock.microsoft_client_secret = None
    mock.apple_client_id = None
    mock.apple_client_secret = None
    return mock


@pytest.fixture
def sample_user():
    """Sample user data."""
    return {
        "id": str(uuid4()),
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
    }


@pytest.fixture
def sample_oauth_accounts():
    """Sample OAuth account records."""
    return [
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "provider": "google",
            "provider_user_id": "google_user_123",
            "profile_data": {"email": "test@gmail.com", "name": "Test User"},
            "is_active": True,
            "created_at": "2024-01-15T10:00:00Z",
        },
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "provider": "github",
            "provider_user_id": "github_user_456",
            "profile_data": {"email": "test@github.com", "login": "testuser"},
            "is_active": True,
            "created_at": "2024-02-01T12:00:00Z",
        },
    ]


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components."""
    with patch("src.auth.oauth_profile_management.st") as mock_st:
        mock_st.session_state = {"username": "testuser"}
        mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
        mock_st.container = MagicMock()
        mock_st.button = MagicMock(return_value=False)
        mock_st.expander = MagicMock()
        mock_st.query_params = {}
        yield mock_st


# =====================================================
# PROVIDER CONFIGURATION TESTS
# =====================================================


def test_get_oauth_providers(mock_settings):
    """Test _get_oauth_providers returns correct configuration."""
    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        providers = _get_oauth_providers()

        # Check Google (enabled)
        assert "google" in providers
        assert providers["google"]["name"] == "Google"
        assert providers["google"]["icon"] == "🔵"
        assert providers["google"]["enabled"] is True

        # Check GitHub (enabled)
        assert "github" in providers
        assert providers["github"]["name"] == "GitHub"
        assert providers["github"]["enabled"] is True

        # Check Microsoft (disabled - no credentials)
        assert "microsoft" in providers
        assert providers["microsoft"]["enabled"] is False

        # Check Apple (disabled - no credentials)
        assert "apple" in providers
        assert providers["apple"]["enabled"] is False


def test_get_oauth_providers_all_disabled():
    """Test _get_oauth_providers when no providers configured."""
    mock_settings = MagicMock()
    mock_settings.google_client_id = None
    mock_settings.google_client_secret = None
    mock_settings.github_client_id = None
    mock_settings.github_client_secret = None
    mock_settings.microsoft_client_id = None
    mock_settings.microsoft_client_secret = None
    mock_settings.apple_client_id = None
    mock_settings.apple_client_secret = None

    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        providers = _get_oauth_providers()

        # All providers should be disabled
        for provider in providers.values():
            assert provider["enabled"] is False


def test_get_provider_display_name():
    """Test get_provider_display_name returns correct names."""
    assert get_provider_display_name("google") == "Google"
    assert get_provider_display_name("github") == "GitHub"
    assert get_provider_display_name("microsoft") == "Microsoft"
    assert get_provider_display_name("apple") == "Apple"


def test_get_provider_display_name_unknown():
    """Test get_provider_display_name with unknown provider."""
    result = get_provider_display_name("unknown_provider")
    # Should capitalize the provider name
    assert result == "Unknown_provider"


def test_get_provider_icon():
    """Test get_provider_icon returns correct icons."""
    assert get_provider_icon("google") == "🔵"
    assert get_provider_icon("github") == "⚫"
    assert get_provider_icon("microsoft") == "🟦"
    assert get_provider_icon("apple") == ""


def test_get_provider_icon_unknown():
    """Test get_provider_icon with unknown provider."""
    result = get_provider_icon("unknown_provider")
    # Should return default icon
    assert result == "🔗"


# =====================================================
# GET LINKED ACCOUNTS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_linked_oauth_accounts_success(sample_user, sample_oauth_accounts):
    """Test successful retrieval of linked OAuth accounts."""
    with patch("src.auth.oauth_profile_management.get_user_by_username", return_value=sample_user):
        with patch(
            "src.auth.oauth_profile_management.get_user_oauth_accounts",
            return_value=sample_oauth_accounts,
        ):
            accounts = await get_linked_oauth_accounts("testuser")

            assert len(accounts) == 2
            assert accounts[0]["provider"] == "google"
            assert accounts[1]["provider"] == "github"


@pytest.mark.asyncio
async def test_get_linked_oauth_accounts_user_not_found():
    """Test get_linked_oauth_accounts when user doesn't exist."""
    with patch("src.auth.oauth_profile_management.get_user_by_username", return_value=None):
        accounts = await get_linked_oauth_accounts("nonexistent")

        assert accounts == []


@pytest.mark.asyncio
async def test_get_linked_oauth_accounts_filters_inactive():
    """Test that inactive accounts are filtered out."""
    accounts_with_inactive = [
        {
            "id": str(uuid4()),
            "provider": "google",
            "is_active": True,
        },
        {
            "id": str(uuid4()),
            "provider": "github",
            "is_active": False,
        },
    ]

    with patch(
        "src.auth.oauth_profile_management.get_user_by_username",
        return_value={"id": str(uuid4())},
    ):
        with patch(
            "src.auth.oauth_profile_management.get_user_oauth_accounts",
            return_value=accounts_with_inactive,
        ):
            accounts = await get_linked_oauth_accounts("testuser")

            # Should only include active accounts
            assert len(accounts) == 1
            assert accounts[0]["provider"] == "google"


@pytest.mark.asyncio
async def test_get_linked_oauth_accounts_error_handling():
    """Test error handling in get_linked_oauth_accounts."""
    with patch(
        "src.auth.oauth_profile_management.get_user_by_username",
        side_effect=Exception("Database error"),
    ):
        accounts = await get_linked_oauth_accounts("testuser")

        # Should return empty list on error
        assert accounts == []


# =====================================================
# RENDER OAUTH ACCOUNT MANAGEMENT TESTS
# =====================================================


def test_render_oauth_account_management_not_authenticated(mock_streamlit):
    """Test rendering when user is not authenticated."""
    mock_streamlit.session_state = {}

    render_oauth_account_management()

    mock_streamlit.error.assert_called_once_with("Not authenticated")


def test_render_oauth_account_management_oauth_disabled(mock_streamlit, mock_settings):
    """Test rendering when OAuth is disabled."""
    mock_settings.oauth_enabled = False

    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        render_oauth_account_management()

        mock_streamlit.info.assert_called_once()


def test_render_oauth_account_management_with_linked_accounts(
    mock_streamlit, mock_settings, sample_user, sample_oauth_accounts
):
    """Test rendering with linked accounts."""
    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        with patch(
            "src.auth.oauth_profile_management.get_user_by_username", return_value=sample_user
        ):
            with patch(
                "src.auth.oauth_profile_management.get_user_oauth_accounts",
                return_value=sample_oauth_accounts,
            ):
                with patch("src.auth.oauth_profile_management.asyncio.run") as mock_run:
                    mock_run.return_value = sample_oauth_accounts

                    render_oauth_account_management()

                    # Should display provider information
                    mock_streamlit.markdown.assert_called()
                    mock_streamlit.container.assert_called()


def test_render_oauth_account_management_unlink_button_click(
    mock_streamlit, mock_settings, sample_user, sample_oauth_accounts
):
    """Test clicking unlink button."""
    mock_streamlit.button = MagicMock(return_value=True)

    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        with patch(
            "src.auth.oauth_profile_management.get_user_by_username", return_value=sample_user
        ):
            with patch(
                "src.auth.oauth_profile_management.get_user_oauth_accounts",
                return_value=sample_oauth_accounts,
            ):
                with patch("src.auth.oauth_profile_management.asyncio.run") as mock_run:
                    mock_run.return_value = sample_oauth_accounts

                    render_oauth_account_management()

                    # Should trigger rerun
                    mock_streamlit.rerun.assert_called()


def test_render_oauth_account_management_link_button_click(
    mock_streamlit, mock_settings, sample_user
):
    """Test clicking link button for new provider."""
    mock_streamlit.button = MagicMock(side_effect=[False, False, False, True])  # Link button

    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        with patch(
            "src.auth.oauth_profile_management.get_user_by_username", return_value=sample_user
        ):
            with patch(
                "src.auth.oauth_profile_management.get_user_oauth_accounts", return_value=[]
            ):
                with patch("src.auth.oauth_profile_management.asyncio.run") as mock_run:
                    mock_run.side_effect = [
                        [],  # get_linked_oauth_accounts
                        ("https://oauth.url", "state_123"),  # initiate_oauth_flow
                    ]

                    render_oauth_account_management()

                    # Should display info about linking
                    mock_streamlit.info.assert_called()


def test_render_oauth_account_management_error_handling(mock_streamlit, mock_settings):
    """Test error handling during rendering."""
    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        with patch(
            "src.auth.oauth_profile_management.asyncio.run",
            side_effect=Exception("Database error"),
        ):
            render_oauth_account_management()

            # Should display error
            mock_streamlit.error.assert_called()


# =====================================================
# OAUTH LINKING CALLBACK TESTS
# =====================================================


def test_render_oauth_linking_callback_handler_not_in_linking_mode(mock_streamlit):
    """Test callback handler when not in linking mode."""
    mock_streamlit.session_state = {"oauth_linking_mode": False}

    render_oauth_linking_callback_handler()

    # Should return early without processing
    mock_streamlit.success.assert_not_called()


def test_render_oauth_linking_callback_handler_no_code(mock_streamlit):
    """Test callback handler when no OAuth code present."""
    mock_streamlit.session_state = {"oauth_linking_mode": True}
    mock_streamlit.query_params = {}

    render_oauth_linking_callback_handler()

    # Should return early without processing
    mock_streamlit.success.assert_not_called()


def test_render_oauth_linking_callback_handler_invalid_state(mock_streamlit):
    """Test callback handler with invalid state parameter."""
    mock_streamlit.session_state = {
        "oauth_linking_mode": True,
        "oauth_link_state_google": "expected_state",
    }
    mock_streamlit.query_params = {"code": "auth_code_123", "state": "invalid_state"}

    render_oauth_linking_callback_handler()

    # Should display error
    mock_streamlit.error.assert_called()


def test_render_oauth_linking_callback_handler_success(mock_streamlit):
    """Test successful OAuth linking callback."""
    mock_streamlit.session_state = {
        "oauth_linking_mode": True,
        "oauth_link_state_google": "valid_state_123",
        "username": "testuser",
    }
    mock_streamlit.query_params = {"code": "auth_code_123", "state": "valid_state_123"}

    with patch("src.auth.oauth_profile_management.asyncio.run") as mock_run:
        mock_run.return_value = None  # complete_oauth_flow succeeds

        render_oauth_linking_callback_handler()

        # Should display success message
        mock_streamlit.success.assert_called()
        mock_streamlit.rerun.assert_called()


def test_render_oauth_linking_callback_handler_error(mock_streamlit):
    """Test error handling in OAuth callback."""
    mock_streamlit.session_state = {
        "oauth_linking_mode": True,
        "oauth_link_state_google": "valid_state_123",
    }
    mock_streamlit.query_params = {"code": "auth_code_123", "state": "valid_state_123"}

    with patch("src.auth.oauth_profile_management.asyncio.run") as mock_run:
        mock_run.side_effect = Exception("OAuth error")

        render_oauth_linking_callback_handler()

        # Should display error
        mock_streamlit.error.assert_called()


# =====================================================
# INTEGRATION TESTS
# =====================================================


def test_oauth_providers_module_constant(mock_settings):
    """Test that OAUTH_PROVIDERS constant is properly initialized."""
    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        # Re-import to trigger initialization
        from src.auth.oauth_profile_management import OAUTH_PROVIDERS

        assert "google" in OAUTH_PROVIDERS
        assert "github" in OAUTH_PROVIDERS
        assert "microsoft" in OAUTH_PROVIDERS
        assert "apple" in OAUTH_PROVIDERS


def test_provider_display_consistency():
    """Test that provider names are consistent across functions."""
    providers = ["google", "github", "microsoft", "apple"]

    for provider in providers:
        display_name = get_provider_display_name(provider)
        icon = get_provider_icon(provider)

        # Display name should be capitalized
        assert display_name[0].isupper()
        # Icon should be an emoji or empty string
        assert isinstance(icon, str)


@pytest.mark.asyncio
async def test_get_linked_accounts_empty_result(sample_user):
    """Test get_linked_oauth_accounts with no linked accounts."""
    with patch("src.auth.oauth_profile_management.get_user_by_username", return_value=sample_user):
        with patch("src.auth.oauth_profile_management.get_user_oauth_accounts", return_value=[]):
            accounts = await get_linked_oauth_accounts("testuser")

            assert accounts == []


def test_render_with_no_enabled_providers(mock_streamlit):
    """Test rendering when no OAuth providers are enabled."""
    mock_settings = MagicMock()
    mock_settings.oauth_enabled = True
    mock_settings.google_client_id = None
    mock_settings.github_client_id = None
    mock_settings.microsoft_client_id = None
    mock_settings.apple_client_id = None

    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        with patch("src.auth.oauth_profile_management.asyncio.run", return_value=[]):
            render_oauth_account_management()

            # Should still render but show no providers
            mock_streamlit.markdown.assert_called()


def test_unlink_confirmation_flow(
    mock_streamlit, mock_settings, sample_user, sample_oauth_accounts
):
    """Test complete unlink confirmation flow."""
    # First call: show unlink button (clicked)
    # Second call: show confirmation dialog
    mock_streamlit.button = MagicMock(side_effect=[True, True, False])  # Unlink, Yes, No

    with patch("src.auth.oauth_profile_management.get_settings", return_value=mock_settings):
        with patch(
            "src.auth.oauth_profile_management.get_user_by_username", return_value=sample_user
        ):
            with patch(
                "src.auth.oauth_profile_management.get_user_oauth_accounts",
                return_value=sample_oauth_accounts,
            ):
                with patch("src.auth.oauth_profile_management.asyncio.run") as mock_run:
                    mock_run.side_effect = [
                        sample_oauth_accounts,  # get_linked_oauth_accounts
                        True,  # unlink_oauth_account success
                    ]

                    mock_streamlit.session_state = {
                        "username": "testuser",
                        "confirm_unlink_google": True,
                    }

                    render_oauth_account_management()

                    # Should display warning
                    mock_streamlit.warning.assert_called()
