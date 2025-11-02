"""
Comprehensive tests for OAuth analytics dashboard functionality.

Tests analytics data retrieval, visualization, and dashboard rendering.
"""

from unittest.mock import MagicMock, patch

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

# =====================================================
# FIXTURES
# =====================================================


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    mock_client = MagicMock()

    # Mock RPC calls
    mock_rpc = MagicMock()
    mock_client.rpc.return_value = mock_rpc

    mock_execute = MagicMock()
    mock_rpc.execute.return_value = mock_execute
    mock_execute.data = []

    return mock_client


@pytest.fixture
def sample_provider_summary():
    """Sample provider summary data."""
    return [
        {
            "provider": "google",
            "total_accounts": 50,
            "unique_users": 45,
            "active_accounts": 48,
            "inactive_accounts": 2,
            "avg_age_days": 30.5,
        },
        {
            "provider": "github",
            "total_accounts": 30,
            "unique_users": 28,
            "active_accounts": 29,
            "inactive_accounts": 1,
            "avg_age_days": 25.2,
        },
    ]


@pytest.fixture
def sample_login_activity():
    """Sample login activity data."""
    return [
        {
            "login_date": "2024-01-15",
            "provider": "google",
            "users_logged_in": 10,
        },
        {
            "login_date": "2024-01-15",
            "provider": "github",
            "users_logged_in": 5,
        },
        {
            "login_date": "2024-01-16",
            "provider": "google",
            "users_logged_in": 12,
        },
    ]


@pytest.fixture
def sample_account_growth():
    """Sample account growth data."""
    return [
        {
            "link_date": "2024-01-15",
            "provider": "google",
            "accounts_linked": 5,
            "cumulative_accounts": 45,
        },
        {
            "link_date": "2024-01-16",
            "provider": "google",
            "accounts_linked": 3,
            "cumulative_accounts": 48,
        },
    ]


@pytest.fixture
def sample_multi_provider_users():
    """Sample multi-provider users data."""
    return [
        {
            "username": "user1",
            "email": "user1@example.com",
            "linked_accounts": 2,
            "providers": "google,github",
        },
        {
            "username": "user2",
            "email": "user2@example.com",
            "linked_accounts": 3,
            "providers": "google,github,microsoft",
        },
    ]


