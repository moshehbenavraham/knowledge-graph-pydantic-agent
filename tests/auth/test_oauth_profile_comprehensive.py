"""Comprehensive tests for OAuth profile management module.

Tests all functionality in src/auth/oauth_profile_management.py.
"""

from unittest.mock import patch

import pytest

from src.auth.oauth_profile_management import (
    get_linked_oauth_accounts,
    get_provider_display_name,
    get_provider_icon,
    render_oauth_account_management,
)


class TestProviderHelpers:
    """Test provider helper functions."""

    def test_get_provider_display_name_google(self):
        """Test getting display name for Google."""
        name = get_provider_display_name("google")
        assert name == "Google"

    def test_get_provider_icon_google(self):
        """Test getting icon for Google."""
        icon = get_provider_icon("google")
        assert icon == "=5"


class TestGetLinkedOAuthAccounts:
    """Test get_linked_oauth_accounts function."""

    @pytest.mark.asyncio
    @patch("src.auth.oauth_profile_management.get_user_by_username")
    @patch("src.auth.oauth_profile_management.get_user_oauth_accounts")
    async def test_get_linked_accounts_success(self, mock_get_accounts, mock_get_user):
        """Test getting linked accounts successfully."""
        mock_get_user.return_value = {"id": "user123"}
        mock_get_accounts.return_value = [
            {"provider": "google", "is_active": True, "id": "account1"},
        ]

        accounts = await get_linked_oauth_accounts("testuser")

        assert len(accounts) == 1


class TestRenderOAuthAccountManagement:
    """Test render_oauth_account_management function."""

    @patch("src.auth.oauth_profile_management.st")
    def test_render_not_authenticated(self, mock_st):
        """Test rendering when not authenticated."""
        mock_st.session_state.get.return_value = None

        render_oauth_account_management()

        mock_st.error.assert_called_once_with("Not authenticated")
