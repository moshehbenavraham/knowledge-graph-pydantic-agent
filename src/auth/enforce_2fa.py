"""
Two-Factor Authentication Enforcement Module

This module provides 2FA enforcement functionality for users who are required
to use 2FA (e.g., admin users). It handles:
- Checking if a user requires 2FA
- Enforcing 2FA setup if not configured
- Verifying TOTP codes during login
- Managing 2FA verification state in session
"""

import streamlit as st
import structlog

from src.auth.db import get_user_by_username
from src.auth.totp_2fa import get_backup_code_manager, get_totp_manager

logger = structlog.get_logger(__name__)


def check_2fa_requirement(username: str) -> tuple[bool, bool]:
    """
    Check if user requires 2FA and if it's enabled.

    Args:
        username: Username to check

    Returns:
        Tuple of (requires_2fa, is_2fa_enabled)
    """
    try:
        user = get_user_by_username(username)
        if not user:
            return False, False

        requires_2fa = user.get("requires_2fa", False)

        # Check if 2FA is actually enabled
        totp_manager = get_totp_manager()
        is_2fa_enabled = totp_manager.is_2fa_enabled(user["id"])

        return requires_2fa, is_2fa_enabled

    except Exception as e:
        logger.error("Failed to check 2FA requirement", username=username, error=str(e))
        return False, False


def render_2fa_setup_required() -> None:
    """
    Render UI forcing user to set up 2FA.
    This is shown when a user with requires_2fa=true hasn't configured 2FA yet.
    """
    st.warning(
        "⚠️ **Two-Factor Authentication Required**\n\n"
        "Your account requires 2FA to be enabled. Please set up 2FA to continue."
    )

    st.markdown("---")
    st.markdown("### 📱 Set Up Two-Factor Authentication")

    username = st.session_state.get("username")
    if not username:
        st.error("Session error. Please log in again.")
        return

    # Get user info
    try:
        user = get_user_by_username(username)
        if not user:
            st.error("User not found. Please log in again.")
            return

        user_id = user["id"]
        totp_manager = get_totp_manager()
        backup_code_manager = get_backup_code_manager()

        # Step 1: Generate and display QR code
        if "2fa_setup_secret" not in st.session_state:
            st.markdown("#### Step 1: Scan QR Code")
            st.info(
                "📱 Use an authenticator app like Google Authenticator, "
                "Authy, or Microsoft Authenticator to scan this QR code."
            )

            # Generate secret and QR code
            secret = totp_manager.generate_and_store_secret(user_id)
            qr_code = totp_manager.generate_qr_code(secret, username)

            # Store secret in session for verification
            st.session_state["2fa_setup_secret"] = secret

            # Display QR code
            st.image(qr_code, caption="Scan this QR code with your authenticator app")

            # Also show manual entry key
            with st.expander("📝 Can't scan? Enter manually"):
                st.code(secret, language=None)
                st.caption("Enter this code manually in your authenticator app")

            st.markdown("---")

        # Step 2: Verify TOTP code
        st.markdown("#### Step 2: Verify Your Setup")
        st.write("Enter the 6-digit code from your authenticator app to verify:")

        verification_code = st.text_input(
            "Verification Code",
            max_chars=6,
            key="2fa_setup_verification_code",
            placeholder="123456",
        )

        col1, _col2 = st.columns([1, 3])
        with col1:
            verify_button = st.button("✅ Verify & Enable 2FA", use_container_width=True)

        if verify_button:
            if not verification_code or len(verification_code) != 6:
                st.error("Please enter a valid 6-digit code")
            else:
                # Verify the code
                try:
                    is_valid = totp_manager.verify_totp(user_id, verification_code)

                    if is_valid:
                        # Enable 2FA
                        success = totp_manager.enable_2fa(user_id, verification_code)

                        if success:
                            # Generate backup codes
                            backup_codes = backup_code_manager.generate_backup_codes(user_id)

                            st.success("✅ 2FA enabled successfully!")
                            st.balloons()

                            # Display backup codes
                            st.markdown("---")
                            st.markdown("#### 🔑 Save Your Backup Codes")
                            st.warning(
                                "⚠️ **IMPORTANT**: Save these backup codes in a safe place. "
                                "You can use them to access your account if you lose "
                                "access to your authenticator app."
                            )

                            # Display backup codes in a copyable format
                            backup_codes_text = "\n".join(backup_codes)
                            st.code(backup_codes_text, language=None)

                            st.info(
                                "💡 **Tip**: Print these codes or save them in a password manager."
                            )

                            # Mark 2FA as verified in session
                            st.session_state["2fa_verified"] = True
                            st.session_state.pop("2fa_setup_secret", None)

                            # Add continue button
                            if st.button("Continue to Luminari Agent", type="primary"):
                                st.rerun()

                        else:
                            st.error("Failed to enable 2FA. Please try again.")
                    else:
                        st.error("❌ Invalid code. Please try again.")

                except Exception as e:
                    logger.error("2FA setup failed", username=username, error=str(e))
                    st.error("An error occurred during setup. Please try again.")

    except Exception as e:
        logger.error("Failed to render 2FA setup", username=username, error=str(e))
        st.error("An error occurred. Please try again or contact support.")


