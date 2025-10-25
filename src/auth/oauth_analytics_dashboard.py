"""
OAuth Analytics Dashboard

Provides comprehensive analytics and visualization for OAuth usage.
Shows provider statistics, login trends, account growth, and adoption metrics.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import structlog

from src.clients.database import get_supabase_client

logger = structlog.get_logger(__name__)


async def refresh_analytics_views() -> bool:
    """Refresh all OAuth analytics materialized views."""
    try:
        client = get_supabase_client()
        result = client.rpc("refresh_oauth_analytics_views").execute()
        return bool(result.data)
    except Exception as e:
        logger.error("Failed to refresh OAuth analytics views", error=str(e))
        return False


async def get_provider_summary() -> List[Dict[str, Any]]:
    """Get OAuth provider summary statistics."""
    try:
        client = get_supabase_client()
        result = client.rpc("get_oauth_provider_summary").execute()
        return result.data or []
    except Exception as e:
        logger.error("Failed to get provider summary", error=str(e))
        return []


async def get_login_activity(days: int = 30) -> List[Dict[str, Any]]:
    """Get OAuth login activity for last N days."""
    try:
        client = get_supabase_client()
        result = client.rpc("get_oauth_login_activity", {"days": days}).execute()
        return result.data or []
    except Exception as e:
        logger.error("Failed to get login activity", error=str(e))
        return []


async def get_account_growth(days: int = 30) -> List[Dict[str, Any]]:
    """Get OAuth account growth for last N days."""
    try:
        client = get_supabase_client()
        result = client.rpc("get_oauth_account_growth", {"days": days}).execute()
        return result.data or []
    except Exception as e:
        logger.error("Failed to get account growth", error=str(e))
        return []


async def get_multi_provider_users() -> List[Dict[str, Any]]:
    """Get users with multiple OAuth providers linked."""
    try:
        client = get_supabase_client()
        result = client.rpc("get_multi_provider_users").execute()
        return result.data or []
    except Exception as e:
        logger.error("Failed to get multi-provider users", error=str(e))
        return []


async def get_adoption_rate() -> List[Dict[str, Any]]:
    """Get OAuth adoption rate metrics."""
    try:
        client = get_supabase_client()
        result = client.rpc("get_oauth_adoption_rate").execute()
        return result.data or []
    except Exception as e:
        logger.error("Failed to get adoption rate", error=str(e))
        return []


def render_oauth_analytics_dashboard() -> None:
    """
    Render comprehensive OAuth analytics dashboard.

    Shows provider statistics, trends, and adoption metrics.
    Requires admin privileges.
    """
    current_username = st.session_state.get("username")
    if not current_username:
        st.error("Not authenticated")
        return

    # Check if user is admin
    from src.auth.admin_2fa_management import is_admin

    is_admin_user = asyncio.run(is_admin(current_username))
    if not is_admin_user:
        st.error("⛔ Access denied. Admin privileges required.")
        return

    st.markdown("# 📊 OAuth Analytics Dashboard")
    st.markdown("Comprehensive analytics for OAuth authentication usage.")

    # Refresh button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            with st.spinner("Refreshing analytics..."):
                success = asyncio.run(refresh_analytics_views())
                if success:
                    st.success("✅ Data refreshed")
                    st.rerun()
                else:
                    st.error("Failed to refresh data")

    st.markdown("---")

    # =====================================================
    # SECTION 1: Overview Metrics
    # =====================================================

    st.markdown("## 📈 Overview")

    # Get provider summary
    provider_summary = asyncio.run(get_provider_summary())

    if provider_summary:
        # Calculate total metrics
        total_accounts = sum(p["total_accounts"] for p in provider_summary)
        total_users = sum(p["unique_users"] for p in provider_summary)
        total_active = sum(p["active_accounts"] for p in provider_summary)

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total OAuth Accounts", total_accounts)

        with col2:
            st.metric("Unique Users with OAuth", total_users)

        with col3:
            st.metric("Active Accounts", total_active)

        with col4:
            providers_count = len(provider_summary)
            st.metric("OAuth Providers", providers_count)

        st.markdown("---")

        # Provider breakdown
        st.markdown("### 🔗 Provider Breakdown")

        # Create DataFrame for easier manipulation
        df_providers = pd.DataFrame(provider_summary)

        # Provider comparison chart
        fig_providers = go.Figure()

        fig_providers.add_trace(
            go.Bar(
                name="Total Accounts",
                x=df_providers["provider"],
                y=df_providers["total_accounts"],
                marker_color="#4285F4",
            )
        )

        fig_providers.add_trace(
            go.Bar(
                name="Unique Users",
                x=df_providers["provider"],
                y=df_providers["unique_users"],
                marker_color="#34A853",
            )
        )

        fig_providers.update_layout(
            title="OAuth Accounts by Provider",
            xaxis_title="Provider",
            yaxis_title="Count",
            barmode="group",
            height=400,
        )

        st.plotly_chart(fig_providers, use_container_width=True)

        # Provider details table
        with st.expander("📋 Provider Details"):
            st.dataframe(
                df_providers[
                    [
                        "provider",
                        "total_accounts",
                        "unique_users",
                        "active_accounts",
                        "inactive_accounts",
                        "avg_age_days",
                    ]
                ],
                use_container_width=True,
            )

    else:
        st.info("No OAuth data available yet.")

    st.markdown("---")

    # =====================================================
    # SECTION 2: Adoption Rate
    # =====================================================

    st.markdown("## 🎯 OAuth Adoption Rate")

    adoption_data = asyncio.run(get_adoption_rate())

    if adoption_data:
        # Create DataFrame
        df_adoption = pd.DataFrame(adoption_data)

        # Display metrics
        col1, col2, col3 = st.columns(3)

        oauth_users = next((d for d in adoption_data if d["metric"] == "OAuth Users"), None)
        password_users = next(
            (d for d in adoption_data if d["metric"] == "Password Only Users"), None
        )
        hybrid_users = next(
            (d for d in adoption_data if d["metric"] == "Hybrid Users (Password + OAuth)"), None
        )

        if oauth_users:
            with col1:
                st.metric("OAuth Users", f"{oauth_users['value']}", f"{oauth_users['percentage']:.1f}%")

        if password_users:
            with col2:
                st.metric(
                    "Password Only",
                    f"{password_users['value']}",
                    f"{password_users['percentage']:.1f}%",
                )

        if hybrid_users:
            with col3:
                st.metric(
                    "Hybrid (Both)",
                    f"{hybrid_users['value']}",
                    f"{hybrid_users['percentage']:.1f}%",
                )

        # Pie chart
        fig_pie = px.pie(
            df_adoption[df_adoption["metric"] != "Total Active Users"],
            values="value",
            names="metric",
            title="User Authentication Methods",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )

        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # =====================================================
    # SECTION 3: Login Activity Trends
    # =====================================================

    st.markdown("## 📅 Login Activity")

    # Time range selector
    time_range = st.selectbox(
        "Time Range",
        options=[7, 14, 30, 60, 90],
        format_func=lambda x: f"Last {x} days",
        index=2,  # Default to 30 days
    )

    login_activity = asyncio.run(get_login_activity(time_range))

    if login_activity:
        df_logins = pd.DataFrame(login_activity)
        df_logins["login_date"] = pd.to_datetime(df_logins["login_date"])

        # Line chart for login trends
        fig_logins = px.line(
            df_logins,
            x="login_date",
            y="users_logged_in",
            color="provider",
            title=f"Daily OAuth Logins (Last {time_range} Days)",
            markers=True,
        )

        fig_logins.update_layout(
            xaxis_title="Date",
            yaxis_title="Users Logged In",
            height=400,
        )

        st.plotly_chart(fig_logins, use_container_width=True)

        # Summary stats
        total_logins = df_logins.groupby("provider")["users_logged_in"].sum().reset_index()

        st.markdown("### Provider Login Summary")
        col1, col2 = st.columns(2)

        with col1:
            st.dataframe(
                total_logins.rename(
                    columns={"provider": "Provider", "users_logged_in": "Total Logins"}
                ),
                use_container_width=True,
            )

        with col2:
            fig_bar = px.bar(
                total_logins,
                x="provider",
                y="users_logged_in",
                title="Total Logins by Provider",
                color="provider",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info(f"No login activity data for the last {time_range} days.")

    st.markdown("---")

    # =====================================================
    # SECTION 4: Account Growth
    # =====================================================

    st.markdown("## 📈 Account Growth")

    growth_data = asyncio.run(get_account_growth(time_range))

    if growth_data:
        df_growth = pd.DataFrame(growth_data)
        df_growth["link_date"] = pd.to_datetime(df_growth["link_date"])

        # Cumulative growth chart
        fig_growth = px.line(
            df_growth,
            x="link_date",
            y="cumulative_accounts",
            color="provider",
            title=f"Cumulative OAuth Account Growth (Last {time_range} Days)",
            markers=True,
        )

        fig_growth.update_layout(
            xaxis_title="Date",
            yaxis_title="Cumulative Accounts",
            height=400,
        )

        st.plotly_chart(fig_growth, use_container_width=True)

        # Daily growth chart
        fig_daily = px.bar(
            df_growth,
            x="link_date",
            y="accounts_linked",
            color="provider",
            title="Daily New Account Links",
        )

        fig_daily.update_layout(
            xaxis_title="Date",
            yaxis_title="New Accounts Linked",
            height=400,
            barmode="stack",
        )

        st.plotly_chart(fig_daily, use_container_width=True)

    else:
        st.info(f"No account growth data for the last {time_range} days.")

    st.markdown("---")

    # =====================================================
    # SECTION 5: Multi-Provider Users
    # =====================================================

    st.markdown("## 🔗 Multi-Provider Users")

    multi_provider = asyncio.run(get_multi_provider_users())

    if multi_provider:
        st.write(
            f"Found **{len(multi_provider)}** user(s) with multiple OAuth providers linked."
        )

        df_multi = pd.DataFrame(multi_provider)

        # Display table
        st.dataframe(
            df_multi[["username", "email", "linked_accounts", "providers"]],
            use_container_width=True,
        )

        # Distribution chart
        provider_combinations = df_multi["linked_accounts"].value_counts().reset_index()
        provider_combinations.columns = ["Provider Count", "Users"]

        fig_multi = px.bar(
            provider_combinations,
            x="Provider Count",
            y="Users",
            title="Distribution of Linked Provider Counts",
            text="Users",
        )

        st.plotly_chart(fig_multi, use_container_width=True)

    else:
        st.info("No users have linked multiple OAuth providers yet.")

    st.markdown("---")

    # =====================================================
    # FOOTER
    # =====================================================

    st.caption(
        "💡 **Tip**: OAuth analytics views are refreshed when you click the 'Refresh Data' button. "
        "For real-time data, refresh the views before viewing the dashboard."
    )
