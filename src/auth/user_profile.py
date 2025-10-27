"""
User profile management UI component.

Provides user profile functionality for Streamlit sidebar:
- Change password
- View active sessions
- Revoke sessions
- View user information
"""

import asyncio

import streamlit as st
import structlog

from src.auth.db import (
    get_user_by_username,
    get_user_sessions,
    revoke_all_user_sessions,
    revoke_session,
    update_user_password,
)
from src.auth.password_strength import is_password_strong, render_password_strength_meter
from src.config import get_settings

logger = structlog.get_logger(__name__)


def get_user_info(username: str) -> dict | None:
    """Get user information from database.

    Args:
        username: Username

    Returns:
        User record or None
    """
    try:
        user = get_user_by_username(username)
        return user
    except Exception as e:
        logger.error("Failed to get user info", username=username, error=str(e))
        return None


def change_user_password(
    username: str, current_password: str, new_password: str
) -> tuple[bool, str]:
    """Change user password.

    Args:
        username: Username
        current_password: Current password for verification
        new_password: New password

    Returns:
        Tuple of (success, message)
    """
    try:
        from src.auth.db import verify_user_password

        # Verify current password
        user = verify_user_password(username, current_password)
        if not user:
            return (False, "Current password is incorrect.")

        # Update password
        update_user_password(user["id"], new_password)

        logger.info("Password changed successfully", username=username)
        return (True, "Password changed successfully!")

    except Exception as e:
        logger.error("Password change failed", username=username, error=str(e))
        return (False, "Failed to change password. Please try again.")


