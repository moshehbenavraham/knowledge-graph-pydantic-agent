"""Email verification completion page.

This page handles the email verification flow when users click the link in their email.
Can be integrated into the main Streamlit app or used as a standalone page.
"""

import asyncio

import streamlit as st
import structlog

from src.auth.email_verification import use_verification_token, verify_verification_token

logger = structlog.get_logger(__name__)


def render_email_verification_page() -> None:
    """Render email verification completion page."""
    st.markdown(
        """
        <style>
        .verify-container {
            max-width: 500px;
            margin: 2rem auto;
            padding: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .verify-title {
            color: white;
            text-align: center;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
        }
        .verify-subtitle {
            color: rgba(255, 255, 255, 0.9);
            text-align: center;
            margin-bottom: 2rem;
        }
        </style>
        <div class="verify-container">
            <div class="verify-title">✉️ Verify Email</div>
            <div class="verify-subtitle">Luminari Agent Email Verification</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Get token from URL query parameters
    query_params = st.query_params
    token = query_params.get("token", None)

    if not token:
        st.error("❌ No verification token provided. Please use the link from your email.")
        st.info("💡 Tip: Check your email for the verification link.")
        return

    # Validate token
    try:
        token_record = asyncio.run(verify_verification_token(token))

        if not token_record:
            st.error("❌ This verification link is invalid or has expired.")
            st.info(
                "💡 Tip: Verification links expire after 24 hours. Request a new verification email if needed."
            )

            # Option to request new verification email
            st.markdown("---")
            st.markdown("### 📧 Need a new verification link?")
            st.info(
                "Please log in to your account and request a new verification email from your profile."
            )
            return

        # Token is valid, show verification confirmation
        st.success("✅ Your verification link is valid.")
        st.markdown("Click the button below to verify your email address.")

        # Verification button
        if st.button(
            "Verify My Email", use_container_width=True, type="primary", key="verify_submit"
        ):
            try:
                # Use verification token
                success = asyncio.run(use_verification_token(token))

                if success:
                    st.success("✅ Email verified successfully!")
                    st.balloons()
                    st.success("🎉 Your account is now fully activated!")

                    st.markdown("---")
                    st.markdown("### 🚀 What's next?")
                    st.markdown("- Log in to your account to start using Luminari Agent")
                    st.markdown("- Explore the powerful RAG capabilities")
                    st.markdown("- Connect your data sources and knowledge bases")

                    # Show login link
                    if st.button("Go to Login", use_container_width=True, key="verify_login"):
                        st.query_params.clear()  # Clear token from URL
                        st.switch_page("streamlit_app.py")  # Redirect to main app
                else:
                    st.error("❌ Email verification failed. Please try again.")

            except Exception as e:
                logger.error("Email verification failed", error=str(e))

                if "Invalid or expired" in str(e):
                    st.error("❌ This verification link is invalid or has already been used.")
                    st.info(
                        "💡 Tip: Each verification link can only be used once. Request a new verification email if needed."
                    )
                else:
                    st.error("❌ An error occurred. Please try again.")

    except Exception as e:
        logger.error("Email verification page error", error=str(e))
        st.error("❌ An error occurred while processing your request.")


if __name__ == "__main__":
    render_email_verification_page()
