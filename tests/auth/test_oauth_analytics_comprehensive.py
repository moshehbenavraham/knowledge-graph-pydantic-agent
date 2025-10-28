"""Comprehensive tests for OAuth analytics dashboard module.

Tests all functionality in src/auth/oauth_analytics_dashboard.py including:
- Refreshing analytics views
- Getting provider summary
- Getting login activity
- Getting account growth
- Getting multi-provider users
- Getting adoption rate
- Rendering OAuth analytics dashboard
"""

from unittest.mock import Mock, patch

import pytest

from src.auth.oauth_analytics_dashboard import (
    get_account_growth,
    get_adoption_rate,
    get_login_activity,
    get_multi_provider_users,
    get_provider_summary,
    refresh_analytics_views,
    render_oauth_analytics_dashboard,
)


class TestRefreshAnalyticsViews:
    """Test refresh_analytics_views function."""

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_refresh_analytics_views_success(self, mock_get_client):
        """Test refreshing analytics views successfully."""
        mock_client = Mock()
        mock_client.rpc.return_value.execute.return_value = Mock(data=True)
        mock_get_client.return_value = mock_client

        result = await refresh_analytics_views()

        assert result is True
        mock_client.rpc.assert_called_once_with("refresh_oauth_analytics_views")

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_refresh_analytics_views_failure(self, mock_get_client):
        """Test refreshing analytics views with failure."""
        mock_client = Mock()
        mock_client.rpc.return_value.execute.side_effect = Exception("Database error")
        mock_get_client.return_value = mock_client

        result = await refresh_analytics_views()

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_refresh_analytics_views_false_data(self, mock_get_client):
        """Test refreshing analytics views when data is False."""
        mock_client = Mock()
        mock_client.rpc.return_value.execute.return_value = Mock(data=False)
        mock_get_client.return_value = mock_client

        result = await refresh_analytics_views()

        assert result is False


class TestGetProviderSummary:
    """Test get_provider_summary function."""

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_provider_summary_success(self, mock_get_client):
        """Test getting provider summary successfully."""
        mock_client = Mock()
        mock_data = [
            {"provider": "google", "total_accounts": 50, "unique_users": 45},
            {"provider": "github", "total_accounts": 30, "unique_users": 28},
        ]
        mock_client.rpc.return_value.execute.return_value = Mock(data=mock_data)
        mock_get_client.return_value = mock_client

        result = await get_provider_summary()

        assert result == mock_data
        assert len(result) == 2
        assert result[0]["provider"] == "google"

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_provider_summary_empty(self, mock_get_client):
        """Test getting provider summary when no data."""
        mock_client = Mock()
        mock_client.rpc.return_value.execute.return_value = Mock(data=None)
        mock_get_client.return_value = mock_client

        result = await get_provider_summary()

        assert result == []

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_provider_summary_exception(self, mock_get_client):
        """Test getting provider summary with exception."""
        mock_client = Mock()
        mock_client.rpc.return_value.execute.side_effect = Exception("RPC error")
        mock_get_client.return_value = mock_client

        result = await get_provider_summary()

        assert result == []


class TestGetLoginActivity:
    """Test get_login_activity function."""

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_login_activity_success(self, mock_get_client):
        """Test getting login activity successfully."""
        mock_client = Mock()
        mock_data = [
            {"login_date": "2025-10-01", "provider": "google", "users_logged_in": 25},
            {"login_date": "2025-10-02", "provider": "google", "users_logged_in": 30},
        ]
        mock_client.rpc.return_value.execute.return_value = Mock(data=mock_data)
        mock_get_client.return_value = mock_client

        result = await get_login_activity(days=30)

        assert result == mock_data
        mock_client.rpc.assert_called_once_with("get_oauth_login_activity", {"days": 30})

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_login_activity_custom_days(self, mock_get_client):
        """Test getting login activity with custom days parameter."""
        mock_client = Mock()
        mock_client.rpc.return_value.execute.return_value = Mock(data=[])
        mock_get_client.return_value = mock_client

        result = await get_login_activity(days=7)

        mock_client.rpc.assert_called_once_with("get_oauth_login_activity", {"days": 7})

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_login_activity_exception(self, mock_get_client):
        """Test getting login activity with exception."""
        mock_client = Mock()
        mock_client.rpc.side_effect = Exception("Database error")
        mock_get_client.return_value = mock_client

        result = await get_login_activity()

        assert result == []