def render_user_profile(username: str):
    """Render user profile section in sidebar.

    Args:
        username: Authenticated username
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 User Profile")

    # Get user info
    try:
        user = get_user_info(username)

        if not user:
            st.sidebar.error("Failed to load user information")
            return

        # User info display
        with st.sidebar.expander("📋 Account Info", expanded=False):
            st.markdown(f"**Username:** {user.get('username')}")
            st.markdown(f"**Email:** {user.get('email')}")

            # Email verification status
            is_verified = user.get("is_email_verified", False)
            if is_verified:
                verified_at = (
                    user.get("email_verified_at", "")[:10]
                    if user.get("email_verified_at")
                    else "N/A"
                )
                st.markdown(f"**Email Status:** ✅ Verified ({verified_at})")
            else:
                st.markdown("**Email Status:** ⚠️ Not Verified")
                st.warning("Please verify your email address to enable all features.")

                # Button to resend verification email
                if st.button(
                    "📧 Resend Verification Email",
                    key="resend_verification",
                    use_container_width=True,
                ):
                    try:
                        from src.auth.email_verification import request_email_verification

                        settings = get_settings()
                        verification_url = settings.verification_url
                        success, message = asyncio.run(
                            request_email_verification(user["id"], verification_url)
                        )

                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    except Exception as e:
                        logger.error("Failed to resend verification email", error=str(e))
                        st.error("Failed to send verification email. Please try again later.")

            st.markdown(f"**Name:** {user.get('full_name')}")
            st.markdown(
                f"**Member Since:** {user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'}"
            )
            st.markdown(
                f"**Last Login:** {user.get('last_login_at', 'Never')[:19] if user.get('last_login_at') else 'Never'}"
            )

        # Change password section
        with st.sidebar.expander("🔑 Change Password", expanded=False):
            # Use session state for password change
            if "change_password_inputs" not in st.session_state:
                st.session_state.change_password_inputs = {
                    "current": "",
                    "new": "",
                    "confirm": "",
                }

            current_password = st.text_input(
                "Current Password",
                type="password",
                key="cp_current",
                value=st.session_state.change_password_inputs["current"],
            )

            new_password = st.text_input(
                "New Password",
                type="password",
                key="cp_new",
                value=st.session_state.change_password_inputs["new"],
            )

            # Show password strength meter if new password entered
            if new_password:
                st.markdown(
                    render_password_strength_meter(new_password),
                    unsafe_allow_html=True,
                )

            confirm_password = st.text_input(
                "Confirm New Password",
                type="password",
                key="cp_confirm",
                value=st.session_state.change_password_inputs["confirm"],
            )

            # Password match indicator
            if new_password and confirm_password:
                if new_password == confirm_password:
                    st.success("✓ Passwords match")
                else:
                    st.error("✗ Passwords do not match")

            if st.button("Change Password", use_container_width=True, key="cp_submit"):
                if not current_password or not new_password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("New passwords do not match.")
                else:
                    # Check password strength
                    is_strong, message = is_password_strong(new_password)

                    if not is_strong:
                        st.error(message)
                    else:
                        # Change password
                        success, msg = change_user_password(
                            username, current_password, new_password
                        )

                        if success:
                            st.success(msg)
                            # Clear inputs on success
                            st.session_state.change_password_inputs = {
                                "current": "",
                                "new": "",
                                "confirm": "",
                            }
                            logger.info("User changed password via profile", username=username)
                            st.rerun()
                        else:
                            st.error(msg)

        # Active sessions section
        with st.sidebar.expander("💻 Active Sessions", expanded=False):
            try:
                sessions = get_user_sessions(user["id"], active_only=True)

                if not sessions:
                    st.info("No active sessions found.")
                else:
                    st.markdown(f"**Total Active Sessions:** {len(sessions)}")

                    # Display sessions
                    for idx, session in enumerate(sessions, 1):
                        st.markdown(f"**Session {idx}:**")
                        created_at = (
                            session.get("created_at", "")[:19]
                            if session.get("created_at")
                            else "N/A"
                        )
                        last_activity = (
                            session.get("last_activity_at", "")[:19]
                            if session.get("last_activity_at")
                            else "N/A"
                        )
                        session_type = session.get("session_type", "N/A")
                        ip_address = session.get("ip_address", "Unknown")

                        st.text(f"Created: {created_at}")
                        st.text(f"Last Activity: {last_activity}")
                        st.text(f"Type: {session_type}")
                        st.text(f"IP: {ip_address}")

                        # Revoke button
                        if st.button(
                            "Revoke This Session",
                            key=f"revoke_session_{session['id']}",
                            use_container_width=True,
                        ):
                            try:
                                success = revoke_session(session["session_token"])
                                if success:
                                    st.success("Session revoked successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to revoke session.")
                            except Exception as e:
                                logger.error("Session revocation failed", error=str(e))
                                st.error("An error occurred.")

                        st.markdown("---")

                    # Revoke all sessions button
                    if len(sessions) > 1:
                        st.markdown("**Danger Zone:**")
                        if st.button(
                            "🚨 Revoke All Sessions",
                            key="revoke_all_sessions",
                            use_container_width=True,
                            type="secondary",
                        ):
                            try:
                                # Confirm action
                                if "confirm_revoke_all" not in st.session_state:
                                    st.session_state.confirm_revoke_all = True
                                    st.warning(
                                        "⚠️ This will log you out from all devices. Click again to confirm."
                                    )
                                else:
                                    count = revoke_all_user_sessions(user["id"])
                                    st.success(f"Revoked {count} session(s).")
                                    st.info("You will be logged out. Please log in again.")
                                    del st.session_state.confirm_revoke_all
                                    # Clear session and reload
                                    st.session_state.clear()
                                    st.rerun()
                            except Exception as e:
                                logger.error("Revoke all sessions failed", error=str(e))
                                st.error("An error occurred.")

            except Exception as e:
                logger.error("Failed to load sessions", error=str(e))
                st.error("Failed to load sessions.")

    except Exception as e:
        logger.error("User profile rendering failed", username=username, error=str(e))
        st.sidebar.error("Failed to load profile.")


def render_user_profile_simple(username: str, full_name: str, email: str | None = None):
    """Render simplified user profile (for YAML mode without database).

    Args:
        username: Username
        full_name: User's full name
        email: User's email (optional)
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 User Profile")

    with st.sidebar.expander("📋 Account Info", expanded=False):
        st.markdown(f"**Username:** {username}")
        if email:
            st.markdown(f"**Email:** {email}")
        st.markdown(f"**Name:** {full_name}")
        st.info(
            "💡 Enable database authentication (`USE_DATABASE_AUTH=true`) for full profile features."
        )