def render_2fa_verification() -> bool:
    """
    Render 2FA verification UI for login.
    This is shown when a user with 2FA enabled logs in.

    Returns:
        True if verification successful, False otherwise
    """
    st.info("🔐 **Two-Factor Authentication**\n\nEnter your 6-digit authentication code.")

    username = st.session_state.get("username")
    if not username:
        st.error("Session error. Please log in again.")
        return False

    # Get user info
    try:
        user = get_user_by_username(username)
        if not user:
            st.error("User not found. Please log in again.")
            return False

        user_id = user["id"]
        totp_manager = get_totp_manager()
        backup_code_manager = get_backup_code_manager()

        # Verification code input
        verification_code = st.text_input(
            "Authentication Code",
            max_chars=8,  # 6 for TOTP or 9 for backup codes (XXXX-XXXX)
            key="2fa_verification_code",
            placeholder="123456 or XXXX-XXXX",
        )

        col1, _col2 = st.columns([1, 2])
        with col1:
            verify_button = st.button("🔐 Verify", use_container_width=True)

        if verify_button:
            if not verification_code:
                st.error("Please enter a verification code")
                return False

            # Remove any spaces or dashes from input
            clean_code = verification_code.replace(" ", "").replace("-", "")

            try:
                # Try TOTP first (6 digits)
                if len(clean_code) == 6 and clean_code.isdigit():
                    is_valid = totp_manager.verify_totp(user_id, clean_code)

                    if is_valid:
                        st.success("✅ Verification successful!")
                        st.session_state["2fa_verified"] = True
                        return True
                    st.error("❌ Invalid code. Please try again.")
                    return False

                # Try backup code (8 characters)
                if len(clean_code) == 8:
                    is_valid = backup_code_manager.verify_backup_code(user_id, clean_code)

                    if is_valid:
                        st.success("✅ Backup code accepted!")
                        st.warning(
                            "⚠️ This backup code has been used and is no longer valid. "
                            "Please generate new backup codes in your profile settings."
                        )
                        st.session_state["2fa_verified"] = True
                        return True
                    st.error("❌ Invalid backup code.")
                    return False

                st.error("❌ Invalid code format. Enter 6 digits or an 8-character backup code.")
                return False

            except Exception as e:
                logger.error("2FA verification failed", username=username, error=str(e))
                st.error("Verification failed. Please try again.")
                return False

        # Show backup code option
        with st.expander("🔑 Lost your device? Use a backup code"):
            st.write(
                "Enter one of your backup codes if you don't have access "
                "to your authenticator app."
            )
            st.caption("Format: XXXX-XXXX (8 characters)")

        return False

    except Exception as e:
        logger.error("Failed to render 2FA verification", username=username, error=str(e))
        st.error("An error occurred. Please try again.")
        return False


def enforce_2fa_if_required(username: str) -> bool:
    """
    Main enforcement function to check and enforce 2FA.
    Should be called after successful password authentication.

    Args:
        username: Username of authenticated user

    Returns:
        True if 2FA is satisfied (or not required), False if needs attention
    """
    try:
        # Check if 2FA is required
        requires_2fa, is_2fa_enabled = check_2fa_requirement(username)

        # If 2FA not required, allow access
        if not requires_2fa:
            return True

        # If 2FA required but not enabled, force setup
        if not is_2fa_enabled:
            logger.info("User requires 2FA but not enabled, forcing setup", username=username)
            render_2fa_setup_required()
            return False

        # If 2FA enabled, check if already verified in this session
        if st.session_state.get("2fa_verified"):
            return True

        # Require 2FA verification
        logger.info("Requiring 2FA verification for user", username=username)
        verified = render_2fa_verification()

        if verified:
            # Rerun to continue to main app
            st.rerun()

        return False

    except Exception as e:
        logger.error("2FA enforcement check failed", username=username, error=str(e))
        st.error("An error occurred during authentication. Please try again.")
        return False