class TestGetAccountGrowth:
    """Test get_account_growth function."""

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_account_growth_success(self, mock_get_client):
        """Test getting account growth successfully."""
        mock_client = Mock()
        mock_data = [
            {
                "link_date": "2025-10-01",
                "provider": "google",
                "accounts_linked": 5,
                "cumulative_accounts": 100,
            }
        ]
        mock_client.rpc.return_value.execute.return_value = Mock(data=mock_data)
        mock_get_client.return_value = mock_client

        result = await get_account_growth(days=30)

        assert result == mock_data
        mock_client.rpc.assert_called_once_with("get_oauth_account_growth", {"days": 30})

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_account_growth_exception(self, mock_get_client):
        """Test getting account growth with exception."""
        mock_client = Mock()
        mock_client.rpc.side_effect = Exception("Database error")
        mock_get_client.return_value = mock_client

        result = await get_account_growth()

        assert result == []


class TestGetMultiProviderUsers:
    """Test get_multi_provider_users function."""

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_multi_provider_users_success(self, mock_get_client):
        """Test getting multi-provider users successfully."""
        mock_client = Mock()
        mock_data = [
            {
                "username": "user1",
                "email": "user1@example.com",
                "linked_accounts": 2,
                "providers": ["google", "github"],
            }
        ]
        mock_client.rpc.return_value.execute.return_value = Mock(data=mock_data)
        mock_get_client.return_value = mock_client

        result = await get_multi_provider_users()

        assert result == mock_data
        assert len(result) == 1
        assert result[0]["linked_accounts"] == 2

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_multi_provider_users_empty(self, mock_get_client):
        """Test getting multi-provider users when none exist."""
        mock_client = Mock()
        mock_client.rpc.return_value.execute.return_value = Mock(data=[])
        mock_get_client.return_value = mock_client

        result = await get_multi_provider_users()

        assert result == []

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_multi_provider_users_exception(self, mock_get_client):
        """Test getting multi-provider users with exception."""
        mock_client = Mock()
        mock_client.rpc.side_effect = Exception("Database error")
        mock_get_client.return_value = mock_client

        result = await get_multi_provider_users()

        assert result == []


class TestGetAdoptionRate:
    """Test get_adoption_rate function."""

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_adoption_rate_success(self, mock_get_client):
        """Test getting adoption rate successfully."""
        mock_client = Mock()
        mock_data = [
            {"metric": "OAuth Users", "value": 100, "percentage": 75.0},
            {"metric": "Password Only Users", "value": 25, "percentage": 18.75},
            {"metric": "Hybrid Users (Password + OAuth)", "value": 8, "percentage": 6.25},
            {"metric": "Total Active Users", "value": 133, "percentage": 100.0},
        ]
        mock_client.rpc.return_value.execute.return_value = Mock(data=mock_data)
        mock_get_client.return_value = mock_client

        result = await get_adoption_rate()

        assert result == mock_data
        assert len(result) == 4

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_adoption_rate_empty(self, mock_get_client):
        """Test getting adoption rate when no data."""
        mock_client = Mock()
        mock_client.rpc.return_value.execute.return_value = Mock(data=None)
        mock_get_client.return_value = mock_client

        result = await get_adoption_rate()

        assert result == []

    @pytest.mark.asyncio
    @patch("src.auth.oauth_analytics_dashboard.get_supabase_client")
    async def test_get_adoption_rate_exception(self, mock_get_client):
        """Test getting adoption rate with exception."""
        mock_client = Mock()
        mock_client.rpc.side_effect = Exception("Database error")
        mock_get_client.return_value = mock_client

        result = await get_adoption_rate()

        assert result == []


