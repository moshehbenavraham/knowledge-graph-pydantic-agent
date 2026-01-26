"""
Password reset completion page.

This page handles the password reset flow when users click the link in their email.
Can be integrated into the main Streamlit app or used as a standalone page.
"""

import asyncio

import streamlit as st
import structlog

from src.auth.password_reset import reset_password_with_token, validate_reset_token
from src.auth.password_strength import is_password_strong, render_password_strength_meter

logger = structlog.get_logger(__name__)


def render_password_reset_page() -> None:
    """Render password reset completion page."""
    st.markdown(
        """
        <style>
        .reset-container {
            max-width: 500px;
            margin: 2rem auto;
            padding: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .reset-title {
            color: white;
            text-align: center;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
        }
        .reset-subtitle {
            color: rgba(255, 255, 255, 0.9);
            text-align: center;
            margin-bottom: 2rem;
        }
        </style>
        <div class="reset-container">
            <div class="reset-title">🔑 Reset Password</div>
            <div class="reset-subtitle">Knowledge Graph Pydantic Agent Password Reset</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Get token from URL query parameters
    query_params = st.query_params
    token = query_params.get("token", None)

    if not token:
        st.error("❌ No reset token provided. Please use the link from your email.")
        st.info("💡 Tip: Check your email for the password reset link.")
        return

    # Validate token
    try:
        is_valid, message, _token_record = asyncio.run(validate_reset_token(token))

        if not is_valid:
            st.error(f"❌ {message}")
            st.info("💡 Tip: Reset links expire after 1 hour. Request a new reset link if needed.")
            return

        st.success("✅ Your reset link is valid. Enter your new password below.")

        # Use session state for password reset inputs
        if "password_reset_inputs" not in st.session_state:
            st.session_state.password_reset_inputs = {"new": "", "confirm": ""}

        # Password inputs with live feedback (outside form)
        new_password = st.text_input(
            "New Password",
            type="password",
            key="pr_new",
            value=st.session_state.password_reset_inputs["new"],
        )

        # Show password strength meter if password entered
        if new_password:
            st.markdown(
                render_password_strength_meter(new_password),
                unsafe_allow_html=True,
            )

        confirm_password = st.text_input(
            "Confirm New Password",
            type="password",
            key="pr_confirm",
            value=st.session_state.password_reset_inputs["confirm"],
        )

        # Password match indicator
        if new_password and confirm_password:
            if new_password == confirm_password:
                st.success("✓ Passwords match")
            else:
                st.error("✗ Passwords do not match")

        # Submit button (outside form for dynamic feedback)
        if st.button("Reset Password", use_container_width=True, type="primary", key="pr_submit"):
            # Validate passwords match
            if not new_password or not confirm_password:
                st.error("❌ Please fill in both password fields.")
            elif new_password != confirm_password:
                st.error("❌ Passwords do not match.")
            else:
                # Check password strength
                is_strong, strength_message = is_password_strong(new_password)

                if not is_strong:
                    st.error(f"❌ {strength_message}")
                else:
                    # Reset password
                    try:
                        success, reset_message = asyncio.run(
                            reset_password_with_token(token, new_password)
                        )

                        if success:
                            st.success(f"✅ {reset_message}")
                            st.balloons()
                            st.info("You can now log in with your new password.")

                            # Clear inputs on success
                            st.session_state.password_reset_inputs = {"new": "", "confirm": ""}

                            # Show login link
                            if st.button("Go to Login", use_container_width=True, key="pr_login"):
                                st.query_params.clear()  # Clear token from URL
                                st.switch_page("streamlit_app.py")  # Redirect to main app
                        else:
                            st.error(f"❌ {reset_message}")

                    except Exception as e:
                        logger.error("Password reset failed", error=str(e))
                        st.error("An error occurred. Please try again.")

    except Exception as e:
        logger.error("Password reset page error", error=str(e))
        st.error("An error occurred while processing your request.")


if __name__ == "__main__":
    render_password_reset_page()
