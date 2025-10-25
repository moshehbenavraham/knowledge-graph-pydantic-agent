"""
Admin 2FA Management UI Component

Provides admin interface for managing 2FA requirements for users.
This component can be included in admin dashboards or user management pages.
"""

import asyncio

import streamlit as st
import structlog

from src.auth.db import get_2fa_requirement, get_user_roles, list_users, set_2fa_requirement

logger = structlog.get_logger(__name__)


async def is_admin(username: str) -> bool:
    """
    Check if a user has admin role.

    Args:
        username: Username to check

    Returns:
        True if user has admin role
    """
    try:
        from src.auth.db import get_user_by_username

        user = await get_user_by_username(username)
        if not user:
            return False

        roles = await get_user_roles(user["id"])
        return any(role.get("name") == "admin" for role in roles)

    except Exception as e:
        logger.error("Failed to check admin status", username=username, error=str(e))
        return False


def render_2fa_management_ui() -> None:
    """
    Render admin UI for managing 2FA requirements.

    This function should only be called for authenticated admin users.
    """
    current_username = st.session_state.get("username")
    if not current_username:
        st.error("Not authenticated")
        return

    # Check if current user is admin
    is_admin_user = asyncio.run(is_admin(current_username))
    if not is_admin_user:
        st.error("⛔ Access denied. Admin privileges required.")
        return

    st.markdown("### 🔐 Two-Factor Authentication Management")
    st.markdown("Manage 2FA requirements for user accounts.")

    # Load all users
    try:
        users = asyncio.run(list_users(limit=1000, include_deleted=False))

        # Filter to active users only
        active_users = [u for u in users if u.get("is_active", False)]

        if not active_users:
            st.info("No active users found.")
            return

        # Create a data table
        st.markdown("#### User 2FA Status")

        # Group users by 2FA requirement
        users_requiring_2fa = [u for u in active_users if u.get("requires_2fa", False)]
        users_not_requiring_2fa = [u for u in active_users if not u.get("requires_2fa", False)]

        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Users", len(active_users))
        with col2:
            st.metric("2FA Required", len(users_requiring_2fa))
        with col3:
            st.metric("2FA Optional", len(users_not_requiring_2fa))

        st.markdown("---")

        # User management interface
        st.markdown("#### Manage User 2FA Requirements")

        # Select user
        user_options = {
            f"{u['username']} ({u['email']}) - {u.get('full_name', 'N/A')}": u["username"]
            for u in active_users
        }

        selected_display = st.selectbox(
            "Select User",
            options=list(user_options.keys()),
            key="2fa_mgmt_user_select",
        )

        if selected_display:
            selected_username = user_options[selected_display]

            # Get current 2FA status
            user = next((u for u in active_users if u["username"] == selected_username), None)
            if user:
                current_requirement = user.get("requires_2fa", False)

                # Display current status
                st.markdown(f"**Current Status:** {'✅ 2FA Required' if current_requirement else '❌ 2FA Optional'}")

                # Get user's 2FA setup status
                from src.auth.totp_2fa import get_totp_manager

                totp_manager = get_totp_manager()
                try:
                    status = asyncio.run(totp_manager.get_2fa_status(user["id"]))
                    is_2fa_enabled = status.get("is_enabled", False)
                    has_backup_codes = status.get("backup_codes_count", 0) > 0

                    if is_2fa_enabled:
                        st.success(
                            f"✅ User has configured 2FA "
                            f"({status.get('backup_codes_count', 0)} backup codes remaining)"
                        )
                    else:
                        st.warning("⚠️ User has NOT configured 2FA yet")

                except Exception as e:
                    logger.error("Failed to get 2FA status", username=selected_username, error=str(e))
                    st.warning("Could not retrieve 2FA setup status")

                st.markdown("---")

                # Toggle 2FA requirement
                col1, col2 = st.columns(2)

                with col1:
                    if st.button(
                        "✅ Require 2FA" if not current_requirement else "✅ 2FA Already Required",
                        disabled=current_requirement,
                        use_container_width=True,
                        type="primary" if not current_requirement else "secondary",
                    ):
                        try:
                            asyncio.run(set_2fa_requirement(selected_username, True))
                            st.success(f"✅ 2FA is now required for user '{selected_username}'")
                            logger.info(
                                "2FA requirement enabled",
                                target_user=selected_username,
                                admin_user=current_username,
                            )
                            st.rerun()
                        except Exception as e:
                            logger.error(
                                "Failed to enable 2FA requirement",
                                username=selected_username,
                                error=str(e),
                            )
                            st.error("Failed to update 2FA requirement")

                with col2:
                    if st.button(
                        "❌ Make 2FA Optional" if current_requirement else "❌ 2FA Already Optional",
                        disabled=not current_requirement,
                        use_container_width=True,
                        type="secondary",
                    ):
                        try:
                            asyncio.run(set_2fa_requirement(selected_username, False))
                            st.success(f"✅ 2FA is now optional for user '{selected_username}'")
                            logger.info(
                                "2FA requirement disabled",
                                target_user=selected_username,
                                admin_user=current_username,
                            )
                            st.rerun()
                        except Exception as e:
                            logger.error(
                                "Failed to disable 2FA requirement",
                                username=selected_username,
                                error=str(e),
                            )
                            st.error("Failed to update 2FA requirement")

                # Warning for removing requirement
                if current_requirement and is_2fa_enabled:
                    st.info(
                        "ℹ️ **Note**: Removing the 2FA requirement will allow this user to log in "
                        "without 2FA verification, but their 2FA configuration will be preserved."
                    )

        st.markdown("---")

        # Bulk actions section
        with st.expander("⚡ Bulk Actions"):
            st.markdown("#### Apply 2FA Requirement to Multiple Users")

            # Role-based bulk action
            st.markdown("**By Role:**")
            if st.button("Require 2FA for all Admin users", use_container_width=True):
                try:
                    # Get all users with admin role
                    admin_count = 0
                    for user in active_users:
                        roles = asyncio.run(get_user_roles(user["id"]))
                        if any(role.get("name") == "admin" for role in roles):
                            if not user.get("requires_2fa", False):
                                asyncio.run(set_2fa_requirement(user["username"], True))
                                admin_count += 1

                    if admin_count > 0:
                        st.success(f"✅ Enabled 2FA requirement for {admin_count} admin user(s)")
                        logger.info(
                            "Bulk 2FA requirement enabled for admins",
                            count=admin_count,
                            admin_user=current_username,
                        )
                        st.rerun()
                    else:
                        st.info("All admin users already require 2FA")

                except Exception as e:
                    logger.error("Failed to apply bulk 2FA requirement", error=str(e))
                    st.error("Failed to apply bulk action")

    except Exception as e:
        logger.error("Failed to load users for 2FA management", error=str(e))
        st.error("Failed to load user list. Please try again.")