@pytest.fixture
def sample_adoption_rate():
    """Sample adoption rate data."""
    return [
        {
            "metric": "Total Active Users",
            "value": 100,
            "percentage": 100.0,
        },
        {
            "metric": "OAuth Users",
            "value": 60,
            "percentage": 60.0,
        },
        {
            "metric": "Password Only Users",
            "value": 30,
            "percentage": 30.0,
        },
        {
            "metric": "Hybrid Users (Password + OAuth)",
            "value": 10,
            "percentage": 10.0,
        },
    ]


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components."""
    with patch("src.auth.oauth_analytics_dashboard.st") as mock_st:
        mock_st.session_state = {"username": "admin"}
        mock_st.columns = MagicMock(return_value=[MagicMock() for _ in range(4)])
        mock_st.container = MagicMock()
        mock_st.button = MagicMock(return_value=False)
        mock_st.selectbox = MagicMock(return_value=30)
        mock_st.expander = MagicMock()
        mock_st.spinner = MagicMock()
        mock_st.dataframe = MagicMock()
        mock_st.plotly_chart = MagicMock()
        yield mock_st


# =====================================================
# REFRESH ANALYTICS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_refresh_analytics_views_success(mock_supabase_client):
    """Test successful refresh of analytics views."""
    mock_supabase_client.rpc().execute.return_value.data = True

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await refresh_analytics_views()

        assert result is True
        mock_supabase_client.rpc.assert_called_once_with("refresh_oauth_analytics_views")


@pytest.mark.asyncio
async def test_refresh_analytics_views_failure(mock_supabase_client):
    """Test handling of refresh failure."""
    mock_supabase_client.rpc().execute.side_effect = Exception("Database error")

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await refresh_analytics_views()

        assert result is False


# =====================================================
# GET PROVIDER SUMMARY TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_provider_summary_success(mock_supabase_client, sample_provider_summary):
    """Test successful retrieval of provider summary."""
    mock_supabase_client.rpc().execute.return_value.data = sample_provider_summary

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_provider_summary()

        assert len(result) == 2
        assert result[0]["provider"] == "google"
        assert result[0]["total_accounts"] == 50


@pytest.mark.asyncio
async def test_get_provider_summary_empty():
    """Test provider summary with no data."""
    mock_client = MagicMock()
    mock_client.rpc().execute.return_value.data = None

    with patch("src.auth.oauth_analytics_dashboard.get_supabase_client", return_value=mock_client):
        result = await get_provider_summary()

        assert result == []


@pytest.mark.asyncio
async def test_get_provider_summary_error(mock_supabase_client):
    """Test error handling in provider summary."""
    mock_supabase_client.rpc().execute.side_effect = Exception("Database error")

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_provider_summary()

        assert result == []


# =====================================================
# GET LOGIN ACTIVITY TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_login_activity_success(mock_supabase_client, sample_login_activity):
    """Test successful retrieval of login activity."""
    mock_supabase_client.rpc().execute.return_value.data = sample_login_activity

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_login_activity(days=30)

        assert len(result) == 3
        assert result[0]["provider"] == "google"
        mock_supabase_client.rpc.assert_called_once_with("get_oauth_login_activity", {"days": 30})


@pytest.mark.asyncio
async def test_get_login_activity_custom_days(mock_supabase_client):
    """Test login activity with custom day range."""
    mock_supabase_client.rpc().execute.return_value.data = []

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        await get_login_activity(days=7)

        mock_supabase_client.rpc.assert_called_once_with("get_oauth_login_activity", {"days": 7})


@pytest.mark.asyncio
async def test_get_login_activity_error(mock_supabase_client):
    """Test error handling in login activity."""
    mock_supabase_client.rpc().execute.side_effect = Exception("Database error")

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_login_activity()

        assert result == []


# =====================================================
# GET ACCOUNT GROWTH TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_account_growth_success(mock_supabase_client, sample_account_growth):
    """Test successful retrieval of account growth."""
    mock_supabase_client.rpc().execute.return_value.data = sample_account_growth

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_account_growth(days=30)

        assert len(result) == 2
        assert result[0]["provider"] == "google"
        mock_supabase_client.rpc.assert_called_once_with("get_oauth_account_growth", {"days": 30})


@pytest.mark.asyncio
async def test_get_account_growth_empty():
    """Test account growth with no data."""
    mock_client = MagicMock()
    mock_client.rpc().execute.return_value.data = None

    with patch("src.auth.oauth_analytics_dashboard.get_supabase_client", return_value=mock_client):
        result = await get_account_growth()

        assert result == []


@pytest.mark.asyncio
async def test_get_account_growth_error(mock_supabase_client):
    """Test error handling in account growth."""
    mock_supabase_client.rpc().execute.side_effect = Exception("Database error")

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_account_growth()

        assert result == []


# =====================================================
# GET MULTI PROVIDER USERS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_multi_provider_users_success(mock_supabase_client, sample_multi_provider_users):
    """Test successful retrieval of multi-provider users."""
    mock_supabase_client.rpc().execute.return_value.data = sample_multi_provider_users

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_multi_provider_users()

        assert len(result) == 2
        assert result[0]["linked_accounts"] == 2
        assert result[1]["linked_accounts"] == 3


@pytest.mark.asyncio
async def test_get_multi_provider_users_empty():
    """Test multi-provider users with no data."""
    mock_client = MagicMock()
    mock_client.rpc().execute.return_value.data = None

    with patch("src.auth.oauth_analytics_dashboard.get_supabase_client", return_value=mock_client):
        result = await get_multi_provider_users()

        assert result == []


@pytest.mark.asyncio
async def test_get_multi_provider_users_error(mock_supabase_client):
    """Test error handling in multi-provider users."""
    mock_supabase_client.rpc().execute.side_effect = Exception("Database error")

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_multi_provider_users()

        assert result == []


# =====================================================
# GET ADOPTION RATE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_adoption_rate_success(mock_supabase_client, sample_adoption_rate):
    """Test successful retrieval of adoption rate."""
    mock_supabase_client.rpc().execute.return_value.data = sample_adoption_rate

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_adoption_rate()

        assert len(result) == 4
        assert result[1]["metric"] == "OAuth Users"
        assert result[1]["percentage"] == 60.0


@pytest.mark.asyncio
async def test_get_adoption_rate_empty():
    """Test adoption rate with no data."""
    mock_client = MagicMock()
    mock_client.rpc().execute.return_value.data = None

    with patch("src.auth.oauth_analytics_dashboard.get_supabase_client", return_value=mock_client):
        result = await get_adoption_rate()

        assert result == []


@pytest.mark.asyncio
async def test_get_adoption_rate_error(mock_supabase_client):
    """Test error handling in adoption rate."""
    mock_supabase_client.rpc().execute.side_effect = Exception("Database error")

    with patch(
        "src.auth.oauth_analytics_dashboard.get_supabase_client",
        return_value=mock_supabase_client,
    ):
        result = await get_adoption_rate()

        assert result == []


# =====================================================
# RENDER DASHBOARD TESTS
# =====================================================


def test_render_oauth_analytics_dashboard_not_authenticated(mock_streamlit):
    """Test dashboard rendering when not authenticated."""
    mock_streamlit.session_state = {}

    render_oauth_analytics_dashboard()

    mock_streamlit.error.assert_called_once_with("Not authenticated")


def test_render_oauth_analytics_dashboard_not_admin(mock_streamlit):
    """Test dashboard rendering when user is not admin."""
    with patch("src.auth.oauth_analytics_dashboard.asyncio.run", return_value=False):
        render_oauth_analytics_dashboard()

        mock_streamlit.error.assert_called_once()


def test_render_oauth_analytics_dashboard_admin_access(
    mock_streamlit, sample_provider_summary, sample_adoption_rate
):
    """Test dashboard rendering with admin access."""
    with patch("src.auth.oauth_analytics_dashboard.asyncio.run") as mock_run:
        mock_run.side_effect = [
            True,  # is_admin
            sample_provider_summary,  # get_provider_summary
            sample_adoption_rate,  # get_adoption_rate
            [],  # get_login_activity
            [],  # get_account_growth
            [],  # get_multi_provider_users
        ]

        with patch("src.auth.oauth_analytics_dashboard.pd.DataFrame"):
            render_oauth_analytics_dashboard()

            # Should render dashboard
            mock_streamlit.markdown.assert_called()


def test_render_oauth_analytics_dashboard_refresh_button(mock_streamlit):
    """Test refresh button functionality."""
    mock_streamlit.button = MagicMock(return_value=True)

    with patch("src.auth.oauth_analytics_dashboard.asyncio.run") as mock_run:
        mock_run.side_effect = [
            True,  # is_admin
            True,  # refresh_analytics_views
        ]

        with patch("src.auth.oauth_analytics_dashboard.st.spinner") as mock_spinner:
            mock_spinner_context = MagicMock()
            mock_spinner.return_value.__enter__ = MagicMock(return_value=mock_spinner_context)
            mock_spinner.return_value.__exit__ = MagicMock(return_value=False)

            render_oauth_analytics_dashboard()

            mock_streamlit.success.assert_called()


def test_render_oauth_analytics_dashboard_with_provider_data(
    mock_streamlit, sample_provider_summary
):
    """Test dashboard with provider summary data."""
    with patch("src.auth.oauth_analytics_dashboard.asyncio.run") as mock_run:
        mock_run.side_effect = [
            True,  # is_admin
            sample_provider_summary,  # get_provider_summary
            [],  # get_adoption_rate
            [],  # get_login_activity
            [],  # get_account_growth
            [],  # get_multi_provider_users
        ]

        with patch("src.auth.oauth_analytics_dashboard.pd.DataFrame") as mock_df:
            mock_df_instance = MagicMock()
            mock_df.return_value = mock_df_instance

            render_oauth_analytics_dashboard()

            # Should display metrics
            mock_streamlit.metric.assert_called()


def test_render_oauth_analytics_dashboard_with_login_activity(
    mock_streamlit, sample_login_activity
):
    """Test dashboard with login activity data."""
    with patch("src.auth.oauth_analytics_dashboard.asyncio.run") as mock_run:
        mock_run.side_effect = [
            True,  # is_admin
            [],  # get_provider_summary
            [],  # get_adoption_rate
            sample_login_activity,  # get_login_activity
            [],  # get_account_growth
            [],  # get_multi_provider_users
        ]

        with patch("src.auth.oauth_analytics_dashboard.pd.DataFrame") as mock_df:
            mock_df_instance = MagicMock()
            mock_df_instance.groupby.return_value.sum.return_value.reset_index.return_value = (
                mock_df_instance
            )
            mock_df.return_value = mock_df_instance

            render_oauth_analytics_dashboard()

            # Should display charts
            mock_streamlit.plotly_chart.assert_called()


def test_render_oauth_analytics_dashboard_with_account_growth(
    mock_streamlit, sample_account_growth
):
    """Test dashboard with account growth data."""
    with patch("src.auth.oauth_analytics_dashboard.asyncio.run") as mock_run:
        mock_run.side_effect = [
            True,  # is_admin
            [],  # get_provider_summary
            [],  # get_adoption_rate
            [],  # get_login_activity
            sample_account_growth,  # get_account_growth
            [],  # get_multi_provider_users
        ]

        with patch("src.auth.oauth_analytics_dashboard.pd.DataFrame") as mock_df:
            mock_df_instance = MagicMock()
            mock_df.return_value = mock_df_instance

            render_oauth_analytics_dashboard()

            # Should display growth charts
            mock_streamlit.plotly_chart.assert_called()


def test_render_oauth_analytics_dashboard_with_multi_provider(
    mock_streamlit, sample_multi_provider_users
):
    """Test dashboard with multi-provider users data."""
    with patch("src.auth.oauth_analytics_dashboard.asyncio.run") as mock_run:
        mock_run.side_effect = [
            True,  # is_admin
            [],  # get_provider_summary
            [],  # get_adoption_rate
            [],  # get_login_activity
            [],  # get_account_growth
            sample_multi_provider_users,  # get_multi_provider_users
        ]

        with patch("src.auth.oauth_analytics_dashboard.pd.DataFrame") as mock_df:
            mock_df_instance = MagicMock()
            mock_df_instance.__getitem__ = MagicMock(return_value=mock_df_instance)
            mock_df_instance.value_counts.return_value.reset_index.return_value = mock_df_instance
            mock_df.return_value = mock_df_instance

            render_oauth_analytics_dashboard()

            # Should display multi-provider info
            mock_streamlit.dataframe.assert_called()


def test_render_oauth_analytics_dashboard_no_data(mock_streamlit):
    """Test dashboard rendering with no data."""
    with patch("src.auth.oauth_analytics_dashboard.asyncio.run") as mock_run:
        mock_run.side_effect = [
            True,  # is_admin
            [],  # get_provider_summary
            [],  # get_adoption_rate
            [],  # get_login_activity
            [],  # get_account_growth
            [],  # get_multi_provider_users
        ]

        render_oauth_analytics_dashboard()

        # Should display info messages for no data
        mock_streamlit.info.assert_called()


def test_render_oauth_analytics_dashboard_time_range_selector(mock_streamlit):
    """Test time range selector functionality."""
    mock_streamlit.selectbox = MagicMock(return_value=7)

    with patch("src.auth.oauth_analytics_dashboard.asyncio.run") as mock_run:
        mock_run.side_effect = [
            True,  # is_admin
            [],  # get_provider_summary
            [],  # get_adoption_rate
            [],  # get_login_activity (7 days)
            [],  # get_account_growth (7 days)
            [],  # get_multi_provider_users
        ]

        render_oauth_analytics_dashboard()

        # Should call functions with selected time range
        mock_streamlit.selectbox.assert_called()


# =====================================================
# INTEGRATION TESTS
# =====================================================


@pytest.mark.asyncio
async def test_all_analytics_functions_return_lists():
    """Test that all analytics functions return lists."""
    mock_client = MagicMock()
    mock_client.rpc().execute.return_value.data = None

    with patch("src.auth.oauth_analytics_dashboard.get_supabase_client", return_value=mock_client):
        provider_summary = await get_provider_summary()
        login_activity = await get_login_activity()
        account_growth = await get_account_growth()
        multi_provider = await get_multi_provider_users()
        adoption_rate = await get_adoption_rate()

        assert isinstance(provider_summary, list)
        assert isinstance(login_activity, list)
        assert isinstance(account_growth, list)
        assert isinstance(multi_provider, list)
        assert isinstance(adoption_rate, list)


@pytest.mark.asyncio
async def test_refresh_analytics_returns_bool():
    """Test that refresh_analytics_views returns boolean."""
    mock_client = MagicMock()
    mock_client.rpc().execute.return_value.data = True

    with patch("src.auth.oauth_analytics_dashboard.get_supabase_client", return_value=mock_client):
        result = await refresh_analytics_views()

        assert isinstance(result, bool)