class TestRenderOAuthAnalyticsDashboard:
    """Test render_oauth_analytics_dashboard function."""

    @patch("src.auth.oauth_analytics_dashboard.st")
    def test_render_dashboard_not_authenticated(self, mock_st):
        """Test rendering dashboard when not authenticated."""
        mock_st.session_state.get.return_value = None

        render_oauth_analytics_dashboard()

        mock_st.error.assert_called_once_with("Not authenticated")

    @patch("src.auth.oauth_analytics_dashboard.st")
    @patch("src.auth.oauth_analytics_dashboard.asyncio")
    @patch("src.auth.oauth_analytics_dashboard.is_admin")
    async def test_render_dashboard_not_admin(self, mock_is_admin, mock_asyncio, mock_st):
        """Test rendering dashboard when user is not admin."""
        mock_st.session_state.get.return_value = "testuser"
        mock_asyncio.run.return_value = False

        render_oauth_analytics_dashboard()

        mock_st.error.assert_called_with("Access denied. Admin privileges required.")

    @patch("src.auth.oauth_analytics_dashboard.st")
    @patch("src.auth.oauth_analytics_dashboard.asyncio")
    @patch("src.auth.oauth_analytics_dashboard.is_admin")
    @patch("src.auth.oauth_analytics_dashboard.get_provider_summary")
    @patch("src.auth.oauth_analytics_dashboard.get_adoption_rate")
    @patch("src.auth.oauth_analytics_dashboard.get_login_activity")
    @patch("src.auth.oauth_analytics_dashboard.get_account_growth")
    @patch("src.auth.oauth_analytics_dashboard.get_multi_provider_users")
    async def test_render_dashboard_admin_with_data(
        self,
        mock_get_multi,
        mock_get_growth,
        mock_get_login,
        mock_get_adoption,
        mock_get_summary,
        mock_is_admin,
        mock_asyncio,
        mock_st,
    ):
        """Test rendering dashboard for admin with data."""
        mock_st.session_state.get.return_value = "admin"
        mock_asyncio.run.side_effect = lambda x: x  # Pass through for async functions

        # Mock is_admin call
        def async_run_side_effect(coro):
            if hasattr(coro, "__name__") and "is_admin" in str(coro):
                return True
            return coro

        mock_asyncio.run.side_effect = async_run_side_effect

        mock_get_summary.return_value = [
            {
                "provider": "google",
                "total_accounts": 100,
                "unique_users": 90,
                "active_accounts": 85,
                "inactive_accounts": 15,
                "avg_age_days": 45,
            }
        ]

        render_oauth_analytics_dashboard()

        # Verify markdown headers are rendered
        assert mock_st.markdown.called

    @patch("src.auth.oauth_analytics_dashboard.st")
    @patch("src.auth.oauth_analytics_dashboard.asyncio")
    @patch("src.auth.oauth_analytics_dashboard.is_admin")
    @patch("src.auth.oauth_analytics_dashboard.get_provider_summary")
    async def test_render_dashboard_no_oauth_data(
        self, mock_get_summary, mock_is_admin, mock_asyncio, mock_st
    ):
        """Test rendering dashboard when no OAuth data available."""
        mock_st.session_state.get.return_value = "admin"

        def async_run_side_effect(coro):
            if hasattr(coro, "__name__") and "is_admin" in str(coro):
                return True
            return []

        mock_asyncio.run.side_effect = async_run_side_effect
        mock_get_summary.return_value = []

        render_oauth_analytics_dashboard()

        # Verify info message for no data
        assert any("No OAuth data" in str(call) for call in mock_st.info.call_args_list)

    @patch("src.auth.oauth_analytics_dashboard.st")
    @patch("src.auth.oauth_analytics_dashboard.asyncio")
    @patch("src.auth.oauth_analytics_dashboard.is_admin")
    @patch("src.auth.oauth_analytics_dashboard.refresh_analytics_views")
    async def test_render_dashboard_refresh_button(
        self, mock_refresh, mock_is_admin, mock_asyncio, mock_st
    ):
        """Test refresh button in dashboard."""
        mock_st.session_state.get.return_value = "admin"

        def async_run_side_effect(coro):
            if hasattr(coro, "__name__") and "is_admin" in str(coro):
                return True
            if hasattr(coro, "__name__") and "refresh" in str(coro):
                return True
            return []

        mock_asyncio.run.side_effect = async_run_side_effect

        # Simulate button click
        mock_st.columns.return_value = [Mock(), Mock()]
        mock_st.button.return_value = True

        render_oauth_analytics_dashboard()

        # Refresh should be called when button clicked
        assert mock_asyncio.run.called