def render_user_2fa_settings(username: str) -> None:
    """
    Render 2FA settings in user profile.

    Shows the user's current 2FA status and allows them to enable/disable it
    (if not required by admin).

    Args:
        username: Username of the logged-in user
    """
    st.markdown("### 🔐 Two-Factor Authentication")

    try:
        # Get user info
        from src.auth.db import get_user_by_username

        user = asyncio.run(get_user_by_username(username))
        if not user:
            st.error("User not found")
            return

        user_id = user["id"]
        requires_2fa = user.get("requires_2fa", False)

        # Get 2FA status
        from src.auth.totp_2fa import get_totp_manager

        totp_manager = get_totp_manager()
        status = asyncio.run(totp_manager.get_2fa_status(user_id))
        is_2fa_enabled = status.get("is_enabled", False)
        backup_codes_count = status.get("backup_codes_count", 0)

        # Display current status
        if requires_2fa:
            st.info("🔒 **2FA is required** for your account by your administrator.")
        else:
            st.info("🔓 **2FA is optional** for your account.")

        if is_2fa_enabled:
            st.success(
                f"✅ **2FA is enabled**\n\n"
                f"You have {backup_codes_count} backup code(s) remaining."
            )

            # Option to regenerate backup codes
            if st.button("🔄 Regenerate Backup Codes", use_container_width=True):
                from src.auth.totp_2fa import get_backup_code_manager

                backup_code_manager = get_backup_code_manager()
                try:
                    new_codes = asyncio.run(backup_code_manager.generate_backup_codes(user_id))
                    st.success("✅ New backup codes generated!")
                    st.code("\n".join(new_codes), language=None)
                    st.warning("⚠️ Save these codes securely. Previous backup codes are now invalid.")
                except Exception as e:
                    logger.error("Failed to regenerate backup codes", error=str(e))
                    st.error("Failed to regenerate backup codes")

            # Option to disable 2FA (if not required)
            if not requires_2fa:
                st.markdown("---")
                if st.button("❌ Disable 2FA", use_container_width=True, type="secondary"):
                    st.warning("Are you sure you want to disable 2FA? This will reduce your account security.")
                    if st.button("⚠️ Yes, Disable 2FA", type="primary"):
                        try:
                            success = asyncio.run(totp_manager.disable_2fa(user_id))
                            if success:
                                st.success("✅ 2FA disabled successfully")
                                st.rerun()
                            else:
                                st.error("Failed to disable 2FA")
                        except Exception as e:
                            logger.error("Failed to disable 2FA", error=str(e))
                            st.error("Failed to disable 2FA")

        else:
            st.warning("⚠️ **2FA is not enabled** for your account.")
            st.write("Enable two-factor authentication to add an extra layer of security.")

            if st.button("📱 Set Up 2FA", use_container_width=True, type="primary"):
                # Redirect to 2FA setup (handled by enforce_2fa module)
                st.session_state["force_2fa_setup"] = True
                st.rerun()

    except Exception as e:
        logger.error("Failed to render 2FA settings", username=username, error=str(e))
        st.error("Failed to load 2FA settings")
